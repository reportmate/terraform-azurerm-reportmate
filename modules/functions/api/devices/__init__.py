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
        
        # Simple query to get devices
        query = """
            SELECT 
                device_id,
                serial_number,
                os_version,
                last_seen,
                created_at
            FROM devices 
            ORDER BY last_seen DESC NULLS LAST
            LIMIT 10
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
            
            logger.info(f"Processing device {device_id} ({serial_number})")
            
            # Try to get device name from inventory
            device_name = serial_number  # Default fallback
            
            try:
                inventory_query = """
                    SELECT module_data 
                    FROM modules 
                    WHERE device_id = %s AND module_id = 'inventory'
                    ORDER BY collected_at DESC
                    LIMIT 1
                """
                inventory_result = db_manager.execute_query(inventory_query, (device_id,))
                
                if inventory_result:
                    module_data = inventory_result[0].get('module_data')
                    if module_data:
                        if isinstance(module_data, str):
                            parsed_data = json.loads(module_data)
                        else:
                            parsed_data = module_data
                            
                        # Look for device name in inventory data
                        if 'inventory' in parsed_data:
                            inventory = parsed_data['inventory']
                            device_name = (
                                inventory.get('deviceName') or 
                                inventory.get('computerName') or 
                                inventory.get('hostname') or 
                                serial_number
                            )
                            logger.info(f"Found device name: {device_name}")
                        else:
                            # Try root level deviceName
                            device_name = (
                                parsed_data.get('deviceName') or
                                parsed_data.get('computerName') or
                                parsed_data.get('hostname') or
                                serial_number
                            )
                        
            except Exception as e:
                logger.warning(f"Could not get inventory for {device_id}: {e}")
            
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
            
            device = {
                'deviceId': device_id,
                'serialNumber': serial_number,
                'name': device_name,
                'os': os_version,
                'status': status,
                'lastSeen': last_seen.isoformat() if last_seen else None,
                'totalEvents': 0,
                'lastEventTime': last_seen.isoformat() if last_seen else None,
                'modules': {}
            }
            devices.append(device)
            logger.info(f"Added device: {device['name']}")
        
        logger.info(f"Successfully processed {len(devices)} devices")
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        
        # Return mock data
        mock_devices = [
            {
                'deviceId': '0F33V9G25083HJ',
                'serialNumber': '0F33V9G25083HJ', 
                'name': 'Rod Christiansen (Fallback)',
                'os': 'Windows 11',
                'status': 'active',
                'lastSeen': datetime.now(timezone.utc).isoformat(),
                'totalEvents': 1,
                'lastEventTime': datetime.now(timezone.utc).isoformat(),
                'modules': {}
            }
        ]
        
        return {
            'success': True,
            'devices': mock_devices,
            'count': len(mock_devices),
            'warning': f'Using mock data: {str(e)}'
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
                headers={'X-Data-Source': 'azure-functions-simplified'}
            )
        else:
            return func.HttpResponse(
                json.dumps({'error': 'Failed to get devices'}, indent=2),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Critical error in devices endpoint: {e}", exc_info=True)
        
        # Emergency fallback
        mock_response = [
            {
                'deviceId': '0F33V9G25083HJ',
                'serialNumber': '0F33V9G25083HJ',
                'name': 'Emergency Fallback Device',
                'os': 'Windows 11',
                'status': 'active',
                'lastSeen': datetime.now(timezone.utc).isoformat(),
                'totalEvents': 0,
                'lastEventTime': datetime.now(timezone.utc).isoformat(),
                'modules': {}
            }
        ]
        
        return func.HttpResponse(
            json.dumps(mock_response, indent=2),
            status_code=200,
            mimetype="application/json",
            headers={'X-Data-Source': 'emergency-fallback'}
        )
