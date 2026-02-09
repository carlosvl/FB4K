"""
Main entry point for Salesforce Data Migration Application
"""

import sys
from typing import Optional
from .salesforce_client import SalesforceClient
from .database_manager import DatabaseManager
from .data_extractor import DataExtractor
from .relationship_mapper import RelationshipMapper
from .migration_engine import MigrationEngine


class MigrationApp:
    """Interactive application for Salesforce data migration."""
    
    def __init__(self):
        """Initialize the migration application."""
        self.sf_client = SalesforceClient()
        self.db_manager = DatabaseManager()
        self.data_extractor = DataExtractor(self.sf_client, self.db_manager)
        self.relationship_mapper = RelationshipMapper(self.db_manager)
        self.migration_engine = MigrationEngine(self.sf_client, self.db_manager)
    
    def display_menu(self):
        """Display the main menu."""
        # Get available orgs
        orgs = self.sf_client.list_orgs()
        
        print("\n" + "="*60)
        print("Salesforce Data Migration Application")
        print("="*60)
        
        # Display available orgs
        if orgs:
            print("\nAvailable Salesforce Orgs:")
            for idx, org in enumerate(orgs, 1):
                alias = org.get('alias') or org.get('username', 'No alias')
                username = org.get('username', 'Unknown')
                print(f"  {idx}. {alias} ({username})")
        else:
            print("\n⚠ No authenticated Salesforce orgs found.")
            print("  Authenticate using: sf org login web")
        
        print("\nMenu Options:")
        print("1. Backup Accounts from Org")
        print("2. Backup Contacts from Org")
        print("3. View Staged Data")
        print("4. Migrate Data to Target Org")
        print("5. Validate Relationships")
        print("6. Compare Data Between Orgs")
        print("0. Exit")
        print("="*60)
    
    def select_org(self, prompt: str = "Select org") -> Optional[str]:
        """Select an org from available SFDX orgs.
        
        Args:
            prompt: Prompt text
            
        Returns:
            Selected org alias or None
        """
        orgs = self.sf_client.list_orgs()
        
        if not orgs:
            print("No authenticated Salesforce orgs found.")
            print("Please authenticate using: sf org login web")
            return None
        
        print(f"\n{prompt}:")
        for idx, org in enumerate(orgs, 1):
            alias = org.get('alias') or org.get('username', 'No alias')
            username = org.get('username', 'Unknown')
            print(f"  {idx}. {alias} ({username})")
        
        try:
            choice = input("\nEnter selection (number): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(orgs):
                selected_org = orgs[idx]
                return selected_org.get('alias') or selected_org.get('username')
            else:
                print("Invalid selection")
                return None
        except ValueError:
            print("Invalid input. Please enter a number.")
            return None
    
    def backup_accounts(self):
        """Backup accounts from selected org."""
        print("\n--- Backup Accounts ---")
        org_alias = self.select_org("Select org to backup accounts from")
        
        if not org_alias:
            return
        
        try:
            accounts = self.data_extractor.extract_accounts(org_alias)
            print(f"\nSuccessfully backed up {len(accounts)} accounts from {org_alias}")
        except Exception as e:
            print(f"Error backing up accounts: {e}")
    
    def backup_contacts(self):
        """Backup contacts from selected org."""
        print("\n--- Backup Contacts ---")
        org_alias = self.select_org("Select org to backup contacts from")
        
        if not org_alias:
            return
        
        try:
            contacts = self.data_extractor.extract_contacts(org_alias, auto_fetch_accounts=True)
            print(f"\nSuccessfully backed up {len(contacts)} contacts from {org_alias}")
        except Exception as e:
            print(f"Error backing up contacts: {e}")
    
    def view_staged_data(self):
        """View staged data in the database."""
        print("\n--- View Staged Data ---")
        
        # Get record counts by org
        counts = self.db_manager.get_record_counts_by_org()
        
        if not counts:
            print("No data staged in database.")
            return
        
        print("\nRecord counts by org:")
        print("-" * 40)
        for org, org_counts in counts.items():
            print(f"{org}:")
            print(f"  Accounts: {org_counts['accounts']}")
            print(f"  Contacts: {org_counts['contacts']}")
        
        # Ask what to view
        print("\nWhat would you like to view?")
        print("1. Accounts")
        print("2. Contacts")
        print("3. Record Types")
        print("4. Migration Log")
        
        try:
            choice = input("\nEnter selection: ").strip()
            
            if choice == '1':
                self._view_accounts()
            elif choice == '2':
                self._view_contacts()
            elif choice == '3':
                self._view_record_types()
            elif choice == '4':
                self._view_migration_log()
            else:
                print("Invalid selection")
        except Exception as e:
            print(f"Error viewing data: {e}")
    
    def _view_accounts(self):
        """View accounts."""
        org_source = input("Enter org source (or press Enter for all): ").strip() or None
        
        accounts = self.db_manager.get_accounts(org_source)
        
        if not accounts:
            print("No accounts found.")
            return
        
        print(f"\nFound {len(accounts)} accounts:")
        print("-" * 80)
        
        # Show first 20 accounts
        for idx, account in enumerate(accounts[:20], 1):
            name = account.get('name') or account.get('Name', 'N/A')
            salesforce_id = account.get('salesforce_id') or account.get('Id', 'N/A')
            record_type = account.get('record_type_name') or 'Default'
            org = account.get('org_source', 'N/A')
            
            print(f"{idx}. {name} ({salesforce_id})")
            print(f"   Record Type: {record_type}, Org: {org}")
        
        if len(accounts) > 20:
            print(f"\n... and {len(accounts) - 20} more accounts")
    
    def _view_contacts(self):
        """View contacts."""
        org_source = input("Enter org source (or press Enter for all): ").strip() or None
        
        contacts = self.db_manager.get_contacts(org_source)
        
        if not contacts:
            print("No contacts found.")
            return
        
        print(f"\nFound {len(contacts)} contacts:")
        print("-" * 80)
        
        # Show first 20 contacts
        for idx, contact in enumerate(contacts[:20], 1):
            name = contact.get('name') or contact.get('Name', 'N/A')
            salesforce_id = contact.get('salesforce_id') or contact.get('Id', 'N/A')
            account_id = contact.get('account_id') or contact.get('AccountId', 'N/A')
            record_type = contact.get('record_type_name') or 'Default'
            org = contact.get('org_source', 'N/A')
            
            print(f"{idx}. {name} ({salesforce_id})")
            print(f"   Account: {account_id}, Record Type: {record_type}, Org: {org}")
        
        if len(contacts) > 20:
            print(f"\n... and {len(contacts) - 20} more contacts")
    
    def _view_record_types(self):
        """View record types."""
        object_type = input("Enter object type (Account/Contact) or press Enter for all: ").strip()
        
        if object_type:
            orgs = self.db_manager.get_record_counts_by_org().keys()
            for org in orgs:
                record_types = self.db_manager.get_record_types(object_type, org)
                if record_types:
                    print(f"\n{object_type} Record Types in {org}:")
                    for rt in record_types:
                        print(f"  - {rt['record_type_name']} ({rt['record_type_id']})")
        else:
            orgs = self.db_manager.get_record_counts_by_org().keys()
            for org in orgs:
                for obj_type in ['Account', 'Contact']:
                    record_types = self.db_manager.get_record_types(obj_type, org)
                    if record_types:
                        print(f"\n{obj_type} Record Types in {org}:")
                        for rt in record_types:
                            print(f"  - {rt['record_type_name']} ({rt['record_type_id']})")
    
    def _view_migration_log(self):
        """View migration log."""
        org_source = input("Enter source org (or press Enter for all): ").strip() or None
        org_target = input("Enter target org (or press Enter for all): ").strip() or None
        
        logs = self.db_manager.get_migration_status(org_source, org_target)
        
        if not logs:
            print("No migration logs found.")
            return
        
        print(f"\nFound {len(logs)} migration log entries:")
        print("-" * 100)
        
        # Show last 20 entries
        for log in logs[:20]:
            status = log.get('status', 'UNKNOWN')
            obj_type = log.get('object_type', 'N/A')
            source_id = log.get('salesforce_id_source', 'N/A')
            target_id = log.get('salesforce_id_target', 'N/A')
            error = log.get('error_message', '')
            timestamp = log.get('timestamp', 'N/A')
            
            print(f"{timestamp} - {obj_type} {source_id} -> {target_id} [{status}]")
            if error:
                print(f"  Error: {error}")
        
        if len(logs) > 20:
            print(f"\n... and {len(logs) - 20} more log entries")
    
    def migrate_data(self):
        """Migrate data to target org."""
        print("\n--- Migrate Data to Target Org ---")
        
        org_source = self.select_org("Select source org")
        if not org_source:
            return
        
        org_target = self.select_org("Select target org")
        if not org_target:
            return
        
        if org_source == org_target:
            print("Source and target orgs cannot be the same!")
            return
        
        # Confirm migration
        print(f"\nThis will migrate data from {org_source} to {org_target}")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Migration cancelled.")
            return
        
        try:
            results = self.migration_engine.migrate_all(org_source, org_target)
            
            print("\n" + "="*60)
            print("Migration Summary")
            print("="*60)
            print(f"Accounts: {results['accounts']['success']} succeeded, {results['accounts']['failed']} failed")
            print(f"Contacts: {results['contacts']['success']} succeeded, {results['contacts']['failed']} failed")
            print(f"Total: {results['total_success']} succeeded, {results['total_failed']} failed")
            
            if results['accounts']['errors'] or results['contacts']['errors']:
                print("\nErrors occurred during migration. Check migration log for details.")
        except Exception as e:
            print(f"Error during migration: {e}")
    
    def validate_relationships(self):
        """Validate relationships."""
        print("\n--- Validate Relationships ---")
        
        try:
            validation = self.relationship_mapper.validate_all_relationships()
            
            print("\nRelationship Validation Results:")
            print("-" * 60)
            print(f"Total Accounts: {validation['account_count']}")
            print(f"Total Contacts: {validation['contact_count']}")
            print(f"Total Relationships: {validation['relationship_count']}")
            print(f"Orphaned Contacts: {validation['orphaned_count']}")
            
            if validation['orphaned_contacts']:
                print("\nOrphaned Contacts (contacts with invalid account references):")
                for contact in validation['orphaned_contacts'][:10]:
                    print(f"  - {contact.get('name', 'N/A')} ({contact.get('salesforce_id', 'N/A')})")
                    print(f"    Missing Account: {contact.get('account_id', 'N/A')}")
                
                if len(validation['orphaned_contacts']) > 10:
                    print(f"  ... and {len(validation['orphaned_contacts']) - 10} more")
            
            if validation['is_valid']:
                print("\n✓ All relationships are valid!")
            else:
                print("\n✗ Some relationships are invalid. Consider fixing orphaned contacts.")
        except Exception as e:
            print(f"Error validating relationships: {e}")
    
    def compare_orgs(self):
        """Compare data between orgs."""
        print("\n--- Compare Data Between Orgs ---")
        
        org1 = self.select_org("Select first org")
        if not org1:
            return
        
        org2 = self.select_org("Select second org")
        if not org2:
            return
        
        try:
            counts1 = self.db_manager.get_record_counts_by_org().get(org1, {})
            counts2 = self.db_manager.get_record_counts_by_org().get(org2, {})
            
            print("\n" + "="*60)
            print("Data Comparison")
            print("="*60)
            print(f"{org1:30} | {org2:30}")
            print("-" * 60)
            print(f"Accounts: {counts1.get('accounts', 0):28} | {counts2.get('accounts', 0):30}")
            print(f"Contacts: {counts1.get('contacts', 0):28} | {counts2.get('contacts', 0):30}")
            
            # Compare record types
            print("\nRecord Types:")
            for obj_type in ['Account', 'Contact']:
                rt1 = self.db_manager.get_record_types(obj_type, org1)
                rt2 = self.db_manager.get_record_types(obj_type, org2)
                
                rt1_names = {rt['record_type_name'] for rt in rt1}
                rt2_names = {rt['record_type_name'] for rt in rt2}
                
                print(f"\n{obj_type}:")
                print(f"  {org1}: {len(rt1_names)} record types")
                print(f"  {org2}: {len(rt2_names)} record types")
                
                only_in_org1 = rt1_names - rt2_names
                only_in_org2 = rt2_names - rt1_names
                common = rt1_names & rt2_names
                
                if only_in_org1:
                    print(f"  Only in {org1}: {', '.join(only_in_org1)}")
                if only_in_org2:
                    print(f"  Only in {org2}: {', '.join(only_in_org2)}")
                if common:
                    print(f"  Common: {', '.join(common)}")
        except Exception as e:
            print(f"Error comparing orgs: {e}")
    
    def run(self):
        """Run the interactive application."""
        print("Welcome to Salesforce Data Migration Application!")
        print("Make sure you have authenticated Salesforce orgs using SFDX CLI")
        
        while True:
            try:
                self.display_menu()
                choice = input("\nEnter your choice: ").strip()
                
                if choice == '0':
                    print("Exiting...")
                    break
                elif choice == '1':
                    self.backup_accounts()
                elif choice == '2':
                    self.backup_contacts()
                elif choice == '3':
                    self.view_staged_data()
                elif choice == '4':
                    self.migrate_data()
                elif choice == '5':
                    self.validate_relationships()
                elif choice == '6':
                    self.compare_orgs()
                else:
                    print("Invalid choice. Please try again.")
                
                input("\nPress Enter to continue...")
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                input("Press Enter to continue...")
        
        # Cleanup
        self.db_manager.close()


def main():
    """Main entry point."""
    app = MigrationApp()
    app.run()


if __name__ == '__main__':
    main()
