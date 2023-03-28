import time

from epics import caget, caput
from haven.instrument.heater import CapillaryHeater


def test_capillary_device(ioc_ptc10):
    # Set up the device and ensure connections match the IOC we have
    device = CapillaryHeater("ptc10ioc:", name="capillary_heater")
    device.wait_for_connection()
    # Check for status objects checking temperature properly
    status = device.set(200)
    assert not status.done
    caput("ptc10ioc:2A:temperature", 200)
    new_temp = device.readback.get(use_monitor=False)
    assert new_temp == 200
    # assert status.done

