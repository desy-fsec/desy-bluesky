from bluesky.utils import maybe_await
from bluesky_queueserver_api.zmq import REManagerAPI as ZMQ_REManagerAPI
from bluesky_queueserver_api.zmq.aio import REManagerAPI as ZMQ_REManagerAPI_AIO
from bluesky_queueserver_api.http import REManagerAPI as HTTP_REManagerAPI
from bluesky_queueserver_api.http.aio import REManagerAPI as HTTP_REManagerAPI_AIO
from bluesky_queueserver_api.console_monitor import (
    ConsoleMonitor_ZMQ_Threads,
    ConsoleMonitor_ZMQ_Async,
    ConsoleMonitor_HTTP_Threads,
    ConsoleMonitor_HTTP_Async
)

REMOTE_QUEUE_COMMAND = "remote_queue"


def check_if_object_is_REManagerAPI(obj):
    if isinstance(
        obj,
        (
            ZMQ_REManagerAPI,
            ZMQ_REManagerAPI_AIO,
            HTTP_REManagerAPI,
            HTTP_REManagerAPI_AIO,
            ConsoleMonitor_HTTP_Threads,
            ConsoleMonitor_HTTP_Async,
            ConsoleMonitor_ZMQ_Threads,
            ConsoleMonitor_ZMQ_Async,
        ),
    ):
        return True
    return False


def is_property(obj, attr_name):
    attr = getattr(obj.__class__, attr_name, None)
    return isinstance(attr, property)


async def remote_queue_coroutine(msg):
    run_manager = msg.obj

    if not check_if_object_is_REManagerAPI(run_manager):
        raise ValueError("The object is not an instance of REManagerAPI or ConsoleMonitor.")

    attr_name = msg.args[0]
    args = msg.args[1]
    kwargs = msg.args[2]
    attr = getattr(run_manager, attr_name)

    if callable(attr):
        result = await maybe_await(attr(*args, **kwargs))
    elif is_property(run_manager, attr_name):
        if args:
            if args[0] is not None:
                setattr(run_manager, attr_name, args[0])
        result = attr
    else:
        raise ValueError(
            f"The attribute '{attr_name}' is neither callable nor a property of REManagerAPI."
        )

    return result
