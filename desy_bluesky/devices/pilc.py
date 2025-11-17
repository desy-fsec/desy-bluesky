from abc import abstractmethod
from typing import Optional, TypeVar
from ophyd_async.core import SignalR, SignalRW, Device, DeviceVector, StandardReadable
from ophyd_async.tango.core import tango_signal_rw, tango_signal_r, TangoDevice
from bluesky.protocols import Readable, Stoppable, Movable

T = TypeVar("T")


class PiLCPort(Readable, Device):
    """An abstract class defining what all PiLC modules have in common in tango

    Members:
    --------

    port_name:
        A signal defining the name of a port in Tango
        this name is also displayed on the PiLC itself
    type:
        A string defining the exact type of a port
        possible values (non exhaustive list):
            IOt, IOnt, ADC, DAC, Temperature, VIO
    """

    port_name: SignalRW = None

    type: str = None

    @abstractmethod
    def __init__(self): ...

    @abstractmethod
    async def read(self):
        """read the value of the port"""

    @abstractmethod
    async def describe(self):
        """describe the value the a port"""

    @abstractmethod
    async def get_value(self):
        """get the current value of the port"""

    async def configure(self, config: dict):
        """configure the port. Note: Currently not functional with bluesky and ophyd_async
        config is a dict with values:
            name: str -> the name of the port
        """
        old = await self.read_configuration()
        if "name" in config:
            await self.port_name.set(config["name"])
        new = await self.read_configuration()

        return (old, new)

    async def read_configuration(self):
        """read the configuration, see PiLCPort.configure for more info"""
        return await self.port_name.read()


class PiLCIO(PiLCPort):
    """A class for storing the needed signals to run a PiLC IO module

    for more info see: https://confluence.desy.de/display/PILC/PiLC+ZMQ+GP

    Members:
    --------

    direction:
        A signal storing a boolean for the input or output mode of a module.
        False = Input       True = Output
    resistor:
        A signal storing an integer for the resistor to be used.
        0 = 50Ohm           1 = 1kOhm
        Note: only available on TTL cards
    level:
        A signal storing an integer for the Level of a NIM TTL card.
        0 = TTL             1 = NIM
        Note: only available on NIM TTL cards
    status:
        A signal storing a boolean for the current value of the card.
        False = Low         True = High
        Note: only settable when operation = 0
    operation:
        A signal storing an integer specifying the current mode of operation.
        0 = Manual      1 = OR      2 = AND     3 = Clock output
    connections (connect in tango):
        A signal storing an integer that either acts as a bit field
        specifying what outputs are connected (ie 3 -> ports 1 and 2) or
        what clock output is connected. The former when operation = 1 or 2 and
        the latter when operation = 3
        Note: not functional in manual mode (operation = 0)
    invers:
        A signal storing a boolean specifying if the output should be inverted.
        False = normal      True = inverted
    dop:
        A signal storing a boolean specifying if the output should
        be a pulse on a rising edge input for time,
        or if the output should delay for time.
        False = Delay       True = Pulse
    time:
        A signal storing a float specifying the delay or pulse width for the dop value.
        See the PiLC docs for more info. minimum: 80ns, unit: us
    counter_enable:
        A signal storing a boolean stating weather the counter is enabled.
    counter_reset:
        A signal for reseting the counter.
    counter_value:
        A readonly signal for reading the value of the counter
        (triggered on rising edge when enabled).

    See PiLCPort for more info on the "type" and "port_name" members
    """

    direction: SignalRW
    resistor: Optional[SignalRW] = None
    level: Optional[SignalRW] = None
    status: SignalRW
    operation: SignalRW
    connections: SignalRW
    invers: SignalRW
    dop: SignalRW
    time: SignalRW
    counter_enable: SignalRW
    counter_reset: SignalRW
    counter_value: SignalR

    def __init__(self):
        return

    async def read(self):
        """read the "status" value of the IO port"""
        return {**await self.status.read(), **await self.counter_value.read()}

    async def describe(self):
        """describe the status value of the IO port"""
        return self.status.describe()

    async def get_value(self):
        """reads the counter value of the port"""
        return await self.counter_value.get_value()

    async def set(self, value):
        """set the status value of the IO port (only available if operation = 0)"""
        return await self.status.set(value)

    async def read_configuration(self):
        pre = {}
        if self.type == "IOt":
            pre |= await self.resistor.read()
        if self.type == "IOnt":
            pre |= await self.level.read()

        return {
            **pre,
            **await self.direction.read(),
            **await self.operation.read(),
            **await self.connections.read(),
            **await self.invers.read(),
            **await self.dop.read(),
            **await self.time.read(),
            **await self.counter_enable.read(),
            **await self.port_name.read(),
        }

    async def configure(self, config: dict):
        """configure the port. Note: Currently not functional with bluesky and ophyd_async
        config is a dict with the members:
            direction
            resistor
            level
            operation
            connections
            invers
            dop
            time
            counter_enable
        the functions of these configurable values is the same as defined in the docstring of PiLCIO
        """
        old = await self.read_configuration()
        if "direction" in config:
            await self.direction.set(config["direction"])
        if "resistor" in config and self.resistor:
            await self.resistor.set(config["resistor"])
        if "level" in config and self.level:
            await self.level.set(config["level"])
        if "operation" in config:
            await self.operation.set(config["operation"])
        if "connections" in config:
            await self.connections.set(config["connections"])
        if "invers" in config:
            await self.invers.set(config["invers"])
        if "dop" in config:
            await self.dop.set(config["dop"])
        if "time" in config:
            await self.time.set(config["time"])
        if "counter_enable" in config:
            await self.counter_enable.set(config["counter_enable"])
        if "name" in config:
            await self.port_name.set(config["name"])
        new = await self.read_configuration()
        return (old, new)


class PiLCReadable(PiLCPort):
    """
    A class for a PiLCPort that is read only
    """

    def __init__(self):
        return

    value: SignalR

    async def read(self):
        return await self.value.read()

    async def describe(self):
        return await self.value.describe()

    async def get_value(self):
        """reads thevalue of the port"""
        return await self.value.get_value()


class PiLCMovable(PiLCReadable, Movable, Stoppable):
    """A subclass of a PiLCReadable with methods for stopping and setting a connected
    device value to set when stopping can be modified with the stopValue property
    """

    stopValue = 0
    value: SignalRW

    def set(self, value):
        """set the value of the port"""
        return self.value.set(value)

    def stop(self, success=True):
        """set the value of the port to the stop value (default 0)"""
        return self.value.set(self.stopValue)


# --------------------------------------------------------------------
class PiLC(TangoDevice, StandardReadable):
    """
    Class Defining a Tango device for the PiLC with configurable output cards

    Members:
    --------
    ports:
        A dict containing the PiLC port classes for operating ports
        Note: ports are numbered 1 - 16 and NOT 0 - 15. Some ports may
        not exist, as some cards require more than 1 port
    aliases:
        A dict containing the current aliases to ports. see the aliases
        parameter of __init__'s docstring for more info
    trl:
        The tango address of the PiLC (created in __init__)
    readablemodules, movablemodules, portconfig:
        See PiLC.__init__'s docstring (created in __init__)

    Ports also can also be accessed with the same name as in tango but lowercase,
    after connecting to tango via the connect function
    example: /IO_DIR_2 -> pilc.io_dir_2
    """

    # for consistancy with tango and the PiLC ports starts counting at 1
    ports: DeviceVector
    clk1: SignalRW
    clk2: SignalRW
    clk3: SignalRW
    clk4: SignalRW
    _movable: list
    _readable: list

    # --------------------------------------------------------------------
    def __init__(
        self,
        trl: str,
        name: str = "",
        port_config: Optional[dict] = None,
        readable_module_types: Optional[list] = None,
        movable_module_types: Optional[list] = None,
        aliases: Optional[dict] = None,
    ) -> None:
        """
        Arguments:
        ----------

        port_config:
            A dict specifying how the ports are layed out example:
                exampleport_configs : dict = {
                    1  :'IO',    2  : 'IO',    3  :'IO',    4  : 'IO',
                    5  :'IO',    6  : 'IO',    7  :'IO',    8  : 'IO',
                    9  :'ADC',   10 : 'ADC',   11 :'DAC',   12 : 'DAC',
                                 14 : 'Temp',               16 : 'VIO',
                }
        readableModules:
            A list specifying wich modules have only one attribute in the style of:
                {Modulename}_{Number} (eg. ["ADC", "Temp"])
        movableModules:
            Same as readableModules but the modules can be written to. (eg. ["DAC"])
        aliases:
            a dict containing strings as keys and ints as values,
            to define aliases wich can be accessed either with the [] or . syntax
            example: aliases = {"adc2":10, "led":11}
            would mean that: pilc.adc2 or pilc["adc2"] -> pilc.ports[10]
            and pilc.led or pilc["led"] -> pilc.ports[11].
            Note: the name does not change in bluesky, so reading from pilc.led will not result
            in a column for pilc-led but instead for pilc-led_11
        """
        self.trl = trl

        self.ports = DeviceVector()

        self.port_config = port_config or None
        self.readable_module_types = readable_module_types or ["ADC", "Temp"]
        self.movable_module_types = movable_module_types or ["DAC"]
        self.aliases = aliases or {}

        TangoDevice.__init__(self, trl, name=name)

    # --------------------------------------------------------------------
    def _register_signal_rw(
        self,
        datatype: type[T],
        prefix_upper: str,
        num: int,
        attr_name: Optional[str] = None,
    ) -> tango_signal_rw:
        """Register a readable and writable signal for a PiLC module

        Parameters:
        -----------

        datatype:
            The type the signal will have
        prefix_upper:
            The tango prefix of the module
        num:
            The number of the module
        attr_name:
            The name of the attribute to be registered
        prefix_lower:
            The prefix used for the internal variable, if the lowercase prefix_upper
            does not fit requirements
        """
        name = ""
        if attr_name is not None:
            name = attr_name + "_"
        ret = tango_signal_rw(
            datatype, f"/{prefix_upper}_{name}{num}", device_proxy=self.proxy
        )
        return ret

    # --------------------------------------------------------------------
    def _register_signal_r(
        self,
        datatype: type[T],
        prefix_upper: str,
        num: int,
        attr_name: Optional[str] = None,
    ) -> tango_signal_rw:
        """Register a read only signal for a PiLC module

        Parameters:
        -----------

        datatype:
            The type the signal will have
        prefix_upper:
            The tango prefix of the module
        num:
            The number of the module
        attr_name:
            The name of the attribute to be registered
        prefix_lower:
            The prefix used for the internal variable, if the lowercase prefix_upper
            does not fit requirements
        """
        name = ""
        if attr_name is not None:
            name = attr_name + "_"
        ret = tango_signal_r(
            datatype, f"/{prefix_upper}_{name}{num}", device_proxy=self.proxy
        )
        return ret

    # --------------------------------------------------------------------
    def register_signals(self) -> None:
        """Function to register signals"""

        # register clock signals
        self.clk1 = tango_signal_rw(float, "/Clk_1", device_proxy=self.proxy)
        self.clk2 = tango_signal_rw(float, "/Clk_2", device_proxy=self.proxy)
        self.clk3 = tango_signal_rw(float, "/Clk_3", device_proxy=self.proxy)
        self.clk4 = tango_signal_rw(float, "/Clk_4", device_proxy=self.proxy)

        self._movable: list = [self.clk1, self.clk2, self.clk3, self.clk4]
        self._readable: list = []

        # attrlist probably won't change while in the for loop. save it outside for
        # performance
        attrlist = self.proxy.get_attribute_list()

        def has_port(port_type: list, num: int, port_list: list, check: str = ""):
            """returns the type name of the port found, if none was found, return
            false"""
            for port_name in port_type:
                if f"{port_name}_{check}{num}" in port_list:
                    return port_name
            return False

        def create_readable(prefix: str, num: int):
            """create a readable port where the tango trl is in the style of
            {prefix}_{num}"""
            mod = PiLCReadable()
            mod.value = self._register_signal_r(float, prefix, num)
            self.ports[num] = mod
            self._readable += [mod.value]

        def create_movable(prefix: str, num: int):
            """create a movable port where the tango trl is in the style of
            {prefix}_{num}"""
            mod = PiLCMovable()
            mod.value = self._register_signal_rw(float, prefix, num)
            self.ports[num] = mod
            self._readable += [mod.value]

        def create_io(prefix: str, num: int):
            """create an io port where the tango trl is in the style of
            {prefix}_{property}_{num} (property is not changable outside of function)"""
            io = PiLCIO()

            io.direction = self._register_signal_rw(bool, prefix, num, "DIR")

            # Decypher between TTL, NIM TTL, and VIO
            # TTL has a resistor attribute, NIM TTL has a level attribute,
            # virtual has none of these attributes
            if f"IO_Resistor_{str(num)}" in attrlist:
                # The module is a TTL card. Resistor is configurable
                io.type = "IOt"
                io.resistor = self._register_signal_rw(int, "IO", num, "Resistor")
            elif f"IO_Level_{str(num)}" in attrlist:
                # The module is a NIM TTL card. Level is configurable
                io.type = "IOnt"
                io.level = self._register_signal_rw(int, "IO", num, "Level")
            else:
                io.type = "VIO"

            io.status = self._register_signal_rw(int, prefix, num, "Status")
            io.operation = self._register_signal_rw(int, prefix, num, "Operation")
            io.connections = self._register_signal_rw(int, prefix, num, "Connect")
            io.invers = self._register_signal_rw(bool, prefix, num, "Invers")
            io.dop = self._register_signal_rw(bool, prefix, num, "DOP")
            io.time = self._register_signal_rw(float, prefix, num, "Time")
            io.counter_enable = self._register_signal_rw(bool, prefix, num, "CTR_En")
            io.counter_reset = self._register_signal_rw(bool, prefix, num, "CTR_RST")
            io.counter_value = self._register_signal_r(int, prefix, num, "CTR_VAL")

            # add io to ports
            self.ports[num] = io

            # add the values to the list of to be registered values
            self._movable += [
                io.direction,
                io.status,
                io.operation,
                io.connections,
                io.invers,
                io.dop,
                io.time,
                io.counter_enable,
            ]

            # resistor or level may not exist so check before appending
            if io.resistor is not None:
                self._movable.append(io.resistor)
            if io.level is not None:
                self._movable.append(io.level)

            self._readable += [io.counter_value]

        if self.port_config is not None:
            for key in self.port_config:
                if self.port_config[key] in self.readable_module_types:
                    create_readable(self.port_config[key], key)
                elif self.port_config[key] in self.movable_module_types:
                    create_movable(self.port_config[key], key)
                elif self.port_config[key] in ["IO", "VIO"]:
                    create_io(self.port_config[key], key)
                else:
                    # the module is not known or misspelled
                    print(f"unknown module: '{self.port_config[key]}'")
                # add name for module if it exists
                if key in self.ports and hasattr(self.ports[key], "name"):
                    self.ports[key].port_name = self._register_signal_rw(
                        str, "Name", key
                    )
                    self._movable.append(self.ports[key].port_name)
        else:
            for i in range(1, 17):
                readable_name = has_port(self.readable_module_types, i, attrlist)
                movable_name = has_port(self.movable_module_types, i, attrlist)
                io_name = has_port(["IO", "VIO"], i, attrlist, "DIR_")
                if readable_name:
                    create_readable(readable_name, i)
                elif movable_name:
                    create_movable(movable_name, i)
                elif io_name:
                    create_io(io_name, i)
                # else:
                #     print(f"nonexistant port {i}, or in use by another module")
                # add name for module if it exists
                if i in self.ports and hasattr(self.ports[i], "name"):
                    self.ports[i].port_name = self._register_signal_rw(str, "Name", i)
                    self._movable.append(self.ports[i].port_name)

        # register all signals
        self.set_readable_signals(read=self._readable, config=self._movable)
        self.set_name(self.name)

    def __getitem__(self, name: str):
        """function to make aliases work with the [] syntax"""
        return self.ports[self.aliases[name]]

    def __getattribute__(self, name: str):
        """function to make aliases work with the . syntax, while keeping other
        values intact"""
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.__getitem__(name)
