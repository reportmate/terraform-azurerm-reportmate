"""
GET /api/v1/hardware - Global Hardware Endpoint
Retrieves hardware inventory across all devices in the fleet
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
    GET /api/v1/hardware
    Retrieve hardware inventory across all devices
    """
    
    logger.info("=== GLOBAL HARDWARE REQUEST ===")
    
    try:
        # Get query parameters
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        manufacturer = req.params.get('manufacturer', '')
        model = req.params.get('model', '')
        sort_by = req.params.get('sort_by', 'device_count')  # device_count, manufacturer, model
        sort_order = req.params.get('sort_order', 'desc')  # asc, desc
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get global hardware data
        hardware_data = await get_global_hardware(
            db_manager, limit, offset, manufacturer, model, sort_by, sort_order
        )
        
        return func.HttpResponse(
            json.dumps(hardware_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in global hardware endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_global_hardware(
    db_manager: DatabaseManager, 
    limit: int, 
    offset: int,
    manufacturer: str = '',
    model: str = '',
    sort_by: str = 'device_count',
    sort_order: str = 'desc'
) -> Dict[str, Any]:
    """
    Retrieve hardware data across all devices with filtering, pagination and sorting
    """
    
    try:
        # Get aggregated hardware data from database
        hardware = await db_manager.get_global_hardware(
            limit, offset, manufacturer, model, sort_by, sort_order
        )
        
        # Get total count for pagination
        total_count = await db_manager.get_global_hardware_count(
            manufacturer, model
        )
        
        # Calculate fleet-wide hardware statistics
        stats = await calculate_global_hardware_stats(db_manager)
        
        # Get hardware insights and recommendations
        insights = await get_hardware_insights(db_manager)
        
        return {
            'success': True,
            'hardware': hardware,
            'count': len(hardware),
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'statistics': stats,
            'insights': insights,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving global hardware data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

async def calculate_global_hardware_stats(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Calculate fleet-wide hardware statistics
    """
    
    try:
        stats = await db_manager.get_hardware_statistics()
        
        return {
            'total_devices': stats.get('total_devices', 0),
            'unique_manufacturers': stats.get('unique_manufacturers', 0),
            'unique_models': stats.get('unique_models', 0),
            'average_age_years': stats.get('average_age_years', 0),
            'warranty_status': {
                'under_warranty': stats.get('under_warranty', 0),
                'warranty_expired': stats.get('warranty_expired', 0),
                'warranty_unknown': stats.get('warranty_unknown', 0)
            },
            'hardware_categories': {
                'desktop': stats.get('desktop_count', 0),
                'laptop': stats.get('laptop_count', 0),
                'server': stats.get('server_count', 0),
                'other': stats.get('other_count', 0)
            },
            'performance_distribution': {
                'high_performance': stats.get('high_performance', 0),
                'medium_performance': stats.get('medium_performance', 0),
                'low_performance': stats.get('low_performance', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating hardware statistics: {e}")
        return {}

async def get_hardware_insights(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Get hardware insights and recommendations
    """
    
    try:
        insights = await db_manager.get_hardware_insights()
        
        return {
            'fleet_health_score': insights.get('fleet_health_score', 0),
            'upgrade_recommendations': insights.get('upgrade_recommendations', []),
            'standardization_opportunities': insights.get('standardization_opportunities', []),
            'cost_optimization': insights.get('cost_optimization', []),
            'top_manufacturers': insights.get('top_manufacturers', []),
            'most_common_models': insights.get('most_common_models', []),
            'performance_bottlenecks': insights.get('performance_bottlenecks', []),
            'warranty_alerts': insights.get('warranty_alerts', [])
        }
        
    except Exception as e:
        logger.error(f"Error getting hardware insights: {e}")
        return {
            'fleet_health_score': 0,
            'upgrade_recommendations': [],
            'standardization_opportunities': [],
            'cost_optimization': [],
            'top_manufacturers': [],
            'most_common_models': [],
            'performance_bottlenecks': [],
            'warranty_alerts': []
        }
