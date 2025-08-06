"""
Displays Module Processor for ReportMate
Handles display device and configuration information using simple pass-through approach
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class DisplaysProcessor(BaseModuleProcessor):
    """
    Processor for displays module data
    Uses simple pass-through approach to preserve all client data
    """
    
    @property
    def module_id(self) -> str:
        return "displays"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process displays module data - stores complete displays data from client
        
        Args:
            device_data: Raw displays data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete displays data as received from client
        """
        try:
            logger.info(f"Processing displays data for device {device_id}")
            
            # Extract displays module data
            displays_data = device_data.get('displays', {})
            
            # Store complete displays data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **displays_data  # Include all displays data as-is
            }
            
            logger.info(f"Successfully processed displays data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing displays data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate displays module data
        
        Args:
            data: Displays data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Displays validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Displays validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Displays validation error: {str(e)}")
            return False
