import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# Use the apartment floorplan data we have from earlier parsing.
# We'll construct a simple graph based on known doors:
# Nodes: Room_1 to Room_6, Corridor_1
# Edges from doors:
# Door_1: Room_3 - Corridor_1
# Door_2: Corridor_1 - Room_2
# Door_3: Room_1 - Corridor_1
# Door_4: Room_4 - Corridor_1
# Door_5: Corridor_1 - Room_5
# Door_6: Room_4 - Room_6

G = nx.Graph()
nodes = ["Room_1", "Room_2", "Room_3", "Room_4", "Room_5", "Room_6", "Corridor_1"]
G.add_nodes_from(nodes)

edges = [
    ("Room_3", "Corridor_1"),
    ("Corridor_1", "Room_2"),
    ("Room_1", "Corridor_1"),
    ("Room_4", "Corridor_1"),
    ("Corridor_1", "Room_5"),
    ("Room_4", "Room_6"),
]
G.add_edges_from(edges)

# Positions: simple circular layout for rooms, corridor in middle
pos = {}
# assign positions
pos["Corridor_1"] = (0, 0)
rooms = ["Room_1", "Room_2", "Room_3", "Room_4", "Room_5", "Room_6"]
angles = np.linspace(0, 2*np.pi, len(rooms)+1)[:-1]  # even spacing
for i, room in enumerate(rooms):
    r = 1.5
    pos[room] = (r * np.cos(angles[i]), r * np.sin(angles[i]))

# Define route Room_2 -> Room_3 via corridor
route = ["Room_2", "Corridor_1", "Room_3"]
route_edges = list(zip(route, route[1:]))

# Draw
fig, ax = plt.subplots(1, 1, figsize=(8, 8))
# draw all edges
nx.draw_networkx_edges(G, pos, ax=ax, edge_color='lightgray')
# draw all nodes
nx.draw_networkx_nodes(G, pos, ax=ax, node_color='white', edgecolors='black', node_size=500)
# draw node labels
nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_family='sans-serif')
# highlight route edges
route_x = []
route_y = []
for u, v in route_edges:
    route_x.append(pos[u][0])
    route_y.append(pos[u][1])
    route_x.append(pos[v][0])
    route_y.append(pos[v][1])
    # add arrow
ax.plot(route_x, route_y, 'r-', linewidth=2)
# add arrowheads
for i in range(len(route_edges)):
    u, v = route_edges[i]
    x1, y1 = pos[u]
    x2, y2 = pos[v]
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))

ax.set_title('Navigation Graph: Room_2 → Room_3')
ax.set_axis_off()
plt.tight_layout()
plt.savefig(r'C:\Users\shive\mapmind\research_deliverables\ieee_latex\figures\navigation_graph.png', dpi=300, bbox_inches='tight')
plt.close()
print('navigation_graph figure saved')