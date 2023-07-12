from unittest import mock

import pytest
from ophyd.sim import instantiate_fake_device

from haven import registry, exceptions
from haven.instrument import stage


def test_stage_init():
    stage_ = stage.XYStage(
        "motor_ioc", pv_vert=":m1", pv_horiz=":m2", labels={"stages"}, name="aerotech"
    )
    assert stage_.name == "aerotech"
    assert stage_.vert.name == "aerotech_vert"
    # Check registry of the stage and the individiual motors
    registry.clear()
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="motors")
    with pytest.raises(exceptions.ComponentNotFound):
        registry.findall(label="stages")
    registry.register(stage_)
    assert len(list(registry.findall(label="motors"))) == 2
    assert len(list(registry.findall(label="stages"))) == 1


def test_load_aerotech_stage():
    stage.load_stages()
    # Make sure these are findable
    stage_ = registry.find(name="Aerotech")
    assert stage_ is not None
    vert_ = registry.find(name="Aerotech_vert")
    assert vert_ is not None


def test_aerotech_flyer():
    aeroflyer = stage.AerotechFlyer(name="aerotech_flyer", axis="@0", encoder=6)
    assert aeroflyer is not None


def test_aerotech_stage():
    fly_stage = stage.AerotechFlyStage(
        "motor_ioc", pv_vert=":m1", pv_horiz=":m2", labels={"stages"}, name="aerotech"
    )
    assert fly_stage is not None
    assert fly_stage.asyn.ascii_output.pvname == "motor_ioc:asynEns.AOUT"


def test_aerotech_fly_params():
    flyer = instantiate_fake_device(
        stage.AerotechFlyer, name="flyer", axis="@0", encoder=0
    )
    # Set some example positions
    flyer.motor_egu.set("micron").wait()
    flyer.encoder_resolution.set(0.001).wait()  # µm
    flyer.start_position.set(20).wait()  # µm
    flyer.end_position.set(10).wait()  # µm
    flyer.step_size.set(0.1).wait()  # µm
    flyer.dwell_time.set(1).wait()  # sec
    # Check that the fly-scan parameters were calculated correctly
    assert flyer.slew_speed.get(use_monitor=False) == 0.1  # µm/sec
    assert flyer.taxi_start.get(use_monitor=False) == 20.5  # µm
    assert flyer.taxi_end.get(use_monitor=False) == 9.5  # µm
    assert flyer.encoder_step_size.get(use_monitor=False) == 100
    assert flyer.encoder_window_start.get(use_monitor=False) == 5
    assert flyer.encoder_window_end.get(use_monitor=False) == -1005


def test_enable_pso():
    flyer = stage.AerotechFlyer(name="flyer", axis="@0", encoder=6)
    flyer.send_command = mock.MagicMock()
    # Set up scan parameters
    flyer.encoder_step_size.set(50).wait()  # In encoder counts
    flyer.encoder_window_start.set(-5).wait()  # In encoder counts
    flyer.encoder_window_end.set(10000).wait()  # In encoder counts
    # Check that commands are sent to set up the controller for flying
    flyer.enable_pso()
    assert flyer.send_command.called
    commands = [c.args[0] for c in flyer.send_command.call_args_list]
    assert commands == [
        "PSOCONTROL @0 RESET",
        "PSOOUTPUT @0 CONTROL 1",
        "PSOPULSE @0 TIME 20,10",
        "PSOOUTPUT @0 PULSE WINDOW MASK",
        "PSOTRACK @0 INPUT 6",
        "PSODISTANCE @0 FIXED 50",
        "PSOWINDOW @0 1 INPUT 6",
        "PSOWINDOW @0 1 RANGE -5,10000",
    ]


def test_arm_pso():
    flyer = stage.AerotechFlyer(name="flyer", axis="@0", encoder=6)
    flyer.send_command = mock.MagicMock()
    assert not flyer.send_command.called
    flyer.arm_pso()
    assert flyer.send_command.called
    command = flyer.send_command.call_args.args[0]
    assert command == "PSOCONTROL @0 ARM"
