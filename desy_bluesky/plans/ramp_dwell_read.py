import bluesky.plan_stubs as bps
from typing import Dict, Any
import time

def ramp_dwell_read(
    positioner: Any,
    setpoint: float,
    dwell_time: float,
    sample_period: float,
    md: Dict[str, Any] | None = None
):
    """
    Ramp the positioner to the setpoints and read the detectors at the specified sample rate.

    Parameters
    ----------
    positioner : Any
        The positioner to be moved.
    setpoint : Sequence[float]
        The target setpoints for the positioner.
    dwell_time (s) : Sequence[float]
        The times to dwell at each setpoint.
    sample_period (s) : float
        The period at which to sample the detectors.
    md : dict, optional
        Metadata to include in the run.
    """
    _md = {
        "plan_name": "ramp_and_read",
        "motors": positioner.name,
        "detectors": [positioner.name],
        "plan_args": {
            "positioner": positioner.name,
            "setpoint": setpoint,
            "dwell_time": dwell_time,
            "sample_period": sample_period,
        },
    }

    if md is not None:
        _md.update(md)

    yield from bps.open_run(md=_md)
    
    ramp_status = yield from bps.abs_set(positioner, setpoint, wait=False)
    while not ramp_status.done:
        yield from bps.trigger_and_read([positioner])
        yield from bps.sleep(sample_period)
    
    start_of_dwell = time.time()
    while time.time() - start_of_dwell < dwell_time:
        yield from bps.trigger_and_read([positioner])
        yield from bps.sleep(sample_period)    
    
    yield from bps.close_run()
    