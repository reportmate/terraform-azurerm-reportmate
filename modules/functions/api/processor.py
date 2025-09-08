"""
Main Device Data Processor for ReportMate
Orchestrates all module processors and handles complete device data processing
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

# Add the current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from shared.base_processor import BaseModuleProcessor
from shared.database import DatabaseManager
from shared.auth import AuthenticationManager
from processors import PROCESSOR_REGISTRY
import json

logger = logging.getLogger(__name__)

class DeviceDataProcessor:
    """
    Main processor that orchestrates all module processors
    Handles complete device data ingestion and processing
    """
    
    def __init__(self, db_manager: DatabaseManager, auth_manager: AuthenticationManager):
        """
        Initialize the device data processor
        
        Args:
            db_manager: Database manager instance
            auth_manager: Authentication manager instance
        """
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.logger = logger
        
        # Initialize all module processors
        self.processors = {}
        for module_id, processor_class in PROCESSOR_REGISTRY.items():
            try:
                self.processors[module_id] = processor_class()
                self.logger.info(f"✅ DEBUG: Initialized processor for module '{module_id}'")
            except Exception as e:
                self.logger.error(f"❌ DEBUG: Failed to initialize processor for module '{module_id}': {e}")
        
        self.logger.info(f"🔍 DEBUG: Total processors initialized: {len(self.processors)}")
        self.logger.info(f"🔍 DEBUG: Available processor modules: {list(self.processors.keys())}")
        self.logger.info(f"🔍 DEBUG: Registry modules: {list(PROCESSOR_REGISTRY.keys())}")
    
    async def process_device_data(self, device_data: Dict[str, Any], machine_group_passphrase: str) -> Dict[str, Any]:
        """
        Process complete device data through all applicable modules
        
        Args:
            device_data: Raw device data payload
            machine_group_passphrase: Machine group authentication passphrase
            
        Returns:
            Processing result with status and processed data
        """
        try:
            self.logger.info("Starting device data processing")
            
            # Authenticate and get machine group info
            auth_result = await self.auth_manager.authenticate_machine_group(machine_group_passphrase)
            if not auth_result['success']:
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'details': auth_result['error']
                }
            
            machine_group = auth_result['machine_group']
            business_unit = auth_result['business_unit']
            
            # Extract device identification
            device_id = self._extract_device_id(device_data)
            if not device_id:
                return {
                    'success': False,
                    'error': 'Unable to identify device',
                    'details': 'Device data missing required identification fields'
                }
            
            # Register or update device
            device_record = await self._register_device(device_id, device_data, machine_group, business_unit)
            
            # Process each module
            processing_results = {}
            processing_errors = []
            
            # Determine which modules to process based on available data
            available_modules = self._detect_available_modules(device_data)
            self.logger.info(f"Detected {len(available_modules)} modules: {', '.join(available_modules)}")
            
            # Process modules in parallel
            module_tasks = []
            for module_id in available_modules:
                if module_id in self.processors:
                    task = self._process_module(module_id, device_data, device_id)
                    module_tasks.append(task)
            
            # Wait for all modules to complete
            module_results = await asyncio.gather(*module_tasks, return_exceptions=True)
            
            # Collect results and errors
            for i, result in enumerate(module_results):
                module_id = available_modules[i]
                
                if isinstance(result, Exception):
                    error_msg = f"Module {module_id} processing failed: {str(result)}"
                    self.logger.error(error_msg)
                    processing_errors.append(error_msg)
                else:
                    processing_results[module_id] = result
                    self.logger.debug(f"Module {module_id} processed successfully")
            
            # Store processed data in database
            storage_result = await self._store_processed_data(device_id, processing_results, device_record)
            
            # Generate summary
            summary = self._generate_processing_summary(processing_results, processing_errors)
            
            self.logger.info(f"Device data processing completed for {device_id}")
            
            return {
                'success': True,
                'device_id': device_id,
                'machine_group': machine_group['name'],
                'business_unit': business_unit['name'],
                'modules_processed': len(processing_results),
                'modules_failed': len(processing_errors),
                'processing_errors': processing_errors,
                'summary': summary,
                'storage_result': storage_result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Device data processing failed: {str(e)}")
            return {
                'success': False,
                'error': 'Processing failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def process_device_data_with_device_id(self, device_data: Dict[str, Any], machine_group_passphrase: str, device_id: str) -> Dict[str, Any]:
        """
        Process complete device data through all applicable modules with explicit device_id
        
        Args:
            device_data: Raw device data payload
            machine_group_passphrase: Machine group authentication passphrase
            device_id: Explicit device identifier (usually serial number)
            
        Returns:
            Processing result with status and processed data
        """
        try:
            self.logger.info(f"🔍 CRITICAL DEBUG: Starting device data processing with explicit device_id: {device_id}")
            self.logger.info(f"🔍 CRITICAL DEBUG: Received device_data keys: {list(device_data.keys())}")
            
            # Authenticate and get machine group info
            auth_result = await self.auth_manager.authenticate_machine_group(machine_group_passphrase)
            if not auth_result['success']:
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'details': auth_result['error']
                }
            
            machine_group = auth_result['machine_group']
            business_unit = auth_result['business_unit']
            
            # Use the provided device_id instead of extracting from data
            self.logger.info(f"Using provided device_id: {device_id}")
            
            # Register or update device
            device_record = await self._register_device(device_id, device_data, machine_group, business_unit)
            
            # Process each module
            processing_results = {}
            processing_errors = []
            
            # Determine which modules to process based on available data
            available_modules = self._detect_available_modules(device_data)
            self.logger.info(f"Detected {len(available_modules)} modules: {', '.join(available_modules)}")
            
            # Process modules in parallel
            module_tasks = []
            for module_id in available_modules:
                if module_id in self.processors:
                    task = self._process_module(module_id, device_data, device_id)
                    module_tasks.append(task)
            
            # Wait for all modules to complete
            module_results = await asyncio.gather(*module_tasks, return_exceptions=True)
            
            # Collect results and errors
            for i, result in enumerate(module_results):
                module_id = available_modules[i]
                
                if isinstance(result, Exception):
                    error_msg = f"Module {module_id} processing failed: {str(result)}"
                    self.logger.error(error_msg)
                    processing_errors.append(error_msg)
                else:
                    processing_results[module_id] = result
                    self.logger.debug(f"Module {module_id} processed successfully")
            
            # Store processed data in database
            storage_result = await self._store_processed_data(device_id, processing_results, device_record)
            
            # Generate summary
            summary = self._generate_processing_summary(processing_results, processing_errors)
            
            self.logger.info(f"Device data processing completed for {device_id}")
            
            return {
                'success': True,
                'device_id': device_id,
                'machine_group': machine_group['name'],
                'business_unit': business_unit['name'],
                'modules_processed': len(processing_results),
                'modules_failed': len(processing_errors),
                'processing_errors': processing_errors,
                'summary': summary,
                'storage_result': storage_result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Device data processing with explicit device_id failed: {str(e)}")
            return {
                'success': False,
                'error': 'Processing failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _process_module(self, module_id: str, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process a single module
        
        Args:
            module_id: Module identifier
            device_data: Raw device data
            device_id: Device identifier
            
        Returns:
            Processed module data
        """
        processor = self.processors[module_id]
        
        # Extract module data with support for both lowercase and capitalized keys
        module_data = None
        if module_id in device_data:
            module_data = device_data[module_id]
        elif module_id.capitalize() in device_data:
            module_data = device_data[module_id.capitalize()]
            # Create a copy of device_data with lowercase key for processor compatibility
            device_data_copy = dict(device_data)
            device_data_copy[module_id] = module_data
            device_data = device_data_copy
        
        if module_data is None:
            raise ValueError(f"Module {module_id} data not found in device payload")
        
        # Process the module data
        processed_data = await processor.process_module_data(device_data, device_id)
        
        # Validate the processed data
        is_valid = await processor.validate_module_data(processed_data)
        if not is_valid:
            raise ValueError(f"Module {module_id} validation failed")
        
        return processed_data
    
    def _extract_device_id(self, device_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract device serial number from payload structure
        Uses the metadata.serialNumber field as the primary identifier for API routing
        
        Args:
            device_data: Raw device data
            
        Returns:
            Device serial number or None if not found
        """
        # Primary: metadata.serialNumber field (for API routing)
        try:
            metadata = device_data.get('metadata', {})
            if metadata:
                serial_number = metadata.get('serialNumber')
                if serial_number and isinstance(serial_number, str) and len(serial_number.strip()) > 2:
                    self.logger.debug(f"Device serial number extracted from metadata.serialNumber: {serial_number}")
                    return serial_number.strip()
        except Exception as e:
            self.logger.debug(f"Failed to extract metadata.serialNumber: {e}")
        
        # Fallback: Try top-level serialNumber
        try:
            serial_number = device_data.get('serialNumber')
            if serial_number and isinstance(serial_number, str) and len(serial_number.strip()) > 2:
                self.logger.debug(f"Device serial number extracted from top-level: {serial_number}")
                return serial_number.strip()
        except Exception as e:
            self.logger.debug(f"Failed to extract top-level serialNumber: {e}")
        
        # Fallback: Try _metadata device_id field
        try:
            metadata = device_data.get('_metadata', {})
            if metadata:
                device_id = metadata.get('device_id')
                if device_id and isinstance(device_id, str) and len(device_id.strip()) > 2:
                    self.logger.debug(f"Device ID extracted from _metadata.device_id: {device_id}")
                    return device_id.strip()
        except Exception as e:
            self.logger.debug(f"Failed to extract device ID from metadata: {e}")
            
        # Last resort: Try inventory module
        try:
            inventory = device_data.get('inventory', {})
            if inventory:
                serial_sources = ['serialNumber', 'serial_number', 'device_serial']
                for field in serial_sources:
                    serial = inventory.get(field)
                    if serial and isinstance(serial, str) and len(serial.strip()) > 2:
                        self.logger.debug(f"Device ID extracted from inventory.{field}: {serial}")
                        return serial.strip()
        except Exception as e:
            self.logger.debug(f"Failed to extract device ID from inventory: {e}")
        
        self.logger.warning("No valid device serial number found in data")
        return None
    
    def _extract_device_uuid(self, device_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract device UUID from payload structure
        Uses the metadata.deviceId field as the primary UUID for device registration
        
        Args:
            device_data: Raw device data
            
        Returns:
            Device UUID or None if not found
        """
        # Primary: metadata.deviceId field (contains the proper UUID)
        try:
            metadata = device_data.get('metadata', {})
            if metadata:
                device_uuid = metadata.get('deviceId')
                if device_uuid and isinstance(device_uuid, str) and len(device_uuid.strip()) > 10:
                    # Validate UUID format (basic check)
                    uuid_str = device_uuid.strip()
                    if '-' in uuid_str and len(uuid_str) >= 32:
                        self.logger.debug(f"Device UUID extracted from metadata.deviceId: {uuid_str}")
                        return uuid_str
        except Exception as e:
            self.logger.debug(f"Failed to extract metadata.deviceId: {e}")
        
        # Fallback: Top-level deviceId field 
        try:
            device_uuid = device_data.get('deviceId')
            if device_uuid and isinstance(device_uuid, str) and len(device_uuid.strip()) > 10:
                # Validate UUID format (basic check)
                uuid_str = device_uuid.strip()
                if '-' in uuid_str and len(uuid_str) >= 32:
                    self.logger.debug(f"Device UUID extracted from top-level deviceId: {uuid_str}")
                    return uuid_str
        except Exception as e:
            self.logger.debug(f"Failed to extract top-level deviceId: {e}")
        
        # Fallback: Try inventory module UUID
        try:
            inventory = device_data.get('inventory', {})
            if inventory:
                uuid_sources = ['uuid', 'deviceId', 'device_uuid']
                for field in uuid_sources:
                    uuid_val = inventory.get(field)
                    if uuid_val and isinstance(uuid_val, str) and len(uuid_val.strip()) > 10:
                        uuid_str = uuid_val.strip()
                        if '-' in uuid_str and len(uuid_str) >= 32:
                            self.logger.debug(f"Device UUID extracted from inventory.{field}: {uuid_str}")
                            return uuid_str
        except Exception as e:
            self.logger.debug(f"Failed to extract device UUID from inventory: {e}")
        
        self.logger.warning("No valid device UUID found in data")
        return None
    
    def _detect_available_modules(self, device_data: Dict[str, Any]) -> List[str]:
        """
        Detect which modules have data available in the payload
        
        Args:
            device_data: Raw device data
            
        Returns:
            List of module IDs with available data
        """
        available_modules = []
        
        # DEBUG: Log the actual structure being received
        self.logger.info(f"🔍 DEBUG: device_data top-level keys: {list(device_data.keys())}")
        self.logger.info(f"🔍 DEBUG: PROCESSOR_REGISTRY keys: {list(PROCESSOR_REGISTRY.keys())}")
        
        # Only process modules that actually have data in the payload
        for module_id in PROCESSOR_REGISTRY.keys():
            # Check both lowercase (processor registry) and capitalized (client payload) versions
            data_found = False
            module_data = None
            
            # Check lowercase key first (processor registry format)
            if module_id in device_data and device_data[module_id] is not None:
                data_found = True
                module_data = device_data[module_id]
                self.logger.info(f"🔍 DEBUG: Found module '{module_id}' (lowercase) in device_data")
            # Check capitalized key (client payload format)
            elif module_id.capitalize() in device_data and device_data[module_id.capitalize()] is not None:
                data_found = True
                module_data = device_data[module_id.capitalize()]
                self.logger.info(f"🔍 DEBUG: Found module '{module_id}' as '{module_id.capitalize()}' (capitalized) in device_data")
            
            if data_found:
                self.logger.info(f"🔍 DEBUG: Module '{module_id}' data type: {type(module_data)}")
                self.logger.info(f"🔍 DEBUG: Module '{module_id}' data keys: {list(module_data.keys()) if isinstance(module_data, dict) else 'not a dict'}")
                available_modules.append(module_id)
            else:
                # Check if either version exists but is None/missing
                if module_id in device_data:
                    if device_data[module_id] is None:
                        self.logger.info(f"🔍 DEBUG: Module '{module_id}' (lowercase) exists but is None")
                    else:
                        self.logger.info(f"🔍 DEBUG: Module '{module_id}' (lowercase) exists but was falsy (empty): {device_data[module_id]}")
                elif module_id.capitalize() in device_data:
                    cap_data = device_data[module_id.capitalize()]
                    if cap_data is None:
                        self.logger.info(f"🔍 DEBUG: Module '{module_id}' as '{module_id.capitalize()}' exists but is None")
                    else:
                        self.logger.info(f"🔍 DEBUG: Module '{module_id}' as '{module_id.capitalize()}' exists but was falsy (empty): {cap_data}")
                # Only log once for missing modules to avoid spam
                elif module_id == 'installs':
                    self.logger.info(f"🔍 DEBUG: Module '{module_id}' not found in device_data keys: {list(device_data.keys())}")
        
        # REMOVED: The problematic "core modules" forcing logic that was overwriting existing data
        # This was causing modules NOT sent by runner.exe to get processed with empty data,
        # which would overwrite existing good data in the database.
        
        self.logger.info(f"Processing only modules with actual data: {available_modules}")
        return available_modules
    
    async def _register_device(self, device_id: str, device_data: Dict[str, Any], 
                             machine_group: Dict[str, Any], business_unit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register or update device in database
        
        Args:
            device_id: Device serial number (for API routing)
            device_data: Raw device data
            machine_group: Machine group information
            business_unit: Business unit information
            
        Returns:
            Device record
        """
        # Extract proper device UUID from top-level data
        device_uuid = self._extract_device_uuid(device_data)
        if not device_uuid:
            raise ValueError(f"No valid device UUID found in device data for device {device_id}")
        
        # Extract device information for registration
        computer_name = device_data.get('inventory', {}).get('computer_name', device_id)
        manufacturer = device_data.get('hardware', {}).get('system_manufacturer')
        model = device_data.get('hardware', {}).get('system_model')
        
        # Extract client version from metadata first, then fallback to top-level
        client_version = None
        try:
            # Primary: Check metadata.clientVersion (ReportMate Windows client format)
            metadata = device_data.get('metadata', {})
            if metadata and 'clientVersion' in metadata:
                client_version = metadata['clientVersion']
                self.logger.debug(f"Client version extracted from metadata.clientVersion: {client_version}")
            # Fallback: Check top-level clientVersion
            elif 'clientVersion' in device_data:
                client_version = device_data['clientVersion']
                self.logger.debug(f"Client version extracted from top-level clientVersion: {client_version}")
        except Exception as e:
            self.logger.debug(f"Failed to extract client version: {e}, leaving empty")
            client_version = None
        
        self.logger.info(f"🔍 REGISTER DEBUG: Device UUID: {device_uuid}, Serial: {device_id}")
        
        device_record = {
            'id': device_id,  # This will be the serial number (primary key for API routing)
            'device_id': device_uuid,  # This will be the actual device UUID
            'serial_number': device_id,  # This will also be the serial number
            'computer_name': computer_name,
            'manufacturer': manufacturer,
            'model': model,
            'client_version': client_version,
            'machine_group_id': machine_group['id'],
            'business_unit_id': business_unit['id'],
            'last_seen': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        # Store in database
        await self.db_manager.upsert_device(device_record)
        
        return device_record
    
    async def _store_processed_data(self, device_id: str, processing_results: Dict[str, Any], 
                                  device_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store processed module data in database
        
        Args:
            device_id: Device identifier
            processing_results: Results from all module processors
            device_record: Device record
            
        Returns:
            Storage result summary
        """
        storage_results = {}
        
        for module_id, module_data in processing_results.items():
            try:
                # Store module data
                await self.db_manager.store_module_data(device_id, module_id, module_data)
                storage_results[module_id] = {'success': True}
                
            except Exception as e:
                self.logger.error(f"Failed to store {module_id} data for {device_id}: {e}")
                storage_results[module_id] = {'success': False, 'error': str(e)}
        
        # Update device last seen timestamp
        await self.db_manager.update_device_last_seen(device_id)
        
        return {
            'modules_stored': len([r for r in storage_results.values() if r['success']]),
            'modules_failed': len([r for r in storage_results.values() if not r['success']]),
            'details': storage_results
        }
    
    def _generate_processing_summary(self, processing_results: Dict[str, Any], 
                                   processing_errors: List[str]) -> Dict[str, Any]:
        """
        Generate summary of processing results
        
        Args:
            processing_results: Results from all module processors
            processing_errors: List of processing errors
            
        Returns:
            Processing summary
        """
        summary = {
            'total_modules': len(PROCESSOR_REGISTRY),
            'modules_processed': len(processing_results),
            'modules_failed': len(processing_errors),
            'success_rate': len(processing_results) / len(PROCESSOR_REGISTRY) * 100 if PROCESSOR_REGISTRY else 0,
            'module_summaries': {}
        }
        
        # Include summary from each module
        for module_id, module_data in processing_results.items():
            if 'summary' in module_data:
                summary['module_summaries'][module_id] = module_data['summary']
        
        return summary
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get current status and latest data for a device
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device status and summary
        """
        try:
            device_record = await self.db_manager.get_device(device_id)
            if not device_record:
                return {
                    'success': False,
                    'error': 'Device not found'
                }
            
            # Get latest module data summaries
            module_summaries = {}
            for module_id in PROCESSOR_REGISTRY.keys():
                latest_data = await self.db_manager.get_latest_module_data(device_id, module_id)
                if latest_data and 'summary' in latest_data:
                    module_summaries[module_id] = latest_data['summary']
            
            return {
                'success': True,
                'device_record': device_record,
                'module_summaries': module_summaries,
                'last_updated': device_record.get('last_seen'),
                'available_modules': list(module_summaries.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get device status for {device_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get overall processing statistics
        
        Returns:
            Processing statistics across all devices and modules
        """
        try:
            stats = await self.db_manager.get_processing_statistics()
            
            return {
                'success': True,
                'statistics': stats,
                'available_processors': list(PROCESSOR_REGISTRY.keys()),
                'processor_info': {
                    module_id: {
                        'class_name': processor_class.__name__,
                        'module_path': processor_class.__module__
                    }
                    for module_id, processor_class in PROCESSOR_REGISTRY.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
# Force update 08/07/2025 11:16:07
