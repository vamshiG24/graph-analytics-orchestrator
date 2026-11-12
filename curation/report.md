# Tool curation report

Every implementation was run on test cases from the provided datasets and compared with NetworkX.
Score = mean over test cases (1 = matches the reference). Ties broken by determinism, speed, options, description.

| Tool | Chosen | Score | Max time (s) | Runner-up scores |
| --- | --- | --- | --- | --- |
| articulation_points_bridges | 3237bc9e | 1.000 | 0.00 | f6f61ae0:1.00, 8f0a9ac4:1.00 |
| betweenness_centrality | 2f7893e5 | 1.000 | 0.03 | fcd76f91:1.00, f6f61ae0:1.00, 98eff80e:1.00, c1fb2ea9:1.00, 7b0e9b7e:1.00, f897d4c5:1.00, d69742a9:0.68 |
| bipartite_check | 6e31812a | 1.000 | 0.00 | 7780ae37:1.00, 62a230f4:1.00, 3c8c3c69:1.00 |
| bipartite_matching | 3f28ff34 | 1.000 | 0.00 | d02c8330:1.00, f9857550:1.00, c52598eb:1.00, e2346c64:1.00, 54d073a3:1.00, 8809b513:1.00, 8f0a9ac4:1.00 |
| closeness_centrality | 7065a2b5 | 1.000 | 0.02 | 7b0e9b7e:0.75, 64036f4f:0.75, 7cc0c2d7:0.50, afc500fb:0.25 |
| clustering_coefficient | da50612d | 1.000 | 0.00 | 6ae0e02c:1.00, d02c8330:1.00, 7b0e9b7e:1.00, 3ddaa37e:1.00, 7065a2b5:0.50, 219c8a12:0.50 |
| connected_components | e2346c64 | 1.000 | 0.20 | f9857550:1.00, 3237bc9e:1.00, 4ebce3f0:1.00, 1e59ba80:0.50, 991d1029:0.50, 37c243f2:0.50 |
| degree_centrality | c52598eb | 1.000 | 0.00 | 54d073a3:1.00, 62a230f4:1.00, a018559c:1.00, f897d4c5:0.67 |
| degree_distribution | c7c2ef65 | 1.000 | 0.00 | 6e31812a:1.00, f3b11984:1.00, c4576e71:1.00, 63fb3e40:1.00, c1fb2ea9:0.50, efd53284:0.00 |
| diameter_eccentricity | 991d1029 | 1.000 | 0.01 | ae9bcafc:1.00, ab9fb3a3:0.75, d69742a9:0.57 |
| ego_network | d35c782d | 1.000 | 0.02 | 51616f3b:1.00, afc500fb:1.00, b2d75536:1.00, e1e14ad1:1.00, 98eff80e:1.00 |
| girvan_newman | c7c2ef65 | 1.000 | 0.98 | d35c782d:1.00, 3237bc9e:1.00, 219c8a12:1.00, 3c8c3c69:1.00, 80ae2fd8:0.74, 64036f4f:0.74, afc500fb:0.74 |
| graph_summary | a20d8c29 | 1.000 | 0.02 | 2f7893e5:1.00, 41c8e8e2:1.00, 80ae2fd8:1.00, 64036f4f:1.00, 5c98c8eb:1.00 |
| greedy_coloring | 4ebce3f0 | 1.000 | 0.01 | 54d073a3:1.00, 8809b513:1.00, f28f69d7:1.00 |
| hits | 219c8a12 | 1.000 | 0.04 | a20d8c29:1.00, f9857550:1.00, 98eff80e:0.50 |
| k_core | d02c8330 | 1.000 | 0.00 | 51616f3b:1.00, 3f28ff34:1.00, b2d75536:1.00 |
| k_hop_neighborhood | b2eb4e3d | 1.000 | 0.02 | f1f54c61:1.00, 3f28ff34:1.00, 3c8c3c69:1.00, 32016695:1.00, e7c02e9e:1.00 |
| label_propagation | 6ae0e02c | 1.000 | 0.01 | a018559c:1.00, 39bca602:0.76, f1f54c61:0.50 |
| link_prediction | d35c782d | 1.000 | 0.02 | eaf1d77a:1.00, 92711a92:1.00, 41c8e8e2:1.00, 37c243f2:1.00 |
| louvain | e7c02e9e | 1.000 | 0.03 | f3b11984:1.00, c4576e71:1.00, f28f69d7:1.00, 91f2b762:1.00, b2d75536:1.00, f1f54c61:1.00 |
| max_flow_min_cut | 991d1029 | 1.000 | 0.03 | da50612d:1.00, 32016695:1.00, 1e59ba80:1.00, edba08e8:1.00, 29a7a55d:1.00, 3ddaa37e:1.00, 5c98c8eb:0.50 |
| maximal_cliques | 6e31812a | 1.000 | 0.03 | 6ae0e02c:1.00, 62a230f4:1.00, 92711a92:0.50, a20d8c29:0.50, a018559c:0.50, 7065a2b5:0.50, ab9fb3a3:0.00 |
| minimum_spanning_tree | b2eb4e3d | 1.000 | 0.11 | 3ddaa37e:0.67, 5c98c8eb:0.67, edba08e8:0.67, 96e40bd2:0.00 |
| motif_count | 63fb3e40 | 1.000 | 0.01 | e1e14ad1:1.00, 51616f3b:1.00, ae9bcafc:1.00, 37c243f2:1.00, 7cc0c2d7:0.50, eaf1d77a:0.00, 81c01533:0.00 |
| node_embedding_similarity | b2eb4e3d | 1.000 | 0.65 | 96e40bd2:1.00, 7780ae37:1.00, 41c8e8e2:1.00, 39bca602:1.00, 4ebce3f0:1.00, efd53284:1.00 |
| node_similarity | 39bca602 | 1.000 | 0.00 | eaf1d77a:1.00, ab9fb3a3:1.00, d69742a9:1.00, 29a7a55d:1.00, 81c01533:1.00 |
| pagerank | da50612d | 1.000 | 0.03 | f3b11984:1.00, 29a7a55d:1.00 |
| personalized_pagerank | e7c02e9e | 1.000 | 0.02 | e1e14ad1:1.00, c52598eb:1.00, 81c01533:0.35 |
| reachability | fcd76f91 | 1.000 | 0.00 | 92711a92:1.00, 91f2b762:1.00, 7780ae37:1.00, f6f61ae0:1.00, 7cc0c2d7:1.00 |
| shortest_path_unweighted | 96e40bd2 | 1.000 | 0.00 | edba08e8:1.00, 8809b513:1.00, f28f69d7:1.00, ae9bcafc:1.00, 8f0a9ac4:1.00 |
| shortest_path_weighted | 32016695 | 1.000 | 0.02 | 91f2b762:1.00, c4576e71:1.00, f897d4c5:1.00 |
| strongly_connected_components | fcd76f91 | 1.000 | 0.22 | e2346c64:1.00, 80ae2fd8:1.00, 2f7893e5:1.00 |
| topological_sort | 63fb3e40 | 1.000 | 0.00 | c7c2ef65:1.00, 1e59ba80:1.00, efd53284:1.00, c1fb2ea9:1.00 |

## Details

### articulation_points_bridges
- **3237bc9e** score 1.000, max 0.00s, deterministic True, options []
- **f6f61ae0** score 1.000, max 0.00s, deterministic True, options []
- **8f0a9ac4** score 1.000, max 0.00s, deterministic True, options []

### betweenness_centrality
- **2f7893e5** score 1.000, max 0.03s, deterministic True, options ['node', 'normalized', 'weighted']
- **fcd76f91** score 1.000, max 0.02s, deterministic True, options ['node', 'normalized', 'weighted']
- **f6f61ae0** score 1.000, max 0.03s, deterministic True, options ['normalized', 'weighted']
- **98eff80e** score 1.000, max 0.04s, deterministic True, options ['normalized', 'weighted']
- **c1fb2ea9** score 1.000, max 0.04s, deterministic True, options ['normalized']
- **7b0e9b7e** score 1.000, max 0.03s, deterministic True, options []
- **f897d4c5** score 1.000, max 0.03s, deterministic True, options []
- **d69742a9** score 0.683, max 0.07s, deterministic True, options []
  - lesmis {'graph_id': 'lesmis'}: 0.05 (1/10 scores match, order WRONG)

### bipartite_check
- **6e31812a** score 1.000, max 0.00s, deterministic True, options []
- **7780ae37** score 1.000, max 0.00s, deterministic True, options []
- **62a230f4** score 1.000, max 0.00s, deterministic True, options []
- **3c8c3c69** score 1.000, max 0.00s, deterministic False, options []

### bipartite_matching
- **3f28ff34** score 1.000, max 0.00s, deterministic True, options []
- **d02c8330** score 1.000, max 0.00s, deterministic True, options []
- **f9857550** score 1.000, max 0.00s, deterministic True, options []
- **c52598eb** score 1.000, max 0.00s, deterministic True, options []
- **e2346c64** score 1.000, max 0.00s, deterministic True, options []
- **54d073a3** score 1.000, max 0.00s, deterministic True, options []
- **8809b513** score 1.000, max 0.00s, deterministic True, options []
- **8f0a9ac4** score 1.000, max 0.00s, deterministic True, options []

### closeness_centrality
- **7065a2b5** score 1.000, max 0.02s, deterministic True, options ['direction', 'node', 'weighted']
- **7b0e9b7e** score 0.750, max 0.01s, deterministic True, options []
  - karate {'graph_id': 'karate', 'node': 'm34'}: 0.0 (unsupported arguments)
- **64036f4f** score 0.750, max 0.02s, deterministic True, options []
  - karate {'graph_id': 'karate', 'node': 'm34'}: 0.0 (unsupported arguments)
- **7cc0c2d7** score 0.500, max 0.01s, deterministic True, options []
  - courses {'graph_id': 'courses'}: 0.0 (0/10 scores match, order WRONG)
  - karate {'graph_id': 'karate', 'node': 'm34'}: 0.0 (unsupported arguments)
- **afc500fb** score 0.250, max 0.00s, deterministic True, options ['node']
  - karate {'graph_id': 'karate'}: 0.0 (tool error: Node 'None' (parameter 'node') is not in graph 'karate'. Use lookup_node to find node ids.)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (tool error: Node 'None' (parameter 'node') is not in graph 'lesmis'. Use lookup_node to find node ids.)
  - courses {'graph_id': 'courses'}: 0.0 (tool error: Node 'None' (parameter 'node') is not in graph 'courses'. Use lookup_node to find node ids.)

### clustering_coefficient
- **da50612d** score 1.000, max 0.00s, deterministic True, options ['node', 'weighted']
- **6ae0e02c** score 1.000, max 0.01s, deterministic True, options ['node']
- **d02c8330** score 1.000, max 0.01s, deterministic True, options ['node']
- **7b0e9b7e** score 1.000, max 0.01s, deterministic True, options ['node']
- **3ddaa37e** score 1.000, max 0.00s, deterministic True, options ['node']
- **7065a2b5** score 0.500, max 0.01s, deterministic True, options ['node', 'weighted']
  - karate {'graph_id': 'karate'}: 0.0 (avg 0.570638)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (avg 0.573137)
- **219c8a12** score 0.500, max 0.00s, deterministic True, options ['node']
  - karate {'graph_id': 'karate'}: 0.0 (avg 0.570638)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (avg 0.573137)

### connected_components
- **e2346c64** score 1.000, max 0.20s, deterministic True, options ['node']
- **f9857550** score 1.000, max 0.23s, deterministic True, options []
- **3237bc9e** score 1.000, max 0.20s, deterministic True, options []
- **4ebce3f0** score 1.000, max 0.22s, deterministic False, options ['node']
- **1e59ba80** score 0.500, max 0.00s, deterministic True, options []
  - courses {'graph_id': 'courses'}: 0.0 (tool error: Graph 'courses' is directed, but connected_components works on undirected graphs only. Use strongly_connected_components for directed graphs, or list_)
  - airports {'graph_id': 'airports'}: 0.0 (tool error: Graph 'airports' is directed, but connected_components works on undirected graphs only. Use strongly_connected_components for directed graphs, or list)
- **991d1029** score 0.500, max 0.01s, deterministic True, options []
  - courses {'graph_id': 'courses'}: 0.0 (tool error: Graph 'courses' is directed; connected_components needs an undirected graph. Use strongly_connected_components for directed graphs, or pick an undirec)
  - airports {'graph_id': 'airports'}: 0.0 (tool error: Graph 'airports' is directed; connected_components needs an undirected graph. Use strongly_connected_components for directed graphs, or pick an undire)
- **37c243f2** score 0.500, max 0.00s, deterministic True, options []
  - courses {'graph_id': 'courses'}: 0.0 (tool error: connected_components requires an undirected graph.)
  - airports {'graph_id': 'airports'}: 0.0 (tool error: connected_components requires an undirected graph.)

### degree_centrality
- **c52598eb** score 1.000, max 0.00s, deterministic True, options ['direction']
- **54d073a3** score 1.000, max 0.01s, deterministic True, options ['direction']
- **62a230f4** score 1.000, max 0.02s, deterministic True, options ['mode']
- **a018559c** score 1.000, max 0.02s, deterministic True, options []
- **f897d4c5** score 0.667, max 0.02s, deterministic True, options []
  - airports {'graph_id': 'airports'}: 0.0 (0/10 scores match, order WRONG)

### degree_distribution
- **c7c2ef65** score 1.000, max 0.00s, deterministic True, options ['mode']
- **6e31812a** score 1.000, max 0.00s, deterministic True, options ['mode']
- **f3b11984** score 1.000, max 0.00s, deterministic True, options ['mode']
- **c4576e71** score 1.000, max 0.00s, deterministic True, options ['mode']
- **63fb3e40** score 1.000, max 0.00s, deterministic True, options []
- **c1fb2ea9** score 0.500, max 0.00s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.5 (mean 4.588, max 17)
  - airports {'graph_id': 'airports'}: 0.5 (mean 80.232, max 423)
- **efd53284** score 0.000, max 0.02s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (mean 4.588, max 17)
  - airports {'graph_id': 'airports'}: 0.0 (mean 80.232, max 423)

### diameter_eccentricity
- **991d1029** score 1.000, max 0.01s, deterministic True, options ['node']
- **ae9bcafc** score 1.000, max 0.02s, deterministic True, options ['node']
- **ab9fb3a3** score 0.750, max 0.01s, deterministic True, options ['use_weights']
  - karate {'graph_id': 'karate', 'node': 'm34'}: 0.0 (unsupported arguments)
- **d69742a9** score 0.575, max 0.05s, deterministic True, options []
  - lesmis {'graph_id': 'lesmis'}: 0.3 (diameter 5 radius 3)
  - karate {'graph_id': 'karate', 'node': 'm34'}: 0.0 (unsupported arguments)

### ego_network
- **d35c782d** score 1.000, max 0.02s, deterministic True, options ['direction', 'node']
- **51616f3b** score 1.000, max 0.02s, deterministic True, options ['direction', 'node']
- **afc500fb** score 1.000, max 0.01s, deterministic True, options ['node']
- **b2d75536** score 1.000, max 0.02s, deterministic False, options ['direction', 'node']
- **e1e14ad1** score 1.000, max 0.00s, deterministic False, options ['direction', 'node']
- **98eff80e** score 1.000, max 0.02s, deterministic False, options ['node']

### girvan_newman
- **c7c2ef65** score 1.000, max 0.98s, deterministic True, options ['num_communities']
- **d35c782d** score 1.000, max 1.33s, deterministic True, options ['use_weights']
- **3237bc9e** score 1.000, max 1.70s, deterministic True, options ['num_communities']
- **219c8a12** score 1.000, max 1.13s, deterministic False, options ['num_communities', 'weighted']
- **3c8c3c69** score 1.000, max 1.13s, deterministic False, options ['num_communities']
- **80ae2fd8** score 0.739, max 0.18s, deterministic True, options ['num_communities']
  - lesmis {'graph_id': 'lesmis'}: 0.217 (modularity 0.0739 (louvain best 0.5667))
- **64036f4f** score 0.739, max 0.19s, deterministic True, options ['num_communities']
  - lesmis {'graph_id': 'lesmis'}: 0.217 (modularity 0.0739 (louvain best 0.5667))
- **afc500fb** score 0.739, max 0.19s, deterministic True, options []
  - lesmis {'graph_id': 'lesmis'}: 0.217 (modularity 0.0739 (louvain best 0.5667))

### graph_summary
- **a20d8c29** score 1.000, max 0.02s, deterministic True, options []
- **2f7893e5** score 1.000, max 0.00s, deterministic True, options []
- **41c8e8e2** score 1.000, max 0.05s, deterministic True, options []
- **80ae2fd8** score 1.000, max 0.03s, deterministic True, options []
- **64036f4f** score 1.000, max 0.00s, deterministic True, options []
- **5c98c8eb** score 1.000, max 0.00s, deterministic True, options []

### greedy_coloring
- **4ebce3f0** score 1.000, max 0.01s, deterministic True, options ['node']
- **54d073a3** score 1.000, max 0.01s, deterministic True, options []
- **8809b513** score 1.000, max 0.00s, deterministic True, options []
- **f28f69d7** score 1.000, max 0.00s, deterministic True, options []

### hits
- **219c8a12** score 1.000, max 0.04s, deterministic True, options ['normalized', 'score', 'weighted']
- **a20d8c29** score 1.000, max 0.05s, deterministic True, options ['rank_by', 'use_weights']
- **f9857550** score 1.000, max 0.06s, deterministic True, options ['sort_by', 'use_weights']
- **98eff80e** score 0.500, max 0.03s, deterministic True, options ['normalized', 'score_type', 'weighted']
  - airports {'graph_id': 'airports'}: 0.0 ()

### k_core
- **d02c8330** score 1.000, max 0.00s, deterministic True, options ['k', 'node']
- **51616f3b** score 1.000, max 0.02s, deterministic True, options ['k', 'mode']
- **3f28ff34** score 1.000, max 0.01s, deterministic True, options ['k']
- **b2d75536** score 1.000, max 0.00s, deterministic False, options ['k']

### k_hop_neighborhood
- **b2eb4e3d** score 1.000, max 0.02s, deterministic True, options ['direction', 'k', 'node']
- **f1f54c61** score 1.000, max 0.02s, deterministic True, options ['k', 'node']
- **3f28ff34** score 1.000, max 0.02s, deterministic True, options ['k', 'node']
- **3c8c3c69** score 1.000, max 0.02s, deterministic False, options ['direction', 'k', 'node']
- **32016695** score 1.000, max 0.02s, deterministic False, options ['direction', 'k', 'node']
- **e7c02e9e** score 1.000, max 0.00s, deterministic False, options ['direction', 'k', 'node']

### label_propagation
- **6ae0e02c** score 1.000, max 0.01s, deterministic True, options []
- **a018559c** score 1.000, max 0.03s, deterministic True, options []
- **39bca602** score 0.764, max 0.01s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.527 (modularity 0.1328 (louvain best 0.4198))
- **f1f54c61** score 0.500, max 0.02s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (modularity 0.0000 (louvain best 0.4198))

### link_prediction
- **d35c782d** score 1.000, max 0.02s, deterministic True, options ['method', 'node']
- **eaf1d77a** score 1.000, max 0.03s, deterministic True, options ['method', 'node']
- **92711a92** score 1.000, max 0.01s, deterministic True, options ['method', 'node']
- **41c8e8e2** score 1.000, max 0.02s, deterministic True, options ['method', 'node']
- **37c243f2** score 1.000, max 0.03s, deterministic True, options ['method']

### louvain
- **e7c02e9e** score 1.000, max 0.03s, deterministic True, options ['node', 'resolution', 'use_weights']
- **f3b11984** score 1.000, max 0.01s, deterministic True, options ['node', 'resolution', 'weighted']
- **c4576e71** score 1.000, max 0.03s, deterministic True, options ['resolution']
- **f28f69d7** score 1.000, max 0.02s, deterministic True, options ['resolution']
- **91f2b762** score 1.000, max 0.01s, deterministic False, options ['node', 'resolution', 'use_weights']
- **b2d75536** score 0.999, max 0.01s, deterministic False, options ['resolution']
  - lesmis {'graph_id': 'lesmis'}: 0.998 (modularity 0.5654 (louvain best 0.5667))
- **f1f54c61** score 0.998, max 0.28s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.998 (modularity 0.4188 (louvain best 0.4198))
  - lesmis {'graph_id': 'lesmis'}: 0.998 (modularity 0.5658 (louvain best 0.5667))

### max_flow_min_cut
- **991d1029** score 1.000, max 0.03s, deterministic True, options []
- **da50612d** score 1.000, max 0.08s, deterministic True, options []
- **32016695** score 1.000, max 0.08s, deterministic True, options []
- **1e59ba80** score 1.000, max 0.07s, deterministic True, options []
- **edba08e8** score 1.000, max 0.04s, deterministic True, options []
- **29a7a55d** score 1.000, max 0.05s, deterministic True, options []
- **3ddaa37e** score 1.000, max 0.09s, deterministic True, options []
- **5c98c8eb** score 0.500, max 0.07s, deterministic True, options []
  - karate {'graph_id': 'karate', 'source': 'm1', 'target': 'm34'}: 0.0 (tool error: Maximum flow requires a directed graph.)
  - lesmis {'graph_id': 'lesmis', 'source': 'c74', 'target': 'c26'}: 0.0 (tool error: Maximum flow requires a directed graph.)

### maximal_cliques
- **6e31812a** score 1.000, max 0.03s, deterministic True, options ['node']
- **6ae0e02c** score 1.000, max 0.04s, deterministic True, options []
- **62a230f4** score 1.000, max 0.03s, deterministic True, options []
- **92711a92** score 0.500, max 0.05s, deterministic True, options ['node']
  - karate {'graph_id': 'karate'}: 0.5 (36 cliques, max 5)
  - lesmis {'graph_id': 'lesmis'}: 0.5 (59 cliques, max 10)
- **a20d8c29** score 0.500, max 0.05s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.5 (36 cliques, max 5)
  - lesmis {'graph_id': 'lesmis'}: 0.5 (59 cliques, max 10)
- **a018559c** score 0.500, max 0.03s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.5 (36 cliques, max 5)
  - lesmis {'graph_id': 'lesmis'}: 0.5 (59 cliques, max 10)
- **7065a2b5** score 0.500, max 0.06s, deterministic False, options ['node']
  - karate {'graph_id': 'karate'}: 0.5 (36 cliques, max 5)
  - lesmis {'graph_id': 'lesmis'}: 0.5 (59 cliques, max 10)
- **ab9fb3a3** score 0.000, max 0.00s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (tool error: Cliques exceed the 8 KB output limit. Reduce top_k or analyse a smaller subgraph.)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (tool error: Cliques exceed the 8 KB output limit. Reduce top_k or analyse a smaller subgraph.)

### minimum_spanning_tree
- **b2eb4e3d** score 1.000, max 0.11s, deterministic True, options []
- **3ddaa37e** score 0.667, max 0.02s, deterministic True, options []
  - airports {'graph_id': 'airports'}: 0.0 (tool error: A spanning tree requires an undirected graph. Select an undirected graph.)
- **5c98c8eb** score 0.667, max 0.00s, deterministic True, options []
  - airports {'graph_id': 'airports'}: 0.0 (tool error: Minimum spanning trees require an undirected graph. Choose an undirected graph such as 'karate' or 'lesmis'.)
- **edba08e8** score 0.667, max 0.02s, deterministic False, options []
  - airports {'graph_id': 'airports'}: 0.0 (tool error: Graph 'airports' is directed, and a minimum spanning tree is only defined for undirected graphs. Use an undirected graph such as 'lesmis' or 'karate'.)
- **96e40bd2** score 0.000, max 0.01s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (total 33.0)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (total 105.0)
  - airports {'graph_id': 'airports'}: 0.0 (tool error: Graph 'airports' is directed, but a minimum spanning tree needs an undirected graph. Use list_graphs to find an undirected graph (for example 'lesmis')

### motif_count
- **63fb3e40** score 1.000, max 0.01s, deterministic True, options ['node']
- **e1e14ad1** score 1.000, max 0.01s, deterministic True, options []
- **51616f3b** score 1.000, max 0.00s, deterministic True, options []
- **ae9bcafc** score 1.000, max 0.00s, deterministic True, options []
- **37c243f2** score 1.000, max 0.02s, deterministic True, options []
- **7cc0c2d7** score 0.500, max 0.00s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (triangles 45)
- **eaf1d77a** score 0.000, max 0.01s, deterministic True, options ['node']
  - karate {'graph_id': 'karate'}: 0.0 (triangles 45)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (triangles 467)
- **81c01533** score 0.000, max 0.01s, deterministic True, options []
  - karate {'graph_id': 'karate'}: 0.0 (triangles 45)
  - lesmis {'graph_id': 'lesmis'}: 0.0 (triangles 467)

### node_embedding_similarity
- **b2eb4e3d** score 1.000, max 0.65s, deterministic True, options ['node', 'use_weights']
- **96e40bd2** score 1.000, max 1.18s, deterministic True, options ['node']
- **7780ae37** score 1.000, max 2.60s, deterministic True, options ['node']
- **41c8e8e2** score 1.000, max 1.37s, deterministic True, options ['node']
- **39bca602** score 1.000, max 1.41s, deterministic True, options ['node']
- **4ebce3f0** score 1.000, max 16.74s, deterministic True, options ['node', 'target']
- **efd53284** score 1.000, max 7.16s, deterministic True, options ['node']

### node_similarity
- **39bca602** score 1.000, max 0.00s, deterministic True, options ['direction', 'node']
- **eaf1d77a** score 1.000, max 0.00s, deterministic True, options ['direction']
- **ab9fb3a3** score 1.000, max 0.00s, deterministic True, options ['direction']
- **d69742a9** score 1.000, max 0.00s, deterministic True, options ['node']
- **29a7a55d** score 1.000, max 0.00s, deterministic True, options []
- **81c01533** score 1.000, max 0.00s, deterministic True, options []

### pagerank
- **da50612d** score 1.000, max 0.03s, deterministic True, options ['weighted']
- **f3b11984** score 1.000, max 0.06s, deterministic True, options ['weighted']
- **29a7a55d** score 1.000, max 0.05s, deterministic True, options []

### personalized_pagerank
- **e7c02e9e** score 1.000, max 0.02s, deterministic True, options ['node', 'seeds', 'use_weights']
- **e1e14ad1** score 1.000, max 0.00s, deterministic True, options ['node', 'use_weights']
- **c52598eb** score 1.000, max 0.02s, deterministic True, options ['node']
- **81c01533** score 0.350, max 0.03s, deterministic True, options []
  - karate {'graph_id': 'karate', 'node': 'm1'}: 0.35 (7/10 scores match, order WRONG)
  - courses {'graph_id': 'courses', 'node': 'CS101'}: 0.35 (7/10 scores match, order WRONG)
  - lesmis {'graph_id': 'lesmis', 'node': 'c74'}: 0.35 (7/10 scores match, order WRONG)

### reachability
- **fcd76f91** score 1.000, max 0.00s, deterministic True, options ['target']
- **92711a92** score 1.000, max 0.00s, deterministic True, options ['target']
- **91f2b762** score 1.000, max 0.00s, deterministic True, options ['target']
- **7780ae37** score 1.000, max 0.00s, deterministic True, options ['target']
- **f6f61ae0** score 1.000, max 0.00s, deterministic True, options ['target']
- **7cc0c2d7** score 1.000, max 0.00s, deterministic True, options ['target']

### shortest_path_unweighted
- **96e40bd2** score 1.000, max 0.00s, deterministic True, options ['target']
- **edba08e8** score 1.000, max 0.00s, deterministic True, options ['target']
- **8809b513** score 1.000, max 0.00s, deterministic True, options ['target']
- **f28f69d7** score 1.000, max 0.00s, deterministic True, options ['target']
- **ae9bcafc** score 1.000, max 0.00s, deterministic True, options ['target']
- **8f0a9ac4** score 1.000, max 0.15s, deterministic True, options []

### shortest_path_weighted
- **32016695** score 1.000, max 0.02s, deterministic True, options ['target']
- **91f2b762** score 1.000, max 0.03s, deterministic True, options ['target']
- **c4576e71** score 1.000, max 0.03s, deterministic True, options ['target']
- **f897d4c5** score 1.000, max 0.06s, deterministic True, options ['target']

### strongly_connected_components
- **fcd76f91** score 1.000, max 0.22s, deterministic True, options ['node']
- **e2346c64** score 1.000, max 0.23s, deterministic True, options ['node']
- **80ae2fd8** score 1.000, max 0.01s, deterministic True, options []
- **2f7893e5** score 1.000, max 0.20s, deterministic False, options ['node']

### topological_sort
- **63fb3e40** score 1.000, max 0.00s, deterministic True, options ['node']
- **c7c2ef65** score 1.000, max 0.00s, deterministic True, options []
- **1e59ba80** score 1.000, max 0.00s, deterministic True, options []
- **efd53284** score 1.000, max 0.00s, deterministic True, options []
- **c1fb2ea9** score 1.000, max 0.00s, deterministic True, options []
