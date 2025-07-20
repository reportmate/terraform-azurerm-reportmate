"""
ReportMate API Module Processors
Comprehensive data processing modules for device telemetry
"""

from .applications import ApplicationsProcessor
from .displays import DisplaysProcessor
from .hardware import HardwareProcessor
from .installs import InstallsProcessor
from .inventory import InventoryProcessor
from .management import ManagementProcessor
from .network import NetworkProcessor
from .printers import PrintersProcessor
from .profiles import ProfilesProcessor
from .security import SecurityProcessor
from .system import SystemProcessor

__all__ = [
    'ApplicationsProcessor',
    'DisplaysProcessor',
    'HardwareProcessor', 
    'InstallsProcessor',
    'InventoryProcessor',
    'ManagementProcessor',
    'NetworkProcessor',
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
