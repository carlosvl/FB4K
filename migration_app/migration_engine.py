"""
Migration engine for migrating data from SQLite to target Salesforce org
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from .salesforce_client import SalesforceClient
from .database_manager import DatabaseManager
from .utils import read_binary_file, encode_base64


class MigrationEngine:
    """Engine for migrating data from SQLite staging to target Salesforce org."""
    
    def __init__(self, salesforce_client: SalesforceClient, db_manager: DatabaseManager):
        """Initialize migration engine.
        
        Args:
            salesforce_client: Salesforce client instance
            db_manager: Database manager instance
        """
        self.sf_client = salesforce_client
        self.db_manager = db_manager
        self.record_type_mapping_cache: Dict[str, Dict[str, str]] = {}
    
    def map_record_types(self, source_org: str, target_org: str, 
                        object_type: str) -> Dict[str, str]:
        """Map record types between source and target orgs.
        
        Args:
            source_org: Source org identifier
            target_org: Target org identifier
            object_type: Object type (Account or Contact)
            
        Returns:
            Dictionary mapping source record type ID to target record type ID
        """
        cache_key = f"{source_org}_{target_org}_{object_type}"
        if cache_key in self.record_type_mapping_cache:
            return self.record_type_mapping_cache[cache_key]
        
        # Get record types from both orgs
        source_record_types = self.db_manager.get_record_types(object_type, source_org)
        target_record_types = self.db_manager.get_record_types(object_type, target_org)
        
        # Build mapping by name (assuming names match)
        mapping = {}
        
        # Create lookup by name for target org
        target_by_name = {rt['record_type_name']: rt['record_type_id'] 
                         for rt in target_record_types}
        
        for source_rt in source_record_types:
            source_name = source_rt['record_type_name']
            source_id = source_rt['record_type_id']
            
            # Try to find matching record type by name
            if source_name in target_by_name:
                mapping[source_id] = target_by_name[source_name]
            else:
                # If not found, use default (None means use org default)
                print(f"Warning: Record type '{source_name}' not found in target org. Using default.")
                mapping[source_id] = None
        
        self.record_type_mapping_cache[cache_key] = mapping
        return mapping
    
    def get_target_fields(self, org_target: str, object_name: str) -> Set[str]:
        """Get set of available field names in target org.
        
        Args:
            org_target: Target org identifier
            object_name: Object name (Account, Contact)
            
        Returns:
            Set of field names available in target org
        """
        # Try to get from database cache first
        cached_fields = self.db_manager.get_field_metadata(object_name, org_target)
        if cached_fields:
            return set(cached_fields)
        
        # If not cached, get from Salesforce and cache it
        fields = self.sf_client.get_object_fields(org_target, object_name)
        if fields:
            # Cache the fields
            describe = self.sf_client.describe_object(org_target, object_name)
            if describe:
                self.db_manager.insert_field_metadata(object_name, describe.get('fields', []), org_target)
            return set(fields)
        
        return set()
    
    def filter_fields_for_migration(self, record: Dict[str, Any], 
                                   source_fields: Set[str], 
                                   target_fields: Set[str]) -> Dict[str, Any]:
        """Filter record to only include fields that exist in target org.
        
        Args:
            record: Record dictionary
            source_fields: Set of fields available in source org
            target_fields: Set of fields available in target org
            
        Returns:
            Filtered record dictionary
        """
        filtered = {}
        skipped_fields = []
        
        for key, value in record.items():
            # Skip internal fields
            if key in {'id', 'salesforce_id', 'record_type_id', 'record_type_name', 
                      'org_source', 'created_at', 'updated_at', 'account_data', 
                      'contact_data', 'Id', 'RecordType', 'attributes'}:
                continue
            
            # Check if field exists in target
            if key in target_fields:
                filtered[key] = value
            else:
                skipped_fields.append(key)
        
        if skipped_fields:
            # Log skipped fields (could be added to migration log)
            pass
        
        return filtered
    
    def prepare_account_for_migration(self, account: Dict[str, Any], 
                                     record_type_mapping: Dict[str, str],
                                     target_fields: Set[str]) -> Dict[str, Any]:
        """Prepare an account record for migration.
        
        Args:
            account: Account dictionary from database
            record_type_mapping: Record type ID mapping
            
        Returns:
            Prepared account dictionary for Salesforce
        """
        # Parse account_data if it's a JSON string
        if isinstance(account.get('account_data'), str):
            account_data = json.loads(account['account_data'])
            account.update(account_data)
        
        # Create new record dict excluding internal fields
        record = {}
        
        # Map record type
        source_record_type_id = account.get('record_type_id') or account.get('RecordTypeId')
        if source_record_type_id and source_record_type_id in record_type_mapping:
            target_record_type_id = record_type_mapping[source_record_type_id]
            if target_record_type_id:
                record['RecordTypeId'] = target_record_type_id
        
        # Filter fields to only include those that exist in target org
        filtered_record = self.filter_fields_for_migration(account, set(account.keys()), target_fields)
        
        # Copy filtered fields
        for key, value in filtered_record.items():
            if value is not None:
                record[key] = value
        
        return record
    
    def prepare_contact_for_migration(self, contact: Dict[str, Any], 
                                      record_type_mapping: Dict[str, str],
                                      account_id_mapping: Dict[str, str],
                                      target_fields: Set[str]) -> Dict[str, Any]:
        """Prepare a contact record for migration.
        
        Args:
            contact: Contact dictionary from database
            record_type_mapping: Record type ID mapping
            account_id_mapping: Mapping of source account IDs to target account IDs
            
        Returns:
            Prepared contact dictionary for Salesforce
        """
        # Parse contact_data if it's a JSON string
        if isinstance(contact.get('contact_data'), str):
            contact_data = json.loads(contact['contact_data'])
            contact.update(contact_data)
        
        # Create new record dict excluding internal fields
        record = {}
        
        # Map record type
        source_record_type_id = contact.get('record_type_id') or contact.get('RecordTypeId')
        if source_record_type_id and source_record_type_id in record_type_mapping:
            target_record_type_id = record_type_mapping[source_record_type_id]
            if target_record_type_id:
                record['RecordTypeId'] = target_record_type_id
        
        # Map account ID
        source_account_id = contact.get('account_id') or contact.get('AccountId')
        if source_account_id and source_account_id in account_id_mapping:
            record['AccountId'] = account_id_mapping[source_account_id]
        
        # Filter fields to only include those that exist in target org
        filtered_record = self.filter_fields_for_migration(contact, set(contact.keys()), target_fields)
        
        # Copy filtered fields
        for key, value in filtered_record.items():
            if value is not None:
                record[key] = value
        
        return record
    
    def migrate_accounts(self, org_source: str, org_target: str, 
                        batch_size: int = 200) -> Dict[str, Any]:
        """Migrate accounts from source org to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            batch_size: Number of records per batch
            
        Returns:
            Dictionary with migration results
        """
        print(f"\nMigrating accounts from {org_source} to {org_target}...")
        
        # Get record type mapping
        record_type_mapping = self.map_record_types(org_source, org_target, 'Account')
        
        # Get target fields for validation
        target_fields = self.get_target_fields(org_target, 'Account')
        
        # Get accounts from source org
        accounts = self.db_manager.get_accounts(org_source)
        
        if not accounts:
            print("No accounts to migrate")
            return {'success': 0, 'failed': 0, 'errors': []}
        
        print(f"Migrating {len(accounts)} accounts...")
        
        # Prepare accounts for migration
        prepared_accounts = []
        for account in accounts:
            prepared = self.prepare_account_for_migration(account, record_type_mapping, target_fields)
            prepared_accounts.append(prepared)
        
        # Migrate in batches
        success_count = 0
        failed_count = 0
        errors = []
        account_id_mapping = {}  # Map source ID to target ID
        
        for i in range(0, len(prepared_accounts), batch_size):
            batch = prepared_accounts[i:i + batch_size]
            batch_source_ids = [accounts[j]['salesforce_id'] for j in range(i, min(i + batch_size, len(accounts)))]
            
            try:
                results = self.sf_client.bulk_create(org_target, 'Account', batch)
                
                for idx, result in enumerate(results):
                    source_id = batch_source_ids[idx]
                    if result.get('success'):
                        target_id = result.get('id')
                        account_id_mapping[source_id] = target_id
                        success_count += 1
                        self.db_manager.log_migration(
                            'Account', source_id, target_id, org_source, org_target,
                            'SUCCESS'
                        )
                    else:
                        failed_count += 1
                        error_msg = '; '.join(result.get('errors', []))
                        errors.append(f"Account {source_id}: {error_msg}")
                        self.db_manager.log_migration(
                            'Account', source_id, None, org_source, org_target,
                            'FAILED', error_msg
                        )
            except Exception as e:
                failed_count += len(batch)
                error_msg = str(e)
                errors.append(f"Batch error: {error_msg}")
                for source_id in batch_source_ids:
                    self.db_manager.log_migration(
                        'Account', source_id, None, org_source, org_target,
                        'FAILED', error_msg
                    )
        
        print(f"Accounts migration complete: {success_count} succeeded, {failed_count} failed")
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors,
            'account_id_mapping': account_id_mapping
        }
    
    def migrate_contacts(self, org_source: str, org_target: str,
                        account_id_mapping: Dict[str, str],
                        batch_size: int = 200) -> Dict[str, Any]:
        """Migrate contacts from source org to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            account_id_mapping: Mapping of source account IDs to target account IDs
            batch_size: Number of records per batch
            
        Returns:
            Dictionary with migration results
        """
        print(f"\nMigrating contacts from {org_source} to {org_target}...")
        
        # Get record type mapping
        record_type_mapping = self.map_record_types(org_source, org_target, 'Contact')
        
        # Get target fields for validation
        target_fields = self.get_target_fields(org_target, 'Contact')
        
        # Get contacts from source org
        contacts = self.db_manager.get_contacts(org_source)
        
        if not contacts:
            print("No contacts to migrate")
            return {'success': 0, 'failed': 0, 'errors': []}
        
        print(f"Migrating {len(contacts)} contacts...")
        
        # Prepare contacts for migration
        prepared_contacts = []
        for contact in contacts:
            prepared = self.prepare_contact_for_migration(
                contact, record_type_mapping, account_id_mapping, target_fields
            )
            prepared_contacts.append(prepared)
        
        # Migrate in batches
        success_count = 0
        failed_count = 0
        errors = []
        contact_id_mapping = {}  # Map source ID to target ID
        
        for i in range(0, len(prepared_contacts), batch_size):
            batch = prepared_contacts[i:i + batch_size]
            batch_source_ids = [contacts[j]['salesforce_id'] for j in range(i, min(i + batch_size, len(contacts)))]
            
            try:
                results = self.sf_client.bulk_create(org_target, 'Contact', batch)
                
                for idx, result in enumerate(results):
                    source_id = batch_source_ids[idx]
                    if result.get('success'):
                        target_id = result.get('id')
                        contact_id_mapping[source_id] = target_id
                        success_count += 1
                        self.db_manager.log_migration(
                            'Contact', source_id, target_id, org_source, org_target,
                            'SUCCESS'
                        )
                    else:
                        failed_count += 1
                        error_msg = '; '.join(result.get('errors', []))
                        errors.append(f"Contact {source_id}: {error_msg}")
                        self.db_manager.log_migration(
                            'Contact', source_id, None, org_source, org_target,
                            'FAILED', error_msg
                        )
            except Exception as e:
                failed_count += len(batch)
                error_msg = str(e)
                errors.append(f"Batch error: {error_msg}")
                for source_id in batch_source_ids:
                    self.db_manager.log_migration(
                        'Contact', source_id, None, org_source, org_target,
                        'FAILED', error_msg
                    )
        
        print(f"Contacts migration complete: {success_count} succeeded, {failed_count} failed")
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors,
            'contact_id_mapping': contact_id_mapping
        }
    
    def migrate_all(self, org_source: str, org_target: str) -> Dict[str, Any]:
        """Migrate all data (accounts then contacts) from source to target.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            
        Returns:
            Dictionary with overall migration results
        """
        print(f"\n{'='*60}")
        print(f"Starting migration from {org_source} to {org_target}")
        print(f"{'='*60}\n")
        
        # Migrate accounts first
        account_results = self.migrate_accounts(org_source, org_target)
        account_id_mapping = account_results.get('account_id_mapping', {})
        
        # Migrate contacts (with account ID mapping)
        contact_results = self.migrate_contacts(org_source, org_target, account_id_mapping)
        
        # Migrate files after records are migrated
        file_results = self.migrate_files(org_source, org_target, account_id_mapping, contact_results.get('contact_id_mapping', {}))
        
        return {
            'accounts': account_results,
            'contacts': contact_results,
            'files': file_results,
            'total_success': account_results['success'] + contact_results['success'],
            'total_failed': account_results['failed'] + contact_results['failed']
        }
    
    def migrate_attachments(self, org_source: str, org_target: str,
                          account_id_mapping: Dict[str, str],
                          contact_id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Migrate attachments to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            account_id_mapping: Mapping of source to target account IDs
            contact_id_mapping: Mapping of source to target contact IDs
            
        Returns:
            Dictionary with migration results
        """
        print(f"\nMigrating attachments from {org_source} to {org_target}...")
        
        # Get all attachments from source org
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM attachments WHERE org_source = ?
        """, (org_source,))
        all_attachments = [dict(row) for row in cursor.fetchall()]
        
        if not all_attachments:
            print("No attachments to migrate")
            return {'success': 0, 'failed': 0, 'errors': []}
        
        print(f"Migrating {len(all_attachments)} attachments...")
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for attachment in all_attachments:
            parent_id = attachment.get('parent_id')
            parent_type = attachment.get('parent_type')
            file_path = attachment.get('file_path')
            
            # Map parent ID
            if parent_type == 'Account':
                target_parent_id = account_id_mapping.get(parent_id)
            elif parent_type == 'Contact':
                target_parent_id = contact_id_mapping.get(parent_id)
            else:
                target_parent_id = None
            
            if not target_parent_id:
                failed_count += 1
                errors.append(f"Attachment {attachment.get('salesforce_id')}: Parent not migrated")
                continue
            
            # Read file
            try:
                binary_data = read_binary_file(Path(file_path))
                body_base64 = encode_base64(binary_data)
                
                # Create attachment record
                attachment_data = {
                    'ParentId': target_parent_id,
                    'Name': attachment.get('name'),
                    'ContentType': attachment.get('content_type'),
                    'Body': body_base64
                }
                
                result_id = self.sf_client.create_record(org_target, 'Attachment', attachment_data)
                
                if result_id:
                    success_count += 1
                    self.db_manager.log_migration(
                        'Attachment', attachment.get('salesforce_id'), result_id,
                        org_source, org_target, 'SUCCESS'
                    )
                else:
                    failed_count += 1
                    errors.append(f"Attachment {attachment.get('salesforce_id')}: Creation failed")
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                errors.append(f"Attachment {attachment.get('salesforce_id')}: {error_msg}")
                self.db_manager.log_migration(
                    'Attachment', attachment.get('salesforce_id'), None,
                    org_source, org_target, 'FAILED', error_msg
                )
        
        print(f"Attachments migration complete: {success_count} succeeded, {failed_count} failed")
        return {'success': success_count, 'failed': failed_count, 'errors': errors}
    
    def migrate_notes(self, org_source: str, org_target: str,
                     account_id_mapping: Dict[str, str],
                     contact_id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Migrate notes to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            account_id_mapping: Mapping of source to target account IDs
            contact_id_mapping: Mapping of source to target contact IDs
            
        Returns:
            Dictionary with migration results
        """
        print(f"\nMigrating notes from {org_source} to {org_target}...")
        
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notes WHERE org_source = ?
        """, (org_source,))
        all_notes = [dict(row) for row in cursor.fetchall()]
        
        if not all_notes:
            print("No notes to migrate")
            return {'success': 0, 'failed': 0, 'errors': []}
        
        print(f"Migrating {len(all_notes)} notes...")
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for note in all_notes:
            parent_id = note.get('parent_id')
            parent_type = note.get('parent_type')
            file_path = note.get('file_path')
            
            # Map parent ID
            if parent_type == 'Account':
                target_parent_id = account_id_mapping.get(parent_id)
            elif parent_type == 'Contact':
                target_parent_id = contact_id_mapping.get(parent_id)
            else:
                target_parent_id = None
            
            if not target_parent_id:
                failed_count += 1
                errors.append(f"Note {note.get('salesforce_id')}: Parent not migrated")
                continue
            
            # Read note body
            try:
                body_data = read_binary_file(Path(file_path))
                body_text = body_data.decode('utf-8')
                
                # Create note record
                note_data = {
                    'ParentId': target_parent_id,
                    'Title': note.get('title'),
                    'Body': body_text
                }
                
                result_id = self.sf_client.create_record(org_target, 'Note', note_data)
                
                if result_id:
                    success_count += 1
                    self.db_manager.log_migration(
                        'Note', note.get('salesforce_id'), result_id,
                        org_source, org_target, 'SUCCESS'
                    )
                else:
                    failed_count += 1
                    errors.append(f"Note {note.get('salesforce_id')}: Creation failed")
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                errors.append(f"Note {note.get('salesforce_id')}: {error_msg}")
                self.db_manager.log_migration(
                    'Note', note.get('salesforce_id'), None,
                    org_source, org_target, 'FAILED', error_msg
                )
        
        print(f"Notes migration complete: {success_count} succeeded, {failed_count} failed")
        return {'success': success_count, 'failed': failed_count, 'errors': errors}
    
    def migrate_content_documents(self, org_source: str, org_target: str,
                                 account_id_mapping: Dict[str, str],
                                 contact_id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Migrate content documents (Files) to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            account_id_mapping: Mapping of source to target account IDs
            contact_id_mapping: Mapping of source to target contact IDs
            
        Returns:
            Dictionary with migration results
        """
        print(f"\nMigrating files from {org_source} to {org_target}...")
        
        conn = self.db_manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM content_document_links WHERE org_source = ?
        """, (org_source,))
        all_links = [dict(row) for row in cursor.fetchall()]
        
        if not all_links:
            print("No files to migrate")
            return {'success': 0, 'failed': 0, 'errors': []}
        
        print(f"Migrating {len(all_links)} file links...")
        
        success_count = 0
        failed_count = 0
        errors = []
        content_doc_mapping = {}  # Map source content document ID to target
        
        # Group links by content document
        links_by_doc = {}
        for link in all_links:
            doc_id = link.get('content_document_id')
            if doc_id not in links_by_doc:
                links_by_doc[doc_id] = []
            links_by_doc[doc_id].append(link)
        
        # Migrate each content document
        for doc_id, links in links_by_doc.items():
            # Get content version
            version = self.db_manager.get_content_version(doc_id, org_source)
            if not version:
                failed_count += len(links)
                errors.append(f"Content document {doc_id}: Version not found")
                continue
            
            file_path = version.get('file_path')
            if not file_path:
                failed_count += len(links)
                errors.append(f"Content document {doc_id}: File path not found")
                continue
            
            try:
                # Read file
                binary_data = read_binary_file(Path(file_path))
                version_data_base64 = encode_base64(binary_data)
                
                # Get document metadata
                conn = self.db_manager._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM content_documents WHERE salesforce_id = ? AND org_source = ?
                """, (doc_id, org_source))
                doc_row = cursor.fetchone()
                doc_meta = dict(doc_row) if doc_row else {}
                
                # Create ContentVersion (which auto-creates ContentDocument)
                version_data = {
                    'Title': doc_meta.get('title', 'Migrated File'),
                    'PathOnClient': f"{doc_meta.get('title', 'file')}.{doc_meta.get('file_extension', '')}",
                    'VersionData': version_data_base64
                }
                
                version_id = self.sf_client.create_record(org_target, 'ContentVersion', version_data)
                
                if not version_id:
                    failed_count += len(links)
                    errors.append(f"Content document {doc_id}: Version creation failed")
                    continue
                
                # Get the ContentDocumentId from the created version
                soql = f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{version_id}'"
                version_records = self.sf_client.query(org_target, soql)
                target_doc_id = None
                if version_records:
                    target_doc_id = version_records[0].get('ContentDocumentId')
                    
                    if target_doc_id:
                        content_doc_mapping[doc_id] = target_doc_id
                        
                        # Create ContentDocumentLinks for all linked entities
                        for link in links:
                            linked_entity_id = link.get('linked_entity_id')
                            linked_entity_type = link.get('linked_entity_type')
                            
                            # Map entity ID
                            if linked_entity_type == 'Account':
                                target_entity_id = account_id_mapping.get(linked_entity_id)
                            elif linked_entity_type == 'Contact':
                                target_entity_id = contact_id_mapping.get(linked_entity_id)
                            else:
                                target_entity_id = None
                            
                            if target_entity_id:
                                link_data = {
                                    'ContentDocumentId': target_doc_id,
                                    'LinkedEntityId': target_entity_id,
                                    'ShareType': 'V'  # Viewer
                                }
                                
                                link_id = self.sf_client.create_record(org_target, 'ContentDocumentLink', link_data)
                                if link_id:
                                    success_count += 1
                                else:
                                    failed_count += 1
                                    errors.append(f"ContentDocumentLink for {linked_entity_id}: Creation failed")
                            else:
                                failed_count += 1
                                errors.append(f"ContentDocumentLink for {linked_entity_id}: Entity not migrated")
                    else:
                        failed_count += len(links)
                        errors.append(f"Content document {doc_id}: ContentDocumentId not found")
            except Exception as e:
                failed_count += len(links)
                error_msg = str(e)
                errors.append(f"Content document {doc_id}: {error_msg}")
        
        print(f"Files migration complete: {success_count} succeeded, {failed_count} failed")
        return {'success': success_count, 'failed': failed_count, 'errors': errors}
    
    def migrate_files(self, org_source: str, org_target: str,
                     account_id_mapping: Dict[str, str],
                     contact_id_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Migrate all files (attachments, notes, content documents) to target org.
        
        Args:
            org_source: Source org identifier
            org_target: Target org identifier
            account_id_mapping: Mapping of source to target account IDs
            contact_id_mapping: Mapping of source to target contact IDs
            
        Returns:
            Dictionary with overall file migration results
        """
        attachments_result = self.migrate_attachments(org_source, org_target, account_id_mapping, contact_id_mapping)
        notes_result = self.migrate_notes(org_source, org_target, account_id_mapping, contact_id_mapping)
        files_result = self.migrate_content_documents(org_source, org_target, account_id_mapping, contact_id_mapping)
        
        return {
            'attachments': attachments_result,
            'notes': notes_result,
            'files': files_result,
            'total_success': attachments_result['success'] + notes_result['success'] + files_result['success'],
            'total_failed': attachments_result['failed'] + notes_result['failed'] + files_result['failed']
        }
