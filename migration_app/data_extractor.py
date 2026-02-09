"""
Data extractor for pulling data from Salesforce orgs
"""

import base64
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from .salesforce_client import SalesforceClient
from .database_manager import DatabaseManager
from .utils import get_file_storage_path, save_binary_file, decode_base64


class DataExtractor:
    """Extracts data from Salesforce orgs and stores in SQLite."""
    
    def __init__(self, salesforce_client: SalesforceClient, db_manager: DatabaseManager):
        """Initialize data extractor.
        
        Args:
            salesforce_client: Salesforce client instance
            db_manager: Database manager instance
        """
        self.sf_client = salesforce_client
        self.db_manager = db_manager
    
    def extract_record_types(self, org_alias: str, object_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract record types for specified object types.
        
        Args:
            org_alias: Org alias or username
            object_types: List of object types (e.g., ['Account', 'Contact'])
            
        Returns:
            Dictionary mapping object_type to list of record types
        """
        record_types_by_object = {}
        
        for object_type in object_types:
            soql = f"""
                SELECT Id, Name, SObjectType, DeveloperName
                FROM RecordType
                WHERE SObjectType = '{object_type}'
            """
            
            records = self.sf_client.query(org_alias, soql)
            if records:
                record_types_by_object[object_type] = records
                # Store in database
                self.db_manager.insert_record_types(object_type, records, org_alias)
        
        return record_types_by_object
    
    def get_all_queryable_fields(self, org_alias: str, object_name: str) -> List[str]:
        """Get all queryable fields for an object.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            
        Returns:
            List of queryable field names
        """
        describe = self.sf_client.describe_object(org_alias, object_name)
        if not describe:
            # Fallback: Use SOQL FIELDS(ALL) to get all fields dynamically
            # This is more reliable than describe when there are connection issues
            try:
                # Try using SOQL FIELDS(ALL) syntax to get all fields
                soql = f"SELECT FIELDS(ALL) FROM {object_name} LIMIT 1"
                test_records = self.sf_client.query(org_alias, soql)
                
                if test_records and len(test_records) > 0:
                    # Extract field names from the first record
                    fields = [key for key in test_records[0].keys() if key != 'attributes']
                    return fields
            except Exception as e:
                pass
            
            # Final fallback to basic fields if describe fails
            if object_name == 'Account':
                return ['Id', 'Name', 'RecordTypeId', 'CreatedDate', 'LastModifiedDate']
            elif object_name == 'Contact':
                return ['Id', 'Name', 'AccountId', 'RecordTypeId', 'CreatedDate', 'LastModifiedDate']
            else:
                return ['Id', 'Name', 'CreatedDate', 'LastModifiedDate']
        
        fields = describe.get('fields', [])
        queryable_fields = []
        
        for field in fields:
            field_name = field.get('name')
            field_type = field.get('type', '')
            
            # Skip compound fields (address, location) and fields that can't be in SELECT
            # Most fields are queryable by default unless they're special types
            if field_type not in ['address', 'location'] and field_name:
                queryable_fields.append(field_name)
        
        # Always ensure Id is included
        if 'Id' not in queryable_fields:
            queryable_fields.insert(0, 'Id')
        
        return queryable_fields
    
    def extract_field_metadata(self, org_alias: str, object_types: List[str]):
        """Extract and cache field metadata for objects.
        
        Args:
            org_alias: Org alias or username
            object_types: List of object types to extract metadata for
        """
        for object_type in object_types:
            describe = self.sf_client.describe_object(org_alias, object_type)
            if describe:
                fields = describe.get('fields', [])
                self.db_manager.insert_field_metadata(object_type, fields, org_alias)
    
    def build_soql_query(self, org_alias: str, object_name: str, 
                        include_record_type: bool = True) -> str:
        """Build a SOQL query to get all fields for an object.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            include_record_type: Whether to include RecordType information
            
        Returns:
            SOQL query string
        """
        # Get all queryable fields
        fields = self.get_all_queryable_fields(org_alias, object_name)
        
        # Build field list
        field_list = ', '.join(fields)
        
        # Add RecordType.Name if needed and RecordTypeId exists
        if include_record_type and 'RecordTypeId' in fields:
            field_list += ', RecordType.Name'
        
        soql = f"SELECT {field_list} FROM {object_name}"
        
        return soql
    
    def extract_accounts(self, org_alias: str, batch_size: int = 200) -> List[Dict[str, Any]]:
        """Extract all accounts from a Salesforce org.
        
        Args:
            org_alias: Org alias or username
            batch_size: Number of records per batch (for pagination)
            
        Returns:
            List of account records
        """
        print(f"Extracting accounts from org: {org_alias}")
        
        # First, extract record types and field metadata
        self.extract_record_types(org_alias, ['Account'])
        self.extract_field_metadata(org_alias, ['Account'])
        
        # Build SOQL query with all fields
        soql = self.build_soql_query(org_alias, 'Account')
        
        # Query all accounts
        accounts = self.sf_client.query_all(org_alias, soql)
        
        if not accounts:
            print(f"No accounts found in org: {org_alias}")
            return []
        
        print(f"Found {len(accounts)} accounts")
        
        # Store in database
        self.db_manager.insert_accounts(accounts, org_alias)
        
        print(f"Stored {len(accounts)} accounts in database")
        
        # Extract files (attachments, notes, content documents) for accounts
        account_ids = [acc.get('Id') for acc in accounts]
        self.extract_files_for_records(org_alias, account_ids, 'Account')
        
        return accounts
    
    def extract_contacts(self, org_alias: str, batch_size: int = 200, 
                        auto_fetch_accounts: bool = True) -> List[Dict[str, Any]]:
        """Extract all contacts from a Salesforce org.
        
        Args:
            org_alias: Org alias or username
            batch_size: Number of records per batch (for pagination)
            auto_fetch_accounts: If True, automatically fetch accounts for contacts
                                 that don't have accounts in local database
            
        Returns:
            List of contact records
        """
        print(f"Extracting contacts from org: {org_alias}")
        
        # First, extract record types and field metadata
        self.extract_record_types(org_alias, ['Contact'])
        self.extract_field_metadata(org_alias, ['Contact'])
        
        # Build SOQL query with all fields
        soql = self.build_soql_query(org_alias, 'Contact')
        
        # Query all contacts
        contacts = self.sf_client.query_all(org_alias, soql)
        
        if not contacts:
            print(f"No contacts found in org: {org_alias}")
            return []
        
        print(f"Found {len(contacts)} contacts")
        
        # Check for missing accounts if auto_fetch_accounts is enabled
        if auto_fetch_accounts:
            missing_account_ids = set()
            for contact in contacts:
                account_id = contact.get('AccountId')
                if account_id and not self.db_manager.account_exists(account_id):
                    missing_account_ids.add(account_id)
            
            if missing_account_ids:
                print(f"Found {len(missing_account_ids)} contacts with accounts not in local database")
                print("Fetching missing accounts...")
                self._fetch_accounts_by_ids(org_alias, list(missing_account_ids))
        
        # Store in database
        self.db_manager.insert_contacts(contacts, org_alias)
        
        print(f"Stored {len(contacts)} contacts in database")
        
        # Extract files (attachments, notes, content documents) for contacts
        contact_ids = [cont.get('Id') for cont in contacts]
        self.extract_files_for_records(org_alias, contact_ids, 'Contact')
        
        return contacts
    
    def _fetch_accounts_by_ids(self, org_alias: str, account_ids: List[str]):
        """Fetch specific accounts by their Salesforce IDs.
        
        Args:
            org_alias: Org alias or username
            account_ids: List of Salesforce account IDs to fetch
        """
        if not account_ids:
            return
        
        # Process in batches of 200 (SOQL IN clause limit)
        batch_size = 200
        all_accounts = []
        
        for i in range(0, len(account_ids), batch_size):
            batch_ids = account_ids[i:i + batch_size]
            # Format IDs for SOQL IN clause
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT Id, Name, RecordTypeId, RecordType.Name, 
                       CreatedDate, LastModifiedDate
                FROM Account
                WHERE Id IN ('{id_list}')
            """
            
            accounts = self.sf_client.query_all(org_alias, soql)
            if accounts:
                all_accounts.extend(accounts)
        
        if all_accounts:
            print(f"Fetched {len(all_accounts)} missing accounts")
            # Store in database
            self.db_manager.insert_accounts(all_accounts, org_alias)
            # Also extract record types for these accounts
            self.extract_record_types(org_alias, ['Account'])
    
    def extract_all(self, org_alias: str, object_types: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all specified object types from an org.
        
        Args:
            org_alias: Org alias or username
            object_types: List of object types to extract (default: ['Account', 'Contact'])
            
        Returns:
            Dictionary mapping object_type to list of records
        """
        if object_types is None:
            object_types = ['Account', 'Contact']
        
        results = {}
        
        for object_type in object_types:
            if object_type == 'Account':
                results['Account'] = self.extract_accounts(org_alias)
            elif object_type == 'Contact':
                results['Contact'] = self.extract_contacts(org_alias)
            else:
                print(f"Unsupported object type: {object_type}")
        
        return results
    
    def get_record_count(self, org_alias: str, object_name: str) -> int:
        """Get count of records for an object in an org.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            
        Returns:
            Count of records
        """
        soql = f"SELECT COUNT() FROM {object_name}"
        
        try:
            # Use query to get count
            result = self.sf_client.query(org_alias, f"SELECT COUNT() FROM {object_name}")
            if result:
                # The query returns records, so count them
                return len(result)
        except Exception as e:
            print(f"Error getting count for {object_name}: {e}")
        
        return 0
    
    def extract_attachments(self, org_alias: str, parent_ids: List[str], parent_type: str) -> List[Dict[str, Any]]:
        """Extract Attachment records for parent records.
        
        Args:
            org_alias: Org alias or username
            parent_ids: List of parent record IDs
            parent_type: Type of parent object (Account, Contact)
            
        Returns:
            List of attachment records with file_path added
        """
        if not parent_ids:
            return []
        
        print(f"Extracting attachments for {len(parent_ids)} {parent_type} records...")
        
        all_attachments = []
        batch_size = 200
        
        # Process in batches
        for i in range(0, len(parent_ids), batch_size):
            batch_ids = parent_ids[i:i + batch_size]
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT Id, ParentId, Name, ContentType, BodyLength, Body
                FROM Attachment
                WHERE ParentId IN ('{id_list}')
            """
            
            attachments = self.sf_client.query_all(org_alias, soql)
            
            for attachment in attachments:
                attachment_id = attachment.get('Id')
                parent_id = attachment.get('ParentId')
                name = attachment.get('Name', 'unnamed')
                body_base64 = attachment.get('Body')
                
                if body_base64:
                    # Decode base64 and save file
                    binary_data = decode_base64(body_base64)
                    file_path = get_file_storage_path(org_alias, parent_type, parent_id, 'attachments', name)
                    save_binary_file(file_path, binary_data)
                    
                    attachment['file_path'] = str(file_path)
                    attachment['parent_type'] = parent_type
                    all_attachments.append(attachment)
        
        if all_attachments:
            print(f"Extracted {len(all_attachments)} attachments")
            self.db_manager.insert_attachments(all_attachments, org_alias)
        
        return all_attachments
    
    def extract_notes(self, org_alias: str, parent_ids: List[str], parent_type: str) -> List[Dict[str, Any]]:
        """Extract Note records for parent records.
        
        Args:
            org_alias: Org alias or username
            parent_ids: List of parent record IDs
            parent_type: Type of parent object (Account, Contact)
            
        Returns:
            List of note records with file_path added
        """
        if not parent_ids:
            return []
        
        print(f"Extracting notes for {len(parent_ids)} {parent_type} records...")
        
        all_notes = []
        batch_size = 200
        
        # Process in batches
        for i in range(0, len(parent_ids), batch_size):
            batch_ids = parent_ids[i:i + batch_size]
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT Id, ParentId, Title, Body
                FROM Note
                WHERE ParentId IN ('{id_list}')
            """
            
            notes = self.sf_client.query_all(org_alias, soql)
            
            for note in notes:
                note_id = note.get('Id')
                parent_id = note.get('ParentId')
                title = note.get('Title', 'Untitled')
                body = note.get('Body', '')
                
                # Save note body as text file
                filename = f"{note_id}.txt"
                file_path = get_file_storage_path(org_alias, parent_type, parent_id, 'notes', filename)
                save_binary_file(file_path, body.encode('utf-8'))
                
                note['file_path'] = str(file_path)
                note['parent_type'] = parent_type
                all_notes.append(note)
        
        if all_notes:
            print(f"Extracted {len(all_notes)} notes")
            self.db_manager.insert_notes(all_notes, org_alias)
        
        return all_notes
    
    def extract_content_documents(self, org_alias: str, linked_entity_ids: List[str], linked_entity_type: str) -> List[Dict[str, Any]]:
        """Extract ContentDocument/ContentVersion records (Files) for linked entities.
        
        Args:
            org_alias: Org alias or username
            linked_entity_ids: List of linked entity record IDs
            linked_entity_type: Type of linked entity (Account, Contact)
            
        Returns:
            List of content document records
        """
        if not linked_entity_ids:
            return []
        
        print(f"Extracting files for {len(linked_entity_ids)} {linked_entity_type} records...")
        
        all_documents = []
        batch_size = 200
        
        # Step 1: Get ContentDocumentLinks
        content_document_ids = set()
        document_links = []
        
        for i in range(0, len(linked_entity_ids), batch_size):
            batch_ids = linked_entity_ids[i:i + batch_size]
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT ContentDocumentId, LinkedEntityId
                FROM ContentDocumentLink
                WHERE LinkedEntityId IN ('{id_list}')
            """
            
            links = self.sf_client.query_all(org_alias, soql)
            for link in links:
                doc_id = link.get('ContentDocumentId')
                content_document_ids.add(doc_id)
                link['linked_entity_type'] = linked_entity_type
                document_links.append(link)
        
        if not content_document_ids:
            print("No files found")
            return []
        
        # Step 2: Get ContentDocuments
        doc_id_list = list(content_document_ids)
        content_documents = {}
        
        for i in range(0, len(doc_id_list), batch_size):
            batch_ids = doc_id_list[i:i + batch_size]
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT Id, Title, FileExtension, ContentSize
                FROM ContentDocument
                WHERE Id IN ('{id_list}')
            """
            
            docs = self.sf_client.query_all(org_alias, soql)
            for doc in docs:
                content_documents[doc.get('Id')] = doc
        
        # Step 3: Get ContentVersions (latest version for each document)
        content_versions = {}
        
        for i in range(0, len(doc_id_list), batch_size):
            batch_ids = doc_id_list[i:i + batch_size]
            id_list = "', '".join(batch_ids)
            
            soql = f"""
                SELECT Id, ContentDocumentId, VersionNumber, Title, FileExtension
                FROM ContentVersion
                WHERE ContentDocumentId IN ('{id_list}')
                AND IsLatest = true
            """
            
            versions = self.sf_client.query_all(org_alias, soql)
            for version in versions:
                doc_id = version.get('ContentDocumentId')
                # Keep only the latest version
                if doc_id not in content_versions:
                    content_versions[doc_id] = version
        
        # Step 4: Download and save files
        for doc_id, version in content_versions.items():
            version_id = version.get('Id')
            
            
            if version_id:
                # Download binary data using REST API
                binary_data = self.sf_client.download_content_version_data(org_alias, version_id)
                
                if binary_data:
                    # Find which entity this file is linked to
                    linked_entity_id = None
                    for link in document_links:
                        if link.get('ContentDocumentId') == doc_id:
                            linked_entity_id = link.get('LinkedEntityId')
                            break
                    
                    if linked_entity_id:
                        title = version.get('Title') or content_documents.get(doc_id, {}).get('Title', 'unnamed')
                        file_ext = version.get('FileExtension') or content_documents.get(doc_id, {}).get('FileExtension', '')
                        filename = f"{title}{'.' + file_ext if file_ext else ''}"
                        
                        file_path = get_file_storage_path(org_alias, linked_entity_type, linked_entity_id, 'files', filename)
                        save_binary_file(file_path, binary_data)
                        
                        version['file_path'] = str(file_path)
                        all_documents.append({
                            'document': content_documents.get(doc_id, {}),
                            'version': version,
                            'linked_entity_id': linked_entity_id,
                            'linked_entity_type': linked_entity_type
                        })
        
        # Store in database
        if content_documents:
            self.db_manager.insert_content_documents(list(content_documents.values()), org_alias)
        
        if content_versions:
            versions_list = [v for v in content_versions.values()]
            self.db_manager.insert_content_versions(versions_list, org_alias)
        
        if document_links:
            self.db_manager.insert_content_document_links(document_links, org_alias)
        
        if all_documents:
            print(f"Extracted {len(all_documents)} files")
        
        return all_documents
    
    def extract_files_for_records(self, org_alias: str, record_ids: List[str], object_type: str):
        """Extract all files (attachments, notes, content documents) for records.
        
        Args:
            org_alias: Org alias or username
            record_ids: List of record IDs
            object_type: Object type (Account, Contact)
        """
        if not record_ids:
            return
        
        print(f"\nExtracting files for {len(record_ids)} {object_type} records...")
        
        # Extract attachments
        self.extract_attachments(org_alias, record_ids, object_type)
        
        # Extract notes
        self.extract_notes(org_alias, record_ids, object_type)
        
        # Extract content documents (Files)
        self.extract_content_documents(org_alias, record_ids, object_type)
        
        print(f"File extraction complete for {object_type} records")
