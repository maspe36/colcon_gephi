import os
from pathlib import Path

import networkx as nx
from colcon_core.package_selection import get_package_descriptors, add_arguments
from colcon_core.plugin_system import satisfies_version
from colcon_core.verb import VerbExtensionPoint
from fs.errors import InvalidPath
from git import Repo, InvalidGitRepositoryError
from networkx.drawing import nx_pydot


def find_repo(path):
    """
    Get a git.Repo from the given path. If not found, search the
    parent folders until we hit the current working directory or return None.
    """

    if path == os.getcwd():
        return None

    try:
        return Repo(path)
    except InvalidGitRepositoryError:
        return find_repo(os.path.join(path, os.pardir))
    except:
        # Probably a weird setup, like not having an "origin" remote
        # or maybe symlinks? Either way, we give up.
        return None


class GephiGraphVerb(VerbExtensionPoint):
    """
    Generate a dot file that can be inspected in Gephi.
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
        packages_in_ws = set([d.name for d in descriptors])

        graph = nx.DiGraph()

        for descriptor in descriptors:
            metadata = descriptor.metadata

            if repo := find_repo(descriptor.path):
                if repo.remotes:
                    metadata['repo'] = Path(str(repo.remotes.origin.url)).stem
                    metadata['remote'] = repo.remotes.origin.url
                else:
                    metadata['repo'] = Path(repo.working_tree_dir).name

            graph.add_node(descriptor.name,
                           path=descriptor.path,
                           type=descriptor.type,
                           **metadata)

            # Only find edges for this node that exist within this workspace
            for dep_type in ['build', 'run', 'test']:
                for dependency in descriptor.dependencies[dep_type]:
                    if dependency in packages_in_ws:
                        graph.add_edge(descriptor.name, dependency, type=dep_type)

        # For now, default to where this command was run
        name = os.path.basename(os.getcwd())
        nx_pydot.write_dot(graph, f'{name}.dot')

        print(f'Wrote dot file to {name}.dot')
