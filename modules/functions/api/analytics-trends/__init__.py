"""
GET /api/v1/analytics/trends - Analytics Trends Endpoint
Provides historical trends and forecasting for fleet management
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
    GET /api/v1/analytics/trends
    Retrieve historical trends and forecasting data
    """
    
    logger.info("=== ANALYTICS TRENDS REQUEST ===")
    
    try:
        # Get query parameters
        time_range = req.params.get('time_range', '90d')  # 30d, 90d, 180d, 1y
        metric = req.params.get('metric', 'all')  # all, devices, security, performance, compliance
        business_unit = req.params.get('business_unit', '')
        granularity = req.params.get('granularity', 'daily')  # hourly, daily, weekly, monthly
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get analytics trends data
        trends_data = await get_analytics_trends(
            db_manager, time_range, metric, business_unit, granularity
        )
        
        return func.HttpResponse(
            json.dumps(trends_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in analytics trends endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_analytics_trends(
    db_manager: DatabaseManager,
    time_range: str,
    metric: str,
    business_unit: str = '',
    granularity: str = 'daily'
) -> Dict[str, Any]:
    """
    Generate comprehensive analytics trends and forecasting
    """
    
    try:
        # Calculate time range
        end_date = datetime.utcnow()
        if time_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_range == '180d':
            start_date = end_date - timedelta(days=180)
        elif time_range == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # Default to 90d
            start_date = end_date - timedelta(days=90)
        
        trends = {
            'success': True,
            'time_range': time_range,
            'start_date': start_date.isoformat() + 'Z',
            'end_date': end_date.isoformat() + 'Z',
            'granularity': granularity,
            'business_unit': business_unit,
            'trends': {},
            'forecasts': {},
            'insights': {},
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Get specific metric trends or all metrics
        if metric == 'all' or metric == 'devices':
            trends['trends']['devices'] = await get_device_trends(db_manager, start_date, end_date, business_unit, granularity)
        
        if metric == 'all' or metric == 'security':
            trends['trends']['security'] = await get_security_trends(db_manager, start_date, end_date, business_unit, granularity)
        
        if metric == 'all' or metric == 'performance':
            trends['trends']['performance'] = await get_performance_trends(db_manager, start_date, end_date, business_unit, granularity)
        
        if metric == 'all' or metric == 'compliance':
            trends['trends']['compliance'] = await get_compliance_trends(db_manager, start_date, end_date, business_unit, granularity)
        
        # Generate forecasts
        trends['forecasts'] = await generate_forecasts(db_manager, trends['trends'], time_range)
        
        # Generate insights
        trends['insights'] = await generate_trend_insights(trends['trends'], trends['forecasts'])
        
        return trends
        
    except Exception as e:
        logger.error(f"Error generating analytics trends: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

async def get_device_trends(db_manager: DatabaseManager, start_date: datetime, end_date: datetime, business_unit: str, granularity: str) -> Dict[str, Any]:
    """Get device-related trends"""
    
    trends = await db_manager.get_device_trends(start_date, end_date, business_unit, granularity)
    
    return {
        'device_count': trends.get('device_count', []),
        'new_registrations': trends.get('new_registrations', []),
        'active_devices': trends.get('active_devices', []),
        'offline_devices': trends.get('offline_devices', []),
        'device_types': trends.get('device_types', {}),
        'os_distribution': trends.get('os_distribution', {})
    }

async def get_security_trends(db_manager: DatabaseManager, start_date: datetime, end_date: datetime, business_unit: str, granularity: str) -> Dict[str, Any]:
    """Get security-related trends"""
    
    trends = await db_manager.get_security_trends(start_date, end_date, business_unit, granularity)
    
    return {
        'security_scores': trends.get('security_scores', []),
        'threat_detections': trends.get('threat_detections', []),
        'vulnerability_counts': trends.get('vulnerability_counts', []),
        'security_incidents': trends.get('security_incidents', []),
        'compliance_scores': trends.get('compliance_scores', []),
        'patch_levels': trends.get('patch_levels', [])
    }

async def get_performance_trends(db_manager: DatabaseManager, start_date: datetime, end_date: datetime, business_unit: str, granularity: str) -> Dict[str, Any]:
    """Get performance-related trends"""
    
    trends = await db_manager.get_performance_trends(start_date, end_date, business_unit, granularity)
    
    return {
        'cpu_utilization': trends.get('cpu_utilization', []),
        'memory_utilization': trends.get('memory_utilization', []),
        'disk_utilization': trends.get('disk_utilization', []),
        'network_utilization': trends.get('network_utilization', []),
        'uptime_percentages': trends.get('uptime_percentages', []),
        'response_times': trends.get('response_times', [])
    }

async def get_compliance_trends(db_manager: DatabaseManager, start_date: datetime, end_date: datetime, business_unit: str, granularity: str) -> Dict[str, Any]:
    """Get compliance-related trends"""
    
    trends = await db_manager.get_compliance_trends(start_date, end_date, business_unit, granularity)
    
    return {
        'compliance_scores': trends.get('compliance_scores', []),
        'policy_violations': trends.get('policy_violations', []),
        'audit_findings': trends.get('audit_findings', []),
        'remediation_rates': trends.get('remediation_rates', []),
        'certification_status': trends.get('certification_status', [])
    }

async def generate_forecasts(db_manager: DatabaseManager, trends: Dict[str, Any], time_range: str) -> Dict[str, Any]:
    """Generate forecasts based on historical trends"""
    
    try:
        forecasts = await db_manager.generate_trend_forecasts(trends, time_range)
        
        return {
            'device_growth': forecasts.get('device_growth', {}),
            'security_projections': forecasts.get('security_projections', {}),
            'performance_predictions': forecasts.get('performance_predictions', {}),
            'compliance_forecasts': forecasts.get('compliance_forecasts', {}),
            'confidence_intervals': forecasts.get('confidence_intervals', {}),
            'methodology': 'Linear regression with seasonal adjustment'
        }
        
    except Exception as e:
        logger.error(f"Error generating forecasts: {e}")
        return {
            'device_growth': {},
            'security_projections': {},
            'performance_predictions': {},
            'compliance_forecasts': {},
            'confidence_intervals': {},
            'methodology': 'Forecast generation failed'
        }

async def generate_trend_insights(trends: Dict[str, Any], forecasts: Dict[str, Any]) -> Dict[str, Any]:
    """Generate insights from trends and forecasts"""
    
    insights = {
        'key_findings': [],
        'growth_patterns': [],
        'risk_indicators': [],
        'opportunities': [],
        'recommendations': []
    }
    
    # Analyze device trends
    if 'devices' in trends:
        device_data = trends['devices'].get('device_count', [])
        if len(device_data) > 1:
            growth_rate = ((device_data[-1] - device_data[0]) / device_data[0]) * 100 if device_data[0] > 0 else 0
            if growth_rate > 10:
                insights['growth_patterns'].append(f"Fleet growing rapidly at {growth_rate:.1f}% over period")
                insights['recommendations'].append("Consider scaling infrastructure for continued growth")
            elif growth_rate > 0:
                insights['growth_patterns'].append(f"Steady fleet growth of {growth_rate:.1f}% over period")
            else:
                insights['risk_indicators'].append(f"Fleet shrinking by {abs(growth_rate):.1f}% over period")
    
    # Analyze security trends
    if 'security' in trends:
        security_scores = trends['security'].get('security_scores', [])
        if len(security_scores) > 1:
            security_trend = (security_scores[-1] - security_scores[0]) / len(security_scores)
            if security_trend > 5:
                insights['key_findings'].append("Security posture improving consistently")
            elif security_trend < -5:
                insights['risk_indicators'].append("Security posture declining - immediate attention required")
                insights['recommendations'].append("Implement enhanced security measures")
    
    # Analyze performance trends
    if 'performance' in trends:
        cpu_util = trends['performance'].get('cpu_utilization', [])
        if cpu_util and max(cpu_util) > 80:
            insights['risk_indicators'].append("High CPU utilization detected across fleet")
            insights['recommendations'].append("Consider hardware upgrades for high-utilization devices")
    
    # Generate opportunities
    insights['opportunities'].extend([
        "Implement predictive maintenance based on performance trends",
        "Optimize resource allocation using utilization patterns",
        "Develop proactive security measures based on threat trends"
    ])
    
    return insights
