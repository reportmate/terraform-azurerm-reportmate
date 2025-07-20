"""
Printers Module Processor for ReportMate
Handles printer information, drivers, jobs, and spooler configuration
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class PrintersProcessor(BaseModuleProcessor):
    """
    Processor for printers module data
    Handles printers, drivers, ports, processors, jobs, spooler, and policies
    """
    
    @property
    def module_id(self) -> str:
        return "printers"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process printer data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed printer data
        """
        self.logger.debug(f"Processing printer module for device {device_id}")
        
        # Extract printer data from the device payload
        printer_data = device_data.get('printer', {})
        
        # Process all printer-related data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'printers': self._process_printers(printer_data.get('printers', [])),
            'print_drivers': self._process_print_drivers(printer_data.get('printDrivers', [])),
            'print_ports': self._process_print_ports(printer_data.get('printPorts', [])),
            'print_processors': self._process_print_processors(printer_data.get('printProcessors', [])),
            'print_jobs': self._process_print_jobs(printer_data.get('recentPrintJobs', [])),
            'spooler_info': self._process_spooler_info(printer_data.get('spoolerInfo', {})),
            'policy_settings': self._process_policy_settings(printer_data.get('policySettings', {})),
            'summary': self._generate_summary(printer_data)
        }
        
        # Log processing summary
        self.logger.info(f"Printer processed - {len(processed_data['printers'])} printers, "
                        f"{len(processed_data['print_drivers'])} drivers, "
                        f"{len(processed_data['print_jobs'])} recent jobs, "
                        f"spooler: {processed_data['spooler_info'].get('serviceStatus', 'Unknown')}")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate printer module data
        
        Args:
            data: Processed printer data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'printers', 'print_drivers']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Printer validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Printer validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        # Validate each printer has at least a name
        for printer in data['printers']:
            if not printer.get('name'):
                self.logger.warning("Printer validation failed - printer missing name")
                return False
        
        return True
    
    def _process_printers(self, printers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process printer information"""
        processed_printers = []
        
        for printer in printers_data:
            processed_printer = {
                'name': printer.get('name', ''),
                'share_name': printer.get('shareName', ''),
                'port_name': printer.get('portName', ''),
                'driver_name': printer.get('driverName', ''),
                'location': printer.get('location', ''),
                'comment': printer.get('comment', ''),
                'status': printer.get('status', ''),
                'printer_status': printer.get('printerStatus', ''),
                'is_shared': printer.get('isShared', False),
                'is_network': printer.get('isNetwork', False),
                'is_default': printer.get('isDefault', False),
                'is_online': printer.get('isOnline', True),
                'server_name': printer.get('serverName', ''),
                'manufacturer': printer.get('manufacturer', ''),
                'model': printer.get('model', ''),
                'device_type': printer.get('deviceType', ''),
                'connection_type': printer.get('connectionType', ''),
                'ip_address': printer.get('ipAddress', ''),
                'priority': printer.get('priority', 0),
                'enable_bidirectional': printer.get('enableBidirectional', False),
                'keep_printed_jobs': printer.get('keepPrintedJobs', False),
                'enable_dev_query': printer.get('enableDevQuery', False),
                'install_date': self._parse_datetime(printer.get('installDate')),
                'properties': printer.get('properties', {}),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_printers.append(processed_printer)
        
        return processed_printers
    
    def _process_print_drivers(self, drivers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process print driver information"""
        processed_drivers = []
        
        for driver in drivers_data:
            processed_driver = {
                'name': driver.get('name', ''),
                'version': driver.get('version', ''),
                'environment': driver.get('environment', ''),
                'config_file': driver.get('configFile', ''),
                'data_file': driver.get('dataFile', ''),
                'driver_path': driver.get('driverPath', ''),
                'help_file': driver.get('helpFile', ''),
                'monitor_name': driver.get('monitorName', ''),
                'default_data_type': driver.get('defaultDataType', ''),
                'provider': driver.get('provider', ''),
                'driver_version': driver.get('driverVersion', ''),
                'driver_date': self._parse_datetime(driver.get('driverDate')),
                'is_signed': driver.get('isSigned', False),
                'dependent_files': driver.get('dependentFiles', []),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_drivers.append(processed_driver)
        
        return processed_drivers
    
    def _process_print_ports(self, ports_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process print port information"""
        processed_ports = []
        
        for port in ports_data:
            processed_port = {
                'name': port.get('name', ''),
                'port_type': port.get('type', ''),
                'description': port.get('description', ''),
                'is_network': port.get('isNetwork', False),
                'is_local': port.get('isLocal', True),
                'timeout_seconds': port.get('timeout', 0),
                'transmission_retry': port.get('transmissionRetry', 0),
                'print_monitor': port.get('printMonitor', ''),
                'configuration': port.get('configuration', {}),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_ports.append(processed_port)
        
        return processed_ports
    
    def _process_print_processors(self, processors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process print processor information"""
        processed_processors = []
        
        for processor in processors_data:
            processed_processor = {
                'name': processor.get('name', ''),
                'environment': processor.get('environment', ''),
                'dll_name': processor.get('dllName', ''),
                'supported_datatypes': processor.get('supportedDatatypes', []),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_processors.append(processed_processor)
        
        return processed_processors
    
    def _process_print_jobs(self, jobs_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process print job information"""
        processed_jobs = []
        
        for job in jobs_data:
            processed_job = {
                'printer_name': job.get('printerName', ''),
                'job_id': job.get('jobId', 0),
                'document_name': job.get('documentName', ''),
                'user_name': job.get('userName', ''),
                'status': job.get('status', ''),
                'submitted_time': self._parse_datetime(job.get('submittedTime')),
                'total_pages': job.get('totalPages', 0),
                'pages_printed': job.get('pagesPrinted', 0),
                'size_bytes': job.get('sizeBytes', 0),
                'priority': job.get('priority', 0),
                'start_time': self._parse_datetime(job.get('startTime')),
                'until_time': self._parse_datetime(job.get('untilTime')),
                'last_updated': datetime.utcnow().isoformat()
            }
            processed_jobs.append(processed_job)
        
        return processed_jobs
    
    def _process_spooler_info(self, spooler_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process print spooler information"""
        return {
            'service_status': spooler_data.get('serviceStatus', ''),
            'service_start_type': spooler_data.get('serviceStartType', ''),
            'default_spool_directory': spooler_data.get('defaultSpoolDirectory', ''),
            'beep_enabled': spooler_data.get('beepEnabled', False),
            'net_popup': spooler_data.get('netPopup', False),
            'log_events': spooler_data.get('logEvents', False),
            'restart_job_on_pool_error': spooler_data.get('restartJobOnPoolError', False),
            'restart_job_on_pool_enabled': spooler_data.get('restartJobOnPoolEnabled', False),
            'port_thread_priority': spooler_data.get('portThreadPriority', 0),
            'scheduler_thread_priority': spooler_data.get('schedulerThreadPriority', 0),
            'total_jobs': spooler_data.get('totalJobs', 0),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _process_policy_settings(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process print policy settings"""
        return {
            'disable_web_printing': policy_data.get('disableWebPrinting', False),
            'disable_server_thread': policy_data.get('disableServerThread', False),
            'disable_spooler_open_printers': policy_data.get('disableSpoolerOpenPrinters', False),
            'spooler_priority': policy_data.get('spoolerPriority', 0),
            'spooler_max_job_schedule': policy_data.get('spoolerMaxJobSchedule', 0),
            'enable_logging': policy_data.get('enableLogging', False),
            'log_level': policy_data.get('logLevel', ''),
            'restrict_driver_installation': policy_data.get('restrictDriverInstallation', False),
            'group_policy_settings': policy_data.get('groupPolicySettings', {}),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _generate_summary(self, printer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for printer data"""
        printers = printer_data.get('printers', [])
        print_jobs = printer_data.get('recentPrintJobs', [])
        
        # Calculate summary statistics
        total_printers = len(printers)
        default_printer = next((p['name'] for p in printers if p.get('isDefault')), '')
        network_printers = len([p for p in printers if p.get('isNetwork')])
        shared_printers = len([p for p in printers if p.get('isShared')])
        online_printers = len([p for p in printers if p.get('isOnline')])
        
        recent_jobs_count = len(print_jobs)
        
        return {
            'total_printers': total_printers,
            'network_printers': network_printers,
            'shared_printers': shared_printers,
            'online_printers': online_printers,
            'default_printer': default_printer,
            'recent_jobs_count': recent_jobs_count,
            'has_spooler_info': bool(printer_data.get('spoolerInfo')),
            'has_policy_settings': bool(printer_data.get('policySettings'))
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
