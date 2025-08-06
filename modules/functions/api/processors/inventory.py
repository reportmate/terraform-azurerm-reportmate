"""
Inventory Module Processor for ReportMate
Handles device identification and asset information
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from shared.base_processor import BaseModuleProcessor
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
        Process inventory module data - stores complete inventory data from client
        
        Args:
            device_data: Raw inventory data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete inventory data as received from client
        """
        try:
            logger.info(f"Processing inventory data for device {device_id}")
            
            # Extract inventory module data
            inventory_data = device_data.get('inventory', {})
            
            # Store complete inventory data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **inventory_data  # Include all inventory data as-is
            }
            
            logger.info(f"Successfully processed inventory data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing inventory data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate inventory module data
        
        Args:
            data: Inventory data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Inventory validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Inventory validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Inventory validation error: {str(e)}")
            return False
