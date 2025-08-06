"""
Field Mapping Utilities for ReportMate
Handles conversion between client PascalCase and database snake_case field names
"""

from typing import Dict, Any, List, Union

def map_client_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert PascalCase client fields to snake_case database fields
    Handle both direct mapping and nested object mapping
    
    Args:
        data: Raw client data with PascalCase field names
        
    Returns:
        Mapped data with snake_case field names
    """
    if not isinstance(data, dict):
        return data
        
    mapped_data = {}
    
    # Field mapping dictionary - client PascalCase to database snake_case
    field_mapping = {
        # Processor fields
        'baseSpeed': 'base_speed',
        'maxSpeed': 'max_speed',
        'logicalProcessors': 'logical_processors',
        'cacheL1': 'cache_l1',
        'cacheL2': 'cache_l2',
        'cacheL3': 'cache_l3',
        
        # Memory fields
        'totalPhysical': 'total_physical',
        'availablePhysical': 'available_physical',
        'totalVirtual': 'total_virtual',
        'availableVirtual': 'available_virtual',
        
        # Storage fields
        'freeSpace': 'free_space',
        'totalSpace': 'total_space',
        'fileSystem': 'file_system',
        'driveType': 'drive_type',
        
        # Graphics fields
        'memorySize': 'memory_size',
        'driverVersion': 'driver_version',
        'driverDate': 'driver_date',
        'dedicatedMemory': 'dedicated_memory',
        'sharedMemory': 'shared_memory',
        
        # Battery fields
        'chargePercent': 'charge_percent',
        'isCharging': 'is_charging',
        'estimatedRuntime': 'estimated_runtime',
        'cycleCount': 'cycle_count',
        'designCapacity': 'design_capacity',
        'fullChargeCapacity': 'full_charge_capacity',
        
        # NPU fields
        'computeUnits': 'compute_units',
        'isAvailable': 'is_available',
        'driverVersion': 'driver_version',
        
        # Network fields
        'macAddress': 'mac_address',
        'ipAddress': 'ip_address',
        'subnetMask': 'subnet_mask',
        'defaultGateway': 'default_gateway',
        'dnsServers': 'dns_servers',
        'dhcpEnabled': 'dhcp_enabled',
        'connectionState': 'connection_state',
        'networkType': 'network_type',
        'linkSpeed': 'link_speed',
        
        # Display fields
        'screenWidth': 'screen_width',
        'screenHeight': 'screen_height',
        'colorDepth': 'color_depth',
        'refreshRate': 'refresh_rate',
        'isPrimary': 'is_primary',
        
        # System fields
        'osVersion': 'os_version',
        'buildNumber': 'build_number',
        'installDate': 'install_date',
        'lastBootTime': 'last_boot_time',
        'timeZone': 'time_zone',
        'domainWorkgroup': 'domain_workgroup',
        
        # Inventory fields
        'deviceName': 'device_name',
        'serialNumber': 'serial_number',
        'assetTag': 'asset_tag',
        'purchaseDate': 'purchase_date',
        'warrantyExpiration': 'warranty_expiration',
        
        # Applications fields
        'installDate': 'install_date',
        'installLocation': 'install_location',
        'uninstallString': 'uninstall_string',
        'displayVersion': 'display_version',
        'estimatedSize': 'estimated_size',
        
        # Installs fields
        'isInstalled': 'is_installed',
        'currentStatus': 'current_status',
        'latestVersion': 'latest_version',
        'pendingPackages': 'pending_packages',
        'recentInstalls': 'recent_installs',
        'recentSessions': 'recent_sessions',
        'recentEvents': 'recent_events',
        'cacheStatus': 'cache_status',
        'windowsUpdates': 'windows_updates',
        'installedPatches': 'installed_patches',
        'pendingUpdates': 'pending_updates',
        'packageManagers': 'package_managers',
        'updateSettings': 'update_settings',
        'updateHistory': 'update_history',
        
        # Management fields
        'scheduledTasks': 'scheduled_tasks',
        'groupPolicies': 'group_policies',
        'registrySettings': 'registry_settings',
        'environmentVariables': 'environment_variables',
        'systemConfiguration': 'system_configuration',
        'userAccounts': 'user_accounts',
        'localGroups': 'local_groups',
        
        # Security fields
        'antivirusProducts': 'antivirus_products',
        'firewallStatus': 'firewall_status',
        'windowsDefender': 'windows_defender',
        'bitlockerStatus': 'bitlocker_status',
        'userAccountControl': 'user_account_control',
        'securityPolicies': 'security_policies',
        'certificateStore': 'certificate_store',
        'encryptionStatus': 'encryption_status',
        
        # Common timestamp fields
        'createdAt': 'created_at',
        'updatedAt': 'updated_at',
        'collectedAt': 'collected_at',
        'lastModified': 'last_modified',
        'lastAccessed': 'last_accessed',
        'lastSeen': 'last_seen',
        
        # Module identification
        'moduleId': 'module_id',
        'deviceId': 'device_id'
    }
    
    for key, value in data.items():
        # Check if this key needs mapping
        mapped_key = field_mapping.get(key, key)
        
        # Recursively process nested dictionaries
        if isinstance(value, dict):
            mapped_data[mapped_key] = map_client_fields(value)
        # Process lists of dictionaries
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            mapped_data[mapped_key] = [map_client_fields(item) for item in value]
        else:
            mapped_data[mapped_key] = value
    
    return mapped_data

def get_value_with_fallback(data: Dict[str, Any], primary_key: str, fallback_keys: List[str] = None, default: Any = None) -> Any:
    """
    Get value from data with fallback to alternative key names
    Supports both snake_case and PascalCase lookups
    
    Args:
        data: Data dictionary to search
        primary_key: Primary key to look for
        fallback_keys: List of alternative keys to try
        default: Default value if no keys found
        
    Returns:
        Found value or default
    """
    if not isinstance(data, dict):
        return default
        
    # Try primary key first
    if primary_key in data:
        return data[primary_key]
    
    # Try fallback keys
    if fallback_keys:
        for key in fallback_keys:
            if key in data:
                return data[key]
    
    # Try common variations based on naming conventions
    variations = generate_key_variations(primary_key)
    for variation in variations:
        if variation in data:
            return data[variation]
    
    return default

def generate_key_variations(key: str) -> List[str]:
    """
    Generate common variations of a key name
    
    Args:
        key: Original key name
        
    Returns:
        List of possible key variations
    """
    variations = []
    
    # If it's snake_case, try PascalCase
    if '_' in key:
        pascal_case = ''.join(word.capitalize() for word in key.split('_'))
        camel_case = pascal_case[0].lower() + pascal_case[1:] if pascal_case else ''
        variations.extend([pascal_case, camel_case])
    
    # If it's PascalCase or camelCase, try snake_case
    elif any(c.isupper() for c in key):
        snake_case = ''.join(['_' + c.lower() if c.isupper() and i > 0 else c.lower() 
                             for i, c in enumerate(key)])
        variations.append(snake_case)
    
    return variations

def safe_get_int(data: Dict[str, Any], key: str, default: int = 0, fallback_keys: List[str] = None) -> int:
    """Safely get integer value with fallback key support"""
    value = get_value_with_fallback(data, key, fallback_keys, default)
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_get_float(data: Dict[str, Any], key: str, default: float = 0.0, fallback_keys: List[str] = None) -> float:
    """Safely get float value with fallback key support"""
    value = get_value_with_fallback(data, key, fallback_keys, default)
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_get_long(data: Dict[str, Any], key: str, default: int = 0, fallback_keys: List[str] = None) -> int:
    """Safely get long/large integer value with fallback key support"""
    value = get_value_with_fallback(data, key, fallback_keys, default)
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_get_bool(data: Dict[str, Any], key: str, default: bool = False, fallback_keys: List[str] = None) -> bool:
    """Safely get boolean value with fallback key support"""
    value = get_value_with_fallback(data, key, fallback_keys, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    if isinstance(value, (int, float)):
        return value != 0
    return default

def safe_get_string(data: Dict[str, Any], key: str, default: str = '', fallback_keys: List[str] = None) -> str:
    """Safely get string value with fallback key support"""
    value = get_value_with_fallback(data, key, fallback_keys, default)
    return str(value) if value is not None else default
