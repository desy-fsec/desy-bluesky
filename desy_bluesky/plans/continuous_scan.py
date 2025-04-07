import bluesky.plan_stubs as bps
from typing import Sequence
from bluesky.protocols import Readable, Movable, Triggerable

READABLE_AND_TRIGGERABLE = Readable | Triggerable

def continuous_scan(
    detectors: Sequence[Readable],
    motor: Movable,
    start: float,
    stop: float,
    sample_rate: float,
    md=None,
):

    _md = {
        "plan_name": "continuous_scan",
        "detectors": [det.name for det in detectors],
        "motors": [motor.name],
        "plan_args": {
            "detectors": [det.name for det in detectors],
            "motor": motor.name,
            "start": start,
            "stop": stop,
            "sample_rate": sample_rate,
        },
        "plan_pattern": "",
        "plan_pattern_module": "",
        "plan_pattern_args": {},
    }

    md = md or {}
    _md.update(md)
    yield from bps.checkpoint()
    yield from bps.mv(motor, start)
    yield from bps.open_run(_md)
    
    move_status = yield from bps.abs_set(motor, stop)
    while move_status.done is False:
        yield from bps.trigger_and_read(detectors)
        
    yield from bps.close_run()
