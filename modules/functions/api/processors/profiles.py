"""
Profiles Module Processor for ReportMate
Handles user profiles and configuration using simple pass-through approach
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class ProfilesProcessor(BaseModuleProcessor):
    """
    Processor for profiles module data
    Uses simple pass-through approach to preserve all client data
    """
    
    @property
    def module_id(self) -> str:
        return "profiles"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process profiles module data - stores complete profiles data from client
        
        Args:
            device_data: Raw profiles data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete profiles data as received from client
        """
        try:
            logger.info(f"Processing profiles data for device {device_id}")
            
            # Extract profiles module data
            profiles_data = device_data.get('profiles', {})
            
            # Store complete profiles data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **profiles_data  # Include all profiles data as-is
            }
            
            logger.info(f"Successfully processed profiles data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing profiles data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate profiles module data
        
        Args:
            data: Profiles data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Profiles validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Profiles validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Profiles validation error: {str(e)}")
            return False
