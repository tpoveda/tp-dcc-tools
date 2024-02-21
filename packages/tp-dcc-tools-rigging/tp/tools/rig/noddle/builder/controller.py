from __future__ import annotations

from tp.core import dcc

if dcc.is_maya():
    from tp.tools.rig.noddle.builder.controllers.maya.controller import MayaNoddleController as NoddleController
elif dcc.is_standalone():
    from tp.tools.rig.noddle.builder.controllers.standalone import StandaloneNoddleController as NoddleController
else:
    raise ImportError(f'Unable to import DCC NoddleController class for: {dcc.current_dcc()}')
