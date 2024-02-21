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


import tp.bootstrap
try:
    tp.bootstrap.shutdown()
except Exception:
    pass


# load framework
import tp.bootstrap
tp.bootstrap.init()
