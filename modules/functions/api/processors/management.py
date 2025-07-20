"""
Management Module Processor for ReportMate
Handles system management features and administrative tools
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class ManagementProcessor(BaseModuleProcessor):
    """
    Processor for management module data
    Handles services, scheduled tasks, group policies, and system management
    """
    
    @property
    def module_id(self) -> str:
        return "management"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process management data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed management data
        """
        self.logger.debug(f"Processing management module for device {device_id}")
        
        # Extract management data from the device payload
        management_data = device_data.get('management', {})
        
        # Build processed management data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'services': self._process_services(management_data),
            'scheduled_tasks': self._process_scheduled_tasks(management_data),
            'group_policies': self._process_group_policies(management_data),
            'registry_settings': self._process_registry_settings(management_data),
            'environment_variables': self._process_environment_variables(management_data),
            'system_configuration': self._process_system_configuration(management_data),
            'user_accounts': self._process_user_accounts(management_data),
            'local_groups': self._process_local_groups(management_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        self.logger.info(f"Management processed - {len(processed_data['services'])} services, "
                        f"{len(processed_data['scheduled_tasks'])} tasks, "
                        f"{len(processed_data['user_accounts'])} user accounts")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate management module data
        
        Args:
            data: Processed management data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'services']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Management validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Management validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _process_services(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process Windows services data"""
        services = []
        services_list = management_data.get('services', [])
        
        for service in services_list:
            if isinstance(service, dict):
                processed_service = {
                    'name': service.get('name', 'Unknown'),
                    'display_name': service.get('display_name', ''),
                    'description': service.get('description', ''),
                    'status': service.get('status', 'Unknown'),
                    'start_mode': service.get('start_mode', 'Unknown'),
                    'service_type': service.get('service_type', 'Unknown'),
                    'path_name': service.get('path_name', ''),
                    'process_id': self.get_int_value(service, 'process_id', 0),
                    'start_name': service.get('start_name', ''),
                    'state': service.get('state', 'Unknown'),
                    'accept_pause': self.get_bool_value(service, 'accept_pause', False),
                    'accept_stop': self.get_bool_value(service, 'accept_stop', False),
                    'desktop_interact': self.get_bool_value(service, 'desktop_interact', False),
                    'error_control': service.get('error_control', 'Unknown'),
                    'exit_code': self.get_int_value(service, 'exit_code', 0),
                    'tag_id': self.get_int_value(service, 'tag_id', 0),
                    'wait_hint': self.get_int_value(service, 'wait_hint', 0),
                    'dependencies': service.get('dependencies', []),
                    'depended_by': service.get('depended_by', [])
                }
                
                services.append(processed_service)
        
        # Sort by name for consistency
        services.sort(key=lambda x: x['name'].lower())
        
        return services
    
    def _process_scheduled_tasks(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process scheduled tasks data"""
        tasks = []
        tasks_list = management_data.get('scheduled_tasks', [])
        
        for task in tasks_list:
            if isinstance(task, dict):
                processed_task = {
                    'name': task.get('name', 'Unknown'),
                    'path': task.get('path', ''),
                    'description': task.get('description', ''),
                    'state': task.get('state', 'Unknown'),
                    'enabled': self.get_bool_value(task, 'enabled', False),
                    'hidden': self.get_bool_value(task, 'hidden', False),
                    'last_run_time': self._parse_datetime(task.get('last_run_time')),
                    'next_run_time': self._parse_datetime(task.get('next_run_time')),
                    'last_result': self.get_int_value(task, 'last_result', 0),
                    'number_of_missed_runs': self.get_int_value(task, 'number_of_missed_runs', 0),
                    'actions': self._process_task_actions(task.get('actions', [])),
                    'triggers': self._process_task_triggers(task.get('triggers', [])),
                    'author': task.get('author', ''),
                    'user_id': task.get('user_id', ''),
                    'run_as_user': task.get('run_as_user', ''),
                    'highest_available': self.get_bool_value(task, 'highest_available', False),
                    'compatibility': task.get('compatibility', 'Unknown')
                }
                
                tasks.append(processed_task)
        
        # Sort by path then by name
        tasks.sort(key=lambda x: (x['path'], x['name'].lower()))
        
        return tasks
    
    def _process_task_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process task actions"""
        processed_actions = []
        
        for action in actions:
            if isinstance(action, dict):
                processed_action = {
                    'type': action.get('type', 'Unknown'),
                    'path': action.get('path', ''),
                    'arguments': action.get('arguments', ''),
                    'working_directory': action.get('working_directory', ''),
                    'id': action.get('id', '')
                }
                processed_actions.append(processed_action)
        
        return processed_actions
    
    def _process_task_triggers(self, triggers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process task triggers"""
        processed_triggers = []
        
        for trigger in triggers:
            if isinstance(trigger, dict):
                processed_trigger = {
                    'type': trigger.get('type', 'Unknown'),
                    'enabled': self.get_bool_value(trigger, 'enabled', False),
                    'start_boundary': self._parse_datetime(trigger.get('start_boundary')),
                    'end_boundary': self._parse_datetime(trigger.get('end_boundary')),
                    'execution_time_limit': trigger.get('execution_time_limit', ''),
                    'repetition_interval': trigger.get('repetition_interval', ''),
                    'repetition_duration': trigger.get('repetition_duration', ''),
                    'stop_at_duration_end': self.get_bool_value(trigger, 'stop_at_duration_end', False),
                    'id': trigger.get('id', '')
                }
                processed_triggers.append(processed_trigger)
        
        return processed_triggers
    
    def _process_group_policies(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process group policy data"""
        policies = []
        policies_list = management_data.get('group_policies', [])
        
        for policy in policies_list:
            if isinstance(policy, dict):
                processed_policy = {
                    'name': policy.get('name', 'Unknown'),
                    'display_name': policy.get('display_name', ''),
                    'path': policy.get('path', ''),
                    'version': policy.get('version', ''),
                    'enabled': self.get_bool_value(policy, 'enabled', False),
                    'computer_enabled': self.get_bool_value(policy, 'computer_enabled', False),
                    'user_enabled': self.get_bool_value(policy, 'user_enabled', False),
                    'creation_time': self._parse_datetime(policy.get('creation_time')),
                    'modification_time': self._parse_datetime(policy.get('modification_time')),
                    'wmi_filter': policy.get('wmi_filter', ''),
                    'description': policy.get('description', ''),
                    'domain': policy.get('domain', ''),
                    'owner': policy.get('owner', ''),
                    'settings_count': self.get_int_value(policy, 'settings_count', 0)
                }
                
                policies.append(processed_policy)
        
        # Sort by name
        policies.sort(key=lambda x: x['name'].lower())
        
        return policies
    
    def _process_registry_settings(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process registry settings data"""
        settings = []
        settings_list = management_data.get('registry_settings', [])
        
        for setting in settings_list:
            if isinstance(setting, dict):
                processed_setting = {
                    'key_path': setting.get('key_path', ''),
                    'value_name': setting.get('value_name', ''),
                    'value_data': setting.get('value_data', ''),
                    'value_type': setting.get('value_type', 'Unknown'),
                    'hive': setting.get('hive', 'Unknown'),
                    'description': setting.get('description', ''),
                    'category': setting.get('category', 'Other'),
                    'last_modified': self._parse_datetime(setting.get('last_modified'))
                }
                
                settings.append(processed_setting)
        
        # Sort by key path then value name
        settings.sort(key=lambda x: (x['key_path'], x['value_name']))
        
        return settings
    
    def _process_environment_variables(self, management_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Process environment variables data"""
        env_vars = management_data.get('environment_variables', {})
        
        processed_env_vars = {}
        
        for scope in ['system', 'user']:
            scope_vars = []
            vars_list = env_vars.get(scope, [])
            
            for var in vars_list:
                if isinstance(var, dict):
                    processed_var = {
                        'name': var.get('name', ''),
                        'value': var.get('value', ''),
                        'type': var.get('type', 'String'),
                        'scope': scope
                    }
                    scope_vars.append(processed_var)
            
            # Sort by name
            scope_vars.sort(key=lambda x: x['name'].lower())
            processed_env_vars[scope] = scope_vars
        
        return processed_env_vars
    
    def _process_system_configuration(self, management_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process system configuration data"""
        config_data = management_data.get('system_configuration', {})
        
        return {
            'computer_name': config_data.get('computer_name', ''),
            'workgroup': config_data.get('workgroup', ''),
            'domain': config_data.get('domain', ''),
            'domain_role': config_data.get('domain_role', 'Unknown'),
            'part_of_domain': self.get_bool_value(config_data, 'part_of_domain', False),
            'automatic_managed_page_file': self.get_bool_value(config_data, 'automatic_managed_page_file', False),
            'page_file_path': config_data.get('page_file_path', ''),
            'virtual_memory_max_size': self.get_long_value(config_data, 'virtual_memory_max_size', 0),
            'virtual_memory_current_size': self.get_long_value(config_data, 'virtual_memory_current_size', 0),
            'dump_file_path': config_data.get('dump_file_path', ''),
            'crash_dump_setting': config_data.get('crash_dump_setting', 'Unknown'),
            'system_startup_delay': self.get_int_value(config_data, 'system_startup_delay', 0),
            'system_failure_options': config_data.get('system_failure_options', {}),
            'performance_options': config_data.get('performance_options', {})
        }
    
    def _process_user_accounts(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process user accounts data"""
        accounts = []
        accounts_list = management_data.get('user_accounts', [])
        
        for account in accounts_list:
            if isinstance(account, dict):
                processed_account = {
                    'name': account.get('name', 'Unknown'),
                    'full_name': account.get('full_name', ''),
                    'description': account.get('description', ''),
                    'sid': account.get('sid', ''),
                    'account_type': account.get('account_type', 'Unknown'),
                    'disabled': self.get_bool_value(account, 'disabled', False),
                    'locked_out': self.get_bool_value(account, 'locked_out', False),
                    'password_changeable': self.get_bool_value(account, 'password_changeable', True),
                    'password_expires': self.get_bool_value(account, 'password_expires', True),
                    'password_required': self.get_bool_value(account, 'password_required', True),
                    'local_account': self.get_bool_value(account, 'local_account', True),
                    'domain': account.get('domain', ''),
                    'last_logon': self._parse_datetime(account.get('last_logon')),
                    'logon_count': self.get_int_value(account, 'logon_count', 0),
                    'bad_password_count': self.get_int_value(account, 'bad_password_count', 0),
                    'password_last_set': self._parse_datetime(account.get('password_last_set')),
                    'password_age': self.get_int_value(account, 'password_age', 0),
                    'profile_path': account.get('profile_path', ''),
                    'home_directory': account.get('home_directory', ''),
                    'script_path': account.get('script_path', '')
                }
                
                accounts.append(processed_account)
        
        # Sort by name
        accounts.sort(key=lambda x: x['name'].lower())
        
        return accounts
    
    def _process_local_groups(self, management_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process local groups data"""
        groups = []
        groups_list = management_data.get('local_groups', [])
        
        for group in groups_list:
            if isinstance(group, dict):
                processed_group = {
                    'name': group.get('name', 'Unknown'),
                    'description': group.get('description', ''),
                    'sid': group.get('sid', ''),
                    'group_type': group.get('group_type', 'Unknown'),
                    'members': group.get('members', []),
                    'member_count': len(group.get('members', [])),
                    'comment': group.get('comment', '')
                }
                
                groups.append(processed_group)
        
        # Sort by name
        groups.sort(key=lambda x: x['name'].lower())
        
        return groups
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for management data"""
        services = processed_data['services']
        tasks = processed_data['scheduled_tasks']
        policies = processed_data['group_policies']
        accounts = processed_data['user_accounts']
        groups = processed_data['local_groups']
        
        # Calculate summary statistics
        summary = {
            'total_services': len(services),
            'running_services': len([s for s in services if s['status'] == 'Running']),
            'stopped_services': len([s for s in services if s['status'] == 'Stopped']),
            'automatic_services': len([s for s in services if s['start_mode'] == 'Auto']),
            'manual_services': len([s for s in services if s['start_mode'] == 'Manual']),
            'disabled_services': len([s for s in services if s['start_mode'] == 'Disabled']),
            'total_scheduled_tasks': len(tasks),
            'enabled_tasks': len([t for t in tasks if t['enabled']]),
            'disabled_tasks': len([t for t in tasks if not t['enabled']]),
            'running_tasks': len([t for t in tasks if t['state'] == 'Running']),
            'total_group_policies': len(policies),
            'enabled_policies': len([p for p in policies if p['enabled']]),
            'total_user_accounts': len(accounts),
            'enabled_accounts': len([a for a in accounts if not a['disabled']]),
            'disabled_accounts': len([a for a in accounts if a['disabled']]),
            'locked_accounts': len([a for a in accounts if a['locked_out']]),
            'local_accounts': len([a for a in accounts if a['local_account']]),
            'domain_accounts': len([a for a in accounts if not a['local_account']]),
            'total_local_groups': len(groups),
            'service_status_breakdown': self._get_service_status_breakdown(services),
            'task_state_breakdown': self._get_task_state_breakdown(tasks),
            'account_type_breakdown': self._get_account_type_breakdown(accounts)
        }
        
        return summary
    
    def _get_service_status_breakdown(self, services: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of services by status"""
        status_counts = {}
        for service in services:
            status = service.get('status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _get_task_state_breakdown(self, tasks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of tasks by state"""
        state_counts = {}
        for task in tasks:
            state = task.get('state', 'Unknown')
            state_counts[state] = state_counts.get(state, 0) + 1
        return state_counts
    
    def _get_account_type_breakdown(self, accounts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of accounts by type"""
        type_counts = {}
        for account in accounts:
            account_type = account.get('account_type', 'Unknown')
            type_counts[account_type] = type_counts.get(account_type, 0) + 1
        return type_counts
    
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
