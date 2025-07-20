import azure.functions as func
import json
import logging
from typing import Optional, Dict, Any
from ..shared.database import DatabaseManager
from ..shared.auth import AuthenticationManager

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to retrieve device displays information
    
    Endpoint: GET /api/device-displays/{device_id}
    Returns comprehensive display device and configuration data
    """
    logging.info('Display API endpoint triggered')

    try:
        # Authentication
        auth_manager = AuthenticationManager()
        auth_result = await auth_manager.authenticate_request(req)
        
        if not auth_result.is_authenticated:
            return func.HttpResponse(
                json.dumps({"error": "Authentication failed", "details": auth_result.error_message}),
                status_code=401,
                headers={"Content-Type": "application/json"}
            )

        # Extract device_id from route
        device_id = req.route_params.get('device_id')
        
        if not device_id:
            return func.HttpResponse(
                json.dumps({"error": "device_id parameter is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # Get database connection
        db_manager = DatabaseManager()
        
        # Fetch display data
        display_data = await fetch_device_display_data(db_manager, device_id)
        
        if not display_data:
            return func.HttpResponse(
                json.dumps({"error": f"No display data found for device {device_id}"}),
                status_code=404,
                headers={"Content-Type": "application/json"}
            )

        # Return successful response
        response_data = {
            "device_id": device_id,
            "display_data": display_data,
            "timestamp": display_data.get("last_updated"),
            "status": "success"
        }

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )

    except Exception as e:
        logging.error(f"Error in display API endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

async def fetch_device_display_data(db_manager: DatabaseManager, device_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive display data for a specific device
    
    Args:
        db_manager: Database manager instance
        device_id: Device identifier
        
    Returns:
        Dictionary containing all display-related data or None if not found
    """
    try:
        # Display devices information
        displays_query = """
        SELECT 
            name,
            device_key,
            manufacturer,
            model,
            serial_number,
            device_string,
            connection_type,
            is_internal,
            is_external,
            is_primary,
            is_active,
            is_enabled,
            diagonal_size_inches,
            width_mm,
            height_mm,
            aspect_ratio,
            current_width,
            current_height,
            current_refresh_rate,
            current_color_depth,
            current_dpi,
            current_scaling,
            current_orientation,
            max_width,
            max_height,
            min_width,
            min_height,
            max_color_depth,
            supported_resolutions,
            supported_refresh_rates,
            capabilities,
            color_space,
            gamma_value,
            brightness,
            contrast,
            position_x,
            position_y,
            display_index,
            panel_type,
            is_hdr,
            is_wide_gamut,
            is_adaptive_sync,
            is_touch,
            driver_version,
            driver_date,
            firmware_version,
            edid_manufacturer,
            edid_product_code,
            edid_week_of_manufacture,
            edid_year_of_manufacture,
            edid_version,
            status,
            health,
            last_connected,
            usage_hours,
            last_updated
        FROM device_displays
        WHERE device_id = ?
        ORDER BY display_index, is_primary DESC
        """
        
        displays = await db_manager.fetch_all(displays_query, (device_id,))
        
        # Display adapters information
        adapters_query = """
        SELECT 
            name,
            adapter_device_id,
            manufacturer,
            chip_type,
            dac_type,
            memory_size,
            driver_version,
            driver_date,
            bios_version,
            connected_displays,
            supported_modes,
            max_displays,
            is_3d_capable,
            is_hardware_accelerated,
            last_updated
        FROM device_display_adapters
        WHERE device_id = ?
        ORDER BY name
        """
        
        adapters = await db_manager.fetch_all(adapters_query, (device_id,))
        
        # Display configuration
        config_query = """
        SELECT 
            total_displays,
            active_displays,
            primary_display,
            display_mode,
            is_extended_desktop,
            is_mirrored_desktop,
            virtual_desktop_width,
            virtual_desktop_height,
            display_sleep_timeout,
            is_power_saving_enabled,
            is_high_contrast_enabled,
            text_scaling,
            is_magnifier_enabled,
            last_updated
        FROM device_display_config
        WHERE device_id = ?
        """
        
        config = await db_manager.fetch_one(config_query, (device_id,))
        
        # Display layout
        layout_query = """
        SELECT 
            display_name,
            x_position,
            y_position,
            width,
            height,
            is_primary,
            orientation,
            last_updated
        FROM device_display_layout
        WHERE device_id = ?
        ORDER BY is_primary DESC, display_name
        """
        
        layout = await db_manager.fetch_all(layout_query, (device_id,))
        
        # Color profiles
        profiles_query = """
        SELECT 
            name,
            file_path,
            description,
            color_space,
            device_model,
            manufacturer,
            is_default,
            created_date,
            file_size,
            last_updated
        FROM device_color_profiles
        WHERE device_id = ?
        ORDER BY is_default DESC, name
        """
        
        profiles = await db_manager.fetch_all(profiles_query, (device_id,))
        
        # Check if any data exists
        if not displays and not adapters and not config:
            return None
        
        # Process and structure the data
        display_data = {
            "displays": [dict(display) for display in displays] if displays else [],
            "adapters": [dict(adapter) for adapter in adapters] if adapters else [],
            "configuration": dict(config) if config else {},
            "layout": [dict(layout_item) for layout_item in layout] if layout else [],
            "color_profiles": [dict(profile) for profile in profiles] if profiles else [],
            "summary": {
                "total_displays": len(displays) if displays else 0,
                "active_displays": len([d for d in displays if d.get('is_active')]) if displays else 0,
                "primary_display": next((d.get('name') for d in displays if d.get('is_primary')), '') if displays else '',
                "internal_displays": len([d for d in displays if d.get('is_internal')]) if displays else 0,
                "external_displays": len([d for d in displays if d.get('is_external')]) if displays else 0,
                "total_adapters": len(adapters) if adapters else 0,
                "has_hdr_support": any(d.get('is_hdr') for d in displays) if displays else False,
                "has_touch_support": any(d.get('is_touch') for d in displays) if displays else False,
                "max_resolution": get_max_resolution(displays) if displays else "",
                "total_desktop_area": calculate_total_desktop_area(displays) if displays else 0
            }
        }
        
        # Add the most recent last_updated timestamp
        all_timestamps = []
        if displays:
            all_timestamps.extend([d.get('last_updated') for d in displays if d.get('last_updated')])
        if adapters:
            all_timestamps.extend([a.get('last_updated') for a in adapters if a.get('last_updated')])
        if config and config.get('last_updated'):
            all_timestamps.append(config.get('last_updated'))
        
        if all_timestamps:
            display_data["last_updated"] = max(all_timestamps)
        
        return display_data
        
    except Exception as e:
        logging.error(f"Error fetching display data for device {device_id}: {str(e)}")
        raise

def get_max_resolution(displays):
    """Get the maximum resolution across all displays"""
    if not displays:
        return ""
    
    max_width = max((d.get('max_width', 0) or d.get('current_width', 0) for d in displays), default=0)
    max_height = max((d.get('max_height', 0) or d.get('current_height', 0) for d in displays), default=0)
    
    if max_width > 0 and max_height > 0:
        return f"{max_width}x{max_height}"
    return ""

def calculate_total_desktop_area(displays):
    """Calculate total desktop area in pixels"""
    if not displays:
        return 0
    
    total_area = 0
    for display in displays:
        width = display.get('current_width', 0)
        height = display.get('current_height', 0)
        if width > 0 and height > 0:
            total_area += width * height
    
    return total_area
