"""
Installs Aggregation Endpoint for ReportMate - ULTRA-FAST VERSION
Returns installs summary data for all devices efficiently.

Performance optimizations:
- Single bulk query for device basic info
- Single bulk query for installs data
- Minimal JSON parsing only for required fields
- Aggregates package counts without loading full package details
"""
import logging
import json
import azure.functions as func
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SyncDatabaseManager

logger = logging.getLogger(__name__)

def extract_install_summary(installs_data, device_id):
    """Extract install summary from installs data without heavy processing"""
    try:
        if isinstance(installs_data, str):
            data = json.loads(installs_data)
        else:
            data = installs_data
        
        # Initialize counters
        summary = {
            'totalPackages': 0,
            'installed': 0,
            'pending': 0,
            'failed': 0,
            'systemName': 'Unknown',
            'packages': []
        }
        
        # Quick extraction from key fields in sample data structure
        if 'recentInstalls' in data:
            recent = data.get('recentInstalls', [])
            summary['installed'] = len(recent)
            for install in recent[:10]:  # Limit to first 10 for performance
                summary['packages'].append({
                    'name': install.get('name', 'Unknown'),
                    'status': 'installed',
                    'version': install.get('version', ''),
                    'lastUpdate': install.get('timestamp', '')
                })
        
        if 'pendingInstalls' in data:
            pending = data.get('pendingInstalls', [])
            summary['pending'] = len(pending)
            for install in pending[:10]:  # Limit to first 10 for performance
                summary['packages'].append({
                    'name': install.get('name', 'Unknown'),
                    'status': 'pending',
                    'version': install.get('version', ''),
                    'lastUpdate': install.get('timestamp', '')
                })
        
        if 'recentEvents' in data:
            events = data.get('recentEvents', [])
            failed_events = [e for e in events if 'error' in str(e.get('message', '')).lower()]
            summary['failed'] = len(failed_events)
        
        # Detect system type
        if 'cimian' in data:
            summary['systemName'] = 'Cimian (Windows)'
        elif 'munki' in data or any('munki' in str(k).lower() for k in data.keys()):
            summary['systemName'] = 'Munki (macOS)'
        else:
            summary['systemName'] = 'Generic'
        
        summary['totalPackages'] = summary['installed'] + summary['pending'] + summary['failed']
        
        return summary
        
    except Exception as e:
        logger.warning(f"Failed to parse installs data for device {device_id}: {e}")
        return {
            'totalPackages': 0,
            'installed': 0,
            'pending': 0,
            'failed': 0,
            'systemName': 'Unknown',
            'packages': []
        }

def get_installs_summary():
    """Get installs summary for all devices efficiently"""
    try:
        logger.info("Starting FAST installs aggregation query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # Get basic device info
        devices_query = """
            SELECT 
                device_id,
                serial_number,
                last_seen,
                created_at
            FROM devices 
            WHERE serial_number IS NOT NULL 
              AND serial_number != ''
              AND serial_number NOT LIKE 'TEST-%'
              AND serial_number != 'localhost'
            ORDER BY last_seen DESC NULLS LAST
        """
        
        devices_raw = db_manager.execute_query(devices_query)
        logger.info(f"Got {len(devices_raw)} devices")
        
        if not devices_raw:
            return []
        
        device_ids = [row['device_id'] for row in devices_raw]
        
        # Bulk query for device names from inventory
        device_names = {}
        try:
            placeholders = ','.join(['%s'] * len(device_ids))
            inventory_query = f"""
                SELECT DISTINCT ON (device_id) 
                    device_id,
                    data
                FROM inventory 
                WHERE device_id IN ({placeholders})
                ORDER BY device_id, collected_at DESC
            """
            inventory_results = db_manager.execute_query(inventory_query, device_ids)
            
            for result in inventory_results:
                device_id = result.get('device_id')
                data = result.get('data')
                
                # Parse inventory data to extract device name
                try:
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    # Try various fields for device name
                    name = (
                        parsed_data.get('deviceName') or
                        parsed_data.get('computerName') or
                        parsed_data.get('hostname') or
                        parsed_data.get('name') or
                        parsed_data.get('displayName')
                    )
                    
                    if name and str(name).strip() and str(name) != 'null':
                        device_names[device_id] = str(name).strip()
                        logger.debug(f"Found device name for {device_id}: {name}")
                    else:
                        logger.debug(f"No valid device name found for {device_id} in inventory data")
                        
                except Exception as e:
                    logger.debug(f"Failed to parse inventory data for device {device_id}: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to get device names: {e}")
        
        # Bulk query for installs data and version info
        installs_data = {}
        cimian_versions = {}
        try:
            installs_query = f"""
                SELECT DISTINCT ON (device_id) 
                    device_id,
                    data,
                    collected_at
                FROM installs 
                WHERE device_id IN ({placeholders})
                ORDER BY device_id, collected_at DESC
            """
            installs_results = db_manager.execute_query(installs_query, device_ids)
            
            for result in installs_results:
                device_id = result.get('device_id')
                data = result.get('data')
                collected_at = result.get('collected_at')
                installs_data[device_id] = {
                    'data': data,
                    'collected_at': collected_at
                }
                
                # Extract Cimian version from installs data
                try:
                    if isinstance(data, str):
                        parsed_data = json.loads(data)
                    else:
                        parsed_data = data
                    
                    # Try to find Cimian version in different locations
                    version = None
                    if 'cimian' in parsed_data:
                        if isinstance(parsed_data['cimian'], dict) and 'version' in parsed_data['cimian']:
                            version = parsed_data['cimian']['version']
                        elif isinstance(parsed_data['cimian'], str):
                            version = parsed_data['cimian']
                    elif 'version' in parsed_data:
                        version = parsed_data['version']
                    
                    if version and str(version).strip():
                        cimian_versions[device_id] = str(version).strip()
                        logger.debug(f"Found Cimian version for {device_id}: {version}")
                        
                except Exception as e:
                    logger.debug(f"Failed to extract version for device {device_id}: {e}")
                
        except Exception as e:
            logger.warning(f"Failed to get installs data: {e}")
        
        # Process devices
        processed_devices = []
        for device_row in devices_raw:
            device_id = device_row['device_id']
            serial_number = device_row['serial_number']
            last_seen = device_row['last_seen']
            created_at = device_row['created_at']
            
            device_name = device_names.get(device_id, serial_number)
            
            # Get installs summary
            install_summary = {'totalPackages': 0, 'installed': 0, 'pending': 0, 'failed': 0, 'systemName': 'Unknown', 'packages': []}
            collected_at = None
            cimian_version = None
            
            if device_id in installs_data:
                install_data = installs_data[device_id]
                install_summary = extract_install_summary(install_data['data'], device_id)
                collected_at = install_data['collected_at']
                cimian_version = cimian_versions.get(device_id)
            
            processed_devices.append({
                'id': device_id,
                'deviceId': device_id,
                'deviceName': device_name,
                'serialNumber': serial_number,
                'lastSeen': last_seen.isoformat() if last_seen else None,
                'createdAt': created_at.isoformat() if created_at else None,
                'collectedAt': collected_at.isoformat() if collected_at else None,
                'totalPackages': install_summary['totalPackages'],
                'installed': install_summary['installed'],
                'pending': install_summary['pending'],
                'failed': install_summary['failed'],
                'packages': install_summary['packages'],
                'systemName': install_summary['systemName'],
                'lastUpdate': collected_at.isoformat() if collected_at else None,
                'modules': {
                    'installs': {
                        'cimian': {
                            'version': cimian_version
                        } if cimian_version else {}
                    },
                    'inventory': {
                        'deviceName': device_name
                    }
                },
                # Add raw property for frontend compatibility
                'raw': {
                    'cimian': {
                        'version': cimian_version
                    } if cimian_version else {},
                    'munki': {
                        # Add munki version if we find it in the future
                    }
                }
            })
        
        logger.info(f"Successfully processed {len(processed_devices)} devices with installs data")
        return processed_devices
        
    except Exception as e:
        logger.error(f"Error getting installs summary: {e}", exc_info=True)
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Installs aggregation endpoint
    """
    try:
        logger.info("Installs aggregation endpoint called")
        
        devices = get_installs_summary()
        
        return func.HttpResponse(
            json.dumps(devices, indent=2),
            status_code=200,
            mimetype="application/json",
            headers={'X-Data-Source': 'azure-functions-database-optimized'}
        )
        
    except Exception as e:
        logger.error(f"Critical error in installs endpoint: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
