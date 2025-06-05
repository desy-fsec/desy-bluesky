import bluesky.plan_stubs as bps
from bluesky.protocols import Readable, Movable
from typing import Any


def ramp(
    positioner: Movable,
    readables: list[Readable],
    setpoint: float,
    sample_period: float,
    md: dict[str, Any] | None = None,
):
    """
    Perform a ramping motion of a positioner while periodically reading detectors.

    This plan moves a positioner (e.g., a motor) to a specified setpoint while
    simultaneously triggering and reading a list of detectors at regular intervals.
    Metadata about the plan, positioner, and detectors is recorded.

    Parameters:
        positioner (Movable): The positioner (e.g., motor) to be moved.
        readables (list[Readable]): A list of readable devices (e.g., detectors) to be triggered and read.
        setpoint (float): The target position for the positioner.
        sample_period (float): The time interval (in seconds) between successive readings of the detectors.
        md (dict[str, Any] | None, optional): Additional metadata to include in the run. Defaults to None.

    Yields:
        Msg: Bluesky messages for controlling the RunEngine.
    """

    _md = {
        "plan_name": "ramp_and_read",
        "motors": [positioner.name],
        "detectors": [det.name for det in readables] + [positioner.name],
        "plan_args": {
            "positioner": positioner.name,
            "readables": [det.name for det in readables],
            "setpoint": setpoint,
            "sample_period": sample_period,
        },
    }

    if md is not None:
        _md.update(md)

    yield from bps.open_run(md=_md)
    yield from bps.checkpoint()
    move_status = yield from bps.abs_set(positioner, setpoint, group="ramp", wait=False)
    readables_and_positioner = [positioner] + readables
    sample_period = float(sample_period)
    while not move_status.done:
        yield from bps.trigger_and_read(readables_and_positioner)
        yield from bps.sleep(sample_period)
    yield from bps.trigger_and_read(readables_and_positioner)
    yield from bps.close_run()
