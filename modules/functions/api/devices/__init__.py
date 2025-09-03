"""
Devices List Endpoint for ReportMate - SIMPLIFIED VERSION
"""
import logging
import json
import azure.functions as func
import os
import sys
from datetime import datetime, timezone, timedelta

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SyncDatabaseManager

logger = logging.getLogger(__name__)

def list_devices_sync():
    """List devices using sync database connection with enhanced device names"""
    try:
        logger.info("Starting devices list query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed, returning mock data")
            raise Exception("Database connection failed")
        
        # Simple query to get devices - include created_at for registration date
        query = """
            SELECT 
                device_id,
                serial_number,
                os_version,
                last_seen,
                created_at
            FROM devices 
            WHERE serial_number IS NOT NULL 
              AND serial_number != ''
              AND serial_number NOT LIKE 'TEST-%'
              AND serial_number != 'localhost'
            ORDER BY last_seen DESC NULLS LAST
        """
        
        logger.info("Executing devices query...")
        devices_raw = db_manager.execute_query(query)
        logger.info(f"Got {len(devices_raw)} raw device records")
        
        if not devices_raw:
            logger.warning("No devices found in database")
            raise Exception("No devices found")
        
        devices = []
        for row in devices_raw:
            device_id = row.get('device_id', 'unknown')
            serial_number = row.get('serial_number', 'Unknown Serial')
            os_version = row.get('os_version', 'Unknown OS')
            last_seen = row.get('last_seen')
            created_at = row.get('created_at')  # Registration date
            
            logger.info(f"Processing device {device_id} ({serial_number})")
            
            # Initialize modules structure and device name
            device_name = serial_number  # Default fallback
            modules = {}
            
            # Get all module data for this device to build proper modules structure
            try:
                modules_query = """
                    SELECT module_id, module_data 
                    FROM modules 
                    WHERE device_id = %s 
                    ORDER BY module_id, collected_at DESC
                """
                modules_result = db_manager.execute_query(modules_query, (device_id,))
                
                if modules_result:
                    # Group by module_id and take the latest data for each module
                    modules_by_id = {}
                    for module_row in modules_result:
                        module_id = module_row.get('module_id')
                        module_data = module_row.get('module_data')
                        
                        if module_id and module_id not in modules_by_id:
                            try:
                                if isinstance(module_data, str):
                                    parsed_data = json.loads(module_data)
                                else:
                                    parsed_data = module_data
                                
                                # Store the actual module content (not wrapped in another object)
                                if isinstance(parsed_data, dict) and module_id in parsed_data:
                                    modules_by_id[module_id] = parsed_data[module_id]
                                else:
                                    modules_by_id[module_id] = parsed_data
                                    
                            except Exception as parse_error:
                                logger.warning(f"Failed to parse {module_id} data for {device_id}: {parse_error}")
                    
                    modules = modules_by_id
                    
                    # Extract device name from inventory module if available
                    if 'inventory' in modules:
                        inventory = modules['inventory']
                        device_name = (
                            inventory.get('deviceName') or 
                            inventory.get('computerName') or 
                            inventory.get('hostname') or 
                            serial_number
                        )
                        logger.info(f"Found device name from inventory: {device_name}")
                        
            except Exception as e:
                logger.warning(f"Could not get modules for {device_id}: {e}")
            
            # Calculate status
            status = 'active'
            if last_seen:
                hours_ago = (datetime.now(timezone.utc) - last_seen.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                if hours_ago > 24:
                    status = 'offline'
                elif hours_ago > 1:
                    status = 'warning'
            else:
                status = 'missing'
            
            # Get event count for this device
            try:
                event_count_query = """
                    SELECT COUNT(*) as event_count 
                    FROM events 
                    WHERE device_id = %s
                """
                event_result = db_manager.execute_query(event_count_query, (device_id,))
                total_events = event_result[0].get('event_count', 0) if event_result else 0
            except Exception as e:
                logger.warning(f"Could not get event count for {device_id}: {e}")
                total_events = 0
            
            device = {
                'deviceId': device_id,
                'serialNumber': serial_number,
                'name': device_name,
                'os': os_version,
                'status': status,
                'lastSeen': last_seen.isoformat() if last_seen else None,
                'createdAt': created_at.isoformat() if created_at else None,  # Registration date
                'totalEvents': total_events,
                'lastEventTime': last_seen.isoformat() if last_seen else None,
                'modules': modules  # Include full modules structure
            }
            devices.append(device)
            logger.info(f"Added device: {device['name']} with {len(modules)} modules and {total_events} events")
        
        logger.info(f"Successfully processed {len(devices)} devices")
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        
        # NO FALLBACK DATA ALLOWED - Return proper error
        return {
            'success': False,
            'error': f'Failed to list devices: {str(e)}',
            'devices': [],
            'count': 0
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Devices list endpoint
    """
    try:
        logger.info("Devices endpoint called")
        
        result = list_devices_sync()

        if result['success']:
            return func.HttpResponse(
                json.dumps(result['devices'], indent=2),
                status_code=200,
                mimetype="application/json",
                headers={'X-Data-Source': 'azure-functions-database'}
            )
        else:
            return func.HttpResponse(
                json.dumps({'error': result.get('error', 'Failed to get devices')}, indent=2),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Critical error in devices endpoint: {e}", exc_info=True)
        
        # NO FALLBACK DATA ALLOWED - Return proper error
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
