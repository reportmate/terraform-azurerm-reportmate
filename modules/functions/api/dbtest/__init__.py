import azure.functions as func
import json
import logging
import os

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Simple database test function"""
    try:
        logger.info("Database test function called")
        
        # Test 1: Check if pg8000 is available
        try:
            import pg8000
            pg8000_status = "✅ Available"
        except ImportError as e:
            pg8000_status = f"❌ Not available: {e}"
        
        # Test 2: Check environment variables
        database_url = os.environ.get('DATABASE_URL', 'Not set')
        
        # Test 3: Try basic database connection with pg8000
        connection_test = "Not tested"
        if 'postgresql://' in database_url:
            try:
                import re
                url_pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)'
                match = re.match(url_pattern, database_url)
                if match:
                    db_user, db_password, db_host, db_port, db_name = match.groups()
                    conn_params = {
                        'host': db_host,
                        'database': db_name,
                        'user': db_user,
                        'password': db_password,
                        'port': int(db_port),
                        'ssl_context': True
                    }
                    
                    import pg8000
                    conn = pg8000.connect(**conn_params)
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    connection_test = f"✅ Success: {result}"
                else:
                    connection_test = "❌ Failed to parse DATABASE_URL"
            except Exception as e:
                connection_test = f"❌ Connection failed: {e}"
        
        return func.HttpResponse(
            json.dumps({
                'pg8000_status': pg8000_status,
                'database_url_available': 'Yes' if database_url != 'Not set' else 'No',
                'database_url_masked': database_url[:30] + '...' if len(database_url) > 30 else database_url,
                'connection_test': connection_test
            }, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return func.HttpResponse(
            json.dumps({
                'error': str(e),
                'test_status': 'failed'
            }),
            status_code=500,
            mimetype="application/json"
        )
