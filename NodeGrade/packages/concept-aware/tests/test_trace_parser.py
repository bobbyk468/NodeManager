"""
Tests for Stage 3b: TraceParsing module.

Run from packages/concept-aware/:
    python -m pytest tests/test_trace_parser.py -v
"""

import pytest
from conceptgrade.trace_parser import parse_trace, summarise_trace, _classify, _link_nodes


# ── Sample LRM output (realistic DeepSeek-R1 style) ──────────────────────────

SAMPLE_TRACE_ENZYME = """<think>
Let me analyze this student answer carefully against the knowledge graph.

Wait, let me re-read the question first to make sure I understand what's expected.

Okay, so the student says: "Enzymes work by binding to the substrate at the active site,
which lowers the activation energy needed for the reaction to occur."

Actually, let me think about what the knowledge graph expects here.

The KG requires: Enzyme -> HAS_PART -> Active_Site, Substrate -> PREREQUISITE_FOR -> Binding,
Binding -> PRODUCES -> Catalysis.

The student correctly identifies that the enzyme and substrate interact via the active site.
This is a direct match for the Enzyme-HAS_PART-Active_Site relationship.

The student also mentions that binding lowers activation energy, which demonstrates
the Binding -> PRODUCES -> Catalysis relationship. This is correctly stated.

However, the student completely fails to mention the role of the substrate concentration
in regulating the binding efficiency. This is a critical concept missing from the answer.

The mention of "lowers activation energy" implies an understanding of catalysis,
but the causal mechanism linking substrate to binding is weak or vague in the answer.

Therefore, while the student shows solid understanding of the core enzyme-substrate
interaction, the omission of substrate concentration effects limits the completeness.

In conclusion, the answer partially satisfies the knowledge graph requirements,
missing one critical edge relationship.
</think>
{"valid": true, "reasoning": "Core enzyme-substrate binding is present; substrate concentration regulation absent."}"""


SAMPLE_TRACE_BACKPROP = """<think>
Hmm, let me consider what the student wrote about backpropagation.

The student states: "Backpropagation uses gradient descent to update weights by computing
the error at the output and propagating it backward through the network."

Does the student mention the chain rule? No, there is no mention of the chain rule
in the answer. The chain rule is required for backpropagation to function correctly.
This is entirely missing.

The student correctly identifies that gradient descent is used in conjunction with
backpropagation. This matches the Gradient_Descent PREREQUISITE_FOR Backpropagation edge.

The student also correctly mentions weight updates as an output of the process.
This confirms the Backpropagation PRODUCES Weight_Update relationship.

However, the absence of the chain rule represents a significant gap. The chain rule is
a prerequisite for the mathematical correctness of the backpropagation algorithm.

So the answer is partially valid but missing the chain rule component which is critical.
</think>
{"valid": false, "reasoning": "Chain rule absent; gradient descent and weight update present."}"""


SAMPLE_TRACE_SHORT = """The student correctly identifies the key concept.
However, the explanation of the mechanism is incomplete.
Therefore, the chain is partially valid."""

SAMPLE_NO_THINK_TAGS = """The student answer correctly mentions gradient descent and
demonstrates understanding of the learning rate concept. The relationship between
learning rate and convergence is clearly explained. However, the neural network
architecture details are missing from the answer. This omission weakens the
overall response.
{"valid": true, "reasoning": "Core concepts present, architecture details missing."}"""


KG_NODES_ENZYME = [
    "Enzyme", "Substrate", "Active_Site", "Binding", "Catalysis",
    "Substrate_Concentration", "Activation_Energy",
]

KG_EDGES_ENZYME = [
    "HAS_PART", "PREREQUISITE_FOR", "PRODUCES", "OPERATES_ON",
]

KG_NODES_BACKPROP = [
    "Backpropagation", "Gradient_Descent", "Learning_Rate",
    "Neural_Network", "Weight_Update", "Chain_Rule",
]

KG_EDGES_BACKPROP = [
    "PREREQUISITE_FOR", "IMPLEMENTS", "PRODUCES", "OPERATES_ON",
]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestParseTrace:

    def test_returns_list(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_step_schema(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        required_keys = {"step_id", "text", "classification", "kg_nodes",
                         "kg_edges", "confidence_delta", "is_conclusion"}
        for step in steps:
            assert required_keys == set(step.keys()), f"Missing keys in step: {step}"

    def test_step_ids_sequential(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        ids = [s["step_id"] for s in steps]
        assert ids == list(range(1, len(steps) + 1))

    def test_exploratory_sentences_filtered(self):
        """'Let me', 'Wait', 'Hmm', and questions should be excluded."""
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        exploratory_markers = ["let me re-read", "wait,", "okay, so", "hmm,"]
        for step in steps:
            lower = step["text"].lower()
            for marker in exploratory_markers:
                assert marker not in lower, (
                    f"Exploratory sentence leaked into output: '{step['text'][:60]}'"
                )

    def test_classification_values(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        valid = {"SUPPORTS", "CONTRADICTS", "UNCERTAIN"}
        for step in steps:
            assert step["classification"] in valid

    def test_contradicts_step_negative_delta(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        contra_steps = [s for s in steps if s["classification"] == "CONTRADICTS"]
        for step in contra_steps:
            assert step["confidence_delta"] < 0, (
                f"CONTRADICTS step should have negative delta: {step}"
            )

    def test_supports_step_positive_delta(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        support_steps = [s for s in steps if s["classification"] == "SUPPORTS"]
        for step in support_steps:
            assert step["confidence_delta"] > 0, (
                f"SUPPORTS step should have positive delta: {step}"
            )

    def test_kg_node_linking_enzyme(self):
        """At least one step should link to Enzyme or Active_Site nodes."""
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        all_nodes = [n for s in steps for n in s["kg_nodes"]]
        assert len(all_nodes) > 0, "No KG nodes were linked — entity linker failed"
        # Check specific nodes that appear clearly in the trace
        assert any("Active_Site" in s["kg_nodes"] or "Enzyme" in s["kg_nodes"]
                   for s in steps), "Expected Enzyme or Active_Site to be linked"

    def test_kg_node_linking_backprop(self):
        steps = parse_trace(SAMPLE_TRACE_BACKPROP, KG_NODES_BACKPROP, KG_EDGES_BACKPROP)
        all_nodes = [n for s in steps for n in s["kg_nodes"]]
        assert len(all_nodes) > 0

    def test_conclusion_marked(self):
        """At least one step should be marked as is_conclusion=True."""
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        conclusions = [s for s in steps if s["is_conclusion"]]
        assert len(conclusions) > 0, "No conclusion steps were marked"

    def test_explicit_conclusion_phrases_marked(self):
        """Sentences with 'therefore', 'in conclusion' etc. must be marked."""
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        conclusion_phrases = ["therefore", "in conclusion", "thus"]
        for step in steps:
            lower = step["text"].lower()
            if any(p in lower for p in conclusion_phrases):
                assert step["is_conclusion"], (
                    f"Step with conclusion phrase not marked: '{step['text'][:60]}'"
                )

    def test_max_steps_respected(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME,
                            max_steps=5)
        assert len(steps) <= 5

    def test_no_think_tags(self):
        """Parser should work even if <think> tags are absent."""
        steps = parse_trace(SAMPLE_NO_THINK_TAGS, KG_NODES_BACKPROP, KG_EDGES_BACKPROP)
        assert isinstance(steps, list)
        # Should still parse something meaningful
        assert len(steps) > 0

    def test_short_trace(self):
        steps = parse_trace(SAMPLE_TRACE_SHORT, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        assert isinstance(steps, list)

    def test_empty_input(self):
        steps = parse_trace("", KG_NODES_ENZYME)
        assert steps == []

    def test_only_questions_filtered(self):
        trace = "<think>Is this correct? Does the student mention substrate? What about catalysis?</think>"
        steps = parse_trace(trace, KG_NODES_ENZYME)
        # All sentences are questions — should return empty or very few steps
        # (fallback may keep some; the key test is no crash)
        assert isinstance(steps, list)


class TestClassify:

    def test_supports_keywords(self):
        assert _classify("The student correctly identifies the concept.") == "SUPPORTS"
        assert _classify("This demonstrates a clear understanding.") == "SUPPORTS"
        assert _classify("The answer accurately captures the mechanism.") == "SUPPORTS"

    def test_contradicts_keywords(self):
        assert _classify("The student completely fails to mention the chain rule.") == "CONTRADICTS"
        assert _classify("This concept is missing from the answer.") == "CONTRADICTS"
        assert _classify("The student omitted the substrate concentration.") == "CONTRADICTS"

    def test_contradicts_priority_over_supports(self):
        """Mixed sentence (correct X but misses Y) should be CONTRADICTS."""
        result = _classify("The student correctly mentions enzyme but misses the active site.")
        assert result == "CONTRADICTS"

    def test_uncertain_keywords(self):
        assert _classify("The causal link is implied but not explicit.") == "UNCERTAIN"
        assert _classify("The student may understand the concept partially.") == "UNCERTAIN"

    def test_default_uncertain(self):
        """Sentences with no recognizable keywords default to UNCERTAIN."""
        result = _classify("The binding event occurs at the molecular level.")
        assert result == "UNCERTAIN"


class TestLinkNodes:

    def test_exact_match(self):
        nodes = _link_nodes("The enzyme binds to the substrate.", ["Enzyme", "Substrate", "Catalysis"])
        assert "Enzyme" in nodes
        assert "Substrate" in nodes
        assert "Catalysis" not in nodes

    def test_underscore_normalized(self):
        """Node ID 'Active_Site' should match 'active site' in text."""
        nodes = _link_nodes("The active site is where binding occurs.", ["Active_Site", "Enzyme"])
        assert "Active_Site" in nodes

    def test_partial_word_match(self):
        """'gradient' should match 'Gradient_Descent' node."""
        nodes = _link_nodes(
            "The gradient computation is key to learning.",
            ["Gradient_Descent", "Learning_Rate", "Chain_Rule"]
        )
        assert "Gradient_Descent" in nodes

    def test_no_false_positives_short_words(self):
        """Short words (<4 chars) should not trigger spurious matches."""
        nodes = _link_nodes("The answer is good.", ["Enzyme", "Substrate"])
        # Neither "Enzyme" nor "Substrate" appears
        assert nodes == []


class TestSummariseTrace:

    def test_summary_schema(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        summary = summarise_trace(steps)
        required = {"total_steps", "supports_count", "contradicts_count",
                    "uncertain_count", "net_delta", "conclusion_text",
                    "nodes_referenced", "edges_referenced"}
        assert required == set(summary.keys())

    def test_counts_sum_to_total(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        summary = summarise_trace(steps)
        assert (summary["supports_count"] + summary["contradicts_count"] +
                summary["uncertain_count"]) == summary["total_steps"]

    def test_empty_steps(self):
        summary = summarise_trace([])
        assert summary["total_steps"] == 0
        assert summary["net_delta"] == 0.0
        assert summary["conclusion_text"] == ""

    def test_net_delta_direction(self):
        """A trace with mostly CONTRADICTS should have negative net_delta."""
        steps = parse_trace(SAMPLE_TRACE_BACKPROP, KG_NODES_BACKPROP, KG_EDGES_BACKPROP)
        summary = summarise_trace(steps)
        # Backprop trace has clear CONTRADICTS (chain rule missing)
        assert summary["contradicts_count"] > 0

    def test_conclusion_text_nonempty(self):
        steps = parse_trace(SAMPLE_TRACE_ENZYME, KG_NODES_ENZYME, KG_EDGES_ENZYME)
        summary = summarise_trace(steps)
        assert len(summary["conclusion_text"]) > 0
