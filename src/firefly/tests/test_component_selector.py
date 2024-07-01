from unittest import mock

import pytest
from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor, sim

from firefly.component_selector import (
    ComponentSelector,
    DeviceComboBoxModel,
    DeviceTreeModel,
)


class Stage(Device):
    motor2 = Cpt(EpicsMotor, "m2", name="motor2")
    motor3 = Cpt(EpicsMotor, "m3", name="motor3")
    lazy_motor = Cpt(EpicsMotor, "m4", name="motor4", lazy=True)


@pytest.fixture()
def motor_registry(sim_registry):
    """A simulated motor registry. Like the ophyd-registry but connected to the queueserver."""
    FakeMotor = sim.make_fake_device(EpicsMotor)
    FakeMotor(name="motor1")
    FakeStage = sim.make_fake_device(Stage)
    FakeStage(name="stage")
    return sim_registry


@pytest.fixture
async def selector(motor_registry, qtbot):
    selector_ = ComponentSelector()
    qtbot.addWidget(selector_)
    # Register our new devices
    await selector_.update_devices(motor_registry)
    return selector_


@pytest.mark.asyncio
async def test_selector_adds_devices(selector):
    """Check that the combobox editable options are set based on the allowed detectors."""
    # await selector._devices_task
    # # Add some items to the
    # Check that positioners were added to the combobox model
    assert selector.combo_box.itemText(0) == "motor1"
    assert selector.combo_box.itemText(1) == "stage"
    assert selector.combo_box.itemText(2) == "stage.motor2"
    assert selector.combo_box.itemText(3) == "stage.motor3"
    # Check that devices were added to the tree model
    tree_model = selector.tree_model
    assert tree_model.item(0).text() == "motor1"


# @pytest.mark.asyncio
# async def test_lazy_signals_omitted(motor_registry, selector):
#     model = DeviceTreeModel()
#     await model.update_devices(motor_registry)
#     stage_idx = 1
#     stage_node = model.item(stage_idx)
#     assert stage_node.text() == "stage"
#     # Make sure the lazy motor isn't included
#     column = 0
#     cpt_names = [stage_node.child(row, column).text() for row in range(stage_node.rowCount())]
#     assert "lazy_motor" not in cpt_names


@pytest.mark.asyncio
async def test_tree_model_adds_device(motor_registry):
    model = DeviceTreeModel()
    await model.add_device(motor_registry["motor1"])
    # Check "Component" column
    assert model.item(0).text() == "motor1"
    assert model.item(0).child(0, column=0).text() == "user_readback"
    # Check "Type" column
    assert model.item(0, column=1).text() == "FakeEpicsMotor"
    assert model.item(0).child(0, column=1).text() == "FakeEpicsSignalRO"


@pytest.mark.asyncio
async def test_combo_box_model_adds_device(motor_registry):
    model = DeviceComboBoxModel()
    await model.add_device(motor_registry["motor1"])
    await model.add_device(motor_registry["stage"])
    # Check that dot-notation is included
    assert model.item(0).text() == "motor1"
    assert model.item(1).text() == "stage"
    assert model.item(2).text() == "stage.motor2"


@pytest.mark.asyncio
async def test_tree_changes_combobox(selector, qtbot):
    """Check that the combobox and tree will update each other."""
    # Select a tree item
    item = selector.tree_model.item(0).child(1, column=0)
    with qtbot.waitSignal(selector.combo_box.currentTextChanged, timeout=1):
        selector.tree_view.selectionModel().currentChanged.emit(
            item.index(), item.index()
        )
    assert selector.combo_box.currentText() == "motor1.user_setpoint"


@pytest.mark.asyncio
async def test_combobox_changes_tree(selector, qtbot):
    """Check that the combobox and tree will update each other."""
    # Select a combobox item
    item = selector.tree_model.item(0).child(1, column=0)
    selector.combo_box.setCurrentIndex(3)
    with qtbot.waitSignal(
        selector.tree_view.selectionModel().currentChanged, timeout=1
    ):
        selector.combo_box.currentTextChanged.emit("motor1.user_setpoint")


@pytest.mark.asyncio
async def test_model_component_from_index(motor_registry):
    model = DeviceTreeModel()
    await model.add_device(motor_registry["motor1"])
    await model.add_device(motor_registry["stage"])
    # Can we retrieve a root device based on its name item
    item = model.item(0)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "motor1"
    # Can we retrieve a component based on its name item
    item = model.item(1).child(1, column=0)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "stage.motor3"
    # Can we retrieve a component based on its type item
    item = model.item(1).child(1, column=1)
    cpt = model.component_from_index(item.index())
    assert cpt.dotted_name == "stage.motor3"


@pytest.mark.asyncio
async def test_model_component_from_dotted_index(motor_registry):
    model = DeviceTreeModel()
    await model.add_device(motor_registry["motor1"])
    await model.add_device(motor_registry["stage"])
    # Can we retrieve a root device based on its dotted name
    item = model.item(0)
    cpt = model.component_from_dotted_name("motor1")
    assert cpt.name_item is item
    # Can we retrieve a component based on its dotted name
    item = model.item(1).child(1, column=0).child(1, column=0)
    cpt = model.component_from_dotted_name("stage.motor3.user_setpoint")
    assert cpt.name_item is item


@pytest.mark.asyncio
async def test_loads_devices_from_registry(selector, motor_registry, qtbot):
    selector.combo_box_model.add_device = mock.AsyncMock()
    await selector.update_devices(motor_registry)
    selector.combo_box_model.add_device.assert_called_with(motor_registry["stage"])
