# FB4K main repository

Repo to hold configuration of Volunteer management for FB4K Salesforce org in Minnesota

## Salesforce Data Migration Application

This repository includes a Python application for migrating data between Salesforce orgs using SQLite as a staging database.

### Features

- **Complete Data Extraction**: Dynamically queries and extracts ALL accessible fields from Account and Contact objects
- **File Backup**: Automatically backs up Attachments, Notes, and Files (ContentDocument/ContentVersion) as binary files
- **Local Storage**: Stores data in SQLite database and files in hierarchical directory structure
- **Relationship Preservation**: Preserves all relationships between objects and files
- **Record Type Tracking**: Tracks record types for Accounts and Contacts with automatic mapping
- **Field Validation**: Automatically filters out fields that don't exist in target org during migration
- **Smart Migration**: Migrates accounts first, then contacts, then files with proper ID mapping
- **Interactive Menu**: User-friendly menu-driven interface
- **Relationship Validation**: Check relationship integrity and find orphaned records
- **Org Comparison**: Compare record counts and record types between orgs

### Prerequisites

- Python 3.7+
- Salesforce CLI (SFDX) installed and configured
- Authenticated Salesforce orgs (use `sf org login web`)

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have authenticated Salesforce orgs:
```bash
sf org list
```

### Usage

Run the migration application:

```bash
python -m migration_app
```

Or:

```bash
python -m migration_app.main
```

### Menu Options

1. **Backup Accounts from Org** - Extract all accounts with all fields, record types, and associated files (attachments, notes, files) from a selected Salesforce org
2. **Backup Contacts from Org** - Extract all contacts with all fields, record types, and associated files from a selected org (automatically fetches missing accounts)
3. **View Staged Data** - View accounts, contacts, record types, or migration logs stored in SQLite
4. **Migrate Data to Target Org** - Migrate staged data from source org to target org (records and files)
5. **Validate Relationships** - Check relationship integrity and find orphaned contacts
6. **Compare Data Between Orgs** - Compare record counts and record types between orgs

### Database

The application uses SQLite to store staged data in `data/migration.db`. The database includes:

- **accounts**: Account records with all fields stored as JSON
- **contacts**: Contact records with Account relationships
- **record_types**: Record type definitions for each org
- **relationships**: Account-Contact relationship mappings
- **attachments**: Attachment metadata with file paths
- **notes**: Note records with file paths
- **content_documents**: ContentDocument metadata
- **content_versions**: ContentVersion records with file paths
- **content_document_links**: Links between files and records
- **field_metadata**: Cached field availability per org for validation
- **migration_log**: Log of all migration operations

### File Storage

Files are stored in a hierarchical structure under `data/files/`:

```
data/files/
└── {org_source}/
    ├── Account/
    │   └── {salesforce_id}/
    │       ├── attachments/
    │       ├── notes/
    │       └── files/
    └── Contact/
        └── {salesforce_id}/
            ├── attachments/
            ├── notes/
            └── files/
```

### Field Extraction

The application automatically:
- Queries ALL accessible fields from Salesforce objects using the describe API
- Filters out non-queryable fields (encrypted fields without permission, complex formulas)
- Caches field metadata per org for efficient validation during migration
- Extracts all field values including custom fields

### File Backup

When backing up accounts or contacts, the application automatically:
- Downloads all **Attachments** (legacy file storage) as binary files
- Downloads all **Notes** as text files
- Downloads all **Files** (ContentDocument/ContentVersion) as binary files
- Preserves file relationships in the database
- Stores files locally with original filenames

### Migration Process

During migration, the application:
1. **Validates Fields**: Checks which fields exist in the target org and automatically skips fields that don't exist
2. **Maps Record Types**: Maps record types by name between source and target orgs
3. **Migrates Records**: Creates accounts first, then contacts (preserving relationships)
4. **Migrates Files**: Uploads attachments, notes, and files after records are created
5. **Logs Everything**: Records all operations, successes, and failures in the migration_log table

### Notes

- The application automatically handles pagination for large datasets
- Record types are mapped by name between orgs during migration
- Accounts are migrated before contacts to preserve relationships
- Files are migrated after records with proper parent ID mapping
- Fields that don't exist in the target org are automatically skipped (with warnings)
- All operations are logged to the migration_log table
- File storage directory (`data/files/`) is excluded from git via `.gitignore`
