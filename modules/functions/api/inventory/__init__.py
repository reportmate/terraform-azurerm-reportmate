"""
Inventory Module Endpoint for ReportMate
Returns inventory data for all devices
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

def get_inventory_data():
    """Get inventory data for all devices from database"""
    try:
        logger.info("Starting inventory data query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # Query to get inventory data from inventory table joined with devices
        query = """
            SELECT 
                i.device_id,
                d.serial_number,
                d.name as device_name,
                d.last_seen,
                i.data as module_data,
                i.collected_at
            FROM inventory i
            JOIN devices d ON i.device_id = d.id
            WHERE d.serial_number IS NOT NULL 
              AND d.serial_number != ''
              AND d.serial_number NOT LIKE 'TEST-%'
              AND d.serial_number != 'localhost'
            ORDER BY i.collected_at DESC
        """
        
        logger.info("Executing inventory query...")
        inventory_raw = db_manager.execute_query(query)
        logger.info(f"Got {len(inventory_raw)} inventory records")
        
        inventory_data = []
        for row in inventory_raw:
            device_id = row.get('device_id', 'unknown')
            serial_number = row.get('serial_number', 'Unknown Serial')
            device_name = row.get('device_name', serial_number)
            last_seen = row.get('last_seen')
            collected_at = row.get('collected_at')
            module_data = row.get('module_data')
            
            logger.info(f"Processing inventory for device {device_id} ({serial_number})")
            
            # Parse module data
            inventory_info = {}
            if module_data:
                try:
                    if isinstance(module_data, str):
                        parsed_data = json.loads(module_data)
                    else:
                        parsed_data = module_data
                        
                    # Extract inventory information from the data
                    if 'inventory' in parsed_data:
                        inventory_info = parsed_data['inventory']
                    else:
                        inventory_info = parsed_data
                        
                except Exception as e:
                    logger.warning(f"Could not parse inventory data for {device_id}: {e}")
                    inventory_info = {}
            
            # Get device name from inventory data with fallbacks
            final_device_name = (
                inventory_info.get('deviceName') or 
                inventory_info.get('computerName') or 
                inventory_info.get('hostname') or 
                device_name or 
                serial_number
            )
            
            # Clean up manufacturer and model data - filter out "Unknown" values
            manufacturer = inventory_info.get('manufacturer')
            if manufacturer and manufacturer.lower() in ['unknown', '', 'null']:
                manufacturer = None
                
            model = inventory_info.get('model') 
            if model and model.lower() in ['unknown', '', 'null']:
                model = None
            
            inventory_item = {
                'id': device_id,
                'deviceId': device_id,
                'deviceName': final_device_name,
                'serialNumber': serial_number,
                'lastSeen': last_seen.isoformat() if last_seen else None,
                'collectedAt': collected_at.isoformat() if collected_at else None,
                # Extract specific inventory fields
                'assetTag': inventory_info.get('assetTag') or inventory_info.get('asset_tag'),
                'location': inventory_info.get('location'),
                'usage': inventory_info.get('usage'),
                'catalog': inventory_info.get('catalog'),
                'computerName': inventory_info.get('computerName') or inventory_info.get('computer_name'),
                'domain': inventory_info.get('domain'),
                'organizationalUnit': inventory_info.get('organizationalUnit') or inventory_info.get('organizational_unit'),
                'manufacturer': manufacturer,
                'model': model,
                'uuid': inventory_info.get('uuid') or inventory_info.get('device_id'),
                'raw': inventory_info
            }
            
            inventory_data.append(inventory_item)
            logger.info(f"Added inventory data for: {final_device_name}")
        
        logger.info(f"Successfully processed {len(inventory_data)} inventory records")
        return {
            'success': True,
            'inventory': inventory_data,
            'count': len(inventory_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting inventory data: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Failed to get inventory data: {str(e)}',
            'inventory': [],
            'count': 0
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Inventory endpoint - returns inventory data for all devices
    """
    try:
        logger.info("Inventory endpoint called")
        
        result = get_inventory_data()

        if result['success']:
            return func.HttpResponse(
                json.dumps(result['inventory'], indent=2),
                status_code=200,
                mimetype="application/json",
                headers={'X-Data-Source': 'azure-functions-database'}
            )
        else:
            return func.HttpResponse(
                json.dumps({'error': result.get('error', 'Failed to get inventory data')}, indent=2),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Critical error in inventory endpoint: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
