from ophyd_async.core import (
    YamlSettingsProvider,
    Device
)
from ophyd_async.plan_stubs import (
    retrieve_settings,
    store_settings,
    apply_settings,
    apply_settings_if_different,
    get_current_settings
)
import os

__all__ = [
    'save_device_settings',
    'load_device_settings',
    'set_provider',
    'use_settings'
]

def save_device_settings(provider: YamlSettingsProvider | str, devices: list):
    """
    Create a provider directory and store the settings of the devices.

    Parameters
    ----------
    provider : YamlSettingsProvider or str
        The settings provider or the path to the provider directory.
    devices : list
        The list of devices whose settings are to be stored.
    """
    if isinstance(provider, str):
        provider = YamlSettingsProvider(provider)
    
    provider_path = str(provider._file_path)
        
    if not os.path.exists(provider_path):
        os.makedirs(provider_path)
    for device in devices:
        yield from store_settings(provider, device.name, device, True)


def load_device_settings(provider: YamlSettingsProvider | str, devices: list):
    """
    Load settings from a provider and apply them to the devices.

    Parameters
    ----------
    provider : YamlSettingsProvider or str
        The settings provider or the path to the provider directory.
    devices : list
        The list of devices to which the settings are to be applied.
    """
    if isinstance(provider, str):
        provider = YamlSettingsProvider(provider)
        
    for device in devices:
        current_settings = yield from get_current_settings(device, True)
        new_settings = yield from retrieve_settings(provider, device.name, device, True)
        yield from apply_settings_if_different(new_settings, apply_settings, current_settings)


def set_provider(provider: YamlSettingsProvider | str):
    """
    Decorator which adds a provider to the local namespace of a function.

    Parameters
    ----------
    provider : YamlSettingsProvider or str
        The settings provider to be added to the local namespace.
    """
    if isinstance(provider, str):
        provider = YamlSettingsProvider(provider)
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Add the provider to the function's local namespace
            func.__globals__['provider'] = provider
            return func(*args, **kwargs)
        return wrapper
    return decorator


def use_settings(provider: YamlSettingsProvider | str):
    """
    Plan decorator which will apply settings from a provider before a plan is run and then reset the settings after the plan is run.

    Parameters
    ----------
    provider : YamlSettingsProvider or str
        The settings provider from which settings are to be applied and reset.
    """
    if isinstance(provider, str):
        provider = YamlSettingsProvider(provider)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            def inner_wrapper():
                devices = {arg for arg in args if isinstance(arg, Device)}
                # If any kwargs are devices, add them to the set
                for arg in kwargs.values():
                    if isinstance(arg, Device):
                        devices.add(arg)
                
                current_settings = {}
                new_settings = {}
                
                for device in devices:
                    current_settings[device.name] = yield from get_current_settings(device, True)
                    new_settings[device.name] = yield from retrieve_settings(provider, device.name, device, True)
                    yield from apply_settings_if_different(new_settings[device.name], apply_settings, current_settings[device.name])
                
                def _reset_devices(_settings, _devices):
                    for device in _devices:
                        yield from apply_settings_if_different(_settings[device.name], apply_settings)
                
                yield from func(*args, **kwargs)
                yield from _reset_devices(current_settings, devices)
            
            return inner_wrapper()
        
        return wrapper
    return decorator