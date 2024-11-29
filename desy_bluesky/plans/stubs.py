from bluesky.protocols import Movable
import bluesky.plan_stubs as bps

def ramp(positioner: Movable, target: float, wait: bool = True, md: dict | None = None):
    """
    Ramp the positioner from its current position to the target position.
    """
    if wait:
        yield from bps.mv(positioner, target)
    else:
        yield from bps.abs_set(positioner, target)

def dwell(time: float):
    """
    Dwell for the time specified in the metadata.
    """
    yield from bps.sleep(float(time))