"""
Security Module Processor for ReportMate
Handles security settings and configuration using simple pass-through approach
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class SecurityProcessor(BaseModuleProcessor):
    """
    Processor for security module data
    Uses simple pass-through approach to preserve all client data
    """
    
    @property
    def module_id(self) -> str:
        return "security"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process security module data - stores complete security data from client
        
        Args:
            device_data: Raw security data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete security data as received from client
        """
        try:
            logger.info(f"Processing security data for device {device_id}")
            
            # Extract security module data
            security_data = device_data.get('security', {})
            
            # Store complete security data as received from client
            # This preserves all the rich data from the client
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                **security_data  # Include all security data as-is
            }
            
            logger.info(f"Successfully processed security data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing security data for device {device_id}: {str(e)}")
            raise
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate security module data
        
        Args:
            data: Security data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Security validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Security validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Security validation error: {str(e)}")
            return False
