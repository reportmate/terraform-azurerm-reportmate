"""
GET /api/v1/devices/{id}/printers - Device Printers Module
Retrieves comprehensive printer information for a specific device
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/v1/devices/{id}/printer
    Retrieve printer information and configuration for a specific device
    """
    
    logger.info("=== DEVICE PRINTER REQUEST ===")
    
    try:
        # Extract device ID from route
        device_id = req.route_params.get('id')
        if not device_id:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device ID required',
                    'details': 'Device ID must be provided in the URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Fetching printer information for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Initialize authentication manager for request validation
        auth_manager = AuthenticationManager()
        
        # Validate the request (optional API key check)
        auth_result = await auth_manager.validate_request(req)
        if not auth_result['valid']:
            logger.warning(f"Authentication failed for device {device_id}: {auth_result.get('error')}")
        
        # Fetch comprehensive printer data for the device
        printer_data = await fetch_device_printer_data(db_manager, device_id)
        
        if not printer_data:
            logger.warning(f"No printer data found for device: {device_id}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device not found',
                    'details': f'No printer information available for device {device_id}',
                    'device_id': device_id
                }),
                status_code=404,
                mimetype="application/json"
            )
        
        logger.info(f"Successfully retrieved printer data for device {device_id}: "
                   f"{len(printer_data.get('printers', []))} printers, "
                   f"{len(printer_data.get('print_jobs', []))} recent jobs")
        
        # Return comprehensive printer information
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'device_id': device_id,
                'printer_data': printer_data,
                'retrieved_at': datetime.utcnow().isoformat() + 'Z'
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_message = f"Failed to retrieve printer data for device {device_id}: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': error_message,
                'device_id': device_id if 'device_id' in locals() else None
            }),
            status_code=500,
            mimetype="application/json"
        )

async def fetch_device_printer_data(db_manager: DatabaseManager, device_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive printer data for a device from multiple tables
    """
    
    try:
        # Main device printer information
        printers_query = """
        SELECT 
            name,
            share_name,
            port_name,
            driver_name,
            location,
            comment,
            status,
            printer_status,
            is_shared,
            is_network,
            is_default,
            is_online,
            server_name,
            manufacturer,
            model,
            device_type,
            connection_type,
            ip_address,
            priority,
            enable_bidirectional,
            keep_printed_jobs,
            enable_dev_query,
            install_date,
            properties,
            last_updated
        FROM device_printers 
        WHERE device_id = ?
        ORDER BY name
        """
        
        printers = await db_manager.fetch_all(printers_query, (device_id,))
        
        # Print drivers information
        drivers_query = """
        SELECT 
            name,
            version,
            environment,
            config_file,
            data_file,
            driver_path,
            help_file,
            monitor_name,
            default_data_type,
            provider,
            driver_version,
            driver_date,
            is_signed,
            dependent_files,
            last_updated
        FROM device_print_drivers
        WHERE device_id = ?
        ORDER BY name
        """
        
        print_drivers = await db_manager.fetch_all(drivers_query, (device_id,))
        
        # Print ports information
        ports_query = """
        SELECT 
            name,
            port_type,
            description,
            is_network,
            is_local,
            timeout_seconds,
            transmission_retry,
            print_monitor,
            configuration,
            last_updated
        FROM device_print_ports
        WHERE device_id = ?
        ORDER BY name
        """
        
        print_ports = await db_manager.fetch_all(ports_query, (device_id,))
        
        # Print processors information
        processors_query = """
        SELECT 
            name,
            environment,
            dll_name,
            supported_datatypes,
            last_updated
        FROM device_print_processors
        WHERE device_id = ?
        ORDER BY name
        """
        
        print_processors = await db_manager.fetch_all(processors_query, (device_id,))
        
        # Recent print jobs (last 7 days)
        jobs_query = """
        SELECT 
            printer_name,
            job_id,
            document_name,
            user_name,
            status,
            submitted_time,
            total_pages,
            pages_printed,
            size_bytes,
            priority,
            start_time,
            until_time,
            last_updated
        FROM device_print_jobs
        WHERE device_id = ? AND submitted_time >= datetime('now', '-7 days')
        ORDER BY submitted_time DESC
        LIMIT 100
        """
        
        print_jobs = await db_manager.fetch_all(jobs_query, (device_id,))
        
        # Print spooler information
        spooler_query = """
        SELECT 
            service_status,
            service_start_type,
            default_spool_directory,
            beep_enabled,
            net_popup,
            log_events,
            restart_job_on_pool_error,
            restart_job_on_pool_enabled,
            port_thread_priority,
            scheduler_thread_priority,
            total_jobs,
            last_updated
        FROM device_print_spooler
        WHERE device_id = ?
        """
        
        spooler_info = await db_manager.fetch_one(spooler_query, (device_id,))
        
        # Print policy settings
        policies_query = """
        SELECT 
            disable_web_printing,
            disable_server_thread,
            disable_spooler_open_printers,
            spooler_priority,
            spooler_max_job_schedule,
            enable_logging,
            log_level,
            restrict_driver_installation,
            group_policy_settings,
            last_updated
        FROM device_print_policies
        WHERE device_id = ?
        """
        
        policy_settings = await db_manager.fetch_one(policies_query, (device_id,))
        
        # Compile the comprehensive response
        printer_data = {
            'printers': [dict(row) for row in printers] if printers else [],
            'print_drivers': [dict(row) for row in print_drivers] if print_drivers else [],
            'print_ports': [dict(row) for row in print_ports] if print_ports else [],
            'print_processors': [dict(row) for row in print_processors] if print_processors else [],
            'print_jobs': [dict(row) for row in print_jobs] if print_jobs else [],
            'spooler_info': dict(spooler_info) if spooler_info else {},
            'policy_settings': dict(policy_settings) if policy_settings else {},
            'summary': {
                'total_printers': len(printers) if printers else 0,
                'total_drivers': len(print_drivers) if print_drivers else 0,
                'total_ports': len(print_ports) if print_ports else 0,
                'total_processors': len(print_processors) if print_processors else 0,
                'recent_jobs_count': len(print_jobs) if print_jobs else 0,
                'has_spooler_info': bool(spooler_info),
                'has_policy_settings': bool(policy_settings)
            }
        }
        
        return printer_data
        
    except Exception as e:
        logger.error(f"Database error fetching printer data for device {device_id}: {str(e)}")
        raise
