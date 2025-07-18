"""
Network Module Processor for ReportMate
Handles network configuration, interfaces, and connectivity data
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..shared.base_processor import BaseModuleProcessor
import json

logger = logging.getLogger(__name__)

class NetworkProcessor(BaseModuleProcessor):
    """
    Processor for network module data
    Handles network adapters, IP configuration, routes, and connectivity
    """
    
    @property
    def module_id(self) -> str:
        return "network"
    
    async def process_module_data(self, device_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """
        Process network data from device payload
        
        Args:
            device_data: Raw device data dictionary
            device_id: Unique device identifier
            
        Returns:
            Processed network data
        """
        self.logger.debug(f"Processing network module for device {device_id}")
        
        # Extract network data from the device payload
        network_data = device_data.get('network', {})
        
        # Build processed network data
        processed_data = {
            'module_id': self.module_id,
            'device_id': device_id,
            'collected_at': datetime.utcnow().isoformat(),
            'network_adapters': self._process_network_adapters(network_data),
            'ip_configuration': self._process_ip_configuration(network_data),
            'routing_table': self._process_routing_table(network_data),
            'dns_configuration': self._process_dns_configuration(network_data),
            'network_shares': self._process_network_shares(network_data),
            'wifi_profiles': self._process_wifi_profiles(network_data),
            'firewall_status': self._process_firewall_status(network_data),
            'network_statistics': self._process_network_statistics(network_data),
            'summary': {}
        }
        
        # Generate summary statistics
        processed_data['summary'] = self._generate_summary(processed_data)
        
        self.logger.info(f"Network processed - {len(processed_data['network_adapters'])} adapters, "
                        f"{len(processed_data['wifi_profiles'])} WiFi profiles, "
                        f"{len(processed_data['network_shares'])} shares")
        
        return processed_data
    
    async def validate_module_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate network module data
        
        Args:
            data: Processed network data
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['module_id', 'device_id', 'network_adapters']
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Network validation failed - missing {field}")
                return False
        
        if data['module_id'] != self.module_id:
            self.logger.warning(f"Network validation failed - incorrect module_id: {data['module_id']}")
            return False
        
        return True
    
    def _process_network_adapters(self, network_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process network adapters data"""
        adapters = []
        adapters_list = network_data.get('network_adapters', [])
        
        for adapter in adapters_list:
            if isinstance(adapter, dict):
                processed_adapter = {
                    'name': adapter.get('name', 'Unknown'),
                    'description': adapter.get('description', ''),
                    'mac_address': adapter.get('mac_address', ''),
                    'manufacturer': adapter.get('manufacturer', ''),
                    'adapter_type': adapter.get('adapter_type', 'Unknown'),
                    'interface_type': adapter.get('interface_type', 'Unknown'),
                    'connection_status': adapter.get('connection_status', 'Unknown'),
                    'operational_status': adapter.get('operational_status', 'Unknown'),
                    'admin_status': adapter.get('admin_status', 'Unknown'),
                    'speed': self.get_long_value(adapter, 'speed', 0),
                    'duplex': adapter.get('duplex', 'Unknown'),
                    'mtu': self.get_int_value(adapter, 'mtu', 0),
                    'dhcp_enabled': self.get_bool_value(adapter, 'dhcp_enabled', False),
                    'ip_addresses': adapter.get('ip_addresses', []),
                    'subnet_masks': adapter.get('subnet_masks', []),
                    'default_gateways': adapter.get('default_gateways', []),
                    'dns_servers': adapter.get('dns_servers', []),
                    'dhcp_server': adapter.get('dhcp_server', ''),
                    'dhcp_lease_obtained': self._parse_datetime(adapter.get('dhcp_lease_obtained')),
                    'dhcp_lease_expires': self._parse_datetime(adapter.get('dhcp_lease_expires')),
                    'wins_servers': adapter.get('wins_servers', []),
                    'net_connection_id': adapter.get('net_connection_id', ''),
                    'net_connection_status': adapter.get('net_connection_status', 'Unknown'),
                    'pnp_device_id': adapter.get('pnp_device_id', ''),
                    'service_name': adapter.get('service_name', ''),
                    'guid': adapter.get('guid', ''),
                    'interface_index': self.get_int_value(adapter, 'interface_index', 0),
                    'is_virtual': self.get_bool_value(adapter, 'is_virtual', False),
                    'is_physical': self.get_bool_value(adapter, 'is_physical', True)
                }
                
                adapters.append(processed_adapter)
        
        # Sort by interface index
        adapters.sort(key=lambda x: x['interface_index'])
        
        return adapters
    
    def _process_ip_configuration(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process IP configuration data"""
        ip_config = network_data.get('ip_configuration', {})
        
        return {
            'hostname': ip_config.get('hostname', ''),
            'domain': ip_config.get('domain', ''),
            'primary_dns_suffix': ip_config.get('primary_dns_suffix', ''),
            'node_type': ip_config.get('node_type', 'Unknown'),
            'ip_routing_enabled': self.get_bool_value(ip_config, 'ip_routing_enabled', False),
            'wins_proxy_enabled': self.get_bool_value(ip_config, 'wins_proxy_enabled', False),
            'dns_suffix_search_list': ip_config.get('dns_suffix_search_list', []),
            'dhcp_scope_id': ip_config.get('dhcp_scope_id', ''),
            'autoconfiguration_enabled': self.get_bool_value(ip_config, 'autoconfiguration_enabled', True),
            'tcp_window_size': self.get_int_value(ip_config, 'tcp_window_size', 0),
            'interfaces': self._process_ip_interfaces(ip_config.get('interfaces', []))
        }
    
    def _process_ip_interfaces(self, interfaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process IP interface details"""
        processed_interfaces = []
        
        for interface in interfaces:
            if isinstance(interface, dict):
                processed_interface = {
                    'interface_index': self.get_int_value(interface, 'interface_index', 0),
                    'name': interface.get('name', ''),
                    'alias': interface.get('alias', ''),
                    'description': interface.get('description', ''),
                    'ip_addresses': interface.get('ip_addresses', []),
                    'subnet_masks': interface.get('subnet_masks', []),
                    'prefix_lengths': interface.get('prefix_lengths', []),
                    'default_gateways': interface.get('default_gateways', []),
                    'dns_servers': interface.get('dns_servers', []),
                    'metric': self.get_int_value(interface, 'metric', 0),
                    'mtu': self.get_int_value(interface, 'mtu', 0),
                    'forwarding_enabled': self.get_bool_value(interface, 'forwarding_enabled', False),
                    'advertising_enabled': self.get_bool_value(interface, 'advertising_enabled', False),
                    'dhcp_enabled': self.get_bool_value(interface, 'dhcp_enabled', False)
                }
                processed_interfaces.append(processed_interface)
        
        return processed_interfaces
    
    def _process_routing_table(self, network_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process routing table data"""
        routes = []
        routes_list = network_data.get('routing_table', [])
        
        for route in routes_list:
            if isinstance(route, dict):
                processed_route = {
                    'destination': route.get('destination', ''),
                    'netmask': route.get('netmask', ''),
                    'gateway': route.get('gateway', ''),
                    'interface': route.get('interface', ''),
                    'metric': self.get_int_value(route, 'metric', 0),
                    'protocol': route.get('protocol', 'Unknown'),
                    'type': route.get('type', 'Unknown'),
                    'age': self.get_int_value(route, 'age', 0),
                    'next_hop': route.get('next_hop', ''),
                    'interface_index': self.get_int_value(route, 'interface_index', 0),
                    'persistent': self.get_bool_value(route, 'persistent', False)
                }
                
                routes.append(processed_route)
        
        # Sort by destination
        routes.sort(key=lambda x: x['destination'])
        
        return routes
    
    def _process_dns_configuration(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process DNS configuration data"""
        dns_config = network_data.get('dns_configuration', {})
        
        return {
            'domain_name': dns_config.get('domain_name', ''),
            'hostname': dns_config.get('hostname', ''),
            'primary_dns_suffix': dns_config.get('primary_dns_suffix', ''),
            'dns_servers': dns_config.get('dns_servers', []),
            'search_order': dns_config.get('search_order', []),
            'dns_suffix_search_list': dns_config.get('dns_suffix_search_list', []),
            'devolution_level': self.get_int_value(dns_config, 'devolution_level', 0),
            'append_to_multi_label_name': self.get_bool_value(dns_config, 'append_to_multi_label_name', False),
            'append_primary_suffixes': self.get_bool_value(dns_config, 'append_primary_suffixes', False),
            'append_parent_suffixes': self.get_bool_value(dns_config, 'append_parent_suffixes', False),
            'ndots': self.get_int_value(dns_config, 'ndots', 1),
            'timeout': self.get_int_value(dns_config, 'timeout', 0),
            'attempts': self.get_int_value(dns_config, 'attempts', 0)
        }
    
    def _process_network_shares(self, network_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process network shares data"""
        shares = []
        shares_list = network_data.get('network_shares', [])
        
        for share in shares_list:
            if isinstance(share, dict):
                processed_share = {
                    'name': share.get('name', 'Unknown'),
                    'path': share.get('path', ''),
                    'description': share.get('description', ''),
                    'type': share.get('type', 'Unknown'),
                    'current_uses': self.get_int_value(share, 'current_uses', 0),
                    'maximum_allowed': self.get_int_value(share, 'maximum_allowed', 0),
                    'allow_maximum': self.get_bool_value(share, 'allow_maximum', False),
                    'caption': share.get('caption', ''),
                    'install_date': self._parse_datetime(share.get('install_date')),
                    'status': share.get('status', 'Unknown'),
                    'access_mask': self.get_int_value(share, 'access_mask', 0),
                    'security_descriptor': share.get('security_descriptor', '')
                }
                
                shares.append(processed_share)
        
        # Sort by name
        shares.sort(key=lambda x: x['name'].lower())
        
        return shares
    
    def _process_wifi_profiles(self, network_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process WiFi profiles data"""
        profiles = []
        profiles_list = network_data.get('wifi_profiles', [])
        
        for profile in profiles_list:
            if isinstance(profile, dict):
                processed_profile = {
                    'name': profile.get('name', 'Unknown'),
                    'ssid': profile.get('ssid', ''),
                    'authentication': profile.get('authentication', 'Unknown'),
                    'encryption': profile.get('encryption', 'Unknown'),
                    'connection_type': profile.get('connection_type', 'Unknown'),
                    'connection_mode': profile.get('connection_mode', 'Unknown'),
                    'auto_connect': self.get_bool_value(profile, 'auto_connect', False),
                    'non_broadcast': self.get_bool_value(profile, 'non_broadcast', False),
                    'signal_strength': self.get_int_value(profile, 'signal_strength', 0),
                    'radio_type': profile.get('radio_type', 'Unknown'),
                    'channel': self.get_int_value(profile, 'channel', 0),
                    'basic_rates': profile.get('basic_rates', []),
                    'other_rates': profile.get('other_rates', []),
                    'mac_randomization': self.get_bool_value(profile, 'mac_randomization', False),
                    'cost': profile.get('cost', 'Unknown'),
                    'approachingDataLimit': self.get_bool_value(profile, 'approaching_data_limit', False),
                    'overDataLimit': self.get_bool_value(profile, 'over_data_limit', False),
                    'roaming': self.get_bool_value(profile, 'roaming', False)
                }
                
                profiles.append(processed_profile)
        
        # Sort by name
        profiles.sort(key=lambda x: x['name'].lower())
        
        return profiles
    
    def _process_firewall_status(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process firewall status data"""
        firewall_data = network_data.get('firewall_status', {})
        
        return {
            'domain_profile': self._process_firewall_profile(firewall_data.get('domain_profile', {})),
            'private_profile': self._process_firewall_profile(firewall_data.get('private_profile', {})),
            'public_profile': self._process_firewall_profile(firewall_data.get('public_profile', {})),
            'current_profile': firewall_data.get('current_profile', 'Unknown'),
            'firewall_enabled': self.get_bool_value(firewall_data, 'firewall_enabled', False),
            'rules_count': self.get_int_value(firewall_data, 'rules_count', 0),
            'active_rules_count': self.get_int_value(firewall_data, 'active_rules_count', 0)
        }
    
    def _process_firewall_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual firewall profile"""
        return {
            'enabled': self.get_bool_value(profile_data, 'enabled', False),
            'default_inbound_action': profile_data.get('default_inbound_action', 'Unknown'),
            'default_outbound_action': profile_data.get('default_outbound_action', 'Unknown'),
            'allow_inbound_rules': self.get_bool_value(profile_data, 'allow_inbound_rules', False),
            'allow_local_firewall_rules': self.get_bool_value(profile_data, 'allow_local_firewall_rules', False),
            'allow_local_ipsec_rules': self.get_bool_value(profile_data, 'allow_local_ipsec_rules', False),
            'allow_user_apps': self.get_bool_value(profile_data, 'allow_user_apps', False),
            'allow_user_ports': self.get_bool_value(profile_data, 'allow_user_ports', False),
            'allow_unicast_response': self.get_bool_value(profile_data, 'allow_unicast_response', False),
            'notify_on_listen': self.get_bool_value(profile_data, 'notify_on_listen', False),
            'enable_stealth_mode': self.get_bool_value(profile_data, 'enable_stealth_mode', False),
            'log_file_name': profile_data.get('log_file_name', ''),
            'log_max_size': self.get_long_value(profile_data, 'log_max_size', 0),
            'log_allowed': self.get_bool_value(profile_data, 'log_allowed', False),
            'log_blocked': self.get_bool_value(profile_data, 'log_blocked', False),
            'log_ignored': self.get_bool_value(profile_data, 'log_ignored', False)
        }
    
    def _process_network_statistics(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process network statistics data"""
        stats_data = network_data.get('network_statistics', {})
        
        return {
            'bytes_received': self.get_long_value(stats_data, 'bytes_received', 0),
            'bytes_sent': self.get_long_value(stats_data, 'bytes_sent', 0),
            'packets_received': self.get_long_value(stats_data, 'packets_received', 0),
            'packets_sent': self.get_long_value(stats_data, 'packets_sent', 0),
            'packets_received_discarded': self.get_long_value(stats_data, 'packets_received_discarded', 0),
            'packets_received_errors': self.get_long_value(stats_data, 'packets_received_errors', 0),
            'packets_outbound_discarded': self.get_long_value(stats_data, 'packets_outbound_discarded', 0),
            'packets_outbound_errors': self.get_long_value(stats_data, 'packets_outbound_errors', 0),
            'output_queue_length': self.get_long_value(stats_data, 'output_queue_length', 0),
            'speed': self.get_long_value(stats_data, 'speed', 0),
            'interface_statistics': self._process_interface_statistics(stats_data.get('interface_statistics', []))
        }
    
    def _process_interface_statistics(self, interface_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process per-interface statistics"""
        processed_stats = []
        
        for stats in interface_stats:
            if isinstance(stats, dict):
                processed_stat = {
                    'interface_index': self.get_int_value(stats, 'interface_index', 0),
                    'interface_description': stats.get('interface_description', ''),
                    'bytes_received': self.get_long_value(stats, 'bytes_received', 0),
                    'bytes_sent': self.get_long_value(stats, 'bytes_sent', 0),
                    'packets_received': self.get_long_value(stats, 'packets_received', 0),
                    'packets_sent': self.get_long_value(stats, 'packets_sent', 0),
                    'errors_received': self.get_long_value(stats, 'errors_received', 0),
                    'errors_sent': self.get_long_value(stats, 'errors_sent', 0),
                    'discards_received': self.get_long_value(stats, 'discards_received', 0),
                    'discards_sent': self.get_long_value(stats, 'discards_sent', 0)
                }
                processed_stats.append(processed_stat)
        
        return processed_stats
    
    def _generate_summary(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for network data"""
        adapters = processed_data['network_adapters']
        wifi_profiles = processed_data['wifi_profiles']
        shares = processed_data['network_shares']
        firewall = processed_data['firewall_status']
        
        # Calculate summary statistics
        summary = {
            'total_adapters': len(adapters),
            'physical_adapters': len([a for a in adapters if a['is_physical']]),
            'virtual_adapters': len([a for a in adapters if a['is_virtual']]),
            'connected_adapters': len([a for a in adapters if a['connection_status'] == 'Connected']),
            'dhcp_enabled_adapters': len([a for a in adapters if a['dhcp_enabled']]),
            'total_wifi_profiles': len(wifi_profiles),
            'auto_connect_profiles': len([p for p in wifi_profiles if p['auto_connect']]),
            'total_shares': len(shares),
            'active_shares': len([s for s in shares if s['current_uses'] > 0]),
            'firewall_enabled': firewall.get('firewall_enabled', False),
            'current_firewall_profile': firewall.get('current_profile', 'Unknown'),
            'adapter_types': self._get_adapter_type_breakdown(adapters),
            'connection_status': self._get_connection_status_breakdown(adapters),
            'ip_address_count': self._get_total_ip_addresses(adapters),
            'dns_servers': self._get_unique_dns_servers(adapters),
            'default_gateways': self._get_unique_gateways(adapters)
        }
        
        return summary
    
    def _get_adapter_type_breakdown(self, adapters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of adapters by type"""
        types = {}
        for adapter in adapters:
            adapter_type = adapter.get('adapter_type', 'Unknown')
            types[adapter_type] = types.get(adapter_type, 0) + 1
        return types
    
    def _get_connection_status_breakdown(self, adapters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of adapters by connection status"""
        statuses = {}
        for adapter in adapters:
            status = adapter.get('connection_status', 'Unknown')
            statuses[status] = statuses.get(status, 0) + 1
        return statuses
    
    def _get_total_ip_addresses(self, adapters: List[Dict[str, Any]]) -> int:
        """Get total number of IP addresses across all adapters"""
        total = 0
        for adapter in adapters:
            ip_addresses = adapter.get('ip_addresses', [])
            if isinstance(ip_addresses, list):
                total += len(ip_addresses)
        return total
    
    def _get_unique_dns_servers(self, adapters: List[Dict[str, Any]]) -> List[str]:
        """Get unique DNS servers across all adapters"""
        dns_servers = set()
        for adapter in adapters:
            servers = adapter.get('dns_servers', [])
            if isinstance(servers, list):
                dns_servers.update(servers)
        return sorted(list(dns_servers))
    
    def _get_unique_gateways(self, adapters: List[Dict[str, Any]]) -> List[str]:
        """Get unique default gateways across all adapters"""
        gateways = set()
        for adapter in adapters:
            gateway_list = adapter.get('default_gateways', [])
            if isinstance(gateway_list, list):
                gateways.update(gateway_list)
        return sorted(list(gateways))
    
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
