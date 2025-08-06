"""
Applications Module Endpoint for ReportMate
Serves applications data for all devices
"""
import logging
import json
import asyncio
import azure.functions as func
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import AsyncDatabaseManager

logger = logging.getLogger(__name__)

async def get_applications_data_async():
    """Get applications data using async database connection"""
    try:
        db_manager = AsyncDatabaseManager()
        
        # Query to get all applications data
        query = """
            SELECT 
                device_id,
                data,
                collected_at,
                created_at,
                updated_at
            FROM applications
            ORDER BY collected_at DESC
        """
        
        applications_raw = await db_manager.execute_query(query)
        
        applications = []
        for row in applications_raw:
            try:
                # Handle different result formats from pg8000 vs psycopg2
                if isinstance(row, dict):
                    # Dict format (psycopg2)
                    device_id_val = row['device_id']
                    data_val = row['data'] 
                    collected_at_val = row['collected_at']
                    created_at_val = row['created_at']
                    updated_at_val = row['updated_at']
                else:
                    # Tuple format (pg8000)
                    device_id_val = row[0]
                    data_val = row[1]
                    collected_at_val = row[2]
                    created_at_val = row[3]
                    updated_at_val = row[4]
                
                applications.append({
                    'device_id': device_id_val,
                    'data': data_val,
                    'collected_at': collected_at_val.isoformat() if collected_at_val else None,
                    'created_at': created_at_val.isoformat() if created_at_val else None,
                    'updated_at': updated_at_val.isoformat() if updated_at_val else None
                })
                
            except Exception as row_error:
                logger.error(f"Error processing row: {row_error}, row type: {type(row)}, row: {str(row)[:200]}")
                continue
        
        logger.info(f"Successfully retrieved applications data for {len(applications)} devices")
        return applications
        
    except Exception as e:
        logger.error(f"Error retrieving applications data: {str(e)}")
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main entry point for applications endpoint"""
    logger.info('Applications endpoint triggered')
    
    try:
        # Get applications data
        applications_data = asyncio.run(get_applications_data_async())
        
        return func.HttpResponse(
            json.dumps(applications_data, default=str),
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
        
    except Exception as e:
        logger.error(f"Applications endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": f"Failed to retrieve applications data: {str(e)}"
            }),
            status_code=500,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )
