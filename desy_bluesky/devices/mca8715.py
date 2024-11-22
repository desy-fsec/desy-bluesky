import numpy as np
from typing import Annotated as A

from ophyd_async.core import (
    AsyncStatus,
    SignalRW,
    SignalX,
    SignalR,
    Array1D,
    StandardReadableFormat as Format
)
from bluesky.protocols import (
    Triggerable,
)

from tango import DeviceProxy

from .fsec_readable_device import FSECReadableDevice


class MCA8715(FSECReadableDevice, Triggerable):
    """
    A device that controls a MCA8715 Multi-Channel Analyzer.
    """
    DataLength: A[SignalRW[int], Format.CONFIG_SIGNAL]
    Data: A[SignalRW[Array1D[np.int32]], Format.HINTED_UNCACHED_SIGNAL]
    Counts: A[SignalR[Array1D[np.float64]], Format.HINTED_UNCACHED_SIGNAL]
    CountsDiff: A[SignalR[Array1D[np.float64]], Format.HINTED_UNCACHED_SIGNAL]
    Clear: SignalX

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        try:
            await self.Clear.trigger()
        except Exception as e:
            raise RuntimeError(f"Error triggering {self.name}: {e}")
