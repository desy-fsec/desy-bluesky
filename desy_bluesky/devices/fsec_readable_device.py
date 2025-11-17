from __future__ import annotations

from typing import TypeVar
from typing import Annotated as A
import time

from bluesky.protocols import Subscribable, Callback, Reading

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.tango.core import TangoPolling, DevStateEnum, TangoDevice
from ophyd_async.core._utils import LazyMock, DEFAULT_TIMEOUT
from tango import DevState

FSECDeviceConfig = TypeVar("FSECDeviceConfig")


class FSECReadableDevice(TangoDevice, StandardReadable):
    State: A[SignalR[DevStateEnum], TangoPolling(0.1)]

    def __repr__(self):
        return self.name


class FSECSubscribable(Subscribable):

    async def connect(
        self,
        mock: bool | LazyMock = False,
        timeout: float = DEFAULT_TIMEOUT,
        force_reconnect: bool = False,
    ) -> None:
        await super().connect(
            mock=mock, timeout=timeout, force_reconnect=force_reconnect
        )
        try:
            self._callbacks: list[Callback] = []
            self._processing_callbacks = False
            self._subscribed_signals = {}
            hints = getattr(self, "hints", {})
            fields = hints.get("fields", [])
            for signal_name in fields:
                parts = signal_name.split("-")
                child = self
                for component in parts[1:]:
                    child = getattr(child, component)
                if hasattr(child, "subscribe"):
                    child.subscribe(self._trigger_callbacks)
                    self._subscribed_signals[child.name] = child
        except Exception as e:
            print(f"Error during connection: {e}")
            raise e

    def _trigger_callbacks(self, foo: dict[str, Reading]):
        try:
            if self._processing_callbacks is True:
                return
            self._processing_callbacks = True
            # If many signals are subscribed, we wait a bit to ensure all signals have been updated
            time.sleep(0.1)
            cached_readings = {
                signal_name: signal._get_cache()._reading
                for signal_name, signal in self._subscribed_signals.items()
            }
            for callback in self._callbacks:
                callback(cached_readings)
            self._processing_callbacks = False
        except Exception as e:
            self._processing_callbacks = False
            raise e

    def subscribe(self, function: Callback):
        if function not in self._callbacks:
            self._callbacks.append(function)
        else:
            raise ValueError("Function already subscribed")

    def clear_sub(self, function: Callback):
        if function in self._callbacks:
            self._callbacks.remove(function)
        else:
            raise ValueError("Function not subscribed")
