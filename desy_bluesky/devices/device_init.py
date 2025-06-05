"""
This module provides methods to asynchronously create and initialize devices using a
device dictionary.

The device dictionary should have the following structure:

    device_list = {
        'device_name': {
            'driver': 'device_module_name.DeviceClassName',
            'uri': 'device_uri',        # Tango TRL, EPICS prefix, or similar
            'kwargs': {
                'name': 'device_name',
                'scalar_kwarg': scalar_value
                'device_kwarg': 'SOME_DEVICE_NAME#device',
                'list_kwarg':
                    - scalar_value,
                    - 'SOME_DEVICE_NAME#device',
                'dict_kwarg':
                    'key1': scalar_value,
                    'key2': 'SOME_DEVICE_NAME#device'
            }
        }
    }

The module provides the following functions:

- create_devices: Asynchronously create devices from a device dictionary.

This module uses an asyncio Lock to ensure that the creation and initialization of
devices is thread-safe.
"""

import asyncio
import copy
import importlib
import os
from typing import Dict, TypeVar, Any

from ophyd_async.core import init_devices
from desy_bluesky.scripts import parse_yml
from bluesky_queueserver import is_ipython_mode

RESOURCE_LOCK = asyncio.Lock()
DEVICES_TO_BE_CREATED = []
DEVICE_INIT_TIMEOUT = 10

T = TypeVar("T")


async def create_devices(
    devlist: Dict[str, Dict[str, Any]], namespace: Dict[str, T] | None = None
) -> Dict[str, Any]:
    """
    Create devices asynchronously from a dictionary of device types and their URIs.

    :param devlist: Dictionary of device types and their URIs
    :param namespace: Namespace to add the devices to. This is usually the global
                      namespace of the calling module or startup script.

    """
    if not devlist:
        return
    tasks = []
    if not namespace:
        print(
            "Warning: No namespace provided. The namespace of the calling module will"
            " be used."
        )
        namespace = globals()

    _check_valid_device_names(devlist)
    # _check_circular_dependencies(devlist)

    print("DEVICES TO BE CREATED: ", DEVICES_TO_BE_CREATED)
    print("Creating devices...")

    for _, device_info in devlist.items():
        try:
            async with RESOURCE_LOCK:
                device_type = namespace[device_info["driver"]]
        except KeyError:
            device_type = _get_device_type(device_info["driver"])
        # Get uri if key exists otherwise set to None
        uri = device_info.get("uri", None)
        try:
            tasks.append(
                asyncio.create_task(
                    _create_device(
                        dtype=device_type,
                        uri=uri,
                        namespace=namespace,
                        **device_info["kwargs"],
                    )
                )
            )
            tasks[-1].add_done_callback(
                lambda task: _device_init_callback(task, namespace)
            )

        except KeyError as exc:
            print(f"Error: {exc}")
            return

    devices = await asyncio.gather(*tasks)
    device_dict = {dev.name: dev for dev in devices}

    if not DEVICES_TO_BE_CREATED:
        print("All startup devices created.")
    else:
        print("Error: Not all devices created.")
        print("Devices not created: ", DEVICES_TO_BE_CREATED)

    return device_dict


async def _create_device(
    dtype: T, uri: str = None, namespace: Dict[str, T] = None, **kwargs
) -> T:
    """
    Asynchronous method to create a device.

    :param dtype: Device type
    :param uri: Device URI. Can be a tango TRL or an EPICS prefix
    """
    if not namespace:
        namespace = globals()
    kwargs_c = copy.deepcopy(kwargs)
    if "name" not in kwargs_c:
        raise KeyError("All devices must have a 'name' kwarg.")

    parent = kwargs_c["name"]
    tasks = []
    for key, value in kwargs_c.items():
        parent_copy = copy.deepcopy(parent)
        new_task = asyncio.create_task(_parse_kwarg(parent_copy, key, value, namespace))
        tasks.append(new_task)
    new_values = await asyncio.gather(*tasks)
    for i, key in enumerate(kwargs_c.keys()):
        kwargs_c[key] = new_values[i]

    device_handles_md = False
    # Get the list of kwargs expected by the device constructor
    expected_kwargs = dtype.__init__.__code__.co_varnames
    # Only pass the kwargs that are expected by the constructor
    good_kwargs = {
        key: value for key, value in kwargs_c.items() if key in expected_kwargs
    }
    if "md" in expected_kwargs:
        device_handles_md = True

    if is_ipython_mode():
        with init_devices():
            dev = dtype(uri, **good_kwargs) if uri else dtype(**good_kwargs)
    else:
        async with init_devices():
            dev = dtype(uri, **good_kwargs) if uri else dtype(**good_kwargs)

    # If md is a kwarg and the device does not handle md in __init__,
    # add it to the device
    if "md" in kwargs_c and not device_handles_md:
        dev.md = kwargs_c["md"]

    return dev


async def _parse_arg(parent: str, arg: str, namespace: Dict[str, T]) -> Any:
    """
    Parse a string that contains a device name and return the device object.
    """
    if not isinstance(arg, str):
        return arg

    if "#device" in arg:
        device_string = arg.split("#")[0]
        device = await _get_sub_device(parent, device_string, namespace)
        return device

    return arg


async def _parse_kwarg(
    parent: str, key: str, value: Any, namespace: Dict[str, T]
) -> Any:

    if key in ["driver", "uri", "name", "md"]:
        return value

    # If the arg is a dictionary, call parse_kwarg recursively
    if isinstance(value, dict):
        arg = {}
        tasks = []
        for sub_key, val in value.items():
            parent_copy = copy.deepcopy(parent)
            tasks.append(_parse_arg(parent_copy, val, namespace))  # Remove await here
        new_values = await asyncio.gather(*tasks)  # Await the tasks here
        for i, sub_key in enumerate(value.keys()):
            arg[sub_key] = new_values[i]
        return arg

    # If the arg is a list, call parse_kwarg recursively for each element

    if isinstance(value, (list, set, tuple)):
        tasks = []
        for _, val in enumerate(value):
            parent_copy = copy.deepcopy(parent)
            new_task = asyncio.create_task(_parse_arg(parent_copy, val, namespace))
            tasks.append(new_task)
        arg = await asyncio.gather(*tasks)
        return arg

    if isinstance(value, str):
        arg = await _parse_arg(parent, value, namespace)
        return arg

    return value


async def _get_sub_device(parent: str, arg: str, namespace: Dict[str, T]) -> T:
    """
    Get a device object from the namespace. If the device does not exist in
    the namespace, wait for it to be created.
    """
    async with RESOURCE_LOCK:
        arg_exists = arg in namespace
    if arg_exists:
        async with RESOURCE_LOCK:
            device = namespace[arg]
            return device
    else:
        # If the arg is a string but there is no object with the same name
        # in the global namespace, check to see if the arg is a device name
        # in the list of devices to be created in the event loop. This is a shared
        # resource so wait for the lock to be released before checking.
        waiting_for_dependent_device = False
        async with RESOURCE_LOCK:
            if arg in DEVICES_TO_BE_CREATED:
                waiting_for_dependent_device = True
            else:
                except_string = (
                    f" {arg} not found in namespace and is not in "
                    f"the list of devices to be created. Check that all"
                    f" dependent devices are being created."
                )
                raise KeyError(except_string)
        # If we are waiting for a dependent device, sleep for one second,
        # request the
        # lock again and check if the device has been created.
        loops = 0
        while waiting_for_dependent_device:
            print(f"{parent} is waiting for for {arg} to" f" be created...")
            loops += 1
            await asyncio.sleep(1)
            async with RESOURCE_LOCK:
                arg_exists = arg in namespace
            if arg_exists:
                waiting_for_dependent_device = False
            if loops >= DEVICE_INIT_TIMEOUT:
                raise TimeoutError(
                    f"Error: {arg} not initialized" f".Check for circular dependencies."
                )

        if arg_exists:
            async with RESOURCE_LOCK:
                device = namespace[arg]
                return device


def _device_init_callback(task: asyncio.Task, namespace: Dict[str, T]) -> None:
    """
    Sync callback to call remove_device_name_on_task_end asynchronously.
    """
    asyncio.create_task(_add_to_namespace(task, namespace))


async def _add_to_namespace(task: asyncio.Task, namespace: Dict[str, T]) -> None:
    """
    Add the device to the global namespace and remove it from the list of devices to be
    created.
    """
    device = task.result()
    async with RESOURCE_LOCK:
        try:
            namespace[device.name] = device
            if task.result().name in DEVICES_TO_BE_CREATED:
                DEVICES_TO_BE_CREATED.remove(task.result().name)
            else:
                print(
                    f"Error: {task.result().name} not in DEVICES_TO_BE_CREATED."
                    f"Nested devices may not have initialized correctly."
                )
            print(f"Device {device.name} of class {device.__class__.__name__} created.")
        except ValueError as exc:
            raise exc


# FIX THIS AT SOME POINT
def _check_circular_dependencies(devlist: Dict) -> None:
    """
    Check for circular dependencies in the device list via a depth-first search.

    :param devlist: Dictionary of device types and their URIs
    :raises ValueError: If a circular dependency is found
    """
    dependencies = {device: set() for device in devlist}

    for device, device_info in devlist.items():
        kwargs = device_info.get("kwargs", {})
        for key, value in kwargs.items():
            if isinstance(value, str) and "#device" in value:
                parts = value.split("#")
                dependencies[device].add(parts[0])
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and "#device" in item:
                        parts = item.split("#")
                        dependencies[device].add(parts[0])
            elif isinstance(value, dict):
                for sub_value in value.values():
                    if isinstance(sub_value, str) and "#device" in sub_value:
                        parts = sub_value.split("#")
                        dependencies[device].add(parts[0])

    for device in devlist:
        visited = set()
        stack = [device]
        while stack:
            current = stack[-1]
            if current in visited:
                raise ValueError(
                    f"Circular dependency found: {device} depends on" f" itself."
                )
            visited.add(current)
            for dependent in dependencies[current]:
                if dependent not in visited:
                    stack.append(dependent)
            if current == stack[-1]:
                stack.pop()


def _get_device_type(type_string: str) -> T:
    # Try to import the module
    try:
        try:
            module_name, class_name = type_string.rsplit(".", 1)
        except ValueError:
            module_name, class_name = type_string
        module = importlib.import_module(module_name)
        device_type = getattr(module, class_name)
    except ImportError as exc:
        raise ImportError(f"Error: {exc}.")
    except KeyError as exc:
        raise KeyError(f"Error: {exc}.")
    return device_type


def _check_valid_device_names(devlist: Dict) -> None:
    """
    Check for valid device names in the device list.

    Requirements:
    - Device names must be strings.
    - In the devlist, each key must be a string and be equal to the 'name' kwarg
      of the device.

    :param devlist: Dictionary of device types and their URIs
    :raises ValueError: If a device name is not a string
    """
    for device, device_info in devlist.items():
        if not isinstance(device, str):
            raise ValueError(f"Error: Device key {device} must be a string.")
        try:
            DEVICES_TO_BE_CREATED.append(device_info["kwargs"]["name"])
        except KeyError as exc:
            print(f"Error: {exc}. Device {device} is missing a 'name' kwarg.")
            raise
        if device != device_info["kwargs"]["name"]:
            raise ValueError(
                f"Error: Device key {device} must be equal to the 'name'"
                f" kwarg of the device."
            )


def get_device_list(device_uri_path: str = None) -> Dict[str, Dict[str, Any]]:
    print("Loading device list...")
    dlist = {}
    if os.path.isfile(device_uri_path):
        dlist = parse_yml(*["devices"], yml_file=device_uri_path)
        print(f"Device list loaded from {device_uri_path}")
    else:
        print(f"Error: {device_uri_path} not found")
    return dlist
