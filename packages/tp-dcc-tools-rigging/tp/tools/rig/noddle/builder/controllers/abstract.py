from __future__ import annotations

import abc


class AbstractNoddleController(abc.ABC):

    @abc.abstractmethod
    def open_file(self, file_path: str, force: bool = False) -> bool:
        """
        Open file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :param bool force: whether to force the opening of the file.
        :return: True if file was opened successfully; False otherwise.
        :rtype: bool
        """

        raise NotImplementedError

    @abc.abstractmethod
    def reference_file(self, file_path: str) -> bool:
        """
        References file within DCC scene.

        :param str file_path: absolute file path pointing to a valid Maya file.
        :return: True if file was referenced successfully; False otherwise.
        :rtype: bool
        """

        raise NotImplementedError

    @abc.abstractmethod
    def nodes_paths(self) -> list[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def load_data_types(self):
        raise NotImplementedError

    @abc.abstractmethod
    def reference_model(self):
        raise NotImplementedError

    @abc.abstractmethod
    def clear_all_references(self):
        raise NotImplementedError

    @abc.abstractmethod
    def increment_save_file(self, file_type):
        raise NotImplementedError

    @abc.abstractmethod
    def save_file_as(self, file_type):
        raise NotImplementedError

    @abc.abstractmethod
    def bind_skin(self):
        pass

    @abc.abstractmethod
    def detach_skin(self):
        pass

    @abc.abstractmethod
    def mirror_skin_weights(self):
        pass

    @abc.abstractmethod
    def copy_skin_weights(self):
        pass

    @abc.abstractmethod
    def export_asset_weights(self):
        pass

    @abc.abstractmethod
    def import_asset_weights(self):
        pass

    @abc.abstractmethod
    def export_selected_weights(self):
        pass

    @abc.abstractmethod
    def import_selected_weights(self):
        pass
