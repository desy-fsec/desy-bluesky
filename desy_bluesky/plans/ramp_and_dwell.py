import bluesky.plan_stubs as bps
import time
from bluesky.protocols import Movable, Readable

def ramp_and_dwell(positioner: Movable | Readable,
                   setpoint: float,
                   dwell_time: float = 0.0,
                   sample_time: float = 0.1,
                   md: dict | None = None):
    """
    Ramp the positioner to the setpoint and dwell for the specified time.

    Parameters
    ----------
    positioner : Movable
        The positioner to ramp.
    setpoint : float
        The setpoint to ramp to.
    dwell_time : float
        The time to dwell after ramping.
    sample_time : float
        The rate at which the positioner is read.
    md : dict, optional
        Metadata to be included in the start document.
    """
    md = md or {}
    _md = {
        'plan_name': 'ramp_and_dwell',
        'detectors': [],
        'motors': [positioner.name],
        'plan_args': {
            'detectors': [],
            'device': positioner.name,
            'setpoint': setpoint,
            'dwell_time': dwell_time,
        },
        'plan_pattern': '',
        'plan_pattern_module': '',
        'plan_pattern_args': {},
    }

    _md.update(md)

    yield from bps.open_run(_md)

    ramp_status = yield from bps.abs_set(positioner, setpoint)
    while ramp_status.done is False:
        yield from bps.checkpoint()
        yield from bps.create()
        yield from bps.read(positioner)
        yield from bps.save()
        time.sleep(sample_time)

    if dwell_time > 0:
        start_time = time.time()
        while time.time() - start_time < dwell_time:
            yield from bps.checkpoint()
            yield from bps.create()
            yield from bps.read(positioner)
            yield from bps.save()
            time.sleep(sample_time)

    yield from bps.close_run()

