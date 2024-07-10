from ophyd_async.core import SignalR, SignalRW, T
from bluesky.protocols import Readable, Stoppable, Movable

from ophyd_async.tango import(
    TangoReadableDevice,
    tango_signal_rw,
    tango_signal_r
)

class PiLCPort(Readable):
    """A class defining what all PiLC modules have in common in tango

    Members:
    --------

    name:
        A signal defining the name of a port in Tango
    type:
        A string defining the exact type of a port
        possible values (non exhaustive list):
            IOt, IOnt, ADC, DAC, Temperature, VIO
    """
    name: SignalRW = None

    type: str = None 

    def read(self):
        return self.name.read()
    def describe(self):
        return self.name.describe()

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
    connect:
        A signal storing an integer that either acts as a bit field
        specifying what outputs are connected (ie 3 -> ports 1 and 2) or
        what clock output is connected. The former when operation = 1 or 2 and
        the latter when operation = 3
        Note: not functional in manual mode (operation = 0)
    invers:
        A signal storing a boolean specifying if the output should be inverted.
        False = normal      True = inverted
    dop:
        A signal storing a boolean specifying if the output should be a pulse on a rising edge input for time,
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
        A readonly signal for reading the value of the counter (triggered on rising edge when enabled).
    
    See PiLCPort for more info on the "type" and "name" members
    """
    direction: SignalRW
    resistor: SignalRW
    level: SignalRW
    status: SignalRW
    operation: SignalRW
    connect: SignalRW
    invers: SignalRW
    dop: SignalRW
    time: SignalRW
    counter_enable: SignalRW
    counter_reset: SignalRW
    counter_value: SignalR
    def read(self):
        return self.status.read()
    def describe(self):
        return self.status.describe()
    def set(self, value):
        return self.status.set(value)

class PiLCReadable(PiLCPort):
    value: SignalR
    def read(self):
        return self.value.read()
    def describe(self):
        return self.value.describe()

class PiLCMovable(PiLCReadable, Movable, Stoppable):
    """A subclass of a PiLCReadable with methods for stopping and setting a connected device
    value to set when stopping can be modified with the stopValue property
    """
    stopValue = 0
    value: SignalRW
    def set(self, value):
        return self.value.set(value)
    def stop(self, success=True):
        return self.value.set(self.stopValue)

# --------------------------------------------------------------------
class PiLC(TangoReadableDevice):
    """
    Class Defining a TangoReadableDevice for the PiLC with configurable output cards
    
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
    ports:dict = {}
    aliases:dict = {}

    # --------------------------------------------------------------------
    def __init__(
            self,
            trl: str,
            name:str="pilc",
            portconfig:dict=None,
            readableModules:list = None,
            movableModules:list = None,
            aliases:dict = None
            ) -> None:
        """
        Parameters:
        -----------
        
        portconfig:
            A dict specifying how the ports are layed out example:
                exampleportconfigs : dict = {
                    1  :'IO',    2  : 'IO',    3  :'IO',    4  : 'IO',
                    5  :'IO',    6  : 'IO',    7  :'IO',    8  : 'IO',
                    9  :'ADC',   10 : 'ADC',   11 :'DAC',   12 : 'DAC',
                                 14 : 'Temp',               16 : 'VIO',
                }
        readableModules:
            A list specifying wich modules have only one attribute in the style of: {Modulename}_{Number} (eg. ["ADC", "Temp"])
        movableModules:
            Same as readableModules but the modules can be written to. (eg. ["DAC"])
        aliases:
            a dict containing strings as keys and ints as values, to define aliases wich can be accessed either with the [] or . syntax
            example: aliases = {"adc2":10, "led":11}
            would mean that: pilc.adc2 or pilc["adc2"] -> pilc.ports[10]   and    pilc.led or pilc["led"] -> pilc.ports[11]
        """
        self.trl=trl

        self.portconfig = portconfig or None
        self.readableModules = readableModules or ["ADC", "Temp"]
        self.movableModules = movableModules or ["DAC"]
        self.aliases = aliases or {}

        TangoReadableDevice.__init__(self, trl, name)
    
    # --------------------------------------------------------------------
    def _register_signal_rw(self, datatype:type[T], prefixUpper:str, num:int, attrname:str = None, prefixLower:str = None) -> tango_signal_rw:
        """Register a readable and writable signal for a PiLC module

        Parameters:
        -----------

        datatype:
            The type the signal will have
        prefixUpper:
            The tango prefix of the module
        num: 
            The number of the module
        attrname:
            The name of the attribute to be registered
        prefixLower:
            The prefix used for the internal variable, if the lowercase prefixUpper does not fit requirements
        """
        name=""
        if(attrname != None):
            name = attrname + '_'
        ret = tango_signal_rw(datatype, f"/{prefixUpper}_{name}{num}", device_proxy=self.proxy)
        setattr(self, f"{prefixLower or prefixUpper.lower()}_{name.lower()}{num}", ret)
        return ret
    
    # --------------------------------------------------------------------
    def _register_signal_r(self, datatype:type[T], prefixUpper:str, num:int, attrname:str = None, prefixLower:str = None) -> tango_signal_rw:
        """Register a read only signal for a PiLC module

        Parameters:
        -----------

        datatype:
            The type the signal will have
        prefixUpper:
            The tango prefix of the module
        num: 
            The number of the module
        attrname:
            The name of the attribute to be registered
        prefixLower:
            The prefix used for the internal variable, if the lowercase prefixUpper does not fit requirements
        """
        name=""
        if(attrname != None):
            name = attrname + '_'
        ret = tango_signal_r(datatype, f"/{prefixUpper}_{name}{num}", device_proxy=self.proxy)
        setattr(self, f"{prefixLower or prefixUpper.lower()}_{name.lower()}{num}", ret)
        return ret

    # --------------------------------------------------------------------
    def register_signals(self) -> None:
        """Function to register signals
        """

        # register clock signals
        self.clk1 = tango_signal_rw(float, '/Clk_1', device_proxy=self.proxy)
        self.clk2 = tango_signal_rw(float, '/Clk_2', device_proxy=self.proxy)
        self.clk3 = tango_signal_rw(float, '/Clk_3', device_proxy=self.proxy)
        self.clk4 = tango_signal_rw(float, '/Clk_4', device_proxy=self.proxy)

        self._configurable:list = [self.clk1, self.clk2, self.clk3, self.clk4]
        self._readable:list = []
        
        # attrlist probably won't change while in the for loop. save it outside for performance
        attrlist = self.proxy.get_attribute_list()

        def hasPort(portType:list, num:int, portList:list, check:str=""):
            """returns the type name of the port found, if none was found, return false"""
            for portName in portType:
                if(f"{portName}_{check}{num}" in portList):
                    return portName
            return False

        def createReadable(prefix:str, num:int):
            """create a readable port where the tango trl is in the style of {prefix}_{num}"""
            mod = PiLCReadable()
            mod.value = self._register_signal_r(float, prefix, num)
            self.ports[num] = mod
            self._readable+=[mod.value]

        def createMovable(prefix:str, num:int):
            """create a movable port where the tango trl is in the style of {prefix}_{num}"""
            mod = PiLCMovable()
            mod.value = self._register_signal_rw(float, prefix, num)
            self.ports[num] = mod
            self._readable+=[mod.value]

        def createIO(prefix:str, num:int):
            """create an io port where the tango trl is in the style of {prefix}_{property}_{num} (property is not changable outside of function)"""
            io = PiLCIO()

            io.direction = self._register_signal_rw(bool, prefix, num, "DIR")

            # Decypher between TTL, NIM TTL, and VIO
            # TTL has a resistor attribute, NIM TTL has a level attribute,
            # virtual has none of these attributes
            if(f"IO_Resistor_{str(num)}" in attrlist):
                # The module is a TTL card. Resistor is configurable
                io.type = "IOt"
                io.resistor = self._register_signal_rw(int, "IO", num, "Resistor")
            elif(f"IO_Level_{str(num)}" in attrlist):
                # The module is a NIM TTL card. Level is configurable
                io.type = "IOnt"
                io.level = self._register_signal_rw(int, "IO", num, "Level")
            else:
                io.type = "VIO"

            io.status = self._register_signal_rw(int, prefix, num, "Status")
            io.operation = self._register_signal_rw(int, prefix, num, "Operation")
            io.connect = self._register_signal_rw(int, prefix, num, "Connect")
            io.invers = self._register_signal_rw(bool, prefix, num, "Invers")
            io.dop = self._register_signal_rw(bool, prefix, num, "DOP")
            io.time = self._register_signal_rw(float, prefix, num, "Time")
            io.counter_enable = self._register_signal_rw(bool, prefix, num, "CTR_En")
            io.counter_reset = self._register_signal_rw(bool, prefix, num, "CTR_RST")
            io.counter_value = self._register_signal_r(int, prefix, num, "CTR_VAL")

            # add io to ports
            self.ports[num] = io

            # add the values to the list of to be registered values
            self._configurable+=[io.direction, io.status, io.operation, io.connect, io.invers, io.dop, io.time, io.counter_enable]

            # resistor or level may not exist so check before appending
            if(hasattr(io, "resistor")):
                self._configurable.append(io.resistor)
            if(hasattr(io, "level")):
                self._configurable.append(io.level)

            self._readable+=[io.counter_value]

        if(self.portconfig != None): 
            for key in self.portconfig:
                if(self.portconfig[key] in self.readableModules):
                    createReadable(self.portconfig[key], key)
                elif(self.portconfig[key] in self.movableModules):
                    createMovable(self.portconfig[key], key)
                elif(self.portconfig[key] in ["IO", "VIO"]):
                    createIO(self.portconfig[key], key)
                else:
                    # the module is not known or misspelled
                    print(f"unknown module: '{self.portconfig[key]}'")
                # add name for module if it exists
                if(key in self.ports and hasattr(self.ports[key], "name")):
                    self.ports[key].name = self._register_signal_rw(str, "Name", key)
                    self._configurable.append(self.ports[key].name)
        else:
            for i in range(1,17):
                readableName = hasPort(self.readableModules, i, attrlist)
                movableName = hasPort(self.movableModules, i, attrlist)
                IOName = hasPort(["IO", "VIO"], i, attrlist, "DIR_")
                if(readableName != False):
                    createReadable(readableName, i)
                elif(movableName != False):
                    createMovable(movableName, i)
                elif(IOName != False):
                    createIO(IOName, i)
                # else:
                #     print(f"nonexistant port {i}, or in use by another module")
                # add name for module if it exists
                if(i in self.ports and hasattr(self.ports[i], "name")):
                    self.ports[i].name = self._register_signal_rw(str, "Name", i)
                    self._configurable.append(self.ports[i].name)
                
                
        # register all signals and set names of child devices
        self.set_readable_signals(read=self._readable, config=self._configurable)
        self.set_name(self.name)
    
    def __getitem__(self, name:str):
        """function to make aliases work with the [] syntax"""
        return self.ports[self.aliases[name]]

    def __getattribute__(self, name: str):
        """function to make aliases work with the . syntax, while keeping other
        values intact"""
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.__getitem__(name)
