"""
ReportMate Base Module Processor
This module provides the base class and infrastructure for all data processors
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
import asyncio
import asyncpg
import os

logger = logging.getLogger(__name__)

class BaseModuleProcessor(ABC):
    """
    Abstract base class for all ReportMate module processors
    Provides common functionality for data validation, storage, and retrieval
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @property
    @abstractmethod
    def module_id(self) -> str:
        """Return the unique identifier for this module"""
        pass
    
    @abstractmethod
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process the incoming device data for this specific module
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed module data dictionary
        """
        pass
    
    @abstractmethod
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate the processed module data
        
        Args:
            data: Processed module data
            
        Returns:
            True if data is valid, False otherwise
        """
        pass
    
    async def store_module_data(self, data: Dict[str, Any], connection: asyncpg.Connection) -> bool:
        """
        Store the processed module data to the database
        
        Args:
            data: Processed and validated module data
            connection: Database connection
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Default implementation stores to a generic module_data table
            # Override in specific processors for custom storage logic
            await connection.execute("""
                INSERT INTO module_data (device_id, module_id, data, collected_at, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (device_id, module_id) 
                DO UPDATE SET 
                    data = EXCLUDED.data,
                    collected_at = EXCLUDED.collected_at,
                    updated_at = NOW()
            """, 
            data.get('device_id'),
            self.module_id,
            json.dumps(data),
            data.get('collected_at', datetime.utcnow()),
            datetime.utcnow()
            )
            
            self.logger.info(f"Stored {self.module_id} data for device {data.get('device_id')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store {self.module_id} data: {e}")
            return False
    
    async def retrieve_module_data(self, device_id: str, connection: asyncpg.Connection) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest module data for a device
        
        Args:
            device_id: Unique device identifier
            connection: Database connection
            
        Returns:
            Latest module data or None if not found
        """
        try:
            row = await connection.fetchrow("""
                SELECT data, collected_at, created_at, updated_at
                FROM module_data 
                WHERE device_id = $1 AND module_id = $2
                ORDER BY collected_at DESC
                LIMIT 1
            """, device_id, self.module_id)
            
            if row:
                data = json.loads(row['data'])
                data['_metadata'] = {
                    'collected_at': row['collected_at'].isoformat() if row['collected_at'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
                return data
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve {self.module_id} data: {e}")
            return None
    
    def get_string_value(self, data: Dict[str, Any], key: str, default: str = "") -> str:
        """Helper method to safely get string values from data"""
        value = data.get(key, default)
        return str(value) if value is not None else default
    
    def get_int_value(self, data: Dict[str, Any], key: str, default: int = 0) -> int:
        """Helper method to safely get integer values from data"""
        try:
            value = data.get(key, default)
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_long_value(self, data: Dict[str, Any], key: str, default: int = 0) -> int:
        """Helper method to safely get long values from data"""
        return self.get_int_value(data, key, default)
    
    def get_float_value(self, data: Dict[str, Any], key: str, default: float = 0.0) -> float:
        """Helper method to safely get float values from data"""
        try:
            value = data.get(key, default)
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool_value(self, data: Dict[str, Any], key: str, default: bool = False) -> bool:
        """Helper method to safely get boolean values from data"""
        value = data.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        if isinstance(value, (int, float)):
            return value != 0
        return default
    
    def get_datetime_value(self, data: Dict[str, Any], key: str) -> Optional[datetime]:
        """Helper method to safely get datetime values from data"""
        try:
            value = data.get(key)
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                # Try common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            return None
        except Exception:
            return None


class ModuleProcessorRegistry:
    """
    Registry for all module processors
    Manages initialization and access to processor instances
    """
    
    def __init__(self):
        self._processors: Dict[str, BaseModuleProcessor] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_processor(self, processor: BaseModuleProcessor):
        """Register a module processor"""
        self._processors[processor.module_id] = processor
        self.logger.info(f"Registered processor for module: {processor.module_id}")
    
    def get_processor(self, module_id: str) -> Optional[BaseModuleProcessor]:
        """Get a processor by module ID"""
        return self._processors.get(module_id)
    
    def get_all_processors(self) -> Dict[str, BaseModuleProcessor]:
        """Get all registered processors"""
        return self._processors.copy()
    
    def get_supported_modules(self) -> List[str]:
        """Get list of all supported module IDs"""
        return list(self._processors.keys())


# Global registry instance
registry = ModuleProcessorRegistry()
