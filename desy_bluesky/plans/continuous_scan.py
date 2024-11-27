import bluesky.plan_stubs as bps

def continuous_scan(detectors,
                    motor,
                    start,
                    stop,
                    sample_rate,
                    md=None):

    _md = {
        'plan_name': 'continuous_scan',
        'detectors': [det.name for det in detectors],
        'motors': [motor.name],
        'plan_args': {
            'detectors': [det.name for det in detectors],
            'motor': motor.name,
            'start': start,
            'stop': stop,
            'sample_rate': sample_rate,
        },
        'plan_pattern': '',
        'plan_pattern_module': '',
        'plan_pattern_args': {},
    }

    md = md or {}
    _md.update(md)

    yield from bps.mv(motor, start)
    yield from bps.open_run(_md)
    move_status = yield from bps.abs_set(motor, stop)

    while move_status.done is False:
        yield from bps.create()
        yield from bps.read(motor)
        for det in detectors:
            yield from bps.read(det)
        yield from bps.save()
        yield from bps.sleep(1/sample_rate)

    yield from bps.close_run()
