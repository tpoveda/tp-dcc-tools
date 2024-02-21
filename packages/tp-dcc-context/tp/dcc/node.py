from tp.core import dcc

if dcc.is_maya():
    from tp.dcc.maya.node import FnNode
elif dcc.is_max():
    from tp.dcc.max.node import FnNode
elif dcc.is_standalone():
    from tp.dcc.standalone.node import FnNode
else:
    raise ImportError(f'Unable to import DCC FnNode class for: {dcc.current_dcc()}')
