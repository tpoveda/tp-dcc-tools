#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related to Maya UI
"""

from __future__ import annotations

import traceback
import contextlib
from collections import OrderedDict

from Qt.QtCore import QObject
from Qt.QtWidgets import QApplication, QWidget, QDesktopWidget, QMainWindow, QTextEdit
from Qt import QtGui
try:
	import shiboken2 as shiboken
except ImportError:
	try:
		from PySide2 import shiboken2 as shiboken
	except ImportError:
		try:
			import shiboken
		except ImportError:
			try:
				from Shiboken import shiboken
			except ImportError:
				try:
					from PySide import shiboken
				except Exception:
					pass

import maya.cmds as cmds
import maya.utils as utils
import maya.mel as mel
import maya.OpenMayaUI as OpenMayaUI1

from tp.core import log
from tp.maya.api import env
from tp.maya.cmds import helpers

logger = log.tpLogger

# ===================================================================================

_DPI_SCALE = 1.0 if not hasattr(cmds, 'mayaDpiSetting') else cmds.mayaDpiSetting(query=True, realScaleValue=True)
current_progress_bar = None

# ===================================================================================


def maya_window(window_name=None, wrap_instance=True):
	"""
	Return the Maya main window widget as a Python object
	:return: Maya Window
	"""

	if wrap_instance:
		if window_name is not None:
			if '|' in str(window_name):
				# qt_obj = pm.uitypes.toQtObject(window_id)
				qt_obj = to_qt_object(window_name)
				if qt_obj is not None:
					return qt_obj
			ptr = OpenMayaUI1.MQtUtil.findControl(window_name)
			if ptr is not None:
				return wrapinstance(ptr, QMainWindow)
		else:
			ptr = OpenMayaUI1.MQtUtil.mainWindow()
			if ptr is not None:
				return wrapinstance(ptr, QMainWindow)

	if isinstance(window_name, (QWidget, QMainWindow)):
		return window_name
	search = window_name or 'MayaWindow'
	for obj in QApplication.topLevelWidgets():
		if obj.objectName() == search:
			return obj


def main_shelf():
	"""
	Returns the Maya main shelf
	"""

	return mel.eval('$tempVar = $gShelfTopLevel')


def main_window():
	"""
	Returns Maya main window through MEL
	"""

	return mel.eval("$tempVar = $gMainWindow")


def script_editor(source_type='python', command_completion=False, show_tooltip_help=False):
	"""
	Returns Maya script editor window
	:param source_type: str
	:param command_completion: bool
	:param show_tooltip_help: bool
	:return:
	"""

	cmds.window()
	cmds.columnLayout()
	executer = cmds.cmdScrollFieldExecuter(
		sourceType=source_type, commandCompletion=command_completion, showTooltipHelp=show_tooltip_help)
	qtobj = to_qt_object(executer, QTextEdit)
	return executer, qtobj


def viewport_message(text):
	"""
	Shows a message in the Maya viewport
	:param text: str, text to show in Maya viewport
	"""

	cmds.inViewMessage(amg='<hl>{}</hl>'.format(text), pos='midCenter', fade=True)


def force_stack_trace_on():
	"""
	Forces enabling Maya Stack Trace
	"""

	try:
		mel.eval('stackTrace -state on')
		cmds.optionVar(intValue=('stackTraceIsOn', True))
		what_is = mel.eval('whatIs "$gLastFocusedCommandReporter"')
		if what_is != 'Unknown':
			last_focused_command_reporter = mel.eval('$tmp = $gLastFocusedCommandReporter')
			if last_focused_command_reporter and last_focused_command_reporter != '':
				mel.eval('synchronizeScriptEditorOption 1 $stackTraceMenuItemSuffix')
	except RuntimeError:
		pass


def pass_message_to_main_thread(message_handler, *args):
	"""
	Executes teh message_handler with the given list of arguments in Maya's main thread
	during the next idle event
	:param message_handler: variant, str || function, string containing Python code or callable function
	"""

	utils.executeInMainThreadWithResult(message_handler, *args)


def dpi_scale(value):
	return _DPI_SCALE * value


def plugin_shapes():
	"""
	Return all available plugin shapes
	:return: dict, plugin shapes by their menu label and script name
	"""

	filters = cmds.pluginDisplayFilter(query=True, listFilters=True)
	labels = [cmds.pluginDisplayFilter(f, query=True, label=True) for f in filters]
	return OrderedDict(zip(labels, filters))


def active_editor():
	"""
	Returns the active editor panel of Maya
	"""

	cmds.currentTime(cmds.currentTime(query=True))
	panel = cmds.playblast(activeEditor=True)
	return panel.split('|')[-1]


def panel_with_focus(viewport3d: bool = True):
	"""
	Returns the panel with focus.

	:param bool viewport3d: True will test to see if the panel under the cursor is a 3d viewport.
	:return: name of the Maya panel.
	:rtype: str
	"""

	focus_panel = cmds.getPanel(withFocus=True)
	try:
		if viewport3d:
			cmds.modelPanel(focus_panel, query=True, camera=True)
	except RuntimeError:
		return ''

	return focus_panel


def panel_under_cursor(viewport3d: bool = True) -> str:
	"""
	Returns the panel under the pointer.

	:param bool viewport3d: True will test to see if the panel under the cursor is a 3d viewport.
	:return: name of the Maya panel.
	:rtype: str
	"""

	try:
		maya_panel = cmds.getPanel(underPointer=True)
		if viewport3d:
			cmds.modelPanel(maya_panel, query=True, camera=True)
		return maya_panel
	except RuntimeError:
		return ''


def first_viewport_panel() -> str:
	"""
	Returns the first visible viewport panel in the current Maya session.

	:return: name of the Maya panel that is a viewport.
	:rtype: str
	"""

	panel = ''
	all_panels = cmds.getPanel(visiblePanels=True)
	for panel in all_panels:
		try:
			cmds.modelPanel(panel, query=True, camera=True)
			break
		except RuntimeError:
			panel = ''

	return panel


def panel_under_pointer_or_focus(
		viewport3d: bool = False, prioritize_under_cursor: bool = True, message: bool = True) -> str:
	"""
	Returns the Maya panel that is either:
		1. Under the cursor.
		2. The active panel (with focus).
		3. First visible viewport panel (only if viewport3d is True).

	:param bool viewport3d: True will test to see if the panel under the cursor is a 3d viewport. If True, will
		return only panels with 3D camears (for example, 3d viewports).
	:param bool prioritize_under_cursor: whether to return under cursor first or with focus. In general, use
		prioritize_under_cursor=True for hotkeys and prioritize_under_cursor=Fasle for UIs.
	:param str message: whether to show warning message if no panel found.
	:return: name of the Maya panel.
	:rtype: str
	"""

	if prioritize_under_cursor:
		panel = panel_under_cursor(viewport3d=viewport3d)
		if panel:
			return panel
		panel = panel_with_focus(viewport3d=viewport3d)
		if panel:
			return panel
	else:
		panel = panel_with_focus(viewport3d=viewport3d)
		if panel:
			return panel
		panel = panel_under_cursor(viewport3d=viewport3d)
		if panel:
			return panel

	if viewport3d:
		panel = first_viewport_panel()
		if panel:
			return panel

	if message:
		logger.warning(
			'No viewport found, the active window must be under the cursor or the active window must be a 3d viewport')

	return ''


def playblack_slider():
	"""
	Returns playback slider Maya control
	:return: str
	"""

	return mel.eval("global string $gPlayBackSlider; " "$gPlayBackSlider = $gPlayBackSlider;")


def get_time_slider_range(highlighted=True, within_highlighted=True, highlighted_only=False):
	"""
	Return the time range from Maya time slider
	:param highlighted: bool, If True it will return a selected frame range (if there is any selection of
		more than one frame) else it will return min and max playblack time
	:param within_highlighted: bool, Maya returns the highlighted range end as a plus one value by default.
		If True, this is fixed by removing one from the last frame number
	:param highlighted_only: bool, If True, it wil return only highlighted frame range
	:return: list<float, float>, [start_frame, end_frame]
	"""

	if highlighted is True:
		playback_slider = playblack_slider()
		if cmds.timeControl(playback_slider, query=True, rangeVisible=True):
			highlighted_range = cmds.timeControl(playback_slider, query=True, rangeArray=True)
			if within_highlighted:
				highlighted_range[-1] -= 1
			return highlighted_range

	if not highlighted_only:
		return [cmds.playbackOptions(
			query=True, minTime=True), cmds.playbackOptions(query=True, maxTime=True)]


def available_screen_size():
	"""
	Returns available screen size without space occupied by task bar
	"""

	if not hasattr(cmds, 'about') or cmds.about(batch=True):
		return [0, 0]

	rect = QDesktopWidget().screenGeometry(-1)
	return [rect.width(), rect.height()]


def top_maya_shelf():
	"""
	Returns top Maya shelf object name.

	:return: Maya shelf object name.
	:rtype: str
	"""

	return mel.eval("global string $gShelfTopLevel; $temp = $gShelfTopLevel;")


def all_shelves():
	return cmds.tabLayout(top_maya_shelf(), query=True, ca=True)


def current_shelf():
	return cmds.tabLayout(top_maya_shelf(), query=True, st=True)


def shelf_exists(shelf_name):
	"""
	Returns True if the given shelf name already exists or False otherwise
	:param shelf_name: str, shelf name
	:return: bool
	"""

	return cmds.shelfLayout(shelf_name, exists=True)


def delete_shelf(shelf_name):
	"""
	Deletes given shelf by name, if exists
	:param shelf_name: str, shelf name
	"""

	if shelf_exists(shelf_name=shelf_name):
		cmds.deleteUI(shelf_name)


def create_shelf(name, parent_layout='ShelfLayout'):
	"""
	Creates a new shelf parented on the given layout
	:param name: str, name of the shelf to create
	:param parent_layout: name of the parent shelf layout
	:return: str
	"""

	return cmds.shelfLayout(name, parent=parent_layout)


@contextlib.contextmanager
def create_independent_panel(width, height, off_screen=False):
	"""
	Creates a Maya panel window without decorations
	:param width: int, width of panel
	:param height: int, height of panel
	:param off_screen: bool
	with create_independent_panel(800, 600):
		cmds.capture()
	"""

	screen_width, screen_height = available_screen_size()
	top_left = [int((screen_height - height) * 0.5), int((screen_width - width) * 0.5)]
	window = cmds.window(
		width=width, height=height, topLeftCorner=top_left,
		menuBarVisible=False, titleBar=False, visible=not off_screen)
	cmds.paneLayout()
	panel = cmds.modelPanel(menuBarVisible=False, label='CapturePanel')
	# Hide icons under panel menus
	bar_layout = cmds.modelPanel(panel, query=True, barLayout=True)
	cmds.frameLayout(bar_layout, edit=True, collapse=True)
	if not off_screen:
		cmds.showWindow(window)

	# Set the modelEditor of the modelPanel as the active view, so it takes the playback focus
	editor = cmds.modelPanel(panel, query=True, modelEditor=True)
	cmds.modelEditor(editor, edit=True, activeView=True)
	cmds.refresh(force=True)

	try:
		yield panel
	finally:
		cmds.deleteUI(panel, panel=True)
		cmds.deleteUI(window)


@contextlib.contextmanager
def disable_inview_messages():
	"""
	Disable in-view help messages during the context
	"""

	original = cmds.optionVar(query='inViewMessageEnable')
	cmds.optionVar(iv=('inViewMessageEnable', 0))
	try:
		yield
	finally:
		cmds.optionVar(iv=('inViewMessageEnable', original))


@contextlib.contextmanager
def maintain_camera_on_panel(panel, camera):
	"""
	Tries to maintain given camera on given panel during the context
	:param panel: str, name of the panel to focus camera on
	:param camera: str, name of the camera we want to focus
	"""

	state = dict()
	if not (not hasattr(cmds, 'about') or cmds.about(batch=True)):
		cmds.lookThru(panel, camera)
	else:
		state = dict((camera, cmds.getAttr(camera + '.rnd')) for camera in cmds.ls(type='camera'))
		cmds.setAttr(camera + '.rnd', True)
	try:
		yield
	finally:
		for camera, renderable in state.items():
			cmds.setAttr(camera + '.rnd', renderable)


@contextlib.contextmanager
def reset_time():
	"""
	The time is reset once the context is finished
	"""

	current_time = cmds.currentTime(query=True)
	try:
		yield
	finally:
		cmds.currentTime(current_time)


@contextlib.contextmanager
def isolated_nodes(nodes, panel):
	"""
	Context manager used for isolating given nodes in  given panel
	"""

	if nodes is not None:
		cmds.isolateSelect(panel, state=True)
		for obj in nodes:
			cmds.isolateSelect(panel, addDagObject=obj)
	yield


def to_qt_object(maya_name: str, qobj=None):
	"""
	Returns an instance of the Maya UI element as a QWidget
	"""

	if not qobj:
		qobj = QWidget
	ptr = OpenMayaUI1.MQtUtil.findControl(maya_name)
	if ptr is None:
		ptr = OpenMayaUI1.MQtUtil.findLayout(maya_name)
	if ptr is None:
		ptr = OpenMayaUI1.MQtUtil.findMenuItem(maya_name)
	if ptr is not None:
		return wrapinstance(int(ptr), qobj)
	return None


def to_maya_object(qt_object):
	"""
	Returns a QtObject as Maya object
	"""

	return OpenMayaUI1.MQtUtil.fullName(unwrapinstance(qt_object))


def parent_widget(widget):
	"""
	Returns given QWidget Maya UI parent
	:param widget: QWidget, Qt widget to get parent for
	:return: QWidget
	"""

	ptr = OpenMayaUI1.MQtUtil.getParent(unwrapinstance(widget))
	return wrapinstance(int(ptr))


def ui_gvars():
	"""
	Returns a list with all UI related vars used by Maya
	:return: list<str>
	"""

	gui_vars = list()
	for g in [x for x in sorted(mel.eval('env')) if x.find('$g') > -1]:
		try:
			var_type = mel.eval('whatIs "{0}"'.format(g))
			if not var_type == 'string variable':
				raise TypeError
			tmp = mel.eval('string $temp = {0};'.format(g))
			if tmp is None:
				raise TypeError
			target_widget = to_qt_object(maya_name=tmp)
			widget_type = type(target_widget)
			if widget_type is None:
				raise ValueError
		except Exception:
			continue
		gui_vars.append([g, widget_type.__name__])
	return gui_vars


def create_dock_window(window, dock_area='right', allowed_areas=None):
	"""
	Docks given window in Maya (used in conjunction with DockedWindow class from window.py module)
	:param window: DockedWindow, UI we want to attach into Maya UI
	:param dock_area: str, area where we want to dock the UI
	:param allowed_areas: list<str>, list of allowed areas for the dock UI
	:return:
	"""

	allowed_areas = allowed_areas or ['left', 'right']
	ui_name = str(window.objectName())
	ui_title = str(window.windowTitle())
	dock_name = '{}Dock'.format(ui_name)
	dock_name = dock_name.replace(' ', '_').replace('-', '_')
	path = 'MayaWindow|{}'.format(dock_name)
	if cmds.dockControl(path, exists=True):
		cmds.deleteUI(dock_name, control=True)
	mel.eval('updateRendererUI;')

	try:
		dock = DockWrapper()
		dock.set_dock_name(dock_name)
		dock.set_name(ui_name)
		dock.set_label(ui_title)
		dock.set_dock_area(dock_area)
		dock.set_allowed_areas(allowed_areas)
		dock.create()
		window.show()
	except Exception:
		logger.warning('{} window failed to load. Maya may need to finish loading'.format(ui_name))
		logger.error(traceback.format_exc())


def is_window_floating(window_name):
	"""
	Returns whether given window is floating
	:param window_name: str
	:return: bool
	"""

	if helpers.get_version() < 2017:
		floating = cmds.dockControl(window_name, floating=True, query=True)
	else:
		floating = cmds.workspaceControl(window_name, floating=True, query=True)

	return floating


def progress_bar():
	"""
	Returns Maya progress bar
	:return: str
	"""

	main_progress_bar = mel.eval('$tmp = $gMainProgressBar')
	return main_progress_bar


def node_editors():
	"""
	Returns all node editors panels opened in Maya
	"""

	found = list()
	for panel in cmds.getPanel(type='scriptedPanel'):
		if cmds.scriptedPanel(panel, query=True, type=True) == 'nodeEditorPanel':
			node_editor = panel + 'NodeEditorEd'
			found.append(node_editor)

	return found


def add_maya_widget(layout, layout_parent, maya_fn, *args, **kwargs):
	if not cmds.window('tempAttrWidgetWin', exists=True):
		cmds.window('tempAttrWidgetWin')

	cmds.columnLayout(adjustableColumn=True)
	try:
		maya_ui = maya_fn(*args, **kwargs)
		qtobj = to_qt_object(maya_ui)
		qtobj.setParent(layout_parent)
		layout.addWidget(qtobj)
	finally:
		if cmds.window('tempAttrWidgetWin', exists=True):
			cmds.deleteUI('tempAttrWidgetWin')

	return qtobj, maya_ui


def add_attribute_widget(layout, layout_parent, lbl, attr=None, attr_type='cbx', size=None, attr_changed_fn=None):

	qt_object = None
	size = size or [10, 60, 40, 80]

	if attr and not cmds.objExists(attr):
		return False

	if not cmds.window('tempAttrWidgetWin', exists=True):
		cmds.window('tempAttrWidgetWin')

	cmds.columnLayout(adjustableColumn=True)

	ui_item = None
	try:
		if attr_type == 'cbx':
			ui_item = cmds.checkBox(label=lbl, v=False, rs=False, w=60)
			cmds.checkBox(ui_item, changeCommand=lambda attr_name: attr_changed_fn(attr_name), edit=True)
			cmds.connectControl(ui_item, attr)

		if attr_type == 'color':
			ui_item = cmds.attrColorSliderGrp(
				label=lbl, attribute=attr, cl4=['left', 'left', 'left', 'left'], cw4=[10, 15, 50, 80])

		if attr_type == 'floatSlider':
			ui_item = cmds.attrFieldSliderGrp(
				label=lbl, attribute=attr, cl4=['left', 'left', 'left', 'left'], cw4=size, pre=2)
			cmds.attrFieldSliderGrp(ui_item, changeCommand=lambda *args: attr_changed_fn(attr), edit=True)

		if attr_type == 'floatSliderMesh':
			ui_item = cmds.attrFieldSliderGrp(
				label=lbl, attribute=attr, cl3=["left", "left", "left"], cw3=size, pre=2)
			cmds.attrFieldSliderGrp(ui_item, changeCommand=lambda *args: attr_changed_fn(attr), edit=True)

		if attr_type == 'float2Col':
			ui_item = cmds.attrFieldSliderGrp(label=lbl, attribute=attr, cl2=["left", "left"], cw2=size, pre=2)
			cmds.attrFieldSliderGrp(ui_item, changeCommand=lambda *args: attr_changed_fn(attr), edit=True)

		if ui_item:
			qt_object = to_qt_object(ui_item)
			qt_object.setParent(layout_parent)
			layout.addWidget(qt_object)
	finally:
		if cmds.window('tempAttrWidgetWin', exists=True):
			cmds.deleteUI('tempAttrWidgetWin')

	return qt_object


def current_model_panel():
	"""
	Returns current model panel name
	:return: str
	"""

	current_panel = cmds.getPanel(withFocus=True)
	current_panel_type = cmds.getPanel(typeOf=current_panel)
	if current_panel_type not in ['modelPanel']:
		return None

	return current_panel


def open_render_settings_window():
	"""
	Opens Maya Render Settings window
	"""

	mel.eval('unifiedRenderGlobalsWindow')


def delete_dock_control(control_name):
	"""
	Handles the deletion of a dock control with a specific name
	:param control_name: str
	:return: bool
	"""

	if cmds.dockControl(control_name, query=True, exists=True):
		floating = cmds.dockControl(control_name, query=True, floating=True)
		cmds.dockControl(control_name, edit=True, r=True)
		cmds.dockControl(control_name, edit=True, floating=False)
	else:
		floating = False

	window_wrap = maya_window(window_name=control_name)
	if window_wrap:
		if window_wrap.parent().parent() is not None:
			maya_window(window_name=control_name).parent().close()

	if floating is not None:
		try:
			cmds.dockControl(control_name, edit=True, floating=floating)
		except RuntimeError:
			pass

	return floating


def delete_workspace_control(control_name: str, reset_floating: bool = True) -> str:
	"""
	Handles the deletion of a workspace control with a specific name.

	:param str control_name: name of the workspace control object to delete.
	:param bool reset_floating: whether to resset workspace floating status.
	:return: name of the removed workspace control object.
	:rtype: str
	"""

	if cmds.workspaceControl(control_name, query=True, exists=True):
		floating = cmds.workspaceControl(control_name, query=True, floating=True)
		cmds.deleteUI(control_name)
	else:
		floating = None

	# If the window is not currently floating, we remove stored preferences
	if cmds.workspaceControlState(
			control_name, query=True, exists=True) and not (floating or floating and reset_floating):
		cmds.workspaceControlState(control_name, remove=True)

	return floating


def open_namespace_editor():
	"""
	Opens Maya Namespace Editor GUI
	"""

	mel.eval('namespaceEditor')


def open_reference_editor():
	"""
	Opens Maya Reference Editor GUI
	"""

	mel.eval('tearOffRestorePanel "Reference Editor" referenceEditor true')


# ===================================================================================
# QT RELATED FUNCTIONS
# Added here from tpDcc.libs.qt.core.qtutils to avoid the import of that module
# This is because DccServer needs this module and we should avoid to import unnecessary
# stuff here
# ===================================================================================

def wrapinstance(ptr, base=None):
	if ptr is None:
		return None

	ptr = int(ptr)
	if 'shiboken' in globals():
		if base is None:
			qObj = shiboken.wrapInstance(int(ptr), QObject)
			meta_obj = qObj.metaObject()
			cls = meta_obj.className()
			super_cls = meta_obj.superClass().className()
			if hasattr(QtGui, cls):
				base = getattr(QtGui, cls)
			elif hasattr(QtGui, super_cls):
				base = getattr(QtGui, super_cls)
			else:
				base = QWidget
		try:
			return shiboken.wrapInstance(int(ptr), base)
		except Exception:
			from PySide.shiboken import wrapInstance
			return wrapInstance(int(ptr), base)
	elif 'sip' in globals():
		base = QObject
		return shiboken.wrapinstance(int(ptr), base)
	else:
		print('Failed to wrap object ...')
		return None


def unwrapinstance(object):
	"""
	Unwraps objects with PySide
	"""

	return int(shiboken.getCppPointer(object)[0])


def maya_pointer_to_qt_object(long_ptr, qobj=None):
	"""
	Returns an instance of the Maya UI element as a QWidget
	"""

	if not qobj:
		qobj = QWidget

	return wrapinstance(long_ptr, qobj)


def open_graph_editor():
	"""
	Opens Graph Editor window
	"""

	cmds.GraphEditor()


def set_channel_box_at_top(channel_box, value):
	"""
	Sets given channel box to be at top.

	:param str channel_box: channel box name to set.
	:param bool value: whether to set on top or not.
	"""

	cmds.channelBox(channel_box, edit=True, containerAtTop=value)


def outliner_paths():
	"""
	Returns a list of all opened outliner paths.

	:return: list of outlinr paths.
	:rtype: list(str)
	"""

	return cmds.getPanel(type='outlinerPanel')


def outliners():
	"""
	Returns all opened outliner widget instances.

	:return: list of outliner widgets.
	:rtype: list(QWidget)
	"""

	return [to_qt_object(outliner_path) for outliner_path in outliner_paths()]


def set_maya_ui_container_display_settings(attrs_to_show_at_top=None, outliner_display_under_parent=None):
	"""
	Changes the container visibility in the outliner and channel box.

	:param bool or None attrs_to_show_at_top: if True, then the selected transform attributes will be displayed at the
		top.
	:param bool or None outliner_display_under_parent: if True, then DGContainrs will be hidden in the outliner.
	"""

	if attrs_to_show_at_top is not None and env.is_interactive():
		set_channel_box_at_top('mainChannelBox', attrs_to_show_at_top)
	if outliner_display_under_parent is not None and env.is_interactive():
		for outliner_path in outliner_paths():
			cmds.outlinerEditor(outliner_path, edit=True, showContainerContents=not outliner_display_under_parent)
			cmds.outlinerEditor(outliner_path, edit=True, showContainedOnly=not outliner_display_under_parent)


def switch_xray_joints():
	"""
	Switches current panel xray joints.
	"""

	current_panel = cmds.getPanel(withFocus=True)
	if cmds.modelEditor(current_panel, query=True, jointXray=True):
		cmds.modelEditor(current_panel, edit=True, jointXray=False)
	else:
		cmds.modelEditor(current_panel, edit=True, jointXray=True)


def set_xray_joints(flag, panel=4):
	"""
	Sets xray joints state.

	:param bool flag: whether to enable or disable xray joints.
	:param int panel: number of the panel to set xray joints status of.
	"""

	cmds.modelEditor(f'modelPanel{panel}', edit=True, jointXray=flag)


class DockWrapper(object):
	def __init__(self, settings=None):
		self._dock_area = 'right'
		self._dock_name = 'dock'
		self._allowed_areas = ['right', 'left']
		self._label = ''
		self._settings = settings
		self._name = ''

	# region Public Functions
	def create(self):
		floating = False

		if self._exists():
			cmds.dockControl(self._dock_name, visible=True)
		else:
			cmds.dockControl(self._dock_name, aa=self._allowed_areas, a=self._dock_area, content=self._name,
							 label=self._label, fl=floating, visible=True, fcc=self._floating_changed)

	def set_name(self, name):
		self._name = name

	def set_dock_area(self, dock_area):
		self._dock_area = dock_area

	def set_dock_name(self, dock_name):
		self._dock_name = dock_name

	def set_label(self, label):
		self._label = label

	def set_allowed_areas(self, areas):
		self._allowed_areas = areas

	def _floating_changed(self):
		if self._settings:
			floating = is_window_floating(window_name=self._dock_name)
			self._settings.set('floating', floating)

	def _exists(self):
		return cmds.dockControl(self._dock_name, exists=True)


class ManageNodeEditors(object):
	def __init__(self):
		self.node_editors = node_editors()
		self._additive_state_dict = dict()
		for editor in self.node_editors:
			current_value = cmds.nodeEditor(editor, query=True, ann=True)
			self._additive_state_dict[editor] = current_value

	def turn_off_add_new_nodes(self):
		for editor in self.node_editors:
			cmds.nodeEditor(editor, e=True, ann=False)

	def restore_add_new_nodes(self):
		for editor in self.node_editors:
			cmds.nodeEditor(editor, e=True, ann=self._additive_state_dict[editor])
