"""
Shared utilities for ReportMate API
"""

from datetime import datetime, timezone, timedelta


def calculate_device_status(last_seen):
    """
    Calculate device status based on last seen timestamp
    Returns: 'active', 'stale', 'warning', or 'error'
    
    This is the centralized status calculation logic used across all API endpoints.
    
    Status Definitions:
    - active: Device reported within last 4 hours
    - warning: Device reported within last 24 hours but more than 4 hours ago  
    - stale: Device reported within last week but more than 24 hours ago
    - error: Device hasn't reported in over a week or has invalid timestamp
    """
    if not last_seen:
        return 'error'  # No last seen time at all
    
    now = datetime.now(timezone.utc)
    
    # Convert string timestamp to datetime if needed
    if isinstance(last_seen, str):
        try:
            # Handle various timestamp formats
            if last_seen.endswith('Z'):
                last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            elif '+' in last_seen or last_seen.endswith('UTC'):
                last_seen = datetime.fromisoformat(last_seen.replace('UTC', '').strip())
            else:
                last_seen = datetime.fromisoformat(last_seen)
        except ValueError:
            return 'error'  # Invalid timestamp format
    
    # Ensure last_seen is timezone-aware
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    
    time_diff = now - last_seen
    
    # Define status thresholds
    if time_diff <= timedelta(hours=4):
        return 'active'    # Reported within last 4 hours
    elif time_diff <= timedelta(hours=24):
        return 'warning'   # Reported within last 24 hours but more than 4 hours ago
    elif time_diff <= timedelta(days=7):
        return 'stale'     # Reported within last week but more than 24 hours ago
    else:
        return 'error'     # Haven't seen in over a week


def get_device_status_from_modules(device_data):
    """
    Extract the most recent timestamp from device modules and calculate status
    
    Args:
        device_data: Device data dict with 'modules' containing module data
        
    Returns:
        Calculated device status string
    """
    if not device_data or 'modules' not in device_data:
        return 'error'
    
    latest_timestamp = None
    modules = device_data.get('modules', {})
    
    # Check each module for collectedAt timestamp
    for module_name, module_data in modules.items():
        if isinstance(module_data, dict) and 'collectedAt' in module_data:
            try:
                module_timestamp = module_data['collectedAt']
                if isinstance(module_timestamp, str):
                    module_timestamp = datetime.fromisoformat(module_timestamp.replace('Z', '+00:00'))
                
                if latest_timestamp is None or module_timestamp > latest_timestamp:
                    latest_timestamp = module_timestamp
            except (ValueError, TypeError):
                continue  # Skip invalid timestamps
    
    # Fallback to device-level last_seen if available
    if latest_timestamp is None and 'last_seen' in device_data:
        try:
            latest_timestamp = device_data['last_seen']
            if isinstance(latest_timestamp, str):
                latest_timestamp = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
    
    if latest_timestamp is None:
        return 'error'
    
    return calculate_device_status(latest_timestamp)
