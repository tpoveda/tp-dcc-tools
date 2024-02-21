from __future__ import annotations

from overrides import override

from tp.tools.rig.noddle.builder.controllers import abstract


class StandaloneNoddleController(abstract.AbstractNoddleController):

    @override
    def open_file(self, file_path: str, force: bool = False) -> bool:
        """
        Open file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :param bool force: whether to force the opening of the file.
        :return: True if file was opened successfully; False otherwise.
        :rtype: bool
        """

        return True

    @override
    def reference_file(self, file_path: str) -> bool:
        """
        References file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :return: True if file was referenced successfully; False otherwise.
        :rtype: bool
        """

        return True

    def nodes_paths(self) -> list[str]:
        return []

    @override
    def load_data_types(self):
        pass

    @override
    def reference_model(self):
        pass

    @override
    def clear_all_references(self):
        pass

    @override
    def increment_save_file(self, file_type):
        pass

    @override
    def save_file_as(self, file_type):
        pass
