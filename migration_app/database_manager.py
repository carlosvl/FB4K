"""
Database manager for SQLite operations
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class DatabaseManager:
    """Manages SQLite database operations for data migration staging."""
    
    def __init__(self, db_path: str = None):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/migration.db
        """
        if db_path is None:
            # Default to data/migration.db relative to project root
            project_root = Path(__file__).parent.parent
            db_path = project_root / "data" / "migration.db"
        
        self.db_path = str(db_path)
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create record_types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS record_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_type TEXT NOT NULL,
                record_type_id TEXT NOT NULL,
                record_type_name TEXT NOT NULL,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(object_type, record_type_id, org_source)
            )
        """)
        
        # Create accounts table with core fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                name TEXT,
                record_type_id TEXT,
                record_type_name TEXT,
                org_source TEXT NOT NULL,
                created_date TEXT,
                last_modified_date TEXT,
                account_data TEXT,  -- JSON blob for all other fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create contacts table with core fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                account_id TEXT,  -- References accounts.salesforce_id
                name TEXT,
                record_type_id TEXT,
                record_type_name TEXT,
                org_source TEXT NOT NULL,
                created_date TEXT,
                last_modified_date TEXT,
                contact_data TEXT,  -- JSON blob for all other fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(salesforce_id)
            )
        """)
        
        # Create relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_object TEXT NOT NULL,
                parent_id TEXT NOT NULL,
                child_object TEXT NOT NULL,
                child_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES accounts(salesforce_id),
                FOREIGN KEY (child_id) REFERENCES contacts(salesforce_id)
            )
        """)
        
        # Create migration_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_type TEXT NOT NULL,
                salesforce_id_source TEXT,
                salesforce_id_target TEXT,
                org_source TEXT NOT NULL,
                org_target TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create attachments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                parent_id TEXT NOT NULL,
                parent_type TEXT NOT NULL,
                name TEXT,
                content_type TEXT,
                file_size INTEGER,
                file_path TEXT,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                parent_id TEXT NOT NULL,
                parent_type TEXT NOT NULL,
                title TEXT,
                body TEXT,
                file_path TEXT,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create content_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                title TEXT,
                file_extension TEXT,
                content_size INTEGER,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create content_versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesforce_id TEXT NOT NULL UNIQUE,
                content_document_id TEXT NOT NULL,
                version_number INTEGER,
                file_path TEXT,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create content_document_links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_document_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_document_id TEXT NOT NULL,
                linked_entity_id TEXT NOT NULL,
                linked_entity_type TEXT NOT NULL,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create field_metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_type TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_type TEXT,
                org_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(object_type, field_name, org_source)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accounts_salesforce_id 
            ON accounts(salesforce_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accounts_org_source 
            ON accounts(org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contacts_salesforce_id 
            ON contacts(salesforce_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contacts_account_id 
            ON contacts(account_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contacts_org_source 
            ON contacts(org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_record_types_lookup 
            ON record_types(object_type, record_type_id, org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attachments_parent 
            ON attachments(parent_id, parent_type, org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_parent 
            ON notes(parent_id, parent_type, org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_document_links 
            ON content_document_links(linked_entity_id, linked_entity_type, org_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_field_metadata_lookup 
            ON field_metadata(object_type, field_name, org_source)
        """)
        
        conn.commit()
    
    def insert_record_types(self, object_type: str, record_types: List[Dict[str, Any]], org_source: str):
        """Insert record types into the database.
        
        Args:
            object_type: Object type (Account or Contact)
            record_types: List of record type dictionaries with Id and Name
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for rt in record_types:
            cursor.execute("""
                INSERT OR REPLACE INTO record_types 
                (object_type, record_type_id, record_type_name, org_source)
                VALUES (?, ?, ?, ?)
            """, (object_type, rt.get('Id'), rt.get('Name'), org_source))
        
        conn.commit()
    
    def get_record_types(self, object_type: str, org_source: str) -> List[Dict[str, Any]]:
        """Get record types for an object from a specific org.
        
        Args:
            object_type: Object type (Account or Contact)
            org_source: Source org identifier
            
        Returns:
            List of record type dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT record_type_id, record_type_name 
            FROM record_types 
            WHERE object_type = ? AND org_source = ?
        """, (object_type, org_source))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def insert_accounts(self, accounts: List[Dict[str, Any]], org_source: str):
        """Insert accounts into the database.
        
        Args:
            accounts: List of account dictionaries from Salesforce
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for account in accounts:
            salesforce_id = account.get('Id')
            name = account.get('Name')
            record_type_id = account.get('RecordTypeId')
            record_type_name = account.get('RecordType', {}).get('Name') if isinstance(
                account.get('RecordType'), dict) else None
            
            # Store all fields as JSON in account_data
            account_data = json.dumps(account)
            
            cursor.execute("""
                INSERT OR REPLACE INTO accounts 
                (salesforce_id, name, record_type_id, record_type_name, org_source,
                 created_date, last_modified_date, account_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                salesforce_id,
                name,
                record_type_id,
                record_type_name,
                org_source,
                account.get('CreatedDate'),
                account.get('LastModifiedDate'),
                account_data
            ))
        
        conn.commit()
    
    def insert_contacts(self, contacts: List[Dict[str, Any]], org_source: str):
        """Insert contacts into the database.
        
        Args:
            contacts: List of contact dictionaries from Salesforce
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for contact in contacts:
            salesforce_id = contact.get('Id')
            name = contact.get('Name')
            account_id = contact.get('AccountId')
            record_type_id = contact.get('RecordTypeId')
            record_type_name = contact.get('RecordType', {}).get('Name') if isinstance(
                contact.get('RecordType'), dict) else None
            
            # Store all fields as JSON in contact_data
            contact_data = json.dumps(contact)
            
            cursor.execute("""
                INSERT OR REPLACE INTO contacts 
                (salesforce_id, account_id, name, record_type_id, record_type_name, org_source,
                 created_date, last_modified_date, contact_data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                salesforce_id,
                account_id,
                name,
                record_type_id,
                record_type_name,
                org_source,
                contact.get('CreatedDate'),
                contact.get('LastModifiedDate'),
                contact_data
            ))
            
            # Store relationship if account_id exists
            if account_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO relationships 
                    (parent_object, parent_id, child_object, child_id, relationship_type, org_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('Account', account_id, 'Contact', salesforce_id, 'AccountId', org_source))
        
        conn.commit()
    
    def get_accounts(self, org_source: str = None) -> List[Dict[str, Any]]:
        """Get accounts from the database.
        
        Args:
            org_source: Optional org filter
            
        Returns:
            List of account dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if org_source:
            cursor.execute("""
                SELECT * FROM accounts WHERE org_source = ?
            """, (org_source,))
        else:
            cursor.execute("SELECT * FROM accounts")
        
        rows = cursor.fetchall()
        accounts = []
        for row in rows:
            account = dict(row)
            # Parse JSON data if present
            if account.get('account_data'):
                account_data = json.loads(account['account_data'])
                account.update(account_data)
            accounts.append(account)
        
        return accounts
    
    def get_contacts(self, org_source: str = None) -> List[Dict[str, Any]]:
        """Get contacts from the database.
        
        Args:
            org_source: Optional org filter
            
        Returns:
            List of contact dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if org_source:
            cursor.execute("""
                SELECT * FROM contacts WHERE org_source = ?
            """, (org_source,))
        else:
            cursor.execute("SELECT * FROM contacts")
        
        rows = cursor.fetchall()
        contacts = []
        for row in rows:
            contact = dict(row)
            # Parse JSON data if present
            if contact.get('contact_data'):
                contact_data = json.loads(contact['contact_data'])
                contact.update(contact_data)
            contacts.append(contact)
        
        return contacts
    
    def account_exists(self, salesforce_id: str) -> bool:
        """Check if an account exists in the database.
        
        Args:
            salesforce_id: Salesforce ID to check
            
        Returns:
            True if account exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM accounts WHERE salesforce_id = ?
        """, (salesforce_id,))
        
        return cursor.fetchone()[0] > 0
    
    def validate_relationships(self) -> Dict[str, Any]:
        """Validate all relationships in the database.
        
        Returns:
            Dictionary with validation results
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Find orphaned contacts (contacts with account_id that doesn't exist)
        cursor.execute("""
            SELECT c.salesforce_id, c.account_id, c.name
            FROM contacts c
            LEFT JOIN accounts a ON c.account_id = a.salesforce_id
            WHERE c.account_id IS NOT NULL AND a.salesforce_id IS NULL
        """)
        
        orphaned_contacts = [dict(row) for row in cursor.fetchall()]
        
        # Count relationships
        cursor.execute("SELECT COUNT(*) FROM relationships")
        relationship_count = cursor.fetchone()[0]
        
        # Count accounts and contacts
        cursor.execute("SELECT COUNT(*) FROM accounts")
        account_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        
        return {
            'orphaned_contacts': orphaned_contacts,
            'orphaned_count': len(orphaned_contacts),
            'relationship_count': relationship_count,
            'account_count': account_count,
            'contact_count': contact_count,
            'is_valid': len(orphaned_contacts) == 0
        }
    
    def get_orphaned_records(self) -> List[Dict[str, Any]]:
        """Get orphaned contacts (contacts without valid account references).
        
        Returns:
            List of orphaned contact records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.salesforce_id, c.account_id, c.name, c.org_source
            FROM contacts c
            LEFT JOIN accounts a ON c.account_id = a.salesforce_id
            WHERE c.account_id IS NOT NULL AND a.salesforce_id IS NULL
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def log_migration(self, object_type: str, salesforce_id_source: str,
                     salesforce_id_target: str, org_source: str, org_target: str,
                     status: str, error_message: str = None):
        """Log a migration operation.
        
        Args:
            object_type: Type of object (Account or Contact)
            salesforce_id_source: Source Salesforce ID
            salesforce_id_target: Target Salesforce ID (if successful)
            org_source: Source org identifier
            org_target: Target org identifier
            status: Status (SUCCESS, FAILED, etc.)
            error_message: Error message if failed
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO migration_log 
            (object_type, salesforce_id_source, salesforce_id_target, 
             org_source, org_target, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (object_type, salesforce_id_source, salesforce_id_target,
              org_source, org_target, status, error_message))
        
        conn.commit()
    
    def get_migration_status(self, org_source: str = None, org_target: str = None) -> List[Dict[str, Any]]:
        """Get migration log entries.
        
        Args:
            org_source: Optional source org filter
            org_target: Optional target org filter
            
        Returns:
            List of migration log entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM migration_log WHERE 1=1"
        params = []
        
        if org_source:
            query += " AND org_source = ?"
            params.append(org_source)
        
        if org_target:
            query += " AND org_target = ?"
            params.append(org_target)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_record_counts_by_org(self) -> Dict[str, Dict[str, int]]:
        """Get record counts grouped by org.
        
        Returns:
            Dictionary mapping org_source to counts
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT org_source, COUNT(*) as count
            FROM accounts
            GROUP BY org_source
        """)
        account_counts = {row['org_source']: row['count'] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT org_source, COUNT(*) as count
            FROM contacts
            GROUP BY org_source
        """)
        contact_counts = {row['org_source']: row['count'] for row in cursor.fetchall()}
        
        result = {}
        all_orgs = set(account_counts.keys()) | set(contact_counts.keys())
        
        for org in all_orgs:
            result[org] = {
                'accounts': account_counts.get(org, 0),
                'contacts': contact_counts.get(org, 0)
            }
        
        return result
    
    def insert_attachments(self, attachments: List[Dict[str, Any]], org_source: str):
        """Insert attachments into the database.
        
        Args:
            attachments: List of attachment dictionaries
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for attachment in attachments:
            cursor.execute("""
                INSERT OR REPLACE INTO attachments 
                (salesforce_id, parent_id, parent_type, name, content_type, file_size, file_path, org_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attachment.get('Id'),
                attachment.get('ParentId'),
                attachment.get('parent_type'),
                attachment.get('Name'),
                attachment.get('ContentType'),
                attachment.get('BodyLength'),
                attachment.get('file_path'),
                org_source
            ))
        
        conn.commit()
    
    def insert_notes(self, notes: List[Dict[str, Any]], org_source: str):
        """Insert notes into the database.
        
        Args:
            notes: List of note dictionaries
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for note in notes:
            cursor.execute("""
                INSERT OR REPLACE INTO notes 
                (salesforce_id, parent_id, parent_type, title, body, file_path, org_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                note.get('Id'),
                note.get('ParentId'),
                note.get('parent_type'),
                note.get('Title'),
                note.get('Body'),
                note.get('file_path'),
                org_source
            ))
        
        conn.commit()
    
    def insert_content_documents(self, documents: List[Dict[str, Any]], org_source: str):
        """Insert content documents into the database.
        
        Args:
            documents: List of content document dictionaries
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for doc in documents:
            cursor.execute("""
                INSERT OR REPLACE INTO content_documents 
                (salesforce_id, title, file_extension, content_size, org_source)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc.get('Id'),
                doc.get('Title'),
                doc.get('FileExtension'),
                doc.get('ContentSize'),
                org_source
            ))
        
        conn.commit()
    
    def insert_content_versions(self, versions: List[Dict[str, Any]], org_source: str):
        """Insert content versions into the database.
        
        Args:
            versions: List of content version dictionaries
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for version in versions:
            cursor.execute("""
                INSERT OR REPLACE INTO content_versions 
                (salesforce_id, content_document_id, version_number, file_path, org_source)
                VALUES (?, ?, ?, ?, ?)
            """, (
                version.get('Id'),
                version.get('ContentDocumentId'),
                version.get('VersionNumber'),
                version.get('file_path'),
                org_source
            ))
        
        conn.commit()
    
    def insert_content_document_links(self, links: List[Dict[str, Any]], org_source: str):
        """Insert content document links into the database.
        
        Args:
            links: List of content document link dictionaries
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for link in links:
            cursor.execute("""
                INSERT OR IGNORE INTO content_document_links 
                (content_document_id, linked_entity_id, linked_entity_type, org_source)
                VALUES (?, ?, ?, ?)
            """, (
                link.get('ContentDocumentId'),
                link.get('LinkedEntityId'),
                link.get('linked_entity_type'),
                org_source
            ))
        
        conn.commit()
    
    def insert_field_metadata(self, object_type: str, fields: List[Dict[str, Any]], org_source: str):
        """Insert field metadata into the database.
        
        Args:
            object_type: Object type (Account, Contact, etc.)
            fields: List of field dictionaries from describe
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for field in fields:
            # Only store queryable fields
            if field.get('queryable', False) and field.get('accessable', False):
                cursor.execute("""
                    INSERT OR REPLACE INTO field_metadata 
                    (object_type, field_name, field_type, org_source)
                    VALUES (?, ?, ?, ?)
                """, (
                    object_type,
                    field.get('name'),
                    field.get('type'),
                    org_source
                ))
        
        conn.commit()
    
    def get_field_metadata(self, object_type: str, org_source: str) -> List[str]:
        """Get list of available field names for an object in an org.
        
        Args:
            object_type: Object type (Account, Contact, etc.)
            org_source: Source org identifier
            
        Returns:
            List of field names
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT field_name FROM field_metadata 
            WHERE object_type = ? AND org_source = ?
        """, (object_type, org_source))
        
        return [row['field_name'] for row in cursor.fetchall()]
    
    def get_attachments_for_parent(self, parent_id: str, parent_type: str, org_source: str) -> List[Dict[str, Any]]:
        """Get attachments for a parent record.
        
        Args:
            parent_id: Parent record ID
            parent_type: Parent object type
            org_source: Source org identifier
            
        Returns:
            List of attachment records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM attachments 
            WHERE parent_id = ? AND parent_type = ? AND org_source = ?
        """, (parent_id, parent_type, org_source))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_notes_for_parent(self, parent_id: str, parent_type: str, org_source: str) -> List[Dict[str, Any]]:
        """Get notes for a parent record.
        
        Args:
            parent_id: Parent record ID
            parent_type: Parent object type
            org_source: Source org identifier
            
        Returns:
            List of note records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM notes 
            WHERE parent_id = ? AND parent_type = ? AND org_source = ?
        """, (parent_id, parent_type, org_source))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_content_document_links_for_parent(self, parent_id: str, parent_type: str, org_source: str) -> List[Dict[str, Any]]:
        """Get content document links for a parent record.
        
        Args:
            parent_id: Parent record ID
            parent_type: Parent object type
            org_source: Source org identifier
            
        Returns:
            List of content document link records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM content_document_links 
            WHERE linked_entity_id = ? AND linked_entity_type = ? AND org_source = ?
        """, (parent_id, parent_type, org_source))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_content_version(self, content_document_id: str, org_source: str) -> Optional[Dict[str, Any]]:
        """Get content version for a content document.
        
        Args:
            content_document_id: Content document ID
            org_source: Source org identifier
            
        Returns:
            Content version record or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM content_versions 
            WHERE content_document_id = ? AND org_source = ?
            ORDER BY version_number DESC LIMIT 1
        """, (content_document_id, org_source))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def org_has_data(self, org_source: str) -> bool:
        """Check if an org has any data in the database.
        
        Args:
            org_source: Source org identifier
            
        Returns:
            True if org has any accounts or contacts
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM accounts WHERE org_source = ?
        """, (org_source,))
        account_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM contacts WHERE org_source = ?
        """, (org_source,))
        contact_count = cursor.fetchone()[0]
        
        return account_count > 0 or contact_count > 0
    
    def flush_org_data(self, org_source: str):
        """Delete all data for a specific org.
        
        Args:
            org_source: Source org identifier
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete in order to respect foreign keys
        cursor.execute("DELETE FROM content_document_links WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM content_versions WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM content_documents WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM attachments WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM notes WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM relationships WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM contacts WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM accounts WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM record_types WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM field_metadata WHERE org_source = ?", (org_source,))
        cursor.execute("DELETE FROM migration_log WHERE org_source = ?", (org_source,))
        
        conn.commit()
        print(f"Flushed all data for org: {org_source}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
