"""
POST /api/v1/ingest - Enhanced Device Data Ingestion Endpoint
Processes comprehensive device telemetry data through modular processors
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from device_processor import DeviceDataProcessor
from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main entry point for device data ingestion
    
    Expects JSON payload with:
    - device_data: Complete device telemetry
    - machine_group_passphrase: Authentication token
    """
    
    logger.info("=== DEVICE DATA INGESTION REQUEST ===")
    
    try:
        # Parse request body
        try:
            request_data = req.get_json()
            if not request_data:
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid JSON payload',
                        'details': 'Request body must contain valid JSON'
                    }),
                    status_code=400,
                    mimetype="application/json"
                )
        except ValueError as e:
            logger.error(f"JSON parsing error: {e}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'JSON parsing failed',
                    'details': str(e)
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Extract required fields
        device_data = request_data.get('device_data') or request_data.get('payload')
        machine_group_passphrase = request_data.get('machine_group_passphrase') or request_data.get('passphrase', '')
        
        if not device_data:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Missing device data',
                    'details': 'Request must include device_data or payload field'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Processing device data with {len(device_data)} top-level modules")
        logger.info(f"Available modules: {list(device_data.keys())}")
        
        # Initialize managers
        db_manager = DatabaseManager()
        auth_manager = AuthenticationManager()
        
        # Initialize processor
        processor = DeviceDataProcessor(db_manager, auth_manager)
        
        # Process the device data
        result = await processor.process_device_data(device_data, machine_group_passphrase)
        
        # Log processing results
        if result['success']:
            logger.info(f"✅ Successfully processed device {result.get('device_id', 'unknown')}")
            logger.info(f"Modules processed: {result.get('modules_processed', 0)}")
            logger.info(f"Modules failed: {result.get('modules_failed', 0)}")
        else:
            logger.error(f"❌ Processing failed: {result.get('error', 'unknown error')}")
        
        # Return result
        status_code = 200 if result['success'] else 400
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=status_code,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in ingest endpoint: {e}", exc_info=True)
        
        error_response = {
            'success': False,
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache'
            }
        )