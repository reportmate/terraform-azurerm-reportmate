"""
Hardware Module Processor for ReportMate
Handles physical device hardware information
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json
import re

logger = logging.getLogger(__name__)

class HardwareProcessor(BaseModuleProcessor):
    """
    Processor for hardware module data
    Handles CPU, memory, storage, graphics, and other hardware components
    """
    
    @property
    def module_id(self) -> str:
        return "hardware"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process hardware data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed hardware data
        """
        self.logger.debug(f"Processing hardware module for device {device_id}")
        
        # Extract hardware data from the device payload
        hardware_data = device_data.get('hardware', {})
        system_info = device_data.get('system', {})
        
        # Build processed hardware data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'manufacturer': self._extract_manufacturer(hardware_data, system_info),
            'model': self._extract_model(hardware_data, system_info),
            'processor': self._process_processor_info(hardware_data),
            'memory': self._process_memory_info(hardware_data),
            'storage': self._process_storage_info(hardware_data),
            'graphics': self._process_graphics_info(hardware_data),
            'thermal': self._process_thermal_info(hardware_data),
            'power': self._process_power_info(hardware_data)
        }
        
        # Calculate total memory in MB for summary
        total_memory_mb = processed_data['memory'].get('total_physical', 0) // (1024 * 1024) if processed_data['memory'].get('total_physical') else 0
        
        self.logger.info(f"Hardware processed - Manufacturer: {processed_data['manufacturer']}, "
                        f"Model: {processed_data['model']}, CPU: {processed_data['processor'].get('name', 'Unknown')}, "
                        f"Memory: {total_memory_mb}MB, Storage devices: {len(processed_data['storage'])}, "
                        f"Graphics: {processed_data['graphics'].get('name', 'Unknown')}")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate hardware module data
        
        Args:
            data: Processed hardware data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'processor', 'memory']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Hardware validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Hardware validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        # Validate processor has at least a name
        if not data['processor'].get('name'):
            self.logger.warning("Hardware validation failed - processor missing name")
            return False
        
        return True
    
    def _extract_manufacturer(self, hardware_data: Dict[str, Any], system_info: Dict[str, Any]) -> str:
        """Extract manufacturer from various sources"""
        manufacturer = (
            hardware_data.get('manufacturer') or
            system_info.get('hardware_vendor') or
            system_info.get('manufacturer') or
            'Unknown'
        )
        return self._clean_manufacturer_name(str(manufacturer))
    
    def _extract_model(self, hardware_data: Dict[str, Any], system_info: Dict[str, Any]) -> str:
        """Extract model from various sources"""
        model = (
            hardware_data.get('model') or
            system_info.get('hardware_model') or
            system_info.get('model') or
            'Unknown'
        )
        return self._clean_product_name(str(model))
    
    def _process_processor_info(self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process processor information"""
        processor = hardware_data.get('processor', {})
        
        return {
            'name': self._clean_processor_name(processor.get('name', 'Unknown')),
            'manufacturer': self._clean_manufacturer_name(processor.get('manufacturer', '')),
            'architecture': processor.get('architecture', 'Unknown'),
            'cores': self.get_int_value(processor, 'cores', 0),
            'logical_processors': self.get_int_value(processor, 'logical_processors', 0),
            'base_speed': self.get_float_value(processor, 'base_speed', 0.0),
            'max_speed': self.get_float_value(processor, 'max_speed', 0.0),
            'socket': processor.get('socket', ''),
            'cache_l1': self.get_int_value(processor, 'cache_l1', 0),
            'cache_l2': self.get_int_value(processor, 'cache_l2', 0),
            'cache_l3': self.get_int_value(processor, 'cache_l3', 0)
        }
    
    def _process_memory_info(self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory information"""
        memory = hardware_data.get('memory', {})
        
        memory_info = {
            'total_physical': self.get_long_value(memory, 'total_physical', 0),
            'available_physical': self.get_long_value(memory, 'available_physical', 0),
            'total_virtual': self.get_long_value(memory, 'total_virtual', 0),
            'available_virtual': self.get_long_value(memory, 'available_virtual', 0),
            'modules': []
        }
        
        # Process memory modules
        modules = memory.get('modules', [])
        for module in modules:
            if isinstance(module, dict):
                memory_info['modules'].append({
                    'location': module.get('location', ''),
                    'manufacturer': self._clean_manufacturer_name(module.get('manufacturer', '')),
                    'type': module.get('type', 'Unknown'),
                    'capacity': self.get_long_value(module, 'capacity', 0),
                    'speed': self.get_int_value(module, 'speed', 0),
                    'part_number': module.get('part_number', '')
                })
        
        return memory_info
    
    def _process_storage_info(self, hardware_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process storage device information"""
        storage_devices = []
        storage_list = hardware_data.get('storage', [])
        
        for device in storage_list:
            if isinstance(device, dict):
                storage_devices.append({
                    'name': device.get('name', 'Unknown'),
                    'type': device.get('type', 'Unknown'),
                    'capacity': self.get_long_value(device, 'capacity', 0),
                    'free_space': self.get_long_value(device, 'free_space', 0),
                    'interface': device.get('interface', 'Unknown'),
                    'health': device.get('health', 'Unknown'),
                    'manufacturer': self._clean_manufacturer_name(device.get('manufacturer', '')),
                    'model': device.get('model', ''),
                    'serial': device.get('serial', ''),
                    'firmware': device.get('firmware', '')
                })
        
        return storage_devices
    
    def _process_graphics_info(self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process graphics card information"""
        graphics = hardware_data.get('graphics', {})
        
        return {
            'name': self._clean_product_name(graphics.get('name', 'Unknown')),
            'manufacturer': self._clean_manufacturer_name(graphics.get('manufacturer', '')),
            'memory_size': self.get_float_value(graphics, 'memory_size', 0.0),
            'driver_version': graphics.get('driver_version', ''),
            'driver_date': graphics.get('driver_date', ''),
            'resolution': graphics.get('resolution', ''),
            'refresh_rate': self.get_int_value(graphics, 'refresh_rate', 0)
        }
    
    def _process_thermal_info(self, hardware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process thermal information"""
        thermal = hardware_data.get('thermal', {})
        
        if not thermal:
            return None
        
        cpu_temp = self.get_int_value(thermal, 'cpu_temperature', 0)
        gpu_temp = self.get_int_value(thermal, 'gpu_temperature', 0)
        
        if cpu_temp == 0 and gpu_temp == 0:
            return None
        
        return {
            'cpu_temperature': cpu_temp,
            'gpu_temperature': gpu_temp,
            'system_temperature': self.get_int_value(thermal, 'system_temperature', 0)
        }
    
    def _process_power_info(self, hardware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process power/battery information"""
        power = hardware_data.get('power', {})
        
        if not power:
            return None
        
        return {
            'battery_present': self.get_bool_value(power, 'battery_present', False),
            'battery_level': self.get_int_value(power, 'battery_level', 0),
            'battery_status': power.get('battery_status', 'Unknown'),
            'power_source': power.get('power_source', 'Unknown')
        }
    
    def _clean_manufacturer_name(self, name: str) -> str:
        """Clean manufacturer name"""
        if not name:
            return ''
        
        # Common manufacturer name mappings
        name = name.strip()
        mappings = {
            'LENOVO': 'Lenovo',
            'DELL INC.': 'Dell',
            'Dell Inc.': 'Dell',
            'Hewlett-Packard': 'HP',
            'HP Inc.': 'HP',
            'ASUS': 'ASUS',
            'ASUSTeK Computer Inc.': 'ASUS',
            'Microsoft Corporation': 'Microsoft',
            'Apple Inc.': 'Apple'
        }
        
        return mappings.get(name, name)
    
    def _clean_product_name(self, name: str) -> str:
        """Clean product name"""
        if not name:
            return ''
        
        # Remove common suffixes and clean up
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
        
        return name
    
    def _clean_processor_name(self, name: str) -> str:
        """Clean processor name"""
        if not name:
            return ''
        
        name = name.strip()
        
        # Remove common processor name clutter
        name = re.sub(r'\s+CPU.*$', '', name)  # Remove " CPU @ X.XGHz" suffix
        name = re.sub(r'\s+@.*$', '', name)   # Remove "@ X.XGHz" suffix
        name = re.sub(r'\s+\d+\.\d+GHz.*$', '', name)  # Remove "X.XGHz" suffix
        name = re.sub(r'\s+', ' ', name)      # Normalize whitespace
        
        return name
