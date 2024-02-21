from __future__ import annotations

import typing


from tp.libs.rig.crit.core import component

if typing.TYPE_CHECKING:
	from tp.libs.rig.crit.core.rig import Rig


def align_guides(rig: Rig, components: list[component.Component]):
	"""
	Align all guides for the components of the given rig.

	:param Rig rig: rig instance which component guides we want to align.
	:param list[component.Component] components: list of components whose guides we want to align.
	"""

	config = rig.configuration
	with component.disconnect_components_context(components):
		for _component in components:
			if not config.auto_align_guides or not _component.has_guide():
				continue
			_component.align_guides()
