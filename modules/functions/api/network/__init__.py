"""
Network Data Endpoint for ReportMate - Bulk Network Module Data
"""
import logging
import json
import azure.functions as func
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import DatabaseManager

logger = logging.getLogger(__name__)

def get_network_data_sync():
    """Get network data using sync database connection - matches device API approach"""
    try:
        logger.info("Starting network data query")
        db_manager = DatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # Query for network module data from the network table with inventory data for device names
        query = """
            SELECT 
                n.device_id,
                n.data as module_data,
                n.collected_at,
                n.created_at,
                d.name as device_name,
                d.serial_number,
                d.last_seen,
                i.data as inventory_data
            FROM network n
            LEFT JOIN devices d ON n.device_id = d.id
            LEFT JOIN inventory i ON n.device_id = i.device_id
            WHERE n.data IS NOT NULL
            ORDER BY n.device_id, n.created_at DESC
        """
        
        logger.info("Executing network data query...")
        results = db_manager.execute_query(query)
        logger.info(f"Got {len(results)} network module records")
        
        if not results:
            logger.warning("No network module data found")
            return []
        
        # Process network data and get latest for each device
        devices_network = {}
        for row in results:
            device_id = row.get('device_id')  # This is the serial number (primary key)
            module_data = row.get('module_data')
            collected_at = row.get('collected_at')
            device_name = row.get('device_name')
            serial_number = row.get('serial_number')
            last_seen = row.get('last_seen')
            inventory_data = row.get('inventory_data')
            
            if not device_id or not module_data:
                continue
            
            # Skip if we already have newer data for this device
            if device_id in devices_network:
                continue
            
            try:
                if isinstance(module_data, str):
                    parsed_data = json.loads(module_data)
                else:
                    parsed_data = module_data
                
                # Get better device name from inventory data if available
                display_name = device_name or device_id
                asset_tag = None
                if inventory_data:
                    try:
                        if isinstance(inventory_data, str):
                            inventory_parsed = json.loads(inventory_data)
                        else:
                            inventory_parsed = inventory_data
                        
                        # Use deviceName from inventory, fallback to computerName, then hostname from network data
                        display_name = (
                            inventory_parsed.get('deviceName') or 
                            inventory_parsed.get('computerName') or 
                            parsed_data.get('hostname') or 
                            device_name or 
                            device_id
                        )
                        
                        # Extract asset tag from inventory
                        asset_tag = inventory_parsed.get('assetTag')
                        
                    except Exception as inv_error:
                        logger.warning(f"Could not parse inventory data for device {device_id}: {inv_error}")
                
                if not serial_number:
                    logger.warning(f"No serial number found for device {device_id}")
                    continue
                
                # Format network data to match expected frontend structure
                network_record = {
                    'id': device_id,
                    'deviceId': device_id,
                    'deviceName': display_name,
                    'serialNumber': serial_number or device_id,
                    'assetTag': asset_tag,
                    'lastSeen': last_seen.isoformat() if last_seen and hasattr(last_seen, 'isoformat') else str(last_seen) if last_seen else None,
                    'collectedAt': collected_at.isoformat() if collected_at and hasattr(collected_at, 'isoformat') else str(collected_at) if collected_at else None,
                    'operatingSystem': 'Unknown OS',  # Network module doesn't contain OS info
                    'osVersion': None,
                    'buildNumber': None,
                    'uptime': None,
                    'bootTime': None,
                    'raw': parsed_data  # Include all the raw network data for frontend processing
                }
                
                devices_network[device_id] = network_record
                logger.info(f"Processed network data for device {display_name} ({serial_number})")
                
            except Exception as e:
                logger.warning(f"Could not parse network data for device {device_id}: {e}")
                continue
        
        network_list = list(devices_network.values())
        logger.info(f"Successfully processed {len(network_list)} network records")
        return network_list
        
    except Exception as e:
        logger.error(f"Error getting network data: {e}", exc_info=True)
        return []

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Network data endpoint
    """
    try:
        logger.info("Network data endpoint called")
        
        network_data = get_network_data_sync()

        if network_data:
            return func.HttpResponse(
                json.dumps(network_data, indent=2),
                status_code=200,
                mimetype="application/json",
                headers={
                    'X-Data-Source': 'azure-functions-database',
                    'X-Records-Count': str(len(network_data))
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
        logger.error(f"Critical error in network data endpoint: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({'error': f'Critical error: {str(e)}'}, indent=2),
            status_code=500,
            mimetype="application/json"
        )
