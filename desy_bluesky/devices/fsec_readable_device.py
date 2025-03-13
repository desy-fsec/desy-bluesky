from __future__ import annotations

from typing import TypeVar
from typing import Annotated as A

from ophyd_async.core import (
    SignalR,
)
from ophyd_async.tango.core import TangoReadable, TangoPolling
from tango import DevState

FSECDeviceConfig = TypeVar("FSECDeviceConfig")


class FSECReadableDevice(TangoReadable):
    State: A[SignalR[DevState], TangoPolling(0.1)]
    
    def __init__(self,
                 trl: str | None = None,
                 name: str = "",
                 auto_fill_signals: bool = True) -> None:
        TangoReadable.__init__(self, trl, name=name, auto_fill_signals=auto_fill_signals)

    def __repr__(self):
        return self.name
