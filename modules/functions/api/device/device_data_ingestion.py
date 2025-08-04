"""
Enhanced Device Data Ingestion Endpoint for ReportMate
This endpoint uses the full DeviceDataProcessor to handle complete device data processing
including all modules (installs, hardware, system, etc.)
"""

import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import DeviceDataProcessor
from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

logger = logging.getLogger(__name__)

async def handle_device_data_ingestion(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle complete device data ingestion from Windows client
    Uses DeviceDataProcessor to process all modules including installs
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"[{timestamp}] === DEVICE DATA INGESTION API ===")
    
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
        logger.info(f"Parsed device data. Top-level keys: {list(device_data.keys())}")
        
        # Check for authentication passphrase
        passphrase = device_data.get('passphrase') or device_data.get('Passphrase') or req.headers.get('X-API-PASSPHRASE')
        if not passphrase:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Authentication required',
                    'details': 'API passphrase is required for device data ingestion'
                }),
                status_code=401,
                mimetype="application/json"
            )
        
        # Extract device identification for logging
        serial_number = None
        device_id = None
        
        # Try to extract from various possible locations in the payload
        if 'payload' in device_data and device_data['payload']:
            payload = device_data['payload']
            if 'device' in payload and payload['device']:
                device_dict = payload['device']
                serial_number = device_dict.get('serialNumber') or device_dict.get('SerialNumber')
                device_id = device_dict.get('deviceId') or device_dict.get('DeviceId')
        
        # Fallback to top-level fields
        if not serial_number:
            serial_number = device_data.get('serialNumber') or device_data.get('SerialNumber') or device_data.get('device')
        if not device_id:
            device_id = device_data.get('deviceId') or device_data.get('DeviceId')
        
        logger.info(f"Processing device data - Serial: {serial_number}, DeviceId: {device_id}")
        
        # Initialize database and authentication managers
        db_manager = DatabaseManager()
        auth_manager = AuthenticationManager()
        
        # Initialize the device data processor
        processor = DeviceDataProcessor(db_manager, auth_manager)
        
        # Process the device data through all module processors
        if serial_number:
            # Use the process_device_data_with_device_id method for explicit device identification
            logger.info(f"Processing with explicit device_id: {serial_number}")
            result = await processor.process_device_data_with_device_id(
                device_data, 
                passphrase, 
                serial_number
            )
        else:
            # Use the standard process_device_data method
            logger.info("Processing with automatic device identification")
            result = await processor.process_device_data(device_data, passphrase)
        
        if result['success']:
            logger.info(f"✅ Device data processing completed successfully")
            logger.info(f"   Device ID: {result.get('device_id', 'Unknown')}")
            logger.info(f"   Modules processed: {result.get('modules_processed', 0)}")
            logger.info(f"   Modules failed: {result.get('modules_failed', 0)}")
            
            if result.get('processing_errors'):
                logger.warning(f"Processing errors encountered: {result['processing_errors']}")
            
            # Return success response
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Device data processed successfully',
                    'device_id': result.get('device_id'),
                    'modules_processed': result.get('modules_processed', 0),
                    'modules_failed': result.get('modules_failed', 0),
                    'timestamp': timestamp,
                    'processing_summary': result.get('summary', {}),
                    'storage_result': result.get('storage_result', {})
                }),
                status_code=200,
                mimetype="application/json"
            )
        else:
            logger.error(f"❌ Device data processing failed: {result.get('error', 'Unknown error')}")
            logger.error(f"   Details: {result.get('details', 'No details provided')}")
            
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': result.get('error', 'Processing failed'),
                    'details': result.get('details', 'Unknown error during processing'),
                    'timestamp': timestamp
                }),
                status_code=500,
                mimetype="application/json"
            )
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Invalid JSON format',
                'details': str(e),
                'timestamp': timestamp
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during device data ingestion: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e),
                'timestamp': timestamp
            }),
            status_code=500,
            mimetype="application/json"
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main entry point for the enhanced device data ingestion API"""
    if req.method == 'POST':
        # Use async handler for POST requests (device data ingestion)
        import asyncio
        return asyncio.run(handle_device_data_ingestion(req))
    elif req.method == 'GET':
        # Keep the existing device lookup functionality for GET requests
        from . import handle_device_lookup
        return handle_device_lookup(req)
    else:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Use POST for device data ingestion or GET for device lookup.'
            }),
            status_code=405,
            mimetype="application/json"
        )
