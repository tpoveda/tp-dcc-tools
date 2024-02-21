from __future__ import annotations

import abc
from copy import deepcopy
from itertools import chain
from typing import Any, Iterator
from collections.abc import MutableMapping, KeysView, ValuesView, ItemsView

from six import integer_types

from tp.core import log
from tp.dcc.abstract import node as abstract_node
from tp.dcc import node, mesh
from tp.common.python import helpers
from tp.common.math import scalar
from tp.dcc.dataclasses import vector

logger = log.tpLogger


class Influences(MutableMapping):
    """
    Overload of MutableMapping used to store influence objects
    """

    __slots__ = ('__objects__')

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.__objects__ = {}

        num_args = len(args)
        if num_args == 1:
            self.update(args[0])

    def __getitem__(self, index: int) -> node.Node | None:
        if isinstance(index, integer_types):
            return self.get(index, None)
        else:
            raise TypeError(f'__getitem__() expects an int ({type(index).__name__} given)!')

    def __setitem__(self, key: int, value: Any):
        influence = node.Node()
        success = influence.try_set_object(value)
        if success:
            self.__objects__[key] = influence
        else:
            raise TypeError(f'__setitem__() expects a valid object ({type(value).__name__} given)!')

    def __delitem__(self, key: int):
        del self.__objects__[key]

    def __contains__(self, item: Any) -> bool:
        return item in self.__objects__.values()

    def __iter__(self) -> Iterator[Any]:
        return iter(self.__objects__)

    def __len__(self) -> int:
        return len(self.__objects__)

    def keys(self) -> KeysView:
        """
        Returns a keys view for this collection.

        :return: collection keys.
        :rtype: KeysView
        """

        return self.__objects__.keys()

    def values(self) -> ValuesView:
        """
        Returns a values view for this collection.

        :return: values view.
        :rtype: ValuesView
        """

        return self.__objects__.values()

    def items(self) -> ItemsView:
        """
        Returns an items view for this collection.

        :return: items view.
        :rtype: ItemsView
        """

        return self.__objects__.items()

    def get(self, index: int, default: Any = None) -> node.Node | None:
        """
        Returns the influence object associated with the given index.

        :param int index: influence index.
        :param Any default: default value to return if influence with given index is not found.
        :return: influence object.
        :rtype: node.Node or None
        """

        return self.__objects__.get(index, default)

    def index(self, influence: Any) -> int | None:
        """
        Returns the index for the given influence.
        If no index is found, then None is returned.

        :param Any influence: influence to get index of.
        :return: influence index.
        :rtype: int or None
        """

        try:
            if isinstance(influence, str):
                influence = node.Node(influence)
            # Get associated value key.
            keys = list(self.__objects__.keys())
            values = list(self.__objects__.values())
            index = values.index(influence)
            return keys[index]
        except (ValueError, TypeError):
            return None

    def last_index(self) -> int:
        """
        Returns the last influence index in this collection.
        If no index found, -1 will be returned.

        :return: last influence index.
        :rtype: int
        """

        indices = list(self.keys())
        num_indices = len(indices)
        return indices[-1] if num_indices > 0 else -1

    def update(self, obj: dict, **kwargs):
        """
        Copies the values from the given object to this collection.

        :param dict obj: dictionary to copy values from.
        """

        for key in sorted(obj.keys()):
            self.__setitem__(key, obj[key])

    def clear(self):
        """
        Removes all the influences from this collection.
        """

        self.__objects__.clear()


class AbstractSkin(abstract_node.AFnNode):
    """
    Overloads of AbstractNode context class to handle behaviour for DCC skinning.
    """

    __slots__ = ('_influences', '_clipboard')

    def __init__(self, *args, **kwargs):
        self._influences = Influences()
        self._clipboard: dict[int, dict[int, float]] = {}

        super().__init__(*args, **kwargs)

    @property
    def clipboard(self) -> dict[int, dict[int, float]]:
        """
        Getter method that returns the clipboard.

        :return: clipboard.
        :rtype: dict[int, dict[int, float]]
        """

        return self._clipboard

    @classmethod
    @abc.abstractmethod
    def create(cls, mesh: mesh.Mesh) -> AbstractSkin:
        """
        Creates a skin and assigns it to the given mesh.

        :param mesh.Mesh mesh: mesh to apply skin to.
        :return: newly created skin.
        :rtype: AbstractSkin
        """

        pass

    @abc.abstractmethod
    def transform(self) -> Any:
        """
        Returns the transform node associated with this skin.

        :return: skin transform node.
        :rtype: Any
        """

        pass

    @abc.abstractmethod
    def shape(self) -> Any:
        """
        Returns teh shape node associated with this skin.

        :return: skin shape node.
        :rtype: Any
        """

        pass

    @abc.abstractmethod
    def intermediate_object(self) -> Any:
        """
        Returns the intermediate object associated with this skin.

        :return: intermediate object.
        :rtype: Any
        """

        pass

    @staticmethod
    def clamp(value: int | float, min_value: int | float = 0.0, max_value: int | float = 1.0) -> int | float:
        """
        Clamps the given value to the given range.

        :param int or float value: value to clamp.
        :param int or float min_value: minimum range value.
        :param int or float max_value: maximum range value.
        :return: clamped value.
        :rtype: int or float
        """

        return scalar.clamp(value, min_value=min_value, max_value=max_value)

    @abc.abstractmethod
    def iterate_vertices(self) -> Iterator[int]:
        """
        Returns a generator that yields vertex indices.

        :return: iterated vertex indices.
        :rtype: Iterator[int]
        """

        pass

    def vertices(self) -> list[int]:
        """
        Returns list of vertex indices.

        :return: vertex indices.
        :rtype: list[int]
        """

        return list(self.iterate_vertices())

    def iterate_control_points(
            self, *indices: int | list[int], cls: type = vector.Vector) -> Iterator[vector.Vector, vector.Vector]:
        """
        Returns a generator that yields the intermediate control points.

        :param int or list[int] indices: optional list of indices to iterate.
        :param type cls: class to return values with.
        :return: iterated intermediate control points.
        :rtype: Iterator[vector.Vector, vector.Vector]
        """

        return mesh.Mesh(self.intermediate_object()).iterate_vertices(*indices, cls=cls)

    def control_points(
            self, *indices: int | list[int], cls: type = vector.Vector) -> list[vector.Vector, vector.Vector]:
        """
        Returns list of intermediate control points.

        :param int or list[int] indices: optional list of indices to iterate.
        :param type cls: class to return values with.
        :return: control points.
        :rtype: list[vector.Vector, vector.Vector]
        """

        return list(self.iterate_control_points(*indices, cls=cls))

    def num_control_points(self) -> int:
        """
        Returns the number of control points from this skin.

        :return: number of control points from this skin.
        :rtype: int
        """

        return mesh.Mesh(self.intermediate_object()).num_vertices()

    @abc.abstractmethod
    def iterate_selection(self) -> Iterator[int]:
        """
        Returns a generator that yields the selected vertex elements.

        :return: iterated selected vertex elements.
        :rtype: Iterator[int]
        """

        pass

    def selection(self) -> list[int]:
        """
        Returns list of selected vertex elements.

        :return: selected vertex elements.
        :rtype: list[int]
        """

        return list(self.iterate_selection())

    @abc.abstractmethod
    def set_selection(self, vertices: list[int]):
        """
        Updates the active selection with the given supplied vertex elements.

        :param list[int] vertices: vertex elements to select.
        """

        pass

    @abc.abstractmethod
    def iterate_soft_selection(self) -> Iterator[dict[int, float]]:
        """
        Returns a generator that yields selected vertex-weight pairs.

        :return: iterated selected vertex-weight pairs.
        :rtype: Iterator[dict[int, float]]
        """

        pass

    def soft_selection(self) -> dict[int, float]:
        """
        Returns a dictionary of the selected vertex-weight pairs.

        :return: dictionary of the selected vertex-weight pairs.
        :rtype: dict[int, float]
        """

        return dict(self.iterate_soft_selection())

    @abc.abstractmethod
    def show_colors(self):
        """
        Enables color feedback for the associated mesh.
        """

        pass

    @abc.abstractmethod
    def hide_colors(self):
        """
        Disables color feedback for the associated mesh.
        """

        pass

    @abc.abstractmethod
    def refresh_colors(self):
        """
        Forces the vertex color display to redraw.
        """

        pass

    @abc.abstractmethod
    def iterate_influences(self) -> Iterator[tuple[int, Any]]:
        """
        Returns a generator that yields the influence id-objects pairs from the skin.

        :return: iterated influence id-objects pairs from the skin.
        :rtype: Iterator[tuple[int, Any]]
        """

        pass

    def influences(self) -> Influences:
        """
        Returns the influence id-objects pairs from the skin.

        :return: list of influence id-objects pairs from the skin.
        :rtype: Influences
        """

        current = len(self._influences)
        if current != self.num_influences():
            self._influences.clear()
            self._influences.update(dict(self.iterate_influences()))

        return self._influences

    def influence_names(self) -> dict[int, str]:
        """
        Returns the influence names from this skin.

        :return: influence names from this skin.
        :rtype: dict[int, str]
        """

        return {influence_id: influence.absoluteName() for (influence_id, influence) in self.influences().items()}

    @abc.abstractmethod
    def num_influences(self) -> int:
        """
        Returns the number of influences in use by this skin.

        :return: number of influences.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def add_influence(self, *influences: Any | list[Any]):
        """
        Adds an influence to this skin.

        :param Any or list[Any] influences: influence(s) to add.
        """

        pass

    @abc.abstractmethod
    def remove_influence(self, *influence_ids: int | list[int]):
        """
        Removes an influence from this skin.

        :param int or list[int] influence_ids: influence IDs to remove.
        """

        pass

    @abc.abstractmethod
    def max_influences(self) -> int:
        """
        Returns the number of maximum influences for this skin.

        :return: maximum number of influences.
        :rtype: int
        """

        pass

    @abc.abstractmethod
    def set_max_influences(self, count: int):
        """
        Updates the maximum number of influences for this skin.

        :param int count: new maximum number of influences.
        """

        pass

    @abc.abstractmethod
    def select_influence(self, influence_id: int):
        """
        Selects the influence with given index.

        :param int influence_id: index of the influence to select.
        """

        pass

    def used_influence_ids(self, *indices: int | list[int]) -> list[int]:
        """
        Returns a list of active influence IDs from the given vertices.

        :param int or list[int] indices: vertex indices to get influence IDs from. If not given, all vertices will be
            evaluated.
        :return: list of active influence IDs from the given vertices.
        :rtype: list[int]
        """

        influence_ids = set()
        for (vertex_index, vertex_weights) in self.iterate_vertex_weights(*indices):
            influence_ids = influence_ids.union(set(vertex_weights.keys()))

        return list(influence_ids)

    def unused_influence_ids(self, *indices: int | list[int]) -> list[int]:
        """
        Returns a list of inactive influence IDs from the given vertices.

        :param int or list[int] indices: vertex indices to get influence IDs from. If not given, all vertices will be
            evaluated.
        :return: list of inactive influence IDs from the given vertices.
        :rtype: list[int]
        """

        return list(set(self.influences().keys()) - set(self.unused_influence_ids(*indices)))

    def create_influence_map(
            self, other_skin: AbstractSkin, influence_ids: list | tuple | set | None = None) -> dict[int, int]:
        """
        Creates an influence map for transferring weights from this skin to the given one.

        :param AbstractSkin other_skin: skin to create influence map for.
        :param list or tuple or set or None influence_ids: optional list of influence indexes that can be supplied to
            simplify the map.
        :return: influence map dictionary.
        :rtype: dict[int, int]
        :raises TypeError: if given skin is not valid.
        :raises KeyError: if we are not able to find a matching ID for one of the influences.
        """

        # Check if skin is valid.
        if not other_skin.is_valid():
            raise TypeError(f'create_influence_map() expects a valid skin ({type(other_skin).__name__} given)!')

        # Check if influence IDs were supplied
        influences = self.influences()
        influence_ids = influence_ids or list(influences.keys())

        # Iterate through influences and try to find a match for the influence name.
        other_influences = other_skin.influences()
        influence_map: dict[int, int] = {}
        for influence_id in influence_ids:
            influence = influences[influence_id]
            remapped_id = other_influences.index(influence.object())
            if remapped_id is not None:
                influence_map[influence_id] = remapped_id
            else:
                # raise KeyError(f'Unable to find a matching ID for {influence.name()} influence!')
                logger.warning(f'Unable to find a matching ID for {influence.name()} influence!')

        logger.debug(f'Successfully created {influence_map} influence map!')

        return influence_map

    def remap_vertex_weights(
            self, vertex_weights: dict[int, dict[int, float]],
            influence_map: dict[int, int]) -> dict[int, dict[int, float]]:
        """
        Remaps the given vertex weights using the given influence map.

        :param dict[int, dict[int, float]] vertex_weights: dictionary containing vertex weights.
        :param dict[int, int] influence_map: influence mapping.
        :return: remapped vertex weights.
        :rtype: dict[int, dict[int, float]]
        :raises TypeError: if given arguments has no expected type.
        """

        if not isinstance(vertex_weights, dict) or not isinstance(influence_map, dict):
            raise TypeError(f'remap_vertex_weights() expects a dict ({type(vertex_weights).__name__} given)!')

        updates = {}
        for (vertex_index, weights) in vertex_weights.items():
            updates[vertex_index] = {}
            for (influence_id, weight) in weights.items():
                # Get remapped id and check if weights should be merged.
                new_influence_id = influence_map[influence_id]
                logger.debug(f'Influence ID: {influence_id}, has been remapped to: {new_influence_id}')
                if new_influence_id in updates[vertex_index]:
                    updates[vertex_index][new_influence_id] += weight
                else:
                    updates[vertex_index][new_influence_id] = weight

        return updates

    def vertices_by_influence_id(self, *influence_ids: int | list[int]) -> list[int]:
        """
        Returns a list of vertices associated with the given influence IDs.

        :param int or list[int] influence_ids: influence indexes to get vertices of.
        :return: list of vertices associated with the given influence IDs.
        :rtype: list[int]
        """

        vertex_indices: list[int] = []
        for (vertex_index, weights) in self.iterate_vertex_weights():
            if any([influenceId in weights for influenceId in influence_ids]):
                vertex_indices.append(vertex_index)

        return vertex_indices

    def find_root(self) -> Any:
        """
        Returns the skeleton root associated with this skin.

        :return: skeleton root.
        :rtype: Any
        """

        influences = self.influences()
        common_path = self.find_common_path(*influences.values())

        if helpers.is_null_or_empty(common_path):
            return None

        strings = common_path.split('/')
        return node.Node(strings[0]).object()

    @abc.abstractmethod
    def iterate_vertex_weights(self, *indices: int | list[int]) -> Iterator[tuple[int, dict[int, float]]]:
        """
        Returns a generator that yields vertex-weights pairs from this node.

        :param int or list[int] indices: indices to iterate. If not given, all weights will be yielded.
        :return: iterated vertex-weights pairs from this node.
        :rtype: Iterator[tuple[int, dict[int, float]]]
        """

        pass

    def vertex_weights(self, *indices: int | list[int]) -> dict[int, dict[int, float]]:
        """
        Returns a dictionary of vertex-weights pairs from this node.

        :param int or list[int] indices: indices to iterate. If not given, all weights will be yielded.
        :return: vertex-weights pairs from this node.
        :rtype: dict[int, dict[int, float]]
        """

        return dict(self.iterate_vertex_weights(*indices))

    def set_weights(self, weights: dict[int, float], target: int, source: list[int], amount: float, falloff: float = 1.0) -> dict[int, float]:
        """
        Sets the given target index to the given amount while preserving normalization.

        :param dict[int, float] weights: weights mapping to set.
        :param int target: target index.
        :param list[int] source: sources list.
        :param float amount: amount to apply.
        :param float falloff: falloff to apply.
        :return: updated vertex weights.
        :rtype: dict[int, float]
        :raises TypeError: if argument types are not valid.
        :raises TypeError: if we are unable to manipulate vertex weights from given arguments.
        """

        # Check weights type, source and target influences and amount type.
        if not isinstance(weights, dict):
            raise TypeError(f'set_weights() expects a dict ({type(weights).__name__} given)!')
        if not isinstance(target, int) or not isinstance(source, list):
            raise TypeError('set_weights() expects a valid target and source influences!')
        if not isinstance(amount, float):
            raise TypeError(f'set_weights() expects a valid amount ({type(amount).__name__} given)!')

        # Copy weights to manipulate.
        new_weights = deepcopy(weights)
        soft_amount = self.clamp(amount) * self.clamp(falloff)
        total = sum([weights.get(x, 0.0) for x in source])
        logger.debug(f'Weights available to redistribute: {total}')

        # Check if influence exists on vertex.
        influence_ids = new_weights.keys()
        num_influences = len(influence_ids)
        max_influences = self.max_influences()

        if (target in influence_ids) or (target not in influence_ids and num_influences < max_influences):

            # Determine redistribution method:
            #   - If amount is less than current then give those weights back to the source list.
            #   - If amount is greater than current then take weights from the source list.
            current = new_weights.get(target, 0.0)
            if soft_amount < current and 0.0 < total:
                # Redistribute target weight to source influences and apply percentage of difference to influence
                diff = current - soft_amount
                for (influence_id, weight) in new_weights.items():
                    if influence_id in source:
                        percent = weight / total
                        new_weight = weight + (diff * percent)
                        new_weights[influence_id] = new_weight
                # Set target to amount.
                new_weights[target] = current - diff
            elif soft_amount > current and 0.0 < total:
                # Make sure amount has not exceeded total.
                diff = soft_amount - current
                if diff >= total:
                    logger.debug(f'Insufficient weights to pull from, clamping amount to: {total}')
                    diff = total
                # Redistribute source weights to target influences.
                for (influence_id, weight) in new_weights.items():
                    if influence_id in source:
                        # Reduce influence based on percentage of difference.
                        percent = weight / total
                        new_weight = weight - (diff * percent)

                        new_weights[influence_id] = new_weight
                # Set target to accumulated amount.
                new_weights[target] = current + diff
        elif target not in influence_ids and num_influences >= max_influences:
            # Check if all influences are being replaced.
            if scalar.is_close(amount, total, absolute_tolerance=1e-06):
                new_weights = {target: 1.0}
            elif amount == 0.0:
                logger.debug('No weights available to redistribute!')
            else:
                logger.warning('Cannot exceed max influences!')
        else:
            raise TypeError('set_weights() was unable to manipulate vertex weights from supplied arguments!')

        return new_weights

    def scale_weights(
            self, weights: dict[int, float], target: int, source: list[int], amount: float,
            falloff: float = 1.0) -> dict[int, float]:
        """Scales the given target ID to the given amount while preserving normalization.

        :param dict[int, float] weights: weights mapping to scale.
        :param int target: target index.
        :param list[int] source: sources list.
        :param float amount: amount to apply.
        :param float falloff: falloff to apply.
        :return: updated vertex weights.
        :rtype: dict[int, float]
        """

        current = weights.get(target, 0.0)
        amount = current + sum([(weights.get(influence_id, 0.0) * amount) * falloff for influence_id in source])

        logger.debug(f'Changing influence ID: {target}, from {current} to {amount}')

        return self.set_weights(weights, target, source, amount)

    def increment_weights(
            self, weights: dict[int, float], target: int, source: list[int], amount: float,
            falloff: float = 1.0) -> dict[int, float]:
        """Increments the given target ID to the given amount while preserving normalization.

        :param dict[int, float] weights: weights mapping to increment.
        :param int target: target index.
        :param list[int] source: sources list.
        :param float amount: amount to apply.
        :param float falloff: falloff to apply.
        :return: updated vertex weights.
        :rtype: dict[int, float]
        """

        current = weights.get(target, 0.0)
        amount = current + (amount * falloff)

        logger.debug(f'Changing influence ID: {target}, from {current} to {amount}')

        return self.set_weights(weights, target, source, amount)

    def remove_zero_weights(self, weights: dict[int, float]) -> dict[int, float]:
        """Removes any zeroes from the given weights.

        :param dict[int, float] weights: weights mapping to clean.
        :return: updated vertex weights.
        :rtype: dict[int, float]
        """

        return {influence_id: weight for (influence_id, weight) in weights.items() if not scalar.is_close(0.0, weight)}

    def is_normalized(self, weights: dict[int, float]) -> bool:
        """Returns whether the given weights have been normalized.

        :param dict[int, float] weights: weights to check.
        :return: True if given weights are normalized; False otherwise.
        :rtype: bool
        """

        if not isinstance(weights, dict):
            raise TypeError(f'is_normalized() expects a dict ({type(weights).__name__} given)!')

        # Check influence weight total.
        total = sum([weight for (influenceId, weight) in weights.items()])
        logger.debug(f'Supplied influence weights equal {total}.')

        return scalar.is_close(1.0, total)

    def normalize_weights(self, weights: dict[int, float], maintain_max_influences: bool = True) -> dict[int, float]:
        """Normalizes the given vertex weights.

        :param dict[int, float] weights: weights to normalize.
        :param bool maintain_max_influences: whether to maintain max influences after normalization.
        :return: updated weights.
        :rtype: dict[int, float]
        :raises TypeError: if given weights are not a valid dict.
        :raises TypeError: if the total of weights is zero.
        """

        if not isinstance(weights, dict):
            raise TypeError(f'normalize_weights() expects a dict ({type(weights).__name__} given)!')

        # Check if influences should be pruned.
        if maintain_max_influences:
            weights = self.cap_weights(weights)

        # Check if weights have already been normalized.
        is_normalized = self.isNormalized(weights)
        if is_normalized:
            logger.debug('Vertex weights have already been normalized.')
            return weights

        # Check if weights can be normalized.
        total = sum(weights.values())
        if total == 0.0:
            raise TypeError('Cannot normalize influences from zero weights!')

        # Scale weights to equal one.
        scale = 1.0 / total
        for influence_id, weight in weights.items():
            normalized = (weight * scale)
            weights[influence_id] = normalized
            logger.debug(f'Normalizing influence ID: {influence_id}, from {weight} to {normalized}')

        return weights

    def prune_weights(self, weights: dict[int, float], tolerance: float = 1e-3):
        """Caps the given weights to meet the maximum number of weighted influences.

        :param dict[int, float] weights: weights to prune.
        :param bool tolerance: tolerance bias value.
        :return: updated weights.
        :rtype: dict[int, float]
        :raises TypeError: if given weights are not a valid dict.
        """

        if not isinstance(weights, dict):
            raise TypeError(f'prune_weights() expects a dict ({type(weights).__name__} given)!')

        pruned_weights = {
            influence_id: influence_weight for (
                influence_id, influence_weight) in weights.items() if influence_weight >= tolerance}

        return self.normalize_weights(pruned_weights)

    def cap_weights(self, weights: dict[int, float]) -> dict[int, float]:
        """Caps the given vertex weights to meet the maximum number of weighted influences.

        :param dict[int, float] weights: weights to cap.
        :return: updated weights.
        :rtype: dict[int, float]
        """

        if not isinstance(weights, dict):
            raise TypeError(f'cap_weights() expects a dict ({type(weights).__name__} given)!')

        # Check if any influences have dropped below limit
        influences = self.influences()
        for influence_id, weight in weights.items():
            if scalar.is_close(0.0, weight) or influences[influence_id] is None:
                weights[influence_id] = 0.0
            else:
                logger.debug(f'Skipping influence ID: {influence_id}')

        # Check if influences have exceeded max allowances
        num_influences = len(weights)
        max_influences = self.max_influences()
        if num_influences > max_influences:
            # Order influences from lowest to highest and replace influences with zero values.
            ordered_influences = sorted(weights, key=weights.get, reverse=False)
            diff = num_influences - max_influences
            for i in range(diff):
                influence_id = ordered_influences[i]
                weights[influence_id] = 0.0
        else:
            logger.debug('Vertex weights have not exceeded max influences.')

        return weights

    def average_weights(self, weights: dict[int, float], maintain_max_influences: bool = True) -> dict[int, float]:
        """Averages the given vertex weights.

        :param dict[int, float] weights: weights to average.
        :param bool maintain_max_influences: whether to maintain max influences after normalization.
        :return: updated weights.
        :rtype: dict[int, float]
        """

        average: dict[int, float] = {}

        # Iterate through copied weights.
        for influence_id, vertex_weight in weights.items():
            # Check if influence key already exists.
            if influence_id not in average:
                average[influence_id] = weights[influence_id]
            else:
                average[influence_id] += weights[influence_id]

        return self.normalize_weights(average, maintain_max_influences=maintain_max_influences)

    def weighted_average_weights(
            self, start_weights: dict[int, float], end_weights: dict[int, float],
            percent: int | float = 0.5) -> dict[int, float]:
        """Averages given vertex weights based on given normalized percentage.

        :param dict[int, float] start_weights: start weights.
        :param dict[int, float] end_weights: end weights.
        :param int or float percent: normalized percentage.
        :return: updated weights.
        :rtype: dict[int, float]
        :raises TypeError: if given normalized percentage has not a valid type.
        """

        if not isinstance(percent, (int, float)):
            raise TypeError(f'weighted_average_weights() expects a float ({type(percent).__name__} given)!')

        # Merge dictionary keys using null values.
        weights = self.merge_dictionaries(start_weights, end_weights)
        influence_ids = weights.keys()
        for influenceId in influence_ids:
            # Get weight values and average weights.
            start_weight = start_weights.get(influenceId, 0.0)
            end_weight = end_weights.get(influenceId, 0.0)
            weight = (start_weight * (1.0 - percent)) + (end_weight * percent)
            weights[influenceId] = weight

        return self.normalize_weights(weights)

    @abc.abstractmethod
    def apply_vertex_weights(self, vertex_weights: dict[int, dict[int, float]]):
        """Assigns the given vertex weights to this skin.

        :param dict[int, dict[int, float]] vertex_weights: vertex weights to apply.
        """

        pass

    @staticmethod
    def merge_dictionaries(*args: dict | list[dict]) -> dict:
        """Combines any number of dictionaries together with null values.

        :param dict or list[dict] args: dictionaries to merge.
        :return: merged dictionary.
        :rtype: dict
        """

        influence_ids = set(chain(*[arg.keys() for arg in args]))
        return dict.fromkeys(influence_ids, 0.0)

    def inverse_distance_weights(
            self, vertex_weights: dict[int, dict[int, float]], distances: list[float],
            power: float = 2.0) -> dict[int, float]:
        """
        Averages given vertex weights based on the inverse distance.

        :param dict[int, dict[int, float]] vertex_weights: weights to average.
        :param list[float] distances: distances between vertices.
        :param float power: distance power.
        :return: updated weights.
        :rtype: dict[int, float]
        :raises TypeError: if the total number of given vertices does not match with the total number of given
            distances.
        """

        num_vertices = len(vertex_weights)
        num_distances = len(distances)
        if num_vertices != num_distances:
            raise TypeError('inverse_distance_weights() expects identical length lists!')

        # Merge dictionary keys using null values and iterate through influences.
        inverse_weights = self.merge_dictionaries(*list(vertex_weights.values()))
        influence_ids = inverse_weights.keys()
        for influenceId in influence_ids:
            # Collect weight values.
            weights = [x.get(influenceId, 0.0) for x in vertex_weights.values()]
            # Zip list and evaluate in parallel.
            numerator = 0.0
            denominator = 0.0
            for weight, distance in zip(weights, distances):
                clamped_distance = distance if distance > 0.0 else 1e-3
                numerator += weight / pow(clamped_distance, power)
                denominator += 1.0 / pow(clamped_distance, power)
            # Assign average to updates.
            inverse_weights[influenceId] = float(numerator / denominator)

        logger.debug(f'Inverse Distance: {inverse_weights}')

        return self.normalize_weights(inverse_weights)
