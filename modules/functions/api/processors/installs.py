"""
Installs Module Processor for ReportMate
Handles software installations, updates, and package management
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class InstallsProcessor(BaseModuleProcessor):
    """
    Processor for installs module data
    Handles Windows Updates, software installations, patches, and package managers
    """
    
    @property
    def module_id(self) -> str:
        return "installs"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process installs data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed installs data
        """
        self.logger.debug(f"Processing installs module for device {device_id}")
        
        # Extract installs data from the device payload
        installs_data = device_data.get('installs', {})
        
        # Build processed installs data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'windows_updates': self._process_windows_updates(installs_data),
            'installed_patches': self._process_installed_patches(installs_data),
            'pending_updates': self._process_pending_updates(installs_data),
            'package_managers': self._process_package_managers(installs_data),
            'update_settings': self._process_update_settings(installs_data),
            'update_history': self._process_update_history(installs_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        self.logger.info(f"Installs processed - {len(processed_data['windows_updates'])} updates, "
                        f"{len(processed_data['pending_updates'])} pending, "
                        f"{len(processed_data['installed_patches'])} patches")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate installs module data
        
        Args:
            data: Processed installs data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'windows_updates']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Installs validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Installs validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _process_windows_updates(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process Windows Updates data"""
        updates = []
        updates_list = installs_data.get('windows_updates', [])
        
        for update in updates_list:
            if isinstance(update, dict):
                processed_update = {
                    'kb_number': update.get('kb_number', ''),
                    'title': update.get('title', 'Unknown Update'),
                    'description': update.get('description', ''),
                    'installed_date': self._parse_datetime(update.get('installed_date')),
                    'size': self.get_long_value(update, 'size', 0),
                    'severity': update.get('severity', 'Unknown'),
                    'classification': update.get('classification', 'Unknown'),
                    'support_url': update.get('support_url', ''),
                    'msrc_severity': update.get('msrc_severity', ''),
                    'installation_behavior': update.get('installation_behavior', {}),
                    'reboot_required': self.get_bool_value(update, 'reboot_required', False),
                    'is_downloaded': self.get_bool_value(update, 'is_downloaded', False),
                    'is_installed': self.get_bool_value(update, 'is_installed', False),
                    'is_superseded': self.get_bool_value(update, 'is_superseded', False),
                    'superseded_by': update.get('superseded_by', []),
                    'categories': update.get('categories', [])
                }
                
                updates.append(processed_update)
        
        # Sort by installation date (newest first)
        updates.sort(key=lambda x: x['installed_date'] or '', reverse=True)
        
        return updates
    
    def _process_installed_patches(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process installed patches data"""
        patches = []
        patches_list = installs_data.get('installed_patches', [])
        
        for patch in patches_list:
            if isinstance(patch, dict):
                processed_patch = {
                    'hotfix_id': patch.get('hotfix_id', ''),
                    'description': patch.get('description', ''),
                    'installed_by': patch.get('installed_by', ''),
                    'installed_on': self._parse_datetime(patch.get('installed_on')),
                    'caption': patch.get('caption', ''),
                    'cs_name': patch.get('cs_name', ''),
                    'fix_comments': patch.get('fix_comments', ''),
                    'service_pack_in_effect': patch.get('service_pack_in_effect', ''),
                    'status': patch.get('status', 'Unknown')
                }
                
                patches.append(processed_patch)
        
        # Sort by installation date (newest first)
        patches.sort(key=lambda x: x['installed_on'] or '', reverse=True)
        
        return patches
    
    def _process_pending_updates(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process pending updates data"""
        pending = []
        pending_list = installs_data.get('pending_updates', [])
        
        for update in pending_list:
            if isinstance(update, dict):
                processed_update = {
                    'title': update.get('title', 'Unknown Update'),
                    'kb_number': update.get('kb_number', ''),
                    'description': update.get('description', ''),
                    'size': self.get_long_value(update, 'size', 0),
                    'severity': update.get('severity', 'Unknown'),
                    'classification': update.get('classification', 'Unknown'),
                    'support_url': update.get('support_url', ''),
                    'msrc_severity': update.get('msrc_severity', ''),
                    'auto_download': self.get_bool_value(update, 'auto_download', False),
                    'auto_install': self.get_bool_value(update, 'auto_install', False),
                    'reboot_required': self.get_bool_value(update, 'reboot_required', False),
                    'is_downloaded': self.get_bool_value(update, 'is_downloaded', False),
                    'download_priority': self.get_int_value(update, 'download_priority', 0),
                    'categories': update.get('categories', []),
                    'deadline': self._parse_datetime(update.get('deadline'))
                }
                
                pending.append(processed_update)
        
        # Sort by severity and then by size
        severity_order = {'Critical': 0, 'Important': 1, 'Moderate': 2, 'Low': 3, 'Unknown': 4}
        pending.sort(key=lambda x: (severity_order.get(x['severity'], 4), -x['size']))
        
        return pending
    
    def _process_package_managers(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process package managers data (Chocolatey, Winget, etc.)"""
        package_managers = []
        pm_list = installs_data.get('package_managers', [])
        
        for pm in pm_list:
            if isinstance(pm, dict):
                processed_pm = {
                    'name': pm.get('name', 'Unknown'),
                    'version': pm.get('version', ''),
                    'installed_packages': self._process_pm_packages(pm.get('packages', [])),
                    'package_count': len(pm.get('packages', [])),
                    'last_update_check': self._parse_datetime(pm.get('last_update_check')),
                    'update_available_count': self.get_int_value(pm, 'update_available_count', 0),
                    'auto_update_enabled': self.get_bool_value(pm, 'auto_update_enabled', False),
                    'configuration': pm.get('configuration', {})
                }
                
                package_managers.append(processed_pm)
        
        return package_managers
    
    def _process_pm_packages(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process packages from package managers"""
        processed_packages = []
        
        for package in packages:
            if isinstance(package, dict):
                processed_package = {
                    'name': package.get('name', 'Unknown'),
                    'version': package.get('version', ''),
                    'latest_version': package.get('latest_version', ''),
                    'installed_date': self._parse_datetime(package.get('installed_date')),
                    'update_available': self.get_bool_value(package, 'update_available', False),
                    'source': package.get('source', ''),
                    'description': package.get('description', ''),
                    'author': package.get('author', ''),
                    'dependencies': package.get('dependencies', [])
                }
                
                processed_packages.append(processed_package)
        
        return processed_packages
    
    def _process_update_settings(self, installs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Windows Update settings"""
        settings_data = installs_data.get('update_settings', {})
        
        return {
            'automatic_updates_enabled': self.get_bool_value(settings_data, 'automatic_updates_enabled', False),
            'install_updates_automatically': self.get_bool_value(settings_data, 'install_updates_automatically', False),
            'download_updates_automatically': self.get_bool_value(settings_data, 'download_updates_automatically', False),
            'notify_before_download': self.get_bool_value(settings_data, 'notify_before_download', False),
            'notify_before_install': self.get_bool_value(settings_data, 'notify_before_install', False),
            'scheduled_install_day': settings_data.get('scheduled_install_day', 'Never'),
            'scheduled_install_time': settings_data.get('scheduled_install_time', ''),
            'active_hours_start': settings_data.get('active_hours_start', ''),
            'active_hours_end': settings_data.get('active_hours_end', ''),
            'pause_updates_until': self._parse_datetime(settings_data.get('pause_updates_until')),
            'defer_feature_updates_days': self.get_int_value(settings_data, 'defer_feature_updates_days', 0),
            'defer_quality_updates_days': self.get_int_value(settings_data, 'defer_quality_updates_days', 0),
            'wsus_server': settings_data.get('wsus_server', ''),
            'update_source': settings_data.get('update_source', 'Windows Update')
        }
    
    def _process_update_history(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process update installation history"""
        history = []
        history_list = installs_data.get('update_history', [])
        
        for entry in history_list:
            if isinstance(entry, dict):
                processed_entry = {
                    'operation': entry.get('operation', 'Unknown'),  # Install, Uninstall, etc.
                    'result_code': self.get_int_value(entry, 'result_code', 0),
                    'result_description': entry.get('result_description', ''),
                    'date': self._parse_datetime(entry.get('date')),
                    'title': entry.get('title', ''),
                    'description': entry.get('description', ''),
                    'kb_numbers': entry.get('kb_numbers', []),
                    'client_application_id': entry.get('client_application_id', ''),
                    'service_id': entry.get('service_id', ''),
                    'unmapped_result_code': self.get_int_value(entry, 'unmapped_result_code', 0),
                    'server_selection': self.get_int_value(entry, 'server_selection', 0)
                }
                
                history.append(processed_entry)
        
        # Sort by date (newest first)
        history.sort(key=lambda x: x['date'] or '', reverse=True)
        
        return history
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for installs data"""
        windows_updates = processed_data['windows_updates']
        pending_updates = processed_data['pending_updates']
        patches = processed_data['installed_patches']
        package_managers = processed_data['package_managers']
        update_settings = processed_data['update_settings']
        
        # Calculate summary statistics
        summary = {
            'total_installed_updates': len(windows_updates),
            'total_pending_updates': len(pending_updates),
            'total_patches': len(patches),
            'total_package_managers': len(package_managers),
            'critical_pending': len([u for u in pending_updates if u['severity'] == 'Critical']),
            'important_pending': len([u for u in pending_updates if u['severity'] == 'Important']),
            'reboot_required_count': len([u for u in pending_updates if u['reboot_required']]),
            'total_pending_size': sum(u['size'] for u in pending_updates),
            'automatic_updates_enabled': update_settings.get('automatic_updates_enabled', False),
            'last_update_date': self._get_last_update_date(windows_updates),
            'update_classifications': self._get_update_classifications(windows_updates),
            'severity_distribution': self._get_severity_distribution(windows_updates + pending_updates),
            'package_manager_summary': self._get_package_manager_summary(package_managers)
        }
        
        return summary
    
    def _get_last_update_date(self, updates: List[Dict[str, Any]]) -> Optional[str]:
        """Get the date of the most recent update installation"""
        if not updates:
            return None
        
        latest_date = None
        for update in updates:
            install_date = update.get('installed_date')
            if install_date and (latest_date is None or install_date > latest_date):
                latest_date = install_date
        
        return latest_date
    
    def _get_update_classifications(self, updates: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of updates by classification"""
        classifications = {}
        for update in updates:
            classification = update.get('classification', 'Unknown')
            classifications[classification] = classifications.get(classification, 0) + 1
        return classifications
    
    def _get_severity_distribution(self, updates: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of updates by severity"""
        severities = {}
        for update in updates:
            severity = update.get('severity', 'Unknown')
            severities[severity] = severities.get(severity, 0) + 1
        return severities
    
    def _get_package_manager_summary(self, package_managers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of package managers"""
        if not package_managers:
            return {
                'total_packages': 0,
                'updates_available': 0,
                'managers': []
            }
        
        total_packages = sum(pm['package_count'] for pm in package_managers)
        updates_available = sum(pm['update_available_count'] for pm in package_managers)
        
        return {
            'total_packages': total_packages,
            'updates_available': updates_available,
            'managers': [
                {
                    'name': pm['name'],
                    'version': pm['version'],
                    'package_count': pm['package_count'],
                    'updates_available': pm['update_available_count']
                }
                for pm in package_managers
            ]
        }
    
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
