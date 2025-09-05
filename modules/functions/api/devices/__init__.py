"""
Devices List Endpoint for ReportMate - ULTRA-FAST VERSION
Returns basic device summaries only. For full device details (modules, events, etc.), 
use the single device endpoint (/device/{id}).

Performance optimizations:
- Single bulk query for device names 
- Removes per-device module counting
- Removes per-device event counting
- Uses PostgreSQL JSONB queries for faster name extraction
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
    """List devices using MINIMAL queries for performance"""
    try:
        logger.info("Starting FAST devices list query")
        db_manager = SyncDatabaseManager()
        
        # Test database connection first
        if not db_manager.test_connection():
            logger.warning("Database connection test failed")
            raise Exception("Database connection failed")
        
        # ULTRA-FAST: Get basic device info only
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
        
        logger.info("Executing FAST devices query...")
        devices_raw = db_manager.execute_query(query)
        logger.info(f"Got {len(devices_raw)} raw device records")
        
        if not devices_raw:
            logger.warning("No devices found in database")
            raise Exception("No devices found")
        
        # FAST: Get all device names in ONE query using bulk lookup
        device_ids = [row.get('device_id') for row in devices_raw]
        device_names = {}
        
        try:
            # Bulk query for device names from inventory
            if device_ids:
                placeholders = ','.join(['%s'] * len(device_ids))
                bulk_inventory_query = f"""
                    SELECT DISTINCT ON (device_id) 
                        device_id,
                        data->'deviceName' as device_name,
                        data->'computerName' as computer_name,
                        data->'hostname' as hostname
                    FROM inventory 
                    WHERE device_id IN ({placeholders})
                    ORDER BY device_id, collected_at DESC
                """
                inventory_results = db_manager.execute_query(bulk_inventory_query, device_ids)
                
                for result in inventory_results:
                    device_id = result.get('device_id')
                    name = (
                        result.get('device_name') or 
                        result.get('computer_name') or 
                        result.get('hostname') or 
                        device_id
                    )
                    if name and name != 'null':
                        device_names[device_id] = name
                        
                logger.info(f"Bulk loaded {len(device_names)} device names")
        except Exception as e:
            logger.warning(f"Bulk device name lookup failed: {e}")
        
        # FAST: Process devices with minimal computation
        devices = []
        for row in devices_raw:
            device_id = row.get('device_id', 'unknown')
            serial_number = row.get('serial_number', 'Unknown Serial')
            os_version = row.get('os_version', 'Unknown OS')
            last_seen = row.get('last_seen')
            created_at = row.get('created_at')
            
            # Use bulk-loaded name or fallback
            device_name = device_names.get(device_id, serial_number)
            
            # FAST: Simple status calculation
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
                'createdAt': created_at.isoformat() if created_at else None,
                # Removed heavy computations:
                # - No individual module counts (use single device endpoint for details)
                # - No event counts (use single device endpoint for details)
                # - No module availability checks (use single device endpoint for details)
                'hasData': True  # Simple flag indicating device has data
            }
            devices.append(device)
        
        logger.info(f"FAST processing completed for {len(devices)} devices")
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        
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
