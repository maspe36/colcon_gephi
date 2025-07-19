import os

import networkx as nx
from colcon_core.package_selection import get_package_descriptors, add_arguments
from colcon_core.plugin_system import satisfies_version
from colcon_core.verb import VerbExtensionPoint
from networkx.drawing import nx_pydot


class GephiGraphVerb(VerbExtensionPoint):
    """
    Generate a dot file that can be inspected in [Gephi](https://github.com/gephi/gephi).
    """

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(VerbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        # I really don't understand why this is needed,
        # but without it `get_package_descriptors` returns an empty set.
        parser.add_argument(
            '--build-base',
            default='build',
            help='The base path for all build directories (default: build)')

        add_arguments(parser)

    def main(self, *, context):  # noqa: D102
        args = context.args

        descriptors = get_package_descriptors(args)

        graph = nx.DiGraph()

        packages_in_ws = set([d.name for d in descriptors])

        for descriptor in descriptors:
            graph.add_node(descriptor.name,
                           path=descriptor.path,
                           type=descriptor.type,
                           metadata=descriptor.metadata)

            # Only find edges for this node that exist within this workspace
            for dep_type in ['build', 'run', 'test']:
                for dependency in descriptor.dependencies[dep_type]:
                    if dependency in packages_in_ws:
                        graph.add_edge(descriptor.name, dependency, type=dep_type)

        # For now, default to where this command was run
        print(os.getcwd())
        name = os.path.basename(os.getcwd())
        nx_pydot.write_dot(graph, f'{name}.dot')

        print(f'Wrote dot file to {name}.dot')
