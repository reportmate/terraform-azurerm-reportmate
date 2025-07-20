"""
GET /api/v1/analytics/summary - Fleet Summary Analytics
Provides comprehensive fleet management analytics and KPIs
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
    GET /api/v1/analytics/summary
    Retrieve comprehensive fleet summary analytics
    """
    
    logger.info("=== ANALYTICS SUMMARY REQUEST ===")
    
    try:
        # Get query parameters
        time_range = req.params.get('time_range', '30d')  # 7d, 30d, 90d, 1y
        business_unit = req.params.get('business_unit', '')
        include_trends = req.params.get('include_trends', 'true').lower() == 'true'
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get fleet analytics summary
        analytics_data = await get_fleet_analytics_summary(
            db_manager, time_range, business_unit, include_trends
        )
        
        return func.HttpResponse(
            json.dumps(analytics_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in analytics summary endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_fleet_analytics_summary(
    db_manager: DatabaseManager,
    time_range: str,
    business_unit: str = '',
    include_trends: bool = True
) -> Dict[str, Any]:
    """
    Generate comprehensive fleet analytics summary
    """
    
    try:
        # Calculate time range
        end_date = datetime.utcnow()
        if time_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_range == '90d':
            start_date = end_date - timedelta(days=90)
        elif time_range == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # Default to 30d
            start_date = end_date - timedelta(days=30)
        
        # Get fleet overview
        fleet_overview = await get_fleet_overview(db_manager, business_unit)
        
        # Get device statistics
        device_stats = await get_device_statistics(db_manager, start_date, end_date, business_unit)
        
        # Get security posture
        security_posture = await get_security_posture(db_manager, business_unit)
        
        # Get compliance metrics
        compliance_metrics = await get_compliance_metrics(db_manager, business_unit)
        
        # Get hardware insights
        hardware_insights = await get_hardware_insights(db_manager, business_unit)
        
        # Get application metrics
        application_metrics = await get_application_metrics(db_manager, business_unit)
        
        # Get trends if requested
        trends = {}
        if include_trends:
            trends = await get_fleet_trends(db_manager, start_date, end_date, business_unit)
        
        return {
            'success': True,
            'time_range': time_range,
            'business_unit': business_unit,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'fleet_overview': fleet_overview,
            'device_statistics': device_stats,
            'security_posture': security_posture,
            'compliance_metrics': compliance_metrics,
            'hardware_insights': hardware_insights,
            'application_metrics': application_metrics,
            'trends': trends if include_trends else None
        }
        
    except Exception as e:
        logger.error(f"Error generating fleet analytics: {e}")
        return {
            'success': False,
            'error': 'Failed to generate analytics',
            'details': str(e)
        }

async def get_fleet_overview(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """Get high-level fleet overview metrics"""
    
    overview = await db_manager.get_fleet_overview(business_unit)
    
    return {
        'total_devices': overview.get('total_devices', 0),
        'active_devices': overview.get('active_devices', 0),
        'inactive_devices': overview.get('inactive_devices', 0),
        'new_devices_30d': overview.get('new_devices_30d', 0),
        'device_types': overview.get('device_types', {}),
        'operating_systems': overview.get('operating_systems', {}),
        'business_units': overview.get('business_units', {}),
        'last_updated': datetime.utcnow().isoformat() + 'Z'
    }

async def get_device_statistics(
    db_manager: DatabaseManager, 
    start_date: datetime, 
    end_date: datetime, 
    business_unit: str = ''
) -> Dict[str, Any]:
    """Get detailed device statistics"""
    
    stats = await db_manager.get_device_statistics(start_date, end_date, business_unit)
    
    return {
        'online_percentage': stats.get('online_percentage', 0),
        'average_uptime': stats.get('average_uptime', 0),
        'performance_scores': stats.get('performance_scores', {}),
        'utilization_metrics': {
            'cpu': stats.get('avg_cpu_utilization', 0),
            'memory': stats.get('avg_memory_utilization', 0),
            'disk': stats.get('avg_disk_utilization', 0)
        },
        'health_status': stats.get('health_status', {}),
        'maintenance_required': stats.get('maintenance_required', 0)
    }

async def get_security_posture(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """Get fleet security posture metrics"""
    
    security = await db_manager.get_security_posture(business_unit)
    
    return {
        'overall_score': security.get('overall_score', 0),
        'compliance_percentage': security.get('compliance_percentage', 0),
        'encryption_coverage': security.get('encryption_coverage', 0),
        'antivirus_coverage': security.get('antivirus_coverage', 0),
        'firewall_coverage': security.get('firewall_coverage', 0),
        'vulnerabilities': {
            'critical': security.get('critical_vulnerabilities', 0),
            'high': security.get('high_vulnerabilities', 0),
            'medium': security.get('medium_vulnerabilities', 0),
            'low': security.get('low_vulnerabilities', 0)
        },
        'threats_detected': security.get('threats_detected_30d', 0),
        'security_incidents': security.get('security_incidents_30d', 0)
    }

async def get_compliance_metrics(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """Get compliance metrics"""
    
    compliance = await db_manager.get_compliance_metrics(business_unit)
    
    return {
        'overall_compliance': compliance.get('overall_compliance', 0),
        'policy_compliance': compliance.get('policy_compliance', {}),
        'certificate_compliance': compliance.get('certificate_compliance', 0),
        'update_compliance': compliance.get('update_compliance', 0),
        'configuration_compliance': compliance.get('configuration_compliance', 0),
        'non_compliant_devices': compliance.get('non_compliant_devices', []),
        'compliance_trends': compliance.get('compliance_trends', [])
    }

async def get_hardware_insights(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """Get hardware insights and recommendations"""
    
    hardware = await db_manager.get_hardware_insights(business_unit)
    
    return {
        'fleet_age': hardware.get('fleet_age', {}),
        'refresh_recommendations': hardware.get('refresh_recommendations', []),
        'performance_bottlenecks': hardware.get('performance_bottlenecks', []),
        'capacity_planning': hardware.get('capacity_planning', {}),
        'warranty_status': hardware.get('warranty_status', {}),
        'hardware_standardization': hardware.get('standardization', {})
    }

async def get_application_metrics(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """Get application metrics"""
    
    apps = await db_manager.get_application_metrics(business_unit)
    
    return {
        'total_applications': apps.get('total_applications', 0),
        'licensed_compliance': apps.get('licensed_compliance', 0),
        'security_compliance': apps.get('security_compliance', 0),
        'version_compliance': apps.get('version_compliance', 0),
        'deployment_success_rate': apps.get('deployment_success_rate', 0),
        'most_used_applications': apps.get('most_used_applications', []),
        'problematic_applications': apps.get('problematic_applications', [])
    }

async def get_fleet_trends(
    db_manager: DatabaseManager, 
    start_date: datetime, 
    end_date: datetime, 
    business_unit: str = ''
) -> Dict[str, Any]:
    """Get fleet trends over time"""
    
    trends = await db_manager.get_fleet_trends(start_date, end_date, business_unit)
    
    return {
        'device_growth': trends.get('device_growth', []),
        'security_trends': trends.get('security_trends', []),
        'compliance_trends': trends.get('compliance_trends', []),
        'performance_trends': trends.get('performance_trends', []),
        'incident_trends': trends.get('incident_trends', [])
    }
