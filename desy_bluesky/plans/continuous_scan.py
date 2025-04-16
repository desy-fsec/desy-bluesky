import bluesky.plan_stubs as bps
from typing import List
from bluesky.protocols import Readable, Movable, Triggerable

READABLE_AND_TRIGGERABLE = Readable | Triggerable

def continuous_scan(
    detectors: List[Readable],
    motor: Movable,
    start: float,
    stop: float,
    sample_period: float,
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
            "sample_rate": sample_period,
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
        detectors_and_motor = detectors + [motor]
        yield from bps.trigger_and_read(detectors_and_motor)
        yield from bps.sleep(sample_period)
        
    yield from bps.close_run()
