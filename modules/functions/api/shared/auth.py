"""
Authentication utilities for ReportMate API
"""

import logging
import hashlib
import hmac
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """
    Manages authentication for ReportMate API
    Supports passphrase-based authentication for machine groups
    """
    
    def __init__(self):
        self.client_passphrases = os.getenv('CLIENT_PASSPHRASES', '')
        self.enable_machine_groups = os.getenv('ENABLE_MACHINE_GROUPS', 'true').lower() == 'true'
        self.enable_business_units = os.getenv('ENABLE_BUSINESS_UNITS', 'true').lower() == 'true'
    
    def validate_passphrase(self, passphrase: str) -> bool:
        """
        Validate a client passphrase
        
        Args:
            passphrase: The passphrase to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not passphrase:
            return False
        
        # For development, allow a simple passphrase check
        # In production, this should check against hashed passphrases in the database
        if not self.client_passphrases:
            logger.warning("No client passphrases configured - allowing all requests")
            return True
        
        # Check against configured passphrases (comma-separated)
        valid_passphrases = [p.strip() for p in self.client_passphrases.split(',') if p.strip()]
        return passphrase in valid_passphrases
    
    def extract_auth_from_request(self, headers: Dict[str, Any]) -> Optional[str]:
        """
        Extract authentication information from request headers
        
        Args:
            headers: Request headers
            
        Returns:
            Passphrase if found, None otherwise
        """
        # Check Authorization header
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check custom header
        passphrase = headers.get('x-reportmate-passphrase', '')
        if passphrase:
            return passphrase
        
        return None
    
    def authenticate_request(self, headers: Dict[str, Any]) -> bool:
        """
        Authenticate a request based on headers
        
        Args:
            headers: Request headers
            
        Returns:
            True if authenticated, False otherwise
        """
        passphrase = self.extract_auth_from_request(headers)
        if not passphrase:
            logger.warning("No authentication credentials found in request")
            return False
        
        is_valid = self.validate_passphrase(passphrase)
        if not is_valid:
            logger.warning(f"Invalid passphrase provided")
        
        return is_valid
    
    async def authenticate_machine_group(self, passphrase: str) -> Dict[str, Any]:
        """
        Authenticate a machine group and return group information
        
        Args:
            passphrase: Machine group passphrase
            
        Returns:
            Authentication result with machine group info
        """
        try:
            if not self.validate_passphrase(passphrase):
                return {
                    'success': False,
                    'error': 'Invalid passphrase',
                    'machine_group': None,
                    'business_unit': None
                }
            
            # For now, return a default machine group
            # In production, this would query the database for the specific machine group
            return {
                'success': True,
                'machine_group': {
                    'id': 'default',
                    'name': 'Default Machine Group',
                    'description': 'Default machine group for authenticated devices'
                },
                'business_unit': {
                    'id': 'default',
                    'name': 'Default Business Unit',
                    'description': 'Default business unit'
                }
            }
            
        except Exception as e:
            logger.error(f"Error during machine group authentication: {e}")
            return {
                'success': False,
                'error': 'Authentication service error',
                'machine_group': None,
                'business_unit': None
            }
            logger.warning("No authentication credentials found in request")
            return False
        
        is_valid = self.validate_passphrase(passphrase)
        if not is_valid:
            logger.warning(f"Invalid passphrase provided")
        
        return is_valid

# Global authentication manager instance
auth_manager = AuthenticationManager()
