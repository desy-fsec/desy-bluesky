from __future__ import annotations

from typing import Annotated as A

from ophyd_async.core import (
    SignalX,
    SignalRW,
    SignalR,
    Array1D,
    StandardReadableFormat as Format
)

from .fsec_readable_device import FSECReadableDevice

class Dante(FSECReadableDevice):
    ConfigFilePath: A[SignalRW[str], Format.CONFIG_SIGNAL]
    Counts00: SignalR[Array1D[int]]
    Counts01: SignalR[Array1D[int]]
    Counts02: SignalR[Array1D[int]]
    Counts03: SignalR[Array1D[int]]
    Data00: SignalR[Array1D[int]]
    Data01: SignalR[Array1D[int]]
    Data02: SignalR[Array1D[int]]
    Data03: SignalR[Array1D[int]]
    FileDir: A[SignalRW[str], Format.CONFIG_SIGNAL]
    FilePrefix: A[SignalRW[str], Format.CONFIG_SIGNAL]
    FileStartNum: A[SignalRW[int], Format.CONFIG_SIGNAL]
    FrameCounter: SignalR[int]
    FramesPerFile: A[SignalRW[int], Format.CONFIG_SIGNAL]
    GatingMode: A[SignalRW[int], Format.CONFIG_SIGNAL]
    ICR00: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    ICR01: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    ICR02: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    ICR03: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    Init: SignalX
    NbFrames: A[SignalRW[int], Format.CONFIG_SIGNAL]
    OCR00: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    OCR01: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    OCR02: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    OCR03: A[SignalR[int], Format.HINTED_UNCACHED_SIGNAL]
    ROIs00: SignalR[Array1D[int]]
    ROIs01: SignalR[Array1D[int]]
    ROIs02: SignalR[Array1D[int]]
    ROIs03: SignalR[Array1D[int]]
    SaveData: A[SignalRW[bool], Format.CONFIG_SIGNAL]
    StartAcq: SignalX
    Status: SignalR[str]
    StopAcq: SignalX
    TimePerPoint: A[SignalRW[int], Format.CONFIG_SIGNAL]