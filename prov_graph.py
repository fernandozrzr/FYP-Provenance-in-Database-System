import csv
from graphviz import Digraph

# Read ProvSQL CSV and build provenance structure
provenance = {}

with open("./static/prov_output.csv", newline="", encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        pos = row["position"]
        formula = row["sr_formula"]

        # Fix corrupted Γèò symbols (Excel sometimes breaks UTF-8 into "├ó┼áΓÇó")
        formula = formula.replace("├ó┼áΓÇó", "Γèò")

        # Parse contributors ΓÇö remove parentheses and split by Γèò
        inputs = [
            f.strip()
            for f in formula.replace("(", "").replace(")", "").split("Γèò")
            if f.strip()
        ]
        provenance[pos] = inputs

# Initialize Graphviz graph
dot = Digraph(comment="Provenance Graph")
dot.attr(rankdir="TB", splines="spline", nodesep="0.6", ranksep="0.8")

# Add input nodes (source tuples)
all_inputs = set(inp for inputs in provenance.values() for inp in inputs)
for inp in all_inputs:
    dot.node(inp, inp, shape="box", style="filled", fillcolor="lightgray")

# Add output nodes (derived tuples)
for out in provenance:
    dot.node(out, out, shape="ellipse", style="filled", fillcolor="lightblue")

# Add Γèò operation nodes and edges
for out, inputs in provenance.items():
    if len(inputs) == 1:
        # Single contributor ΓåÆ direct edge
        dot.edge(inputs[0], out)
    elif len(inputs) > 1:
        plus_node = f"plus_{out}"
        dot.node(
            plus_node,
            label="Γèò",
            shape="circle",
            style="filled",
            fillcolor="white",
            fontsize="18",
            fontname="Segoe UI Symbol",
            fixedsize="false",  # auto-size
        )

        # Connect inputs to Γèò node, then to output
        for inp in inputs:
            dot.edge(inp, plus_node)
        dot.edge(plus_node, out)

# Render and view the graph
dot.render("./static/prov_graph_plus", view=False, format="png", cleanup=True)
print("Γ£à Provenance entries loaded:", len(provenance))
print("Γ£à Graph generated as prov_graph_plus.png")
