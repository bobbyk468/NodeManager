"""
Expert-Curated Data Structures Domain Knowledge Graph.

This is the reference knowledge graph for Computer Science Data Structures,
built from standard curriculum (Cormen et al., Goodrich & Tamassia).
Covers concepts typically assessed in the Mohler dataset.
"""

from .ontology import Concept, Relationship, ConceptType as CT, RelationshipType as RT
from .domain_graph import DomainKnowledgeGraph


def build_data_structures_graph() -> DomainKnowledgeGraph:
    """
    Build the expert-validated Data Structures knowledge graph.
    
    Covers: Arrays, Linked Lists, Stacks, Queues, Trees, Graphs,
    Hash Tables, Sorting, Searching, Complexity Analysis, Recursion.
    """
    graph = DomainKnowledgeGraph(domain="data_structures", version="1.0-expert")

    # ========================================================
    # ABSTRACT / FOUNDATIONAL CONCEPTS
    # ========================================================
    concepts = [
        # Top-level abstractions
        Concept("data_structure", "Data Structure", CT.ABSTRACT_CONCEPT,
                "A way of organizing and storing data to enable efficient access and modification",
                ["DS"], 1),
        Concept("algorithm", "Algorithm", CT.ABSTRACT_CONCEPT,
                "A finite sequence of well-defined instructions to solve a problem",
                ["algo"], 1),
        Concept("abstract_data_type", "Abstract Data Type", CT.ABSTRACT_CONCEPT,
                "A mathematical model defining data and operations independent of implementation",
                ["ADT"], 2),
        Concept("recursion", "Recursion", CT.ABSTRACT_CONCEPT,
                "A method where the solution depends on solutions to smaller instances of the same problem",
                ["recursive"], 2),
        Concept("iteration", "Iteration", CT.ABSTRACT_CONCEPT,
                "Repeated execution of a set of instructions using loops",
                ["iterative", "loop"], 1),
        Concept("pointer", "Pointer", CT.PROGRAMMING_CONSTRUCT,
                "A variable that stores the memory address of another variable",
                ["reference", "memory address"], 1),
        Concept("node", "Node", CT.ABSTRACT_CONCEPT,
                "A fundamental unit of a data structure that contains data and links to other nodes",
                ["vertex", "element"], 1),
        Concept("memory_allocation", "Memory Allocation", CT.ABSTRACT_CONCEPT,
                "The process of reserving memory space for data storage",
                ["malloc", "dynamic allocation"], 2),
        Concept("dynamic_memory", "Dynamic Memory", CT.ABSTRACT_CONCEPT,
                "Memory allocated at runtime from the heap",
                ["heap memory"], 2),
        Concept("static_memory", "Static Memory", CT.ABSTRACT_CONCEPT,
                "Memory allocated at compile time with fixed size",
                ["stack memory"], 2),

        # Complexity classes
        Concept("time_complexity", "Time Complexity", CT.COMPLEXITY_CLASS,
                "The amount of time an algorithm takes as a function of input size",
                ["runtime complexity", "time cost"], 2),
        Concept("space_complexity", "Space Complexity", CT.COMPLEXITY_CLASS,
                "The amount of memory an algorithm uses as a function of input size",
                ["memory complexity"], 2),
        Concept("o_1", "O(1)", CT.COMPLEXITY_CLASS, "Constant time complexity", ["constant time"], 2),
        Concept("o_log_n", "O(log n)", CT.COMPLEXITY_CLASS, "Logarithmic time complexity", ["logarithmic"], 2),
        Concept("o_n", "O(n)", CT.COMPLEXITY_CLASS, "Linear time complexity", ["linear time"], 2),
        Concept("o_n_log_n", "O(n log n)", CT.COMPLEXITY_CLASS, "Linearithmic time complexity", ["n log n"], 3),
        Concept("o_n2", "O(n²)", CT.COMPLEXITY_CLASS, "Quadratic time complexity", ["quadratic"], 2),
        Concept("big_o_notation", "Big-O Notation", CT.ABSTRACT_CONCEPT,
                "Asymptotic notation describing the upper bound of an algorithm's growth rate",
                ["Big O", "asymptotic notation", "order of growth"], 2),

        # ========================================================
        # LINEAR DATA STRUCTURES
        # ========================================================
        # Arrays
        Concept("array", "Array", CT.DATA_STRUCTURE,
                "A contiguous block of memory storing elements of the same type, accessed by index",
                ["list", "vector"], 1),
        Concept("dynamic_array", "Dynamic Array", CT.DATA_STRUCTURE,
                "An array that automatically resizes when capacity is exceeded",
                ["ArrayList", "vector", "resizable array"], 2),
        Concept("index", "Index", CT.ABSTRACT_CONCEPT,
                "An integer position used to access elements in an array",
                ["subscript", "position"], 1),

        # Linked Lists
        Concept("linked_list", "Linked List", CT.DATA_STRUCTURE,
                "A linear data structure where elements are connected via pointers",
                ["singly linked list"], 1),
        Concept("doubly_linked_list", "Doubly Linked List", CT.DATA_STRUCTURE,
                "A linked list where each node has pointers to both next and previous nodes",
                ["DLL", "double linked list"], 2),
        Concept("circular_linked_list", "Circular Linked List", CT.DATA_STRUCTURE,
                "A linked list where the last node points back to the first node",
                ["circular list"], 2),
        Concept("head", "Head", CT.ABSTRACT_CONCEPT,
                "The first node in a linked list", ["head pointer", "front"], 1),
        Concept("tail", "Tail", CT.ABSTRACT_CONCEPT,
                "The last node in a linked list", ["tail pointer", "rear", "end"], 1),

        # Stacks
        Concept("stack", "Stack", CT.DATA_STRUCTURE,
                "A LIFO data structure where elements are added and removed from the top",
                ["LIFO"], 1),
        Concept("push", "Push", CT.OPERATION,
                "Add an element to the top of a stack", [], 1),
        Concept("pop", "Pop", CT.OPERATION,
                "Remove and return the top element of a stack", [], 1),
        Concept("peek", "Peek", CT.OPERATION,
                "View the top element without removing it",
                ["top", "peek operation"], 1),
        Concept("lifo", "LIFO", CT.PROPERTY,
                "Last In, First Out — the element added last is removed first",
                ["Last In First Out"], 1),
        Concept("stack_overflow", "Stack Overflow", CT.PROPERTY,
                "Error when pushing to a full stack", ["overflow"], 2),
        Concept("stack_underflow", "Stack Underflow", CT.PROPERTY,
                "Error when popping from an empty stack", ["underflow"], 2),

        # Queues
        Concept("queue", "Queue", CT.DATA_STRUCTURE,
                "A FIFO data structure where elements are added at rear and removed from front",
                ["FIFO queue"], 1),
        Concept("enqueue", "Enqueue", CT.OPERATION,
                "Add an element to the rear of a queue", ["add", "offer"], 1),
        Concept("dequeue", "Dequeue", CT.OPERATION,
                "Remove and return the front element of a queue", ["remove", "poll"], 1),
        Concept("fifo", "FIFO", CT.PROPERTY,
                "First In, First Out — the element added first is removed first",
                ["First In First Out"], 1),
        Concept("priority_queue", "Priority Queue", CT.DATA_STRUCTURE,
                "A queue where elements are dequeued based on priority rather than order",
                ["PQ", "heap-based queue"], 3),
        Concept("circular_queue", "Circular Queue", CT.DATA_STRUCTURE,
                "A queue implemented using a circular array to efficiently use space",
                ["ring buffer"], 2),
        Concept("deque", "Deque", CT.DATA_STRUCTURE,
                "A double-ended queue allowing insertion and deletion at both ends",
                ["double-ended queue"], 2),

        # ========================================================
        # TREES
        # ========================================================
        Concept("tree", "Tree", CT.DATA_STRUCTURE,
                "A hierarchical data structure with a root node and child nodes forming subtrees",
                ["tree structure"], 2),
        Concept("binary_tree", "Binary Tree", CT.DATA_STRUCTURE,
                "A tree where each node has at most two children (left and right)",
                ["BT"], 2),
        Concept("binary_search_tree", "Binary Search Tree", CT.DATA_STRUCTURE,
                "A binary tree where left child < parent < right child for all nodes",
                ["BST", "ordered binary tree", "sorted binary tree"], 2),
        Concept("avl_tree", "AVL Tree", CT.DATA_STRUCTURE,
                "A self-balancing BST where the height difference between subtrees is at most 1",
                ["balanced BST", "Adelson-Velsky Landis tree"], 3),
        Concept("red_black_tree", "Red-Black Tree", CT.DATA_STRUCTURE,
                "A self-balancing BST with color-coded nodes ensuring O(log n) operations",
                ["RB tree"], 4),
        Concept("heap", "Heap", CT.DATA_STRUCTURE,
                "A complete binary tree satisfying the heap property (max-heap or min-heap)",
                ["binary heap"], 2),
        Concept("max_heap", "Max Heap", CT.DATA_STRUCTURE,
                "A heap where every parent node is greater than or equal to its children", [], 2),
        Concept("min_heap", "Min Heap", CT.DATA_STRUCTURE,
                "A heap where every parent node is less than or equal to its children", [], 2),
        Concept("b_tree", "B-Tree", CT.DATA_STRUCTURE,
                "A self-balancing tree optimized for systems that read/write large blocks of data",
                ["balanced tree"], 4),
        Concept("trie", "Trie", CT.DATA_STRUCTURE,
                "A tree-like structure for storing strings where each node represents a character",
                ["prefix tree", "digital tree"], 3),

        # Tree concepts
        Concept("root", "Root", CT.ABSTRACT_CONCEPT,
                "The topmost node in a tree with no parent", ["root node"], 1),
        Concept("leaf", "Leaf", CT.ABSTRACT_CONCEPT,
                "A node with no children in a tree", ["leaf node", "terminal node"], 1),
        Concept("parent", "Parent", CT.ABSTRACT_CONCEPT,
                "A node that has one or more child nodes", ["parent node"], 1),
        Concept("child", "Child", CT.ABSTRACT_CONCEPT,
                "A node connected below its parent node", ["child node"], 1),
        Concept("subtree", "Subtree", CT.ABSTRACT_CONCEPT,
                "A tree formed by a node and all its descendants", [], 2),
        Concept("tree_height", "Tree Height", CT.PROPERTY,
                "The length of the longest path from the root to a leaf", ["height", "depth of tree"], 2),
        Concept("balanced_tree", "Balanced Tree", CT.PROPERTY,
                "A tree where the height difference between subtrees is bounded",
                ["balanced", "height-balanced"], 2),

        # Tree operations
        Concept("inorder", "Inorder Traversal", CT.ALGORITHM,
                "Tree traversal visiting left subtree, root, then right subtree",
                ["in-order", "LNR"], 2),
        Concept("preorder", "Preorder Traversal", CT.ALGORITHM,
                "Tree traversal visiting root, left subtree, then right subtree",
                ["pre-order", "NLR"], 2),
        Concept("postorder", "Postorder Traversal", CT.ALGORITHM,
                "Tree traversal visiting left subtree, right subtree, then root",
                ["post-order", "LRN"], 2),
        Concept("level_order", "Level Order Traversal", CT.ALGORITHM,
                "Tree traversal visiting nodes level by level from top to bottom",
                ["breadth-first traversal", "BFS traversal"], 2),
        Concept("tree_traversal", "Tree Traversal", CT.ALGORITHM,
                "The process of visiting all nodes in a tree in a specific order",
                ["traversal"], 2),

        # ========================================================
        # GRAPHS
        # ========================================================
        Concept("graph", "Graph", CT.DATA_STRUCTURE,
                "A collection of vertices connected by edges",
                ["network"], 2),
        Concept("directed_graph", "Directed Graph", CT.DATA_STRUCTURE,
                "A graph where edges have a direction from source to destination",
                ["digraph", "directed network"], 3),
        Concept("undirected_graph", "Undirected Graph", CT.DATA_STRUCTURE,
                "A graph where edges have no direction",
                ["undirected network"], 2),
        Concept("weighted_graph", "Weighted Graph", CT.DATA_STRUCTURE,
                "A graph where edges have associated weights or costs",
                ["weighted network"], 3),
        Concept("vertex", "Vertex", CT.ABSTRACT_CONCEPT,
                "A fundamental unit in a graph", ["node", "graph node"], 2),
        Concept("edge", "Edge", CT.ABSTRACT_CONCEPT,
                "A connection between two vertices in a graph",
                ["arc", "link"], 2),
        Concept("adjacency_list", "Adjacency List", CT.DATA_STRUCTURE,
                "Graph representation using a list of neighbors for each vertex", [], 3),
        Concept("adjacency_matrix", "Adjacency Matrix", CT.DATA_STRUCTURE,
                "Graph representation using a 2D matrix of edge weights", [], 3),

        # Graph algorithms
        Concept("bfs", "Breadth-First Search", CT.ALGORITHM,
                "Graph traversal exploring all neighbors at the current depth before going deeper",
                ["BFS", "breadth first"], 2),
        Concept("dfs", "Depth-First Search", CT.ALGORITHM,
                "Graph traversal exploring as far as possible along each branch before backtracking",
                ["DFS", "depth first"], 2),
        Concept("dijkstra", "Dijkstra's Algorithm", CT.ALGORITHM,
                "Finds the shortest path from a source to all other vertices in a weighted graph",
                ["Dijkstra", "single source shortest path"], 3),
        Concept("topological_sort", "Topological Sort", CT.ALGORITHM,
                "Linear ordering of vertices such that for every directed edge u→v, u comes before v",
                ["topological ordering", "topo sort"], 3),
        Concept("minimum_spanning_tree", "Minimum Spanning Tree", CT.ALGORITHM,
                "A spanning tree with the minimum total edge weight",
                ["MST"], 3),
        Concept("shortest_path", "Shortest Path", CT.ABSTRACT_CONCEPT,
                "The path between two vertices with the minimum total edge weight",
                ["optimal path"], 3),
        Concept("cycle", "Cycle", CT.PROPERTY,
                "A path that starts and ends at the same vertex", ["loop", "circuit"], 2),
        Concept("connected_graph", "Connected Graph", CT.PROPERTY,
                "A graph where there is a path between every pair of vertices",
                ["connected"], 2),

        # ========================================================
        # HASH TABLES
        # ========================================================
        Concept("hash_table", "Hash Table", CT.DATA_STRUCTURE,
                "A data structure that maps keys to values using a hash function",
                ["hash map", "dictionary", "associative array"], 2),
        Concept("hash_function", "Hash Function", CT.ALGORITHM,
                "A function that maps data of arbitrary size to fixed-size values",
                ["hashing", "hash"], 2),
        Concept("collision", "Collision", CT.ABSTRACT_CONCEPT,
                "When two different keys map to the same hash table index",
                ["hash collision"], 2),
        Concept("chaining", "Chaining", CT.DESIGN_PATTERN,
                "Collision resolution by storing multiple elements at the same index using a linked list",
                ["separate chaining"], 3),
        Concept("open_addressing", "Open Addressing", CT.DESIGN_PATTERN,
                "Collision resolution by probing for the next empty slot",
                ["linear probing", "probing"], 3),
        Concept("load_factor", "Load Factor", CT.PROPERTY,
                "The ratio of stored elements to the total number of slots in a hash table",
                ["fill ratio"], 3),

        # ========================================================
        # SORTING ALGORITHMS
        # ========================================================
        Concept("sorting", "Sorting", CT.ABSTRACT_CONCEPT,
                "The process of arranging elements in a specific order",
                ["sort", "ordering"], 1),
        Concept("bubble_sort", "Bubble Sort", CT.ALGORITHM,
                "A simple sorting algorithm that repeatedly swaps adjacent elements that are in the wrong order",
                ["bubble"], 1),
        Concept("selection_sort", "Selection Sort", CT.ALGORITHM,
                "Sorting by repeatedly finding the minimum element and placing it at the beginning",
                ["selection"], 1),
        Concept("insertion_sort", "Insertion Sort", CT.ALGORITHM,
                "Sorting by building a sorted portion one element at a time",
                ["insertion"], 1),
        Concept("merge_sort", "Merge Sort", CT.ALGORITHM,
                "A divide-and-conquer sorting algorithm that recursively splits and merges subarrays",
                ["mergesort"], 2),
        Concept("quick_sort", "Quick Sort", CT.ALGORITHM,
                "A divide-and-conquer sorting algorithm using a pivot element to partition the array",
                ["quicksort", "partition sort"], 2),
        Concept("heap_sort", "Heap Sort", CT.ALGORITHM,
                "Sorting by building a heap and repeatedly extracting the maximum element",
                ["heapsort"], 3),
        Concept("comparison_sort", "Comparison Sort", CT.ABSTRACT_CONCEPT,
                "A sorting algorithm that determines order by comparing elements",
                ["comparison-based sorting"], 3),
        Concept("stable_sort", "Stable Sort", CT.PROPERTY,
                "A sort that preserves the relative order of equal elements",
                ["stability"], 3),
        Concept("divide_and_conquer", "Divide and Conquer", CT.DESIGN_PATTERN,
                "A strategy that breaks a problem into smaller subproblems, solves them, and combines results",
                ["D&C"], 2),

        # ========================================================
        # SEARCHING ALGORITHMS
        # ========================================================
        Concept("searching", "Searching", CT.ABSTRACT_CONCEPT,
                "The process of finding a specific element in a data structure",
                ["search"], 1),
        Concept("linear_search", "Linear Search", CT.ALGORITHM,
                "Searching by checking each element sequentially",
                ["sequential search"], 1),
        Concept("binary_search", "Binary Search", CT.ALGORITHM,
                "Searching a sorted array by repeatedly dividing the search interval in half",
                ["binary search algorithm"], 2),

        # ========================================================
        # COMMON OPERATIONS
        # ========================================================
        Concept("insertion", "Insertion", CT.OPERATION,
                "Adding a new element to a data structure", ["insert", "add"], 1),
        Concept("deletion", "Deletion", CT.OPERATION,
                "Removing an element from a data structure", ["delete", "remove"], 1),
        Concept("traversal", "Traversal", CT.OPERATION,
                "Visiting all elements in a data structure", ["iterate", "visit"], 1),
        Concept("access", "Access", CT.OPERATION,
                "Retrieving an element from a data structure", ["get", "lookup", "read"], 1),
    ]

    for concept in concepts:
        graph.add_concept(concept)

    # ========================================================
    # RELATIONSHIPS
    # ========================================================
    relationships = [
        # === IS_A hierarchies ===
        Relationship("array", "data_structure", RT.IS_A, 1.0),
        Relationship("linked_list", "data_structure", RT.IS_A, 1.0),
        Relationship("stack", "data_structure", RT.IS_A, 1.0),
        Relationship("queue", "data_structure", RT.IS_A, 1.0),
        Relationship("tree", "data_structure", RT.IS_A, 1.0),
        Relationship("graph", "data_structure", RT.IS_A, 1.0),
        Relationship("hash_table", "data_structure", RT.IS_A, 1.0),
        Relationship("heap", "data_structure", RT.IS_A, 1.0),
        Relationship("binary_tree", "tree", RT.IS_A, 1.0),
        Relationship("binary_search_tree", "binary_tree", RT.IS_A, 1.0),
        Relationship("avl_tree", "binary_search_tree", RT.IS_A, 1.0),
        Relationship("red_black_tree", "binary_search_tree", RT.IS_A, 1.0),
        Relationship("max_heap", "heap", RT.IS_A, 1.0),
        Relationship("min_heap", "heap", RT.IS_A, 1.0),
        Relationship("directed_graph", "graph", RT.IS_A, 1.0),
        Relationship("undirected_graph", "graph", RT.IS_A, 1.0),
        Relationship("weighted_graph", "graph", RT.IS_A, 1.0),
        Relationship("priority_queue", "queue", RT.IS_A, 0.8),
        Relationship("circular_queue", "queue", RT.IS_A, 0.8),
        Relationship("deque", "queue", RT.IS_A, 0.7),
        Relationship("dynamic_array", "array", RT.IS_A, 0.9),
        Relationship("bubble_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("selection_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("insertion_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("merge_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("quick_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("heap_sort", "algorithm", RT.IS_A, 1.0),
        Relationship("linear_search", "algorithm", RT.IS_A, 1.0),
        Relationship("binary_search", "algorithm", RT.IS_A, 1.0),
        Relationship("bfs", "algorithm", RT.IS_A, 1.0),
        Relationship("dfs", "algorithm", RT.IS_A, 1.0),
        Relationship("dijkstra", "algorithm", RT.IS_A, 1.0),
        Relationship("inorder", "tree_traversal", RT.IS_A, 1.0),
        Relationship("preorder", "tree_traversal", RT.IS_A, 1.0),
        Relationship("postorder", "tree_traversal", RT.IS_A, 1.0),
        Relationship("level_order", "tree_traversal", RT.IS_A, 1.0),

        # === HAS_PART (compositional) ===
        Relationship("linked_list", "node", RT.HAS_PART, 1.0, "Each element is stored in a node"),
        Relationship("linked_list", "pointer", RT.HAS_PART, 1.0, "Nodes are connected via pointers"),
        Relationship("linked_list", "head", RT.HAS_PART, 1.0),
        Relationship("linked_list", "tail", RT.HAS_PART, 0.8),
        Relationship("doubly_linked_list", "pointer", RT.HAS_PART, 1.0, "Has both next and prev pointers"),
        Relationship("tree", "root", RT.HAS_PART, 1.0),
        Relationship("tree", "node", RT.HAS_PART, 1.0),
        Relationship("tree", "leaf", RT.HAS_PART, 1.0),
        Relationship("binary_tree", "subtree", RT.HAS_PART, 1.0),
        Relationship("graph", "vertex", RT.HAS_PART, 1.0),
        Relationship("graph", "edge", RT.HAS_PART, 1.0),
        Relationship("hash_table", "hash_function", RT.HAS_PART, 1.0),

        # === VARIANT_OF ===
        Relationship("doubly_linked_list", "linked_list", RT.VARIANT_OF, 1.0),
        Relationship("circular_linked_list", "linked_list", RT.VARIANT_OF, 1.0),
        Relationship("adjacency_list", "linked_list", RT.VARIANT_OF, 0.6, "Uses linked lists for neighbors"),
        Relationship("adjacency_matrix", "array", RT.VARIANT_OF, 0.6, "Uses 2D array for edges"),

        # === USES ===
        Relationship("bfs", "queue", RT.USES, 1.0, "BFS uses a queue for level-order exploration"),
        Relationship("dfs", "stack", RT.USES, 1.0, "DFS uses a stack (or call stack) for backtracking"),
        Relationship("dijkstra", "priority_queue", RT.USES, 1.0, "Dijkstra uses a priority queue for greedy selection"),
        Relationship("heap_sort", "heap", RT.USES, 1.0, "Heap sort builds and uses a heap"),
        Relationship("priority_queue", "heap", RT.USES, 0.9, "Priority queues are commonly implemented with heaps"),
        Relationship("hash_table", "array", RT.USES, 0.8, "Hash tables use arrays as underlying storage"),
        Relationship("hash_table", "linked_list", RT.USES, 0.7, "Chaining uses linked lists"),
        Relationship("level_order", "queue", RT.USES, 1.0, "Level-order traversal uses a queue"),
        Relationship("topological_sort", "dfs", RT.USES, 0.8),
        # NOTE: binary_search→array also appears as OPERATES_ON below.
        # NetworkX DiGraph only stores the last edge for a given (src, tgt) pair,
        # so _verify_relationship uses domain_graph.get_all_relationships() instead
        # of the graph structure to handle both relationship types correctly.
        Relationship("binary_search", "array", RT.USES, 0.9, "Binary search requires a sorted array"),

        # === IMPLEMENTS ===
        Relationship("merge_sort", "divide_and_conquer", RT.IMPLEMENTS, 1.0),
        Relationship("quick_sort", "divide_and_conquer", RT.IMPLEMENTS, 1.0),
        Relationship("binary_search", "divide_and_conquer", RT.IMPLEMENTS, 1.0),
        Relationship("chaining", "collision", RT.IMPLEMENTS, 0.8, "Chaining resolves collisions"),
        Relationship("open_addressing", "collision", RT.IMPLEMENTS, 0.8, "Open addressing resolves collisions"),

        # === PREREQUISITE_FOR ===
        Relationship("array", "hash_table", RT.PREREQUISITE_FOR, 0.9),
        Relationship("array", "dynamic_array", RT.PREREQUISITE_FOR, 0.9),
        Relationship("array", "sorting", RT.PREREQUISITE_FOR, 0.8),
        Relationship("array", "binary_search", RT.PREREQUISITE_FOR, 0.8),
        Relationship("pointer", "linked_list", RT.PREREQUISITE_FOR, 1.0),
        Relationship("node", "linked_list", RT.PREREQUISITE_FOR, 1.0),
        Relationship("linked_list", "stack", RT.PREREQUISITE_FOR, 0.7),
        Relationship("linked_list", "queue", RT.PREREQUISITE_FOR, 0.7),
        Relationship("binary_tree", "binary_search_tree", RT.PREREQUISITE_FOR, 1.0),
        Relationship("binary_search_tree", "avl_tree", RT.PREREQUISITE_FOR, 1.0),
        Relationship("binary_search_tree", "red_black_tree", RT.PREREQUISITE_FOR, 1.0),
        Relationship("tree", "binary_tree", RT.PREREQUISITE_FOR, 1.0),
        Relationship("recursion", "tree_traversal", RT.PREREQUISITE_FOR, 0.9),
        Relationship("recursion", "merge_sort", RT.PREREQUISITE_FOR, 0.9),
        Relationship("recursion", "quick_sort", RT.PREREQUISITE_FOR, 0.9),
        Relationship("recursion", "dfs", RT.PREREQUISITE_FOR, 0.8),
        Relationship("graph", "bfs", RT.PREREQUISITE_FOR, 1.0),
        Relationship("graph", "dfs", RT.PREREQUISITE_FOR, 1.0),
        Relationship("graph", "dijkstra", RT.PREREQUISITE_FOR, 1.0),
        Relationship("sorting", "binary_search", RT.PREREQUISITE_FOR, 0.8, "Binary search requires sorted data"),

        # === HAS_PROPERTY ===
        Relationship("stack", "lifo", RT.HAS_PROPERTY, 1.0, "Stack follows Last In First Out"),
        Relationship("queue", "fifo", RT.HAS_PROPERTY, 1.0, "Queue follows First In First Out"),
        Relationship("binary_search_tree", "balanced_tree", RT.HAS_PROPERTY, 0.5, "BST may or may not be balanced"),
        Relationship("avl_tree", "balanced_tree", RT.HAS_PROPERTY, 1.0, "AVL is always balanced"),
        Relationship("red_black_tree", "balanced_tree", RT.HAS_PROPERTY, 1.0),
        Relationship("heap", "balanced_tree", RT.HAS_PROPERTY, 0.9, "Heap is a complete binary tree"),
        Relationship("merge_sort", "stable_sort", RT.HAS_PROPERTY, 1.0, "Merge sort is stable"),
        Relationship("insertion_sort", "stable_sort", RT.HAS_PROPERTY, 1.0, "Insertion sort is stable"),
        Relationship("bubble_sort", "stable_sort", RT.HAS_PROPERTY, 1.0, "Bubble sort is stable"),
        Relationship("stack", "stack_overflow", RT.HAS_PROPERTY, 0.7),
        Relationship("stack", "stack_underflow", RT.HAS_PROPERTY, 0.7),

        # === HAS_COMPLEXITY ===
        Relationship("array", "o_1", RT.HAS_COMPLEXITY, 1.0, "Array access is O(1)"),
        Relationship("linked_list", "o_n", RT.HAS_COMPLEXITY, 0.8, "Linked list access is O(n)"),
        Relationship("linked_list", "o_1", RT.HAS_COMPLEXITY, 0.8, "Linked list insertion at head is O(1)"),
        Relationship("binary_search", "o_log_n", RT.HAS_COMPLEXITY, 1.0, "Binary search is O(log n)"),
        Relationship("linear_search", "o_n", RT.HAS_COMPLEXITY, 1.0, "Linear search is O(n)"),
        Relationship("bubble_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0, "Bubble sort is O(n²)"),
        Relationship("selection_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0, "Selection sort is O(n²)"),
        Relationship("insertion_sort", "o_n2", RT.HAS_COMPLEXITY, 1.0, "Insertion sort is O(n²) worst case"),
        Relationship("merge_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 1.0, "Merge sort is O(n log n)"),
        Relationship("quick_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 0.9, "Quick sort average is O(n log n)"),
        Relationship("heap_sort", "o_n_log_n", RT.HAS_COMPLEXITY, 1.0, "Heap sort is O(n log n)"),
        Relationship("hash_table", "o_1", RT.HAS_COMPLEXITY, 0.9, "Hash table operations are O(1) average"),
        Relationship("binary_search_tree", "o_log_n", RT.HAS_COMPLEXITY, 0.8, "BST operations O(log n) average"),
        Relationship("bfs", "o_n", RT.HAS_COMPLEXITY, 0.8, "BFS is O(V + E)"),
        Relationship("dfs", "o_n", RT.HAS_COMPLEXITY, 0.8, "DFS is O(V + E)"),

        # === OPERATES_ON ===
        Relationship("tree_traversal", "tree", RT.OPERATES_ON, 1.0),
        Relationship("bfs", "graph", RT.OPERATES_ON, 1.0),
        Relationship("dfs", "graph", RT.OPERATES_ON, 1.0),
        Relationship("dijkstra", "weighted_graph", RT.OPERATES_ON, 1.0),
        Relationship("topological_sort", "directed_graph", RT.OPERATES_ON, 1.0),
        Relationship("sorting", "array", RT.OPERATES_ON, 0.9),
        Relationship("binary_search", "array", RT.OPERATES_ON, 1.0),
        Relationship("linear_search", "array", RT.OPERATES_ON, 0.8),

        # === CONTRASTS_WITH ===
        Relationship("bfs", "dfs", RT.CONTRASTS_WITH, 1.0, "BFS explores breadth-first, DFS explores depth-first"),
        Relationship("array", "linked_list", RT.CONTRASTS_WITH, 0.9, "Contiguous vs. pointer-based storage"),
        Relationship("stack", "queue", RT.CONTRASTS_WITH, 0.8, "LIFO vs. FIFO access pattern"),
        Relationship("linear_search", "binary_search", RT.CONTRASTS_WITH, 0.8, "O(n) vs. O(log n)"),
        Relationship("recursion", "iteration", RT.CONTRASTS_WITH, 0.9, "Recursive vs. iterative approaches"),
        Relationship("static_memory", "dynamic_memory", RT.CONTRASTS_WITH, 0.8),
        Relationship("adjacency_list", "adjacency_matrix", RT.CONTRASTS_WITH, 0.9),
        Relationship("chaining", "open_addressing", RT.CONTRASTS_WITH, 0.8),

        # === Operations on data structures ===
        Relationship("push", "stack", RT.OPERATES_ON, 1.0),
        Relationship("pop", "stack", RT.OPERATES_ON, 1.0),
        Relationship("peek", "stack", RT.OPERATES_ON, 1.0),
        Relationship("enqueue", "queue", RT.OPERATES_ON, 1.0),
        Relationship("dequeue", "queue", RT.OPERATES_ON, 1.0),
        Relationship("insertion", "data_structure", RT.OPERATES_ON, 0.8),
        Relationship("deletion", "data_structure", RT.OPERATES_ON, 0.8),
        Relationship("traversal", "data_structure", RT.OPERATES_ON, 0.8),
        Relationship("access", "data_structure", RT.OPERATES_ON, 0.8),

        # === Big-O Notation: HAS_INSTANCE links (Q9 fix) ===
        Relationship("big_o_notation", "o_n", RT.HAS_PROPERTY, 1.0,
                     "O(n) is a Big-O complexity class"),
        Relationship("big_o_notation", "o_n_log_n", RT.HAS_PROPERTY, 1.0,
                     "O(n log n) is a Big-O complexity class"),
        Relationship("big_o_notation", "o_n2", RT.HAS_PROPERTY, 1.0,
                     "O(n\u00b2) is a Big-O complexity class"),
        Relationship("big_o_notation", "o_log_n", RT.HAS_PROPERTY, 1.0,
                     "O(log n) is a Big-O complexity class"),
        Relationship("big_o_notation", "o_1", RT.HAS_PROPERTY, 1.0,
                     "O(1) is a Big-O complexity class"),
        Relationship("o_n", "o_n_log_n", RT.CONTRASTS_WITH, 0.9,
                     "O(n) vs O(n log n) growth comparison"),
        Relationship("o_n_log_n", "o_n2", RT.CONTRASTS_WITH, 0.9,
                     "O(n log n) vs O(n\u00b2) growth comparison"),
        Relationship("o_n", "o_n2", RT.CONTRASTS_WITH, 0.9,
                     "O(n) vs O(n\u00b2) growth comparison"),
        Relationship("big_o_notation", "time_complexity", RT.HAS_PROPERTY, 1.0,
                     "Big-O notation measures time complexity"),
        Relationship("time_complexity", "algorithm", RT.HAS_PROPERTY, 1.0,
                     "Time complexity is a property of algorithms"),
        Relationship("big_o_notation", "algorithm", RT.HAS_COMPLEXITY, 0.9,
                     "Big-O notation characterizes algorithm complexity"),

        # === BST chain coverage fixes (Q3 fix) ===
        Relationship("balanced_tree", "o_log_n", RT.HAS_COMPLEXITY, 1.0,
                     "Balanced trees have O(log n) search"),
        Relationship("binary_search_tree", "subtree", RT.HAS_PART, 0.8,
                     "BST is composed of subtrees"),
        Relationship("searching", "binary_search_tree", RT.USES, 0.8,
                     "BST search uses the ordering property"),
    ]

    for rel in relationships:
        graph.add_relationship(rel)

    # Auto-tag concepts as primary / secondary based on graph topology
    graph.tag_hierarchical_concepts()

    return graph


def get_topic_questions() -> dict[str, list[str]]:
    """
    Return sample questions mapped to their expected concept subsets.
    Used for testing concept extraction against the knowledge graph.
    """
    return {
        "What is a linked list?": ["linked_list", "node", "pointer", "data_structure"],
        "Explain the difference between a stack and a queue": [
            "stack", "queue", "lifo", "fifo", "push", "pop", "enqueue", "dequeue"
        ],
        "How does binary search work?": [
            "binary_search", "array", "sorting", "divide_and_conquer", "o_log_n"
        ],
        "What is a binary search tree?": [
            "binary_search_tree", "binary_tree", "tree", "node", "root", "leaf"
        ],
        "Explain BFS and DFS": [
            "bfs", "dfs", "graph", "queue", "stack", "traversal"
        ],
        "How does a hash table handle collisions?": [
            "hash_table", "hash_function", "collision", "chaining", "open_addressing"
        ],
        "Compare merge sort and quick sort": [
            "merge_sort", "quick_sort", "divide_and_conquer", "o_n_log_n",
            "stable_sort", "recursion"
        ],
        "What is the time complexity of insertion in a linked list vs array?": [
            "linked_list", "array", "insertion", "time_complexity", "o_1", "o_n"
        ],
    }
