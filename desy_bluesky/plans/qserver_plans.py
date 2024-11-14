from ..beamline_config.beamline import *
from bluesky.utils import (
    separate_devices,
    all_safe_rewind,
    Msg,
    ensure_generator,
    short_uid as _short_uid,
)
import bluesky.plan_stubs as bps
from bluesky.plans import rel_scan as _rel_scan
from bluesky import preprocessors as bpp
import time
from ophyd.status import Status

from bluesky.plans import count as _count
from bluesky.plans import grid_scan as _grid_scan
from bluesky.plans import scan as _scan
from larch.xray import *

from bluesky.preprocessors import run_wrapper
from bluesky.plan_stubs import kickoff, sleep, wait, abs_set, stop
from bluesky_queueserver import parameter_annotation_decorator
import yaml
import numpy as np
import time

from ophyd.sim import motor
from beamlinetools.plans.dcm_optimization_parameters import get_cr2ropi_c2roll

from beamlinetools.beamline_config.base import bec

element_list = ["Fe", "Cu", "Pt", "Ni", "Al", "Au", "Ge", "P", "S", "Cl", "Ar", "He", "Ne", "Kr", "Cs", "Ba", "La",
                "Ce"]

# Define Detectors
try:
    from beamlinetools.beamline_config.beamline import mca, kth00, kth01, gas_system, reactor_cell, eiger, \
        secondary_qserver, dcm, sample_y, sample_z

    se_detectors = [gas_system.massflow_contr1, gas_system.massflow_contr2, gas_system.massflow_contr3,
                    gas_system.backpressure_contr1, reactor_cell.temperature_sam, reactor_cell.temperature_reg]
    xrd_detectors = [eiger, kth00, kth01]

    # Define Gasses
    with open("/opt/bluesky/beamlinetools/beamlinetools/beamline_config/gas_system.yaml") as stream:
        gas_system_config = yaml.safe_load(stream)

    gas_flows = gas_system_config['process_gasses']
    mfcs = gas_system_config['mass_flow_controllers']
    mfc_vals = list(mfcs.values())


    def _set_gas(mfc_tuple):

        yield from bps.mv(gas_system.massflow_contr1, mfc_tuple[0], gas_system.massflow_contr2, mfc_tuple[1],
                          gas_system.massflow_contr3, mfc_tuple[2], group='mfc_setting')
        yield from bps.wait(group='mfc_setting', timeout=180)
        print(f"successfully set the gas to {mfc_tuple}")


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "gas_sel": {
                "annotation": "gasses",
                "enums": {
                    "gasses": [f"{k} - > {mfc_vals[0]} = {v[0]}, {mfc_vals[1]} = {v[1]}, {mfc_vals[2]} = {v[2]}" for
                               k, v in gas_flows.items()]},
                "convert_device_names": False,
            },
            "pressure": {
                "default": 1.5,
                "min": 0.0,
                "max": 50,
                "step": 0.1,
            },
            "ramp_rate": {
                "default": 0.0,
                "min": 0.0,
                "max": 100,
                "step": 0.1,
            }
        }
    })
    def set_pressure(gas_sel, pressure: float = 1.5, ramp_rate: float = 0.0, interval: int = 1, md=None):

        """
        This plan will set gas back pressure and wait there for a given amount of time

        A delay of "interval" can be set between triggers

        Parameters
        ------------

        pressure : float
            back pressure
        interval : int
            seconds between triggers after an acquisition has finished
        md : dict
            A dictionary of additional metadata

        -------

        """
        _md = {'detectors': [det.name for det in se_detectors],
               'use_unix_epoch': True,
               'plan_name': 'set_pressure',
               'hints': {}
               }
        _md.update(md or {})
        _md['hints'].setdefault('dimensions', [(('time',), 'primary')])

        # Set the Gas

        @bpp.run_decorator(md=_md)
        def inner_plan():
            selected_gas_name = gas_sel.split()[0]
            # Set the Gas
            print(f"Setting the gas to {selected_gas_name} -> {gas_flows[selected_gas_name]}")
            yield from _set_gas(gas_flows[str(selected_gas_name)])

            yield from bps.abs_set(gas_system.backpressure_contr1.ramp, float(ramp_rate), wait=True)
            # Set the pressure
            print(f"Starting to change the pressure to {pressure}")
            pressure_complete_status = yield Msg('set', gas_system.backpressure_contr1, pressure)

            # Now stay here until the pressure is set
            while not pressure_complete_status.done:
                yield from bps.one_shot(se_detectors)  # triggers and reads everything in the detectors list
                yield from bps.checkpoint()
                yield from bps.sleep(interval)
            yield from bps.one_shot(se_detectors)

        return (yield from inner_plan())


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {

            "gas_sel": {
                "annotation": "gasses",
                "enums": {
                    "gasses": [f"{k} - > {mfc_vals[0]} = {v[0]}, {mfc_vals[1]} = {v[1]}, {mfc_vals[2]} = {v[2]}" for
                               k, v in gas_flows.items()]},
                "convert_device_names": False,
            },
            "temp_setpoint": {
                "default": 30,
                "min": 0.0,
                "max": 800,
                "step": 0.1,
            },
            "temp_ramp": {
                "default": 0.1,
                "min": 0.1,
                "max": 100,
                "step": 0.1,
            },
            "plans": {
                "annotation": "typing.List[__PLAN__]",
            },

        }
    })
    def ramp(gas_sel, temp_setpoint: float = 30, temp_ramp: float = 0.1, interval: int = 1, plans: list = [], md=None):

        """
        This plan will set gas mfc and temperature controllers and wait for
        the temperature to reach a required value "temp_setpoint"

        Once the temperature has been set, it will be held for "dwell" seconds
        During this time the eiger will be triggered as before

        Parameters
        ------------
        gas_sel: string
            The g as to be selected ('N2', 'H2', 'CO')
        temp_setpoint : float
            temperature to be reached. Until this temperature is reached, stay in this loop
        temp_ramp : float
            degrees/ min to ramp at. Can be positive or negative. If negative there is just no heat
        interval : int
            seconds between triggers after an acquisition has finished
        md : dict
            A dictionary of additional metadata


        """

        # Get the current temperature
        current_temp = yield from bps.rd(reactor_cell.temperature_reg)
        temp_gap = np.abs(current_temp - temp_setpoint)
        estimated_num_points = np.ceil(np.ceil(temp_gap / (temp_ramp / 60)) / interval)  # num_seconds

        _md = {'detectors': [det.name for det in se_detectors],
               'plan_args': {
                   'selected_gas': gas_sel.split()[0],
                   'gas_flows': gas_flows[gas_sel.split()[0]],
                   'temp_setpoint': temp_setpoint,
                   'temp_ramp': temp_ramp,
                   'sample_interval': interval,
               },
               'num_points': estimated_num_points,
               'current_temp': current_temp,
               'temp_gap': temp_gap,
               'legend_keys': [gas_sel.split()[0]],
               'use_unix_epoch': True,
               'plan_name': 'ramp',
               'hints': {}
               }
        _md.update(md or {})
        _md['hints'].setdefault('dimensions', [(('time',), 'primary')])

        @bpp.run_decorator(md=_md)
        def inner_plan():
            # Pass photon measurements to other qserver
            yield from abs_set(secondary_qserver.addPlan, plans)

            # Set the Gas
            selected_gas_name = gas_sel.split()[0]
            print(f"Setting the gas to {selected_gas_name} -> {gas_flows[selected_gas_name]}")
            yield from _set_gas(gas_flows[str(selected_gas_name)])

            # Set the temperature controller ramp rate
            yield from abs_set(reactor_cell.temperature_reg.ramp, temp_ramp, wait=True)

            # Set the temperature controller setpoint and keep track of the status
            complete_status = yield Msg('set', reactor_cell.temperature_reg, temp_setpoint)

            # Start photon measurements
            yield from (kickoff(secondary_qserver))

            # Since we have no readback from gas analysis on actual gas env,
            # the only thing we can do is wait for a known time
            print(f"Starting the acquire loop while temperature is changing")
            while not complete_status.done:
                yield from bps.one_shot(se_detectors)

                yield from bps.checkpoint()
                yield from bps.sleep(interval)

            yield from bps.one_shot(se_detectors)
            yield from stop(secondary_qserver)

        return (yield from inner_plan())


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "plans": {
                "annotation": "typing.List[__PLAN__]",
            },
            "gas_sel": {
                "annotation": "gasses",
                "enums": {
                    "gasses": [f"{k} - > {mfc_vals[0]} = {v[0]}, {mfc_vals[1]} = {v[1]}, {mfc_vals[2]} = {v[2]}" for
                               k, v in gas_flows.items()]},
                "convert_device_names": False,
            },
            "dwell": {
                "default": 60,
                "min": 0,
                "max": 600000,
                "step": 1,
            },
        }
    })
    def dwell(gas_sel, dwell: int = 60, interval: int = 1, plans: list = [], md=None):

        """
        This plan will set gas mfc and wait there for a given amount of time

        During this period the eiger will be triggered
        A delay of "interval" can be set between triggers

        Parameters
        ------------
        dwell : int
            seconds to dwell at this state for
        interval : int
            seconds between triggers after an acquisition has finished
        md : dict
            A dictionary of additional metadata

        -------

        """
        _md = {'plan_name': 'dwell',
               'detectors': [det.name for det in se_detectors],
               'plan_args': {
                   'selected_gas': gas_sel.split()[0],
                   'gas_flows': gas_flows[gas_sel.split()[0]],
                   'dwell_time': dwell,
                   'sample_interval': interval
               },
               'num_points': np.ceil(dwell / interval),
               'legend_keys': [gas_sel.split()[0]],
               'hints': {}
               }
        _md.update(md or {})
        _md['hints'].setdefault('dimensions', [(('time',), 'primary')])

        @bpp.run_decorator(md=_md)
        def inner_plan():
            yield from abs_set(secondary_qserver.addPlan, plans)
            yield from (kickoff(secondary_qserver))

            # Set the Gas
            selected_gas_name = gas_sel.split()[0]
            print(f"Setting the gas to {selected_gas_name} -> {gas_flows[selected_gas_name]}")
            yield from _set_gas(gas_flows[str(selected_gas_name)])

            t0 = time.time()

            while time.time() < t0 + dwell:
                yield from bps.one_shot(se_detectors)  # triggers and reads everything in the detectors list
                yield from bps.checkpoint()
                yield from bps.sleep(interval)

            yield from bps.one_shot(se_detectors)
            yield from stop(secondary_qserver)

        return (yield from inner_plan())


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "detectors": {
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
        }
    })
    def count_detectors(detectors, num: int, delay: float = 0.0, md: dict = None):
        yield from _count(detectors, num, delay=delay, md=md)


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "element": {
                "annotation": "elements",
                "enums": {"elements": element_list},
                "convert_device_names": False,
            },
            "edge": {
                "annotation": "edges",
                "enums": {"edges": ["K", "L1", "L2", "L3"]},
                "convert_device_names": False,
            },
        }
    })
    def move_dcm_edge(element, edge):

        edge_object = xray_edge(element, edge)
        yield from bps.mov(dcm.p.energy, edge_object.energy / 1000)


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "energy": {
                "default": 12,
                "min": 4,
                "max": 21,
                "step": 0.01,
            }
        }
    })
    def move_dcm_energy(energy: float = 12):

        yield from bps.mov(dcm.p.energy, energy)


    # if the eiger is connected then we should initialize it.
    eiger.initialize()  # only needs to be done once at the start of the session
    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "energy_KeV": {
                "default": 12,
                "min": 4,
                "max": 21,
                "step": 0.01,
            },
            "exposure_time_s": {
                "default": 1,
                "min": 0,
                "max": 1000,
                "step": 0.1
            },
            "num_images": {
                "default": 1,
                "min": 1,
                "max": 1000
            },

        }
    })
    def xrd(energy_KeV: float = 12, exposure_time_s: float = 1, num_images: int = 1, md: dict = None):

        _md = {'plan_name': 'xrd',
               'detectors': [det.name for det in se_detectors + xrd_detectors],
               'plan_args': {
                   'energy_KeV': energy_KeV,
                   'exposure_time_s': exposure_time_s,
                   'num_images': num_images,
               },
               'techniques': ['NXmonopd'],
               'num_points': np.ceil(num_images / exposure_time_s),
               'hints': {}
               }
        _md.update(md or {})

        # check if optimized positions for ropi and roll are available
        cr2ropi_position, cr2roll_position = get_cr2ropi_c2roll("diffraction")
        if cr2ropi_position is None or cr2roll_position is None:
            print(
                f"Optimized positions for c2ropi {cr2ropi_position} and/or c2roll{cr2roll_position} not found, using current positions.")
        else:
            yield from bps.mv(dcm.cr2ropi, cr2ropi_position, dcm.cr2roll, cr2roll_position)

        # move the energy of the dcm
        yield from bps.mov(dcm.p.energy, energy_KeV)
        yield from abs_set(eiger.cam.acquire_time, exposure_time_s)
        # yield from sleep(1) #We shouldn't need to do this...
        yield from _count(xrd_detectors + se_detectors, num=num_images, md=_md)


    from bluesky_queueserver import parameter_annotation_decorator


    @parameter_annotation_decorator({
        "parameters": {
            "num_points": {
                "default": 20,
                "min": 1,
                "max": 1000
            },
            "rel_start": {
                "default": -2,
                "min": -10000,
                "max": 100000,
                "step": 1.0,
            },
            "rel_stop": {
                "default": 2,
                "min": -10000,
                "max": 100000,
                "step": 1.0,
            }
        }
    })
    def align_sample_z(num_points: int = 20, rel_start: float = -2, rel_stop: float = 2):

        # move the energy of the dcm
        yield from _rel_scan([kth00], sample_z, rel_start, rel_stop, num_points)
        peaks_dict = bec.peaks
        max_pos = peaks_dict['cen']['kth00']
        yield from bps.mv(sample_z, max_pos)
        yield from _rel_scan([kth00], sample_z, -0.001, 0.001, 3)


    from bluesky.plan_stubs import sleep as _sleep


    @parameter_annotation_decorator({
        "parameters": {
            "period_s": {
                "default": 1.0,
                "min": 1,
                "max": 100000,
                "step": 1.0,
            },

        }
    })
    def sleep(period_s: int = 1):

        """
        This plan will sleep for period seconds.
        It is split into a loop of N sleep commands so that it can
        be paused with a deferred pause and it will stop within 1 second.

        arguments:

            period: int total period in seconds to sleep for
        """

        for i in range(period):
            yield from _sleep(period)
            yield from bps.checkpoint()
            print(f"There are {period - i} seconds remaining before next operation")

except Exception as e:
    print(e)
