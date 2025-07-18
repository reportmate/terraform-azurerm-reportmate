"""
GET /api/v1/version - API Version Information
Provides detailed API version and capability information
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any
import azure.functions as func
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/v1/version
    Return API version and capability information
    """
    
    logger.info("=== API VERSION REQUEST ===")
    
    try:
        version_info = {
            'success': True,
            'api': {
                'name': 'ReportMate REST API',
                'version': '1.0.0',
                'build': os.environ.get('BUILD_NUMBER', 'development'),
                'environment': os.environ.get('AZURE_FUNCTIONS_ENVIRONMENT', 'Production'),
                'deployment_time': os.environ.get('DEPLOYMENT_TIME', datetime.utcnow().isoformat() + 'Z')
            },
            'capabilities': {
                'device_management': True,
                'fleet_analytics': True,
                'security_monitoring': True,
                'compliance_reporting': True,
                'real_time_updates': True,
                'multi_tenant': True,
                'business_units': True,
                'machine_groups': True
            },
            'endpoints': {
                'core_device_endpoints': [
                    'POST /api/v1/devices/ingest',
                    'GET /api/v1/devices',
                    'GET /api/v1/devices/{id}',
                    'DELETE /api/v1/devices/{id}'
                ],
                'modular_data_endpoints': [
                    'GET /api/v1/devices/{id}/applications',
                    'GET /api/v1/devices/{id}/hardware', 
                    'GET /api/v1/devices/{id}/security',
                    'GET /api/v1/devices/{id}/network',
                    'GET /api/v1/devices/{id}/system',
                    'GET /api/v1/devices/{id}/inventory',
                    'GET /api/v1/devices/{id}/management',
                    'GET /api/v1/devices/{id}/profiles',
                    'GET /api/v1/devices/{id}/installs'
                ],
                'global_module_endpoints': [
                    'GET /api/v1/applications',
                    'GET /api/v1/hardware',
                    'GET /api/v1/security',
                    'GET /api/v1/network',
                    'GET /api/v1/system',
                    'GET /api/v1/inventory',
                    'GET /api/v1/management',
                    'GET /api/v1/profiles',
                    'GET /api/v1/installs'
                ],
                'analytics_reporting': [
                    'GET /api/v1/analytics/summary',
                    'GET /api/v1/analytics/trends',
                    'GET /api/v1/analytics/compliance'
                ],
                'administrative': [
                    'GET /api/v1/health',
                    'GET /api/v1/metrics',
                    'GET /api/v1/version'
                ]
            },
            'data_processing_modules': [
                'applications - Installed software and application inventory',
                'hardware - Physical hardware specifications and capabilities', 
                'inventory - Asset management and device tracking',
                'system - Operating system information and configuration',
                'management - MDM enrollment and management status',
                'security - Security features, compliance, and vulnerabilities',
                'network - Network interfaces and connectivity',
                'profiles - Configuration profiles and policies',
                'installs - Managed installations (Munki, Cimian, etc.)'
            ],
            'authentication': {
                'device_authentication': 'Passphrase-based authentication',
                'api_key_management': 'Future enhancement',
                'rate_limiting': 'Enabled',
                'throttling': 'Enabled'
            },
            'features': {
                'real_time_messaging': 'Azure Web PubSub integration',
                'database': 'PostgreSQL with business unit support',
                'monitoring': 'Application Insights integration',
                'security': 'Managed identities and access control',
                'scalability': 'Azure Functions consumption plan'
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return func.HttpResponse(
            json.dumps(version_info, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in version endpoint: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Failed to retrieve version information',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
