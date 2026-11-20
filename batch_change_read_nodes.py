import os
import re
import nuke

# Handle Qt imports across Nuke versions (Nuke 11-13 = PySide2, Nuke 14+ = PySide6)
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


def get_nuke_formats():
    """Retrieve available project formats formatted for QComboBox."""
    formats = ["-- keep value --"]
    for f in nuke.formats():
        name = f.name() if f.name() else f"{f.width()}x{f.height()}"
        formats.append(name)
    return formats


def get_colorspace_mapping(node):
    """
    Returns clean display labels and internal OCIO/Nuke name mappings.
    """
    knob = node.knob('colorspace')
    
    display_names = []
    mapping = {}
    
    try:
        import nuke.colorspaces
        raw_spaces = nuke.colorspaces.getColorspaces(node)
        
        for item in raw_spaces:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                label, internal = item[0], item[1]
            else:
                label = str(item)
                internal = str(item)
                
            if label not in display_names:
                display_names.append(label)
                mapping[label] = internal
    except Exception:
        pass

    if not display_names:
        try:
            raw_values = knob.values()
            for idx, raw in enumerate(raw_values):
                parts = raw.split('\t')
                clean_label = parts[0].strip()
                internal_value = parts[-1].split(',')[-1].strip() if len(parts) > 1 else idx
                
                if clean_label not in display_names:
                    display_names.append(clean_label)
                    mapping[clean_label] = internal_value
        except Exception:
            pass

    return display_names, mapping


class BatchReadNodesDialog(QtWidgets.QDialog):
    """Batch Properties Edit Dialog matching Nuke's native Read Node layout with custom branding."""
    
    def __init__(self, selected_reads):
        super(BatchReadNodesDialog, self).__init__()
        self.selected_reads = selected_reads
        self.sample_node = selected_reads[0]
        self.reset_to_orig_range = False
        self.force_disk_refresh = False

        self.setWindowTitle("Batch Change Read Nodes")
        self.setMinimumWidth(660)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # --- TOP HEADER DESCRIPTION ---
        header_frame = QtWidgets.QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        header_layout = QtWidgets.QVBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 6, 6, 6)
        
        title_label = QtWidgets.QLabel("<b>Batch Change Read Nodes</b>")
        title_label.setStyleSheet("color: #ffcc00; font-size: 13px;")
        
        desc_label = QtWidgets.QLabel(
            "Quickly modify properties, frame ranges, colorspaces, and localization settings "
            "across multiple selected Read nodes simultaneously while mirroring Nuke's native layout."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)
        main_layout.addWidget(header_frame)
        
        # --- TAB WIDGET (READ NODE PROPERTIES) ---
        tab_widget = QtWidgets.QTabWidget()
        read_tab = QtWidgets.QWidget()
        tab_layout = QtWidgets.QFormLayout(read_tab)
        tab_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        
        # 1. Localization Policy
        loc_layout = QtWidgets.QHBoxLayout()
        self.loc_combo = QtWidgets.QComboBox()
        self.loc_combo.addItems(["-- keep value --", "off", "on", "from auto-localize path"])
        self.btn_update_loc = QtWidgets.QPushButton("Update")
        self.btn_update_loc.clicked.connect(self._update_localization)
        loc_layout.addWidget(self.loc_combo, stretch=2)
        loc_layout.addWidget(self.btn_update_loc)
        tab_layout.addRow("Localization Policy:", loc_layout)

        # 2. Format & Proxy Format
        format_list = get_nuke_formats()
        
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItems(format_list)
        tab_layout.addRow("Format:", self.format_combo)

        self.proxy_combo = QtWidgets.QComboBox()
        self.proxy_combo.addItems(format_list)
        tab_layout.addRow("Proxy Format:", self.proxy_combo)

        # 3. Frame Range & Handles
        frame_range_layout = QtWidgets.QHBoxLayout()
        self.first_frame_input = QtWidgets.QLineEdit()
        self.first_frame_input.setPlaceholderText("First")
        
        self.before_combo = QtWidgets.QComboBox()
        self.before_combo.addItems(["-- keep value --", "hold", "loop", "bounce", "black"])
        
        self.last_frame_input = QtWidgets.QLineEdit()
        self.last_frame_input.setPlaceholderText("Last")
        
        self.after_combo = QtWidgets.QComboBox()
        self.after_combo.addItems(["-- keep value --", "hold", "loop", "bounce", "black"])

        frame_range_layout.addWidget(self.first_frame_input)
        frame_range_layout.addWidget(self.before_combo)
        frame_range_layout.addWidget(self.last_frame_input)
        frame_range_layout.addWidget(self.after_combo)
        tab_layout.addRow("Frame Range:", frame_range_layout)

        # 4. Frame Row (expression, start at, offset)
        frame_mode_layout = QtWidgets.QHBoxLayout()
        self.frame_mode_combo = QtWidgets.QComboBox()
        self.frame_mode_combo.addItems(["-- keep value --", "expression", "start at", "offset"])
        
        self.frame_value_input = QtWidgets.QLineEdit()
        self.frame_value_input.setPlaceholderText("Value / Expression")
        
        self.frame_mode_combo.currentTextChanged.connect(self._on_frame_mode_changed)
        
        frame_mode_layout.addWidget(self.frame_mode_combo)
        frame_mode_layout.addWidget(self.frame_value_input)
        tab_layout.addRow("Frame:", frame_mode_layout)

        # 5. Original Range, Reset Button, and Refresh Button
        orig_layout = QtWidgets.QHBoxLayout()
        
        sample_orig_first = str(int(self.sample_node.knob('origfirst').value()))
        sample_orig_last = str(int(self.sample_node.knob('origlast').value()))
        
        self.orig_first_display = QtWidgets.QLineEdit(sample_orig_first)
        self.orig_first_display.setReadOnly(True)
        self.orig_first_display.setMaximumWidth(60)
        
        self.orig_last_display = QtWidgets.QLineEdit(sample_orig_last)
        self.orig_last_display.setReadOnly(True)
        self.orig_last_display.setMaximumWidth(60)

        self.btn_reset_orig = QtWidgets.QPushButton("Set to Original Frame Range")
        self.btn_reset_orig.setCheckable(True)
        self.btn_reset_orig.toggled.connect(self._toggle_reset_range)

        self.btn_refresh_range = QtWidgets.QPushButton("Refresh Frame Range")
        self.btn_refresh_range.setCheckable(True)
        self.btn_refresh_range.toggled.connect(self._toggle_refresh_range)

        orig_layout.addWidget(self.orig_first_display)
        orig_layout.addWidget(self.orig_last_display)
        orig_layout.addWidget(self.btn_reset_orig)
        orig_layout.addWidget(self.btn_refresh_range)
        tab_layout.addRow("Original Range:", orig_layout)

        # 6. Missing Frames & Reload Button
        missing_layout = QtWidgets.QHBoxLayout()
        self.missing_combo = QtWidgets.QComboBox()
        self.missing_combo.addItems(["-- keep value --", "error", "black", "checkerboard", "nearest frame"])
        
        self.btn_reload = QtWidgets.QPushButton("reload")
        self.btn_reload.clicked.connect(self._reload_reads)
        
        missing_layout.addWidget(self.missing_combo, stretch=2)
        missing_layout.addWidget(self.btn_reload)
        tab_layout.addRow("Missing Frames:", missing_layout)

        # 7. Input Transform & Checkboxes
        input_tf_layout = QtWidgets.QHBoxLayout()
        labels, self.cs_mapping = get_colorspace_mapping(self.sample_node)
        
        ui_colorspace_list = ["-- keep value --"] + labels
        
        self.colorspace_combo = QtWidgets.QComboBox()
        self.colorspace_combo.addItems(ui_colorspace_list)

        self.chk_premult = QtWidgets.QCheckBox("Premultiplied")
        self.chk_raw = QtWidgets.QCheckBox("Raw Data")
        self.chk_auto_alpha = QtWidgets.QCheckBox("Auto Alpha")
        
        for chk in [self.chk_premult, self.chk_raw, self.chk_auto_alpha]:
            chk.setTristate(True)
            chk.setCheckState(QtCore.Qt.PartiallyChecked)

        self.chk_raw.stateChanged.connect(self._on_raw_toggled)

        input_tf_layout.addWidget(self.colorspace_combo, stretch=2)
        input_tf_layout.addWidget(self.chk_premult)
        input_tf_layout.addWidget(self.chk_raw)
        input_tf_layout.addWidget(self.chk_auto_alpha)
        tab_layout.addRow("Input Transform:", input_tf_layout)

        tab_widget.addTab(read_tab, "Read")
        main_layout.addWidget(tab_widget)

        # --- FOOTER LAYOUT (AUTHOR SIGNATURE & BUTTON BOX) ---
        footer_layout = QtWidgets.QHBoxLayout()
        
        # Left side: Author credit, version, date, and Nukepedia link
        author_info = (
            "<b>Created by:</b> mi sci<br>"
            "<b>Version:</b> v1.01 (October 26)<br>"
            "<b>Nukepedia:</b> <a href='https://www.nukepedia.com/tools/python/ui/' style='color: #66b3ff;'>View on Nukepedia</a>"
        )
        self.credit_label = QtWidgets.QLabel(author_info)
        self.credit_label.setOpenExternalLinks(True)
        self.credit_label.setStyleSheet("color: #888888; font-size: 10px; line-height: 1.2;")
        footer_layout.addWidget(self.credit_label)
        
        footer_layout.addStretch()
        
        # Right side: OK / Cancel buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        footer_layout.addWidget(btn_box)
        
        main_layout.addLayout(footer_layout)

    def _on_raw_toggled(self, state):
        if state == QtCore.Qt.Checked:
            self.colorspace_combo.setEnabled(False)
        else:
            self.colorspace_combo.setEnabled(True)

    def _on_frame_mode_changed(self, mode):
        if mode == "expression":
            self.frame_value_input.setPlaceholderText("e.g. frame+10")
        elif mode in ["start at", "offset"]:
            self.frame_value_input.setPlaceholderText("e.g. 100 or -10")
        else:
            self.frame_value_input.setPlaceholderText("Value / Expression")

    def _toggle_reset_range(self, checked):
        self.reset_to_orig_range = checked
        if checked:
            self.btn_refresh_range.setChecked(False)
            self.first_frame_input.setEnabled(False)
            self.last_frame_input.setEnabled(False)
            self.first_frame_input.clear()
            self.last_frame_input.clear()
        elif not self.force_disk_refresh:
            self.first_frame_input.setEnabled(True)
            self.last_frame_input.setEnabled(True)

    def _toggle_refresh_range(self, checked):
        self.force_disk_refresh = checked
        if checked:
            self.btn_reset_orig.setChecked(False)
            self.first_frame_input.setEnabled(False)
            self.last_frame_input.setEnabled(False)
            self.first_frame_input.clear()
            self.last_frame_input.clear()
        elif not self.reset_to_orig_range:
            self.first_frame_input.setEnabled(True)
            self.last_frame_input.setEnabled(True)

    def _reload_reads(self):
        for node in self.selected_reads:
            try:
                node.knob('reload').execute()
            except Exception:
                pass

    def _update_localization(self):
        for node in self.selected_reads:
            try:
                node.knob('updateLocalization').execute()
            except Exception:
                pass

    def _rescan_sequence_from_disk(self, node):
        """Scans sequence on disk via Nuke's directory evaluation tools and updates 'first' and 'last'."""
        file_path = node.knob('file').value()
        if not file_path:
            return

        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            return

        try:
            seq_list = nuke.getFileNameList(dir_path)
            base_name = os.path.basename(file_path).split('.')[0]
            
            found_frames = []
            for seq in seq_list:
                if base_name in seq:
                    match = re.search(r'\b(\d+)-(\d+)\b', seq)
                    if match:
                        found_frames.extend([int(match.group(1)), int(match.group(2))])
            
            if found_frames:
                min_frame = min(found_frames)
                max_frame = max(found_frames)
                
                node.knob('reload').execute()
                node.knob('first').setValue(min_frame)
                node.knob('last').setValue(max_frame)
                return
        except Exception:
            pass

        try:
            node.knob('reload').execute()
            node.knob('first').setValue(int(node.knob('origfirst').value()))
            node.knob('last').setValue(int(node.knob('origlast').value()))
        except Exception:
            pass

    def apply_changes(self):
        count = 0
        
        loc_val = self.loc_combo.currentText()
        fmt_val = self.format_combo.currentText()
        proxy_val = self.proxy_combo.currentText()
        
        first_str = self.first_frame_input.text().strip()
        last_str = self.last_frame_input.text().strip()
        
        before_val = self.before_combo.currentText()
        after_val = self.after_combo.currentText()
        
        frame_mode = self.frame_mode_combo.currentText()
        frame_val_str = self.frame_value_input.text().strip()

        missing_val = self.missing_combo.currentText()
        chosen_label = self.colorspace_combo.currentText()

        for node in self.selected_reads:
            # 1. Localization Policy
            if loc_val != "-- keep value --":
                node.knob('localizationPolicy').setValue(loc_val)

            # 2. Formats
            if fmt_val != "-- keep value --":
                node.knob('format').setValue(fmt_val)
            if proxy_val != "-- keep value --":
                node.knob('proxy_format').setValue(proxy_val)

            # 3. Frame Range logic
            if self.force_disk_refresh:
                self._rescan_sequence_from_disk(node)
            elif self.reset_to_orig_range:
                node.knob('first').setValue(int(node.knob('origfirst').value()))
                node.knob('last').setValue(int(node.knob('origlast').value()))
            else:
                if first_str:
                    try:
                        node.knob('first').setValue(int(first_str))
                    except ValueError:
                        pass
                if last_str:
                    try:
                        node.knob('last').setValue(int(last_str))
                    except ValueError:
                        pass

            if before_val != "-- keep value --":
                node.knob('before').setValue(before_val)
            if after_val != "-- keep value --":
                node.knob('after').setValue(after_val)

            # 4. Frame Mode
            if frame_mode != "-- keep value --":
                node.knob('frame_mode').setValue(frame_mode)
                if frame_val_str:
                    node.knob('frame').setValue(frame_val_str)

            # 5. Missing Frames
            if missing_val != "-- keep value --":
                node.knob('on_error').setValue(missing_val)

            # 6. Raw Data, Premult, Auto Alpha
            if self.chk_raw.checkState() != QtCore.Qt.PartiallyChecked:
                node.knob('raw').setValue(self.chk_raw.isChecked())

            if self.chk_premult.checkState() != QtCore.Qt.PartiallyChecked:
                node.knob('premultiplied').setValue(self.chk_premult.isChecked())

            if self.chk_auto_alpha.checkState() != QtCore.Qt.PartiallyChecked:
                node.knob('auto_alpha').setValue(self.chk_auto_alpha.isChecked())

            # 7. Input Transform / Colorspace
            if chosen_label != "-- keep value --":
                target_value = self.cs_mapping.get(chosen_label)
                if target_value is not None:
                    if node.knob('raw').value():
                        node.knob('raw').setValue(False)
                    node.knob('colorspace').setValue(target_value)

            count += 1

        print(f"[Batch Read Nodes] Updated {count} Read node(s).")


def batch_change_read_nodes():
    selected_nodes = nuke.selectedNodes()
    selected_reads = [node for node in selected_nodes if node.Class() == 'Read']
    
    if not selected_reads:
        nuke.message("Please select at least one Read node in the Node Graph.")
        return

    dialog = BatchReadNodesDialog(selected_reads)
    if dialog.exec_():
        dialog.apply_changes()