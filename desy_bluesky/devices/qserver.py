from ophyd.signal import Signal
from ophyd import Device
from ophyd import Component as Cpt
from ophyd.status import DeviceStatus
from bluesky_queueserver_api import BItem, BPlan
from ast import literal_eval

from bluesky_queueserver_api.zmq import REManagerAPI


class QserverDevice(Device):
    """
    The Device takes a queueserver ip and port and will use it to connect to the queueserver on kickoff.
    It behaves like a flyer where only the kickoff is relevant since to access the data you can
    just subscribe to the remote dispatcher of the queueserver. On Every kickoff the queue is cleared
    and the value of addPlan is readout.
    """

    addPlan = Cpt(Signal)

    def __init__(self, zmq_address, name=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self._client = None
        self._zmq_address = zmq_address
        self.kickoff_status = None

        while not self._client:
            self._client = REManagerAPI(zmq_control_addr=self._zmq_address)

    def kickoff(self):

        if self._client == None:
            raise Exception("qserver device secondary qserver not connected")

        qserver_status = self._client.status()
        if not qserver_status["worker_environment_exists"]:
            raise Exception("qserver device secondary qserver environment not open")

        self.stop()
        self._client.queue_clear()
        self._client.queue_mode_set(mode={"loop": True})
        # add the plans in addPlan to the queue. TODO add plans as batch
        plan = self.addPlan.get()
        if isinstance(plan, list):
            if isinstance(plan[0], str):
                plan = [literal_eval(item) for item in plan]
            self._client.item_add_batch(plan, user_group="primary")
        elif (
            isinstance(plan, BItem) or isinstance(plan, BPlan) or isinstance(plan, dict)
        ):
            self._client.item_add(plan, user_group="primary")
        else:
            raise TypeError(
                f"Found {type(plan)} in addPlan which is not a valid option to represent a plan for now."
            )

        status = self._client.queue_start()
        # return success if everything worked
        self.kickoff_status = DeviceStatus(self)
        self.kickoff_status._finished(success=status["success"])
        return self.kickoff_status

    # these functions are not needed for now. to get the data connect to the remote dispatcher of the queueserver
    def complete(self):
        pass

    def collect(self):
        pass

    def describe_collect(self):
        pass

    def pause(self):
        qserver_status = self._client.status()
        if qserver_status["re_state"] == "running":
            try:
                status = self._client.re_pause("deferred")
                self._client.wait_for_idle_or_paused(
                    timeout=60 * 16
                )  # wait for the mono to potentially move for 15 mins!
                return status
            except Exception as e:
                print(f"Failed to pause RE {e}")
                # We know we can call stop from any state, so this is a safe option
                self.stop()
        elif qserver_status["re_state"] == "idle":
            # We know we can call stop from any state, so this is a safe option. This hadles the case where we are between two plans
            self.stop()

    def resume(self):
        qserver_status = self._client.status()
        if qserver_status["re_state"] == "paused":
            try:
                status = self._client.re_resume()
                return status
            except Exception as e:
                print(f"Failed to resume RE {e}")
        elif qserver_status["manager_state"] == "idle":
            status = self._client.queue_start()
            return status

    def stop(self):
        # Stop the RE in the secondary qserver if it is running

        # First we check if the queue is running and has not been stopped (idle) or paused by the user(paused)
        qserver_status = self._client.status()
        if qserver_status["manager_state"] == "executing_queue":
            self._client.queue_stop()  # stops the queue to stop any next plan from running. This is important because if we just transitioned from running to pa

        # RE state is either running, paused or idle

        # if running we need to pause first
        qserver_status = self._client.status()
        if qserver_status["re_state"] == "running":
            try:
                self._client.re_pause("deferred")  # equivalent to (ctrl + c x2)

            except Exception as e:
                print(f"Could not pause running plan. Probably it was already idle {e}")

        # now we know we are either idle or paused. If paused, we need to stop the RE
        self._client.wait_for_idle_or_paused(
            timeout=60 * 16
        )  # wait for the mono to potentially move for 15 mins!
        qserver_status = self._client.status()
        if qserver_status["manager_state"] == "paused":
            self._client.re_stop()  # equivalent to (RE.stop())
            self._client.wait_for_idle(
                timeout=60
            )  # this one doesn'y need to be as long because we know the RE is already paused.

        # now the RE state is idle and the queue is stopped
