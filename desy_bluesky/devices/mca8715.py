import numpy as np

from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
    ConfigSignal,
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
    DataLength: SignalRW[int]
    Data: SignalRW[Array1D[np.int32]]
    Counts: SignalR[Array1D[np.float64]]
    CountsDiff: SignalR[Array1D[np.float64]]
    Clear: SignalX

    def __init__(
            self,
            trl: str | None = None,
            device_proxy: DeviceProxy | None = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Data, self.Counts, self.CountsDiff], Format.HINTED_SIGNAL)
        self.add_readables([self.DataLength], Format.CONFIG_SIGNAL)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        try:
            await self.Clear.trigger()
        except Exception as e:
            raise RuntimeError(f"Error triggering {self.name}: {e}")
