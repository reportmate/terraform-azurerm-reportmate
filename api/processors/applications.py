"""
Applications Module Processor for ReportMate
Handles software inventory and application management
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class ApplicationsProcessor(BaseModuleProcessor):
    """
    Processor for applications module data
    Handles installed applications, running processes, and software inventory
    """
    
    @property
    def module_id(self) -> str:
        return "applications"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process applications data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed applications data
        """
        self.logger.debug(f"Processing applications module for device {device_id}")
        
        # Extract applications data from the device payload
        applications_data = device_data.get('applications', {})
        
        # Build processed applications data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'installed_applications': self._process_installed_applications(applications_data),
            'running_processes': self._process_running_processes(applications_data),
            'startup_applications': self._process_startup_applications(applications_data),
            'browser_extensions': self._process_browser_extensions(applications_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        self.logger.info(f"Applications processed - {len(processed_data['installed_applications'])} installed, "
                        f"{len(processed_data['running_processes'])} running, "
                        f"{len(processed_data['startup_applications'])} startup apps")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate applications module data
        
        Args:
            data: Processed applications data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'installed_applications']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Applications validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Applications validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _process_installed_applications(self, applications_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process installed applications data"""
        installed_apps = []
        apps_list = applications_data.get('installed_applications', [])
        
        for app in apps_list:
            if isinstance(app, dict):
                processed_app = {
                    'name': app.get('name', 'Unknown'),
                    'version': app.get('version', ''),
                    'publisher': app.get('publisher', ''),
                    'install_date': self._parse_date(app.get('install_date')),
                    'install_location': app.get('install_location', ''),
                    'size': self.get_long_value(app, 'size', 0),
                    'architecture': app.get('architecture', ''),
                    'language': app.get('language', ''),
                    'uninstall_string': app.get('uninstall_string', ''),
                    'registry_key': app.get('registry_key', ''),
                    'is_system_component': self.get_bool_value(app, 'is_system_component', False),
                    'category': self._categorize_application(app.get('name', ''))
                }
                
                # Only add if we have a valid name
                if processed_app['name'] and processed_app['name'] != 'Unknown':
                    installed_apps.append(processed_app)
        
        # Sort by name for consistency
        installed_apps.sort(key=lambda x: x['name'].lower())
        
        return installed_apps
    
    def _process_running_processes(self, applications_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process running processes data"""
        running_processes = []
        processes_list = applications_data.get('running_processes', [])
        
        for process in processes_list:
            if isinstance(process, dict):
                processed_process = {
                    'name': process.get('name', 'Unknown'),
                    'pid': self.get_int_value(process, 'pid', 0),
                    'parent_pid': self.get_int_value(process, 'parent_pid', 0),
                    'cpu_percent': self.get_float_value(process, 'cpu_percent', 0.0),
                    'memory_usage': self.get_long_value(process, 'memory_usage', 0),
                    'executable_path': process.get('executable_path', ''),
                    'command_line': process.get('command_line', ''),
                    'start_time': self._parse_datetime(process.get('start_time')),
                    'user': process.get('user', ''),
                    'session_id': self.get_int_value(process, 'session_id', 0)
                }
                
                # Only add processes with valid PIDs
                if processed_process['pid'] > 0:
                    running_processes.append(processed_process)
        
        # Sort by CPU usage (highest first) then by name
        running_processes.sort(key=lambda x: (-x['cpu_percent'], x['name'].lower()))
        
        return running_processes
    
    def _process_startup_applications(self, applications_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process startup applications data"""
        startup_apps = []
        startup_list = applications_data.get('startup_applications', [])
        
        for app in startup_list:
            if isinstance(app, dict):
                processed_app = {
                    'name': app.get('name', 'Unknown'),
                    'command': app.get('command', ''),
                    'path': app.get('path', ''),
                    'source': app.get('source', ''),  # Registry, Startup folder, etc.
                    'enabled': self.get_bool_value(app, 'enabled', True),
                    'impact': app.get('impact', 'Unknown'),  # High, Medium, Low
                    'publisher': app.get('publisher', '')
                }
                
                startup_apps.append(processed_app)
        
        # Sort by impact then by name
        impact_order = {'High': 0, 'Medium': 1, 'Low': 2, 'Unknown': 3}
        startup_apps.sort(key=lambda x: (impact_order.get(x['impact'], 3), x['name'].lower()))
        
        return startup_apps
    
    def _process_browser_extensions(self, applications_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process browser extensions data"""
        extensions = []
        extensions_list = applications_data.get('browser_extensions', [])
        
        for ext in extensions_list:
            if isinstance(ext, dict):
                processed_ext = {
                    'name': ext.get('name', 'Unknown'),
                    'version': ext.get('version', ''),
                    'browser': ext.get('browser', 'Unknown'),
                    'enabled': self.get_bool_value(ext, 'enabled', True),
                    'id': ext.get('id', ''),
                    'description': ext.get('description', ''),
                    'permissions': ext.get('permissions', []),
                    'install_date': self._parse_date(ext.get('install_date'))
                }
                
                extensions.append(processed_ext)
        
        # Sort by browser then by name
        extensions.sort(key=lambda x: (x['browser'], x['name'].lower()))
        
        return extensions
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for applications data"""
        installed_apps = processed_data['installed_applications']
        running_processes = processed_data['running_processes']
        startup_apps = processed_data['startup_applications']
        extensions = processed_data['browser_extensions']
        
        # Calculate summary statistics
        summary = {
            'total_installed': len(installed_apps),
            'total_running': len(running_processes),
            'total_startup': len(startup_apps),
            'total_extensions': len(extensions),
            'total_memory_usage': sum(p['memory_usage'] for p in running_processes),
            'high_cpu_processes': len([p for p in running_processes if p['cpu_percent'] > 5.0]),
            'system_components': len([a for a in installed_apps if a['is_system_component']]),
            'user_applications': len([a for a in installed_apps if not a['is_system_component']]),
            'categories': self._get_category_breakdown(installed_apps),
            'publishers': self._get_top_publishers(installed_apps, 10),
            'largest_applications': self._get_largest_applications(installed_apps, 5)
        }
        
        return summary
    
    def _categorize_application(self, app_name: str) -> str:
        """Categorize application based on name"""
        if not app_name:
            return 'Unknown'
        
        app_name_lower = app_name.lower()
        
        # Development tools
        if any(keyword in app_name_lower for keyword in ['visual studio', 'eclipse', 'intellij', 'code', 'git', 'docker', 'python', 'node']):
            return 'Development'
        
        # Office and productivity
        if any(keyword in app_name_lower for keyword in ['office', 'word', 'excel', 'powerpoint', 'outlook', 'teams', 'slack', 'zoom']):
            return 'Productivity'
        
        # Web browsers
        if any(keyword in app_name_lower for keyword in ['chrome', 'firefox', 'edge', 'safari', 'browser']):
            return 'Browser'
        
        # Media and graphics
        if any(keyword in app_name_lower for keyword in ['photoshop', 'illustrator', 'vlc', 'media', 'video', 'audio', 'player']):
            return 'Media'
        
        # Security
        if any(keyword in app_name_lower for keyword in ['antivirus', 'defender', 'security', 'firewall', 'vpn']):
            return 'Security'
        
        # System utilities
        if any(keyword in app_name_lower for keyword in ['driver', 'utility', 'update', 'runtime', 'redistributable', 'framework']):
            return 'System'
        
        # Games
        if any(keyword in app_name_lower for keyword in ['game', 'steam', 'origin', 'uplay']):
            return 'Games'
        
        return 'Other'
    
    def _get_category_breakdown(self, installed_apps: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of applications by category"""
        categories = {}
        for app in installed_apps:
            category = app.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _get_top_publishers(self, installed_apps: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Get top publishers by number of applications"""
        publishers = {}
        for app in installed_apps:
            publisher = app.get('publisher', 'Unknown')
            if publisher and publisher != 'Unknown':
                publishers[publisher] = publishers.get(publisher, 0) + 1
        
        # Sort by count and return top N
        sorted_publishers = sorted(publishers.items(), key=lambda x: x[1], reverse=True)
        return [{'name': pub, 'count': count} for pub, count in sorted_publishers[:limit]]
    
    def _get_largest_applications(self, installed_apps: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Get largest applications by size"""
        apps_with_size = [app for app in installed_apps if app.get('size', 0) > 0]
        apps_with_size.sort(key=lambda x: x['size'], reverse=True)
        
        return [{
            'name': app['name'],
            'size': app['size'],
            'publisher': app.get('publisher', '')
        } for app in apps_with_size[:limit]]
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {e}")
        
        return None
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[str]:
        """Parse datetime string to ISO format"""
        if not datetime_str:
            return None
        
        try:
            # Try common datetime formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                try:
                    parsed_datetime = datetime.strptime(datetime_str, fmt)
                    return parsed_datetime.isoformat()
                except ValueError:
                    continue
        except Exception as e:
            self.logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
        
        return None
