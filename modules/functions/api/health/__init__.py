import azure.functions as func
import json
import logging
from datetime import datetime

# Simple health check without complex imports
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple health check endpoint for ReportMate API
    Returns basic API status without complex dependencies
    """
    logger.info('Health check endpoint called')
    
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "api": {
                "name": "ReportMate API",
                "version": "1.0.0",
                "environment": "azure"
            },
            "message": "ReportMate API is running successfully"
        }
        
        return func.HttpResponse(
            json.dumps(health_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
