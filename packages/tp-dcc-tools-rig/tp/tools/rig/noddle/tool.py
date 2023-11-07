from overrides import override

from tp.core import tool


class NoddleBuilderTool(tool.Tool):

    id = 'tp.rig.noddle.builder'
    creator = 'Tomi Poveda'
    tags = ['rig', 'script']

    @override
    def execute(self, *args, **kwargs):

        from tp.tools.rig.noddle.builder import client, window
        from tp.tools.rig.noddle.builder.graph import registers

        # Load nodes locally
        registers.load_plugins()

        # Force client to load nodes
        client = client.NoddleBuilderMayaClient()
        if client.is_host_online():
            client.execute('TP_DCC_RELOAD_MODULES')
            client.load_plugins()

        win = window.NoddleBuilderWindow(client=client)
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