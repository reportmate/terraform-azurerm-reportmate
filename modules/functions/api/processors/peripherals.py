"""
Peripherals Module Processor for ReportMate
Handles peripheral device information including displays, printers, input devices, and USB devices
"""

import logging
from datetime import datetime
from typing import Dict, Any
from shared.base_processor import BaseModuleProcessor

logger = logging.getLogger(__name__)

class PeripheralsProcessor(BaseModuleProcessor):
    """
    Processor for peripherals module data
    Combines displays, printers, input devices, and USB devices into a unified peripheral view
    """
    
    @property
    def module_id(self) -> str:
        return "peripherals"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process peripherals module data - stores complete peripheral device data
        
        Args:
            device_data: Raw peripheral data from client
            device_id: Device identifier
            
        Returns:
            Dict: Complete peripherals data organized by device type
        """
        try:
            logger.info(f"Processing peripherals data for device {device_id}")
            
            # Extract peripherals module data
            peripherals_data = device_data.get('peripherals', {})
            
            # Organize peripheral data by categories
            processed_data = {
                'module_id': self.module_id,
                'device_id': device_id,
                'collected_at': datetime.utcnow().isoformat(),
                'displays': self._process_displays(peripherals_data),
                'printers': self._process_printers(peripherals_data),
                'usb_devices': self._process_usb_devices(peripherals_data),
                'input_devices': self._process_input_devices(peripherals_data),
                'audio_devices': self._process_audio_devices(peripherals_data),
                'bluetooth_devices': self._process_bluetooth_devices(peripherals_data),
                'camera_devices': self._process_camera_devices(peripherals_data),
                'storage_devices': self._process_storage_devices(peripherals_data),
                'summary': self._generate_summary(peripherals_data)
            }
            
            logger.info(f"Successfully processed peripherals data for device {device_id}")
            return processed_data
                
        except Exception as e:
            logger.error(f"Error processing peripherals data for device {device_id}: {str(e)}")
            raise
    
    def _process_displays(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process display and graphics information"""
        displays = {
            'graphics_cards': [],
            'monitors': [],
            'display_settings': {},
            'drivers': []
        }
        
        # Process video_info data
        video_info = data.get('displays_video_info', [])
        for card in video_info:
            displays['graphics_cards'].append({
                'model': card.get('model', 'Unknown'),
                'manufacturer': card.get('manufacturer', 'Unknown'),
                'driver_version': card.get('driver_version', 'Unknown'),
                'driver_date': card.get('driver_date', 'Unknown')
            })
        
        # Process display adapter registry data
        adapter_data = data.get('displays_registry_adapters', [])
        memory_data = data.get('displays_memory_info', [])
        
        # Combine adapter and memory information
        for adapter in adapter_data:
            displays['drivers'].append({
                'description': adapter.get('data', 'Unknown'),
                'registry_path': adapter.get('path', ''),
                'memory_size': self._find_memory_for_adapter(adapter.get('path', ''), memory_data)
            })
        
        return displays
    
    def _process_printers(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process printer information"""
        printers = {
            'installed_printers': [],
            'print_queues': [],
            'printer_drivers': []
        }
        
        # Process printers_info data
        printer_info = data.get('printers_info', [])
        for printer in printer_info:
            printers['installed_printers'].append({
                'name': printer.get('name', 'Unknown'),
                'driver': printer.get('driver', 'Unknown'),
                'location': printer.get('location', ''),
                'status': printer.get('status', 'Unknown'),
                'share_name': printer.get('sharename', ''),
                'attributes': printer.get('attributes', '')
            })
        
        return printers
    
    def _process_usb_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process USB device information"""
        usb = {
            'connected_devices': [],
            'device_details': []
        }
        
        # Process usb_devices data
        usb_devices = data.get('usb_devices', [])
        for device in usb_devices:
            usb['connected_devices'].append({
                'vendor': device.get('vendor', 'Unknown'),
                'vendor_id': device.get('vendor_id', ''),
                'model': device.get('model', 'Unknown'),
                'model_id': device.get('model_id', ''),
                'serial': device.get('serial', ''),
                'class': device.get('class', ''),
                'subclass': device.get('subclass', ''),
                'protocol': device.get('protocol', ''),
                'removable': device.get('removable', False)
            })
        
        return usb
    
    def _process_input_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input device information (keyboards, mice, etc.)"""
        input_devices = {
            'keyboards': [],
            'mice': [],
            'other_input': []
        }
        
        # Process keyboard data
        keyboards = data.get('input_devices_keyboards', [])
        for keyboard in keyboards:
            input_devices['keyboards'].append({
                'description': keyboard.get('data', 'Unknown'),
                'registry_path': keyboard.get('path', '')
            })
        
        # Process mice data
        mice = data.get('input_devices_mice', [])
        for mouse in mice:
            input_devices['mice'].append({
                'description': mouse.get('data', 'Unknown'),
                'registry_path': mouse.get('path', '')
            })
        
        return input_devices
    
    def _process_audio_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio device information"""
        audio = {
            'devices': []
        }
        
        audio_devices = data.get('audio_devices', [])
        for device in audio_devices:
            audio['devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', '')
            })
        
        return audio
    
    def _process_bluetooth_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Bluetooth device information"""
        bluetooth = {
            'paired_devices': []
        }
        
        bt_devices = data.get('bluetooth_devices', [])
        for device in bt_devices:
            bluetooth['paired_devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', '')
            })
        
        return bluetooth
    
    def _process_camera_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process camera and imaging device information"""
        cameras = {
            'imaging_devices': []
        }
        
        camera_devices = data.get('camera_devices', [])
        for device in camera_devices:
            cameras['imaging_devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', '')
            })
        
        return cameras
    
    def _process_storage_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process storage device information"""
        storage = {
            'logical_drives': []
        }
        
        storage_devices = data.get('storage_devices', [])
        for device in storage_devices:
            storage['logical_drives'].append({
                'device': device.get('device', 'Unknown'),
                'device_id': device.get('device_id', ''),
                'label': device.get('label', ''),
                'type': device.get('type', 'Unknown'),
                'size': device.get('size', 0),
                'encrypted': device.get('encrypted', False)
            })
        
        return storage
    
    def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all peripheral devices"""
        summary = {
            'total_displays': len(data.get('displays_video_info', [])),
            'total_printers': len(data.get('printers_info', [])),
            'total_usb_devices': len(data.get('usb_devices', [])),
            'total_keyboards': len(data.get('input_devices_keyboards', [])),
            'total_mice': len(data.get('input_devices_mice', [])),
            'total_audio_devices': len(data.get('audio_devices', [])),
            'total_bluetooth_devices': len(data.get('bluetooth_devices', [])),
            'total_cameras': len(data.get('camera_devices', [])),
            'total_storage_devices': len(data.get('storage_devices', []))
        }
        
        summary['total_peripherals'] = sum(summary.values())
        
        return summary
    
    def _find_memory_for_adapter(self, adapter_path: str, memory_data: list) -> str:
        """Find memory size for a specific display adapter"""
        # Extract adapter key from path
        import re
        match = re.search(r'\\(\d{4})\\', adapter_path)
        if match:
            adapter_key = match.group(1)
            for memory_entry in memory_data:
                if adapter_key in memory_entry.get('path', ''):
                    return memory_entry.get('data', 'Unknown')
        return 'Unknown'
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate peripherals module data
        
        Args:
            data: Peripherals data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['module_id', 'device_id']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Peripherals validation failed: missing required field '{field}'")
                    return False
            
            if data['module_id'] != self.module_id:
                logger.error(f"Peripherals validation failed: invalid module_id '{data['module_id']}'")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Peripherals validation error: {str(e)}")
            return False
