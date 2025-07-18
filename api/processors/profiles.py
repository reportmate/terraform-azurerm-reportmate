"""
Profiles Module Processor for ReportMate
Handles user profiles, settings, and configuration data
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class ProfilesProcessor(BaseModuleProcessor):
    """
    Processor for profiles module data
    Handles user profiles, browser data, application settings, and personalization
    """
    
    @property
    def module_id(self) -> str:
        return "profiles"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process profiles data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed profiles data
        """
        self.logger.debug(f"Processing profiles module for device {device_id}")
        
        # Extract profiles data from the device payload
        profiles_data = device_data.get('profiles', {})
        
        # Build processed profiles data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'user_profiles': self._process_user_profiles(profiles_data),
            'browser_profiles': self._process_browser_profiles(profiles_data),
            'application_settings': self._process_application_settings(profiles_data),
            'desktop_settings': self._process_desktop_settings(profiles_data),
            'registry_profiles': self._process_registry_profiles(profiles_data),
            'recent_documents': self._process_recent_documents(profiles_data),
            'folder_redirection': self._process_folder_redirection(profiles_data),
            'roaming_profiles': self._process_roaming_profiles(profiles_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        self.logger.info(f"Profiles processed - {len(processed_data['user_profiles'])} user profiles, "
                        f"{len(processed_data['browser_profiles'])} browser profiles, "
                        f"{len(processed_data['application_settings'])} app settings")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate profiles module data
        
        Args:
            data: Processed profiles data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'user_profiles']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Profiles validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Profiles validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _process_user_profiles(self, profiles_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process user profiles data"""
        profiles = []
        profiles_list = profiles_data.get('user_profiles', [])
        
        for profile in profiles_list:
            if isinstance(profile, dict):
                processed_profile = {
                    'username': profile.get('username', 'Unknown'),
                    'sid': profile.get('sid', ''),
                    'profile_path': profile.get('profile_path', ''),
                    'profile_type': profile.get('profile_type', 'Unknown'),
                    'profile_size': self.get_long_value(profile, 'profile_size', 0),
                    'last_use_time': self._parse_datetime(profile.get('last_use_time')),
                    'last_download_time': self._parse_datetime(profile.get('last_download_time')),
                    'last_upload_time': self._parse_datetime(profile.get('last_upload_time')),
                    'profile_state': profile.get('profile_state', 'Unknown'),
                    'health_status': profile.get('health_status', 'Unknown'),
                    'roaming_configured': self.get_bool_value(profile, 'roaming_configured', False),
                    'roaming_available': self.get_bool_value(profile, 'roaming_available', False),
                    'roaming_preference': profile.get('roaming_preference', 'Unknown'),
                    'special_accounts': self.get_bool_value(profile, 'special_accounts', False),
                    'loaded': self.get_bool_value(profile, 'loaded', False),
                    'local_path': profile.get('local_path', ''),
                    'central_profile': profile.get('central_profile', ''),
                    'profile_quota': self.get_long_value(profile, 'profile_quota', 0),
                    'profile_quota_used': self.get_long_value(profile, 'profile_quota_used', 0),
                    'folders': self._process_profile_folders(profile.get('folders', {}))
                }
                
                profiles.append(processed_profile)
        
        # Sort by username
        profiles.sort(key=lambda x: x['username'].lower())
        
        return profiles
    
    def _process_profile_folders(self, folders_data: Dict[str, Any]) -> Dict[str, str]:
        """Process special folders within a profile"""
        return {
            'desktop': folders_data.get('desktop', ''),
            'documents': folders_data.get('documents', ''),
            'downloads': folders_data.get('downloads', ''),
            'pictures': folders_data.get('pictures', ''),
            'music': folders_data.get('music', ''),
            'videos': folders_data.get('videos', ''),
            'favorites': folders_data.get('favorites', ''),
            'start_menu': folders_data.get('start_menu', ''),
            'startup': folders_data.get('startup', ''),
            'app_data': folders_data.get('app_data', ''),
            'local_app_data': folders_data.get('local_app_data', ''),
            'temp': folders_data.get('temp', ''),
            'recent': folders_data.get('recent', ''),
            'send_to': folders_data.get('send_to', ''),
            'history': folders_data.get('history', ''),
            'cookies': folders_data.get('cookies', ''),
            'cache': folders_data.get('cache', '')
        }
    
    def _process_browser_profiles(self, profiles_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process browser profiles data"""
        browser_profiles = []
        browsers_list = profiles_data.get('browser_profiles', [])
        
        for browser in browsers_list:
            if isinstance(browser, dict):
                processed_browser = {
                    'browser_name': browser.get('browser_name', 'Unknown'),
                    'browser_version': browser.get('browser_version', ''),
                    'profile_name': browser.get('profile_name', 'Default'),
                    'profile_path': browser.get('profile_path', ''),
                    'is_default_profile': self.get_bool_value(browser, 'is_default_profile', False),
                    'last_used': self._parse_datetime(browser.get('last_used')),
                    'profile_size': self.get_long_value(browser, 'profile_size', 0),
                    'bookmarks_count': self.get_int_value(browser, 'bookmarks_count', 0),
                    'history_count': self.get_int_value(browser, 'history_count', 0),
                    'extensions_count': self.get_int_value(browser, 'extensions_count', 0),
                    'cookies_count': self.get_int_value(browser, 'cookies_count', 0),
                    'settings': self._process_browser_settings(browser.get('settings', {})),
                    'security_settings': self._process_browser_security(browser.get('security_settings', {})),
                    'sync_settings': self._process_browser_sync(browser.get('sync_settings', {})),
                    'homepage': browser.get('homepage', ''),
                    'startup_urls': browser.get('startup_urls', []),
                    'search_engines': self._process_search_engines(browser.get('search_engines', [])),
                    'top_sites': self._process_top_sites(browser.get('top_sites', []))
                }
                
                browser_profiles.append(processed_browser)
        
        # Sort by browser name then profile name
        browser_profiles.sort(key=lambda x: (x['browser_name'], x['profile_name']))
        
        return browser_profiles
    
    def _process_browser_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Process browser settings"""
        return {
            'default_search_engine': settings.get('default_search_engine', ''),
            'homepage_is_new_tab': self.get_bool_value(settings, 'homepage_is_new_tab', False),
            'startup_action': settings.get('startup_action', 'Unknown'),
            'show_home_button': self.get_bool_value(settings, 'show_home_button', False),
            'show_bookmarks_bar': self.get_bool_value(settings, 'show_bookmarks_bar', False),
            'downloads_location': settings.get('downloads_location', ''),
            'ask_where_to_save': self.get_bool_value(settings, 'ask_where_to_save', False),
            'clear_on_exit': self.get_bool_value(settings, 'clear_on_exit', False),
            'password_manager_enabled': self.get_bool_value(settings, 'password_manager_enabled', False),
            'autofill_enabled': self.get_bool_value(settings, 'autofill_enabled', False),
            'popup_blocked': self.get_bool_value(settings, 'popup_blocked', False),
            'javascript_enabled': self.get_bool_value(settings, 'javascript_enabled', True),
            'images_enabled': self.get_bool_value(settings, 'images_enabled', True),
            'plugins_enabled': self.get_bool_value(settings, 'plugins_enabled', True)
        }
    
    def _process_browser_security(self, security: Dict[str, Any]) -> Dict[str, Any]:
        """Process browser security settings"""
        return {
            'safe_browsing_enabled': self.get_bool_value(security, 'safe_browsing_enabled', True),
            'enhanced_protection': self.get_bool_value(security, 'enhanced_protection', False),
            'password_breach_detection': self.get_bool_value(security, 'password_breach_detection', False),
            'site_isolation_enabled': self.get_bool_value(security, 'site_isolation_enabled', False),
            'https_only_mode': self.get_bool_value(security, 'https_only_mode', False),
            'dns_over_https': self.get_bool_value(security, 'dns_over_https', False),
            'privacy_sandbox': self.get_bool_value(security, 'privacy_sandbox', False),
            'tracking_protection': security.get('tracking_protection', 'Unknown'),
            'cookie_settings': security.get('cookie_settings', 'Unknown'),
            'security_level': security.get('security_level', 'Unknown')
        }
    
    def _process_browser_sync(self, sync: Dict[str, Any]) -> Dict[str, Any]:
        """Process browser sync settings"""
        return {
            'sync_enabled': self.get_bool_value(sync, 'sync_enabled', False),
            'sync_account': sync.get('sync_account', ''),
            'sync_bookmarks': self.get_bool_value(sync, 'sync_bookmarks', False),
            'sync_history': self.get_bool_value(sync, 'sync_history', False),
            'sync_passwords': self.get_bool_value(sync, 'sync_passwords', False),
            'sync_settings': self.get_bool_value(sync, 'sync_settings', False),
            'sync_extensions': self.get_bool_value(sync, 'sync_extensions', False),
            'sync_themes': self.get_bool_value(sync, 'sync_themes', False),
            'sync_apps': self.get_bool_value(sync, 'sync_apps', False),
            'last_sync': self._parse_datetime(sync.get('last_sync'))
        }
    
    def _process_search_engines(self, engines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process search engines"""
        processed_engines = []
        
        for engine in engines:
            if isinstance(engine, dict):
                processed_engine = {
                    'name': engine.get('name', ''),
                    'keyword': engine.get('keyword', ''),
                    'url': engine.get('url', ''),
                    'is_default': self.get_bool_value(engine, 'is_default', False),
                    'created_by_policy': self.get_bool_value(engine, 'created_by_policy', False),
                    'prepopulated': self.get_bool_value(engine, 'prepopulated', False)
                }
                processed_engines.append(processed_engine)
        
        return processed_engines
    
    def _process_top_sites(self, sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process top/most visited sites"""
        processed_sites = []
        
        for site in sites:
            if isinstance(site, dict):
                processed_site = {
                    'title': site.get('title', ''),
                    'url': site.get('url', ''),
                    'visit_count': self.get_int_value(site, 'visit_count', 0),
                    'last_visit': self._parse_datetime(site.get('last_visit'))
                }
                processed_sites.append(processed_site)
        
        return processed_sites
    
    def _process_application_settings(self, profiles_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process application settings data"""
        app_settings = []
        settings_list = profiles_data.get('application_settings', [])
        
        for setting in settings_list:
            if isinstance(setting, dict):
                processed_setting = {
                    'application_name': setting.get('application_name', 'Unknown'),
                    'application_version': setting.get('application_version', ''),
                    'settings_location': setting.get('settings_location', ''),
                    'config_files': setting.get('config_files', []),
                    'registry_keys': setting.get('registry_keys', []),
                    'user_data_path': setting.get('user_data_path', ''),
                    'cache_path': setting.get('cache_path', ''),
                    'log_path': setting.get('log_path', ''),
                    'recent_files': setting.get('recent_files', []),
                    'preferences': setting.get('preferences', {}),
                    'plugins': setting.get('plugins', []),
                    'themes': setting.get('themes', []),
                    'last_used': self._parse_datetime(setting.get('last_used')),
                    'settings_size': self.get_long_value(setting, 'settings_size', 0)
                }
                
                app_settings.append(processed_setting)
        
        # Sort by application name
        app_settings.sort(key=lambda x: x['application_name'].lower())
        
        return app_settings
    
    def _process_desktop_settings(self, profiles_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process desktop and personalization settings"""
        desktop_data = profiles_data.get('desktop_settings', {})
        
        return {
            'wallpaper_path': desktop_data.get('wallpaper_path', ''),
            'wallpaper_style': desktop_data.get('wallpaper_style', 'Unknown'),
            'theme_name': desktop_data.get('theme_name', ''),
            'color_scheme': desktop_data.get('color_scheme', 'Unknown'),
            'accent_color': desktop_data.get('accent_color', ''),
            'transparency_enabled': self.get_bool_value(desktop_data, 'transparency_enabled', False),
            'dark_mode_enabled': self.get_bool_value(desktop_data, 'dark_mode_enabled', False),
            'screen_saver': desktop_data.get('screen_saver', ''),
            'screen_saver_timeout': self.get_int_value(desktop_data, 'screen_saver_timeout', 0),
            'screen_saver_secure': self.get_bool_value(desktop_data, 'screen_saver_secure', False),
            'power_scheme': desktop_data.get('power_scheme', 'Unknown'),
            'display_settings': self._process_display_settings(desktop_data.get('display_settings', {})),
            'taskbar_settings': self._process_taskbar_settings(desktop_data.get('taskbar_settings', {})),
            'start_menu_settings': self._process_start_menu_settings(desktop_data.get('start_menu_settings', {}))
        }
    
    def _process_display_settings(self, display: Dict[str, Any]) -> Dict[str, Any]:
        """Process display settings"""
        return {
            'resolution': display.get('resolution', ''),
            'orientation': display.get('orientation', 'Unknown'),
            'refresh_rate': self.get_int_value(display, 'refresh_rate', 0),
            'color_depth': self.get_int_value(display, 'color_depth', 0),
            'scaling': self.get_int_value(display, 'scaling', 100),
            'multiple_displays': display.get('multiple_displays', 'Unknown'),
            'primary_display': self.get_bool_value(display, 'primary_display', True)
        }
    
    def _process_taskbar_settings(self, taskbar: Dict[str, Any]) -> Dict[str, Any]:
        """Process taskbar settings"""
        return {
            'position': taskbar.get('position', 'Bottom'),
            'auto_hide': self.get_bool_value(taskbar, 'auto_hide', False),
            'lock_taskbar': self.get_bool_value(taskbar, 'lock_taskbar', True),
            'small_buttons': self.get_bool_value(taskbar, 'small_buttons', False),
            'combine_buttons': taskbar.get('combine_buttons', 'Always'),
            'show_labels': self.get_bool_value(taskbar, 'show_labels', True),
            'notification_area': taskbar.get('notification_area', {}),
            'toolbars': taskbar.get('toolbars', [])
        }
    
    def _process_start_menu_settings(self, start_menu: Dict[str, Any]) -> Dict[str, Any]:
        """Process Start menu settings"""
        return {
            'use_start_screen': self.get_bool_value(start_menu, 'use_start_screen', False),
            'show_recent_items': self.get_bool_value(start_menu, 'show_recent_items', True),
            'show_frequent_items': self.get_bool_value(start_menu, 'show_frequent_items', True),
            'show_suggestions': self.get_bool_value(start_menu, 'show_suggestions', False),
            'live_tiles_enabled': self.get_bool_value(start_menu, 'live_tiles_enabled', True),
            'tile_groups': start_menu.get('tile_groups', []),
            'pinned_items': start_menu.get('pinned_items', [])
        }
    
    def _process_registry_profiles(self, profiles_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process registry-based profile data"""
        reg_profiles = []
        profiles_list = profiles_data.get('registry_profiles', [])
        
        for profile in profiles_list:
            if isinstance(profile, dict):
                processed_profile = {
                    'key_path': profile.get('key_path', ''),
                    'profile_name': profile.get('profile_name', ''),
                    'values': profile.get('values', {}),
                    'subkeys': profile.get('subkeys', []),
                    'last_modified': self._parse_datetime(profile.get('last_modified')),
                    'size': self.get_long_value(profile, 'size', 0)
                }
                
                reg_profiles.append(processed_profile)
        
        return reg_profiles
    
    def _process_recent_documents(self, profiles_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process recent documents data"""
        recent_docs = []
        docs_list = profiles_data.get('recent_documents', [])
        
        for doc in docs_list:
            if isinstance(doc, dict):
                processed_doc = {
                    'name': doc.get('name', ''),
                    'path': doc.get('path', ''),
                    'application': doc.get('application', ''),
                    'last_accessed': self._parse_datetime(doc.get('last_accessed')),
                    'file_type': doc.get('file_type', ''),
                    'file_size': self.get_long_value(doc, 'file_size', 0),
                    'exists': self.get_bool_value(doc, 'exists', True)
                }
                
                recent_docs.append(processed_doc)
        
        # Sort by last accessed (newest first)
        recent_docs.sort(key=lambda x: x['last_accessed'] or '', reverse=True)
        
        return recent_docs
    
    def _process_folder_redirection(self, profiles_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process folder redirection settings"""
        redirection_data = profiles_data.get('folder_redirection', {})
        
        return {
            'enabled': self.get_bool_value(redirection_data, 'enabled', False),
            'policy_applied': self.get_bool_value(redirection_data, 'policy_applied', False),
            'redirected_folders': redirection_data.get('redirected_folders', {}),
            'redirection_method': redirection_data.get('redirection_method', 'Unknown'),
            'target_location': redirection_data.get('target_location', ''),
            'offline_files_enabled': self.get_bool_value(redirection_data, 'offline_files_enabled', False)
        }
    
    def _process_roaming_profiles(self, profiles_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process roaming profile settings"""
        roaming_data = profiles_data.get('roaming_profiles', {})
        
        return {
            'enabled': self.get_bool_value(roaming_data, 'enabled', False),
            'server_path': roaming_data.get('server_path', ''),
            'cache_enabled': self.get_bool_value(roaming_data, 'cache_enabled', False),
            'slow_link_detection': self.get_bool_value(roaming_data, 'slow_link_detection', False),
            'background_upload': self.get_bool_value(roaming_data, 'background_upload', False),
            'profile_size_limit': self.get_long_value(roaming_data, 'profile_size_limit', 0),
            'exclude_directories': roaming_data.get('exclude_directories', []),
            'include_registry': self.get_bool_value(roaming_data, 'include_registry', True),
            'delete_cached_copies': self.get_bool_value(roaming_data, 'delete_cached_copies', False)
        }
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for profiles data"""
        user_profiles = processed_data['user_profiles']
        browser_profiles = processed_data['browser_profiles']
        app_settings = processed_data['application_settings']
        recent_docs = processed_data['recent_documents']
        
        # Calculate summary statistics
        summary = {
            'total_user_profiles': len(user_profiles),
            'loaded_profiles': len([p for p in user_profiles if p['loaded']]),
            'roaming_profiles': len([p for p in user_profiles if p['roaming_configured']]),
            'total_browser_profiles': len(browser_profiles),
            'default_browser_profiles': len([p for p in browser_profiles if p['is_default_profile']]),
            'total_app_settings': len(app_settings),
            'total_recent_documents': len(recent_docs),
            'total_profile_size': sum(p['profile_size'] for p in user_profiles),
            'browsers_with_profiles': len(set(p['browser_name'] for p in browser_profiles)),
            'applications_with_settings': len(set(a['application_name'] for a in app_settings)),
            'profile_types': self._get_profile_type_breakdown(user_profiles),
            'browser_breakdown': self._get_browser_breakdown(browser_profiles),
            'recent_file_types': self._get_file_type_breakdown(recent_docs),
            'largest_profiles': self._get_largest_profiles(user_profiles, 5)
        }
        
        return summary
    
    def _get_profile_type_breakdown(self, profiles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of profiles by type"""
        types = {}
        for profile in profiles:
            profile_type = profile.get('profile_type', 'Unknown')
            types[profile_type] = types.get(profile_type, 0) + 1
        return types
    
    def _get_browser_breakdown(self, browser_profiles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of browser profiles by browser"""
        browsers = {}
        for profile in browser_profiles:
            browser = profile.get('browser_name', 'Unknown')
            browsers[browser] = browsers.get(browser, 0) + 1
        return browsers
    
    def _get_file_type_breakdown(self, recent_docs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of recent documents by file type"""
        types = {}
        for doc in recent_docs:
            file_type = doc.get('file_type', 'Unknown')
            types[file_type] = types.get(file_type, 0) + 1
        return types
    
    def _get_largest_profiles(self, profiles: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Get largest profiles by size"""
        profiles_with_size = [p for p in profiles if p.get('profile_size', 0) > 0]
        profiles_with_size.sort(key=lambda x: x['profile_size'], reverse=True)
        
        return [{
            'username': profile['username'],
            'profile_size': profile['profile_size'],
            'profile_type': profile['profile_type']
        } for profile in profiles_with_size[:limit]]
    
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
