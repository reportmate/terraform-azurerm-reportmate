"""
GET /api/v1/devices/{id}/security - Device Security Module
Retrieves comprehensive security information for a specific device
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
    GET /api/v1/devices/{id}/security
    Retrieve security features and compliance status for a specific device
    """
    
    logger.info("=== DEVICE SECURITY REQUEST ===")
    
    try:
        # Extract device ID from route
        device_id = req.route_params.get('id')
        if not device_id:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device ID required',
                    'details': 'Device ID must be provided in the URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Fetching security data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device security data
        security_data = await get_device_security(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(security_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device security endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_security(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive security data for a specific device
    """
    
    try:
        # Get security data from database
        security = await db_manager.get_device_security(device_id)
        
        if not security:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No security data found for device {device_id}'
            }
        
        # Calculate security score and compliance status
        security_assessment = assess_device_security(security)
        
        return {
            'success': True,
            'device_id': device_id,
            'security_features': {
                'bitlocker': {
                    'enabled': security.get('bitlocker_enabled', False),
                    'status': security.get('bitlocker_status', 'Unknown'),
                    'encryption_method': security.get('bitlocker_encryption_method')
                },
                'windows_defender': {
                    'enabled': security.get('defender_enabled', False),
                    'status': security.get('defender_status', 'Unknown'),
                    'last_scan': security.get('defender_last_scan'),
                    'real_time_protection': security.get('defender_realtime', False)
                },
                'firewall': {
                    'enabled': security.get('firewall_enabled', False),
                    'profiles': security.get('firewall_profiles', {})
                },
                'secure_boot': {
                    'enabled': security.get('secure_boot_enabled', False),
                    'status': security.get('secure_boot_status', 'Unknown')
                },
                'tpm': {
                    'present': security.get('tpm_present', False),
                    'version': security.get('tpm_version'),
                    'enabled': security.get('tpm_enabled', False)
                },
                'credential_guard': {
                    'enabled': security.get('credential_guard_enabled', False),
                    'status': security.get('credential_guard_status')
                }
            },
            'compliance': {
                'score': security_assessment['score'],
                'status': security_assessment['status'],
                'requirements_met': security_assessment['requirements_met'],
                'requirements_failed': security_assessment['requirements_failed'],
                'recommendations': security_assessment['recommendations']
            },
            'vulnerabilities': {
                'missing_updates': security.get('missing_updates', []),
                'outdated_software': security.get('outdated_software', []),
                'security_alerts': security.get('security_alerts', [])
            },
            'certificates': {
                'count': security.get('certificate_count', 0),
                'expired': security.get('expired_certificates', 0),
                'expiring_soon': security.get('expiring_certificates', 0)
            },
            'last_security_scan': security.get('last_security_scan'),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device security: {e}")
        return {
            'success': False,
            'error': 'Failed to retrieve security data',
            'details': str(e)
        }

def assess_device_security(security: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess device security posture and calculate compliance score
    """
    
    score = 0
    max_score = 100
    requirements_met = []
    requirements_failed = []
    recommendations = []
    
    # BitLocker assessment (20 points)
    if security.get('bitlocker_enabled', False):
        score += 20
        requirements_met.append('Disk encryption enabled (BitLocker)')
    else:
        requirements_failed.append('Disk encryption not enabled')
        recommendations.append('Enable BitLocker disk encryption')
    
    # Windows Defender assessment (20 points)
    if security.get('defender_enabled', False):
        score += 15
        requirements_met.append('Antivirus protection enabled')
        
        if security.get('defender_realtime', False):
            score += 5
            requirements_met.append('Real-time protection enabled')
        else:
            recommendations.append('Enable real-time protection')
    else:
        requirements_failed.append('Antivirus protection not enabled')
        recommendations.append('Enable Windows Defender')
    
    # Firewall assessment (15 points)
    if security.get('firewall_enabled', False):
        score += 15
        requirements_met.append('Windows Firewall enabled')
    else:
        requirements_failed.append('Windows Firewall not enabled')
        recommendations.append('Enable Windows Firewall')
    
    # Secure Boot assessment (15 points)
    if security.get('secure_boot_enabled', False):
        score += 15
        requirements_met.append('Secure Boot enabled')
    else:
        requirements_failed.append('Secure Boot not enabled')
        recommendations.append('Enable Secure Boot in BIOS/UEFI')
    
    # TPM assessment (15 points)
    if security.get('tpm_present', False):
        score += 10
        requirements_met.append('TPM module present')
        
        if security.get('tpm_enabled', False):
            score += 5
            requirements_met.append('TPM module enabled')
        else:
            recommendations.append('Enable TPM module')
    else:
        requirements_failed.append('TPM module not present')
        recommendations.append('Ensure TPM 2.0 is available and enabled')
    
    # Credential Guard assessment (10 points)
    if security.get('credential_guard_enabled', False):
        score += 10
        requirements_met.append('Credential Guard enabled')
    else:
        recommendations.append('Enable Credential Guard for enhanced security')
    
    # Security updates assessment (5 points)
    missing_updates = len(security.get('missing_updates', []))
    if missing_updates == 0:
        score += 5
        requirements_met.append('Security updates current')
    else:
        requirements_failed.append(f'{missing_updates} security updates missing')
        recommendations.append('Install pending security updates')
    
    # Determine compliance status
    if score >= 90:
        status = 'Excellent'
    elif score >= 75:
        status = 'Good'
    elif score >= 60:
        status = 'Fair'
    elif score >= 40:
        status = 'Poor'
    else:
        status = 'Critical'
    
    return {
        'score': score,
        'max_score': max_score,
        'percentage': round((score / max_score) * 100, 1),
        'status': status,
        'requirements_met': requirements_met,
        'requirements_failed': requirements_failed,
        'recommendations': recommendations
    }
