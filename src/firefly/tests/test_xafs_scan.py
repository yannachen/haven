from firefly.plans.xafs_scan import XafsScanDisplay
import numpy as np
from bluesky_queueserver_api import BPlan
from unittest import mock

# default values for EXAFS scan
pre_edge = [-50, -20, 1]
XANES_region = [-20, 50, 0.2]
EXAFS_region = [50, 500, 0.5]
default_values = [pre_edge, XANES_region, EXAFS_region]

def test_region_number(qtbot):
    """Does changing the region number affect the UI?"""
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # Check that the display has the right number of rows to start with
    assert disp.ui.regions_spin_box.value() == 3
    assert hasattr(disp, "regions")
    assert len(disp.regions) == 3
    
    # Check that regions can be inserted
    disp.ui.regions_spin_box.setValue(5)
    assert len(disp.regions) == 5

    # Check that regions can be removed
    disp.ui.regions_spin_box.setValue(1)
    assert len(disp.regions) == 1


def test_E0_checkbox(qtbot):
    """Does selecting the E0 checkbox adjust the UI properly?"""
    disp = XafsScanDisplay()
    qtbot.addWidget(disp)
    # check whether extracted edge value is correct
    disp.edge_combo_box.setCurrentText("Pt L3 (11500.8 eV)")
    disp.ui.use_edge_checkbox.setChecked(True)

    # check whether the math is done correctly when switching off E0
    disp.ui.use_edge_checkbox.setChecked(False)
    # check whether edge value is extracted correctly
    np.testing.assert_equal(disp.edge_value, 11500.8)
    # K-space checkboxes should be disabled when E0 is unchecked    
    assert not disp.regions[0].k_space_checkbox.isEnabled()

    # check whether energy values is added correctly 
    for i in range(len(default_values)):
        np.testing.assert_almost_equal(float(disp.regions[i].start_line_edit.text()), default_values[i][0] + disp.edge_value, decimal=3)
        np.testing.assert_almost_equal(float(disp.regions[i].stop_line_edit.text()), default_values[i][1] + disp.edge_value, decimal=3)
        np.testing.assert_almost_equal(float(disp.regions[i].step_line_edit.text()), default_values[i][2], decimal=3)

    # check whether k range is calculated right 
    disp.ui.use_edge_checkbox.setChecked(True)
    # K-space checkbox should become re-enabled after E0 is checked
    assert disp.regions[-1].k_space_checkbox.isEnabled()
    disp.regions[-1].k_space_checkbox.setChecked(True)
    np.testing.assert_almost_equal(float(disp.regions[i].start_line_edit.text()), 3.6226, decimal=4)
    np.testing.assert_almost_equal(float(disp.regions[i].stop_line_edit.text()), 11.4557, decimal=4)
    np.testing.assert_almost_equal(float(disp.regions[i].step_line_edit.text()), 3.64069-3.6226, decimal=4)


# def test_move_energy(qtbot, ffapp, sim_registry):
#     mono = FakeMonochromator("mono_ioc", name="monochromator")
#     sim_registry.register(
#         FakeEnergyPositioner(
#             mono_pv="mono_ioc:Energy",
#             id_offset_pv="mono_ioc:ID_offset",
#             id_tracking_pv="mono_ioc:ID_tracking",
#             id_prefix="id_ioc",
#             name="energy",
#         )
#     )
#     # Load display
#     disp = EnergyDisplay()
#     # Click the set energy button
#     btn = disp.ui.set_energy_button
#     expected_item = BPlan("set_energy", energy=8402.0)

#     def check_item(item):
#         return item.to_dict() == expected_item.to_dict()

#     qtbot.keyClicks(disp.target_energy_lineedit, "8402")
#     with qtbot.waitSignal(
#         ffapp.queue_item_added, timeout=1000, check_params_cb=check_item
#     ):
#         qtbot.mouseClick(btn, QtCore.Qt.LeftButton)


def test_xafs_scan_plan_queued(ffapp, qtbot):
    display = XafsScanDisplay()
    
    display.edge_combo_box.setCurrentText("Pt L3 (11500.8 eV)")
    display.regions[-1].region_checkbox.setChecked(False)
    # set up detector list
    display.ui.detectors_list.selected_detectors = mock.MagicMock(
        return_value=["vortex_me4", "I0"]
    )
    energies_region0 = np.arange(default_values[0][0], default_values[0][1] + default_values[0][2], default_values[0][2])
    energies_region1 = np.arange(default_values[1][0]+default_values[1][2], default_values[1][1] + default_values[1][2], default_values[1][2])
    energies_merge = np.hstack([energies_region0, energies_region1])
    exposures = np.ones(energies_merge.shape)
    expected_item = BPlan(
        "energy_scan",
        energies=energies_merge,
        exposure=exposures,
        E0=11500.8,
        detectors=["vortex_me4", "I0"],
        md=None,
    )

#     def check_item(item):
#         from pprint import pprint

#         pprint(item.to_dict())
#         pprint(expected_item.to_dict())
#         return item.to_dict() == expected_item.to_dict()

#     # Click the run button and see if the plan is queued
#     with qtbot.waitSignal(
#         ffapp.queue_item_added, timeout=1000, check_params_cb=check_item
#     ):
#         qtbot.mouseClick(display.ui.run_button, QtCore.Qt.LeftButton)


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
