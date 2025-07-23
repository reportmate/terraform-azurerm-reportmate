import azure.functions as func
import json
import logging
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test pg8000 directly
    """
    
    try:
        # Test pg8000 import
        try:
            import pg8000
            pg8000_status = f"SUCCESS - pg8000 {pg8000.__version__} is available"
        except Exception as e:
            pg8000_status = f"FAILED - {str(e)}"
        
        # Test database connection
        db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_CONNECTION_STRING')
        db_connection_test = "Not attempted"
        
        if db_url and 'pg8000' in pg8000_status:
            try:
                from urllib.parse import urlparse
                
                parsed = urlparse(db_url)
                db_config = {
                    'host': parsed.hostname,
                    'port': parsed.port or 5432,
                    'database': parsed.path.lstrip('/'),
                    'user': parsed.username,
                    'password': parsed.password
                }
                
                # Try to connect
                conn = pg8000.connect(**db_config)
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    result = cursor.fetchone()
                    db_connection_test = f"SUCCESS - Connected to {result[0][:50]}..."
                conn.close()
                
            except Exception as e:
                db_connection_test = f"FAILED - {str(e)}"
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'pg8000_status': pg8000_status,
                'db_url_present': bool(db_url),
                'db_connection_test': db_connection_test
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
