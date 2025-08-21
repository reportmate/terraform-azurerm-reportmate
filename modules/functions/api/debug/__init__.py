"""
Debug endpoint to test database connection and environment variables
"""
import azure.functions as func
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Debug endpoint to check database connection and environment"""
    
    try:
        logger.info("Debug endpoint called")
        
        # Check environment variables
        database_url = os.getenv('DATABASE_URL')
        database_connection_string = os.getenv('DATABASE_CONNECTION_STRING')
        client_passphrases = os.getenv('CLIENT_PASSPHRASES')
        functions_worker_runtime = os.getenv('FUNCTIONS_WORKER_RUNTIME')
        
        # Check available Python packages
        available_drivers = []
        import_errors = []
        
        try:
            import psycopg2
            available_drivers.append('psycopg2')
        except ImportError as e:
            import_errors.append(f'psycopg2: {str(e)}')
        
        try:
            import pg8000
            available_drivers.append('pg8000')
        except ImportError as e:
            import_errors.append(f'pg8000: {str(e)}')
        
        try:
            import asyncpg
            available_drivers.append('asyncpg')
        except ImportError as e:
            import_errors.append(f'asyncpg: {str(e)}')
        
        # Test database connection
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
            from shared.database import SyncDatabaseManager
            db_manager = SyncDatabaseManager()
            
            connection_test = db_manager.test_connection()
            driver_info = db_manager.driver
            
        except Exception as e:
            connection_test = False
            driver_info = f"Error: {str(e)}"
        
        debug_info = {
            'environment_variables': {
                'DATABASE_URL': 'SET' if database_url else 'NOT SET',
                'DATABASE_CONNECTION_STRING': 'SET' if database_connection_string else 'NOT SET',
                'CLIENT_PASSPHRASES': 'SET' if client_passphrases else 'NOT SET',
                'FUNCTIONS_WORKER_RUNTIME': functions_worker_runtime or 'NOT SET'
            },
            'database_url_preview': database_url[:50] + '...' if database_url else 'None',
            'available_drivers': available_drivers,
            'import_errors': import_errors,
            'database_connection_test': connection_test,
            'database_driver': driver_info,
            'python_version': sys.version,
            'working_directory': os.getcwd()
        }
        
        return func.HttpResponse(
            json.dumps(debug_info, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.exception(f"Debug endpoint error: {e}")
        return func.HttpResponse(
            json.dumps({
                'error': str(e),
                'type': type(e).__name__
            }),
            status_code=500,
            mimetype="application/json"
        )
