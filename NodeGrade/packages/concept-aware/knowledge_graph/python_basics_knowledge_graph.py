"""
Expert-Curated Python Fundamentals Domain Knowledge Graph.

Built for Experiment #4 (independent review round 4, decisive experiment
"controlled domain/KG matching across more than one KG"). Unlike
knowledge_graph/programming_knowledge_graph.py (OOP design theory --
inheritance, polymorphism, SOLID principles, design patterns), this graph
targets introductory Python syntax and semantics: functions, data
structures, control flow, exceptions, modules, and type conversion --
the actual topic distribution of the SPRAG public dataset (Bonthu et al.,
"SPRAG: building and benchmarking a Short Programming-Related Answer
Grading dataset", Int. J. Data Sci. Anal. 2024;
https://github.com/sridevibonthu/SPRAG), whose 68 questions (PythonQ001-068)
are almost entirely basic-syntax questions with only incidental OOP content
(one question, "Define a class"). Pairing SPRAG with the existing OOP KG
would replicate a domain-MISMATCH condition (like DigiKlausur/Kaggle ASAG
in Paper 1); this KG exists so SPRAG can instead serve as a genuine second
MATCHED domain, testing whether Mohler+DS-KG's evaluation pattern
replicates under a different but equally well-aligned domain/KG pairing.
"""

from .ontology import Concept, Relationship, ConceptType as CT, RelationshipType as RT
from .domain_graph import DomainKnowledgeGraph


def build_python_basics_graph() -> DomainKnowledgeGraph:
    """
    Build the expert-validated Python fundamentals knowledge graph.

    Covers: functions & parameters, core data structures, string/list
    operations, control flow, operators, exception handling, modules,
    type conversion, recursion, and the language-mechanics topics
    (comments, indentation, keywords, literals) that make up SPRAG's
    PythonQ001-068 question set.
    """
    graph = DomainKnowledgeGraph(domain="python_basics", version="1.0-expert")

    concepts = [
        # ========================================================
        # LANGUAGE MECHANICS
        # ========================================================
        Concept("python", "Python", CT.ABSTRACT_CONCEPT,
                "A high-level, interpreted, dynamically-typed programming language",
                ["python language"], 1),
        Concept("interpreter", "Interpreter", CT.PROGRAMMING_CONSTRUCT,
                "A program that executes source code directly, line by line, without producing a separate compiled artifact",
                ["python interpreter"], 1),
        Concept("compiler", "Compiler", CT.PROGRAMMING_CONSTRUCT,
                "A program that translates source code into a lower-level form (e.g. machine or assembly code) before execution",
                [], 1),
        Concept("indentation", "Indentation", CT.PROGRAMMING_CONSTRUCT,
                "Whitespace at the start of a line that Python uses to delimit code blocks, replacing braces",
                ["whitespace block"], 1),
        Concept("comment", "Comment", CT.PROGRAMMING_CONSTRUCT,
                "Text in source code ignored by the interpreter, used to explain code (# for single-line, triple-quotes for multi-line)",
                [], 1),
        Concept("keyword", "Keyword", CT.PROGRAMMING_CONSTRUCT,
                "A reserved word with special syntactic meaning that cannot be used as an identifier (e.g. if, def, class, import)",
                ["reserved word"], 1),
        Concept("literal", "Literal", CT.PROGRAMMING_CONSTRUCT,
                "A fixed value written directly in source code (e.g. an integer, string, or boolean literal)",
                [], 1),
        Concept("expression", "Expression", CT.PROGRAMMING_CONSTRUCT,
                "A combination of values, variables, and operators that evaluates to a single value",
                [], 1),
        Concept("module", "Module", CT.PROGRAMMING_CONSTRUCT,
                "A file containing Python code (functions, classes, variables) that can be imported and reused",
                [".py file"], 1),
        Concept("import_statement", "Import", CT.PROGRAMMING_CONSTRUCT,
                "A statement that makes the contents of a module available in the current namespace",
                ["import keyword"], 1),
        Concept("built_in_module", "Built-in Module", CT.PROGRAMMING_CONSTRUCT,
                "A module distributed with Python itself, requiring no separate installation (e.g. math, os, random)",
                ["standard library module"], 2),

        # ========================================================
        # VARIABLES & SCOPE
        # ========================================================
        Concept("variable", "Variable", CT.PROGRAMMING_CONSTRUCT,
                "A named reference to a value stored in memory",
                [], 1),
        Concept("local_variable", "Local Variable", CT.PROGRAMMING_CONSTRUCT,
                "A variable whose scope is restricted to the block (typically a function) in which it is defined",
                [], 1),
        Concept("global_variable", "Global Variable", CT.PROGRAMMING_CONSTRUCT,
                "A variable whose scope extends to the entire program/module, accessible from any function",
                [], 1),
        Concept("scope", "Scope", CT.ABSTRACT_CONCEPT,
                "The region of a program in which a variable is accessible",
                [], 1),
        Concept("lifetime", "Variable Lifetime", CT.ABSTRACT_CONCEPT,
                "The duration for which a variable exists in memory during program execution",
                [], 2),
        Concept("operator", "Operator", CT.PROGRAMMING_CONSTRUCT,
                "A symbol that performs an operation on one or more operands (arithmetic, comparison, logical)",
                [], 1),
        Concept("division_operator", "Division Operators", CT.PROGRAMMING_CONSTRUCT,
                "Python's / (true division, float result) and // (floor division, integer result) operators",
                ["true division", "floor division"], 1),
        Concept("exponent_operator", "Exponent Operator (**)", CT.PROGRAMMING_CONSTRUCT,
                "The ** operator, which raises its left operand to the power of its right operand",
                ["power operator"], 1),
        Concept("membership_operator", "Membership Operator (in)", CT.PROGRAMMING_CONSTRUCT,
                "The 'in' operator, which tests whether a value exists within a sequence or collection",
                ["in operator"], 1),
        Concept("type_conversion", "Type Conversion", CT.PROGRAMMING_CONSTRUCT,
                "Converting a value from one data type to another, either implicitly or explicitly",
                ["type casting"], 1),
        Concept("explicit_type_conversion", "Explicit Type Conversion", CT.PROGRAMMING_CONSTRUCT,
                "Deliberately converting a value's type using functions like int(), float(), str()",
                ["type casting functions"], 1),

        # ========================================================
        # CONTROL FLOW
        # ========================================================
        Concept("conditional_statement", "Conditional Statement", CT.PROGRAMMING_CONSTRUCT,
                "A statement (if / elif / else) that executes different code paths depending on a boolean condition",
                ["if statement", "if-else"], 1),
        Concept("two_way_decision", "Two-Way Decision (if-else)", CT.PROGRAMMING_CONSTRUCT,
                "A conditional structure offering exactly two branches: if and else",
                [], 1),
        Concept("if_else_ladder", "if-elif-else Ladder", CT.PROGRAMMING_CONSTRUCT,
                "A chain of if/elif/else statements used to test multiple conditions in sequence",
                ["elif chain"], 1),
        Concept("ternary_expression", "Ternary Expression", CT.PROGRAMMING_CONSTRUCT,
                "Python's conditional expression 'value_if_true if condition else value_if_false', written on one line",
                ["conditional expression"], 1),
        Concept("loop", "Loop", CT.PROGRAMMING_CONSTRUCT,
                "A control structure (for or while) that repeats a block of code",
                ["iteration"], 1),
        Concept("break_statement", "Break", CT.PROGRAMMING_CONSTRUCT,
                "A statement that immediately terminates the innermost enclosing loop",
                [], 1),
        Concept("continue_statement", "Continue", CT.PROGRAMMING_CONSTRUCT,
                "A statement that skips the rest of the current loop iteration and proceeds to the next",
                [], 1),
        Concept("pass_statement", "Pass", CT.PROGRAMMING_CONSTRUCT,
                "A null operation statement used as a placeholder where syntax requires a statement but no action is needed",
                [], 1),

        # ========================================================
        # FUNCTIONS
        # ========================================================
        Concept("function", "Function", CT.PROGRAMMING_CONSTRUCT,
                "A reusable, named block of code that performs a specific task and can be invoked by name",
                ["def"], 1),
        Concept("parameter", "Formal Parameter", CT.PROGRAMMING_CONSTRUCT,
                "A variable listed in a function's definition that receives an argument when the function is called",
                ["formal argument"], 1),
        Concept("argument", "Actual Parameter (Argument)", CT.PROGRAMMING_CONSTRUCT,
                "The concrete value passed to a function at call time, bound to a parameter",
                ["actual parameter"], 1),
        Concept("return_statement", "Return Value", CT.PROGRAMMING_CONSTRUCT,
                "The value a function sends back to its caller via the return statement; defaults to None if omitted",
                ["return keyword"], 1),
        Concept("default_argument", "Default Argument", CT.PROGRAMMING_CONSTRUCT,
                "A parameter value used automatically when the caller does not supply that argument",
                ["default parameter value"], 1),
        Concept("keyword_argument", "Keyword Argument", CT.PROGRAMMING_CONSTRUCT,
                "An argument passed by explicitly naming the parameter it binds to, rather than by position",
                ["named argument"], 1),
        Concept("positional_argument", "Positional Argument", CT.PROGRAMMING_CONSTRUCT,
                "An argument matched to a parameter by its position in the call, not by name",
                [], 1),
        Concept("variable_length_argument", "Variable-Length Arguments (*args/**kwargs)", CT.PROGRAMMING_CONSTRUCT,
                "Syntax (*args, **kwargs) that lets a function accept an arbitrary number of positional or keyword arguments",
                ["*args", "**kwargs", "varargs"], 2),
        Concept("lambda_function", "Lambda (Anonymous Function)", CT.PROGRAMMING_CONSTRUCT,
                "A small, unnamed function defined inline with the lambda keyword, limited to a single expression",
                ["anonymous function"], 1),
        Concept("recursion", "Recursion", CT.ABSTRACT_CONCEPT,
                "A technique where a function calls itself to solve smaller instances of the same problem",
                ["recursive function"], 1),

        # ========================================================
        # DATA STRUCTURES
        # ========================================================
        Concept("list", "List", CT.DATA_STRUCTURE,
                "An ordered, mutable collection of items, typically of mixed or uniform type",
                [], 1),
        Concept("tuple", "Tuple", CT.DATA_STRUCTURE,
                "An ordered, immutable collection of items",
                [], 1),
        Concept("dictionary", "Dictionary", CT.DATA_STRUCTURE,
                "A mutable collection of key-value pairs, offering fast lookup by key",
                ["dict"], 1),
        Concept("set", "Set", CT.DATA_STRUCTURE,
                "An unordered, mutable collection of unique elements",
                [], 1),
        Concept("string", "String", CT.DATA_STRUCTURE,
                "An immutable sequence of characters",
                [], 1),
        Concept("mutability", "Mutability", CT.PROPERTY,
                "Whether a data structure's contents can be changed after creation (mutable) or not (immutable)",
                ["mutable", "immutable"], 1),
        Concept("list_comprehension", "List Comprehension", CT.PROGRAMMING_CONSTRUCT,
                "A concise syntax for constructing a list by applying an expression to each item of an iterable",
                [], 2),
        Concept("numpy_array", "NumPy Array", CT.DATA_STRUCTURE,
                "A fixed-type, contiguous array structure from the NumPy library, faster and more memory-efficient than a Python list for numeric data",
                ["ndarray"], 2),

        # ========================================================
        # STRING / LIST OPERATIONS
        # ========================================================
        Concept("split_method", "split() Method", CT.PROGRAMMING_CONSTRUCT,
                "A string method that breaks a string into a list of substrings using a delimiter",
                [], 1),
        Concept("slicing", "Slicing ([start:stop:step])", CT.PROGRAMMING_CONSTRUCT,
                "Syntax for extracting a subsequence from a list, tuple, or string, including reversal via a negative step",
                ["[::-1]", "slice notation"], 1),
        Concept("append_method", "append() Method", CT.PROGRAMMING_CONSTRUCT,
                "A list method that adds a single element to the end of the list",
                [], 1),
        Concept("extend_method", "extend() Method", CT.PROGRAMMING_CONSTRUCT,
                "A list method that appends all elements of an iterable to the end of the list",
                [], 1),
        Concept("del_statement", "del Statement", CT.PROGRAMMING_CONSTRUCT,
                "A statement that removes a variable, list element, or slice by position/reference",
                [], 1),
        Concept("remove_method", "remove() Method", CT.PROGRAMMING_CONSTRUCT,
                "A list method that removes the first matching element by value",
                [], 1),
        Concept("count_method", "count() Method", CT.PROGRAMMING_CONSTRUCT,
                "A method that returns the number of occurrences of a value in a list or string",
                [], 1),
        Concept("min_max_functions", "min() / max() Functions", CT.PROGRAMMING_CONSTRUCT,
                "Built-in functions that return the smallest/largest item in an iterable",
                [], 1),

        # ========================================================
        # EXCEPTIONS & FILES
        # ========================================================
        Concept("exception", "Exception", CT.ABSTRACT_CONCEPT,
                "An event that disrupts normal program flow, raised when an error occurs during execution",
                ["error"], 1),
        Concept("exception_handling", "Exception Handling (try/except)", CT.PROGRAMMING_CONSTRUCT,
                "A mechanism (try/except/finally) for catching and responding to exceptions without crashing the program",
                ["try-except", "try-catch"], 1),
        Concept("file_read", "File read() / readlines()", CT.PROGRAMMING_CONSTRUCT,
                "File object methods: read() returns the whole file as one string, readlines() returns a list of lines",
                [], 1),

        # ========================================================
        # OOP TOUCHPOINT (incidental in SPRAG, kept for completeness)
        # ========================================================
        Concept("class_basics", "Class (basic definition)", CT.PROGRAMMING_CONSTRUCT,
                "A blueprint for creating objects, bundling data and behavior together",
                ["class definition"], 1),
    ]

    for c in concepts:
        graph.add_concept(c)

    relationships = [
        # === IS_A ===
        Relationship("local_variable", "variable", RT.IS_A, 1.0),
        Relationship("global_variable", "variable", RT.IS_A, 1.0),
        Relationship("list_comprehension", "list", RT.IS_A, 0.8,
                     "A list comprehension is a compact way of constructing a list"),
        Relationship("numpy_array", "list", RT.CONTRASTS_WITH, 0.7,
                     "NumPy arrays and Python lists both hold sequences but differ in performance and type constraints"),
        Relationship("two_way_decision", "conditional_statement", RT.IS_A, 1.0),
        Relationship("if_else_ladder", "conditional_statement", RT.IS_A, 1.0),
        Relationship("ternary_expression", "conditional_statement", RT.IS_A, 0.8),
        Relationship("break_statement", "loop", RT.IS_A, 0.7,
                     "break is a control statement used inside loops"),
        Relationship("continue_statement", "loop", RT.IS_A, 0.7,
                     "continue is a control statement used inside loops"),
        Relationship("lambda_function", "function", RT.IS_A, 1.0),
        Relationship("keyword_argument", "argument", RT.IS_A, 1.0),
        Relationship("positional_argument", "argument", RT.IS_A, 1.0),
        Relationship("default_argument", "parameter", RT.IS_A, 0.8),
        Relationship("variable_length_argument", "argument", RT.IS_A, 0.8),
        Relationship("explicit_type_conversion", "type_conversion", RT.IS_A, 1.0),
        Relationship("division_operator", "operator", RT.IS_A, 1.0),
        Relationship("exponent_operator", "operator", RT.IS_A, 1.0),
        Relationship("membership_operator", "operator", RT.IS_A, 1.0),
        Relationship("built_in_module", "module", RT.IS_A, 1.0),

        # === HAS_PART ===
        Relationship("function", "parameter", RT.HAS_PART, 1.0,
                     "A function definition has zero or more formal parameters"),
        Relationship("function", "return_statement", RT.HAS_PART, 0.9,
                     "A function body may contain one or more return statements"),
        Relationship("conditional_statement", "expression", RT.HAS_PART, 0.9,
                     "A conditional statement's test is a boolean expression"),
        Relationship("exception_handling", "exception", RT.OPERATES_ON, 1.0,
                     "try/except blocks catch and handle exception objects"),

        # === PREREQUISITE_FOR ===
        Relationship("variable", "scope", RT.PREREQUISITE_FOR, 0.8,
                     "Understanding variables is a prerequisite for understanding scope"),
        Relationship("scope", "local_variable", RT.PREREQUISITE_FOR, 0.8),
        Relationship("scope", "global_variable", RT.PREREQUISITE_FOR, 0.8),
        Relationship("function", "recursion", RT.PREREQUISITE_FOR, 0.9,
                     "Recursion requires understanding of function calls"),
        Relationship("function", "lambda_function", RT.PREREQUISITE_FOR, 0.8),
        Relationship("list", "list_comprehension", RT.PREREQUISITE_FOR, 0.9),
        Relationship("loop", "list_comprehension", RT.PREREQUISITE_FOR, 0.7,
                     "List comprehensions conceptually replace explicit loops"),
        Relationship("interpreter", "python", RT.PREREQUISITE_FOR, 0.5,
                     "Python programs are executed by an interpreter"),

        # === USES ===
        Relationship("recursion", "function", RT.USES, 1.0),
        Relationship("import_statement", "module", RT.USES, 1.0),
        Relationship("slicing", "string", RT.USES, 0.8),
        Relationship("slicing", "list", RT.USES, 0.8),
        Relationship("split_method", "string", RT.USES, 1.0),
        Relationship("append_method", "list", RT.USES, 1.0),
        Relationship("extend_method", "list", RT.USES, 1.0),
        Relationship("remove_method", "list", RT.USES, 1.0),
        Relationship("count_method", "list", RT.USES, 0.9),
        Relationship("del_statement", "list", RT.USES, 0.8),
        Relationship("min_max_functions", "list", RT.USES, 0.8),
        Relationship("file_read", "string", RT.PRODUCES, 0.7,
                     "read() produces a string; readlines() produces a list of strings"),

        # === HAS_PROPERTY ===
        Relationship("list", "mutability", RT.HAS_PROPERTY, 1.0),
        Relationship("tuple", "mutability", RT.HAS_PROPERTY, 1.0),
        Relationship("dictionary", "mutability", RT.HAS_PROPERTY, 1.0),
        Relationship("set", "mutability", RT.HAS_PROPERTY, 1.0),
        Relationship("string", "mutability", RT.HAS_PROPERTY, 1.0),
        Relationship("local_variable", "lifetime", RT.HAS_PROPERTY, 0.8),
        Relationship("global_variable", "lifetime", RT.HAS_PROPERTY, 0.7),

        # === VARIANT_OF ===
        Relationship("keyword_argument", "positional_argument", RT.VARIANT_OF, 0.6,
                     "Both are ways of binding arguments to parameters, differing in how the binding is specified"),
        Relationship("ternary_expression", "two_way_decision", RT.VARIANT_OF, 0.8,
                     "The ternary expression is a single-line variant of an if-else statement"),
        Relationship("if_else_ladder", "two_way_decision", RT.VARIANT_OF, 0.7,
                     "An if-elif-else ladder generalizes the two-way if-else to multiple branches"),

        # === CONTRASTS_WITH ===
        Relationship("list", "tuple", RT.CONTRASTS_WITH, 1.0,
                     "Lists are mutable; tuples are immutable"),
        Relationship("compiler", "interpreter", RT.CONTRASTS_WITH, 1.0,
                     "A compiler translates the whole program before execution; an interpreter executes line by line"),
        Relationship("break_statement", "continue_statement", RT.CONTRASTS_WITH, 0.9,
                     "break exits the loop entirely; continue skips only the current iteration"),
        Relationship("del_statement", "remove_method", RT.CONTRASTS_WITH, 0.8,
                     "del removes by position/reference; remove() removes by value"),
        Relationship("append_method", "extend_method", RT.CONTRASTS_WITH, 0.9,
                     "append() adds one element (even if it is itself a list); extend() adds each element of an iterable"),
        Relationship("local_variable", "global_variable", RT.CONTRASTS_WITH, 1.0),
        Relationship("keyword_argument", "positional_argument", RT.CONTRASTS_WITH, 0.7),
        Relationship("recursion", "loop", RT.CONTRASTS_WITH, 0.7,
                     "Recursion and iteration are two different techniques for repeated computation"),

        # === HAS_COMPLEXITY (kept for schema parity; qualitative only here) ===
        Relationship("numpy_array", "list", RT.HAS_COMPLEXITY, 0.4,
                     "NumPy arrays offer better time/space performance than lists for numeric operations"),
    ]

    for rel in relationships:
        graph.add_relationship(rel)

    return graph


def get_topic_questions() -> dict[str, list[str]]:
    """Sample questions mapped to expected concept subsets, mirroring the
    other domain KG modules' testing convention."""
    return {
        "Write down the mutable data structures in Python?": [
            "list", "set", "dictionary", "mutability"
        ],
        "What is the difference between list and tuple in python?": [
            "list", "tuple", "mutability"
        ],
        "What is the difference between local variable and global variable?": [
            "local_variable", "global_variable", "scope"
        ],
        "What is the difference between a compiler and an interpreter?": [
            "compiler", "interpreter"
        ],
        "What is meant by recursion?": [
            "recursion", "function"
        ],
        "What are the keywords used for exception handling in Python?": [
            "exception", "exception_handling", "keyword"
        ],
        "Can we assign a default value to a formal parameter of function?": [
            "parameter", "default_argument", "function"
        ],
    }
