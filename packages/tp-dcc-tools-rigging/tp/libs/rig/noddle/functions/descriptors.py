from __future__ import annotations


def path_as_descriptor_expression(path_parts: tuple[str, ...]) -> str:
    """
    Surrounds the given path parts with the descriptor attribute expression ("@{srts}").

    :param tuple[str] path_parts: path parts to convert to expression.
    :return: expressions for the given path parts.
    :rtype: str
    .. code-block:: python

        expression = path_as_descriptor_expression(('self', 'guide_layer', 'rootMotion''))
        // result = '@{self.guide_layer.rootMotion}'
    """

    return '@{' + '.'.join(path_parts) + '}'
