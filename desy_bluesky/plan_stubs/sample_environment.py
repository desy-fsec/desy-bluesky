from typing import Hashable
import bluesky.plan_stubs as bps
from bluesky.protocols import Movable

def ramp(positioner: Movable,
         setpoint: float,
         group: Hashable | None = None,
         wait: bool = True):
    """
    Ramp the positioner to the specified setpoint.

    Parameters
    ----------
    positioner : Movable
        The positioner to be moved.
    setpoint : float
        The target setpoint for the positioner.
    group : Hashable, optional
        Group identifier for the movement.
    wait : bool, optional
        If True, wait for the movement to complete before proceeding.

    Returns
    -------
    Status
        Status object that completes when the value is set. If wait is True, this will always be complete by the time it is returned.
    """
    return (yield from bps.abs_set(positioner, setpoint, group=group, wait=wait))

def dwell(dwell_time: float):
    """
    Dwell for the specified amount of time.

    Parameters
    ----------
    dwell_time : float
        The time to dwell in seconds.

    Returns
    -------
    generator
        A generator that yields a bluesky plan to sleep for the specified time.
    """
    yield from bps.sleep(dwell_time)

def ramp_and_dwell(positioner: Movable,
                   setpoint: float,
                   dwell_time: float = 0.0):
    """
    Ramp the positioner to the specified setpoint and dwell for the specified time.

    Parameters
    ----------
    positioner : Movable
        The positioner to be moved.
    setpoint : float
        The target setpoint for the positioner.
    dwell_time : float, optional
        The time to dwell at the setpoint in seconds.

    Returns
    -------
    generator
        A generator that yields a bluesky plan to ramp the positioner and dwell.
    """
    yield from ramp(positioner, setpoint, wait=True)
    if dwell_time > 0:
        yield from dwell(dwell_time)