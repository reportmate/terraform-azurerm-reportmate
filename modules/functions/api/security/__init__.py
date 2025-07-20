"""
GET /api/v1/security - Global Security Endpoint
Retrieves security posture overview across all devices in the fleet
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
    GET /api/v1/security
    Retrieve security posture overview across all devices
    """
    
    logger.info("=== GLOBAL SECURITY REQUEST ===")
    
    try:
        # Get query parameters
        business_unit = req.params.get('business_unit', '')
        risk_level = req.params.get('risk_level', '')  # low, medium, high, critical
        include_details = req.params.get('include_details', 'false').lower() == 'true'
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get global security data
        security_data = await get_global_security(
            db_manager, business_unit, risk_level, include_details
        )
        
        return func.HttpResponse(
            json.dumps(security_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in global security endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_global_security(
    db_manager: DatabaseManager, 
    business_unit: str = '',
    risk_level: str = '',
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Retrieve security posture data across all devices
    """
    
    try:
        # Get aggregated security data from database
        security_overview = await db_manager.get_global_security_overview(business_unit, risk_level)
        
        # Calculate fleet-wide security statistics
        stats = await calculate_global_security_stats(db_manager, business_unit)
        
        # Get security insights and threat analysis
        insights = await get_security_insights(db_manager, business_unit)
        
        # Get compliance summary
        compliance = await get_compliance_summary(db_manager, business_unit)
        
        result = {
            'success': True,
            'security_overview': security_overview,
            'statistics': stats,
            'insights': insights,
            'compliance': compliance,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Include detailed device-level security data if requested
        if include_details:
            device_details = await db_manager.get_security_device_details(business_unit, risk_level)
            result['device_details'] = device_details
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving global security data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

async def calculate_global_security_stats(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """
    Calculate fleet-wide security statistics
    """
    
    try:
        stats = await db_manager.get_security_statistics(business_unit)
        
        return {
            'total_devices': stats.get('total_devices', 0),
            'security_scores': {
                'average_score': stats.get('average_security_score', 0),
                'high_security': stats.get('high_security_devices', 0),
                'medium_security': stats.get('medium_security_devices', 0),
                'low_security': stats.get('low_security_devices', 0)
            },
            'threat_indicators': {
                'critical_threats': stats.get('critical_threats', 0),
                'high_threats': stats.get('high_threats', 0),
                'medium_threats': stats.get('medium_threats', 0),
                'low_threats': stats.get('low_threats', 0)
            },
            'security_features': {
                'antivirus_enabled': stats.get('antivirus_enabled', 0),
                'firewall_enabled': stats.get('firewall_enabled', 0),
                'encryption_enabled': stats.get('encryption_enabled', 0),
                'auto_updates_enabled': stats.get('auto_updates_enabled', 0)
            },
            'vulnerability_summary': {
                'critical_vulnerabilities': stats.get('critical_vulnerabilities', 0),
                'high_vulnerabilities': stats.get('high_vulnerabilities', 0),
                'medium_vulnerabilities': stats.get('medium_vulnerabilities', 0),
                'low_vulnerabilities': stats.get('low_vulnerabilities', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating security statistics: {e}")
        return {}

async def get_security_insights(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """
    Get security insights and threat analysis
    """
    
    try:
        insights = await db_manager.get_security_insights(business_unit)
        
        return {
            'fleet_security_score': insights.get('fleet_security_score', 0),
            'top_security_risks': insights.get('top_security_risks', []),
            'security_trends': insights.get('security_trends', {}),
            'recommended_actions': insights.get('recommended_actions', []),
            'urgent_alerts': insights.get('urgent_alerts', []),
            'security_best_practices': insights.get('security_best_practices', []),
            'threat_landscape': insights.get('threat_landscape', {}),
            'incident_summary': insights.get('incident_summary', {})
        }
        
    except Exception as e:
        logger.error(f"Error getting security insights: {e}")
        return {
            'fleet_security_score': 0,
            'top_security_risks': [],
            'security_trends': {},
            'recommended_actions': [],
            'urgent_alerts': [],
            'security_best_practices': [],
            'threat_landscape': {},
            'incident_summary': {}
        }

async def get_compliance_summary(db_manager: DatabaseManager, business_unit: str = '') -> Dict[str, Any]:
    """
    Get compliance summary and regulatory status
    """
    
    try:
        compliance = await db_manager.get_compliance_summary(business_unit)
        
        return {
            'overall_compliance_score': compliance.get('overall_compliance_score', 0),
            'regulatory_frameworks': {
                'gdpr_compliance': compliance.get('gdpr_compliance', 0),
                'hipaa_compliance': compliance.get('hipaa_compliance', 0),
                'sox_compliance': compliance.get('sox_compliance', 0),
                'pci_compliance': compliance.get('pci_compliance', 0)
            },
            'compliance_gaps': compliance.get('compliance_gaps', []),
            'certification_status': compliance.get('certification_status', {}),
            'audit_readiness': compliance.get('audit_readiness', 0),
            'policy_violations': compliance.get('policy_violations', []),
            'remediation_required': compliance.get('remediation_required', [])
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance summary: {e}")
        return {
            'overall_compliance_score': 0,
            'regulatory_frameworks': {},
            'compliance_gaps': [],
            'certification_status': {},
            'audit_readiness': 0,
            'policy_violations': [],
            'remediation_required': []
        }
