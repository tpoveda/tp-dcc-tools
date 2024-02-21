class CritError(Exception):

    MSG = ''

    def __init__(self, msg: str = '', *args, **kwargs):
        super().__init__(str(msg), *args)


class CritRigDuplicationError(CritError):

    MSG = 'Duplicated rigs in the scene, please use namespace filtering: {}'

    def __init__(self, dupes, *args, **kwargs):
        msg = self.MSG.format(dupes)
        super().__init__(msg, *args, **kwargs)


class CritComponentDoesNotExistError(CritError):

    MSG = 'Component does not exist in the scene.'


class CritMissingComponentType(CritError):

    MSG = 'Missing component of type: {}, from the CRIT components manager.'

    def __init__(self, component_type, *args, **kwargs):
        msg = self.MSG.format(component_type)
        super(CritMissingComponentType, self).__init__(msg, *args, **kwargs)


class CritInitializeComponentError(CritError):

    MSG = 'Failed to initialize component: {}'

    def __init__(self, component_name, *args, **kwargs):
        msg = self.MSG.format(component_name)
        super(CritInitializeComponentError, self).__init__(msg, *args, **kwargs)


class CritMissingRootTransform(CritError):

    MSG = 'Missing Root transform on meta node: {}'

    def __init__(self, meta_name, *args, **kwargs):
        msg = self.MSG.format(meta_name)
        super(CritMissingRootTransform, self).__init__(msg, *args, **kwargs)


class CritBuildComponentUnknownError(CritError):

    MSG = 'Unknown build guides error'


class CritBuildComponentGuideUnknownError(CritError):

    MSG = 'Unknown build guide error'


class CritBuildComponentSkeletonUnknownError(CritError):

    MSG = 'Unknown build skeleton error'


class CritBuildComponentRigUnknownError(CritError):

    MSG = 'Unknown build rig error'


class CritMissingMetaNode(CritError):

    MSG = 'Attached meta node is not a valid one'


class CritInvalidInputNodeMetaData(CritError):

    MSG = 'Input Layer MetaData is missing an input node connection'


class CritInvalidOutputNodeMetaData(CritError):

    MSG = 'Output Layer MetaData is missing an input node connection'


class CritMissingControlError(CritError):

    MSG = 'Missing control by ID: {}'


class CritMissingRigForNode(CritError):

    MSG = 'Node is not attached to a rig'


class CritTemplateAlreadyExistsError(CritError):

    MSG = 'Template path: {} already exists!'


class CritTemplateMissingComponents(CritError):

    MSG = 'No component specified in template: {}'


class CritTemplateRootPathDoesNotExist(CritError):

    MSG = 'Template root path does not exist on disk: {}'
