from tp.core import dcc

if dcc.is_maya():
    from tp.dcc.maya.scene import FnScene
elif dcc.is_max():
    from tp.dcc.max.scene import FnScene
elif dcc.is_standalone():
    from tp.dcc.standalone.scene import FnScene
else:
    raise ImportError(f'Unable to import DCC FnScene class for: {dcc.current_dcc()}')
