"""
Displays Module Processor for ReportMate
Handles comprehensive display device and configuration information
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class DisplaysProcessor(BaseModuleProcessor):
    """
    Processor for displays module data
    Handles displays, adapters, configuration, layout, and color profiles
    """
    
    @property
    def module_id(self) -> str:
        return "displays"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process display data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed display data
        """
        self.logger.debug(f"Processing display module for device {device_id}")
        
        # Extract display data from the device payload
        display_data = device_data.get('display', {})
        
        # Process all display-related data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'displays': self._process_displays(display_data.get('displays', [])),
            'display_adapters': self._process_display_adapters(display_data.get('displayAdapters', [])),
            'display_settings': self._process_display_settings(display_data.get('displaySettings', {})),
            'color_profiles': self._process_color_profiles(display_data.get('colorProfiles', [])),
            'summary': self._generate_summary(display_data)
        }
        
        # Log processing summary
        self.logger.info(f"Display processed - {len(processed_data['displays'])} displays, "
                        f"{len(processed_data['display_adapters'])} adapters, "
                        f"Primary: {processed_data['summary'].get('primary_display', 'Unknown')}, "
                        f"Resolution: {processed_data['summary'].get('max_resolution', 'Unknown')}")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate display module data
        
        Args:
            data: Processed display data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'displays']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Display validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Display validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        # At least some display information should be present for validation to pass
        if not data['displays'] and not data['display_adapters']:
            self.logger.warning("Display validation warning - no display devices or adapters found")
            # Don't fail validation as this could be a headless system
        
        return True
    
    def _process_displays(self, displays_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process display device information"""
        processed_displays = []
        
        for display in displays_data:
            processed_display = {
                'name': display.get('name', ''),
                'device_id': display.get('deviceId', ''),
                'device_key': display.get('deviceKey', ''),
                'manufacturer': display.get('manufacturer', ''),
                'model': display.get('model', ''),
                'serial_number': display.get('serialNumber', ''),
                'device_string': display.get('deviceString', ''),
                
                # Connection and type
                'connection_type': display.get('connectionType', ''),
                'is_internal': display.get('isInternal', False),
                'is_external': display.get('isExternal', False),
                'is_primary': display.get('isPrimary', False),
                'is_active': display.get('isActive', False),
                'is_enabled': display.get('isEnabled', False),
                
                # Physical properties
                'diagonal_size_inches': self.get_float_value(display, 'diagonalSizeInches', 0.0),
                'width_mm': self.get_int_value(display, 'widthMm', 0),
                'height_mm': self.get_int_value(display, 'heightMm', 0),
                'aspect_ratio': self.get_float_value(display, 'aspectRatio', 0.0),
                
                # Current settings
                'current_width': self.get_int_value(display.get('currentResolution', {}), 'width', 0),
                'current_height': self.get_int_value(display.get('currentResolution', {}), 'height', 0),
                'current_refresh_rate': self.get_int_value(display, 'currentRefreshRate', 0),
                'current_color_depth': self.get_int_value(display, 'currentColorDepth', 0),
                'current_dpi': self.get_int_value(display, 'currentDpi', 0),
                'current_scaling': self.get_float_value(display, 'currentScaling', 1.0),
                'current_orientation': display.get('currentOrientation', ''),
                
                # Capabilities
                'max_width': self.get_int_value(display.get('maxResolution', {}), 'width', 0),
                'max_height': self.get_int_value(display.get('maxResolution', {}), 'height', 0),
                'min_width': self.get_int_value(display.get('minResolution', {}), 'width', 0),
                'min_height': self.get_int_value(display.get('minResolution', {}), 'height', 0),
                'max_color_depth': self.get_int_value(display, 'maxColorDepth', 0),
                'supported_resolutions': json.dumps(display.get('supportedResolutions', [])),
                'supported_refresh_rates': json.dumps(display.get('supportedRefreshRates', [])),
                'capabilities': json.dumps(display.get('capabilities', [])),
                
                # Color and quality
                'color_space': display.get('colorSpace', ''),
                'gamma_value': self.get_float_value(display, 'gamma', 0.0),
                'brightness': self.get_int_value(display, 'brightness', 0),
                'contrast': self.get_int_value(display, 'contrast', 0),
                
                # Position and layout
                'position_x': self.get_int_value(display, 'positionX', 0),
                'position_y': self.get_int_value(display, 'positionY', 0),
                'display_index': self.get_int_value(display, 'displayIndex', 0),
                
                # Technology features
                'panel_type': display.get('panelType', ''),
                'is_hdr': display.get('isHdr', False),
                'is_wide_gamut': display.get('isWideGamut', False),
                'is_adaptive_sync': display.get('isAdaptiveSync', False),
                'is_touch': display.get('isTouch', False),
                
                # Driver and firmware
                'driver_version': display.get('driverVersion', ''),
                'driver_date': self._parse_datetime(display.get('driverDate')),
                'firmware_version': display.get('firmwareVersion', ''),
                
                # EDID information
                'edid_manufacturer': display.get('edidManufacturer', ''),
                'edid_product_code': display.get('edidProductCode', ''),
                'edid_week_of_manufacture': self.get_int_value(display, 'edidWeekOfManufacture', 0),
                'edid_year_of_manufacture': self.get_int_value(display, 'edidYearOfManufacture', 0),
                'edid_version': display.get('edidVersion', ''),
                
                # Status and health
                'status': display.get('status', ''),
                'health': display.get('health', ''),
                'last_connected': self._parse_datetime(display.get('lastConnected')),
                'usage_hours': self.get_long_value(display, 'usageHours', 0),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_displays.append(processed_display)
        
        return processed_displays
    
    def _process_display_adapters(self, adapters_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process display adapter information"""
        processed_adapters = []
        
        for adapter in adapters_data:
            processed_adapter = {
                'name': adapter.get('name', ''),
                'adapter_device_id': adapter.get('deviceId', ''),
                'manufacturer': adapter.get('manufacturer', ''),
                'chip_type': adapter.get('chipType', ''),
                'dac_type': adapter.get('dacType', ''),
                'memory_size': self.get_long_value(adapter, 'memorySize', 0),
                'driver_version': adapter.get('driverVersion', ''),
                'driver_date': self._parse_datetime(adapter.get('driverDate')),
                'bios_version': adapter.get('biosVersion', ''),
                'connected_displays': json.dumps(adapter.get('connectedDisplays', [])),
                'supported_modes': json.dumps(adapter.get('supportedModes', [])),
                'max_displays': self.get_int_value(adapter, 'maxDisplays', 0),
                'is_3d_capable': adapter.get('is3dCapable', False),
                'is_hardware_accelerated': adapter.get('isHardwareAccelerated', False),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_adapters.append(processed_adapter)
        
        return processed_adapters
    
    def _process_display_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process display configuration and settings"""
        return {
            'total_displays': self.get_int_value(settings_data, 'totalDisplays', 0),
            'active_displays': self.get_int_value(settings_data, 'activeDisplays', 0),
            'primary_display': settings_data.get('primaryDisplay', ''),
            'display_mode': settings_data.get('displayMode', ''),
            'is_extended_desktop': settings_data.get('isExtendedDesktop', False),
            'is_mirrored_desktop': settings_data.get('isMirroredDesktop', False),
            'virtual_desktop_width': self.get_int_value(settings_data, 'virtualDesktopWidth', 0),
            'virtual_desktop_height': self.get_int_value(settings_data, 'virtualDesktopHeight', 0),
            'display_sleep_timeout': self.get_int_value(settings_data, 'displaySleepTimeout', 0),
            'is_power_saving_enabled': settings_data.get('isPowerSavingEnabled', False),
            'is_high_contrast_enabled': settings_data.get('isHighContrastEnabled', False),
            'text_scaling': self.get_float_value(settings_data, 'textScaling', 1.0),
            'is_magnifier_enabled': settings_data.get('isMagnifierEnabled', False),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _process_color_profiles(self, profiles_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process color profile information"""
        processed_profiles = []
        
        for profile in profiles_data:
            processed_profile = {
                'name': profile.get('name', ''),
                'file_path': profile.get('filePath', ''),
                'description': profile.get('description', ''),
                'color_space': profile.get('colorSpace', ''),
                'device_model': profile.get('deviceModel', ''),
                'manufacturer': profile.get('manufacturer', ''),
                'is_default': profile.get('isDefault', False),
                'created_date': self._parse_datetime(profile.get('createdDate')),
                'file_size': self.get_long_value(profile, 'fileSize', 0),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_profiles.append(processed_profile)
        
        return processed_profiles
    
    def _generate_summary(self, display_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for display data"""
        displays = display_data.get('displays', [])
        adapters = display_data.get('displayAdapters', [])
        settings = display_data.get('displaySettings', {})
        
        # Calculate summary statistics
        total_displays = len(displays)
        active_displays = len([d for d in displays if d.get('isActive')])
        internal_displays = len([d for d in displays if d.get('isInternal')])
        external_displays = len([d for d in displays if d.get('isExternal')])
        
        primary_display = next((d['name'] for d in displays if d.get('isPrimary')), '')
        if not primary_display:
            primary_display = settings.get('primaryDisplay', '')
        
        # Find maximum resolution
        max_resolution = ""
        max_pixels = 0
        for display in displays:
            current_res = display.get('currentResolution', {})
            width = current_res.get('width', 0)
            height = current_res.get('height', 0)
            if width * height > max_pixels:
                max_pixels = width * height
                max_resolution = f"{width}x{height}"
        
        # Check for advanced features
        has_hdr = any(d.get('isHdr') for d in displays)
        has_touch = any(d.get('isTouch') for d in displays)
        has_4k = any(d.get('currentResolution', {}).get('width', 0) >= 3840 for d in displays)
        
        return {
            'total_displays': total_displays,
            'active_displays': active_displays,
            'internal_displays': internal_displays,
            'external_displays': external_displays,
            'primary_display': primary_display,
            'max_resolution': max_resolution,
            'total_adapters': len(adapters),
            'has_hdr_support': has_hdr,
            'has_touch_support': has_touch,
            'has_4k_display': has_4k,
            'display_mode': settings.get('displayMode', 'Unknown'),
            'is_multi_monitor': total_displays > 1,
            'total_color_profiles': len(display_data.get('colorProfiles', []))
        }
    
    def _parse_datetime(self, date_string: Optional[str]) -> Optional[str]:
        """Parse datetime string to ISO format"""
        if not date_string:
            return None
        
        try:
            # Handle various datetime formats
            if 'T' in date_string and ('Z' in date_string or '+' in date_string):
                # Already in ISO format
                return date_string
            
            # Try to parse common formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    dt = datetime.strptime(date_string, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If we can't parse it, return as-is
            return date_string
            
        except Exception as e:
            self.logger.warning(f"Failed to parse datetime '{date_string}': {e}")
            return date_string
