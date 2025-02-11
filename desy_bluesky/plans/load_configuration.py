import yaml
from typing import Dict, Any

from bluesky.plan_stubs import abs_set, wait
from ophyd_async.core import DEFAULT_TIMEOUT

def load_configuration(config: Dict[str, Any] | str,
                       devices: Dict[str, Any],
                       timeout: float | None = DEFAULT_TIMEOUT):
    """
    Load configuration into devices. Only devices in the devices dictionary passed to the plan. Pass the namespace 
    containing your devices to allow all devices to be loaded with configuration.

    Parameters
    ----------
    config : Dict[str, Any] | str
        Configuration to load into devices. Can be a dictionary or a string path to a yaml file.
    devices : Dict[str, Any]
        Dictionary of devices to load configuration into.        
    timeout : float, optional
        Timeout for waiting for devices to finish setting, by default DEFAULT_TIMEOUT.

    """
    
    configuration = {}
    
    if isinstance(config, dict):
        configuration = config
    elif isinstance(config, str):
        with open(config, 'r') as f:
            try:
                configuration = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Error loading configuration file {config}. {e}")
    else:
        raise ValueError(f"config must be a dictionary or a string path to a yaml file.")
    
    groups_to_await = set()
    for device_name, device_configuration in configuration.items():
        try:
            device = devices[device_name]
        except KeyError:
            raise ValueError(f"Device {device_name} not found in devices dictionary passed to plan.")
        
        for field_name, field_value in device_configuration.items():
            try:
                field = getattr(device, field_name)
            except AttributeError:
                raise ValueError(f"Field {field_name} not found in device {device_name}.")
            yield from abs_set(field, field_value, group=device_name)
            groups_to_await.add(device_name)
    
    for group in groups_to_await:
        try:
            yield from wait(group=group, timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"Timeout waiting for group {group}.")
