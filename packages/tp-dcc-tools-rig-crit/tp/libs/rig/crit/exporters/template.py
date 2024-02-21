from __future__ import annotations

import typing
import dataclasses

from overrides import override

from tp.core import output
from tp.libs.rig.crit.core import exporter
from tp.libs.rig.crit.core.rig import Rig

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.component import Component


@dataclasses.dataclass
class TemplateExportSettings:
    name: str = ''
    overwrite: bool = True
    components: list[Component] = dataclasses.field(default_factory=lambda: [])
    display_errors: bool = False
    folder_path: str | None = None


class TemplateExporterPlugin(exporter.ExporterPlugin):

    ID = 'critTemplate'

    @override(check_signature=False)
    def export_settings(self) -> TemplateExportSettings:
        """
        Returns the export settings instance which will be used in the `export` function.

        :return: export settings.
        :rtype: TemplateExportSettings
        """

        return TemplateExportSettings()

    @override(check_signature=False)
    def export(self, rig: Rig, export_options: TemplateExportSettings) -> str:
        """
        Exports the CRIT rig as a template.

        :param Rig rig: rig instance to export.
        :param TemplateExportSettings export_options: export options for this exporter to use.
       :return: export path.
        :rtype: str
        """

        if not rig or not isinstance(rig, Rig):
            output.display_warning('Must supply a valid rig to save a template.')
            return
        if not export_options.name:
            output.display_warning('Must supply a valid name for the template.')
            return
        if not export_options.overwrite:
            manager = rig.configuration.templates_manager()
            if manager.has_template(export_options.name):
                output.display_warning(f'Template already exists: {export_options.name}')
                return

        data = rig.serialize_from_scene(rig_components=export_options.components)
        path = rig.configuration.templates_manager().save_template(
            export_options.name, data, overwrite=export_options.overwrite,
            template_root_path=export_options.folder_path)

        return path
