from graph_logic import build_news_graph
from graphviz import Source
import os

def stategraph_to_dot(graph):
    dot = ["digraph G {"]
    # Add nodes
    for node in graph.nodes:
        dot.append(f'    "{node}" [label="{node}"];')
    # Add edges
    for edge in graph.edges:
        src, tgt = edge
        dot.append(f'    "{src}" -> "{tgt}";')
    dot.append("}")
    return "\n".join(dot)

# Build the raw StateGraph
app = build_news_graph()

# Output folder
os.makedirs("graph_output", exist_ok=True)
dot_path = "graph_output/news_workflow.dot"
png_path = "graph_output/news_workflow.png"

# Export graph to DOT format file manually
dot_str = stategraph_to_dot(app)

with open(dot_path, "w") as f:
    f.write(dot_str)

# Render PNG from DOT string
graph = Source(dot_str)
graph.render(filename=png_path.replace(".png", ""), format="png", cleanup=True)

print(f"Graph saved to {png_path}")