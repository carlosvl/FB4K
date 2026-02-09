"""
Relationship mapper for validating and mapping relationships between objects
"""

from typing import List, Dict, Any
from .database_manager import DatabaseManager


class RelationshipMapper:
    """Maps and validates relationships between Salesforce objects."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize relationship mapper.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
    
    def map_account_contacts(self, org_source: str = None) -> Dict[str, Any]:
        """Map Account-Contact relationships.
        
        Args:
            org_source: Optional org filter
            
        Returns:
            Dictionary with mapping statistics
        """
        contacts = self.db_manager.get_contacts(org_source)
        
        relationship_count = 0
        orphaned_count = 0
        
        for contact in contacts:
            account_id = contact.get('account_id') or contact.get('AccountId')
            if account_id:
                # Check if account exists
                if self.db_manager.account_exists(account_id):
                    relationship_count += 1
                else:
                    orphaned_count += 1
        
        return {
            'total_contacts': len(contacts),
            'contacts_with_accounts': relationship_count,
            'orphaned_contacts': orphaned_count,
            'contacts_without_accounts': len([c for c in contacts if not (c.get('account_id') or c.get('AccountId'))])
        }
    
    def validate_all_relationships(self) -> Dict[str, Any]:
        """Validate all relationships in the database.
        
        Returns:
            Dictionary with validation results
        """
        return self.db_manager.validate_relationships()
    
    def get_orphaned_records(self) -> List[Dict[str, Any]]:
        """Get orphaned contacts (contacts without valid account references).
        
        Returns:
            List of orphaned contact records
        """
        return self.db_manager.get_orphaned_records()
    
    def get_relationship_summary(self, org_source: str = None) -> Dict[str, Any]:
        """Get a summary of relationships.
        
        Args:
            org_source: Optional org filter
            
        Returns:
            Dictionary with relationship summary
        """
        validation = self.validate_all_relationships()
        mapping = self.map_account_contacts(org_source)
        
        return {
            'validation': validation,
            'mapping': mapping,
            'is_valid': validation['is_valid']
        }
    
    def fix_orphaned_contacts(self, data_extractor, org_alias: str) -> int:
        """Attempt to fix orphaned contacts by fetching their accounts.
        
        Args:
            data_extractor: DataExtractor instance
            org_alias: Org alias to fetch accounts from
            
        Returns:
            Number of contacts fixed
        """
        orphaned = self.get_orphaned_records()
        
        if not orphaned:
            return 0
        
        # Filter by org_source if needed
        account_ids = [contact['account_id'] for contact in orphaned 
                      if contact.get('org_source') == org_alias or not org_alias]
        
        if account_ids:
            print(f"Fetching {len(account_ids)} missing accounts to fix orphaned contacts...")
            data_extractor._fetch_accounts_by_ids(org_alias, account_ids)
            
            # Re-validate
            new_orphaned = self.get_orphaned_records()
            fixed_count = len(orphaned) - len(new_orphaned)
            
            return fixed_count
        
        return 0
