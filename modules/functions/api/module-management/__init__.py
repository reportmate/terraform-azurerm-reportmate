"""
GET /api/v1/devices/{id}/management - Device Management Module
Retrieves comprehensive MDM and management information for a specific device
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
    GET /api/v1/devices/{id}/management
    Retrieve MDM enrollment and management status for a specific device
    """
    
    logger.info("=== DEVICE MANAGEMENT REQUEST ===")
    
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
        
        logger.info(f"Fetching management data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device management data
        management_data = await get_device_management(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(management_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device management endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_management(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive management data for a specific device
    """
    
    try:
        # Get management data from database
        management = await db_manager.get_device_management(device_id)
        
        if not management:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No management data found for device {device_id}'
            }
        
        return {
            'success': True,
            'device_id': device_id,
            'device_state': {
                'status': management.get('device_status', 'Unknown'),
                'entra_joined': management.get('entra_joined', False),
                'enterprise_joined': management.get('enterprise_joined', False),
                'domain_joined': management.get('domain_joined', False),
                'workplace_joined': management.get('workplace_joined', False),
                'device_name': management.get('device_name', ''),
                'virtual_desktop': management.get('virtual_desktop', False)
            },
            'mdm_enrollment': {
                'enrolled': management.get('mdm_enrolled', False),
                'provider': management.get('mdm_provider', 'Unknown'),
                'enrollment_type': management.get('enrollment_type', ''),
                'enrollment_id': management.get('enrollment_id', ''),
                'user_principal_name': management.get('user_principal_name', ''),
                'server_url': management.get('server_url', ''),
                'management_url': management.get('management_url', ''),
                'last_sync': management.get('last_sync')
            },
            'tenant_details': {
                'tenant_name': management.get('tenant_name', ''),
                'tenant_id': management.get('tenant_id', ''),
                'mdm_url': management.get('mdm_url', ''),
                'compliance_url': management.get('compliance_url', ''),
                'settings_url': management.get('settings_url', '')
            },
            'device_details': {
                'device_id': management.get('device_uuid', ''),
                'thumbprint': management.get('thumbprint', ''),
                'certificate_validity': management.get('certificate_validity', ''),
                'key_container_id': management.get('key_container_id', ''),
                'tmp_protected': management.get('tmp_protected', False),
                'auth_status': management.get('auth_status', '')
            },
            'user_state': {
                'ngc_set': management.get('ngc_set', False),
                'ngc_key_id': management.get('ngc_key_id', ''),
                'can_reset': management.get('can_reset', False),
                'wam_default_set': management.get('wam_default_set', False),
                'wam_default_authority': management.get('wam_default_authority', ''),
                'wam_default_id': management.get('wam_default_id', '')
            },
            'sso_state': {
                'entra_prt': management.get('entra_prt', False),
                'enterprise_prt': management.get('enterprise_prt', False),
                'on_prem_tgt': management.get('on_prem_tgt', False),
                'cloud_tgt': management.get('cloud_tgt', False),
                'prt_authority': management.get('prt_authority', ''),
                'prt_update_time': management.get('prt_update_time'),
                'prt_expiry_time': management.get('prt_expiry_time')
            },
            'compliance': {
                'status': management.get('compliance_status', 'Unknown'),
                'last_check': management.get('compliance_last_check'),
                'policies_applied': management.get('policies_applied', 0),
                'policies_failed': management.get('policies_failed', 0)
            },
            'certificates': management.get('certificates', []),
            'policies': management.get('policies', []),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device management: {e}")
        return {
            'success': False,
            'error': 'Failed to retrieve management data',
            'details': str(e)
        }
