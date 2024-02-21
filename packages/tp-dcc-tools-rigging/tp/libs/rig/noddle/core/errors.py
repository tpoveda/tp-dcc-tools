from __future__ import annotations


class NoddleError(Exception):

    MSG = ''

    def __init__(self, msg: str = '', *args, **kwargs):
        super().__init__(str(msg), *args)


class NoddleRigDuplicationError(NoddleError):

    MSG = 'Duplicated rigs in the scene, please use namespace filtering: {}'

    def __init__(self, dupes, *args, **kwargs):
        msg = self.MSG.format(dupes)
        super().__init__(msg, *args, **kwargs)


class NoddleComponentDoesNotExistError(NoddleError):

    MSG = 'Component does not exist in the scene.'


class NoddleMissingRootTransform(NoddleError):

    MSG = 'Missing Root transform on meta node: {}'

    def __init__(self, meta_name, *args, **kwargs):
        msg = self.MSG.format(meta_name)
        super().__init__(msg, *args, **kwargs)


class NoddleBuildComponentUnknownError(NoddleError):

    MSG = 'Unknown build component error'


class NoddleBuildComponentGuideUnknownError(NoddleError):

    MSG = 'Unknown build guide error'


class NoddleBuildComponentSkeletonUnknownError(NoddleError):

    MSG = 'Unknown build skeleton error'


class NoddleBuildComponentRigUnknownError(NoddleError):

    MSG = 'Unknown build component rig error'


class NoddleMissingComponentType(NoddleError):

    MSG = 'Missing component of type: {}, from Noddle components manager.'

    def __init__(self, component_type, *args, **kwargs):
        msg = self.MSG.format(component_type)
        super().__init__(msg, *args, **kwargs)


class NoddleInitializeComponentError(NoddleError):

    MSG = 'Failed to initialize component: {}'

    def __init__(self, component_name, *args, **kwargs):
        msg = self.MSG.format(component_name)
        super().__init__(msg, *args, **kwargs)


class NoddleMissingMetaNode(NoddleError):

    MSG = 'Attached meta node is not a valid one'


class NoddleInvalidInputNodeMetaData(NoddleError):

    MSG = 'Input Layer MetaData is missing an input node connection'


class NoddleInvalidOutputNodeMetaData(NoddleError):

    MSG = 'Output Layer MetaData is missing an input node connection'


class NoddleMissingControlError(NoddleError):

    MSG = 'Missing control by ID: {}'


class NoddleMissingRigForNode(NoddleError):

    MSG = 'Node is not attached to a rig'
