"""
GET /api/v1/devices/{id}/profiles - Device Profiles Module
Retrieves configuration profiles and policies for a specific device
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
    GET /api/v1/devices/{id}/profiles
    Retrieve configuration profiles for a specific device
    """
    
    logger.info("=== DEVICE PROFILES REQUEST ===")
    
    try:
        # Extract device ID from route
        device_id = req.route_params.get('id')
        if not device_id:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device ID required',
                    'details': 'Device ID must be provided in URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Fetching profiles data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device profiles data
        profiles_data = await get_device_profiles(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(profiles_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device profiles endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_profiles(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive profiles data for a specific device
    """
    
    try:
        # Get profiles data from database
        profiles = await db_manager.get_device_profiles(device_id)
        
        if not profiles:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No profiles data found for device {device_id}'
            }
        
        # Calculate configuration compliance
        compliance_info = calculate_profile_compliance(profiles)
        
        return {
            'success': True,
            'device_id': device_id,
            'profiles_data': profiles,
            'compliance_info': compliance_info,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device profiles data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

def calculate_profile_compliance(profiles: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate configuration profile compliance and policy adherence
    """
    
    compliance = {
        'overall_score': 0,
        'profile_summary': {},
        'policy_compliance': {},
        'recommendations': [],
        'violations': [],
        'applied_profiles': []
    }
    
    installed_profiles = profiles.get('installed_profiles', [])
    required_profiles = profiles.get('required_profiles', [])
    
    compliance['profile_summary'] = {
        'total_installed': len(installed_profiles),
        'total_required': len(required_profiles),
        'missing_profiles': 0,
        'outdated_profiles': 0
    }
    
    # Check for missing required profiles
    installed_ids = {p.get('profile_id') for p in installed_profiles}
    required_ids = {p.get('profile_id') for p in required_profiles}
    missing_profiles = required_ids - installed_ids
    
    compliance['profile_summary']['missing_profiles'] = len(missing_profiles)
    
    if missing_profiles:
        compliance['violations'].extend([
            f"Missing required profile: {profile_id}" 
            for profile_id in missing_profiles
        ])
    
    # Check for outdated profiles
    for installed in installed_profiles:
        profile_id = installed.get('profile_id')
        installed_version = installed.get('version', '1.0')
        
        # Find required version
        required = next((r for r in required_profiles if r.get('profile_id') == profile_id), None)
        if required:
            required_version = required.get('version', '1.0')
            if installed_version != required_version:
                compliance['profile_summary']['outdated_profiles'] += 1
                compliance['violations'].append(
                    f"Profile {profile_id} version {installed_version} is outdated (required: {required_version})"
                )
    
    # Policy compliance checking
    policies = profiles.get('policies', {})
    
    compliance['policy_compliance'] = {
        'security_policies': check_security_policies(policies.get('security', {})),
        'configuration_policies': check_configuration_policies(policies.get('configuration', {})),
        'compliance_policies': check_compliance_policies(policies.get('compliance', {}))
    }
    
    # Calculate overall score
    base_score = 100
    
    # Deduct for missing profiles
    base_score -= len(missing_profiles) * 15
    
    # Deduct for outdated profiles
    base_score -= compliance['profile_summary']['outdated_profiles'] * 10
    
    # Factor in policy compliance
    policy_scores = [
        compliance['policy_compliance']['security_policies'].get('score', 0),
        compliance['policy_compliance']['configuration_policies'].get('score', 0),
        compliance['policy_compliance']['compliance_policies'].get('score', 0)
    ]
    
    if policy_scores:
        avg_policy_score = sum(policy_scores) / len(policy_scores)
        base_score = int((base_score + avg_policy_score) / 2)
    
    compliance['overall_score'] = max(0, base_score)
    
    # Generate recommendations
    if compliance['overall_score'] >= 90:
        compliance['recommendations'].append("Profile configuration is excellent")
    elif compliance['overall_score'] >= 75:
        compliance['recommendations'].append("Profile configuration is good with minor improvements needed")
    elif compliance['overall_score'] >= 50:
        compliance['recommendations'].append("Profile configuration needs attention")
    else:
        compliance['recommendations'].append("Profile configuration requires immediate attention")
    
    if missing_profiles:
        compliance['recommendations'].append("Install missing required profiles")
    
    if compliance['profile_summary']['outdated_profiles'] > 0:
        compliance['recommendations'].append("Update outdated configuration profiles")
    
    return compliance

def check_security_policies(security_policies: Dict[str, Any]) -> Dict[str, Any]:
    """Check security policy compliance"""
    
    score = 100
    issues = []
    
    # Check key security settings
    if not security_policies.get('password_policy_enabled', True):
        score -= 25
        issues.append("Password policy not enforced")
    
    if not security_policies.get('encryption_required', True):
        score -= 30
        issues.append("Encryption not required")
    
    if not security_policies.get('firewall_enabled', True):
        score -= 20
        issues.append("Firewall policy not enforced")
    
    return {
        'score': max(0, score),
        'issues': issues,
        'compliant': score >= 80
    }

def check_configuration_policies(config_policies: Dict[str, Any]) -> Dict[str, Any]:
    """Check configuration policy compliance"""
    
    score = 100
    issues = []
    
    # Check configuration standards
    if not config_policies.get('auto_update_enabled'):
        score -= 20
        issues.append("Auto-update policy not configured")
    
    if not config_policies.get('software_restriction_policy'):
        score -= 15
        issues.append("Software restriction policy missing")
    
    return {
        'score': max(0, score),
        'issues': issues,
        'compliant': score >= 80
    }

def check_compliance_policies(compliance_policies: Dict[str, Any]) -> Dict[str, Any]:
    """Check regulatory compliance policies"""
    
    score = 100
    issues = []
    
    # Check compliance requirements
    if not compliance_policies.get('audit_logging_enabled'):
        score -= 25
        issues.append("Audit logging not enabled")
    
    if not compliance_policies.get('data_protection_policy'):
        score -= 20
        issues.append("Data protection policy not applied")
    
    return {
        'score': max(0, score),
        'issues': issues,
        'compliant': score >= 80
    }
