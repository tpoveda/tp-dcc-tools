from __future__ import annotations

from tp.core import dcc


if dcc.is_maya():
    from tp.dcc.maya.callback import FnCallback
elif dcc.is_max():
    from tp.dcc.max.callback import FnCallback
elif dcc.is_standalone():
    from tp.dcc.standalone.callback import FnCallback
else:
    raise ImportError(f'Unable to import DCC Mesh class for: {dcc.current_dcc()}')
