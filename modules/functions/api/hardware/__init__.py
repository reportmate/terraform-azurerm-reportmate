"""
Hardware Module Endpoint for ReportMate
Returns hardware data for all devices
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

def get_hardware_data():
    """Get hardware data for all devices from database"""
    try:
        logger.info("Starting hardware data query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # Query to get hardware data from hardware table
        query = """
            SELECT 
                h.device_id,
                d.serial_number,
                d.name as device_name,
                d.last_seen,
                h.data as module_data,
                h.collected_at
            FROM hardware h
            JOIN devices d ON h.device_id = d.id
            WHERE d.serial_number IS NOT NULL 
              AND d.serial_number != ''
              AND d.serial_number NOT LIKE 'TEST-%'
              AND d.serial_number != 'localhost'
            ORDER BY h.collected_at DESC
        """
        
        logger.info("Executing hardware query...")
        hardware_raw = db_manager.execute_query(query)
        logger.info(f"Got {len(hardware_raw)} hardware records")
        
        hardware_data = []
        for row in hardware_raw:
            device_id = row.get('device_id', 'unknown')
            serial_number = row.get('serial_number', 'Unknown Serial')
            device_name = row.get('device_name', serial_number)
            last_seen = row.get('last_seen')
            collected_at = row.get('collected_at')
            module_data = row.get('module_data')
            
            logger.info(f"Processing hardware for device {device_id} ({serial_number})")
            
            # Parse module data
            hardware_info = {}
            if module_data:
                try:
                    if isinstance(module_data, str):
                        parsed_data = json.loads(module_data)
                    else:
                        parsed_data = module_data
                        
                    # Extract hardware information from the data
                    if 'hardware' in parsed_data:
                        hardware_info = parsed_data['hardware']
                    else:
                        hardware_info = parsed_data
                        
                except Exception as e:
                    logger.warning(f"Could not parse hardware data for {device_id}: {e}")
                    hardware_info = {}
            
            hardware_item = {
                'id': device_id,
                'deviceId': device_id,
                'deviceName': device_name,
                'serialNumber': serial_number,
                'lastSeen': last_seen.isoformat() if last_seen else None,
                'collectedAt': collected_at.isoformat() if collected_at else None,
                # Extract specific hardware fields
                'processor': hardware_info.get('processor') or hardware_info.get('cpu', {}).get('name'),
                'processorSpeed': hardware_info.get('processorSpeed') or hardware_info.get('cpu', {}).get('speed'),
                'cores': hardware_info.get('cores') or hardware_info.get('cpu', {}).get('cores'),
                'memory': hardware_info.get('memory') or hardware_info.get('totalRAM'),
                'storage': hardware_info.get('storage') or hardware_info.get('disk', {}).get('total'),
                'graphics': hardware_info.get('graphics') or hardware_info.get('gpu', {}).get('name'),
                'motherboard': hardware_info.get('motherboard', {}).get('name'),
                'bios': hardware_info.get('bios', {}).get('version'),
                'architecture': hardware_info.get('architecture'),
                'raw': hardware_info
            }
            
            hardware_data.append(hardware_item)
            logger.info(f"Added hardware data for: {device_name}")
        
        logger.info(f"Successfully processed {len(hardware_data)} hardware records")
        return {
            'success': True,
            'hardware': hardware_data,
            'count': len(hardware_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting hardware data: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Failed to get hardware data: {str(e)}',
            'hardware': [],
            'count': 0
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Hardware endpoint - returns hardware data for all devices
    """
    try:
        logger.info("Hardware endpoint called")
        
        result = get_hardware_data()

        if result['success']:
            return func.HttpResponse(
                json.dumps(result['hardware'], indent=2),
                status_code=200,
                mimetype="application/json",
                headers={'X-Data-Source': 'azure-functions-database'}
            )
        else:
            return func.HttpResponse(
                json.dumps({'error': result.get('error', 'Failed to get hardware data')}, indent=2),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Critical error in hardware endpoint: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
