"""
Printers Module Processor for ReportMate
Handles printer information and configuration using simple pass-through approach
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class PrintersProcessor(BaseModuleProcessor):
    """
    Processor for printers module data
    Uses simple pass-through approach to preserve all client data
    """
    
    @property
    def module_id(self) -> str:
        return "printers"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process printers module data - stores complete printers data from client
        
        Args:
            device_data: Raw printers data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete printers data as received from client
        """
        try:
            logger.info(f"Processing printers data for device {device_id}")
            
            # Extract printers module data
            printers_data = device_data.get('printers', {})
            
            # Store complete printers data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **printers_data  # Include all printers data as-is
            }
            
            logger.info(f"Successfully processed printers data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing printers data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate printers module data
        
        Args:
            data: Printers data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Printers validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Printers validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Printers validation error: {str(e)}")
            return False
