"""
GET /api/v1/applications - Global Applications Endpoint
Retrieves application inventory across all devices in the fleet
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/v1/applications
    Retrieve application inventory across all devices
    """
    
    logger.info("=== GLOBAL APPLICATIONS REQUEST ===")
    
    try:
        # Get query parameters
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        search = req.params.get('search', '')
        category = req.params.get('category', '')
        publisher = req.params.get('publisher', '')
        sort_by = req.params.get('sort_by', 'name')  # name, install_count, devices
        sort_order = req.params.get('sort_order', 'asc')  # asc, desc
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get global applications data
        applications_data = await get_global_applications(
            db_manager, limit, offset, search, category, publisher, sort_by, sort_order
        )
        
        return func.HttpResponse(
            json.dumps(applications_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in global applications endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_global_applications(
    db_manager: DatabaseManager, 
    limit: int, 
    offset: int,
    search: str = '',
    category: str = '',
    publisher: str = '',
    sort_by: str = 'name',
    sort_order: str = 'asc'
) -> Dict[str, Any]:
    """
    Retrieve applications data across all devices with filtering, pagination and sorting
    """
    
    try:
        # Get aggregated applications data from database
        applications = await db_manager.get_global_applications(
            limit, offset, search, category, publisher, sort_by, sort_order
        )
        
        # Get total count for pagination
        total_count = await db_manager.get_global_applications_count(
            search, category, publisher
        )
        
        # Calculate fleet-wide application statistics
        stats = await calculate_global_application_stats(db_manager)
        
        # Get top applications and publishers
        insights = await get_application_insights(db_manager)
        
        return {
            'success': True,
            'applications': applications,
            'stats': stats,
            'insights': insights,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'search': search,
                'category': category,
                'publisher': publisher,
                'sort_by': sort_by,
                'sort_order': sort_order
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving global applications: {e}")
        return {
            'success': False,
            'error': 'Failed to retrieve applications',
            'details': str(e)
        }

async def calculate_global_application_stats(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Calculate fleet-wide application statistics
    """
    
    try:
        stats = await db_manager.get_application_fleet_stats()
        
        return {
            'total_applications': stats.get('total_unique_apps', 0),
            'total_installations': stats.get('total_installations', 0),
            'unique_publishers': stats.get('unique_publishers', 0),
            'categories': stats.get('categories', {}),
            'average_apps_per_device': stats.get('avg_apps_per_device', 0),
            'most_common_apps': stats.get('most_common_apps', []),
            'security_status': {
                'outdated_apps': stats.get('outdated_apps', 0),
                'vulnerable_apps': stats.get('vulnerable_apps', 0),
                'unlicensed_apps': stats.get('unlicensed_apps', 0)
            },
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
    except Exception as e:
        logger.error(f"Error calculating application stats: {e}")
        return {}

async def get_application_insights(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Get application insights and recommendations
    """
    
    try:
        insights = await db_manager.get_application_insights()
        
        return {
            'trending_apps': insights.get('trending_apps', []),
            'compliance_issues': insights.get('compliance_issues', []),
            'license_optimization': insights.get('license_optimization', []),
            'security_recommendations': insights.get('security_recommendations', []),
            'deployment_opportunities': insights.get('deployment_opportunities', [])
        }
    except Exception as e:
        logger.error(f"Error getting application insights: {e}")
        return {}
