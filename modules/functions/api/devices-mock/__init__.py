import logging
import azure.functions as func
import json
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Testing HTTP-based database access')
    
    try:
        # Since PostgreSQL drivers aren't available, let's return mock data
        # This will allow us to test the full pipeline while we resolve driver issues
        
        # Mock device data - only the actual reporting device
        mock_devices = [
            {
                "id": 1,
                "device_id": "bc8adf50-74b3-4a75-a29e-ff7cf5b0e4a8",
                "serial_number": "0F33V9G25083HJ",
                "hostname": "DESKTOP-RCHRISTIANSEN",
                "os_name": "Microsoft Windows 11 Pro",
                "os_version": "10.0.22631",
                "last_seen": "2025-07-21T02:00:00Z",
                "status": "active"
            }
        ]
        
        # Get specific device if requested
        device_id = req.params.get('device_id')
        serial_number = req.params.get('serial_number')
        
        if device_id or serial_number:
            # Return specific device
            for device in mock_devices:
                if (device_id and device['device_id'] == device_id) or \
                   (serial_number and device['serial_number'] == serial_number):
                    return func.HttpResponse(
                        json.dumps({
                            'success': True,
                            'device': device,
                            'source': 'mock_data'
                        }, indent=2),
                        status_code=200,
                        mimetype="application/json"
                    )
            
            # Device not found
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device not found',
                    'device_id': device_id,
                    'serial_number': serial_number
                }, indent=2),
                status_code=404,
                mimetype="application/json"
            )
        else:
            # Return all devices
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'devices': mock_devices,
                    'count': len(mock_devices),
                    'source': 'mock_data',
                    'note': 'Using mock data until PostgreSQL driver issue is resolved'
                }, indent=2),
                status_code=200,
                mimetype="application/json"
            )
        
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e)
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
