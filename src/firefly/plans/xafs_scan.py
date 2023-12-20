from qtpy import QtWidgets

from firefly import display


class XafsScanRegion:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        
        # First energy box
        self.start_line_edit = QtWidgets.QLineEdit()
        self.start_line_edit.setPlaceholderText("Start…")
        self.layout.addWidget(self.start_line_edit)
        # Last energy box
        self.stop_line_edit = QtWidgets.QLineEdit()
        self.stop_line_edit.setPlaceholderText("Stop…")
        self.layout.addWidget(self.stop_line_edit)
        # Energy step box
        self.step_line_edit = QtWidgets.QLineEdit()
        self.step_line_edit.setPlaceholderText("Step…")
        self.layout.addWidget(self.step_line_edit)
        # K-space checkbox
        self.k_space_checkbox = QtWidgets.QCheckBox()
        self.k_space_checkbox.setText("K-space")
        self.k_space_checkbox.setEnabled(False)
        self.layout.addWidget(self.k_space_checkbox)
        # K-weight factor box, hidden at first
        self.k_weight_line_edit = QtWidgets.QLineEdit()
        self.k_weight_line_edit.setPlaceholderText("K-weight")
        self.k_weight_line_edit.setEnabled(False)
        self.layout.addWidget(self.k_weight_line_edit)
        # Connect the k-space enabled checkbox to the relevant signals
        self.k_space_checkbox.stateChanged.connect(self.k_weight_line_edit.setEnabled)
    
    def update_edge_enabled(self, is_checked: int):
        # Go back to real space if k-space was enabled
        if not is_checked:
            self.k_space_checkbox.setChecked(False)
        # Disabled the k-space checkbox
        self.k_space_checkbox.setEnabled(is_checked)

class XafsScanDisplay(display.FireflyDisplay):
    def customize_ui(self):
        self.reset_default_regions()
        # Connect the E0 checkbox to the E0 combobox
        self.ui.use_edge_checkbox.stateChanged.connect(self.edge_combo_box.setEnabled)
        # update only after enter is hit instead of immediately changing
        # self.ui.regions_spin_box.valueChanged.connect(self.update_regions)
        self.ui.regions_spin_box.editingFinished.connect(self.update_regions)
        #TODO 
        self.ui.pushButton.clicked.connect(self.reset_default_regions) 

    def reset_default_regions(self):
        default_num_regions = 3
        if not hasattr(self, 'regions'):
            self.regions = []
            self.add_regions(default_num_regions)
        self.ui.regions_spin_box.setValue(default_num_regions)
        self.update_regions()

    def add_regions(self, num=1):
        for i in range(num):
            region = XafsScanRegion()
            self.ui.regions_layout.addLayout(region.layout)
            # Connect the E0 checkbox to each of the regions
            self.ui.use_edge_checkbox.stateChanged.connect(region.update_edge_enabled)
            # Save it to the list
            self.regions.append(region)

    def remove_regions(self, num=1):
        for i in range(num):
            layout = self.regions[-1].layout
            # iterate/wait, and delete all widgets in the layout in the end
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.regions.pop()
        
    def update_regions(self):
        new_region_num = self.ui.regions_spin_box.value()
        old_region_num = len(self.regions)
        diff_region_num = new_region_num - old_region_num

        if diff_region_num < 0:
            self.remove_regions(abs(diff_region_num))
        elif diff_region_num > 0:
            self.add_regions(diff_region_num)

    def ui_filename(self):
        return "plans/xafs_scan.ui"
