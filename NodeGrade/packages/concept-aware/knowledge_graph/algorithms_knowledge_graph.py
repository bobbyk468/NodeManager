"""
Expert-Curated Algorithms Domain Knowledge Graph.

This is the reference knowledge graph for Computer Science Algorithms,
built from standard curriculum (Cormen et al. CLRS, Kleinberg & Tardos).
Covers sorting, searching, graph algorithms, dynamic programming,
divide & conquer, greedy algorithms, and complexity analysis.
"""

from .ontology import Concept, Relationship, ConceptType as CT, RelationshipType as RT
from .domain_graph import DomainKnowledgeGraph


def build_algorithms_graph() -> DomainKnowledgeGraph:
    """
    Build the expert-validated Algorithms knowledge graph.

    Covers: Sorting Algorithms, Searching Algorithms, Graph Algorithms,
    Dynamic Programming, Divide & Conquer, Greedy Algorithms,
    Backtracking, Complexity Analysis, and Algorithmic Foundations.
    """
    graph = DomainKnowledgeGraph(domain="algorithms", version="1.0-expert")

    # ========================================================
    # ABSTRACT / FOUNDATIONAL CONCEPTS
    # ========================================================
    concepts = [
        # Top-level abstractions
        Concept("algorithm", "Algorithm", CT.ABSTRACT_CONCEPT,
                "A finite sequence of well-defined instructions to solve a computational problem",
                ["algo", "procedure"], 1),
        Concept("correctness", "Correctness", CT.PROPERTY,
                "The property that an algorithm produces the right output for every valid input",
                ["algorithm correctness", "loop invariant"], 2),
        Concept("efficiency", "Efficiency", CT.PROPERTY,
                "How well an algorithm uses computational resources such as time and space",
                ["performance"], 2),
        Concept("recursion", "Recursion", CT.ABSTRACT_CONCEPT,
                "A method where the solution depends on solutions to smaller instances of the same problem",
                ["recursive", "base case", "recursive case"], 2),
        Concept("iteration", "Iteration", CT.ABSTRACT_CONCEPT,
                "Repeated execution of a set of instructions using loops",
                ["iterative", "loop"], 1),
        Concept("recurrence_relation", "Recurrence Relation", CT.ABSTRACT_CONCEPT,
                "An equation that defines a sequence where each term is a function of preceding terms; "
                "used to express the time complexity of recursive algorithms (e.g. T(n) = 2T(n/2) + O(n))",
                ["recurrence", "T(n)"], 3),
        Concept("master_theorem", "Master Theorem", CT.ABSTRACT_CONCEPT,
                "A formula for solving divide-and-conquer recurrences of the form T(n) = aT(n/b) + f(n)",
                ["master method"], 4),
        Concept("amortized_analysis", "Amortized Analysis", CT.ABSTRACT_CONCEPT,
                "A technique for analyzing the average performance of a sequence of operations "
                "in the worst case, spreading the cost of expensive operations over many cheap ones",
                ["amortized cost"], 4),
        Concept("loop_invariant", "Loop Invariant", CT.ABSTRACT_CONCEPT,
                "A condition that is true before and after each iteration of a loop, "
                "used to prove algorithm correctness",
                ["invariant"], 3),

        # Complexity classes
        Concept("time_complexity", "Time Complexity", CT.COMPLEXITY_CLASS,
                "The amount of time an algorithm takes as a function of input size",
                ["runtime complexity", "time cost"], 2),
        Concept("space_complexity", "Space Complexity", CT.COMPLEXITY_CLASS,
                "The amount of memory an algorithm uses as a function of input size",
                ["memory complexity", "auxiliary space"], 2),
        Concept("big_o_notation", "Big-O Notation", CT.ABSTRACT_CONCEPT,
                "Asymptotic notation describing the upper bound of an algorithm's growth rate",
                ["Big O", "asymptotic notation", "order of growth"], 2),
        Concept("o_1", "O(1)", CT.COMPLEXITY_CLASS, "Constant time complexity", ["constant time"], 1),
        Concept("o_log_n", "O(log n)", CT.COMPLEXITY_CLASS, "Logarithmic time complexity",
                ["logarithmic", "log n"], 2),
        Concept("o_n", "O(n)", CT.COMPLEXITY_CLASS, "Linear time complexity", ["linear time"], 1),
        Concept("o_n_log_n", "O(n log n)", CT.COMPLEXITY_CLASS, "Linearithmic time complexity",
                ["n log n", "linearithmic"], 2),
        Concept("o_n2", "O(n²)", CT.COMPLEXITY_CLASS, "Quadratic time complexity",
                ["quadratic", "O(n^2)"], 2),
        Concept("o_v_plus_e", "O(V+E)", CT.COMPLEXITY_CLASS,
                "Linear graph complexity proportional to vertices plus edges",
                ["O(V+E)", "linear graph time"], 3),
        Concept("o_ve", "O(VE)", CT.COMPLEXITY_CLASS,
                "Graph complexity proportional to vertices times edges",
                ["O(VE)"], 3),
        Concept("o_v3", "O(V³)", CT.COMPLEXITY_CLASS,
                "Cubic graph complexity proportional to the cube of vertices",
                ["O(V^3)", "cubic"], 3),

        # ========================================================
        # ALGORITHM DESIGN PARADIGMS
        # ========================================================
        Concept("divide_and_conquer", "Divide and Conquer", CT.DESIGN_PATTERN,
                "An algorithm design paradigm that recursively splits a problem into independent "
                "subproblems, solves each, and combines the results",
                ["D&C", "divide & conquer"], 2),
        Concept("dynamic_programming", "Dynamic Programming", CT.DESIGN_PATTERN,
                "An optimization technique that solves problems by breaking them into overlapping "
                "subproblems, storing results to avoid redundant computation",
                ["DP", "dynamic prog"], 4),
        Concept("memoization", "Memoization", CT.DESIGN_PATTERN,
                "Top-down dynamic programming technique that caches the results of expensive "
                "function calls and returns the cached result when the same inputs occur again",
                ["top-down DP", "cache", "memo"], 3),
        Concept("tabulation", "Tabulation", CT.DESIGN_PATTERN,
                "Bottom-up dynamic programming technique that fills a table iteratively "
                "from base cases to the final solution",
                ["bottom-up DP", "DP table"], 3),
        Concept("greedy_algorithm", "Greedy Algorithm", CT.DESIGN_PATTERN,
                "An algorithm paradigm that makes locally optimal choices at each step "
                "hoping to find a global optimum; does not always yield the optimal solution",
                ["greedy", "greedy method"], 3),
        Concept("backtracking", "Backtracking", CT.DESIGN_PATTERN,
                "A systematic algorithmic technique that considers searching every possible "
                "combination and abandons a candidate as soon as it cannot lead to a valid solution",
                ["backtrack", "pruning"], 4),
        Concept("brute_force", "Brute Force", CT.DESIGN_PATTERN,
                "An exhaustive search technique that tries every possible candidate solution",
                ["exhaustive search", "try all"], 1),
        Concept("randomized_algorithm", "Randomized Algorithm", CT.DESIGN_PATTERN,
                "An algorithm that uses random numbers to influence its behavior or choices",
                ["randomized", "randomization"], 4),

        # Algorithmic properties / sub-concepts
        Concept("optimal_substructure", "Optimal Substructure", CT.PROPERTY,
                "A problem has optimal substructure if an optimal solution can be constructed "
                "efficiently from optimal solutions of its subproblems",
                ["optimal subproblem"], 4),
        Concept("overlapping_subproblems", "Overlapping Subproblems", CT.PROPERTY,
                "A property where the same subproblems are solved multiple times during recursion; "
                "a prerequisite for dynamic programming to be beneficial",
                ["repeated subproblems"], 4),

        # ========================================================
        # SORTING ALGORITHMS
        # ========================================================
        Concept("sorting", "Sorting", CT.ABSTRACT_CONCEPT,
                "The process of arranging elements in a specified order (ascending or descending)",
                ["sort", "ordering"], 1),
        Concept("sorted_sequence", "Sorted Sequence", CT.ABSTRACT_CONCEPT,
                "An ordered sequence where each element is no greater than the next",
                ["sorted output", "ordered list"], 1),
        Concept("comparison_based_sorting", "Comparison-Based Sorting", CT.ABSTRACT_CONCEPT,
                "A class of sorting algorithms that determine order solely by comparing elements; "
                "provably requires Ω(n log n) comparisons in the worst case",
                ["comparison sort", "comparison-based"], 3),
        Concept("stable_sort", "Stable Sort", CT.PROPERTY,
                "A sorting algorithm is stable if it preserves the relative order of equal elements",
                ["stability", "stable sorting"], 3),
        Concept("in_place_sort", "In-Place Sort", CT.PROPERTY,
                "A sorting algorithm that uses only O(1) auxiliary memory beyond the input array",
                ["in-place", "in place sorting"], 3),

        Concept("bubble_sort", "Bubble Sort", CT.ALGORITHM,
                "A simple comparison-based sorting algorithm that repeatedly swaps adjacent "
                "out-of-order elements until the array is sorted; O(n²) time",
                ["bubble"], 2),
        Concept("selection_sort", "Selection Sort", CT.ALGORITHM,
                "A comparison-based sorting algorithm that repeatedly selects the minimum element "
                "from the unsorted portion and places it at the beginning; O(n²) time",
                ["selection"], 2),
        Concept("insertion_sort", "Insertion Sort", CT.ALGORITHM,
                "A comparison-based sorting algorithm that builds the sorted array one element "
                "at a time by inserting each into its correct position; O(n²) worst case, O(n) best",
                ["insertion"], 2),
        Concept("merge_sort", "Merge Sort", CT.ALGORITHM,
                "A stable, divide-and-conquer sorting algorithm that recursively splits the array "
                "in half, sorts each half, and merges them; O(n log n) time, O(n) auxiliary space",
                ["mergesort", "merge-sort"], 3),
        Concept("quick_sort", "Quick Sort", CT.ALGORITHM,
                "A divide-and-conquer in-place sorting algorithm that partitions the array around "
                "a pivot; O(n log n) average, O(n²) worst case",
                ["quicksort", "partition sort"], 3),
        Concept("heap_sort", "Heap Sort", CT.ALGORITHM,
                "An in-place, comparison-based sorting algorithm that uses a max-heap to repeatedly "
                "extract the maximum element; O(n log n) time, not stable",
                ["heapsort"], 3),
        Concept("counting_sort", "Counting Sort", CT.ALGORITHM,
                "A non-comparison integer sorting algorithm that counts element occurrences "
                "and uses prefix sums to place elements; O(n+k) time where k is the value range",
                ["counting"], 3),
        Concept("radix_sort", "Radix Sort", CT.ALGORITHM,
                "A non-comparison sorting algorithm that sorts integers digit by digit "
                "from least to most significant using a stable sort; O(d(n+k)) time",
                ["radix"], 3),
        Concept("bucket_sort", "Bucket Sort", CT.ALGORITHM,
                "A distribution sorting algorithm that partitions elements into buckets, "
                "sorts each bucket, and concatenates; O(n+k) average time",
                ["bucket", "bin sort"], 3),

        # Sorting sub-concepts
        Concept("pivot_selection", "Pivot Selection", CT.ABSTRACT_CONCEPT,
                "The strategy for choosing the pivot element in quicksort; "
                "affects worst-case performance (e.g. median-of-three, random pivot)",
                ["pivot", "pivot element", "median-of-three"], 3),
        Concept("partition_scheme", "Partition Scheme", CT.ABSTRACT_CONCEPT,
                "The procedure in quicksort that rearranges elements around the pivot "
                "(e.g. Lomuto or Hoare partition scheme)",
                ["partitioning", "Lomuto", "Hoare"], 3),
        Concept("merge_procedure", "Merge Procedure", CT.OPERATION,
                "The subroutine in merge sort that combines two sorted subarrays into one sorted array",
                ["merge step", "merge"], 3),

        # ========================================================
        # SEARCHING ALGORITHMS
        # ========================================================
        Concept("searching", "Searching", CT.ABSTRACT_CONCEPT,
                "The process of finding a target element within a data collection",
                ["search"], 1),
        Concept("linear_search", "Linear Search", CT.ALGORITHM,
                "A sequential search algorithm that checks each element one by one; "
                "O(n) time, works on unsorted data",
                ["sequential search"], 1),
        Concept("binary_search", "Binary Search", CT.ALGORITHM,
                "A divide-and-conquer search algorithm on a sorted array that repeatedly "
                "halves the search interval; O(log n) time",
                ["binary search algorithm", "half-interval search"], 2),

        # ========================================================
        # GRAPH ALGORITHM FOUNDATIONS
        # ========================================================
        Concept("graph_algorithm", "Graph Algorithm", CT.ABSTRACT_CONCEPT,
                "An algorithm designed to operate on graph data structures "
                "(vertices and edges)",
                ["graph algo"], 3),
        Concept("weighted_graph", "Weighted Graph", CT.ABSTRACT_CONCEPT,
                "A graph where each edge carries a numerical weight or cost",
                ["weighted network", "edge weights"], 2),
        Concept("directed_acyclic_graph", "Directed Acyclic Graph", CT.ABSTRACT_CONCEPT,
                "A directed graph with no directed cycles; used in topological sort and DP on graphs",
                ["DAG"], 3),
        Concept("negative_cycle", "Negative Cycle", CT.PROPERTY,
                "A cycle in a weighted graph whose total edge weight is negative; "
                "makes shortest-path undefined for some pairs",
                ["negative weight cycle"], 4),
        Concept("relaxation", "Relaxation", CT.OPERATION,
                "The edge-relaxation step in shortest-path algorithms: update the estimated "
                "distance to a vertex if a shorter path is found through a neighbor",
                ["edge relaxation", "relax"], 3),
        Concept("priority_queue_heap", "Priority Queue (Heap)", CT.ABSTRACT_CONCEPT,
                "A min-heap-backed priority queue used in Dijkstra's and Prim's algorithms "
                "to efficiently extract the vertex with the smallest tentative distance/key",
                ["min-heap priority queue", "heap-based PQ"], 3),
        Concept("union_find", "Union-Find", CT.ABSTRACT_CONCEPT,
                "A disjoint-set data structure supporting union and find operations; "
                "used in Kruskal's algorithm to detect cycles efficiently",
                ["disjoint set union", "DSU", "disjoint set"], 4),
        Concept("minimum_spanning_tree", "Minimum Spanning Tree", CT.ABSTRACT_CONCEPT,
                "A spanning tree of a weighted undirected graph with the minimum total edge weight",
                ["MST", "minimum spanning tree"], 3),

        # ========================================================
        # GRAPH ALGORITHMS
        # ========================================================
        Concept("dijkstra", "Dijkstra's Algorithm", CT.ALGORITHM,
                "A greedy single-source shortest-path algorithm for graphs with non-negative "
                "edge weights; O((V+E) log V) with a min-heap priority queue",
                ["Dijkstra", "single source shortest path", "SSSP"], 4),
        Concept("bellman_ford", "Bellman-Ford Algorithm", CT.ALGORITHM,
                "A single-source shortest-path algorithm that handles negative edge weights "
                "and detects negative cycles; O(VE) time",
                ["Bellman Ford", "bellman-ford"], 4),
        Concept("floyd_warshall", "Floyd-Warshall Algorithm", CT.ALGORITHM,
                "An all-pairs shortest-path algorithm based on dynamic programming; "
                "O(V³) time, handles negative edges but not negative cycles",
                ["Floyd Warshall", "all-pairs shortest path", "APSP"], 4),
        Concept("prim", "Prim's Algorithm", CT.ALGORITHM,
                "A greedy algorithm for finding a minimum spanning tree by greedily adding "
                "the cheapest edge connecting the tree to a non-tree vertex; "
                "O((V+E) log V) with a min-heap",
                ["Prim", "Prim MST"], 4),
        Concept("kruskal", "Kruskal's Algorithm", CT.ALGORITHM,
                "A greedy algorithm for finding a minimum spanning tree by sorting all edges "
                "and adding them if they don't form a cycle, using union-find; O(E log E) time",
                ["Kruskal", "Kruskal MST"], 4),
        Concept("topological_sort", "Topological Sort", CT.ALGORITHM,
                "A linear ordering of vertices in a DAG such that for every directed edge u→v, "
                "u appears before v; computed via DFS or Kahn's (BFS-based) algorithm",
                ["topological ordering", "topo sort", "Kahn's algorithm"], 3),
        Concept("bfs", "Breadth-First Search", CT.ALGORITHM,
                "A graph traversal that explores all neighbors at the current depth before "
                "proceeding to the next level; O(V+E), uses a queue",
                ["BFS", "breadth first search"], 2),
        Concept("dfs", "Depth-First Search", CT.ALGORITHM,
                "A graph traversal that explores as far as possible along each branch before "
                "backtracking; O(V+E), uses a stack or recursion",
                ["DFS", "depth first search"], 2),

        # ========================================================
        # CLASSIC DP PROBLEMS (illustrative sub-concepts)
        # ========================================================
        Concept("longest_common_subsequence", "Longest Common Subsequence", CT.ALGORITHM,
                "A classic DP problem: find the longest subsequence common to two sequences; "
                "O(mn) time and space",
                ["LCS"], 4),
        Concept("knapsack_problem", "Knapsack Problem", CT.ALGORITHM,
                "A classic DP/optimization problem: select items with maximum total value "
                "subject to a weight capacity constraint; O(nW) for 0/1 knapsack",
                ["0/1 knapsack", "knapsack"], 4),
        Concept("matrix_chain_multiplication", "Matrix Chain Multiplication", CT.ALGORITHM,
                "A classic DP problem that finds the optimal parenthesization of a matrix product "
                "to minimize scalar multiplications; O(n³)",
                ["matrix chain", "MCM"], 5),

        # ========================================================
        # ADVANCED / SUPPORTING CONCEPTS
        # ========================================================
        Concept("np_completeness", "NP-Completeness", CT.ABSTRACT_CONCEPT,
                "A class of decision problems for which no known polynomial-time algorithm exists; "
                "central to computational complexity theory",
                ["NP-complete", "NP hard", "computational complexity"], 5),
        Concept("reduction", "Reduction", CT.ABSTRACT_CONCEPT,
                "Transforming one problem into another to show equivalence of hardness",
                ["polynomial reduction"], 5),
        Concept("approximation_algorithm", "Approximation Algorithm", CT.ALGORITHM,
                "An algorithm that finds near-optimal solutions to NP-hard optimization problems "
                "with a guaranteed approximation ratio",
                ["approximation", "approximation ratio"], 5),
    ]

    for concept in concepts:
        graph.add_concept(concept)

    # ========================================================
    # RELATIONSHIPS
    # ========================================================
    relationships = [

        # ============================================================
        # IS_A — taxonomy
        # ============================================================
        Relationship("bubble_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("selection_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("insertion_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("merge_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("quick_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("heap_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("counting_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("radix_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("bucket_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("linear_search", "algorithm", RT.IS_A, 1.0),
        Relationship("binary_search", "algorithm", RT.IS_A, 1.0),
        Relationship("dijkstra", "algorithm", RT.IS_A, 1.0),
        Relationship("bellman_ford", "algorithm", RT.IS_A, 1.0),
        Relationship("floyd_warshall", "algorithm", RT.IS_A, 1.0),
        Relationship("prim", "algorithm", RT.IS_A, 1.0),
        Relationship("kruskal", "algorithm", RT.IS_A, 1.0),
        Relationship("topological_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("bfs", "algorithm", RT.IS_A, 1.0),
        Relationship("dfs", "algorithm", RT.IS_A, 1.0),
        Relationship("longest_common_subsequence", "algorithm", RT.IS_A, 1.0),
        Relationship("knapsack_problem", "algorithm", RT.IS_A, 1.0),
        Relationship("matrix_chain_multiplication", "algorithm", RT.IS_A, 1.0),
        Relationship("approximation_algorithm", "algorithm", RT.IS_A, 1.0),

        Relationship("bubble_sort", "comparison_based_sorting", RT.IS_A, 1.0),
        Relationship("selection_sort", "comparison_based_sorting", RT.IS_A, 1.0),
        Relationship("insertion_sort", "comparison_based_sorting", RT.IS_A, 1.0),
        Relationship("merge_sort", "comparison_based_sorting", RT.IS_A, 1.0),
        Relationship("quick_sort", "comparison_based_sorting", RT.IS_A, 1.0),
        Relationship("heap_sort", "comparison_based_sorting", RT.IS_A, 1.0),

        Relationship("dijkstra", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("bellman_ford", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("floyd_warshall", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("prim", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("kruskal", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("topological_sort", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("bfs", "graph_algorithm", RT.IS_A, 1.0),
        Relationship("dfs", "graph_algorithm", RT.IS_A, 1.0),

        Relationship("memoization", "dynamic_programming", RT.IS_A, 0.9,
                     "Memoization is the top-down variant of dynamic programming"),
        Relationship("tabulation", "dynamic_programming", RT.IS_A, 0.9,
                     "Tabulation is the bottom-up variant of dynamic programming"),

        # ============================================================
        # IMPLEMENTS — paradigm realizations
        # ============================================================
        Relationship("merge_sort", "divide_and_conquer", RT.IMPLEMENTS, 1.0,
                     "Merge sort splits the array in half recursively then merges"),
        Relationship("quick_sort", "divide_and_conquer", RT.IMPLEMENTS, 1.0,
                     "Quick sort partitions the array around a pivot recursively"),
        Relationship("binary_search", "divide_and_conquer", RT.IMPLEMENTS, 1.0,
                     "Binary search halves the search space each iteration"),
        Relationship("floyd_warshall", "dynamic_programming", RT.IMPLEMENTS, 1.0,
                     "Floyd-Warshall uses a DP table dp[i][j][k] for all-pairs shortest paths"),
        Relationship("longest_common_subsequence", "dynamic_programming", RT.IMPLEMENTS, 1.0),
        Relationship("knapsack_problem", "dynamic_programming", RT.IMPLEMENTS, 1.0),
        Relationship("matrix_chain_multiplication", "dynamic_programming", RT.IMPLEMENTS, 1.0),
        Relationship("dijkstra", "greedy_algorithm", RT.IMPLEMENTS, 1.0,
                     "Dijkstra greedily picks the unvisited vertex with the smallest tentative distance"),
        Relationship("prim", "greedy_algorithm", RT.IMPLEMENTS, 1.0,
                     "Prim greedily picks the minimum-weight edge crossing the cut"),
        Relationship("kruskal", "greedy_algorithm", RT.IMPLEMENTS, 1.0,
                     "Kruskal greedily adds the cheapest edge that doesn't form a cycle"),

        # ============================================================
        # USES — data structure / subroutine dependencies
        # ============================================================
        Relationship("dijkstra", "priority_queue_heap", RT.USES, 1.0,
                     "Dijkstra uses a min-heap priority queue to extract the next closest vertex"),
        Relationship("prim", "priority_queue_heap", RT.USES, 1.0,
                     "Prim uses a min-heap to efficiently find the minimum-weight crossing edge"),
        Relationship("kruskal", "union_find", RT.USES, 1.0,
                     "Kruskal uses union-find to detect cycles when adding edges"),
        Relationship("quick_sort", "pivot_selection", RT.USES, 1.0,
                     "Quick sort selects a pivot element before partitioning"),
        Relationship("quick_sort", "partition_scheme", RT.USES, 1.0,
                     "Quick sort uses a partition scheme to rearrange elements around the pivot"),
        Relationship("merge_sort", "merge_procedure", RT.USES, 1.0,
                     "Merge sort uses the merge subroutine to combine sorted halves"),
        Relationship("heap_sort", "priority_queue_heap", RT.USES, 0.9,
                     "Heap sort builds a max-heap and repeatedly extracts the maximum"),
        Relationship("bfs", "topological_sort", RT.USES, 0.6,
                     "Kahn's topological sort is based on BFS using in-degree tracking"),
        Relationship("dfs", "topological_sort", RT.USES, 0.8,
                     "DFS-based topological sort pushes vertices to a stack on finish"),
        Relationship("dynamic_programming", "memoization", RT.USES, 0.9,
                     "Top-down DP uses memoization to cache subproblem results"),
        Relationship("dynamic_programming", "tabulation", RT.USES, 0.9,
                     "Bottom-up DP uses tabulation to fill a table from base cases"),
        Relationship("bellman_ford", "relaxation", RT.USES, 1.0,
                     "Bellman-Ford repeatedly relaxes all edges V-1 times"),
        Relationship("dijkstra", "relaxation", RT.USES, 1.0,
                     "Dijkstra relaxes edges from the currently extracted vertex"),

        # ============================================================
        # HAS_PROPERTY
        # ============================================================
        Relationship("merge_sort", "stable_sort", RT.HAS_PROPERTY, 1.0,
                     "Merge sort preserves the relative order of equal elements"),
        Relationship("bubble_sort", "stable_sort", RT.HAS_PROPERTY, 1.0,
                     "Bubble sort is stable"),
        Relationship("insertion_sort", "stable_sort", RT.HAS_PROPERTY, 1.0,
                     "Insertion sort is stable"),
        Relationship("counting_sort", "stable_sort", RT.HAS_PROPERTY, 1.0,
                     "Counting sort is stable"),
        Relationship("radix_sort", "stable_sort", RT.HAS_PROPERTY, 1.0,
                     "Radix sort requires a stable sub-sort and is itself stable"),
        Relationship("quick_sort", "in_place_sort", RT.HAS_PROPERTY, 1.0,
                     "Quick sort partitions in place using O(log n) stack space"),
        Relationship("heap_sort", "in_place_sort", RT.HAS_PROPERTY, 1.0,
                     "Heap sort sorts in place with O(1) auxiliary space"),
        Relationship("selection_sort", "in_place_sort", RT.HAS_PROPERTY, 1.0,
                     "Selection sort is in-place"),
        Relationship("insertion_sort", "in_place_sort", RT.HAS_PROPERTY, 1.0,
                     "Insertion sort is in-place"),
        Relationship("bubble_sort", "in_place_sort", RT.HAS_PROPERTY, 1.0,
                     "Bubble sort is in-place"),
        Relationship("dynamic_programming", "optimal_substructure", RT.HAS_PROPERTY, 1.0,
                     "DP requires that optimal solutions are built from optimal subproblem solutions"),
        Relationship("dynamic_programming", "overlapping_subproblems", RT.HAS_PROPERTY, 1.0,
                     "DP benefits when the same subproblems recur"),
        Relationship("greedy_algorithm", "optimal_substructure", RT.HAS_PROPERTY, 0.8,
                     "Greedy algorithms also rely on optimal substructure"),
        Relationship("bellman_ford", "negative_cycle", RT.HAS_PROPERTY, 0.9,
                     "Bellman-Ford can detect negative cycles"),
        Relationship("quick_sort", "correctness", RT.HAS_PROPERTY, 1.0),
        Relationship("merge_sort", "correctness", RT.HAS_PROPERTY, 1.0),

        # ============================================================
        # HAS_COMPLEXITY
        # ============================================================
        Relationship("bubble_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0,
                     "Bubble sort is O(n²) average and worst case"),
        Relationship("selection_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0,
                     "Selection sort is O(n²) always"),
        Relationship("insertion_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0,
                     "Insertion sort is O(n²) worst case; O(n) best case on nearly sorted data"),
        Relationship("merge_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 1.0,
                     "Merge sort is O(n log n) in all cases"),
        Relationship("quick_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 0.9,
                     "Quick sort is O(n log n) average case"),
        Relationship("quick_sort", "o_n2", RT.HAS_COMPLEXITY, 0.7,
                     "Quick sort degrades to O(n²) worst case with bad pivot choice"),
        Relationship("heap_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 1.0,
                     "Heap sort is O(n log n) guaranteed"),
        Relationship("counting_sort", "o_n", RT.HAS_COMPLEXITY, 0.9,
                     "Counting sort is O(n+k) where k is the value range"),
        Relationship("radix_sort", "o_n", RT.HAS_COMPLEXITY, 0.9,
                     "Radix sort is O(d(n+k)); linear when d and k are constants"),
        Relationship("bucket_sort", "o_n", RT.HAS_COMPLEXITY, 0.9,
                     "Bucket sort is O(n) average when input is uniformly distributed"),
        Relationship("linear_search", "o_n", RT.HAS_COMPLEXITY, 1.0,
                     "Linear search is O(n) in the worst case"),
        Relationship("binary_search", "o_log_n", RT.HAS_COMPLEXITY, 1.0,
                     "Binary search is O(log n)"),
        Relationship("bfs", "o_v_plus_e", RT.HAS_COMPLEXITY, 1.0,
                     "BFS visits every vertex and edge once: O(V+E)"),
        Relationship("dfs", "o_v_plus_e", RT.HAS_COMPLEXITY, 1.0,
                     "DFS visits every vertex and edge once: O(V+E)"),
        Relationship("topological_sort", "o_v_plus_e", RT.HAS_COMPLEXITY, 1.0,
                     "Topological sort (DFS or Kahn's) runs in O(V+E)"),
        Relationship("dijkstra", "o_v_plus_e", RT.HAS_COMPLEXITY, 0.8,
                     "Dijkstra with a Fibonacci heap is O((V+E) log V); commonly stated O(E log V)"),
        Relationship("bellman_ford", "o_ve", RT.HAS_COMPLEXITY, 1.0,
                     "Bellman-Ford is O(VE): V-1 passes over E edges"),
        Relationship("floyd_warshall", "o_v3", RT.HAS_COMPLEXITY, 1.0,
                     "Floyd-Warshall has three nested loops over V vertices"),
        Relationship("prim", "o_v_plus_e", RT.HAS_COMPLEXITY, 0.8,
                     "Prim with a min-heap is O((V+E) log V)"),
        Relationship("kruskal", "o_v_plus_e", RT.HAS_COMPLEXITY, 0.8,
                     "Kruskal is O(E log E) dominated by edge sorting"),
        Relationship("knapsack_problem", "o_n2", RT.HAS_COMPLEXITY, 0.6,
                     "0/1 Knapsack DP is O(nW); pseudo-polynomial"),
        Relationship("matrix_chain_multiplication", "o_v3", RT.HAS_COMPLEXITY, 0.5,
                     "Matrix chain DP is O(n³)"),

        # ============================================================
        # PREREQUISITE_FOR — learning dependencies
        # ============================================================
        Relationship("sorting", "binary_search", RT.PREREQUISITE_FOR, 1.0,
                     "Binary search requires sorted input"),
        Relationship("comparison_based_sorting", "merge_sort", RT.PREREQUISITE_FOR, 0.8),
        Relationship("comparison_based_sorting", "quick_sort", RT.PREREQUISITE_FOR, 0.8),
        Relationship("comparison_based_sorting", "heap_sort", RT.PREREQUISITE_FOR, 0.8),
        Relationship("divide_and_conquer", "merge_sort", RT.PREREQUISITE_FOR, 0.9),
        Relationship("divide_and_conquer", "quick_sort", RT.PREREQUISITE_FOR, 0.9),
        Relationship("divide_and_conquer", "binary_search", RT.PREREQUISITE_FOR, 0.9),
        Relationship("recursion", "merge_sort", RT.PREREQUISITE_FOR, 1.0),
        Relationship("recursion", "quick_sort", RT.PREREQUISITE_FOR, 1.0),
        Relationship("recursion", "binary_search", RT.PREREQUISITE_FOR, 0.8,
                     "Binary search can be implemented recursively"),
        Relationship("recursion", "backtracking", RT.PREREQUISITE_FOR, 1.0),
        Relationship("recursion", "dfs", RT.PREREQUISITE_FOR, 0.9),
        Relationship("recurrence_relation", "master_theorem", RT.PREREQUISITE_FOR, 1.0),
        Relationship("recurrence_relation", "divide_and_conquer", RT.PREREQUISITE_FOR, 0.9),
        Relationship("divide_and_conquer", "dynamic_programming", RT.PREREQUISITE_FOR, 0.7,
                     "DP solves overlapping subproblems that D&C would redundantly recompute"),
        Relationship("optimal_substructure", "dynamic_programming", RT.PREREQUISITE_FOR, 1.0),
        Relationship("overlapping_subproblems", "dynamic_programming", RT.PREREQUISITE_FOR, 1.0),
        Relationship("optimal_substructure", "greedy_algorithm", RT.PREREQUISITE_FOR, 0.8),
        Relationship("greedy_algorithm", "dijkstra", RT.PREREQUISITE_FOR, 0.9),
        Relationship("greedy_algorithm", "prim", RT.PREREQUISITE_FOR, 0.9),
        Relationship("greedy_algorithm", "kruskal", RT.PREREQUISITE_FOR, 0.9),
        Relationship("dynamic_programming", "floyd_warshall", RT.PREREQUISITE_FOR, 0.9),
        Relationship("dynamic_programming", "longest_common_subsequence", RT.PREREQUISITE_FOR, 1.0),
        Relationship("dynamic_programming", "knapsack_problem", RT.PREREQUISITE_FOR, 1.0),
        Relationship("dynamic_programming", "matrix_chain_multiplication", RT.PREREQUISITE_FOR, 1.0),
        Relationship("bfs", "dijkstra", RT.PREREQUISITE_FOR, 0.6,
                     "Dijkstra is conceptually similar to BFS but with weighted edges"),
        Relationship("dfs", "topological_sort", RT.PREREQUISITE_FOR, 0.9),
        Relationship("union_find", "kruskal", RT.PREREQUISITE_FOR, 1.0),
        Relationship("priority_queue_heap", "dijkstra", RT.PREREQUISITE_FOR, 1.0),
        Relationship("priority_queue_heap", "prim", RT.PREREQUISITE_FOR, 1.0),
        Relationship("weighted_graph", "dijkstra", RT.PREREQUISITE_FOR, 1.0),
        Relationship("weighted_graph", "bellman_ford", RT.PREREQUISITE_FOR, 1.0),
        Relationship("weighted_graph", "floyd_warshall", RT.PREREQUISITE_FOR, 1.0),
        Relationship("weighted_graph", "prim", RT.PREREQUISITE_FOR, 1.0),
        Relationship("weighted_graph", "kruskal", RT.PREREQUISITE_FOR, 1.0),
        Relationship("directed_acyclic_graph", "topological_sort", RT.PREREQUISITE_FOR, 1.0),
        Relationship("memoization", "longest_common_subsequence", RT.PREREQUISITE_FOR, 0.7),
        Relationship("tabulation", "longest_common_subsequence", RT.PREREQUISITE_FOR, 0.7),
        Relationship("np_completeness", "approximation_algorithm", RT.PREREQUISITE_FOR, 0.9),
        Relationship("reduction", "np_completeness", RT.PREREQUISITE_FOR, 0.9),
        Relationship("amortized_analysis", "dynamic_array", RT.PREREQUISITE_FOR, 0.7,
                     "Amortized analysis explains why dynamic array append is O(1) amortized"),
        Relationship("loop_invariant", "correctness", RT.PREREQUISITE_FOR, 0.9),

        # ============================================================
        # OPERATES_ON — what each algorithm acts upon
        # ============================================================
        Relationship("bubble_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("selection_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("insertion_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("merge_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("quick_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("heap_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("counting_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("radix_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("bucket_sort", "sorting", RT.OPERATES_ON, 1.0),
        Relationship("linear_search", "searching", RT.OPERATES_ON, 1.0),
        Relationship("binary_search", "searching", RT.OPERATES_ON, 1.0),
        Relationship("binary_search", "sorting", RT.OPERATES_ON, 0.8,
                     "Binary search requires sorted input to function correctly"),
        Relationship("dijkstra", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("bellman_ford", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("floyd_warshall", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("prim", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("kruskal", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("topological_sort", "directed_acyclic_graph", RT.OPERATES_ON, 1.0),
        Relationship("bfs", "graph_algorithm", RT.OPERATES_ON, 0.8),
        Relationship("dfs", "graph_algorithm", RT.OPERATES_ON, 0.8),

        # ============================================================
        # PRODUCES — outputs
        # ============================================================
        Relationship("bubble_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("selection_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("insertion_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("merge_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("quick_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("heap_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("counting_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("radix_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("bucket_sort", "sorted_sequence", RT.PRODUCES, 1.0),
        Relationship("dijkstra", "shortest_path", RT.PRODUCES, 1.0),
        Relationship("bellman_ford", "shortest_path", RT.PRODUCES, 1.0),
        Relationship("floyd_warshall", "shortest_path", RT.PRODUCES, 1.0),
        Relationship("prim", "minimum_spanning_tree", RT.PRODUCES, 1.0),
        Relationship("kruskal", "minimum_spanning_tree", RT.PRODUCES, 1.0),

        # ============================================================
        # CONTRASTS_WITH — comparative relationships
        # ============================================================
        Relationship("merge_sort", "quick_sort", RT.CONTRASTS_WITH, 1.0,
                     "Merge sort is stable and O(n log n) worst-case but uses O(n) extra space; "
                     "quick sort is in-place but unstable and O(n²) worst case"),
        Relationship("counting_sort", "comparison_based_sorting", RT.CONTRASTS_WITH, 1.0,
                     "Counting sort is non-comparison based and achieves O(n+k), "
                     "breaking the Ω(n log n) lower bound for comparison sorts"),
        Relationship("radix_sort", "comparison_based_sorting", RT.CONTRASTS_WITH, 1.0,
                     "Radix sort is non-comparison based"),
        Relationship("bucket_sort", "comparison_based_sorting", RT.CONTRASTS_WITH, 0.9,
                     "Bucket sort uses distribution, not comparison, to achieve linear time"),
        Relationship("memoization", "tabulation", RT.CONTRASTS_WITH, 1.0,
                     "Memoization is top-down and computes only needed subproblems; "
                     "tabulation is bottom-up and computes all subproblems in a fixed order"),
        Relationship("dijkstra", "bellman_ford", RT.CONTRASTS_WITH, 1.0,
                     "Dijkstra is faster (O(E log V)) but requires non-negative weights; "
                     "Bellman-Ford handles negative weights at O(VE) cost"),
        Relationship("prim", "kruskal", RT.CONTRASTS_WITH, 0.9,
                     "Both find MST greedily; Prim grows a single tree, "
                     "Kruskal adds edges globally sorted by weight"),
        Relationship("bfs", "dfs", RT.CONTRASTS_WITH, 1.0,
                     "BFS explores level by level (uses queue); DFS explores depth-first (uses stack)"),
        Relationship("dijkstra", "floyd_warshall", RT.CONTRASTS_WITH, 0.9,
                     "Dijkstra gives single-source shortest paths; "
                     "Floyd-Warshall gives all-pairs in O(V³)"),
        Relationship("greedy_algorithm", "dynamic_programming", RT.CONTRASTS_WITH, 0.9,
                     "Greedy makes one locally optimal choice per step and cannot revise it; "
                     "DP considers all possibilities through stored subproblem solutions"),
        Relationship("divide_and_conquer", "dynamic_programming", RT.CONTRASTS_WITH, 0.8,
                     "D&C solves independent subproblems; DP solves overlapping subproblems "
                     "and caches results to avoid redundant computation"),
        Relationship("recursion", "iteration", RT.CONTRASTS_WITH, 0.9,
                     "Recursive solutions use the call stack; iterative solutions use explicit loops"),
        Relationship("brute_force", "greedy_algorithm", RT.CONTRASTS_WITH, 0.8,
                     "Brute force exhaustively tries all possibilities; greedy picks the best local choice"),
        Relationship("brute_force", "dynamic_programming", RT.CONTRASTS_WITH, 0.8,
                     "Brute force recomputes everything; DP stores and reuses subproblem results"),
        Relationship("linear_search", "binary_search", RT.CONTRASTS_WITH, 0.9,
                     "Linear search is O(n) and works on unsorted data; "
                     "binary search is O(log n) but requires sorted data"),
        Relationship("heap_sort", "merge_sort", RT.CONTRASTS_WITH, 0.8,
                     "Both are O(n log n); heap sort is in-place but not stable, "
                     "merge sort is stable but uses O(n) extra space"),

        # ============================================================
        # VARIANT_OF — algorithmic variations
        # ============================================================
        Relationship("counting_sort", "radix_sort", RT.VARIANT_OF, 0.6,
                     "Radix sort uses counting sort as its stable sub-routine"),
        Relationship("memoization", "tabulation", RT.VARIANT_OF, 0.7,
                     "Both are DP variants; memoization is top-down, tabulation is bottom-up"),
        Relationship("bellman_ford", "dijkstra", RT.VARIANT_OF, 0.5,
                     "Both solve SSSP; Bellman-Ford is a more general variant"),

        # ============================================================
        # HAS_PART — compositional
        # ============================================================
        Relationship("merge_sort", "recurrence_relation", RT.HAS_PART, 0.9,
                     "Merge sort's complexity is described by T(n) = 2T(n/2) + O(n)"),
        Relationship("quick_sort", "recurrence_relation", RT.HAS_PART, 0.9,
                     "Quick sort's average complexity is T(n) = 2T(n/2) + O(n)"),
        Relationship("binary_search", "recurrence_relation", RT.HAS_PART, 0.9,
                     "Binary search's complexity is T(n) = T(n/2) + O(1)"),
        Relationship("divide_and_conquer", "recurrence_relation", RT.HAS_PART, 1.0,
                     "Every D&C algorithm has a recurrence describing its complexity"),
        Relationship("recurrence_relation", "master_theorem", RT.HAS_PART, 0.8,
                     "The master theorem provides closed-form solutions for standard recurrences"),
        Relationship("dijkstra", "relaxation", RT.HAS_PART, 1.0),
        Relationship("bellman_ford", "relaxation", RT.HAS_PART, 1.0),
        Relationship("floyd_warshall", "relaxation", RT.HAS_PART, 0.9),
    ]

    # extra convenience alias concepts that help round out the graph
    extra_concepts = [
        Concept("dynamic_array", "Dynamic Array", CT.ABSTRACT_CONCEPT,
                "An array that resizes automatically; used to understand amortized O(1) append",
                ["ArrayList", "resizable array", "vector"], 2),
        Concept("shortest_path", "Shortest Path", CT.ABSTRACT_CONCEPT,
                "The path between two vertices in a graph with minimum total edge weight",
                ["optimal path", "shortest route"], 3),
    ]
    for c in extra_concepts:
        graph.add_concept(c)

    for rel in relationships:
        graph.add_relationship(rel)

    return graph


def get_topic_questions() -> dict[str, list[str]]:
    """
    Return sample questions mapped to their expected concept subsets.
    Used for testing concept extraction against the knowledge graph.
    """
    return {
        "Explain how merge sort works": [
            "merge_sort", "divide_and_conquer", "recursion", "merge_procedure",
            "o_n_log_n", "stable_sort"
        ],
        "What is the difference between merge sort and quick sort?": [
            "merge_sort", "quick_sort", "divide_and_conquer", "stable_sort",
            "in_place_sort", "o_n_log_n", "pivot_selection"
        ],
        "How does Dijkstra's algorithm find the shortest path?": [
            "dijkstra", "greedy_algorithm", "shortest_path", "weighted_graph",
            "priority_queue_heap", "relaxation"
        ],
        "What is dynamic programming and how does it differ from divide and conquer?": [
            "dynamic_programming", "divide_and_conquer", "memoization", "tabulation",
            "overlapping_subproblems", "optimal_substructure"
        ],
        "Explain Bellman-Ford and when to use it over Dijkstra": [
            "bellman_ford", "dijkstra", "negative_cycle", "relaxation",
            "o_ve", "weighted_graph"
        ],
        "What is the difference between Prim's and Kruskal's algorithms?": [
            "prim", "kruskal", "minimum_spanning_tree", "greedy_algorithm",
            "union_find", "priority_queue_heap"
        ],
        "Why can't comparison-based sorting do better than O(n log n)?": [
            "comparison_based_sorting", "o_n_log_n", "counting_sort",
            "radix_sort", "sorting"
        ],
        "What is memoization and how does it relate to dynamic programming?": [
            "memoization", "dynamic_programming", "tabulation", "overlapping_subproblems",
            "recursion"
        ],
        "How does binary search achieve O(log n) time?": [
            "binary_search", "divide_and_conquer", "o_log_n", "sorting",
            "recurrence_relation"
        ],
        "Explain topological sort and when it applies": [
            "topological_sort", "directed_acyclic_graph", "dfs", "bfs",
            "o_v_plus_e"
        ],
    }
