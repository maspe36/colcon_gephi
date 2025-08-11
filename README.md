# colcon_gephi

Colcon plugin to generate a rich dependency graph for ROS 2 workspaces, intended for viewing
in [Gephi](https://gephi.org/), but usable in other graph viewing tools like [GraphViz](https://graphviz.org/)
or [Graphia](https://graphia.app/).

Currently supports exporting in:
- **DOT** (default, for Graphviz and other generic graph tools)
- **GML** (human-readable text format, supported by many graph libraries)
- **GEXF** (ideal for Gephi, preserves complex attributes)

Unlike `colcon graph`, this extension preserves extra package metadata (e.g., maintainers, repository info, build type)
as node attributes. This makes it easier to analyze dependency relationships visually in Gephi.
Features

- Generates a graph file from your ROS 2 workspace using the same package descriptors as `colcon graph`.
- Automatically includes the following as node attributes:
    - Package path
    - Build type
    - Maintainers
    - Version
    - Git repository name and remote URL (if applicable)
- Includes edges for build, run, and test dependencies between packages in the workspace.
- Produces output ready to open in Gephi — no manual attribute editing required.

## Usage

```bash
cd ros2_rolling/
colcon gephi_graph
```

The generated `.dot` file will have the name of the directory the command was run in. So in this case,
it is `ros2_rolling.dot`.

To change the file format, pass the `--format` flag.
```bash
colcon gephi_graph --format gml
```
