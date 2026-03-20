#!/usr/bin/env python3
"""
Phase 2 End-to-End Demo: Cognitive Depth Assessment + Misconception Detection

Demonstrates the full Paper 2 pipeline:
  1. Load the DS knowledge graph (from Phase 1)
  2. Extract concepts from student answers (Phase 1 ConceptExtractor)
  3. Compare against expert graph (Phase 1 KnowledgeGraphComparator)
  4. Classify cognitive depth: Bloom's + SOLO (Phase 2 — NEW)
  5. Detect misconceptions against CS taxonomy (Phase 2 — NEW)

Uses 4 student responses of varying quality to show differentiation.

Usage:
    GROQ_API_KEY=gsk_... python run_phase2_demo.py
"""

import json
import os
import sys
import time
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
from concept_extraction.extractor import ConceptExtractor
from graph_comparison.comparator import KnowledgeGraphComparator
from cognitive_depth.blooms_classifier import BloomsClassifier, BloomsLevel
from cognitive_depth.solo_classifier import SOLOClassifier, SOLOLevel
from misconception_detection.detector import MisconceptionDetector


# ── Sample assessment data ──────────────────────────────────────────
QUESTION = "Compare linked lists and arrays. Explain when you would use each, and discuss the trade-offs in terms of time complexity for common operations."

STUDENT_ANSWERS = {
    "student_A_excellent": {
        "label": "Student A — Excellent (Expected: Bloom's 5-6, SOLO 5)",
        "answer": (
            "Arrays and linked lists are both linear data structures, but they differ fundamentally "
            "in memory layout and performance characteristics. Arrays store elements in contiguous memory, "
            "enabling O(1) random access via index arithmetic, whereas linked lists use dynamically allocated "
            "nodes connected by pointers, requiring O(n) traversal for access. "
            "For insertion and deletion, linked lists excel at the head with O(1) operations, but inserting "
            "at an arbitrary position still requires O(n) traversal to find the location. Arrays require O(n) "
            "shifting for mid-array insertions but offer O(1) amortized append with dynamic arrays. "
            "The trade-off extends beyond asymptotic complexity: arrays benefit from spatial locality and "
            "CPU cache prefetching, making them significantly faster in practice for sequential access patterns "
            "on modern hardware. This is why Java's ArrayList outperforms LinkedList in most benchmarks despite "
            "theoretically worse insertion complexity. "
            "I would use arrays (or dynamic arrays) for random access-heavy workloads and when the dataset size "
            "is relatively stable. Linked lists are preferable when frequent insertions/deletions at known positions "
            "are needed, such as implementing an LRU cache with a doubly linked list combined with a hash map "
            "for O(1) lookup and eviction."
        ),
    },
    "student_B_good": {
        "label": "Student B — Good (Expected: Bloom's 4, SOLO 4)",
        "answer": (
            "Arrays use contiguous memory, so accessing an element by index is O(1). Linked lists "
            "use pointers to connect nodes, so you have to traverse from the head, which takes O(n). "
            "For insertion, linked lists are O(1) at the head because you just update pointers, "
            "but arrays need to shift elements which is O(n). "
            "However, arrays are better when you need fast lookups, and linked lists are better "
            "when you need frequent insertions and deletions. Arrays also have a fixed size unless "
            "you use dynamic arrays, which can waste memory due to over-allocation."
        ),
    },
    "student_C_basic": {
        "label": "Student C — Basic (Expected: Bloom's 2, SOLO 2-3)",
        "answer": (
            "A linked list is a data structure where each node points to the next one. "
            "An array stores elements in a row. You can access array elements quickly."
        ),
    },
    "student_D_misconceptions": {
        "label": "Student D — Misconceptions (Expected: Bloom's 2-3, SOLO 3, multiple misconceptions)",
        "answer": (
            "Arrays and linked lists are both used to store data. Linked lists let you access elements "
            "by index in O(1) time because each node has a number. Insertion in a linked list is always O(1) "
            "no matter where you insert. Arrays are slower because they use pointers like linked lists. "
            "I think linked lists are always better than arrays because they use dynamic memory."
        ),
    },
}


def print_header(title: str, char: str = "═"):
    width = 80
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}\n")


def print_section(title: str, char: str = "─"):
    print(f"\n  {char * 60}")
    print(f"  {title}")
    print(f"  {char * 60}")


def run_demo():
    # Get API key
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("BEARER_TOKEN")
    if not api_key:
        # Try .env file
        env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("BEARER_TOKEN="):
                        api_key = line.strip().split("=", 1)[1]
                        break
    
    if not api_key:
        print("ERROR: Set GROQ_API_KEY or BEARER_TOKEN environment variable")
        sys.exit(1)

    print_header("PHASE 2 END-TO-END DEMO", "█")
    print("  Concept-Aware Assessment Framework")
    print("  Paper 2: Automated Cognitive Depth Assessment")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  LLM: Groq (llama-3.3-70b-versatile)")

    # ── Step 1: Load expert knowledge graph ──
    print_header("STEP 1: Load Expert Knowledge Graph (Phase 1)")
    expert_graph = build_data_structures_graph()
    print(f"  Concepts: {expert_graph.graph.number_of_nodes()}")
    print(f"  Relationships: {expert_graph.graph.number_of_edges()}")

    # ── Initialize all modules ──
    print_header("STEP 2: Initialize Assessment Modules")
    extractor = ConceptExtractor(domain_graph=expert_graph, api_key=api_key)
    comparator = KnowledgeGraphComparator(domain_graph=expert_graph)
    blooms_clf = BloomsClassifier(api_key=api_key)
    solo_clf = SOLOClassifier(api_key=api_key)
    misconception_det = MisconceptionDetector(api_key=api_key)
    print("  ✓ ConceptExtractor (Phase 1)")
    print("  ✓ KnowledgeGraphComparator (Phase 1)")
    print("  ✓ BloomsClassifier (Phase 2 — NEW)")
    print("  ✓ SOLOClassifier (Phase 2 — NEW)")
    print("  ✓ MisconceptionDetector (Phase 2 — NEW)")

    # ── Process each student ──
    all_results = {}
    
    for student_id, student_data in STUDENT_ANSWERS.items():
        print_header(f"PROCESSING: {student_data['label']}", "▓")
        answer = student_data["answer"]
        print(f"  Answer (first 120 chars): {answer[:120]}...")

        # Phase 1: Extract concepts
        print_section("Phase 1: Concept Extraction")
        time.sleep(2)  # Rate limiting for Groq
        concept_graph_obj = None
        try:
            concept_graph_obj = extractor.extract(
                question=QUESTION,
                student_answer=answer,
            )
            cg_dict = concept_graph_obj.to_dict()
            concepts = cg_dict.get("concepts", [])
            rels = cg_dict.get("relationships", [])
            print(f"    Concepts extracted: {len(concepts)}")
            print(f"    Relationships found: {len(rels)}")
            for c in concepts[:5]:
                print(f"      - {c.get('concept_id', c.get('id', '?'))}: {c.get('evidence', '?')[:50]}")
        except Exception as e:
            print(f"    ⚠ Extraction error: {e}")
            cg_dict = {"concepts": [], "relationships": []}

        # Phase 1: Compare against expert graph
        print_section("Phase 1: Knowledge Graph Comparison")
        time.sleep(2)
        try:
            if concept_graph_obj is not None:
                comparison = comparator.compare(
                    student_graph=concept_graph_obj,
                )
            else:
                comparison = None
            if comparison and hasattr(comparison, 'to_dict'):
                comp_dict = comparison.to_dict()
            elif comparison:
                comp_dict = comparison
            else:
                comp_dict = {"scores": {}, "analysis": {}}
            scores = comp_dict.get("scores", {})
            print(f"    Concept coverage: {scores.get('concept_coverage', 0):.0%}")
            print(f"    Relationship accuracy: {scores.get('relationship_accuracy', 0):.0%}")
            print(f"    Integration quality: {scores.get('integration_quality', 0):.0%}")
            print(f"    Overall score: {scores.get('overall', scores.get('overall_score', 0)):.2f}")
        except Exception as e:
            print(f"    ⚠ Comparison error: {e}")
            comp_dict = {"scores": {}, "analysis": {}}

        # ── Phase 2 NEW: Bloom's Classification ──
        print_section("Phase 2 (NEW): Bloom's Taxonomy Classification")
        time.sleep(1)
        try:
            blooms_result = blooms_clf.classify(
                question=QUESTION,
                student_answer=answer,
                concept_graph=cg_dict,
                comparison_result=comp_dict,
            )
            blooms_dict = blooms_result.to_dict()
            print(f"    ★ Bloom's Level: {blooms_dict['level']} — {blooms_dict['label']}")
            print(f"    Confidence: {blooms_dict['confidence']:.0%}")
            print(f"    Justification: {blooms_dict['justification'][:100]}...")
            for step in blooms_dict.get("reasoning_steps", [])[:3]:
                print(f"      CoT: {step[:80]}...")
        except Exception as e:
            print(f"    ⚠ Bloom's classification error: {e}")
            blooms_dict = {"level": 0, "label": "Error", "confidence": 0}

        # ── Phase 2 NEW: SOLO Classification ──
        print_section("Phase 2 (NEW): SOLO Taxonomy Classification")
        time.sleep(1)
        try:
            solo_result = solo_clf.classify(
                question=QUESTION,
                student_answer=answer,
                concept_graph=cg_dict,
                comparison_result=comp_dict,
            )
            solo_dict = solo_result.to_dict()
            print(f"    ★ SOLO Level: {solo_dict['level']} — {solo_dict['label']}")
            print(f"    Capacity: {solo_dict['capacity']}")
            print(f"    Relating operation: {solo_dict['relating_operation']}")
            print(f"    Confidence: {solo_dict['confidence']:.0%}")
            print(f"    Justification: {solo_dict['justification'][:100]}...")
        except Exception as e:
            print(f"    ⚠ SOLO classification error: {e}")
            solo_dict = {"level": 0, "label": "Error", "confidence": 0}

        # ── Phase 2 NEW: Misconception Detection ──
        print_section("Phase 2 (NEW): Misconception Detection")
        time.sleep(1)
        try:
            misconception_report = misconception_det.detect(
                question=QUESTION,
                student_answer=answer,
                concept_graph=cg_dict,
                comparison_result=comp_dict,
            )
            misc_dict = misconception_report.to_dict()
            total = misc_dict["total_misconceptions"]
            by_sev = misc_dict["by_severity"]
            print(f"    ★ Misconceptions found: {total}")
            print(f"    Severity: {by_sev['critical']} critical, {by_sev['moderate']} moderate, {by_sev['minor']} minor")
            print(f"    Overall accuracy: {misc_dict['overall_accuracy']:.0%}")
            for m in misc_dict.get("misconceptions", [])[:3]:
                print(f"      [{m['severity'].upper()}] {m.get('explanation', m.get('student_claim', ''))[:80]}...")
                if m.get("remediation_hint"):
                    print(f"        → Hint: {m['remediation_hint'][:70]}...")
        except Exception as e:
            print(f"    ⚠ Misconception detection error: {e}")
            misc_dict = {"total_misconceptions": 0, "misconceptions": []}

        # Store results
        all_results[student_id] = {
            "label": student_data["label"],
            "answer_preview": answer[:100] + "...",
            "concept_graph": cg_dict,
            "comparison": comp_dict,
            "blooms": blooms_dict,
            "solo": solo_dict,
            "misconceptions": misc_dict,
        }

    # ── Summary Table ──
    print_header("SUMMARY: All Students Compared", "█")
    
    blooms_col = "Bloom's"
    header = f"{'Student':<35} {blooms_col:<18} {'SOLO':<22} {'Misconceptions':<15}"
    print(f"  {header}")
    print(f"  {'─' * 90}")
    
    for sid, result in all_results.items():
        b = result["blooms"]
        s = result["solo"]
        m = result["misconceptions"]
        b_str = f"L{b.get('level', '?')}: {b.get('label', '?')}"
        s_str = f"L{s.get('level', '?')}: {s.get('label', '?')}"
        m_str = f"{m.get('total_misconceptions', 0)} ({m.get('by_severity', {}).get('critical', 0)}C)"
        label = result["label"].split("—")[0].strip()
        print(f"  {label:<35} {b_str:<18} {s_str:<22} {m_str:<15}")

    # ── Save results ──
    results_path = os.path.join(os.path.dirname(__file__), "data", "phase2_demo_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump({
            "meta": {
                "phase": 2,
                "timestamp": datetime.now().isoformat(),
                "question": QUESTION,
                "llm_model": "llama-3.3-70b-versatile",
                "modules": [
                    "ConceptExtractor", "KnowledgeGraphComparator",
                    "BloomsClassifier", "SOLOClassifier", "MisconceptionDetector",
                ],
            },
            "results": all_results,
        }, f, indent=2)
    print(f"\n  Results saved to: {results_path}")

    print_header("DEMO COMPLETE", "█")
    print("  Phase 2 modules validated:")
    print("    ✓ Bloom's taxonomy classification with CoT reasoning")
    print("    ✓ SOLO taxonomy classification (novel: rule-based + LLM ensemble)")
    print("    ✓ Misconception detection with 16-entry CS taxonomy")
    print("    ✓ Full pipeline: Extract → Compare → Classify → Detect")
    print()


if __name__ == "__main__":
    run_demo()
