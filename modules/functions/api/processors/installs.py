"""
Installs Module Processor for ReportMate
Handles software installations and updates using simple pass-through approach
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class InstallsProcessor(BaseModuleProcessor):
    """
    Processor for installs module data
    Uses simple pass-through approach to preserve all client data
    """
    
    @property
    def module_id(self) -> str:
        return "installs"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process installs module data - stores complete installs data from client
        
        Args:
            device_data: Raw installs data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete installs data as received from client
        """
        try:
            logger.info(f"Processing installs data for device {device_id}")
            
            # Extract installs module data
            installs_data = device_data.get('installs', {})
            
            # Store complete installs data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **installs_data  # Include all installs data as-is
            }
            
            logger.info(f"Successfully processed installs data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing installs data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate installs module data
        
        Args:
            data: Installs data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Installs validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Installs validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Installs validation error: {str(e)}")
            return False
