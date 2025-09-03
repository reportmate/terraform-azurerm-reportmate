"""
System Data Endpoint for ReportMate - Bulk System Module Data
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

def get_system_data_sync():
    """Get system data using sync database connection"""
    try:
        logger.info("Starting system data query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # Query for system module data
        query = """
            SELECT 
                device_id,
                module_data,
                collected_at
            FROM modules 
            WHERE module_id = 'system'
              AND module_data IS NOT NULL
            ORDER BY device_id, collected_at DESC
        """
        
        logger.info("Executing system data query...")
        results = db_manager.execute_query(query)
        logger.info(f"Got {len(results)} system module records")
        
        if not results:
            logger.warning("No system module data found")
            return []
        
        # Process system data and get latest for each device
        devices_system = {}
        for row in results:
            device_id = row.get('device_id')
            module_data = row.get('module_data')
            collected_at = row.get('collected_at')
            
            if not device_id or not module_data:
                continue
            
            # Skip if we already have newer data for this device
            if device_id in devices_system:
                continue
            
            try:
                if isinstance(module_data, str):
                    parsed_data = json.loads(module_data)
                else:
                    parsed_data = module_data
                
                # Get device serial number
                device_query = "SELECT serial_number FROM devices WHERE device_id = %s"
                device_result = db_manager.execute_query(device_query, (device_id,))
                
                serial_number = None
                if device_result:
                    serial_number = device_result[0].get('serial_number')
                
                if not serial_number:
                    logger.warning(f"No serial number found for device {device_id}")
                    continue
                
                # Extract system information
                system_info = {}
                if 'system' in parsed_data:
                    system_data = parsed_data['system']
                elif 'operatingSystem' in parsed_data:
                    # Direct OS data
                    system_info['operatingSystem'] = parsed_data['operatingSystem']
                else:
                    # Try to extract from root level
                    system_info = parsed_data
                
                system_record = {
                    'deviceId': device_id,
                    'serialNumber': serial_number,
                    'collectedAt': collected_at.isoformat() if collected_at else None,
                    **system_info
                }
                
                devices_system[device_id] = system_record
                logger.info(f"Processed system data for device {serial_number}")
                
            except Exception as e:
                logger.warning(f"Could not parse system data for device {device_id}: {e}")
                continue
        
        system_list = list(devices_system.values())
        logger.info(f"Successfully processed {len(system_list)} system records")
        return system_list
        
    except Exception as e:
        logger.error(f"Error getting system data: {e}", exc_info=True)
        return []

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    System data endpoint
    """
    try:
        logger.info("System data endpoint called")
        
        system_data = get_system_data_sync()

        if system_data:
            return func.HttpResponse(
                json.dumps(system_data, indent=2),
                status_code=200,
                mimetype="application/json",
                headers={
                    'X-Data-Source': 'azure-functions-database',
                    'X-Records-Count': str(len(system_data))
                }
            )
        else:
            return func.HttpResponse(
                json.dumps([], indent=2),
                status_code=200,
                mimetype="application/json",
                headers={'X-Data-Source': 'azure-functions-database-empty'}
            )
        
    except Exception as e:
        logger.error(f"Critical error in system data endpoint: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
