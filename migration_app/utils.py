"""
Utility functions for the migration application
"""

import json
import os
import base64
from pathlib import Path
from typing import Any, Dict, List


def safe_get_field(record: Dict[str, Any], field_name: str, default: Any = None) -> Any:
    """Safely get a field from a Salesforce record."""
    return record.get(field_name, default)


def format_record_for_db(record: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """Format a Salesforce record for database insertion."""
    db_record = {}
    for field in fields:
        value = safe_get_field(record, field)
        # Convert None to NULL for database
        if value is None:
            db_record[field] = None
        elif isinstance(value, (dict, list)):
            # Store complex objects as JSON strings
            db_record[field] = json.dumps(value)
        else:
            db_record[field] = value
    return db_record


def get_record_type_info(record: Dict[str, Any]) -> tuple:
    """Extract record type ID and name from a record."""
    record_type_id = safe_get_field(record, 'RecordTypeId')
    record_type_name = safe_get_field(record, 'RecordType', {}).get('Name') if isinstance(
        safe_get_field(record, 'RecordType'), dict) else None
    
    # If RecordType is not expanded, we'll need to query it separately
    return record_type_id, record_type_name


def get_file_storage_path(org_source: str, object_type: str, record_id: str, 
                         file_type: str, filename: str = None) -> Path:
    """Generate file storage path for a file.
    
    Args:
        org_source: Source org identifier
        object_type: Object type (Account, Contact, etc.)
        record_id: Salesforce record ID
        file_type: Type of file (attachments, notes, files)
        filename: Optional filename
        
    Returns:
        Path object for the file
    """
    project_root = Path(__file__).parent.parent
    base_path = project_root / "data" / "files" / org_source / object_type / record_id / file_type
    
    if filename:
        return base_path / filename
    
    return base_path


def ensure_directory_exists(file_path: Path):
    """Ensure directory structure exists for a file path.
    
    Args:
        file_path: Path to file (directory will be created)
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def save_binary_file(file_path: Path, binary_data: bytes):
    """Save binary data to a file.
    
    Args:
        file_path: Path where file should be saved
        binary_data: Binary data to save
    """
    ensure_directory_exists(file_path)
    with open(file_path, 'wb') as f:
        f.write(binary_data)


def read_binary_file(file_path: Path) -> bytes:
    """Read binary data from a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Binary data
    """
    with open(file_path, 'rb') as f:
        return f.read()


def encode_base64(binary_data: bytes) -> str:
    """Encode binary data to base64 string for Salesforce API.
    
    Args:
        binary_data: Binary data to encode
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(binary_data).decode('utf-8')


def decode_base64(base64_data: str) -> bytes:
    """Decode base64 string to binary data.
    
    Args:
        base64_data: Base64 encoded string
        
    Returns:
        Binary data
    """
    return base64.b64decode(base64_data)
