from __future__ import annotations

from typing import Any, Callable

from Qt.QtCore import QObject

from tp.common.python import helpers


class Model(QObject):
    """
    Class that exposes functions to store data and handles data updates automatically when UI is changed.
    """

    def __init__(self):
        super().__init__()

        self.state = helpers.ObjectDict()
        self._listeners = {}

    def update(self, key: str, value: Any):
        """
        Updates the data and calls all the corresponding listeners.

        :param str key: key to update.
        :param Any value: new value for given key.
        """

        if self.state.get(key) == value:
            return
        self.state[key] = value
        for listener in self._listeners.get(key, []):
            listener(value)

    def update_all(self):
        """
        Updates all listeners.
        """

        for key, value in self.state.items():
            for listener in self._listeners.get(key, []):
                listener(value)

    def updater(self, key: str) -> Callable:
        """
        Returns a callback which, when called, changes the data.

        :param str key: key to bind.
        :return: update callback for given key.
        :rtype: Callable
        """

        return lambda value: self.update(key, value)

    def listen(self, key: str, listener: Callable, value: Any = None):
        """
        Registers a listener for the given key.

        :param str key: listener key.
        :param Callable listener: widget function that will be called when controller data is updated.
        :param Any value: optinal value to initialize state with
        """

        self._listeners[key] = self._listeners.get(key, []) + [listener]
        if key not in self.state:
            self.state[key] = value


class Controller(QObject):
    """
    Simple Controller class that stores an instance to the model and can handle the logic of a tool.
    All DCC specific logic code should be handled by a controller.
    """

    def __init__(self, model: Model):
        super().__init__()

        self._model = model

    @property
    def model(self) -> Model:
        return self._model
