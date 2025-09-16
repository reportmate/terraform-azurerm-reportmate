import azure.functions as func
import json
import logging
import os
import sys

# Add the parent directory to the path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Device API with database lookup for installs module data"""
    try:
        logger.info("Device API called with database lookup")
        
        serial_number = req.route_params.get('serial_number')
        if not serial_number:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Serial number required'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Looking up device: {serial_number}")
        
        # Test if pg8000 is available
        try:
            import pg8000
            logger.info(f"✅ pg8000 available: {pg8000.__version__}")
        except ImportError as pg_error:
            logger.error(f"❌ pg8000 not available: {pg_error}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database driver not available',
                    'details': f'pg8000 import failed: {str(pg_error)}'
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        try:
            # Import DatabaseManager
            from shared.database import DatabaseManager
            db_manager = DatabaseManager()
            
            # Test connection first
            if not db_manager.test_connection():
                logger.error("Database connection failed")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Database connection failed'
                    }),
                    status_code=500,
                    mimetype="application/json"
                )
            
            # Look up device
            device_query = """
                SELECT id, device_id, serial_number, last_seen, client_version, created_at
                FROM devices 
                WHERE id = %s OR serial_number = %s
                LIMIT 1
            """
            
            device_result = db_manager.execute_query(device_query, (serial_number, serial_number))
            
            if not device_result:
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Device not found',
                        'details': f'No device found with serial: {serial_number}'
                    }),
                    status_code=404,
                    mimetype="application/json"
                )
            
            device_row = device_result[0]
            logger.info(f"Found device: {device_row['id']}")
            
            # Get all module data
            modules_data = {}
            
            # List of all module tables
            module_tables = [
                'installs', 'applications', 'hardware', 'inventory', 
                'system', 'network', 'security', 'management', 
                'profiles', 'displays', 'printers'
            ]
            
            for module_name in module_tables:
                try:
                    module_query = f"""
                        SELECT data, collected_at
                        FROM {module_name} 
                        WHERE device_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    
                    module_result = db_manager.execute_query(module_query, (device_row['id'],))
                    
                    if module_result and module_result[0].get('data'):
                        modules_data[module_name] = module_result[0]['data']
                        logger.info(f"✅ Found {module_name} data")
                        
                        # Special logging for installs module
                        if module_name == 'installs':
                            module_data = module_result[0]['data']
                            if isinstance(module_data, dict):
                                cimian_data = module_data.get('cimian', {})
                                if 'items' in cimian_data:
                                    items = cimian_data['items']
                                    logger.info(f"🔍 Found {len(items)} install items")
                                    # Count statuses for verification
                                    statuses = {}
                                    for item in items:
                                        status = item.get('currentStatus', 'unknown')
                                        statuses[status] = statuses.get(status, 0) + 1
                                    logger.info(f"📊 Install statuses: {statuses}")
                    else:
                        logger.info(f"⚠️ No {module_name} data found")
                        
                except Exception as module_error:
                    logger.warning(f"⚠️ Error querying {module_name}: {module_error}")
                    continue
            
            # Return response
            response_data = {
                'success': True,
                'device': {
                    'deviceId': device_row['device_id'],
                    'serialNumber': device_row['serial_number'],
                    'lastSeen': device_row['last_seen'].isoformat() if device_row.get('last_seen') and hasattr(device_row['last_seen'], 'isoformat') else str(device_row.get('last_seen')) if device_row.get('last_seen') else None,
                    'createdAt': device_row['created_at'].isoformat() if device_row.get('created_at') and hasattr(device_row['created_at'], 'isoformat') else str(device_row.get('created_at')) if device_row.get('created_at') else None,
                    'clientVersion': device_row.get('client_version'),
                    'modules': modules_data
                }
            }
            
            logger.info(f"✅ Device lookup successful - returning {len(modules_data)} modules: {list(modules_data.keys())}")
            
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=200,
                mimetype="application/json"
            )
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database lookup failed',
                    'details': str(db_error)
                }),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Error in device API: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
