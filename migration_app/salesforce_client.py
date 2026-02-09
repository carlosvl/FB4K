"""
Salesforce client using SFDX authentication
"""

import subprocess
import json
import sys
from typing import Dict, List, Optional, Any
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError


class SalesforceClient:
    """Client for connecting to Salesforce using SFDX authentication."""
    
    def __init__(self):
        """Initialize Salesforce client."""
        self.connections: Dict[str, Salesforce] = {}
        self.org_info: Dict[str, Dict[str, Any]] = {}
    
    def list_orgs(self) -> List[Dict[str, Any]]:
        """List all authenticated SFDX orgs.
        
        Returns:
            List of org dictionaries with alias, username, instanceUrl, etc.
        """
        try:
            result = subprocess.run(
                ['sf', 'org', 'list', '--json'],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            
            if 'result' in data and 'nonScratchOrgs' in data['result']:
                orgs = []
                for org in data['result']['nonScratchOrgs']:
                    org_info = {
                        'alias': org.get('alias', ''),
                        'username': org.get('username', ''),
                        'orgId': org.get('orgId', ''),
                        'instanceUrl': org.get('instanceUrl', ''),
                        'accessToken': org.get('accessToken', '')
                    }
                    orgs.append(org_info)
                    self.org_info[org_info['alias'] or org_info['username']] = org_info
                
                return orgs
            return []
        except subprocess.CalledProcessError as e:
            print(f"Error listing orgs: {e.stderr}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing org list JSON: {e}", file=sys.stderr)
            return []
        except FileNotFoundError:
            print("Error: SFDX CLI not found. Please install Salesforce CLI.", file=sys.stderr)
            return []
    
    def get_org_info(self, org_alias: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific org.
        
        Args:
            org_alias: Org alias or username
            
        Returns:
            Org information dictionary
        """
        if org_alias in self.org_info:
            return self.org_info[org_alias]
        
        try:
            result = subprocess.run(
                ['sf', 'org', 'display', '--target-org', org_alias, '--json'],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            
            if 'result' in data:
                org_info = {
                    'alias': data['result'].get('alias', org_alias),
                    'username': data['result'].get('username', ''),
                    'orgId': data['result'].get('id', ''),
                    'instanceUrl': data['result'].get('instanceUrl', ''),
                    'accessToken': data['result'].get('accessToken', '')
                }
                self.org_info[org_alias] = org_info
                return org_info
        except subprocess.CalledProcessError as e:
            print(f"Error getting org info: {e.stderr}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Error parsing org info JSON: {e}", file=sys.stderr)
        
        return None
    
    def connect(self, org_alias: str) -> Optional[Salesforce]:
        """Connect to a Salesforce org using SFDX authentication.
        
        Args:
            org_alias: Org alias or username
            
        Returns:
            Salesforce connection object or None if connection fails
        """
        if org_alias in self.connections:
            return self.connections[org_alias]
        
        org_info = self.get_org_info(org_alias)
        if not org_info:
            print(f"Could not find org: {org_alias}", file=sys.stderr)
            return None
        
        instance_url = org_info.get('instanceUrl')
        access_token = org_info.get('accessToken')
        
        if not instance_url or not access_token:
            print(f"Missing instance URL or access token for org: {org_alias}", file=sys.stderr)
            return None
        
        try:
            # Create Salesforce connection using access token
            sf = Salesforce(
                instance_url=instance_url,
                session_id=access_token
            )
            self.connections[org_alias] = sf
            return sf
        except Exception as e:
            print(f"Error connecting to Salesforce: {e}", file=sys.stderr)
            return None
    
    def query(self, org_alias: str, soql: str) -> Optional[List[Dict[str, Any]]]:
        """Execute a SOQL query.
        
        Args:
            org_alias: Org alias or username
            soql: SOQL query string
            
        Returns:
            List of records or None if query fails
        """
        sf = self.connect(org_alias)
        if not sf:
            return None
        
        try:
            result = sf.query(soql)
            records = result.get('records', [])
            
            # Remove 'attributes' key from each record
            for record in records:
                record.pop('attributes', None)
            
            return records
        except SalesforceError as e:
            print(f"Salesforce query error: {e}", file=sys.stderr)
            return None
    
    def query_all(self, org_alias: str, soql: str) -> Optional[List[Dict[str, Any]]]:
        """Execute a SOQL query and handle pagination.
        
        Args:
            org_alias: Org alias or username
            soql: SOQL query string
            
        Returns:
            List of all records across all pages
        """
        sf = self.connect(org_alias)
        if not sf:
            return None
        
        try:
            all_records = []
            result = sf.query(soql)
            
            while True:
                records = result.get('records', [])
                # Remove 'attributes' key from each record
                for record in records:
                    record.pop('attributes', None)
                all_records.extend(records)
                
                # Check if there are more pages
                if not result.get('done', True):
                    result = sf.query_more(result['nextRecordsUrl'], True)
                else:
                    break
            
            return all_records
        except SalesforceError as e:
            print(f"Salesforce query error: {e}", file=sys.stderr)
            return None
    
    def describe_object(self, org_alias: str, object_name: str) -> Optional[Dict[str, Any]]:
        """Get object metadata/describe information.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            
        Returns:
            Object describe dictionary or None if fails
        """
        sf = self.connect(org_alias)
        if not sf:
            return None
        
        try:
            # Use the REST API to get describe
            # Try to get API version from Salesforce instance, default to latest
            api_version = getattr(sf, 'sf_version', 'v58.0')
            if not api_version.startswith('v'):
                api_version = f"v{api_version}"
            
            describe_url = f"/services/data/{api_version}/sobjects/{object_name}/describe"
            result = sf.restful(describe_url)
            return result
        except (SalesforceError, AttributeError) as e:
            # Fallback: try using the describe method if available
            try:
                obj = getattr(sf, object_name)
                if hasattr(obj, 'describe'):
                    return obj.describe()
            except:
                pass
            print(f"Error describing object {object_name}: {e}", file=sys.stderr)
            return None
    
    def get_object_fields(self, org_alias: str, object_name: str) -> List[str]:
        """Get list of field names for an object.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            
        Returns:
            List of field API names
        """
        describe = self.describe_object(org_alias, object_name)
        if not describe:
            return []
        
        fields = describe.get('fields', [])
        return [field['name'] for field in fields if field.get('accessable', False)]
    
    def create_record(self, org_alias: str, object_name: str, record_data: Dict[str, Any]) -> Optional[str]:
        """Create a record in Salesforce.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            record_data: Dictionary of field values
            
        Returns:
            Created record ID or None if creation fails
        """
        sf = self.connect(org_alias)
        if not sf:
            return None
        
        try:
            # Get the object handler
            obj = getattr(sf, object_name)
            result = obj.create(record_data)
            return result.get('id') if result.get('success') else None
        except SalesforceError as e:
            print(f"Error creating {object_name} record: {e}", file=sys.stderr)
            return None
    
    def bulk_create(self, org_alias: str, object_name: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create records in Salesforce.
        
        Args:
            org_alias: Org alias or username
            object_name: Name of the Salesforce object
            records: List of record dictionaries
            
        Returns:
            List of results with success status and IDs
        """
        sf = self.connect(org_alias)
        if not sf:
            return []
        
        results = []
        try:
            # Get the object handler
            obj = getattr(sf, object_name)
            
            # Process in batches of 200 (Salesforce limit)
            batch_size = 200
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                batch_results = obj.bulk.create(batch)
                results.extend(batch_results)
        except SalesforceError as e:
            print(f"Error bulk creating {object_name} records: {e}", file=sys.stderr)
        
        return results
