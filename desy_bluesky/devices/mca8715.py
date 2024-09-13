from typing import Optional, Union
import numpy.typing as npt

from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
    ConfigSignal,
    SignalRW,
    SignalX,
    SignalR,
)
from bluesky.protocols import (
    Triggerable,
)

from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class MCA8715(FSECReadableDevice, Triggerable):
    """
    A device that controls a MCA8715 Multi-Channel Analyzer.
    """
    DataLength: SignalRW[int]
    Data: SignalRW[npt.NDArray[int]]
    Counts: SignalR[npt.NDArray[float]]
    CountsDiff: SignalR[npt.NDArray[float]]
    Clear: SignalX

    def __init__(
            self,
            trl: Optional[str] = None,
            device_proxy: Optional[Union[AsyncDeviceProxy, SyncDeviceProxy]] = None,
            name: str = "",
    ) -> None:
        super().__init__(trl, device_proxy, name)
        self.add_readables([self.Data, self.Counts, self.CountsDiff], HintedSignal)
        self.add_readables([self.DataLength], ConfigSignal)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        try:
            await self.Clear.trigger()
        except Exception as e:
            raise RuntimeError(f"Error triggering {self.name}: {e}")
