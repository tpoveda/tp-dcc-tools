from overrides import override

from tp.core import tool
from tp.common.nodegraph import registers


class NoddleBuilderTool(tool.Tool):

    id = 'tp.rig.noddle.builder'
    creator = 'Tomi Poveda'
    tags = ['rig', 'script']

    @override
    def execute(self, *args, **kwargs):

        from tp.tools.rig.noddle.builder import controller, window
        noddle_controller = controller.NoddleController()
        noddle_controller.load_data_types()

        # Load nodes locally and update registers
        registers.load_plugins(noddle_controller.nodes_paths())

        win = window.NoddleBuilderWindow(controller=noddle_controller)
        win.show()

        return win


if __name__ == '__main__':

    # load framework
    import tp.bootstrap
    tp.bootstrap.init(package_version_file='package_version_standalone.config')

    # setup default project
    # TODO: remove
    from tp.libs.rig.noddle import api as noddle
    noddle.Project.set(r'E:\noddle\projects\characters')

    from tp.core.managers import tools
    tools.ToolsManager().launch_tool_by_id('tp.rig.noddle.builder')
