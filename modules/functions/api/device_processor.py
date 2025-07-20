"""
Main Device Data Processor for ReportMate
Orchestrates all module processors and handles complete device data processing
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from .shared.base_processor import BaseModuleProcessor
from .shared.database import DatabaseManager
from .shared.auth import AuthenticationManager
from .processors import PROCESSOR_REGISTRY
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
            self.processors[module_id] = processor_class()
            self.logger.debug(f"Initialized {module_id} processor")
    
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
        
        # Process the module data
        processed_data = await processor.process_module_data(device_data, device_id)
        
        # Validate the processed data
        is_valid = await processor.validate_module_data(processed_data)
        if not is_valid:
            raise ValueError(f"Module {module_id} validation failed")
        
        return processed_data
    
    def _extract_device_id(self, device_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract unique device identifier from device data
        
        Args:
            device_data: Raw device data
            
        Returns:
            Device identifier or None if not found
        """
        # Try multiple sources for device identification
        device_id_sources = [
            ('hardware', 'motherboard_serial'),
            ('hardware', 'bios_serial'),
            ('system', 'system_info', 'uuid'),
            ('system', 'system_info', 'serial_number'),
            ('inventory', 'computer_name'),
            ('network', 'network_adapters', 0, 'mac_address')  # First adapter MAC
        ]
        
        for source in device_id_sources:
            try:
                value = device_data
                for key in source:
                    if isinstance(key, int):
                        # Array index
                        if isinstance(value, list) and len(value) > key:
                            value = value[key]
                        else:
                            break
                    else:
                        # Dictionary key
                        if isinstance(value, dict) and key in value:
                            value = value[key]
                        else:
                            break
                
                if value and isinstance(value, str) and len(value) > 5:
                    self.logger.debug(f"Device ID extracted from {'.'.join(map(str, source))}: {value}")
                    return value
                    
            except Exception as e:
                self.logger.debug(f"Failed to extract device ID from {source}: {e}")
                continue
        
        # Fallback: generate from computer name + MAC address
        try:
            computer_name = device_data.get('inventory', {}).get('computer_name', '')
            mac_address = ''
            
            adapters = device_data.get('network', {}).get('network_adapters', [])
            if adapters and len(adapters) > 0:
                mac_address = adapters[0].get('mac_address', '')
            
            if computer_name and mac_address:
                device_id = f"{computer_name}_{mac_address}".replace(':', '').replace('-', '')
                self.logger.debug(f"Generated fallback device ID: {device_id}")
                return device_id
                
        except Exception as e:
            self.logger.warning(f"Failed to generate fallback device ID: {e}")
        
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
        
        for module_id in PROCESSOR_REGISTRY.keys():
            if module_id in device_data and device_data[module_id]:
                available_modules.append(module_id)
        
        # Always try to process these core modules if any data is present
        core_modules = ['inventory', 'system', 'hardware']
        for module in core_modules:
            if module not in available_modules and any(key in device_data for key in device_data.keys()):
                available_modules.append(module)
        
        return available_modules
    
    async def _register_device(self, device_id: str, device_data: Dict[str, Any], 
                             machine_group: Dict[str, Any], business_unit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register or update device in database
        
        Args:
            device_id: Device identifier
            device_data: Raw device data
            machine_group: Machine group information
            business_unit: Business unit information
            
        Returns:
            Device record
        """
        # Extract basic device info for registration
        computer_name = device_data.get('inventory', {}).get('computer_name', device_id)
        manufacturer = device_data.get('hardware', {}).get('system_manufacturer', 'Unknown')
        model = device_data.get('hardware', {}).get('system_model', 'Unknown')
        
        device_record = {
            'device_id': device_id,
            'computer_name': computer_name,
            'manufacturer': manufacturer,
            'model': model,
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
