import azure.functions as func
import json
import logging
import sys
import os

logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Test import chain to isolate the import issue"""
    
    try:
        # Add the parent directory to the path for imports
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Test imports step by step
        logger.info(f"Python path: {sys.path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Parent directory: {parent_dir}")
        
        try:
            from shared.base_processor import BaseModuleProcessor
            logger.info("✓ Successfully imported BaseModuleProcessor")
        except Exception as e:
            logger.error(f"✗ Failed to import BaseModuleProcessor: {e}")
            return func.HttpResponse(f"Failed to import BaseModuleProcessor: {e}", status_code=500)
        
        try:
            from processor import DeviceDataProcessor
            logger.info("✓ Successfully imported DeviceDataProcessor")
        except Exception as e:
            logger.error(f"✗ Failed to import DeviceDataProcessor: {e}")
            return func.HttpResponse(f"Failed to import DeviceDataProcessor: {e}", status_code=500)
        
        return func.HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'All imports successful',
                'python_path': sys.path,
                'cwd': os.getcwd(),
                'parent_dir': parent_dir
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.exception(f"Test import failed: {e}")
        return func.HttpResponse(
            json.dumps({
                'status': 'error',
                'error': str(e),
                'python_path': sys.path,
                'cwd': os.getcwd()
            }),
            status_code=500,
            mimetype="application/json"
        )
