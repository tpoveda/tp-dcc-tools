from __future__ import annotations

import typing

from tp.common.qt import api as qt

if typing.TYPE_CHECKING:
	from tp.tools.rig.crit.componentseditor.controller import CritComponentsEditorController
	from tp.tools.rig.crit.builder.models.component import ComponentModel


class BaseSettingsWidget(qt.QWidget):

	modified = qt.Signal()

	def __init__(self, controller: CritComponentsEditorController, parent: qt.QWidget | None = None):
		super().__init__(parent)

		self._controller = controller

		self._default_name = ''
		self._default_type = ''
		self._default_display_name = ''
		self._default_description = ''
		self._default_version = ''
		self._default_descriptor_version = ''
		self._default_side = ''

		main_layout = qt.grid_layout(spacing=2)
		self.setLayout(main_layout)

		self._name_line = qt.line_edit(parent=self)
		self._type_line = qt.line_edit(read_only=True, parent=self)
		self._display_name_line = qt.line_edit(parent=self)
		self._description_text = qt.QPlainTextEdit(parent=self)
		self._version_spin = qt.QSpinBox(parent=self)
		self._version_spin.setEnabled(False)
		self._descriptor_version_spin = qt.QSpinBox(parent=self)
		self._descriptor_version_spin.setEnabled(False)
		self._side_combo = qt.combobox(items=[], parent=self)

		main_layout.addWidget(qt.label('Name', parent=self), 0, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._name_line, 0, 1)
		main_layout.addWidget(qt.label('Type', parent=self), 1, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._type_line, 1, 1)
		main_layout.addWidget(qt.label('Display Name', parent=self), 2, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._display_name_line, 2, 1)
		main_layout.addWidget(qt.label('Description', parent=self), 3, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._description_text, 3, 1)
		main_layout.addWidget(qt.label('Version', parent=self), 4, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._version_spin, 4, 1)
		main_layout.addWidget(qt.label('Descriptor Version', parent=self), 5, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._descriptor_version_spin, 5, 1)
		main_layout.addWidget(qt.label('Side', parent=self), 6, 0, qt.Qt.AlignRight)
		main_layout.addWidget(self._side_combo, 6, 1)

		self._controller.activeComponentModelChanged.connect(self._on_controller_active_component_model_changed)

		# self._name_line.textChanged.connect(self._on_modify)
		# self._display_name_line.textChanged.connect(self._on_modify)
		# self._description_text.textChanged.connect(self._on_modify)
		# self._side_combo.currentIndexChanged.connect(self._on_modify)
	def clear(self):
		"""
		Clears base settings internal variables and UI.
		"""

		self._default_name = ''
		self._default_type = ''
		self._default_display_name = ''
		self._default_description = ''
		self._default_version = ''
		self._default_descriptor_version = ''
		self._default_side = ''

		with qt.block_signals(self, children=True):
			self._name_line.setText('')
			self._type_line.setText('')
			self._display_name_line.setText('')
			self._description_text.setPlainText('')
			self._version_spin.setValue(0)
			self._descriptor_version_spin.setValue(0)
			self._side_combo.setCurrentIndex(0)

	def _on_controller_active_component_model_changed(self, component_model: ComponentModel):
		"""
		Internal callback function that is called each time a rig component is edited.

		:param ComponentModel component_model: active component model instance.
		"""

		if not component_model:
			self._name_line.setText('')
			self._type_line.setText('')
			self._display_name_line.setText('')
			self._description_text.setPlainText('')
			self._version_spin.setValue(0)
			self._descriptor_version_spin.setValue(0)
			self._side_combo.setCurrentIndex(0)
			return

		with qt.block_signals(self, children=True):
			self._name_line.setText(self._default_name)
			self._type_line.setText(self._default_type)
			self._display_name_line.setText(self._default_display_name)
			self._description_text.setPlainText(self._default_description)
			self._version_spin.setValue(int(self._default_version or 0))
			self._descriptor_version_spin.setValue(int(self._default_descriptor_version or 0))
			self._side_combo.setCurrentText(self._default_side)
