"""
Simple Events List Endpoint
Returns events from the device_events table
"""
import logging
import json
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple events endpoint that returns mock data until database is available
    """
    
    try:
        # Check authentication
        api_passphrase = req.headers.get('X-API-PASSPHRASE')
        expected_passphrase = os.environ.get('API_PASSPHRASE', 's3cur3-p@ssphras3!')
        
        if api_passphrase != expected_passphrase:
            logger.warning('Invalid API passphrase provided')
            return func.HttpResponse(
                json.dumps({'error': 'Invalid API passphrase'}),
                status_code=401,
                headers={'Content-Type': 'application/json'}
            )

        # For now, return mock data until database connectivity is resolved
        # In production, this would query the device_events table
        mock_events = [
            {
                "id": "event-001",
                "device": "bc8adf50-74b3-4a75-a29e-ff7cf5b0e4a8", 
                "kind": "info",
                "ts": "2025-07-21T02:00:00Z",
                "payload": {
                    "message": "Device registration successful",
                    "module": "registration",
                    "status": "completed"
                }
            },
            {
                "id": "event-002", 
                "device": "bc8adf50-74b3-4a75-a29e-ff7cf5b0e4a8",
                "kind": "success",
                "ts": "2025-07-21T02:05:00Z", 
                "payload": {
                    "message": "System health check passed",
                    "module": "health",
                    "cpu_usage": "15%",
                    "memory_usage": "45%"
                }
            }
        ]
        
        # Filter by device if requested
        device_id = req.params.get('device_id')
        if device_id:
            mock_events = [e for e in mock_events if e['device'] == device_id]
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'events': mock_events,
                'count': len(mock_events),
                'source': 'mock_data',
                'note': 'Using mock data until PostgreSQL connectivity is resolved'
            }, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in events endpoint: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }, indent=2),
            status_code=500,
            mimetype="application/json"
        )
