"""
Inventory Module Processor for ReportMate
Handles device identification and asset information
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class InventoryProcessor(BaseModuleProcessor):
    """
    Processor for inventory module data
    Handles device identification, serial numbers, asset tags, and device naming
    """
    
    @property
    def module_id(self) -> str:
        return "inventory"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process inventory data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed inventory data
        """
        self.logger.debug(f"Processing inventory module for device {device_id}")
        
        # Extract inventory data from the device payload
        inventory_data = device_data.get('inventory', {})
        system_info = device_data.get('system', {})
        
        # Build processed inventory data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'deviceName': self._extract_device_name(inventory_data, system_info),  # Use camelCase to match API expectations
            'device_name': self._extract_device_name(inventory_data, system_info),  # Keep snake_case for backward compatibility
            'serial_number': self._extract_serial_number(inventory_data, system_info),
            'serialNumber': self._extract_serial_number(inventory_data, system_info),  # Add camelCase version
            'uuid': self._extract_device_uuid(inventory_data, system_info),
            'asset_tag': self._extract_asset_tag(inventory_data),
            'assetTag': self._extract_asset_tag(inventory_data),  # Add camelCase version
            'location': inventory_data.get('location', ''),
            'owner': inventory_data.get('owner', ''),
            'department': inventory_data.get('department', ''),
            'catalog': inventory_data.get('catalog', ''),
            'usage': inventory_data.get('usage', ''),
            'purchase_date': self._extract_purchase_date(inventory_data),
            'warranty_expiration': self._extract_warranty_expiration(inventory_data)
        }
        
        self.logger.info(f"Inventory processed - Serial: {processed_data['serial_number']}, "
                        f"UUID: {processed_data['uuid']}, Device: {processed_data['deviceName']}")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate inventory module data
        
        Args:
            data: Processed inventory data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id']
        
        for field in required_fields:
            if not data.get(field):
                self.logger.warning(f"Inventory validation failed - missing {field}")
                return False
        
        # Check for device name in either format
        if not (data.get('device_name') or data.get('deviceName')):
            self.logger.warning("Inventory validation failed - missing device_name/deviceName")
            return False
            
        # Check for serial number in either format
        if not (data.get('serial_number') or data.get('serialNumber')):
            self.logger.warning("Inventory validation failed - missing serial_number/serialNumber")
            return False

        if data['module_id'] != self.module_id:
            self.logger.warning(f"Inventory validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _extract_device_name(self, inventory_data: Dict[str, Any], system_info: Dict[str, Any]) -> str:
        """Extract device name from various sources"""
        # Priority: inventory allocation > deviceName (camelCase) > device_name (snake_case) > system computer_name > hostname > machine name
        device_name = (
            inventory_data.get('allocation') or
            inventory_data.get('deviceName') or
            inventory_data.get('device_name') or
            system_info.get('computer_name') or
            system_info.get('hostname') or
            'Unknown'
        )
        return str(device_name)
    
    def _extract_serial_number(self, inventory_data: Dict[str, Any], system_info: Dict[str, Any]) -> str:
        """Extract serial number from various sources"""
        serial = (
            inventory_data.get('serial_number') or
            system_info.get('hardware_serial') or
            system_info.get('serial') or
            'Unknown'
        )
        
        # Filter out common placeholder values
        invalid_serials = {'0', 'System Serial Number', 'To be filled by O.E.M.', 'Default string', 'Unknown'}
        if serial in invalid_serials:
            # Try chassis serial as fallback
            chassis_serial = system_info.get('chassis_serial')
            if chassis_serial and chassis_serial not in invalid_serials:
                return str(chassis_serial)
            return 'Unknown'
        
        return str(serial)
    
    def _extract_device_uuid(self, inventory_data: Dict[str, Any], system_info: Dict[str, Any]) -> str:
        """Extract device UUID from various sources"""
        uuid = (
            inventory_data.get('uuid') or
            system_info.get('uuid') or
            system_info.get('hardware_uuid') or
            'Unknown'
        )
        
        # Filter out common placeholder values
        invalid_uuids = {'00000000-0000-0000-0000-000000000000', 'Unknown', ''}
        if uuid in invalid_uuids:
            return 'Unknown'
        
        return str(uuid)
    
    def _extract_asset_tag(self, inventory_data: Dict[str, Any]) -> str:
        """Extract asset tag from inventory data"""
        asset_tag = (
            inventory_data.get('asset_tag') or
            inventory_data.get('asset') or
            inventory_data.get('assetTag') or
            ''
        )
        
        # Filter out common placeholder values
        invalid_tags = {'0', 'Asset Tag', 'To be filled by O.E.M.', 'Unknown'}
        if asset_tag in invalid_tags:
            return ''
        
        return str(asset_tag)
    
    def _extract_purchase_date(self, inventory_data: Dict[str, Any]) -> Optional[str]:
        """Extract purchase date from inventory data"""
        purchase_date = inventory_data.get('purchase_date')
        if purchase_date:
            try:
                # Try to parse and format the date
                if isinstance(purchase_date, str):
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                        try:
                            parsed_date = datetime.strptime(purchase_date, fmt)
                            return parsed_date.date().isoformat()
                        except ValueError:
                            continue
                elif isinstance(purchase_date, datetime):
                    return purchase_date.date().isoformat()
            except Exception as e:
                self.logger.warning(f"Failed to parse purchase date '{purchase_date}': {e}")
        
        return None
    
    def _extract_warranty_expiration(self, inventory_data: Dict[str, Any]) -> Optional[str]:
        """Extract warranty expiration from inventory data"""
        warranty_exp = inventory_data.get('warranty_expiration')
        if warranty_exp:
            try:
                # Try to parse and format the date
                if isinstance(warranty_exp, str):
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                        try:
                            parsed_date = datetime.strptime(warranty_exp, fmt)
                            return parsed_date.date().isoformat()
                        except ValueError:
                            continue
                elif isinstance(warranty_exp, datetime):
                    return warranty_exp.date().isoformat()
            except Exception as e:
                self.logger.warning(f"Failed to parse warranty expiration '{warranty_exp}': {e}")
        
        return None
