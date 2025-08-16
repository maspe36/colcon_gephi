import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Dict

import networkx as nx
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.package_selection import get_package_descriptors, add_arguments
from colcon_core.plugin_system import satisfies_version
from colcon_core.verb import VerbExtensionPoint
from git import Repo, InvalidGitRepositoryError
from networkx import generate_gexf, write_gml
from networkx.drawing.nx_pydot import write_dot

CLOC_FOUND = shutil.which("cloc") is not None


class SupportedFileFormats(Enum):
    """
    See the list of supported graph formats from Gephi for an understanding of why we may want a different format.
    https://gephi.org/users/supported-graph-formats/
    """
    DOT = "dot"
    GEXF = "gexf"
    GML = "gml"


def is_iterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False


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
    except Exception:
        # Probably a weird setup, like not having an "origin" remote
        # or maybe symlinks? Either way, we give up.
        return None


def build_cloc_attributes(paths):
    """
    Return a dictionary with keys for the given directory paths, and values containing a list of per-file cloc stats.
    """

    result = subprocess.run(
        ["cloc", "--json", "--by-file"] + paths,
        text=True,
        capture_output=True,
        check=True
    )

    # Now, we need to create a dictionary with the sum of all useful `cloc` stats with a key for each given path
    data = json.loads(result.stdout)

    cloc_attributes = defaultdict(list)

    for package in paths:
        for key, value in data.items():
            if key.startswith(package):
                value["file"] = key
                cloc_attributes[package].append(value)

    return cloc_attributes


def build_attributes(descriptor: PackageDescriptor) -> Dict[str, any]:
    """
    Construct a dictionary of string attributes for a package node in the dependency graph.

    The returned attributes are based on the package's metadata and additional
    information inferred from its location and repository state. They are
    intended for direct use as node attributes in a NetworkX graph.
    """

    attributes = descriptor.metadata
    attributes['path'] = str(descriptor.path)
    attributes['build_type'] = descriptor.type

    # This is useless for us, but can come from the descriptors original metadata
    attributes.pop('get_python_setup_options', None)

    if repo := find_repo(descriptor.path):
        if repo.remotes:
            # noinspection PyUnresolvedReferences
            attributes['repo'] = Path(str(repo.remotes.origin.url)).stem
            # noinspection PyUnresolvedReferences
            attributes['remote'] = repo.remotes.origin.url
        else:
            attributes['repo'] = Path(repo.working_tree_dir).name

    # So far, all supported file types don't like having raw lists as node attributes :/
    for k, v in attributes.items():
        if is_iterable(v) and not isinstance(v, (str, bytes)):
            attributes[k] = ",".join(attributes[k])

    return attributes


class GephiGraphVerb(VerbExtensionPoint):
    """
    Generate a gexf (or gml) file that can be inspected in Gephi.
    """

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(VerbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        # I really don't understand why this specific arg is needed,
        # but without it `get_package_descriptors` returns an empty set.
        parser.add_argument(
            '--build-base',
            default='build',
            help='The base path for all build directories (default: build)')

        parser.add_argument(
            '--format',
            default=SupportedFileFormats.DOT.value,
            choices=[f.value for f in SupportedFileFormats],
            help='The graph file format to be generated (default: dot)')

        add_arguments(parser)

    def main(self, *, context):  # noqa: D102
        args = context.args
        descriptors = get_package_descriptors(args)
        packages_in_ws = set([d.name for d in descriptors])

        cloc_attributes = {}
        if CLOC_FOUND:
            print('cloc found, running...')
            cloc_attributes = build_cloc_attributes([str(d.path) for d in descriptors])
        else:
            print('No cloc executable found, skipping associated node attributes')

        graph = nx.DiGraph()

        for descriptor in descriptors:
            attributes = build_attributes(descriptor)

            if CLOC_FOUND:
                comment_count = 0
                code_count = 0
                for f in cloc_attributes[str(descriptor.path)]:
                    for k, v in f.items():
                        if k == 'comment':
                            comment_count += v
                        elif k == 'code':
                            code_count += v

                attributes['lines_of_comments'] = comment_count
                attributes['lines_of_code'] = code_count
                attributes['number_of_files'] = len(cloc_attributes[str(descriptor.path)])

            graph.add_node(descriptor.name, **attributes)

            # Only find edges for this node that exist within this workspace
            for dep_type in ['build', 'run', 'test']:
                for dependency in descriptor.dependencies[dep_type]:
                    if dependency in packages_in_ws:
                        graph.add_edge(descriptor.name, dependency, dep_type=dep_type)

        # For now, default to where this command was run
        name = os.path.basename(os.getcwd())

        if args.format == SupportedFileFormats.GEXF.value:
            # Networkx doesn't seem to support things like gephi's ListString (which I think is part of the gexf standard?)
            # Fall back to some good'ol xml parsing/editing.
            raw_xml = "".join([line for line in generate_gexf(graph)])
            root = ET.fromstring(raw_xml)

            for maintainer in root.findall(".//{*}attribute[@title='maintainers']"):
                if maintainer.get("type") == "string":
                    maintainer.set("type", "liststring")

            tree = ET.ElementTree(root)

            tree.write(f"{name}.gexf", encoding="utf-8")
            print(f'Wrote gexf file to {name}.gexf')

        elif args.format == SupportedFileFormats.GML.value:
            write_gml(graph, f'{name}.gml')
            print(f'Wrote gml file to {name}.gml')

        elif args.format == SupportedFileFormats.DOT.value:
            write_dot(graph, f'{name}.dot')
            print(f'Wrote dot file to {name}.dot')
