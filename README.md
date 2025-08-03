# colcon_gephi

Colcon plugin to output a rich .dot file that can be inspected in [Gephi](https://github.com/gephi/gephi).

The .dot file is generated for the current working directory, and uses the same package descriptors as `colcon graph` to
build the nodes and edges.

## Usage

```bash
cd ros2_rolling/
colcon gephi_graph
```

The generated `.dot` file will have the name of the directory the command was run in. So in this case,
it is `ros2_rolling.dot`