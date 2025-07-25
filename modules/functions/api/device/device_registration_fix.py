import azure.functions as func
import json
import logging
import pg8000
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def handle_device_registration(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle device registration requests from Windows client
    """
    logger.info("=== DEVICE REGISTRATION API ===")
    
    try:
        # Get request body
        req_body = req.get_body()
        if not req_body:
            logger.warning("Empty request body received")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Empty request body',
                    'message': 'No data received'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Decode and parse JSON
        body_str = req_body.decode('utf-8')
        logger.info(f"Request body size: {len(body_str)} characters")
        
        device_data = json.loads(body_str)
        logger.info(f"Parsed device data. Keys: {list(device_data.keys())}")
        
        # Extract registration data from Windows client
        device_id = device_data.get('device', '') or device_data.get('deviceId', '')
        serial_number = device_data.get('serialNumber', '') or device_data.get('SerialNumber', '')
        computer_name = device_data.get('computerName', '') or device_data.get('ComputerName', '')
        model = device_data.get('model', '') or device_data.get('Model', '')
        os_name = device_data.get('os', '') or device_data.get('OperatingSystem', '')
        manufacturer = device_data.get('manufacturer', '') or device_data.get('Manufacturer', '')
        
        logger.info(f"Registration data: device_id={device_id}, serial={serial_number}, name={computer_name}")
        
        # Validate required fields
        if not device_id or not serial_number:
            missing_fields = []
            if not device_id:
                missing_fields.append('deviceId')
            if not serial_number:
                missing_fields.append('serialNumber')
            
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Both deviceId and serialNumber are required for device registration',
                    'details': f'Missing fields: {", ".join(missing_fields)}'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Database connection parameters
        conn_params = {
            'host': os.environ.get('DB_HOST'),
            'database': os.environ.get('DB_NAME'), 
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'port': int(os.environ.get('DB_PORT', 5432))
        }
        
        try:
            # Connect to database
            conn = pg8000.connect(**conn_params)
            cursor = conn.cursor()
            current_time = datetime.utcnow()
            
            # Log the values being inserted for debugging
            logger.info(f"Inserting device registration:")
            logger.info(f"  id (serial_number): '{serial_number}'")
            logger.info(f"  device_id: '{device_id}'")
            logger.info(f"  name: '{computer_name}'")
            logger.info(f"  serial_number: '{serial_number}'")
            logger.info(f"  os: '{os_name}'")
            logger.info(f"  model: '{model}'")
            logger.info(f"  manufacturer: '{manufacturer}'")
            
            # Use UPSERT with comprehensive conflict handling
            device_query = """
                INSERT INTO devices (
                    id, device_id, name, serial_number, os, status, last_seen, 
                    model, manufacturer, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) 
                DO UPDATE SET 
                    device_id = EXCLUDED.device_id,
                    name = EXCLUDED.name,
                    os = EXCLUDED.os,
                    model = EXCLUDED.model,
                    manufacturer = EXCLUDED.manufacturer,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at,
                    status = EXCLUDED.status
            """
            
            cursor.execute(device_query, (
                serial_number,      # id (serial number as primary key)
                device_id,          # device_id (ReportMate internal UUID)
                computer_name,      # name
                serial_number,      # serial_number (same as id)
                os_name,           # os
                'active',          # status
                current_time,      # last_seen
                model,             # model
                manufacturer,      # manufacturer
                current_time,      # created_at
                current_time       # updated_at
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Device {serial_number} registered successfully")
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Device registered successfully',
                    'deviceId': device_id,
                    'serialNumber': serial_number,
                    'registered_at': current_time.isoformat()
                }),
                status_code=200,
                mimetype="application/json"
            )
            
        except Exception as reg_error:
            logger.error(f"❌ Device registration failed: {reg_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device registration failed',
                    'details': str(reg_error)
                }),
                status_code=500,
                mimetype="application/json"
            )
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Invalid JSON format',
                'details': str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in device registration: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main entry point for the device registration API"""
    if req.method == 'POST':
        return handle_device_registration(req)
    else:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Use POST for device registration.'
            }),
            status_code=405,
            mimetype="application/json"
        )
