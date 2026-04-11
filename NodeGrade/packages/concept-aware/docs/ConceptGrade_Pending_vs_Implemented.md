# ConceptGrade — Implemented vs Pending

**Last updated:** 2026-04-08  
**Purpose:** One place to distinguish what is **shipped in this repo**, what is **partial or placeholder**, and what remains **research / paper / ops** work.  
**Related:** [ConceptGrade_Dashboard_Implementation.md](./ConceptGrade_Dashboard_Implementation.md) (build + run) · [AGENT_HANDOFF.md](../AGENT_HANDOFF.md) (research checklist §6–§7) · [ConceptGrade_Dashboard_Manual_Test_Guide.md](./ConceptGrade_Dashboard_Manual_Test_Guide.md) (QA)

---

## 1. Instructor dashboard and visualization API

| Area | Status | Notes |
|------|--------|--------|
| NestJS `GET /api/visualization/datasets` | **Implemented** | Lists slugs derived from compatible `*_eval_results.json` files (non-empty `results[]` with required score fields). Aggregate-only files (e.g. offline ablations) are omitted. |
| NestJS `GET /api/visualization/datasets/:dataset` (+ `specs`) | **Implemented** | Returns **9** visualization specs per dataset with fixed `viz_id` contract. |
| Python `verify_visualization_api.py` / `npm run verify:visualization` | **Implemented** | CI-style check for dataset list + 9 specs per dataset. |
| Frontend `/dashboard` | **Implemented** | Dataset tabs, summary metrics, insights alerts, refresh. |
| Charts driven from eval JSON | **Implemented** | `class_summary`, `blooms_dist`, `solo_dist`, `score_comparison`, `concept_frequency`, `chain_coverage_dist`, `score_scatter` (table). |
| Study conditions `?condition=A` / `?condition=B` | **Implemented** | A: metrics without full chart grid. B: full analytics + study task panel. |
| Study logger + export JSON | **Implemented** | `localStorage` session log; download button. |
| `student_radar` | **Partial** | API + `StudentRadarChart` render; **data** is placeholder (`dimensions` / `students` empty) until the pipeline exports real structures. |
| `misconception_heatmap` | **Partial** | API + `MisconceptionHeatmap` render; **data** is placeholder (`cells` empty) until the pipeline exports real structures. |
| Optional Mohler (or other) tab | **Data-dependent** | Appears only if a matching `*_eval_results.json` exists in `packages/concept-aware/data/` with the required per-sample schema—not a code TODO. |
| Fourth benchmark dataset (Phase 2) | **Explicitly skipped** | Documented in the implementation guide; effort redirected to dashboard and study. |
| “API unreachable” red `Alert` (TC-UI-008) | **Implemented in code** | Full **visual** confirmation needs stopping Nest locally; remote sandboxes often mark this **CONDITIONAL** (404 JSON can still be checked). |

---

## 2. Research, scoring pipeline, and paper (Python `packages/concept-aware`)

This work lives mostly outside the React/Nest dashboard. **Authoritative detail:** [AGENT_HANDOFF.md](../AGENT_HANDOFF.md) — **§6 What Is DONE**, **§7 What Is PENDING**, **§8 Known Issues**.

**Implemented (high level):** cached batch scoring, multi-dataset evals (Mohler, DigiKlausur, Kaggle ASAG), ablations, paper report generators, KG prompt tooling, etc. (see handoff §6).

**Pending (high level — not an exhaustive list):**

- Stronger **Kaggle ASAG** behavior (e.g. semantic concept matching, coverage thresholds); re-score after changes.  
- **Extension ablation** in **LLM mode** (vs heuristic-only artifact in `extension_ablation_results.json`).  
- **Paper narrative** for multi-dataset generalization (why some datasets do not show KG lift).  
- **DigiKlausur** metric fairness (optional discrete-score snapping in `score_batch_results.py`).  
- **Full educator user study** (recruitment, IRB if required, A/B sessions beyond scaffolding).  
- **VIS submission** (calendar-driven).

---

## 3. Other docs that may look “out of date”

| Document | Issue | Resolution |
|----------|--------|------------|
| [ConceptGrade_Implementation_Report.md](./ConceptGrade_Implementation_Report.md) §4 | States “Full dashboard / V-NLI UI … out of scope” for an **older** benchmark-focused scope. | **Superseded for NodeGrade** by the dashboard described in [ConceptGrade_Dashboard_Implementation.md](./ConceptGrade_Dashboard_Implementation.md). |

When this status file and the handoff diverge, prefer **editing AGENT_HANDOFF §6–§8** for research items and **ConceptGrade_Dashboard_Implementation.md** for dashboard/API details; update the summary tables here only when you want a single entry point for stakeholders.
