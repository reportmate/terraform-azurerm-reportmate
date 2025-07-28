"""
Shared utility functions for ReportMate API
"""
from datetime import datetime, timezone, timedelta

def calculate_device_status(last_seen, recent_events=None):
    """
    Calculate device status based on last seen timestamp and recent events
    
    NEW LOGIC per user requirements:
    - active: < 24 hours 
    - stale: 24 hours - 7 days
    - missing: 7+ days
    - warning/error: Come strictly from events data (installs module errors)
    
    Args:
        last_seen: datetime object or None (collectedAt timestamp)
        recent_events: list of recent events with 'event_type' field (optional)
        
    Returns:
        str: One of 'active', 'stale', 'missing', 'warning', 'error'
    """
    # First check for event-based status (overrides time-based status)
    if recent_events:
        # Check for error events first (highest priority)
        if any(event.get('event_type') == 'error' for event in recent_events):
            return 'error'
        # Check for warning events
        if any(event.get('event_type') == 'warning' for event in recent_events):
            return 'warning'
    
    # If no events or no error/warning events, calculate time-based status
    if not last_seen:
        return 'missing'
    
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    
    time_diff = now - last_seen
    
    # Updated time-based status thresholds per user requirements
    if time_diff <= timedelta(hours=24):
        return 'active'    # < 24 hours
    elif time_diff <= timedelta(days=7):
        return 'stale'     # 24 hours - 7 days
    else:
        return 'missing'   # 7+ days
