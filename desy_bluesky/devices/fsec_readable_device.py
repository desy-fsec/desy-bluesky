from __future__ import annotations

from typing import TypeVar

from ophyd_async.core import (
    SignalR,
)
from ophyd_async.tango import (
    TangoReadable,
    tango_polling
)
from tango import DevState

FSECDeviceConfig = TypeVar("FSECDeviceConfig")


@tango_polling((0.1, 0.1, 0.1))
class FSECReadableDevice(TangoReadable):
    State: SignalR[DevState]
