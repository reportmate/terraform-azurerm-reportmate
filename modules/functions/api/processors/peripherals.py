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
        """Process display information - ONLY actual display devices, NO graphics cards"""
        displays = {
            'monitors': [],
            'display_settings': {},
            'drivers': []
            # REMOVED: 'graphics_cards' - these belong in hardware module, not peripherals
        }
        
        # IMPORTANT: Do NOT process videoInfo here - that contains graphics cards which belong in hardware module
        # The PeripheralsModuleProcessor.cs only collects external monitors, not graphics cards
        
        # Process ACTUAL display devices/monitors (external monitors, internal displays)
        # Look for actual monitor data from different sources
            
        # Process ACTUAL display devices/monitors (external monitors, internal displays)
        # Look for actual monitor data from different sources
        monitor_data = []
        
        # From displays module (actual monitor devices)
        if 'displays' in data:
            displays_section = data['displays']
            # Look for actual monitor/display device data
            if 'externalMonitors' in displays_section:
                monitor_data.extend(displays_section.get('externalMonitors', []))
            if 'pnpDisplays' in displays_section:
                monitor_data.extend(displays_section.get('pnpDisplays', []))
            if 'edidData' in displays_section:
                monitor_data.extend(displays_section.get('edidData', []))
                
        # From peripherals.displays structure (should contain actual monitors)
        displays_info = data.get('displays_device_info', [])
        if displays_info:
            monitor_data.extend(displays_info)
            
        # Process actual monitor devices
        for monitor in monitor_data:
            displays['monitors'].append({
                'name': monitor.get('friendlyName', monitor.get('name', 'Unknown Monitor')),
                'manufacturer': monitor.get('manufacturer', 'Unknown'),
                'model': monitor.get('model', monitor.get('deviceDescription', 'Unknown')),
                'serial_number': monitor.get('serialNumber', ''),
                'device_id': monitor.get('pnpDeviceId', monitor.get('deviceId', '')),
                'connection_type': monitor.get('connectionType', 'Unknown'),
                'is_external': monitor.get('isExternal', True),
                'is_primary': monitor.get('isPrimary', False),
                'resolution': monitor.get('resolution', 'Unknown'),
                'type': 'monitor'  # Mark as actual monitor/display
            })
        
        # Process display adapter registry data
        adapter_data = data.get('displays_registry_adapters', [])
        memory_data = data.get('displays_memory_info', [])
        
        # Handle Windows client structure
        if not adapter_data and 'displays' in data:
            displays_section = data['displays']
            adapter_data = displays_section.get('registryAdapters', [])
            memory_data = displays_section.get('memoryInfo', [])
        
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
        
        # Process printers_info data - handle both structures
        printer_info = data.get('printers_info', [])  # Direct API structure
        if not printer_info and 'printers' in data:
            # Windows client structure: peripherals.printers.installedPrinters
            printers_section = data['printers']
            printer_info = printers_section.get('installedPrinters', [])
        
        for printer in printer_info:
            printer_name = printer.get('name', 'Unknown')
            
            # Filter out virtual printers that shouldn't be considered real hardware
            if any(virtual_name.lower() in printer_name.lower() for virtual_name in [
                'Microsoft Print to PDF',
                'Microsoft XPS Document Writer', 
                'Fax',
                'OneNote'
            ]):
                continue
                
            printers['installed_printers'].append({
                'name': printer_name,
                'driver': printer.get('driver', 'Unknown'),
                'location': printer.get('location', ''),
                'status': printer.get('status', 'Unknown'),
                'share_name': printer.get('sharename', printer.get('shareName', '')),
                'attributes': printer.get('attributes', '')
            })
        
        return printers
    
    def _process_usb_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process USB device information"""
        usb = {
            'connected_devices': [],
            'device_details': []
        }
        
        # Process usb_devices data - handle both structures
        usb_devices = data.get('usb_devices', [])  # Direct API structure
        if not usb_devices and 'usbDevices' in data:
            # Windows client structure: peripherals.usbDevices.connectedDevices
            usb_section = data['usbDevices']
            usb_devices = usb_section.get('connectedDevices', [])
        
        for device in usb_devices:
            usb['connected_devices'].append({
                'vendor': device.get('vendor', 'Unknown'),
                'vendor_id': device.get('vendor_id', device.get('vendorId', '')),
                'model': device.get('model', 'Unknown'),
                'model_id': device.get('model_id', device.get('modelId', '')),
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
        
        # Process keyboard data - handle both structures
        keyboards = data.get('input_devices_keyboards', [])  # Direct API structure
        mice = data.get('input_devices_mice', [])  # Direct API structure
        
        if not keyboards and 'inputDevices' in data:
            # Windows client structure: peripherals.inputDevices.keyboards
            input_section = data['inputDevices']
            keyboards = input_section.get('keyboards', [])
            mice = input_section.get('mice', [])
        
        for keyboard in keyboards:
            input_devices['keyboards'].append({
                'description': keyboard.get('data', keyboard.get('description', 'Unknown')),
                'registry_path': keyboard.get('path', keyboard.get('registryPath', '')),
                'device_type': keyboard.get('deviceType', '')
            })
        
        # Process mice data
        for mouse in mice:
            input_devices['mice'].append({
                'description': mouse.get('data', mouse.get('description', 'Unknown')),
                'registry_path': mouse.get('path', mouse.get('registryPath', '')),
                'device_type': mouse.get('deviceType', '')
            })
        
        return input_devices
    
    def _process_audio_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio device information"""
        audio = {
            'devices': []
        }
        
        # Handle both structures
        audio_devices = data.get('audio_devices', [])  # Direct API structure
        if not audio_devices and 'audioDevices' in data:
            # Windows client structure: peripherals.audioDevices.devices
            audio_section = data['audioDevices']
            audio_devices = audio_section.get('devices', [])
        
        for device in audio_devices:
            audio['devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', device.get('registryPath', ''))
            })
        
        return audio
    
    def _process_bluetooth_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Bluetooth device information"""
        bluetooth = {
            'paired_devices': []
        }
        
        # Handle both structures
        bt_devices = data.get('bluetooth_devices', [])  # Direct API structure
        if not bt_devices and 'bluetoothDevices' in data:
            # Windows client structure: peripherals.bluetoothDevices.devices
            bt_section = data['bluetoothDevices']
            bt_devices = bt_section.get('devices', [])
        
        for device in bt_devices:
            bluetooth['paired_devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', device.get('registryPath', ''))
            })
        
        return bluetooth
    
    def _process_camera_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process camera and imaging device information"""
        cameras = {
            'imaging_devices': []
        }
        
        # Handle both structures
        camera_devices = data.get('camera_devices', [])  # Direct API structure
        if not camera_devices and 'cameraDevices' in data:
            # Windows client structure: peripherals.cameraDevices.devices
            camera_section = data['cameraDevices']
            camera_devices = camera_section.get('devices', [])
        
        for device in camera_devices:
            cameras['imaging_devices'].append({
                'name': device.get('name', 'Unknown'),
                'data': device.get('data', ''),
                'registry_path': device.get('path', device.get('registryPath', ''))
            })
        
        return cameras
    
    def _process_storage_devices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process storage device information"""
        storage = {
            'logical_drives': []
        }
        
        # Handle both structures
        storage_devices = data.get('storage_devices', [])  # Direct API structure
        if not storage_devices and 'storageDevices' in data:
            # Windows client structure: peripherals.storageDevices.devices
            storage_section = data['storageDevices']
            storage_devices = storage_section.get('devices', [])
        
        for device in storage_devices:
            storage['logical_drives'].append({
                'device': device.get('device', 'Unknown'),
                'device_id': device.get('device_id', device.get('deviceId', '')),
                'label': device.get('label', ''),
                'type': device.get('type', 'Unknown'),
                'size': device.get('size', 0),
                'encrypted': device.get('encrypted', False)
            })
        
        return storage
    
    def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all peripheral devices"""
        # Handle both direct API structure and Windows client structure
        displays_count = 0
        printers_count = 0
        usb_count = 0
        keyboards_count = 0
        mice_count = 0
        audio_count = 0
        bluetooth_count = 0
        cameras_count = 0
        storage_count = 0
        
        # Count ACTUAL monitors/displays only, NOT graphics cards
        # Direct API structure - look for actual display device data
        displays_count = len(data.get('displays_device_info', []))
        printers_count = len(data.get('printers_info', []))
        usb_count = len(data.get('usb_devices', []))
        keyboards_count = len(data.get('input_devices_keyboards', []))
        mice_count = len(data.get('input_devices_mice', []))
        audio_count = len(data.get('audio_devices', []))
        bluetooth_count = len(data.get('bluetooth_devices', []))
        cameras_count = len(data.get('camera_devices', []))
        storage_count = len(data.get('storage_devices', []))
        
        # Windows client structure - look for actual monitor/display devices
        if displays_count == 0 and 'displays' in data:
            displays_section = data['displays']
            # Count external monitors, PnP displays, EDID data, etc. - NOT videoInfo (graphics cards)
            displays_count = (
                len(displays_section.get('externalMonitors', [])) + 
                len(displays_section.get('pnpDisplays', [])) + 
                len(displays_section.get('edidData', []))
            )
        if printers_count == 0 and 'printers' in data:
            printers_count = len(data['printers'].get('registryPrinters', []))
        if usb_count == 0 and 'usbDevices' in data:
            usb_count = len(data['usbDevices'].get('connectedDevices', []))
        if keyboards_count == 0 and 'inputDevices' in data:
            keyboards_count = len(data['inputDevices'].get('keyboards', []))
        if mice_count == 0 and 'inputDevices' in data:
            mice_count = len(data['inputDevices'].get('mice', []))
        if audio_count == 0 and 'audioDevices' in data:
            audio_count = len(data['audioDevices'].get('devices', []))
        if bluetooth_count == 0 and 'bluetoothDevices' in data:
            bluetooth_count = len(data['bluetoothDevices'].get('pairedDevices', []))
        if cameras_count == 0 and 'cameraDevices' in data:
            cameras_count = len(data['cameraDevices'].get('devices', []))
        if storage_count == 0 and 'storageDevices' in data:
            storage_count = len(data['storageDevices'].get('devices', []))
        
        summary = {
            'total_displays': displays_count,
            'total_printers': printers_count,
            'total_usb_devices': usb_count,
            'total_keyboards': keyboards_count,
            'total_mice': mice_count,
            'total_audio_devices': audio_count,
            'total_bluetooth_devices': bluetooth_count,
            'total_cameras': cameras_count,
            'total_storage_devices': storage_count
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
