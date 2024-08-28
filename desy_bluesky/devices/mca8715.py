from typing import Optional, Union

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
from ophyd_async.tango import (
    TangoReadable
)
from tango import DeviceProxy as SyncDeviceProxy
from tango.asyncio import DeviceProxy as AsyncDeviceProxy

from .fsec_readable_device import FSECReadableDevice


class MCA8715(FSECReadableDevice, Triggerable):
    """
    A device that controls a MCA8715 Multi-Channel Analyzer.
    """
    DataLength: SignalRW
    Data: SignalRW
    State: SignalR
    Counts: SignalR
    CountsDiff: SignalR
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

    def trigger(self) -> AsyncStatus:
        return AsyncStatus(self._clear())

    async def _clear(self) -> None:
        try:
            await self.Clear.trigger()
        except Exception as e:
            raise RuntimeError(f"Error triggering {self.name}: {e}")
