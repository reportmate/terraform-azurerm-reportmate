import logging
import azure.functions as func
import json
import os
import hashlib
import hmac
import base64
import time
from urllib.parse import quote

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Functions endpoint for SignalR client negotiation.
    This endpoint provides clients with connection information for Azure Web PubSub.
    """
    logging.info('SignalR negotiate function processed a request.')
    
    try:
        # Get Web PubSub connection string from environment
        connection_string = os.environ.get('EVENTS_CONNECTION')
        if not connection_string:
            logging.error('EVENTS_CONNECTION not found in environment variables')
            return func.HttpResponse(
                json.dumps({'error': 'Web PubSub not configured'}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse connection string
        parts = {}
        for part in connection_string.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                parts[key] = value
        
        endpoint = parts.get('Endpoint', '')
        access_key = parts.get('AccessKey', '')
        
        if not endpoint or not access_key:
            logging.error('Invalid connection string format')
            return func.HttpResponse(
                json.dumps({'error': 'Invalid Web PubSub configuration'}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Extract user information and device type from request
        user_id = req.headers.get('x-user-id', 'anonymous')
        device_type = req.params.get('device', 'client')  # Handle the device parameter
        
        hub_name = 'reportmate'
        
        # Generate access token for Web PubSub
        audience = f"{endpoint}/client/hubs/{hub_name}"
        exp = int(time.time()) + 3600  # Token valid for 1 hour
        
        # Create token payload with device info
        payload = {
            "aud": audience,
            "iat": int(time.time()),
            "exp": exp,
            "sub": user_id,
            "device": device_type  # Include device type in token
        }
        
        # Create JWT header
        header = {
            "typ": "JWT",
            "alg": "HS256"
        }
        
        # Encode JWT parts
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Create signature
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            base64.b64decode(access_key + '=='),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        # Complete JWT token
        access_token = f"{message}.{signature_b64}"
        
        # Create connection info
        connection_info = {
            'url': f"{endpoint}/client/hubs/{hub_name}",
            'accessToken': access_token
        }
        
        logging.info(f'Providing SignalR connection for user: {user_id}, device: {device_type}')
        
        return func.HttpResponse(
            json.dumps(connection_info),
            status_code=200,
            mimetype="application/json",
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-user-id'
            }
        )
        
    except Exception as e:
        logging.error(f'Error in negotiate function: {str(e)}')
        return func.HttpResponse(
            json.dumps({'error': f'Failed to negotiate SignalR connection: {str(e)}'}),
            status_code=500,
            mimetype="application/json"
        )
