"""
GET /api/v1/metrics - API Metrics Endpoint
Provides API performance metrics and statistics
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
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
    GET /api/v1/metrics
    Retrieve API performance metrics and statistics
    """
    
    logger.info("=== API METRICS REQUEST ===")
    
    try:
        # Get query parameters
        time_range = req.params.get('time_range', '24h')  # 1h, 6h, 24h, 7d, 30d
        include_detailed = req.params.get('include_detailed', 'false').lower() == 'true'
        endpoint_filter = req.params.get('endpoint', '')
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get API metrics data
        metrics_data = await get_api_metrics(
            db_manager, time_range, include_detailed, endpoint_filter
        )
        
        return func.HttpResponse(
            json.dumps(metrics_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in API metrics endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_api_metrics(
    db_manager: DatabaseManager,
    time_range: str,
    include_detailed: bool = False,
    endpoint_filter: str = ''
) -> Dict[str, Any]:
    """
    Retrieve comprehensive API performance metrics
    """
    
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        if time_range == '1h':
            start_time = end_time - timedelta(hours=1)
        elif time_range == '6h':
            start_time = end_time - timedelta(hours=6)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        elif time_range == '30d':
            start_time = end_time - timedelta(days=30)
        else:  # Default to 24h
            start_time = end_time - timedelta(hours=24)
        
        # Get basic metrics
        basic_metrics = await get_basic_api_metrics(db_manager, start_time, end_time, endpoint_filter)
        
        # Get performance metrics
        performance_metrics = await get_performance_metrics(db_manager, start_time, end_time, endpoint_filter)
        
        # Get error metrics
        error_metrics = await get_error_metrics(db_manager, start_time, end_time, endpoint_filter)
        
        # Get usage patterns
        usage_patterns = await get_usage_patterns(db_manager, start_time, end_time, endpoint_filter)
        
        result = {
            'success': True,
            'time_range': time_range,
            'start_time': start_time.isoformat() + 'Z',
            'end_time': end_time.isoformat() + 'Z',
            'endpoint_filter': endpoint_filter,
            'basic_metrics': basic_metrics,
            'performance_metrics': performance_metrics,
            'error_metrics': error_metrics,
            'usage_patterns': usage_patterns,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Include detailed metrics if requested
        if include_detailed:
            detailed_metrics = await get_detailed_metrics(db_manager, start_time, end_time, endpoint_filter)
            result['detailed_metrics'] = detailed_metrics
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving API metrics: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

async def get_basic_api_metrics(db_manager: DatabaseManager, start_time: datetime, end_time: datetime, endpoint_filter: str) -> Dict[str, Any]:
    """Get basic API usage metrics"""
    
    try:
        metrics = await db_manager.get_api_basic_metrics(start_time, end_time, endpoint_filter)
        
        return {
            'total_requests': metrics.get('total_requests', 0),
            'successful_requests': metrics.get('successful_requests', 0),
            'failed_requests': metrics.get('failed_requests', 0),
            'unique_clients': metrics.get('unique_clients', 0),
            'requests_per_minute': metrics.get('requests_per_minute', 0),
            'success_rate': metrics.get('success_rate', 0),
            'uptime_percentage': metrics.get('uptime_percentage', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting basic API metrics: {e}")
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'unique_clients': 0,
            'requests_per_minute': 0,
            'success_rate': 0,
            'uptime_percentage': 0
        }

async def get_performance_metrics(db_manager: DatabaseManager, start_time: datetime, end_time: datetime, endpoint_filter: str) -> Dict[str, Any]:
    """Get API performance metrics"""
    
    try:
        metrics = await db_manager.get_api_performance_metrics(start_time, end_time, endpoint_filter)
        
        return {
            'average_response_time_ms': metrics.get('average_response_time_ms', 0),
            'median_response_time_ms': metrics.get('median_response_time_ms', 0),
            'p95_response_time_ms': metrics.get('p95_response_time_ms', 0),
            'p99_response_time_ms': metrics.get('p99_response_time_ms', 0),
            'fastest_response_ms': metrics.get('fastest_response_ms', 0),
            'slowest_response_ms': metrics.get('slowest_response_ms', 0),
            'throughput_rps': metrics.get('throughput_rps', 0),
            'concurrent_connections': metrics.get('concurrent_connections', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            'average_response_time_ms': 0,
            'median_response_time_ms': 0,
            'p95_response_time_ms': 0,
            'p99_response_time_ms': 0,
            'fastest_response_ms': 0,
            'slowest_response_ms': 0,
            'throughput_rps': 0,
            'concurrent_connections': 0
        }

async def get_error_metrics(db_manager: DatabaseManager, start_time: datetime, end_time: datetime, endpoint_filter: str) -> Dict[str, Any]:
    """Get API error metrics"""
    
    try:
        metrics = await db_manager.get_api_error_metrics(start_time, end_time, endpoint_filter)
        
        return {
            'error_rate_percentage': metrics.get('error_rate_percentage', 0),
            'status_code_distribution': metrics.get('status_code_distribution', {}),
            'error_types': metrics.get('error_types', {}),
            'top_errors': metrics.get('top_errors', []),
            'critical_errors': metrics.get('critical_errors', 0),
            'timeout_errors': metrics.get('timeout_errors', 0),
            'authentication_errors': metrics.get('authentication_errors', 0),
            'rate_limit_errors': metrics.get('rate_limit_errors', 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting error metrics: {e}")
        return {
            'error_rate_percentage': 0,
            'status_code_distribution': {},
            'error_types': {},
            'top_errors': [],
            'critical_errors': 0,
            'timeout_errors': 0,
            'authentication_errors': 0,
            'rate_limit_errors': 0
        }

async def get_usage_patterns(db_manager: DatabaseManager, start_time: datetime, end_time: datetime, endpoint_filter: str) -> Dict[str, Any]:
    """Get API usage patterns"""
    
    try:
        patterns = await db_manager.get_api_usage_patterns(start_time, end_time, endpoint_filter)
        
        return {
            'peak_usage_hour': patterns.get('peak_usage_hour', 0),
            'lowest_usage_hour': patterns.get('lowest_usage_hour', 0),
            'busiest_endpoints': patterns.get('busiest_endpoints', []),
            'client_distribution': patterns.get('client_distribution', {}),
            'geographic_distribution': patterns.get('geographic_distribution', {}),
            'user_agent_distribution': patterns.get('user_agent_distribution', {}),
            'request_size_distribution': patterns.get('request_size_distribution', {}),
            'response_size_distribution': patterns.get('response_size_distribution', {})
        }
        
    except Exception as e:
        logger.error(f"Error getting usage patterns: {e}")
        return {
            'peak_usage_hour': 0,
            'lowest_usage_hour': 0,
            'busiest_endpoints': [],
            'client_distribution': {},
            'geographic_distribution': {},
            'user_agent_distribution': {},
            'request_size_distribution': {},
            'response_size_distribution': {}
        }

async def get_detailed_metrics(db_manager: DatabaseManager, start_time: datetime, end_time: datetime, endpoint_filter: str) -> Dict[str, Any]:
    """Get detailed API metrics"""
    
    try:
        detailed = await db_manager.get_api_detailed_metrics(start_time, end_time, endpoint_filter)
        
        return {
            'endpoint_performance': detailed.get('endpoint_performance', {}),
            'time_series_data': detailed.get('time_series_data', {}),
            'resource_utilization': detailed.get('resource_utilization', {}),
            'cache_performance': detailed.get('cache_performance', {}),
            'database_performance': detailed.get('database_performance', {}),
            'security_metrics': detailed.get('security_metrics', {}),
            'compliance_metrics': detailed.get('compliance_metrics', {})
        }
        
    except Exception as e:
        logger.error(f"Error getting detailed metrics: {e}")
        return {
            'endpoint_performance': {},
            'time_series_data': {},
            'resource_utilization': {},
            'cache_performance': {},
            'database_performance': {},
            'security_metrics': {},
            'compliance_metrics': {}
        }
