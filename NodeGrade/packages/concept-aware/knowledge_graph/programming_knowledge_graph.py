"""
Expert-Curated Object-Oriented Programming & Software Engineering Domain Knowledge Graph.

This is the reference knowledge graph for OOP and Software Engineering concepts,
built from standard curriculum (Gang of Four, Robert C. Martin, Grady Booch).
Covers concepts typically assessed in introductory and intermediate CS OOP courses.
"""

from .ontology import Concept, Relationship, ConceptType as CT, RelationshipType as RT
from .domain_graph import DomainKnowledgeGraph


def build_programming_graph() -> DomainKnowledgeGraph:
    """
    Build the expert-validated OOP & Software Engineering knowledge graph.

    Covers: OOP Core, OOP Principles, Design Patterns, Class Relationships,
    Method Types, Type System, SOLID Principles, Exception Handling, Memory Management.
    """
    graph = DomainKnowledgeGraph(domain="programming_oop", version="1.0-expert")

    # ========================================================
    # ABSTRACT / FOUNDATIONAL CONCEPTS
    # ========================================================
    concepts = [
        # Top-level abstractions
        Concept("programming_paradigm", "Programming Paradigm", CT.ABSTRACT_CONCEPT,
                "A fundamental style or approach to programming that provides a framework for thinking about software",
                ["paradigm", "coding style"], 1),
        Concept("object_oriented_programming", "Object-Oriented Programming", CT.ABSTRACT_CONCEPT,
                "A programming paradigm based on the concept of objects that encapsulate data and behavior",
                ["OOP", "object orientation", "object-oriented"], 1),
        Concept("software_engineering", "Software Engineering", CT.ABSTRACT_CONCEPT,
                "The systematic application of engineering principles to the design, development, and maintenance of software",
                ["SE", "software development"], 2),

        # ========================================================
        # OOP CORE CONCEPTS
        # ========================================================
        Concept("class", "Class", CT.PROGRAMMING_CONSTRUCT,
                "A blueprint or template that defines the attributes and behaviors of objects",
                ["class definition", "type"], 1),
        Concept("object", "Object", CT.PROGRAMMING_CONSTRUCT,
                "An instance of a class that encapsulates state (attributes) and behavior (methods)",
                ["instance", "object instance"], 1),
        Concept("instance", "Instance", CT.ABSTRACT_CONCEPT,
                "A concrete realization of a class; an individual object created from a class",
                ["object instance", "instantiation"], 1),
        Concept("method", "Method", CT.PROGRAMMING_CONSTRUCT,
                "A function defined inside a class that operates on object data",
                ["member function", "behavior", "operation"], 1),
        Concept("attribute", "Attribute", CT.PROGRAMMING_CONSTRUCT,
                "A variable defined inside a class that holds object state",
                ["field", "member variable", "property", "instance variable", "data member"], 1),
        Concept("constructor", "Constructor", CT.PROGRAMMING_CONSTRUCT,
                "A special method called when an object is created, used to initialize object state",
                ["__init__", "initializer", "__new__"], 1),
        Concept("destructor", "Destructor", CT.PROGRAMMING_CONSTRUCT,
                "A special method called when an object is destroyed, used for cleanup",
                ["__del__", "finalizer"], 2),
        Concept("self", "Self / This", CT.PROGRAMMING_CONSTRUCT,
                "A reference to the current object instance within a method",
                ["this", "self keyword"], 1),

        # ========================================================
        # OOP CORE PRINCIPLES
        # ========================================================
        Concept("encapsulation", "Encapsulation", CT.ABSTRACT_CONCEPT,
                "Bundling data (attributes) and methods together in a class and restricting direct access to internal state",
                ["data hiding", "information hiding", "access control"], 1),
        Concept("inheritance", "Inheritance", CT.ABSTRACT_CONCEPT,
                "A mechanism where a subclass acquires the properties and behaviors of a parent class",
                ["subclassing", "class hierarchy", "extends", "is-a relationship"], 1),
        Concept("polymorphism", "Polymorphism", CT.ABSTRACT_CONCEPT,
                "The ability of objects of different types to be treated as objects of a common type, enabling a single interface for different forms",
                ["polymorphic", "multiple forms"], 1),
        Concept("abstraction", "Abstraction", CT.ABSTRACT_CONCEPT,
                "Hiding implementation details and exposing only essential features of an object or system",
                ["abstract", "generalization"], 1),
        Concept("interface", "Interface", CT.PROGRAMMING_CONSTRUCT,
                "A contract specifying methods that implementing classes must provide, with no implementation",
                ["protocol", "abstract interface", "Java interface"], 2),

        # ========================================================
        # CLASS TYPES
        # ========================================================
        Concept("abstract_class", "Abstract Class", CT.PROGRAMMING_CONSTRUCT,
                "A class that cannot be instantiated and may contain abstract methods that subclasses must implement",
                ["abstract base class", "ABC"], 2),
        Concept("concrete_class", "Concrete Class", CT.PROGRAMMING_CONSTRUCT,
                "A class that provides full implementations for all its methods and can be instantiated",
                ["instantiable class"], 1),
        Concept("mixin", "Mixin", CT.PROGRAMMING_CONSTRUCT,
                "A class that provides optional behavior to other classes through multiple inheritance without being a standalone entity",
                ["mixin class", "trait"], 3),
        Concept("base_class", "Base Class", CT.PROGRAMMING_CONSTRUCT,
                "A class from which other classes inherit; the parent in an inheritance hierarchy",
                ["parent class", "superclass", "super class"], 1),
        Concept("derived_class", "Derived Class", CT.PROGRAMMING_CONSTRUCT,
                "A class that inherits from a base class; the child in an inheritance hierarchy",
                ["child class", "subclass", "sub class"], 1),

        # ========================================================
        # METHOD FEATURES
        # ========================================================
        Concept("overriding", "Method Overriding", CT.PROGRAMMING_CONSTRUCT,
                "Providing a new implementation of a method in a subclass that replaces the parent class implementation",
                ["method overriding", "runtime polymorphism", "override"], 2),
        Concept("overloading", "Method Overloading", CT.PROGRAMMING_CONSTRUCT,
                "Defining multiple methods with the same name but different parameter signatures",
                ["method overloading", "compile-time polymorphism"], 2),
        Concept("method_resolution_order", "Method Resolution Order", CT.ABSTRACT_CONCEPT,
                "The order in which Python (or another language) searches for methods through the class hierarchy during inheritance",
                ["MRO", "C3 linearization", "method lookup order"], 3),
        Concept("static_method", "Static Method", CT.PROGRAMMING_CONSTRUCT,
                "A method that belongs to the class rather than any instance and does not access instance or class state",
                ["@staticmethod", "class-level method"], 2),
        Concept("class_method", "Class Method", CT.PROGRAMMING_CONSTRUCT,
                "A method that takes the class as its first argument instead of the instance",
                ["@classmethod", "cls method"], 2),

        # ========================================================
        # ACCESS MODIFIERS
        # ========================================================
        Concept("access_modifier", "Access Modifier", CT.PROGRAMMING_CONSTRUCT,
                "A keyword that sets the accessibility of a class, method, or attribute",
                ["visibility modifier", "access control"], 1),
        Concept("public", "Public", CT.PROPERTY,
                "An access level that makes a member accessible from anywhere",
                ["public access"], 1),
        Concept("private", "Private", CT.PROPERTY,
                "An access level that restricts a member to within the defining class only",
                ["private access", "name mangling"], 1),
        Concept("protected", "Protected", CT.PROPERTY,
                "An access level that restricts a member to the class and its subclasses",
                ["protected access"], 2),

        # ========================================================
        # RELATIONSHIPS BETWEEN CLASSES
        # ========================================================
        Concept("association", "Association", CT.ABSTRACT_CONCEPT,
                "A general relationship between two classes where one class uses or knows about another",
                ["class association", "uses-a"], 2),
        Concept("aggregation", "Aggregation", CT.ABSTRACT_CONCEPT,
                "A weaker form of composition where a class contains a reference to another class object, but the contained object can exist independently",
                ["has-a relationship", "weak aggregation"], 2),
        Concept("composition", "Composition", CT.ABSTRACT_CONCEPT,
                "A strong form of aggregation where the contained object cannot exist independently of the containing class",
                ["strong aggregation", "part-of relationship", "owns-a"], 2),
        Concept("dependency", "Dependency", CT.ABSTRACT_CONCEPT,
                "A relationship where one class depends on another, typically by using it as a parameter or local variable",
                ["uses relationship", "client-supplier"], 2),

        # ========================================================
        # DESIGN PATTERNS
        # ========================================================
        Concept("design_pattern", "Design Pattern", CT.DESIGN_PATTERN,
                "A reusable solution to a commonly occurring software design problem in a given context",
                ["GoF pattern", "software pattern"], 2),
        Concept("creational_pattern", "Creational Pattern", CT.DESIGN_PATTERN,
                "Design patterns that deal with object creation mechanisms",
                ["creational design pattern"], 2),
        Concept("structural_pattern", "Structural Pattern", CT.DESIGN_PATTERN,
                "Design patterns that deal with object composition and class structure",
                ["structural design pattern"], 2),
        Concept("behavioral_pattern", "Behavioral Pattern", CT.DESIGN_PATTERN,
                "Design patterns that deal with communication between objects",
                ["behavioral design pattern"], 2),
        Concept("factory_pattern", "Factory Pattern", CT.DESIGN_PATTERN,
                "A creational pattern that defines an interface for creating objects but lets subclasses decide which class to instantiate",
                ["factory method", "abstract factory", "factory"], 3),
        Concept("singleton_pattern", "Singleton Pattern", CT.DESIGN_PATTERN,
                "A creational pattern ensuring a class has only one instance and provides a global access point to it",
                ["singleton", "single instance pattern"], 3),
        Concept("observer_pattern", "Observer Pattern", CT.DESIGN_PATTERN,
                "A behavioral pattern where an object (subject) maintains a list of dependents (observers) and notifies them of state changes",
                ["observer", "publish-subscribe", "event listener"], 3),
        Concept("strategy_pattern", "Strategy Pattern", CT.DESIGN_PATTERN,
                "A behavioral pattern that defines a family of algorithms, encapsulates each one, and makes them interchangeable",
                ["strategy", "policy pattern"], 3),
        Concept("decorator_pattern", "Decorator Pattern", CT.DESIGN_PATTERN,
                "A structural pattern that adds behavior to objects dynamically by wrapping them in decorator objects",
                ["decorator", "wrapper pattern"], 3),

        # ========================================================
        # ADVANCED OOP CONCEPTS
        # ========================================================
        Concept("duck_typing", "Duck Typing", CT.ABSTRACT_CONCEPT,
                "A concept where the type of an object is determined by its behavior (methods/attributes) rather than its class hierarchy",
                ["structural typing", "EAFP", "pythonic typing"], 3),
        Concept("multiple_inheritance", "Multiple Inheritance", CT.ABSTRACT_CONCEPT,
                "A feature where a class can inherit from more than one parent class",
                ["multi-inheritance", "diamond problem"], 3),

        # ========================================================
        # SOLID PRINCIPLES & SOFTWARE DESIGN PRINCIPLES
        # ========================================================
        Concept("SOLID_principles", "SOLID Principles", CT.ABSTRACT_CONCEPT,
                "Five design principles for object-oriented software that make it more understandable, flexible, and maintainable",
                ["SOLID", "OOP design principles"], 3),
        Concept("single_responsibility", "Single Responsibility Principle", CT.PROPERTY,
                "A class should have only one reason to change; it should have a single, well-defined purpose",
                ["SRP", "single responsibility"], 3),
        Concept("open_closed_principle", "Open/Closed Principle", CT.PROPERTY,
                "Software entities should be open for extension but closed for modification",
                ["OCP", "open closed"], 3),
        Concept("liskov_substitution", "Liskov Substitution Principle", CT.PROPERTY,
                "Objects of a subclass should be substitutable for objects of the parent class without altering correctness",
                ["LSP", "Liskov"], 3),
        Concept("interface_segregation", "Interface Segregation Principle", CT.PROPERTY,
                "Clients should not be forced to depend on interfaces they do not use; prefer smaller, focused interfaces",
                ["ISP", "interface segregation"], 3),
        Concept("dependency_inversion", "Dependency Inversion Principle", CT.PROPERTY,
                "High-level modules should not depend on low-level modules; both should depend on abstractions",
                ["DIP", "dependency inversion"], 3),
        Concept("DRY_principle", "DRY Principle", CT.PROPERTY,
                "Don't Repeat Yourself — every piece of knowledge should have a single, authoritative representation in a system",
                ["DRY", "Don't Repeat Yourself", "code reuse"], 2),
        Concept("coupling", "Coupling", CT.PROPERTY,
                "The degree of interdependence between software modules; low coupling is preferred for maintainability",
                ["tight coupling", "loose coupling", "module coupling"], 2),
        Concept("cohesion", "Cohesion", CT.PROPERTY,
                "The degree to which elements within a module belong together; high cohesion is preferred",
                ["high cohesion", "module cohesion"], 2),

        # ========================================================
        # EXCEPTION HANDLING
        # ========================================================
        Concept("exception", "Exception", CT.PROGRAMMING_CONSTRUCT,
                "An event that disrupts the normal flow of a program's execution",
                ["error", "runtime error", "exception object"], 1),
        Concept("exception_handling", "Exception Handling", CT.ABSTRACT_CONCEPT,
                "A mechanism for responding to and recovering from exceptional conditions during program execution",
                ["error handling", "exception management"], 1),
        Concept("try_catch", "Try-Catch Block", CT.PROGRAMMING_CONSTRUCT,
                "A control structure that encloses code that might throw an exception and handles it if it does",
                ["try-except", "try/catch", "try block", "catch block", "except block"], 1),
        Concept("custom_exception", "Custom Exception", CT.PROGRAMMING_CONSTRUCT,
                "A user-defined exception class that inherits from a built-in exception class to represent domain-specific errors",
                ["user-defined exception", "custom error class"], 2),
        Concept("finally_block", "Finally Block", CT.PROGRAMMING_CONSTRUCT,
                "A block of code that executes regardless of whether an exception was raised or caught, used for cleanup",
                ["finally", "ensure block"], 2),

        # ========================================================
        # MEMORY MANAGEMENT
        # ========================================================
        Concept("garbage_collection", "Garbage Collection", CT.ABSTRACT_CONCEPT,
                "Automatic memory management that reclaims memory occupied by objects no longer in use",
                ["GC", "automatic memory management", "garbage collector"], 2),
        Concept("reference_counting", "Reference Counting", CT.ABSTRACT_CONCEPT,
                "A memory management technique that counts the number of references to each object and deallocates when count reaches zero",
                ["ref count", "reference count"], 3),
        Concept("memory_leak", "Memory Leak", CT.PROPERTY,
                "A condition where memory is allocated but never released, leading to progressive memory exhaustion",
                ["memory leakage", "unreleased memory"], 2),
    ]

    for concept in concepts:
        graph.add_concept(concept)

    # ========================================================
    # RELATIONSHIPS
    # ========================================================
    relationships = [
        # === IS_A hierarchies — OOP paradigm ===
        Relationship("object_oriented_programming", "programming_paradigm", RT.IS_A, 1.0),
        Relationship("class", "object_oriented_programming", RT.IS_A, 0.9,
                     "Classes are the fundamental building block of OOP"),
        Relationship("object", "object_oriented_programming", RT.IS_A, 0.9,
                     "Objects are the runtime instances in OOP"),
        Relationship("abstract_class", "class", RT.IS_A, 1.0),
        Relationship("concrete_class", "class", RT.IS_A, 1.0),
        Relationship("mixin", "class", RT.IS_A, 0.8),
        Relationship("base_class", "class", RT.IS_A, 1.0),
        Relationship("derived_class", "class", RT.IS_A, 1.0),
        Relationship("interface", "abstract_class", RT.IS_A, 0.7,
                     "Interfaces are fully abstract with no implementation"),
        Relationship("constructor", "method", RT.IS_A, 1.0),
        Relationship("destructor", "method", RT.IS_A, 1.0),
        Relationship("static_method", "method", RT.IS_A, 1.0),
        Relationship("class_method", "method", RT.IS_A, 1.0),

        # === IS_A hierarchies — Principles ===
        Relationship("encapsulation", "object_oriented_programming", RT.IS_A, 0.8),
        Relationship("inheritance", "object_oriented_programming", RT.IS_A, 0.8),
        Relationship("polymorphism", "object_oriented_programming", RT.IS_A, 0.8),
        Relationship("abstraction", "object_oriented_programming", RT.IS_A, 0.8),
        Relationship("single_responsibility", "SOLID_principles", RT.IS_A, 1.0),
        Relationship("open_closed_principle", "SOLID_principles", RT.IS_A, 1.0),
        Relationship("liskov_substitution", "SOLID_principles", RT.IS_A, 1.0),
        Relationship("interface_segregation", "SOLID_principles", RT.IS_A, 1.0),
        Relationship("dependency_inversion", "SOLID_principles", RT.IS_A, 1.0),

        # === IS_A hierarchies — Design Patterns ===
        Relationship("design_pattern", "software_engineering", RT.IS_A, 0.8),
        Relationship("factory_pattern", "creational_pattern", RT.IS_A, 1.0),
        Relationship("singleton_pattern", "creational_pattern", RT.IS_A, 1.0),
        Relationship("observer_pattern", "behavioral_pattern", RT.IS_A, 1.0),
        Relationship("strategy_pattern", "behavioral_pattern", RT.IS_A, 1.0),
        Relationship("decorator_pattern", "structural_pattern", RT.IS_A, 1.0),
        Relationship("creational_pattern", "design_pattern", RT.IS_A, 1.0),
        Relationship("structural_pattern", "design_pattern", RT.IS_A, 1.0),
        Relationship("behavioral_pattern", "design_pattern", RT.IS_A, 1.0),

        # === IS_A hierarchies — Class Relationships ===
        Relationship("aggregation", "association", RT.IS_A, 0.9,
                     "Aggregation is a specialized form of association"),
        Relationship("composition", "aggregation", RT.IS_A, 0.9,
                     "Composition is a strong form of aggregation"),
        Relationship("dependency", "association", RT.IS_A, 0.7),

        # === IS_A hierarchies — Exception ===
        Relationship("custom_exception", "exception", RT.IS_A, 1.0),

        # === HAS_PART (compositional) ===
        Relationship("class", "method", RT.HAS_PART, 1.0,
                     "Classes contain methods that define behavior"),
        Relationship("class", "attribute", RT.HAS_PART, 1.0,
                     "Classes contain attributes that define state"),
        Relationship("class", "constructor", RT.HAS_PART, 0.9),
        Relationship("object", "attribute", RT.HAS_PART, 1.0,
                     "Objects hold instance attribute values"),
        Relationship("try_catch", "exception_handling", RT.HAS_PART, 1.0),
        Relationship("try_catch", "finally_block", RT.HAS_PART, 0.7),
        Relationship("SOLID_principles", "single_responsibility", RT.HAS_PART, 1.0),
        Relationship("SOLID_principles", "open_closed_principle", RT.HAS_PART, 1.0),
        Relationship("SOLID_principles", "liskov_substitution", RT.HAS_PART, 1.0),
        Relationship("SOLID_principles", "interface_segregation", RT.HAS_PART, 1.0),
        Relationship("SOLID_principles", "dependency_inversion", RT.HAS_PART, 1.0),
        Relationship("encapsulation", "access_modifier", RT.HAS_PART, 0.9,
                     "Encapsulation uses access modifiers to control visibility"),
        Relationship("access_modifier", "public", RT.HAS_PART, 1.0),
        Relationship("access_modifier", "private", RT.HAS_PART, 1.0),
        Relationship("access_modifier", "protected", RT.HAS_PART, 1.0),

        # === VARIANT_OF ===
        Relationship("overriding", "polymorphism", RT.VARIANT_OF, 0.8,
                     "Method overriding is the runtime form of polymorphism"),
        Relationship("overloading", "polymorphism", RT.VARIANT_OF, 0.7,
                     "Method overloading is the compile-time form of polymorphism"),
        Relationship("duck_typing", "polymorphism", RT.VARIANT_OF, 0.7,
                     "Duck typing achieves polymorphism through structural compatibility"),
        Relationship("multiple_inheritance", "inheritance", RT.VARIANT_OF, 1.0),
        Relationship("mixin", "multiple_inheritance", RT.VARIANT_OF, 0.8,
                     "Mixins exploit multiple inheritance for optional behavior composition"),

        # === IMPLEMENTS ===
        Relationship("concrete_class", "interface", RT.IMPLEMENTS, 1.0,
                     "Concrete classes implement interfaces by providing method bodies"),
        Relationship("derived_class", "abstract_class", RT.IMPLEMENTS, 0.9,
                     "Derived classes implement abstract methods of the abstract class"),
        Relationship("overriding", "polymorphism", RT.IMPLEMENTS, 1.0,
                     "Overriding is the mechanism that implements runtime polymorphism"),
        Relationship("singleton_pattern", "encapsulation", RT.IMPLEMENTS, 0.7,
                     "Singleton hides its constructor using encapsulation"),
        Relationship("factory_pattern", "abstraction", RT.IMPLEMENTS, 0.8,
                     "Factory pattern abstracts the object creation process"),
        Relationship("observer_pattern", "dependency_inversion", RT.IMPLEMENTS, 0.7),
        Relationship("strategy_pattern", "open_closed_principle", RT.IMPLEMENTS, 0.8,
                     "Strategy allows extending behavior without modifying existing code"),
        Relationship("decorator_pattern", "open_closed_principle", RT.IMPLEMENTS, 0.8,
                     "Decorator adds behavior to objects without modifying their class"),

        # === USES ===
        Relationship("derived_class", "base_class", RT.USES, 1.0,
                     "Derived classes use base class methods and attributes"),
        Relationship("method_resolution_order", "multiple_inheritance", RT.USES, 1.0,
                     "MRO is used to resolve method lookup in multiple inheritance"),
        Relationship("exception_handling", "try_catch", RT.USES, 1.0),
        Relationship("reference_counting", "garbage_collection", RT.USES, 0.8,
                     "Reference counting is one strategy used in garbage collection"),
        Relationship("observer_pattern", "interface", RT.USES, 0.8,
                     "Observer pattern uses interfaces for the observer contract"),
        Relationship("strategy_pattern", "interface", RT.USES, 0.8,
                     "Strategy pattern uses an interface for algorithm family"),
        Relationship("factory_pattern", "inheritance", RT.USES, 0.9,
                     "Factory method relies on inheritance to delegate object creation"),

        # === PREREQUISITE_FOR ===
        Relationship("class", "object", RT.PREREQUISITE_FOR, 1.0,
                     "A class must be defined before objects can be created from it"),
        Relationship("class", "inheritance", RT.PREREQUISITE_FOR, 1.0),
        Relationship("class", "encapsulation", RT.PREREQUISITE_FOR, 0.9),
        Relationship("inheritance", "polymorphism", RT.PREREQUISITE_FOR, 0.9,
                     "Inheritance is a prerequisite for subtype polymorphism"),
        Relationship("inheritance", "overriding", RT.PREREQUISITE_FOR, 1.0,
                     "Method overriding requires an inheritance relationship"),
        Relationship("inheritance", "method_resolution_order", RT.PREREQUISITE_FOR, 1.0),
        Relationship("abstract_class", "interface", RT.PREREQUISITE_FOR, 0.7),
        Relationship("encapsulation", "abstraction", RT.PREREQUISITE_FOR, 0.7,
                     "Encapsulation is foundational to achieving abstraction"),
        Relationship("exception", "exception_handling", RT.PREREQUISITE_FOR, 1.0),
        Relationship("exception", "custom_exception", RT.PREREQUISITE_FOR, 1.0),
        Relationship("class", "design_pattern", RT.PREREQUISITE_FOR, 0.9,
                     "Understanding classes is required to understand design patterns"),
        Relationship("inheritance", "design_pattern", RT.PREREQUISITE_FOR, 0.8),
        Relationship("polymorphism", "design_pattern", RT.PREREQUISITE_FOR, 0.8),
        Relationship("SOLID_principles", "software_engineering", RT.PREREQUISITE_FOR, 0.8),
        Relationship("design_pattern", "software_engineering", RT.PREREQUISITE_FOR, 0.8),
        Relationship("multiple_inheritance", "method_resolution_order", RT.PREREQUISITE_FOR, 1.0),
        Relationship("base_class", "derived_class", RT.PREREQUISITE_FOR, 1.0),

        # === HAS_PROPERTY ===
        Relationship("composition", "coupling", RT.HAS_PROPERTY, 0.8,
                     "Composition creates tight coupling between composing classes"),
        Relationship("aggregation", "coupling", RT.HAS_PROPERTY, 0.6,
                     "Aggregation creates looser coupling than composition"),
        Relationship("encapsulation", "cohesion", RT.HAS_PROPERTY, 0.9,
                     "Well-encapsulated classes tend to have high cohesion"),
        Relationship("single_responsibility", "cohesion", RT.HAS_PROPERTY, 1.0,
                     "SRP directly drives high cohesion within a class"),
        Relationship("dependency_inversion", "coupling", RT.HAS_PROPERTY, 0.8,
                     "DIP reduces coupling between high- and low-level modules"),
        Relationship("singleton_pattern", "single_responsibility", RT.HAS_PROPERTY, 0.6),
        Relationship("DRY_principle", "cohesion", RT.HAS_PROPERTY, 0.7,
                     "DRY promotes keeping related logic together"),
        Relationship("memory_leak", "garbage_collection", RT.HAS_PROPERTY, 0.7,
                     "Proper garbage collection prevents memory leaks"),

        # === OPERATES_ON ===
        Relationship("method", "object", RT.OPERATES_ON, 1.0,
                     "Methods operate on object state (attributes)"),
        Relationship("constructor", "object", RT.OPERATES_ON, 1.0,
                     "Constructors initialize the object's state at creation"),
        Relationship("destructor", "object", RT.OPERATES_ON, 1.0),
        Relationship("garbage_collection", "object", RT.OPERATES_ON, 1.0,
                     "Garbage collector reclaims unreachable object memory"),
        Relationship("reference_counting", "object", RT.OPERATES_ON, 1.0),
        Relationship("overriding", "method", RT.OPERATES_ON, 1.0),
        Relationship("overloading", "method", RT.OPERATES_ON, 1.0),
        Relationship("exception_handling", "exception", RT.OPERATES_ON, 1.0),
        Relationship("method_resolution_order", "class", RT.OPERATES_ON, 1.0),

        # === PRODUCES ===
        Relationship("class", "object", RT.PRODUCES, 1.0,
                     "Instantiating a class produces an object"),
        Relationship("factory_pattern", "object", RT.PRODUCES, 1.0,
                     "Factory pattern produces objects through a factory method"),
        Relationship("constructor", "instance", RT.PRODUCES, 1.0,
                     "The constructor produces a fully initialized instance"),

        # === CONTRASTS_WITH ===
        Relationship("composition", "aggregation", RT.CONTRASTS_WITH, 0.9,
                     "Composition implies ownership; aggregation does not"),
        Relationship("encapsulation", "abstraction", RT.CONTRASTS_WITH, 0.6,
                     "Encapsulation hides data; abstraction hides complexity"),
        Relationship("overriding", "overloading", RT.CONTRASTS_WITH, 0.9,
                     "Overriding is runtime polymorphism; overloading is compile-time"),
        Relationship("abstract_class", "interface", RT.CONTRASTS_WITH, 0.8,
                     "Abstract classes may have state; interfaces have no state"),
        Relationship("public", "private", RT.CONTRASTS_WITH, 1.0),
        Relationship("coupling", "cohesion", RT.CONTRASTS_WITH, 0.7,
                     "Good design seeks low coupling and high cohesion simultaneously"),
        Relationship("static_method", "class_method", RT.CONTRASTS_WITH, 0.8,
                     "Static methods have no class/instance access; class methods receive the class"),
        Relationship("duck_typing", "inheritance", RT.CONTRASTS_WITH, 0.7,
                     "Duck typing uses structural compatibility instead of class hierarchy"),
        Relationship("reference_counting", "garbage_collection", RT.CONTRASTS_WITH, 0.7,
                     "Reference counting is synchronous; tracing GC is asynchronous"),
    ]

    for rel in relationships:
        graph.add_relationship(rel)

    return graph


def get_topic_questions() -> dict[str, list[str]]:
    """
    Return sample questions mapped to their expected concept subsets.
    Used for testing concept extraction against the OOP knowledge graph.
    """
    return {
        "What is a class and how does it differ from an object?": [
            "class", "object", "instance", "attribute", "method", "constructor"
        ],
        "Explain the four pillars of OOP": [
            "encapsulation", "inheritance", "polymorphism", "abstraction"
        ],
        "What is method overriding vs method overloading?": [
            "overriding", "overloading", "polymorphism", "inheritance", "derived_class"
        ],
        "Describe the difference between composition and aggregation": [
            "composition", "aggregation", "association", "coupling", "dependency"
        ],
        "What is the Singleton design pattern?": [
            "singleton_pattern", "design_pattern", "creational_pattern", "encapsulation", "object"
        ],
        "Explain the SOLID principles": [
            "SOLID_principles", "single_responsibility", "open_closed_principle",
            "liskov_substitution", "interface_segregation", "dependency_inversion"
        ],
        "What is duck typing in Python?": [
            "duck_typing", "polymorphism", "interface", "method"
        ],
        "How does garbage collection work?": [
            "garbage_collection", "reference_counting", "memory_leak", "object", "destructor"
        ],
    }
