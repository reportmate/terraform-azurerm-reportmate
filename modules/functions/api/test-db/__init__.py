"""
Simple database test endpoint
"""
import logging
import json
import azure.functions as func
import os

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test basic imports and environment
    """
    
    try:
        # Test DATABASE_URL
        db_url = os.getenv('DATABASE_URL')
        db_url_present = bool(db_url)
        
        # Test psycopg2 import
        try:
            import psycopg2
            psycopg2_available = True
            psycopg2_version = psycopg2.__version__
        except Exception as e:
            psycopg2_available = False
            psycopg2_version = f"Error: {str(e)}"
        
        # Test asyncpg import
        try:
            import asyncpg
            asyncpg_available = True
            asyncpg_version = asyncpg.__version__
        except Exception as e:
            asyncpg_available = False
            asyncpg_version = f"Error: {str(e)}"
        
        # Test SyncDatabaseManager import
        sync_db_available = False
        sync_db_error = "Not tested"
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from shared.sync_database import SyncDatabaseManager
            db_manager = SyncDatabaseManager()
            sync_db_available = True
            sync_db_error = f"Success - using {db_manager.driver} driver"
        except Exception as e:
            sync_db_error = str(e)
        
        # Test basic connection with psycopg2 directly
        connection_test = "Not attempted"
        if psycopg2_available and db_url:
            try:
                import psycopg2
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                connection_test = f"Success: {result}"
            except Exception as e:
                connection_test = f"Failed: {str(e)}"
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Basic test successful',
                'database_url_present': db_url_present,
                'database_url_preview': db_url[:50] + "..." if db_url else None,
                'psycopg2_available': psycopg2_available,
                'psycopg2_version': psycopg2_version,
                'asyncpg_available': asyncpg_available,
                'asyncpg_version': asyncpg_version,
                'sync_db_available': sync_db_available,
                'sync_db_error': sync_db_error,
                'connection_test': connection_test
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }),
            status_code=500,
            mimetype="application/json"
        )
