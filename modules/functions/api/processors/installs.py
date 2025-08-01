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
    
    @staticmethod
    def map_cimian_status_to_reportmate(cimian_status: str) -> str:
        """
        Maps Cimian's detailed status values to ReportMate's simplified dashboard statuses
        Uses only: Installed, Pending, Warning, Error, Removed
        """
        if not cimian_status:
            return "Pending"  # Default unknown to Pending
            
        status_lower = cimian_status.lower()
        
        # ReportMate simplified status mapping - Only 5 status types
        status_mapping = {
            # Installed - Successfully installed and working
            "installed": "Installed",
            "success": "Installed",
            "install loop": "Installed",  # Technically installed despite issues
            "install_loop": "Installed",
            
            # Pending - Needs action or in progress
            "available": "Pending",
            "pending": "Pending",
            "update available": "Pending",
            "update_available": "Pending", 
            "downloading": "Pending",
            "installing": "Pending",
            
            # Warning - Installed but with issues
            "warning": "Warning",
            
            # Error - Failed installation or critical issues
            "error": "Error",
            "failed": "Error",
            "fail": "Error",
            
            # Removed - Uninstalled or removed
            "removed": "Removed",
            "uninstalled": "Removed"
        }
        
        mapped_status = status_mapping.get(status_lower, "Pending")
        
        # Special handling for status without explicit mapping
        if mapped_status == "Pending" and status_lower not in status_mapping:
            # Apply heuristics for common patterns
            if "loop" in status_lower or "success" in status_lower or "ok" in status_lower:
                return "Installed"
            elif "fail" in status_lower or "error" in status_lower:
                return "Error"
            elif "warn" in status_lower:
                return "Warning"
            elif "remov" in status_lower or "uninstall" in status_lower:
                return "Removed"
        
        return mapped_status
    
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
        
        # Build processed installs data with Cimian integration
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'cimian': self._process_cimian_data(installs_data),
            'munki': self._process_munki_data(installs_data),
            'recent_installs': self._process_recent_installs(installs_data),
            'pending_installs': self._process_pending_installs(installs_data),
            'recent_sessions': self._process_recent_sessions(installs_data),
            'recent_events': self._process_recent_events(installs_data),
            'cache_status': self._process_cache_status(installs_data),
            'bootstrap_mode_active': installs_data.get('BootstrapModeActive', False),
            'last_check_in': self._parse_datetime(installs_data.get('LastCheckIn')),
            # Legacy Windows Updates support for backward compatibility
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
        
        # Log Cimian-specific info if available
        cimian_info = processed_data.get('cimian', {})
        if cimian_info.get('is_installed'):
            self.logger.info(f"Installs processed - Cimian installed: {cimian_info.get('version', 'Unknown')}, "
                           f"Sessions: {len(processed_data['recent_sessions'])}, "
                           f"Events: {len(processed_data['recent_events'])}, "
                           f"Installs: {len(processed_data['recent_installs'])}")
        else:
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
        required_fields = ['module_id', 'device_id', 'collected_at']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Installs validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Installs validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        # Check if we have either Cimian data or Windows Updates data
        has_cimian = data.get('cimian', {}).get('is_installed', False)
        has_windows_updates = len(data.get('windows_updates', [])) > 0
        
        if not has_cimian and not has_windows_updates:
            self.logger.warning("Installs validation warning - no Cimian or Windows Updates data found")
            # Don't fail validation, just warn
        
        return True

    def _process_cimian_data(self, installs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Cimian installation manager data"""
        # Support both PascalCase (old) and camelCase (new) field names
        cimian_data = installs_data.get('Cimian', installs_data.get('cimian', {}))
        
        return {
            'is_installed': self.get_bool_value(cimian_data, 'IsInstalled', 
                                               self.get_bool_value(cimian_data, 'isInstalled', False)),
            'version': cimian_data.get('Version', cimian_data.get('version', '')),
            'last_run': self._parse_datetime(cimian_data.get('LastRun', cimian_data.get('lastRun'))),
            'status': cimian_data.get('Status', cimian_data.get('status', 'Unknown')),
            'pending_packages': cimian_data.get('PendingPackages', cimian_data.get('pendingPackages', [])),
            'services': cimian_data.get('Services', cimian_data.get('services', [])),
            'active_processes': cimian_data.get('ActiveProcesses', cimian_data.get('activeProcesses', [])),
            'registry_config': cimian_data.get('RegistryConfig', cimian_data.get('registryConfig', {})),
            'config': cimian_data.get('Config', cimian_data.get('config', {})),  # Primary config.yaml data
            'bootstrap_flag_present': self.get_bool_value(cimian_data, 'BootstrapFlagPresent', 
                                                         self.get_bool_value(cimian_data, 'bootstrapFlagPresent', False)),
            'last_session_time': self._parse_datetime(cimian_data.get('LastSessionTime', 
                                                                     cimian_data.get('lastSessionTime'))),
            'total_sessions': self.get_int_value(cimian_data, 'TotalSessions', 
                                                self.get_int_value(cimian_data, 'totalSessions', 0)),
            'reports': cimian_data.get('Reports', cimian_data.get('reports', {}))
        }

    def _process_munki_data(self, installs_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process Munki installation manager data"""
        munki_data = installs_data.get('Munki')
        if not munki_data:
            return None
        
        return {
            'version': munki_data.get('version', ''),
            'last_run': self._parse_datetime(munki_data.get('last_run')),
            'status': munki_data.get('status', 'Unknown')
        }

    def _process_recent_installs(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process recent software installations with enhanced Cimian format"""
        installs = []
        
        # Primary source: enhanced Cimian items array
        cimian_data = installs_data.get('Cimian', installs_data.get('cimian', {}))
        cimian_items = cimian_data.get('items', [])
        
        # Fallback: legacy RecentInstalls for backward compatibility
        if not cimian_items:
            cimian_items = installs_data.get('RecentInstalls', installs_data.get('recentInstalls', []))
        
        for install in cimian_items:
            if isinstance(install, dict):
                # Get original Cimian status and map it to ReportMate status
                original_status = install.get('currentStatus', install.get('Status', install.get('status', 'Unknown')))
                mapped_status = self.map_cimian_status_to_reportmate(original_status)
                
                processed_install = {
                    # Core fields - Enhanced Cimian structure
                    'id': install.get('id', install.get('Id', '')),
                    'name': install.get('itemName', install.get('Name', install.get('name', 'Unknown'))),
                    'display_name': install.get('displayName', install.get('DisplayName', install.get('displayName', ''))),
                    'item_type': install.get('itemType', install.get('ItemType', install.get('itemType', ''))),
                    'status': mapped_status,  # Use mapped ReportMate status
                    'original_status': original_status,  # Store original Cimian status for reference
                    'version': install.get('latestVersion', install.get('Version', install.get('version', ''))),
                    'installed_version': install.get('installedVersion', install.get('InstalledVersion', install.get('installedVersion', ''))),
                    'last_seen_in_session': install.get('lastSeenInSession', install.get('LastSeenInSession', install.get('lastSeenInSession', ''))),
                    'last_successful_time': self._parse_datetime(install.get('LastSuccessfulTime', install.get('lastSuccessfulTime'))),
                    'last_attempt_time': self._parse_datetime(install.get('lastAttemptTime', install.get('LastAttemptTime', install.get('lastAttemptTime')))),
                    'last_attempt_status': install.get('lastAttemptStatus', install.get('LastAttemptStatus', install.get('lastAttemptStatus', ''))),
                    'last_update': self._parse_datetime(install.get('lastUpdate', install.get('LastUpdate', install.get('lastUpdate')))),
                    'scheduled_time': self._parse_datetime(install.get('ScheduledTime', install.get('scheduledTime'))),
                    'source': install.get('Source', install.get('source', 'Unknown')),
                    'install_location': install.get('InstallLocation', install.get('installLocation', '')),
                    'publisher': install.get('Publisher', install.get('publisher', '')),
                    'install_date': self._parse_datetime(install.get('InstallDate', install.get('installDate'))),
                    # Enhanced tracking fields - enhanced Cimian structure
                    'has_install_loop': self.get_bool_value(install, 'installLoopDetected', 
                                                           self.get_bool_value(install, 'HasInstallLoop', 
                                                           self.get_bool_value(install, 'hasInstallLoop', False))),
                    'install_count': self.get_int_value(install, 'installCount', 
                                                       self.get_int_value(install, 'InstallCount', 
                                                       self.get_int_value(install, 'installCount', 0))),
                    'update_count': self.get_int_value(install, 'updateCount', 
                                                      self.get_int_value(install, 'UpdateCount', 
                                                      self.get_int_value(install, 'updateCount', 0))),
                    'failure_count': self.get_int_value(install, 'failureCount', 
                                                       self.get_int_value(install, 'FailureCount', 
                                                       self.get_int_value(install, 'failureCount', 0))),
                    'total_sessions': self.get_int_value(install, 'totalSessions', 
                                                        self.get_int_value(install, 'TotalSessions', 
                                                        self.get_int_value(install, 'totalSessions', 0))),
                    'install_method': install.get('installMethod', install.get('InstallMethod', install.get('installMethod', ''))),
                    'type': install.get('type', install.get('Type', install.get('type', ''))),
                    'recent_attempts': install.get('recentAttempts', install.get('RecentAttempts', install.get('recentAttempts', [])))
                }
                installs.append(processed_install)
        
        # Sort by install date (newest first)
        installs.sort(key=lambda x: x['install_date'] or '', reverse=True)
        return installs

    def _process_pending_installs(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process pending software installations"""
        pending = []
        pending_list = installs_data.get('PendingInstalls', [])
        
        for install in pending_list:
            if isinstance(install, dict):
                processed_install = {
                    'name': install.get('Name', 'Unknown'),
                    'version': install.get('Version', ''),
                    'status': install.get('Status', 'Pending'),
                    'scheduled_time': self._parse_datetime(install.get('ScheduledTime')),
                    'source': install.get('Source', 'Unknown'),
                    'install_location': install.get('InstallLocation', ''),
                    'publisher': install.get('Publisher', '')
                }
                pending.append(processed_install)
        
        return pending

    def _process_recent_sessions(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process recent Cimian sessions with enhanced format"""
        sessions = []
        
        # Primary source: enhanced Cimian sessions array
        cimian_data = installs_data.get('Cimian', installs_data.get('cimian', {}))
        cimian_sessions = cimian_data.get('sessions', [])
        
        # Fallback: legacy RecentSessions for backward compatibility
        if not cimian_sessions:
            cimian_sessions = installs_data.get('RecentSessions', installs_data.get('recentSessions', []))
        
        for session in cimian_sessions:
            if isinstance(session, dict):
                processed_session = {
                    'session_id': session.get('SessionId', session.get('sessionId', '')),
                    'run_type': session.get('RunType', session.get('runType', 'Unknown')),
                    'status': session.get('Status', session.get('status', 'Unknown')),
                    'start_time': self._parse_datetime(session.get('StartTime', session.get('startTime'))),
                    'end_time': self._parse_datetime(session.get('EndTime', session.get('endTime'))),
                    'duration': session.get('Duration', session.get('duration')),  # Keep as is, could be TimeSpan string
                    'duration_seconds': self.get_float_value(session, 'DurationSeconds', 
                                                           self.get_float_value(session, 'durationSeconds', 0.0)),
                    # Enhanced Cimian fields
                    'total_packages_managed': self.get_int_value(session, 'TotalPackagesManaged', 
                                                               self.get_int_value(session, 'totalPackagesManaged', 0)),
                    'packages_installed': self.get_int_value(session, 'PackagesInstalled', 
                                                           self.get_int_value(session, 'packagesInstalled', 0)),
                    'packages_pending': self.get_int_value(session, 'PackagesPending', 
                                                         self.get_int_value(session, 'packagesPending', 0)),
                    'packages_failed': self.get_int_value(session, 'PackagesFailed', 
                                                        self.get_int_value(session, 'packagesFailed', 0)),
                    'cache_size_mb': self.get_float_value(session, 'CacheSizeMb', 
                                                        self.get_float_value(session, 'cacheSizeMb', 0.0)),
                    # Legacy fields for backward compatibility
                    'total_actions': self.get_int_value(session, 'TotalActions', 
                                                       self.get_int_value(session, 'totalActions', 0)),
                    'installs': self.get_int_value(session, 'Installs', 
                                                  self.get_int_value(session, 'installs', 0)),
                    'updates': self.get_int_value(session, 'Updates', 
                                                 self.get_int_value(session, 'updates', 0)),
                    'removals': self.get_int_value(session, 'Removals', 
                                                  self.get_int_value(session, 'removals', 0)),
                    'successes': self.get_int_value(session, 'Successes', 
                                                   self.get_int_value(session, 'successes', 0)),
                    'failures': self.get_int_value(session, 'Failures', 
                                                  self.get_int_value(session, 'failures', 0)),
                    'packages_handled': session.get('PackagesHandled', session.get('packagesHandled', [])),
                    'environment': session.get('Environment', session.get('environment', {})),
                    'config': session.get('Config', session.get('config', {})),
                    'hostname': session.get('Hostname', session.get('hostname', '')),
                    'user': session.get('User', session.get('user', '')),
                    'process_id': self.get_int_value(session, 'ProcessId', 
                                                    self.get_int_value(session, 'processId', 0)),
                    'log_version': session.get('LogVersion', session.get('logVersion', ''))
                }
                sessions.append(processed_session)
        
        # Sort by start time (newest first)
        sessions.sort(key=lambda x: x['start_time'] or '', reverse=True)
        return sessions

    def _process_recent_events(self, installs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process recent Cimian events with enhanced format"""
        events = []
        
        # Primary source: enhanced Cimian events array  
        cimian_data = installs_data.get('Cimian', installs_data.get('cimian', {}))
        cimian_events = cimian_data.get('events', [])
        
        # Fallback: legacy RecentEvents for backward compatibility
        if not cimian_events:
            cimian_events = installs_data.get('RecentEvents', [])
        
        for event in cimian_events:
            if isinstance(event, dict):
                processed_event = {
                    'event_id': event.get('eventId', event.get('EventId', '')),
                    'session_id': event.get('sessionId', event.get('SessionId', '')),
                    'timestamp': self._parse_datetime(event.get('timestamp', event.get('Timestamp'))),
                    'level': event.get('level', event.get('Level', 'INFO')),
                    'event_type': event.get('eventType', event.get('EventType', 'general')),
                    'package': event.get('package', event.get('Package', '')),
                    'version': event.get('version', event.get('Version', '')),
                    'action': event.get('action', event.get('Action', '')),
                    'status': event.get('status', event.get('Status', '')),
                    'message': event.get('message', event.get('Message', '')),
                    'duration': event.get('duration', event.get('Duration')),  # Keep as is, could be TimeSpan string
                    'progress': event.get('progress', event.get('Progress')),
                    'error': event.get('error', event.get('Error', '')),
                    'context': event.get('context', event.get('Context', {})),
                    'source_file': event.get('sourceFile', event.get('SourceFile', '')),
                    'source_function': event.get('sourceFunction', event.get('SourceFunction', '')),
                    'source_line': self.get_int_value(event, 'sourceLine', self.get_int_value(event, 'SourceLine', 0)),
                    'log_file': event.get('logFile', event.get('LogFile', ''))
                }
                events.append(processed_event)
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        return events

    def _process_cache_status(self, installs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process cache status information"""
        cache_status = installs_data.get('CacheStatus', {})
        
        return {
            'total_size_bytes': self.get_long_value(cache_status, 'total_size_bytes', 0),
            'file_count': self.get_int_value(cache_status, 'file_count', 0),
            'latest_file': cache_status.get('latest_file', ''),
            'latest_modification': self._parse_datetime(cache_status.get('latest_modification'))
        }
    
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
        cimian_data = processed_data.get('cimian', {})
        recent_installs = processed_data['recent_installs']
        pending_installs = processed_data['pending_installs']
        recent_sessions = processed_data['recent_sessions']
        recent_events = processed_data['recent_events']
        
        # Legacy Windows Updates support
        windows_updates = processed_data['windows_updates'] 
        pending_updates = processed_data['pending_updates']
        patches = processed_data['installed_patches']
        package_managers = processed_data['package_managers']
        update_settings = processed_data['update_settings']
        
        # Calculate summary statistics - focus on Cimian if available
        if cimian_data.get('is_installed'):
            # Cimian-based summary
            error_events = [e for e in recent_events if e['level'] == 'ERROR']
            warn_events = [e for e in recent_events if e['level'] == 'WARN']
            
            summary = {
                'managed_installs_system': 'Cimian',
                'cimian_version': cimian_data.get('version', 'Unknown'),
                'cimian_status': cimian_data.get('status', 'Unknown'),
                'total_recent_installs': len(recent_installs),
                'total_pending_installs': len(pending_installs),
                'failed_installs': len([i for i in recent_installs if 'failed' in i.get('status', '').lower()]),
                'successful_installs': len([i for i in recent_installs if 'success' in i.get('status', '').lower() or i.get('status') == 'Installed']),
                'recent_sessions': len(recent_sessions),
                'recent_events': len(recent_events),
                'error_events': len(error_events),
                'warning_events': len(warn_events),
                'bootstrap_mode_active': processed_data.get('bootstrap_mode_active', False),
                'last_successful_session': self._get_last_successful_session(recent_sessions),
                'cache_info': processed_data.get('cache_status', {}),
                'registry_config': cimian_data.get('registry_config', {}),
                # Legacy support
                'total_installed_updates': len(windows_updates),
                'total_pending_updates': len(pending_updates),
                'total_patches': len(patches),
                'total_package_managers': len(package_managers)
            }
        else:
            # Legacy Windows Updates-based summary
            summary = {
                'managed_installs_system': 'Windows Updates',
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

    def _get_last_successful_session(self, sessions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the most recent successful session"""
        successful_sessions = [s for s in sessions if s.get('status', '').upper() == 'SUCCESS']
        if not successful_sessions:
            return None
        
        # Sessions are already sorted by start_time descending
        latest_session = successful_sessions[0]
        return {
            'session_id': latest_session.get('session_id'),
            'start_time': latest_session.get('start_time'),
            'successes': latest_session.get('successes', 0),
            'failures': latest_session.get('failures', 0),
            'packages_handled': latest_session.get('packages_handled', [])
        }
    
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
