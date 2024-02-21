from tp.preferences import manager


def noddle_interface():
    """
    Returns the Noddle preference interface.

    :return: Noddle preference interface instance.
    :rtype: NoddlePreferenceInterface
    """

    return manager.preference().interface('noddle')
