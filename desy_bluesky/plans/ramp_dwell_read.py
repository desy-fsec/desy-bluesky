import bluesky.plan_stubs as bps
from bluesky.protocols import Readable, Movable
from typing import Dict, Any, List
import time

def ramp_dwell_read(
    positioner: Movable,
    readables: List[Readable],
    setpoint: float,
    dwell_time: float,
    sample_period: float | None = None,
    md: Dict[str, Any] | None = None
):
    """
    Ramp the positioner to the setpoints and read the detectors at the specified sample rate.

    Parameters
    ----------
    positioner : Any
        The positioner to be moved.
    readables : List[Readable]
        The detectors or Readable devices to be read.
    setpoint : Sequence[float]
        The target setpoints for the positioner.
    dwell_time (s) : Sequence[float]
        The times to dwell at each setpoint.
    sample_period (s) : float, optional
        The period at which to sample the detectors. If None, the detectors will not be sampled.
    md : dict, optional
        Metadata to include in the run.
    """
    _md = {
        "plan_name": "ramp_and_read",
        "motors": positioner.name,
        "detectors": [det.name for det in readables] + [positioner.name],
        "plan_args": {
            "positioner": positioner.name,
            "readables": [det.name for det in readables],
            "setpoint": setpoint,
            "dwell_time": dwell_time,
            "sample_period": sample_period,
        },
    }

    if md is not None:
        _md.update(md)

    ramp_status = yield from bps.abs_set(positioner, setpoint, group='ramp', wait=False)
    readables_and_positioner = [positioner] + readables
    
    if sample_period is not None:
        sample_period = float(sample_period)
        yield from bps.open_run(md=_md)
        while not ramp_status.done:
            yield from bps.trigger_and_read(readables_and_positioner)
            yield from bps.sleep(sample_period)
        
        start_of_dwell = time.time()
        while time.time() - start_of_dwell < dwell_time:
            yield from bps.trigger_and_read(readables_and_positioner)
            yield from bps.sleep(sample_period)
        yield from bps.close_run()
        
    else:
        yield from bps.wait('ramp')
        yield from bps.sleep(dwell_time)
    
    
    