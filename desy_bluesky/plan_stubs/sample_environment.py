from typing import Hashable
import bluesky.plan_stubs as bps
from bluesky.protocols import Movable

def ramp(positioner: Movable,
         setpoint: float,
         group: Hashable | None = None,
         wait: bool = True
):
    return (yield from bps.abs_set(positioner, setpoint, group=group, wait=wait))

def dwell(dwell_time: float):
    yield from bps.sleep(dwell_time)

def ramp_and_dwell(positioner: Movable,
                   setpoint: float,
                   dwell_time: float = 0.0,
                   group: Hashable | None = None,
                   wait: bool = True
):
    yield from ramp(positioner, setpoint, group=group, wait=wait)
    if dwell_time > 0:
        yield from dwell(dwell_time)