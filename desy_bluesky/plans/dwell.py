from typing import Any
import time
import bluesky.plan_stubs as bps
from bluesky.protocols import Readable


def dwell(
    readables: list[Readable],
    dwell_time: float,
    sample_period: float,
    md: dict[str, Any] | None = None,
):
    """
    Dwell at the current position and read the readable devices at the specified sample rate.

    Parameters
    ----------
    readables : List[Readable]
        The detectors or Readable devices to be read.
    dwell_time (s) : float
        The time to dwell at the current position.
    sample_period (s) : float
        The period at which to sample the readable devices.
    md : dict, optional
        Metadata to include in the run.
    """
    _md = {
        "plan_name": "dwell_and_read",
        "detectors": [det.name for det in readables],
        "plan_args": {
            "readables": [det.name for det in readables],
            "dwell_time": dwell_time,
            "sample_period": sample_period,
        },
    }

    if md is not None:
        _md.update(md)

    if sample_period is not None:
        sample_period = float(sample_period)
        yield from bps.open_run(md=_md)
        start_of_dwell = time.time()
        end_of_dwell = start_of_dwell + dwell_time
        while True:
            current_time = time.time()
            if current_time + sample_period < end_of_dwell:
                yield from bps.trigger_and_read(readables)
                yield from bps.sleep(sample_period)
            if current_time >= end_of_dwell:
                break
        yield from bps.trigger_and_read(readables)
        yield from bps.close_run()
