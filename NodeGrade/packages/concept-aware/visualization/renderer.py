"""
Visualization Renderer for ConceptGrade Analytics.

Generates visualization data structures that can be rendered by:
  - A web frontend (D3.js / Plotly / Chart.js)
  - The NodeGrade visualization panel
  - Exported as static HTML reports

Visualization types:
  1. Concept Map — Student vs Expert concept graph overlay
  2. Bloom's/SOLO Distribution — Bar/pie charts of taxonomy levels
  3. Misconception Heatmap — Concept × Severity matrix
  4. Concept Co-occurrence Matrix — Which concepts appear together
  5. Student Comparison Radar — Multi-dimensional student profiles
  6. Class Summary Dashboard — Aggregate metrics
"""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VisualizationSpec:
    """A complete visualization specification for rendering."""
    viz_id: str
    viz_type: str  # bar, heatmap, concept_map, radar, table, etc.
    title: str
    subtitle: str = ""
    data: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    insights: list = field(default_factory=list)  # Auto-generated insights

    def to_dict(self) -> dict:
        return {
            "viz_id": self.viz_id,
            "viz_type": self.viz_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "data": self.data,
            "config": self.config,
            "insights": self.insights,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class VisualizationRenderer:
    """
    Renders ConceptGrade analytics into visualization specifications.
    
    Each method produces a VisualizationSpec that can be consumed by
    frontend rendering libraries (D3.js, Plotly, Chart.js).
    """

    @staticmethod
    def blooms_distribution(
        assessments: list,
        title: str = "Bloom's Taxonomy Distribution",
    ) -> VisualizationSpec:
        """Generate Bloom's taxonomy distribution chart."""
        levels = {
            "Remember": {"count": 0, "level": 1, "color": "#ef4444"},
            "Understand": {"count": 0, "level": 2, "color": "#f97316"},
            "Apply": {"count": 0, "level": 3, "color": "#eab308"},
            "Analyze": {"count": 0, "level": 4, "color": "#22c55e"},
            "Evaluate": {"count": 0, "level": 5, "color": "#3b82f6"},
            "Create": {"count": 0, "level": 6, "color": "#8b5cf6"},
        }

        for a in assessments:
            label = a.get("blooms", {}).get("label", "Remember") if isinstance(a, dict) else a.blooms.get("label", "Remember")
            if label in levels:
                levels[label]["count"] += 1

        total = len(assessments) or 1
        bars = []
        for label, info in levels.items():
            bars.append({
                "label": label,
                "level": info["level"],
                "count": info["count"],
                "percentage": round(info["count"] / total * 100, 1),
                "color": info["color"],
            })

        # Generate insights
        insights = []
        max_level = max(bars, key=lambda x: x["count"])
        if max_level["count"] > 0:
            insights.append(
                f"Most students ({max_level['count']}/{total}) are at the "
                f"'{max_level['label']}' level of Bloom's taxonomy."
            )
        high_order = sum(b["count"] for b in bars if b["level"] >= 4)
        if high_order > 0:
            insights.append(
                f"{high_order} student(s) ({round(high_order/total*100)}%) demonstrate "
                f"higher-order thinking (Analyze/Evaluate/Create)."
            )

        return VisualizationSpec(
            viz_id="blooms_dist",
            viz_type="bar_chart",
            title=title,
            subtitle=f"{total} students assessed",
            data={"bars": bars, "x_label": "Bloom's Level", "y_label": "Student Count"},
            config={"orientation": "vertical", "show_percentages": True},
            insights=insights,
        )

    @staticmethod
    def solo_distribution(
        assessments: list,
        title: str = "SOLO Taxonomy Distribution",
    ) -> VisualizationSpec:
        """Generate SOLO taxonomy distribution chart."""
        levels = {
            "Prestructural": {"count": 0, "level": 1, "color": "#ef4444"},
            "Unistructural": {"count": 0, "level": 2, "color": "#f97316"},
            "Multistructural": {"count": 0, "level": 3, "color": "#eab308"},
            "Relational": {"count": 0, "level": 4, "color": "#22c55e"},
            "Extended Abstract": {"count": 0, "level": 5, "color": "#3b82f6"},
        }

        for a in assessments:
            label = a.get("solo", {}).get("label", "Prestructural") if isinstance(a, dict) else a.solo.get("label", "Prestructural")
            if label in levels:
                levels[label]["count"] += 1

        total = len(assessments) or 1
        bars = []
        for label, info in levels.items():
            bars.append({
                "label": label,
                "level": info["level"],
                "count": info["count"],
                "percentage": round(info["count"] / total * 100, 1),
                "color": info["color"],
            })

        insights = []
        relational_plus = sum(b["count"] for b in bars if b["level"] >= 4)
        if relational_plus > 0:
            insights.append(
                f"{relational_plus} student(s) show Relational or Extended Abstract "
                f"understanding, indicating integrated concept knowledge."
            )

        return VisualizationSpec(
            viz_id="solo_dist",
            viz_type="bar_chart",
            title=title,
            subtitle=f"{total} students assessed",
            data={"bars": bars, "x_label": "SOLO Level", "y_label": "Student Count"},
            config={"orientation": "vertical", "show_percentages": True},
            insights=insights,
        )

    @staticmethod
    def misconception_heatmap(
        assessments: list,
        title: str = "Misconception Heatmap",
    ) -> VisualizationSpec:
        """Generate misconception heatmap (concept × severity)."""
        concept_severity = {}  # {concept: {critical: n, moderate: n, minor: n}}

        for a in assessments:
            misc = a.get("misconceptions", {}) if isinstance(a, dict) else a.misconceptions
            for m in misc.get("misconceptions", []):
                src = m.get("source_concept", "unknown")
                tgt = m.get("target_concept", "unknown")
                severity = m.get("severity", "moderate")
                for concept in [src, tgt]:
                    if concept and concept != "unknown" and concept != "":
                        if concept not in concept_severity:
                            concept_severity[concept] = {"critical": 0, "moderate": 0, "minor": 0}
                        if severity in concept_severity[concept]:
                            concept_severity[concept][severity] += 1

        # Build heatmap data
        concepts = sorted(concept_severity.keys())
        severities = ["critical", "moderate", "minor"]

        # Compute per-severity max counts for dynamic normalization so the
        # colour scale stays meaningful regardless of class size.
        max_per_severity = {
            s: max((concept_severity[c].get(s, 0) for c in concepts), default=1)
            for s in severities
        }

        cells = []
        for concept in concepts:
            for severity in severities:
                count = concept_severity[concept].get(severity, 0)
                denom = max_per_severity[severity] or 1
                cells.append({
                    "concept": concept,
                    "severity": severity,
                    "count": count,
                    "intensity": round(count / denom, 4),
                })

        insights = []
        if concept_severity:
            worst = max(concept_severity.items(),
                       key=lambda x: x[1].get("critical", 0) * 3 + x[1].get("moderate", 0))
            insights.append(
                f"'{worst[0]}' has the most misconceptions "
                f"({worst[1].get('critical', 0)} critical, {worst[1].get('moderate', 0)} moderate)."
            )

        return VisualizationSpec(
            viz_id="misconception_heatmap",
            viz_type="heatmap",
            title=title,
            subtitle=f"Across {len(assessments)} students",
            data={
                "cells": cells,
                "x_labels": severities,
                "y_labels": concepts,
                "color_scale": ["#fef2f2", "#fca5a5", "#ef4444", "#991b1b"],
            },
            config={"show_values": True},
            insights=insights,
        )

    @staticmethod
    def concept_coverage_chart(
        assessments: list,
        title: str = "Concept Coverage by Student",
    ) -> VisualizationSpec:
        """Generate concept coverage comparison chart."""
        students = []
        for a in assessments:
            if isinstance(a, dict):
                sid = a.get("student_id", "?")
                concepts = a.get("concept_graph", {}).get("concepts", [])
                coverage = a.get("comparison", {}).get("scores", {}).get("concept_coverage", 0)
                integration = a.get("comparison", {}).get("scores", {}).get("integration_quality", 0)
            else:
                sid = a.student_id
                concepts = a.concept_graph.get("concepts", [])
                coverage = a.comparison.get("scores", {}).get("concept_coverage", 0)
                integration = a.comparison.get("scores", {}).get("integration_quality", 0)

            students.append({
                "student_id": sid,
                "num_concepts": len(concepts),
                "coverage": round(coverage * 100, 1),
                "integration": round(integration * 100, 1),
            })

        return VisualizationSpec(
            viz_id="concept_coverage",
            viz_type="grouped_bar",
            title=title,
            data={
                "students": students,
                "metrics": ["coverage", "integration"],
                "labels": {"coverage": "Concept Coverage %", "integration": "Integration Quality %"},
            },
            config={"show_values": True},
        )

    @staticmethod
    def student_radar(
        assessments: list,
        title: str = "Student Comparison — Multi-Dimensional",
    ) -> VisualizationSpec:
        """Generate radar chart comparing students across dimensions."""
        dimensions = [
            "Bloom's Level", "SOLO Level", "Concept Coverage",
            "Integration Quality", "Accuracy (no misconceptions)",
        ]
        students = []
        for a in assessments:
            if isinstance(a, dict):
                sid = a.get("student_id", "?")
                blooms = a.get("blooms", {}).get("level", 1)
                solo = a.get("solo", {}).get("level", 1)
                coverage = a.get("comparison", {}).get("scores", {}).get("concept_coverage", 0)
                integration = a.get("comparison", {}).get("scores", {}).get("integration_quality", 0)
                accuracy = a.get("misconceptions", {}).get("overall_accuracy", 1.0)
            else:
                sid = a.student_id
                blooms = a.blooms.get("level", 1)
                solo = a.solo.get("level", 1)
                coverage = a.comparison.get("scores", {}).get("concept_coverage", 0)
                integration = a.comparison.get("scores", {}).get("integration_quality", 0)
                accuracy = a.misconceptions.get("overall_accuracy", 1.0)

            students.append({
                "student_id": sid,
                "values": [
                    round(blooms / 6 * 100, 1),     # Normalized to 0-100
                    round(solo / 5 * 100, 1),
                    round(coverage * 100, 1),
                    round(integration * 100, 1),
                    round(accuracy * 100, 1),
                ],
            })

        return VisualizationSpec(
            viz_id="student_radar",
            viz_type="radar",
            title=title,
            data={
                "dimensions": dimensions,
                "students": students,
                "max_value": 100,
            },
            config={"show_labels": True, "fill_opacity": 0.2},
        )

    @staticmethod
    def concept_cooccurrence(
        assessments: list,
        title: str = "Concept Co-occurrence Matrix",
    ) -> VisualizationSpec:
        """Generate concept co-occurrence matrix (which concepts appear together)."""
        cooccurrence = {}
        all_concepts = set()

        for a in assessments:
            cg = a.get("concept_graph", {}) if isinstance(a, dict) else a.concept_graph
            concepts = [
                c.get("concept_id", c.get("id", ""))
                for c in cg.get("concepts", [])
            ]
            all_concepts.update(concepts)
            # Count pairs
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i + 1:]:
                    pair = tuple(sorted([c1, c2]))
                    cooccurrence[pair] = cooccurrence.get(pair, 0) + 1

        # Build matrix
        concept_list = sorted(all_concepts)[:15]  # Limit to top 15
        cells = []
        for c1 in concept_list:
            for c2 in concept_list:
                if c1 == c2:
                    count = sum(1 for a in assessments
                                for c in (a.get("concept_graph", {}) if isinstance(a, dict) else a.concept_graph).get("concepts", [])
                                if c.get("concept_id", c.get("id", "")) == c1)
                else:
                    pair = tuple(sorted([c1, c2]))
                    count = cooccurrence.get(pair, 0)
                cells.append({"concept_a": c1, "concept_b": c2, "count": count})

        return VisualizationSpec(
            viz_id="concept_cooccurrence",
            viz_type="heatmap",
            title=title,
            data={
                "cells": cells,
                "concepts": concept_list,
                "color_scale": ["#f0f9ff", "#93c5fd", "#3b82f6", "#1e3a5f"],
            },
            config={"symmetric": True, "show_values": True},
        )

    @staticmethod
    def class_dashboard(
        analytics,  # ClassAnalytics
        assessments: list,
    ) -> list[VisualizationSpec]:
        """
        Generate a complete class dashboard with multiple visualizations.
        
        Returns a list of VisualizationSpec objects for the full dashboard.
        """
        renderer = VisualizationRenderer()
        dashboard = [
            # 1. Summary card
            VisualizationSpec(
                viz_id="class_summary",
                viz_type="summary_card",
                title="Class Overview",
                data={
                    "num_students": analytics.num_students if hasattr(analytics, 'num_students') else analytics.get("num_students", 0),
                    "avg_score": round((analytics.class_average_score if hasattr(analytics, 'class_average_score') else analytics.get("overall", {}).get("class_average_score", 0)) * 100, 1),
                    "blooms_avg": round(analytics.blooms_average if hasattr(analytics, 'blooms_average') else 0, 1),
                    "solo_avg": round(analytics.solo_average if hasattr(analytics, 'solo_average') else 0, 1),
                    "total_misconceptions": analytics.total_misconceptions if hasattr(analytics, 'total_misconceptions') else 0,
                },
            ),
            # 2. Bloom's distribution
            renderer.blooms_distribution(assessments),
            # 3. SOLO distribution
            renderer.solo_distribution(assessments),
            # 4. Misconception heatmap
            renderer.misconception_heatmap(assessments),
            # 5. Student radar comparison
            renderer.student_radar(assessments),
            # 6. Concept coverage
            renderer.concept_coverage_chart(assessments),
            # 7. Co-occurrence matrix
            renderer.concept_cooccurrence(assessments),
        ]
        return dashboard
