"""
GET /api/v1/devices/{id}/inventory - Device Inventory Module
Retrieves comprehensive asset and identification data for a specific device
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
    GET /api/v1/devices/{id}/inventory
    Retrieve inventory data for a specific device
    """
    
    logger.info("=== DEVICE INVENTORY REQUEST ===")
    
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
        
        logger.info(f"Fetching inventory data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device inventory data
        inventory_data = await get_device_inventory(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(inventory_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device inventory endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_inventory(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive inventory data for a specific device
    """
    
    try:
        # Get inventory data from database
        inventory = await db_manager.get_device_inventory(device_id)
        
        if not inventory:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No inventory data found for device {device_id}'
            }
        
        # Calculate asset tracking metrics
        tracking_info = calculate_asset_tracking(inventory)
        
        return {
            'success': True,
            'device_id': device_id,
            'inventory_data': inventory,
            'asset_tracking': tracking_info,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device inventory data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

def calculate_asset_tracking(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate asset tracking and compliance information
    """
    
    tracking = {
        'asset_tag': inventory.get('asset_tag', ''),
        'serial_number': inventory.get('serial_number', ''),
        'purchase_date': inventory.get('purchase_date', ''),
        'warranty_status': 'unknown',
        'compliance_score': 0,
        'identification_metrics': {},
        'recommendations': [],
        'warnings': []
    }
    
    # Asset identification completeness
    identification_score = 0
    total_fields = 7
    
    if tracking['asset_tag']:
        identification_score += 1
        tracking['recommendations'].append("Asset tag assigned")
    else:
        tracking['warnings'].append("Asset tag missing")
    
    if tracking['serial_number']:
        identification_score += 1
        tracking['recommendations'].append("Serial number recorded")
    else:
        tracking['warnings'].append("Serial number missing")
    
    if inventory.get('manufacturer'):
        identification_score += 1
    
    if inventory.get('model'):
        identification_score += 1
    
    if inventory.get('location'):
        identification_score += 1
        tracking['recommendations'].append("Device location tracked")
    else:
        tracking['warnings'].append("Device location not specified")
    
    if inventory.get('owner'):
        identification_score += 1
        tracking['recommendations'].append("Device owner assigned")
    else:
        tracking['warnings'].append("Device owner not assigned")
    
    if inventory.get('department'):
        identification_score += 1
        tracking['recommendations'].append("Department assignment recorded")
    
    tracking['identification_metrics'] = {
        'completeness_score': round((identification_score / total_fields) * 100),
        'fields_completed': identification_score,
        'total_fields': total_fields
    }
    
    # Warranty analysis
    if tracking['purchase_date']:
        try:
            purchase_date = datetime.fromisoformat(tracking['purchase_date'].replace('Z', '+00:00'))
            warranty_years = inventory.get('warranty_years', 3)
            warranty_end = purchase_date.replace(year=purchase_date.year + warranty_years)
            
            if datetime.utcnow().replace(tzinfo=purchase_date.tzinfo) < warranty_end:
                tracking['warranty_status'] = 'active'
                tracking['recommendations'].append("Device under warranty")
            else:
                tracking['warranty_status'] = 'expired'
                tracking['warnings'].append("Warranty has expired")
        except:
            tracking['warranty_status'] = 'unknown'
    
    # Overall compliance score
    compliance_score = tracking['identification_metrics']['completeness_score']
    if tracking['warranty_status'] == 'active':
        compliance_score += 20
    elif tracking['warranty_status'] == 'expired':
        compliance_score -= 10
    
    tracking['compliance_score'] = max(0, min(100, compliance_score))
    
    return tracking
