"""
Management Module Processor for ReportMate
Handles system management features and administrative tools
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class ManagementProcessor(BaseModuleProcessor):
    """
    Processor for management module data
    Handles services, scheduled tasks, group policies, and system management
    """
    
    @property
    def module_id(self) -> str:
        """Return the unique identifier for this module"""
        return "management"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process management module data - stores complete management data from client
        
        Args:
            device_data: Raw management data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete management data as received from client
        """
        try:
            logger.info(f"Processing management data for device {device_id}")
            
            # Extract management module data
            management_data = device_data.get('management', {})
            
            # Store complete management data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **management_data  # Include all management data as-is
            }
            
            logger.info(f"Successfully processed management data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing management data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate management module data
        
        Args:
            data: Management data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Management validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Management validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Management validation error: {str(e)}")
            return False
