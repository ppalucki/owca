from typing import Dict, Set, List

from wca.scheduler.cluster_simulator import Node, Resources
from wca.scheduler.types import ResourceType as rt


def prepare_nodes(
        node_specs: Dict[str, Dict],  # node_type to resource dict,
        type_counts: Dict[str, int],  # node_type to number of nodes,
        dimensions: Set[rt]
        ) -> List[Node]:
    """Create cluster with node_specs with number of each kind (node_spec are sorted by name).
    A: {ram: 1}, B: {ram: 10}
    {A: 2, B: 3} result in
    A1, A2, B1, B2, B3 machines
    """
    for name in node_specs:
        assert '_' not in name, '_ used as separator for class later in reporting'

    # Filter only dimensions required.
    node_specs = {node_type: {dim: val for dim, val in node_spec.items() if dim in dimensions}
                  for node_type, node_spec in node_specs.items()}

    nodes = []
    for node_type in sorted(node_specs.keys()):
        for node_id in range(type_counts[node_type]):
            node_name = node_type+'_'+str(node_id)
            node = Node(node_name, available_resources=Resources(node_specs[node_type]))
            nodes.append(node)
    return nodes
