"""
System Module Processor for ReportMate
Handles system information, performance, and environmental data
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class SystemProcessor(BaseModuleProcessor):
    """
    Processor for system module data
    Handles system information, performance metrics, and environmental data
    """
    
    @property
    def module_id(self) -> str:
        return "system"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process system data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed system data
        """
        self.logger.debug(f"Processing system module for device {device_id}")
        
        # Extract system data from the device payload
        system_data = device_data.get('system', {})
        
        # Build processed system data - preserve original structure from runner.exe
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': system_data.get('collectedAt', datetime.utcnow().isoformat()),
            'version': system_data.get('version', '1.0.0'),
            
            # Preserve original data structure from runner.exe
            'operatingSystem': system_data.get('operatingSystem', {}),
            'updates': system_data.get('updates', []),
            'services': system_data.get('services', []),
            'environment': system_data.get('environment', []),
            'uptime': system_data.get('uptime', ''),
            'uptimeString': system_data.get('uptimeString', ''),
            'lastBootTime': system_data.get('lastBootTime', ''),
            
            # Legacy processed data for backward compatibility
            'system_info': self._process_system_info(system_data),
            'performance_counters': self._process_performance_counters(system_data),
            'event_logs': self._process_event_logs(system_data),
            'processes': self._process_processes(system_data),
            'system_health': self._process_system_health(system_data),
            'boot_configuration': self._process_boot_configuration(system_data),
            'power_management': self._process_power_management(system_data),
            'drivers': self._process_drivers(system_data),
            'system_files': self._process_system_files(system_data),
            'registry_info': self._process_registry_info(system_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        # Log what we actually found in the system data
        if processed_data.get('operatingSystem'):
            os_info = processed_data['operatingSystem']
            self.logger.info(f"System processed - OS: {os_info.get('name', 'Unknown')} "
                           f"{os_info.get('version', 'Unknown')} "
                           f"(Build {os_info.get('build', 'Unknown')}), "
                           f"Architecture: {os_info.get('architecture', 'Unknown')}")
        else:
            self.logger.warning("No operatingSystem data found in system module")
        
        self.logger.info(f"System processed - {len(processed_data['updates'])} updates, "
                        f"{len(processed_data['services'])} services, "
                        f"{len(processed_data['environment'])} environment variables")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate system module data
        
        Args:
            data: Processed system data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"System validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"System validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        # Check if we have either new format (operatingSystem) or legacy format (system_info)
        if not data.get('operatingSystem') and not data.get('system_info'):
            self.logger.warning("System validation failed - no operating system data found")
            return False
        
        return True
    
    def _process_system_info(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process basic system information"""
        info_data = system_data.get('system_info', {})
        
        return {
            'computer_name': info_data.get('computer_name', ''),
            'domain': info_data.get('domain', ''),
            'workgroup': info_data.get('workgroup', ''),
            'manufacturer': info_data.get('manufacturer', ''),
            'model': info_data.get('model', ''),
            'system_type': info_data.get('system_type', ''),
            'processor_architecture': info_data.get('processor_architecture', ''),
            'system_directory': info_data.get('system_directory', ''),
            'windows_directory': info_data.get('windows_directory', ''),
            'boot_device': info_data.get('boot_device', ''),
            'system_device': info_data.get('system_device', ''),
            'page_file_location': info_data.get('page_file_location', ''),
            'time_zone': info_data.get('time_zone', ''),
            'locale': info_data.get('locale', ''),
            'system_locale': info_data.get('system_locale', ''),
            'keyboard_layout': info_data.get('keyboard_layout', ''),
            'total_physical_memory': self.get_long_value(info_data, 'total_physical_memory', 0),
            'available_physical_memory': self.get_long_value(info_data, 'available_physical_memory', 0),
            'total_virtual_memory': self.get_long_value(info_data, 'total_virtual_memory', 0),
            'available_virtual_memory': self.get_long_value(info_data, 'available_virtual_memory', 0),
            'page_file_size': self.get_long_value(info_data, 'page_file_size', 0),
            'number_of_processors': self.get_int_value(info_data, 'number_of_processors', 0),
            'number_of_logical_processors': self.get_int_value(info_data, 'number_of_logical_processors', 0),
            'hypervisor_present': self.get_bool_value(info_data, 'hypervisor_present', False),
            'secure_boot_enabled': self.get_bool_value(info_data, 'secure_boot_enabled', False),
            'uefi_firmware': self.get_bool_value(info_data, 'uefi_firmware', False),
            'install_date': self._parse_datetime(info_data.get('install_date')),
            'last_boot_time': self._parse_datetime(info_data.get('last_boot_time')),
            'system_up_time': self.get_long_value(info_data, 'system_up_time', 0),
            'bios_version': info_data.get('bios_version', ''),
            'bios_date': self._parse_date(info_data.get('bios_date')),
            'serial_number': info_data.get('serial_number', ''),
            'uuid': info_data.get('uuid', '')
        }
    
    def _process_performance_counters(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance counter data"""
        perf_data = system_data.get('performance_counters', {})
        
        return {
            'cpu_usage': self.get_float_value(perf_data, 'cpu_usage', 0.0),
            'memory_usage': self.get_float_value(perf_data, 'memory_usage', 0.0),
            'disk_usage': self._process_disk_usage(perf_data.get('disk_usage', [])),
            'network_usage': self._process_network_usage(perf_data.get('network_usage', {})),
            'process_count': self.get_int_value(perf_data, 'process_count', 0),
            'thread_count': self.get_int_value(perf_data, 'thread_count', 0),
            'handle_count': self.get_int_value(perf_data, 'handle_count', 0),
            'uptime_seconds': self.get_long_value(perf_data, 'uptime_seconds', 0),
            'context_switches_per_sec': self.get_long_value(perf_data, 'context_switches_per_sec', 0),
            'system_calls_per_sec': self.get_long_value(perf_data, 'system_calls_per_sec', 0),
            'interrupt_per_sec': self.get_long_value(perf_data, 'interrupt_per_sec', 0),
            'page_faults_per_sec': self.get_long_value(perf_data, 'page_faults_per_sec', 0),
            'committed_bytes': self.get_long_value(perf_data, 'committed_bytes', 0),
            'committed_bytes_in_use': self.get_float_value(perf_data, 'committed_bytes_in_use', 0.0),
            'kernel_time': self.get_float_value(perf_data, 'kernel_time', 0.0),
            'user_time': self.get_float_value(perf_data, 'user_time', 0.0),
            'idle_time': self.get_float_value(perf_data, 'idle_time', 0.0)
        }
    
    def _process_disk_usage(self, disk_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process disk usage data"""
        processed_disks = []
        
        for disk in disk_data:
            if isinstance(disk, dict):
                processed_disk = {
                    'device_name': disk.get('device_name', ''),
                    'disk_reads_per_sec': self.get_float_value(disk, 'disk_reads_per_sec', 0.0),
                    'disk_writes_per_sec': self.get_float_value(disk, 'disk_writes_per_sec', 0.0),
                    'disk_read_bytes_per_sec': self.get_long_value(disk, 'disk_read_bytes_per_sec', 0),
                    'disk_write_bytes_per_sec': self.get_long_value(disk, 'disk_write_bytes_per_sec', 0),
                    'avg_disk_queue_length': self.get_float_value(disk, 'avg_disk_queue_length', 0.0),
                    'current_disk_queue_length': self.get_int_value(disk, 'current_disk_queue_length', 0),
                    'percent_disk_time': self.get_float_value(disk, 'percent_disk_time', 0.0),
                    'percent_idle_time': self.get_float_value(disk, 'percent_idle_time', 0.0)
                }
                processed_disks.append(processed_disk)
        
        return processed_disks
    
    def _process_network_usage(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process network usage data"""
        return {
            'bytes_received_per_sec': self.get_long_value(network_data, 'bytes_received_per_sec', 0),
            'bytes_sent_per_sec': self.get_long_value(network_data, 'bytes_sent_per_sec', 0),
            'packets_received_per_sec': self.get_long_value(network_data, 'packets_received_per_sec', 0),
            'packets_sent_per_sec': self.get_long_value(network_data, 'packets_sent_per_sec', 0),
            'current_bandwidth': self.get_long_value(network_data, 'current_bandwidth', 0),
            'output_queue_length': self.get_int_value(network_data, 'output_queue_length', 0),
            'packets_received_discarded': self.get_long_value(network_data, 'packets_received_discarded', 0),
            'packets_received_errors': self.get_long_value(network_data, 'packets_received_errors', 0),
            'packets_outbound_discarded': self.get_long_value(network_data, 'packets_outbound_discarded', 0),
            'packets_outbound_errors': self.get_long_value(network_data, 'packets_outbound_errors', 0)
        }
    
    def _process_event_logs(self, system_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process event log entries"""
        events = []
        events_list = system_data.get('event_logs', [])
        
        for event in events_list:
            if isinstance(event, dict):
                processed_event = {
                    'log_name': event.get('log_name', ''),
                    'source': event.get('source', ''),
                    'event_id': self.get_int_value(event, 'event_id', 0),
                    'level': event.get('level', 'Unknown'),
                    'keywords': event.get('keywords', []),
                    'time_created': self._parse_datetime(event.get('time_created')),
                    'time_written': self._parse_datetime(event.get('time_written')),
                    'event_record_id': self.get_long_value(event, 'event_record_id', 0),
                    'computer_name': event.get('computer_name', ''),
                    'user_id': event.get('user_id', ''),
                    'process_id': self.get_int_value(event, 'process_id', 0),
                    'thread_id': self.get_int_value(event, 'thread_id', 0),
                    'channel': event.get('channel', ''),
                    'task': event.get('task', ''),
                    'opcode': event.get('opcode', ''),
                    'message': event.get('message', ''),
                    'data': event.get('data', {})
                }
                
                events.append(processed_event)
        
        # Sort by time created (newest first)
        events.sort(key=lambda x: x['time_created'] or '', reverse=True)
        
        return events
    
    def _process_processes(self, system_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process running processes"""
        processes = []
        processes_list = system_data.get('processes', [])
        
        for process in processes_list:
            if isinstance(process, dict):
                processed_process = {
                    'name': process.get('name', ''),
                    'process_id': self.get_int_value(process, 'process_id', 0),
                    'parent_process_id': self.get_int_value(process, 'parent_process_id', 0),
                    'executable_path': process.get('executable_path', ''),
                    'command_line': process.get('command_line', ''),
                    'creation_date': self._parse_datetime(process.get('creation_date')),
                    'termination_date': self._parse_datetime(process.get('termination_date')),
                    'kernel_mode_time': self.get_long_value(process, 'kernel_mode_time', 0),
                    'user_mode_time': self.get_long_value(process, 'user_mode_time', 0),
                    'working_set_size': self.get_long_value(process, 'working_set_size', 0),
                    'peak_working_set_size': self.get_long_value(process, 'peak_working_set_size', 0),
                    'page_file_usage': self.get_long_value(process, 'page_file_usage', 0),
                    'peak_page_file_usage': self.get_long_value(process, 'peak_page_file_usage', 0),
                    'virtual_size': self.get_long_value(process, 'virtual_size', 0),
                    'peak_virtual_size': self.get_long_value(process, 'peak_virtual_size', 0),
                    'thread_count': self.get_int_value(process, 'thread_count', 0),
                    'handle_count': self.get_int_value(process, 'handle_count', 0),
                    'session_id': self.get_int_value(process, 'session_id', 0),
                    'priority': self.get_int_value(process, 'priority', 0),
                    'description': process.get('description', ''),
                    'company': process.get('company', ''),
                    'version': process.get('version', ''),
                    'owner': process.get('owner', ''),
                    'cpu_time': self.get_long_value(process, 'cpu_time', 0),
                    'percent_processor_time': self.get_float_value(process, 'percent_processor_time', 0.0)
                }
                
                processes.append(processed_process)
        
        # Sort by CPU usage (highest first)
        processes.sort(key=lambda x: x['percent_processor_time'], reverse=True)
        
        return processes
    
    def _process_system_health(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process system health indicators"""
        health_data = system_data.get('system_health', {})
        
        return {
            'cpu_temperature': self.get_float_value(health_data, 'cpu_temperature', 0.0),
            'system_temperature': self.get_float_value(health_data, 'system_temperature', 0.0),
            'fan_speeds': health_data.get('fan_speeds', []),
            'voltage_readings': health_data.get('voltage_readings', {}),
            'power_consumption': self.get_float_value(health_data, 'power_consumption', 0.0),
            'battery_status': self._process_battery_status(health_data.get('battery_status', {})),
            'thermal_state': health_data.get('thermal_state', 'Unknown'),
            'system_errors': health_data.get('system_errors', []),
            'hardware_errors': health_data.get('hardware_errors', []),
            'memory_errors': self.get_int_value(health_data, 'memory_errors', 0),
            'disk_errors': health_data.get('disk_errors', []),
            'network_errors': health_data.get('network_errors', [])
        }
    
    def _process_battery_status(self, battery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process battery status information"""
        return {
            'battery_present': self.get_bool_value(battery_data, 'battery_present', False),
            'charge_level': self.get_int_value(battery_data, 'charge_level', 0),
            'charging': self.get_bool_value(battery_data, 'charging', False),
            'time_remaining': self.get_int_value(battery_data, 'time_remaining', 0),
            'battery_health': battery_data.get('battery_health', 'Unknown'),
            'cycle_count': self.get_int_value(battery_data, 'cycle_count', 0),
            'design_capacity': self.get_int_value(battery_data, 'design_capacity', 0),
            'full_charge_capacity': self.get_int_value(battery_data, 'full_charge_capacity', 0),
            'power_state': battery_data.get('power_state', 'Unknown')
        }
    
    def _process_boot_configuration(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process boot configuration data"""
        boot_data = system_data.get('boot_configuration', {})
        
        return {
            'boot_method': boot_data.get('boot_method', 'Unknown'),
            'secure_boot_enabled': self.get_bool_value(boot_data, 'secure_boot_enabled', False),
            'uefi_boot': self.get_bool_value(boot_data, 'uefi_boot', False),
            'fast_boot_enabled': self.get_bool_value(boot_data, 'fast_boot_enabled', False),
            'boot_order': boot_data.get('boot_order', []),
            'boot_options': boot_data.get('boot_options', []),
            'recovery_enabled': self.get_bool_value(boot_data, 'recovery_enabled', False),
            'system_recovery_options': boot_data.get('system_recovery_options', {}),
            'startup_programs': boot_data.get('startup_programs', []),
            'boot_time': self.get_float_value(boot_data, 'boot_time', 0.0),
            'boot_critical': self.get_bool_value(boot_data, 'boot_critical', False)
        }
    
    def _process_power_management(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process power management settings"""
        power_data = system_data.get('power_management', {})
        
        return {
            'current_power_scheme': power_data.get('current_power_scheme', ''),
            'power_schemes': power_data.get('power_schemes', []),
            'hibernate_enabled': self.get_bool_value(power_data, 'hibernate_enabled', False),
            'hybrid_sleep_enabled': self.get_bool_value(power_data, 'hybrid_sleep_enabled', False),
            'wake_timers_enabled': self.get_bool_value(power_data, 'wake_timers_enabled', False),
            'lid_close_action': power_data.get('lid_close_action', 'Unknown'),
            'power_button_action': power_data.get('power_button_action', 'Unknown'),
            'sleep_button_action': power_data.get('sleep_button_action', 'Unknown'),
            'display_timeout': self.get_int_value(power_data, 'display_timeout', 0),
            'sleep_timeout': self.get_int_value(power_data, 'sleep_timeout', 0),
            'hibernate_timeout': self.get_int_value(power_data, 'hibernate_timeout', 0),
            'usb_selective_suspend': self.get_bool_value(power_data, 'usb_selective_suspend', False),
            'processor_power_management': power_data.get('processor_power_management', {}),
            'adaptive_display_timeout': self.get_bool_value(power_data, 'adaptive_display_timeout', False)
        }
    
    def _process_drivers(self, system_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process system drivers"""
        drivers = []
        drivers_list = system_data.get('drivers', [])
        
        for driver in drivers_list:
            if isinstance(driver, dict):
                processed_driver = {
                    'name': driver.get('name', ''),
                    'display_name': driver.get('display_name', ''),
                    'description': driver.get('description', ''),
                    'driver_version': driver.get('driver_version', ''),
                    'driver_date': self._parse_date(driver.get('driver_date')),
                    'driver_provider': driver.get('driver_provider', ''),
                    'inf_name': driver.get('inf_name', ''),
                    'hardware_id': driver.get('hardware_id', ''),
                    'compatible_id': driver.get('compatible_id', ''),
                    'service_name': driver.get('service_name', ''),
                    'class_name': driver.get('class_name', ''),
                    'class_guid': driver.get('class_guid', ''),
                    'device_instance_id': driver.get('device_instance_id', ''),
                    'location_info': driver.get('location_info', ''),
                    'manufacturer': driver.get('manufacturer', ''),
                    'driver_type': driver.get('driver_type', 'Unknown'),
                    'is_signed': self.get_bool_value(driver, 'is_signed', False),
                    'is_inbox': self.get_bool_value(driver, 'is_inbox', False),
                    'status': driver.get('status', 'Unknown'),
                    'problem_code': self.get_int_value(driver, 'problem_code', 0),
                    'error_description': driver.get('error_description', ''),
                    'file_path': driver.get('file_path', ''),
                    'file_size': self.get_long_value(driver, 'file_size', 0)
                }
                
                drivers.append(processed_driver)
        
        # Sort by name
        drivers.sort(key=lambda x: x['name'].lower())
        
        return drivers
    
    def _process_system_files(self, system_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process critical system files"""
        files = []
        files_list = system_data.get('system_files', [])
        
        for file_info in files_list:
            if isinstance(file_info, dict):
                processed_file = {
                    'file_path': file_info.get('file_path', ''),
                    'file_name': file_info.get('file_name', ''),
                    'file_size': self.get_long_value(file_info, 'file_size', 0),
                    'file_version': file_info.get('file_version', ''),
                    'product_version': file_info.get('product_version', ''),
                    'description': file_info.get('description', ''),
                    'company': file_info.get('company', ''),
                    'creation_time': self._parse_datetime(file_info.get('creation_time')),
                    'last_write_time': self._parse_datetime(file_info.get('last_write_time')),
                    'last_access_time': self._parse_datetime(file_info.get('last_access_time')),
                    'is_system_file': self.get_bool_value(file_info, 'is_system_file', False),
                    'is_hidden': self.get_bool_value(file_info, 'is_hidden', False),
                    'is_readonly': self.get_bool_value(file_info, 'is_readonly', False),
                    'digital_signature': file_info.get('digital_signature', {}),
                    'file_hash': file_info.get('file_hash', ''),
                    'hash_algorithm': file_info.get('hash_algorithm', ''),
                    'is_critical': self.get_bool_value(file_info, 'is_critical', False)
                }
                
                files.append(processed_file)
        
        # Sort by file path
        files.sort(key=lambda x: x['file_path'].lower())
        
        return files
    
    def _process_registry_info(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process registry information"""
        registry_data = system_data.get('registry_info', {})
        
        return {
            'total_keys': self.get_int_value(registry_data, 'total_keys', 0),
            'total_values': self.get_int_value(registry_data, 'total_values', 0),
            'registry_size': self.get_long_value(registry_data, 'registry_size', 0),
            'hive_files': registry_data.get('hive_files', []),
            'last_backup_time': self._parse_datetime(registry_data.get('last_backup_time')),
            'auto_backup_enabled': self.get_bool_value(registry_data, 'auto_backup_enabled', False),
            'registry_health': registry_data.get('registry_health', 'Unknown'),
            'corrupted_keys': self.get_int_value(registry_data, 'corrupted_keys', 0),
            'orphaned_entries': self.get_int_value(registry_data, 'orphaned_entries', 0),
            'invalid_references': self.get_int_value(registry_data, 'invalid_references', 0)
        }
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for system data"""
        system_info = processed_data['system_info']
        performance = processed_data['performance_counters']
        processes = processed_data['processes']
        drivers = processed_data['drivers']
        event_logs = processed_data['event_logs']
        health = processed_data['system_health']
        
        # Calculate summary statistics
        summary = {
            'computer_name': system_info.get('computer_name', ''),
            'manufacturer': system_info.get('manufacturer', ''),
            'model': system_info.get('model', ''),
            'total_memory_gb': round(system_info.get('total_physical_memory', 0) / (1024**3), 2),
            'available_memory_gb': round(system_info.get('available_physical_memory', 0) / (1024**3), 2),
            'memory_usage_percent': performance.get('memory_usage', 0.0),
            'cpu_usage_percent': performance.get('cpu_usage', 0.0),
            'total_processes': len(processes),
            'total_drivers': len(drivers),
            'total_event_logs': len(event_logs),
            'uptime_days': round(system_info.get('system_up_time', 0) / (24 * 3600), 1),
            'last_boot_time': system_info.get('last_boot_time'),
            'hypervisor_present': system_info.get('hypervisor_present', False),
            'secure_boot_enabled': system_info.get('secure_boot_enabled', False),
            'uefi_firmware': system_info.get('uefi_firmware', False),
            'system_health_status': self._calculate_health_status(health),
            'top_cpu_processes': self._get_top_cpu_processes(processes, 5),
            'top_memory_processes': self._get_top_memory_processes(processes, 5),
            'error_events_count': len([e for e in event_logs if e['level'] == 'Error']),
            'warning_events_count': len([e for e in event_logs if e['level'] == 'Warning']),
            'system_errors': len(health.get('system_errors', [])),
            'hardware_errors': len(health.get('hardware_errors', []))
        }
        
        return summary
    
    def _calculate_health_status(self, health_data: Dict[str, Any]) -> str:
        """Calculate overall system health status"""
        error_count = len(health_data.get('system_errors', [])) + len(health_data.get('hardware_errors', []))
        
        if error_count == 0:
            return 'Healthy'
        elif error_count <= 5:
            return 'Warning'
        else:
            return 'Critical'
    
    def _get_top_cpu_processes(self, processes: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Get top CPU consuming processes"""
        top_processes = sorted(processes, key=lambda x: x['percent_processor_time'], reverse=True)[:limit]
        return [{
            'name': p['name'],
            'process_id': p['process_id'],
            'cpu_percent': p['percent_processor_time']
        } for p in top_processes]
    
    def _get_top_memory_processes(self, processes: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Get top memory consuming processes"""
        top_processes = sorted(processes, key=lambda x: x['working_set_size'], reverse=True)[:limit]
        return [{
            'name': p['name'],
            'process_id': p['process_id'],
            'memory_mb': round(p['working_set_size'] / (1024*1024), 1)
        } for p in top_processes]
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[str]:
        """Parse datetime string to ISO format"""
        if not datetime_str:
            return None
        
        try:
            # Try common datetime formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%m/%d/%Y %H:%M:%S']:
                try:
                    parsed_datetime = datetime.strptime(datetime_str, fmt)
                    return parsed_datetime.isoformat()
                except ValueError:
                    continue
        except Exception as e:
            self.logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
        
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {e}")
        
        return None
