"""
ReportMate API Module Processors
Comprehensive data processing modules for device telemetry
"""

from processors.applications import ApplicationsProcessor
from processors.displays import DisplaysProcessor
from processors.hardware import HardwareProcessor
from processors.installs import InstallsProcessor
from processors.inventory import InventoryProcessor
from processors.management import ManagementProcessor
from processors.network import NetworkProcessor
from processors.peripherals import PeripheralsProcessor
from processors.printers import PrintersProcessor
from processors.profiles import ProfilesProcessor
from processors.security import SecurityProcessor
from processors.system import SystemProcessor

__all__ = [
    'ApplicationsProcessor',
    'DisplaysProcessor',
    'HardwareProcessor', 
    'InstallsProcessor',
    'InventoryProcessor',
    'ManagementProcessor',
    'NetworkProcessor',
    'PeripheralsProcessor',
    'PrintersProcessor',
    'ProfilesProcessor',
    'SecurityProcessor',
    'SystemProcessor'
]

# Module processor registry for dynamic loading
PROCESSOR_REGISTRY = {
    'applications': ApplicationsProcessor,
    'displays': DisplaysProcessor,
    'hardware': HardwareProcessor,
    'installs': InstallsProcessor,
    'inventory': InventoryProcessor,
    'management': ManagementProcessor,
    'network': NetworkProcessor,
    'peripherals': PeripheralsProcessor,
    'printers': PrintersProcessor,
    'profiles': ProfilesProcessor,
    'security': SecurityProcessor,
    'system': SystemProcessor
}

def get_processor(module_id: str):
    """
    Get processor class for a given module ID
    
    Args:
        module_id: The module identifier
        
    Returns:
        Processor class or None if not found
    """
    return PROCESSOR_REGISTRY.get(module_id)
