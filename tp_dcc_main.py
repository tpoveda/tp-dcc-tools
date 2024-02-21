import os
import sys

# Register environemnt variables
os.environ['TPDCC_ADMIN'] = 'True'
os.environ['TPDCC_ENV_DEV'] = 'True'
os.environ['TPDCC_TOOLS_ROOT'] = r'E:\tools\dev\tp-dcc-tools'
os.environ['TPDCC_DEPS_ROOT'] = r'E:\tools\dev\tp-dcc-tools\venv310\Lib\site-packages'

root_python_path = os.path.abspath(os.path.join(os.environ['TPDCC_TOOLS_ROOT'], 'bootstrap', 'python'))
if root_python_path not in sys.path:
    sys.path.append(root_python_path)


def reload_modules():
    """
    Function that forces the reloading of all related modules
    """

    modules_to_reload = ('tp',)
    for k in sys.modules.copy().keys():
        found = False
        for mod in modules_to_reload:
            if mod == k:
                del sys.modules[mod]
                found = True
                break
        if found:
            continue
        if k.startswith(modules_to_reload):
            del sys.modules[k]


import tp.bootstrap
try:
    tp.bootstrap.shutdown()
except Exception:
    pass
reload_modules()

# load framework
import tp.bootstrap
tp.bootstrap.init(package_version_file='package_version_standalone.config')

# from tp.core.managers import tools
# win = tools.ToolsManager().launch_tool_by_id('tp.rig.crit.naming')

# from tp.core import client
# maya_client = client.MayaClient()
# maya_client.execute('make_cube')