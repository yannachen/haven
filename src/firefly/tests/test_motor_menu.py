import pytest
from ophyd.sim import make_fake_device

from firefly.main_window import FireflyMainWindow
from haven.instrument import motor


@pytest.fixture
def fake_motors(sim_registry):
    motor_names = ["motorA", "motorB", "motorC"]
    motors = []
    for name in motor_names:
        this_motor = make_fake_device(motor.HavenMotor)(name=name, labels={"motors"})
        sim_registry.register(this_motor)
        motors.append(this_motor)
    print(sim_registry.device_names)
    return motors


def test_motor_menu(fake_motors, qtbot, ffapp):
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Create the window
    window = FireflyMainWindow()
    # Check that the menu items have been created
    assert hasattr(window.ui, "positioners_menu")
    assert len(ffapp.motor_actions) == 3
    window.destroy()


def test_open_motor_window(fake_motors, monkeypatch, ffapp):
    # Set up the application
    ffapp.setup_window_actions()
    ffapp.setup_runengine_actions()
    # Simulate clicking on the menu action (they're in alpha order)
    action = ffapp.motor_actions["motorC"]
    action.trigger()
    # See if the window was created
    motor_3_name = "FireflyMainWindow_motor_motorC"
    assert motor_3_name in ffapp.windows.keys()
    macros = ffapp.windows[motor_3_name].display_widget().macros()
    assert macros["MOTOR"] == "motorC"
