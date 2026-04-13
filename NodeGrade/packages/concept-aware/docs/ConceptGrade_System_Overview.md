# ConceptGrade — Problem Statement and Implementation Plan

**Author:** Brahmaji Katragadda  
**Date:** April 2026  
**Project:** ConceptGrade — A Visual Analytics Dashboard for Knowledge Graph-Grounded Automated Essay Grading

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
   - [The Grading Bottleneck in Large Classes](#11-the-grading-bottleneck-in-large-classes)
   - [The Limits of Existing Automated Grading](#12-the-limits-of-existing-automated-grading)
   - [The Research Gap](#13-the-research-gap)

2. [The Existing Model (Baseline: C_LLM)](#2-the-existing-model-baseline-c_llm)
   - [What C_LLM Does Well](#21-what-c_llm-does-well)
   - [What C_LLM Fails to Provide](#22-what-c_llm-fails-to-provide)

3. [Proposed System and Why](#3-proposed-system-and-why)
   - [What We Are Proposing](#31-what-we-are-proposing)
   - [Why a Knowledge Graph?](#32-why-a-knowledge-graph)
   - [Why a Visual Analytics Dashboard?](#33-why-a-visual-analytics-dashboard)
   - [Why These Changes and Not Others?](#34-why-these-changes-and-not-others)

4. [Implementation Plan](#4-implementation-plan)
   - [Overview](#41-overview)
   - [Phase 1 — Knowledge Graph Quality](#42-phase-1--knowledge-graph-quality)
   - [Phase 2 — Backend API Bridge](#43-phase-2--backend-api-bridge)
   - [Phase 3 — Frontend Dashboard](#44-phase-3--frontend-dashboard)
   - [Phase 4 — User Study Scaffolding](#45-phase-4--user-study-scaffolding)

5. [Key Engineering Decisions and Rationale](#5-key-engineering-decisions-and-rationale)
   - [Async File I/O with In-Memory Cache](#51-async-file-io-with-in-memory-cache)
   - [Race Condition Guard in KG Overlay Fetch](#52-race-condition-guard-in-kg-overlay-fetch)
   - [KG Drag Cursor via Direct DOM Mutation](#53-kg-drag-cursor-via-direct-dom-mutation)
   - [Question-Scoped `is_expected` Flags in KG](#54-question-scoped-is_expected-flags-in-kg)
   - [Edge Weight Averaging in KG Aggregation](#55-edge-weight-averaging-in-kg-aggregation)
   - [Dual-Layer Study Log Storage](#56-dual-layer-study-log-storage)
   - [Persistent XAI Error Chip](#57-persistent-xai-error-chip)

6. [System Architecture (As Built)](#6-system-architecture-as-built)

7. [File Structure](#7-file-structure)

8. [Evaluation Results](#8-evaluation-results)

9. [How to Run](#9-how-to-run)

---

## 1. Problem Statement

### 1.1 The Grading Bottleneck in Large Classes

Grading short-answer questions at scale is genuinely hard. Instructors face two pressures that pull in opposite directions: feedback has to come quickly enough to be pedagogically useful, and it has to be detailed enough to actually help the student understand what they got wrong. In a class of 600, you simply cannot do both. Grading 600 answers at even two minutes each is twenty hours of work — and that is before accounting for the fact that reading the same topic five hundred times makes it increasingly hard to evaluate each answer on its own merits.

In practice, large-class grading degrades to rubric-mechanical marking: the instructor or TA checks for a few key words or phrases, awards partial credit by pattern, and moves on. Students get a number back. They rarely learn which specific concept they misunderstood, and the instructor rarely gets a coherent picture of where the class as a whole went wrong.

### 1.2 The Limits of Existing Automated Grading

Automated short-answer grading has been an active research area since the late 1990s (Burstein et al., Page, Leacock & Chodorow), and the emergence of large language models has pushed numerical performance to genuinely impressive levels. A well-prompted LLM can correlate with human scores at r > 0.97 on standard benchmarks. That sounds like a solved problem. I would argue it is not.

The issue is not accuracy in the aggregate — it is what the system cannot tell you:

**Problem 1 — Opacity.** The output is a number. The model does not report which concepts were present in the answer, which were absent, or what specifically drove the score down. An instructor looking at a score of 2.5 out of 5 has no more diagnostic information than they started with.

**Problem 2 — Sensitivity to surface form.** LLMs grade primarily by matching the student's phrasing against the reference answer. A student who memorises the wording of a model answer without understanding it can score well. Conversely, a student who genuinely understands the material but uses different terminology may score poorly. The model is not actually checking whether the student *understood* the concept, only whether their text *resembles* the reference text.

**Problem 3 — Structural blindness.** Knowledge in a domain has structure — concepts depend on each other. You cannot meaningfully explain backpropagation if you have not understood gradient descent. A flat LLM sees the student answer and the reference answer as bags of tokens. It has no representation of the prerequisite structure of the domain, so it cannot detect that a student's answer is wrong for a specific, diagnosable reason.

**Problem 4 — No interface for the instructor.** Even if the scoring were perfect, a spreadsheet of scores is not a useful tool for instruction. What should I do with this information? Which concept do I need to re-teach? Which students should I invite to office hours, and why? Those are analytical questions, and a number column has no answer for them.

### 1.3 The Research Gap

Much of the AES (Automated Essay/Answer Scoring) literature is focused on pushing accuracy metrics higher. That is a legitimate goal, but it sidesteps a different question: once you have good automated scores, how do you make the results *actionable* for the instructor? How should results be visualised? What interactions should be supported? Does an interactive dashboard actually change what instructors notice and decide? These questions sit at the intersection of visual analytics and educational technology, and the literature on them is comparatively thin. That gap is what this project is trying to address.

---

## 2. The Existing Model (Baseline: C_LLM)

The baseline I am comparing against — which I call **C_LLM** throughout this document — is a direct prompting approach: pass the student answer, the reference answer, and the rubric criteria to Gemini 2.5 Flash and ask it to produce a score. No external knowledge is injected. No structured concept checking is performed. The model draws on its pre-trained representations of the domain and pattern-matches against the reference.

### 2.1 What C_LLM Does Well

On datasets where the rubric is well-specified and the grading task reduces largely to paraphrase matching, C_LLM performs well. On the Mohler 2011 CS dataset (120 answers graded 0–5), it achieves r = 0.971 correlation with human scores and MAE = 0.330. These are competitive numbers. Any system I build has to beat that, and I want to be honest that beating a 0.97 correlation baseline is not easy.

### 2.2 What C_LLM Fails to Provide

The accuracy numbers, though, hide what the system cannot do at all:

- There is no record of which concepts appeared in the student's answer and which did not. Every score is a black box.
- There is no analysis of whether the student demonstrated understanding at the right level of Bloom's taxonomy or SOLO structure — you just get a number.
- There is no prerequisite-chain analysis. If a student scored 2/5, you do not know if it is because they missed one peripheral concept or because they fundamentally misunderstood a foundational one.
- There is no instructor interface. C_LLM is a grading function, not a grading *tool*.

In short, C_LLM answers "What score?" reasonably well. It has nothing to say about "Why?" or "What should I do about it?"

---

## 3. Proposed System and Why

### 3.1 What We Are Proposing

ConceptGrade adds two things on top of C_LLM:

**1. A Knowledge Graph-grounded grading pipeline (C5)**  
A five-stage pipeline that wraps the LLM call with structured concept checking. Before and after calling the LLM, the system consults a per-question Knowledge Graph that encodes the important concepts in the topic and how they relate to each other. The pipeline grades not just by matching the answer text against the reference, but by verifying whether the student's answer demonstrates the right concepts and their prerequisite structure.

**2. An interactive Visual Analytics dashboard for instructors**  
A multi-panel dashboard that presents the per-class grading results as linked interactive visualisations. Instructors can see which concepts the class is struggling with, click into individual student answers, see a plain-language explanation of why a particular score was assigned, and explore the concept neighbourhood using an interactive knowledge graph diagram. The two study conditions (with charts / without charts) allow us to measure whether the visual tools actually change what instructors notice and decide.

### 3.2 Why a Knowledge Graph?

The KG is what allows us to move from surface matching to structured concept verification. Concretely:

- **Addressing opacity:** Every concept in the domain gets a named node in the graph. The pipeline records which nodes the student's answer touched — so the output is not just a score, it is a concept fingerprint. The instructor can see *exactly* what was matched and what was missed.

- **Addressing surface-form sensitivity:** Rather than comparing the student text directly against the reference text, the pipeline extracts concept mentions from the student answer using the LLM, then checks those mentions against the KG. Two different phrasings of the same underlying concept map to the same graph node. The check is conceptual, not lexical.

- **Addressing structural blindness:** The KG encodes prerequisite edges (e.g., gradient descent → backpropagation). The pipeline computes a *chain coverage score* — what fraction of the prerequisite path to the target concept the student actually demonstrated. A student who names the right answer concept but shows no evidence of understanding its foundations gets a lower chain score, even if surface matching would have rewarded them.

### 3.3 Why a Visual Analytics Dashboard?

There is a well-established argument in information visualisation that for complex exploratory tasks, interactive visual tools outperform summary statistics alone (Tufte, Card et al., Shneiderman). In the context of grading, the instructor's task is inherently exploratory: they do not know in advance which students are struggling or why. They need to move between class-level patterns and individual cases, and they need to be able to verify automated judgements rather than just accepting them.

The specific design choices I made are:

- **Overview-first layout** following Shneiderman's mantra: summary metric cards and distribution charts at the top, individual student data behind a click.
- **Coordinated Multiple Views (CMV):** Clicking a concept in the heatmap filters the student list; clicking a student recolours the knowledge graph. This kind of linking lets the instructor maintain context as they drill down, rather than having to mentally hold multiple unconnected views in mind simultaneously.
- **XAI provenance in the table:** Each row in the score table can be expanded to show which concepts the student matched (green chips) and missed (red chips), with a plain-language causal explanation. This is the mechanism by which the instructor can actually audit the automated grade rather than just accepting it.
- **Two study conditions:** The same codebase gates all the charts behind a URL parameter (`?condition=A` for numbers only, `?condition=B` for the full dashboard). This makes it straightforward to run a controlled study comparing what instructors can and cannot figure out with and without the visual tools.

### 3.4 Why These Changes and Not Others?

Some alternatives I considered and ruled out:

| Alternative | Why I Did Not Pursue It |
|-------------|------------------------|
| Better prompting of C_LLM only | Accuracy is already near ceiling; still black-box; no instructor interface |
| KG pipeline without a dashboard | Does not answer the interface question; not a VIS paper |
| Graph neural network for grading | Requires large labelled sets per course; not generalisable to new domains |
| Static PDF report rather than interactive tool | Cannot support linking, filtering, or the study design |
| Using Canvas or existing LMS analytics | Existing tools track engagement (logins, clicks), not conceptual understanding |

---

## 4. Implementation Plan

### 4.1 Overview

The implementation has four phases with a hard dependency chain:

```
Phase 1: KG Quality  →  Phase 2: Backend API  →  Phase 3: Frontend  →  Phase 4: Study
```

I dropped the originally planned Phase 2 (new dataset collection). Three datasets give enough statistical power for the VIS submission, and the time is better spent on the dashboard and study design.

### 4.2 Phase 1 — Knowledge Graph Quality

**File:** `packages/concept-aware/generate_auto_kg_prompt.py`

The KGs are built by prompting Gemini to extract concepts and relationships from each exam question. Two categories of noise show up in the raw output reliably enough that they needed to be handled systematically:

**Noise type 1 — Generic concept nodes.** The LLM occasionally extracts words like "process", "method", or "step" as concept nodes. These are not domain-specific and will match almost any student answer, producing spurious hits.

**Noise type 2 — Non-canonical relationship types.** The schema defines 15 valid relationship types. The LLM sometimes returns variants — LEADS_TO instead of PRODUCES, ENABLES instead of PREREQUISITE_FOR — that are semantically equivalent but will not match downstream string comparisons.

**Fixes:**

| Fix | Implementation |
|-----|---------------|
| Remove generic concepts | `GENERIC_CONCEPT_STOPLIST` (30 terms); nodes in the list are pruned before saving |
| Remap relationship variants | `REL_TYPE_REMAP` dict (15 entries); types not in the dict and not already valid are dropped with a logged warning |
| Flag thin KGs | Questions with fewer than 4 surviving concepts are marked `_needs_retry: True` |
| Retry pass | A separate prompt prefix is sent for marked questions asking for richer concept extraction |

New CLI flags added:
```
--process-response PATH   Path to raw Gemini JSON to clean and save
--max-retries INT         How many retry passes to run (default: 1)
```

### 4.3 Phase 2 — Backend API Bridge

The Python pipeline saves results as JSON files. The React dashboard cannot read files from disk directly — it needs an HTTP API. A new NestJS module bridges the gap.

**New directory:** `packages/backend/src/visualization/`

#### Data Types (`visualization.types.ts`)

```typescript
export interface VisualizationSpec {
  viz_id: string
  viz_type: 'bar_chart' | 'heatmap' | 'grouped_bar' | 'radar' | 'table' | 'summary_card' | 'concept_map'
  title: string
  subtitle: string
  data: Record<string, unknown>
  config: Record<string, unknown>
  insights: string[]
}

export interface DatasetSummaryResponse {
  dataset: string
  n: number
  metrics: { C_LLM: DatasetMetrics; C5_fix: DatasetMetrics }
  wilcoxon_p: number
  mae_reduction_pct: number
  visualizations: VisualizationSpec[]
}
```

#### Service (`visualization.service.ts`)

| Method | Purpose |
|--------|---------|
| `listDatasets()` | Scans data directory; validates each file has per-sample scores (skips old ablation files) |
| `getDatasetVisualization(dataset)` | Loads a file and produces a full `DatasetSummaryResponse` with 7 visualisation specs |
| `adaptToVisualizationSpecs()` | Groups, buckets, and aggregates the flat sample array into chart-ready structures |
| `loadJson()` | Async read with lazy in-memory cache — avoids re-reading unchanged files on every request |

Visualisation spec transformations:

| viz_id | viz_type | What it computes |
|--------|----------|-----------------|
| `blooms_dist` | `bar_chart` | Group by Bloom's label, count per level, Bloom palette colours |
| `solo_dist` | `bar_chart` | Group by SOLO label, count per level, SOLO palette colours |
| `score_comparison` | `grouped_bar` | Bucket by human score range; compute C_LLM and C5 MAE per bucket |
| `concept_frequency` | `bar_chart` | Flatten all matched_concepts arrays; count occurrences; top 15 |
| `class_summary` | `summary_card` | n, avg C5 score, avg Bloom level, mae_reduction_pct, wilcoxon_p |
| `chain_coverage_dist` | `bar_chart` | Parse chain_pct to int; bucket into 5 × 20-point ranges |
| `score_scatter` | `table` | Raw per-sample: id, human_score, cllm_score, c5_score, solo, bloom, chain_pct |

**Security note:** Every `:dataset` URL parameter passes through `path.basename()` before reaching the filesystem. This strips directory components — so `/api/visualization/datasets/../../etc/passwd` cannot escape the data directory.

#### REST Endpoints (`visualization.controller.ts`)

```
GET /api/visualization/datasets                        → { datasets: string[] }
GET /api/visualization/datasets/:dataset               → DatasetSummaryResponse
GET /api/visualization/datasets/:dataset/specs         → { specs: VisualizationSpec[] }
GET /api/visualization/datasets/:dataset/concept/:id   → ConceptAnswersResponse
GET /api/visualization/datasets/:dataset/kg/:id        → KGSubgraphResponse
GET /api/visualization/datasets/:dataset/sample/:id    → SampleXAIData
GET /api/visualization                                 → { datasets: DatasetSummaryResponse[] }
```

`VisualizationModule` is registered in `AppModule`'s `imports` array.

### 4.4 Phase 3 — Frontend Dashboard

#### Shared Types and Logger

`packages/frontend/src/common/visualization.types.ts` mirrors the backend interfaces so the frontend gets compile-time checking on API responses.

`packages/frontend/src/utils/studyLogger.ts` handles event recording. Every event goes to `localStorage['ng-study-log']` immediately, and also gets POSTed to `POST /api/study/log` as a server-side backup.

#### Chart Components (`packages/frontend/src/components/charts/`)

| Component | What it shows | Library |
|-----------|--------------|---------|
| `BloomsBarChart.tsx` | Bloom's level distribution | Recharts `BarChart` + `Cell` (per-bar colour) |
| `SoloBarChart.tsx` | SOLO level distribution | Same pattern |
| `ConceptFrequencyChart.tsx` | Top 15 most-missed concepts | `BarChart layout="vertical"`, left margin 120px |
| `ScoreComparisonChart.tsx` | C_LLM vs C5 MAE per score bucket | `BarChart` with 2 `Bar` elements |
| `ChainCoverageChart.tsx` | Prerequisite chain completion distribution | Green gradient bars |
| `MisconceptionHeatmap.tsx` | Concept × severity grid | MUI `Grid` of coloured `Box` cells |
| `StudentRadarChart.tsx` | Per-student cognitive profile | Recharts `RadarChart` with quartile chips |
| `StudentAnswerPanel.tsx` | Filtered student list + answer detail | MUI master-detail layout |
| `ConceptKGPanel.tsx` | Ego-graph with drag and student overlay | SVG rendered by React |
| `ScoreSamplesTable.tsx` | Per-row XAI expansion with concept chips | MUI `Table` with expandable rows |
| `CrossDatasetComparisonChart.tsx` | C_LLM vs C5 across all 3 datasets | Custom SVG slopegraph |

#### Shared State (`packages/frontend/src/contexts/DashboardContext.tsx`)

All interactive selections live in a single React context managed by `useReducer`. Named action types (`SELECT_CONCEPT`, `SELECT_STUDENT`, `SELECT_QUARTILE`, `SET_LOADING`, `SET_ERROR`, `CLEAR_ALL`) make state transitions explicit — every selection change dispatches a named action rather than directly modifying state variables.

State fields:

| Field | What it tracks |
|-------|---------------|
| `selectedConcept` | Concept clicked in the heatmap |
| `selectedSeverity` | Severity column clicked |
| `selectedStudentId` | Currently selected student |
| `selectedStudentMatchedConcepts` | Concept IDs that student covered (from XAI fetch) |
| `studentOverlayLoading` | Whether the KG overlay fetch is in progress |
| `studentOverlayError` | Whether the last KG overlay fetch failed |
| `selectedQuartileIndex` | Active radar quartile filter |

#### Dashboard Layout (`packages/frontend/src/pages/InstructorDashboard.tsx`)

```
Header: title + dataset tabs + refresh
Study Task Panel  (only when ?condition= is in URL)
─────────────────────────────────────────
Summary cards: N | C5 MAE | Baseline MAE | Reduction % | p-value
Insight alerts
─────────────────────────────────────────
[Condition B only — everything below]
Cross-Dataset Slopegraph
Bloom's bar   |  SOLO bar
Score Comparison  |  Chain Coverage
Concept Frequency (full width)
Score Samples Table with XAI rows
Radar   |  Misconception Heatmap
Student Answer Panel + KG Panel (when a concept is selected)
─────────────────────────────────────────
Export Study Log  (study mode only)
```

Route added to `App.tsx`: `<Route path="dashboard" element={<InstructorDashboard />} />`

### 4.5 Phase 4 — User Study Scaffolding

Condition gating is a URL parameter check at the top of the dashboard component:

```typescript
const condition = searchParams.get('condition') ?? 'B'
// condition=A: summary cards only
// condition=B: full dashboard
```

When `?condition=` is present, a task panel appears asking: *"Looking at the data for this class, which concept do students struggle with most? Which students would you prioritise for office hours, and why?"* The instructor types a response, rates their confidence on a 1–5 slider, and submits. Time from first keystroke to submission is recorded.

Events logged:

| Event | Trigger | Payload |
|-------|---------|---------|
| `page_view` | Dashboard mount | `{ session_id, is_study }` |
| `tab_change` | Dataset tab switch | `{ dataset }` |
| `task_start` | First focus on answer textarea | `{}` |
| `task_submit` | Submit click | `{ answer, confidence, time_to_answer_ms }` |
| `chart_hover` | Mouse enter on any chart | `{ viz_id }` |

The Export button downloads the localStorage log as `study-log-{session_prefix}.json`.

---

## 5. Key Engineering Decisions and Rationale

### 5.1 Async File I/O with In-Memory Cache

**What happened:** The original backend read dataset files synchronously. Node.js has a single-threaded event loop, so a synchronous file read blocks the server from doing anything else until the read completes. For a single user this is tolerable; for a user study with multiple participants hitting the same server simultaneously it would cause visible stalls.

**Fix:** All reads use `fs.promises.readFile`. Results go into a `Map<string, unknown>` keyed by absolute path. Subsequent requests for the same dataset are served from the map without touching disk.

### 5.2 Race Condition Guard in KG Overlay Fetch

**What happened:** When an instructor clicks through students quickly, several fetch requests go out concurrently. If response N+1 arrives before response N (which is possible under any real network latency), the wrong student's concept data gets applied to the KG panel.

**Fix:** A `latestSelectedIdRef` ref is updated synchronously on every student click. When a fetch result arrives, it is only applied if the student ID in the response still matches the ref. Stale results are discarded silently. A ref rather than state is used so the guard is in place before any re-render fires.

### 5.3 KG Drag Cursor via Direct DOM Mutation

**What happened:** The KG panel lets instructors drag nodes to rearrange the layout. The drag state was stored in a React ref (correct for a high-frequency operation that should not cause re-renders), but because changing a ref does not trigger a render, the cursor style never visually updated during the drag.

**Fix:** `svgRef.current.style.cursor = 'grabbing'` is set directly in the `mousedown` handler, and reset to `'grab'` in `mouseup`. This bypasses React's render cycle. For a cursor change that needs to happen at mouse-down latency, direct DOM mutation is the right tool.

### 5.4 Question-Scoped `is_expected` Flags in KG

**What happened:** Initially, a KG node was marked as expected (shown red if the student missed it) if it appeared in the expected concepts for *any* question in the dataset. This was wrong — a node should only be red if it was expected for the *specific question the student answered*. The earlier logic was producing false red nodes for students who never had to demonstrate those concepts at all.

**Fix:** The KG endpoint accepts an optional `?questionId=` parameter. When present, the `is_expected` flag is set only for concepts that appear in that question's expected list. This is the pedagogically correct definition and makes the red/green encoding trustworthy.

### 5.5 Edge Weight Averaging in KG Aggregation

**What happened:** The same conceptual relationship can appear in multiple questions with slightly different weights. The original aggregation code kept the first occurrence and discarded the rest — so the edge weight in the final graph reflected whichever question happened to be processed first.

**Fix:** Weights are accumulated and then divided by the number of occurrences. The final weight is an average across all questions where that edge appears, which is a more stable and semantically meaningful signal.

### 5.6 Dual-Layer Study Log Storage

**What happened:** The initial design wrote study events only to `localStorage`. If a participant closed the browser tab before the facilitator could export the log, the data was lost.

**Fix:** Every event is also POSTed to `POST /api/study/log` as a background fire-and-forget request. The backend appends the event to a per-session JSONL file at `data/study_logs/{session_id}.jsonl`. The browser export is still the primary mechanism, but the server copy means data is not lost on browser close.

### 5.7 Persistent XAI Error Chip

**What happened:** When the KG overlay fetch fails (e.g., the backend is under load), the instructor needs to know the node colours are stale. An early version used a timed toast notification that disappeared after a few seconds. In think-aloud study sessions, that notification fires while the participant is in the middle of explaining their reasoning — it disappears before the facilitator can note it, and it interrupts the verbal flow.

**Fix:** A persistent amber chip (`⚠ overlay unavailable`) is shown in the KG panel header. It stays until the instructor selects a different student or concept. Persistent means it is readable in a session recording even if the facilitator did not notice it in real time.

---

## 6. System Architecture (As Built)

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Python Pipeline  (packages/concept-aware/)            │
│                                                                 │
│  CSV answers + exam questions                                   │
│  → generate_auto_kg_prompt.py   → per-question KG JSON         │
│  → evaluator.py (5-stage C5)    → eval_results.json            │
│  → generate_dashboard_extras.py → heatmap / radar extras JSON  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ JSON files on disk
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 2: NestJS Backend API  (packages/backend/src/)           │
│                                                                 │
│  GET  /api/visualization/datasets         list datasets         │
│  GET  /api/visualization/datasets/:ds     full dashboard spec   │
│  GET  /api/visualization/datasets/:ds/concept/:id               │
│  GET  /api/visualization/datasets/:ds/kg/:id                    │
│  GET  /api/visualization/datasets/:ds/sample/:id                │
│  POST /api/study/log                      append event          │
│  GET  /api/study/health                   liveness probe        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP REST (port 5001)
┌──────────────────────────▼──────────────────────────────────────┐
│  LAYER 3: React Frontend  (packages/frontend/src/)              │
│                                                                 │
│  DashboardContext (useReducer)  — shared selection state        │
│  InstructorDashboard            — layout + condition gating     │
│  MisconceptionHeatmap → StudentAnswerPanel → ConceptKGPanel     │
│  StudentRadarChart (quartile filter)                            │
│  ScoreSamplesTable → ConceptKGPanel (XAI overlay)              │
│  BloomsBarChart, SoloBarChart, ScoreComparisonChart, etc.       │
│  studyLogger.ts  — localStorage + server backup                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. File Structure

```
packages/
├── concept-aware/
│   ├── data/
│   │   ├── digiklausur_eval_results.json
│   │   ├── kaggle_asag_eval_results.json
│   │   ├── digiklausur_dashboard_extras.json
│   │   ├── kaggle_asag_dashboard_extras.json
│   │   └── study_logs/              per-session .jsonl files
│   ├── generate_auto_kg_prompt.py   KG generation + cleaning
│   ├── generate_dashboard_extras.py heatmap + radar pre-computation
│   └── evaluator.py                 5-stage C5 grading pipeline
│
├── backend/src/
│   ├── visualization/
│   │   ├── visualization.controller.ts
│   │   ├── visualization.service.ts
│   │   ├── visualization.types.ts
│   │   └── visualization.module.ts
│   └── study/
│       ├── study.controller.ts
│       └── study.service.ts
│
└── frontend/src/
    ├── contexts/DashboardContext.tsx
    ├── components/charts/
    │   ├── BloomsBarChart.tsx
    │   ├── SoloBarChart.tsx
    │   ├── ConceptFrequencyChart.tsx
    │   ├── ScoreComparisonChart.tsx
    │   ├── ChainCoverageChart.tsx
    │   ├── MisconceptionHeatmap.tsx
    │   ├── StudentRadarChart.tsx
    │   ├── StudentAnswerPanel.tsx
    │   ├── ConceptKGPanel.tsx
    │   ├── ScoreSamplesTable.tsx
    │   ├── CrossDatasetComparisonChart.tsx
    │   └── index.ts
    ├── pages/InstructorDashboard.tsx
    ├── common/visualization.types.ts
    └── utils/studyLogger.ts
```

---

## 8. Evaluation Results

Tested across three datasets, 1,239 answers in total:

| Dataset | Domain | N | C_LLM MAE | C5 MAE | Reduction | Wilcoxon p |
|---------|--------|---|-----------|--------|-----------|------------|
| Mohler 2011 | Computer Science | 120 | 0.330 | 0.223 | **32.4%** | 0.0013 |
| DigiKlausur | Neural Networks | 646 | 0.394 | 0.296 | **24.9%** | 0.049 |
| Kaggle ASAG | Elementary Science | 473 | 0.244 | 0.252 | −3.3% (n.s.) | 0.148 |

Combined across all three (Fisher's method): p = 0.0014.

The pattern makes sense: the KG helps most in technical domains where the vocabulary is specialised and the concept dependencies are tight. Elementary science answers use everyday language that the LLM handles well without any additional structure, so the KG adds noise rather than signal there.

---

## 9. How to Run

**Prerequisites:** Node.js 18+, Python 3.12, Yarn 4+

**Build and start the backend:**
```bash
cd packages/backend
yarn build
node dist/src/main.js
# API at http://localhost:5001
```

**Start the frontend dev server:**
```bash
cd packages/frontend
yarn dev
# Dashboard at http://localhost:5173
```

**Dashboard URLs:**

| URL | What you get |
|-----|-------------|
| `/dashboard` | Full dashboard (Condition B by default) |
| `/dashboard?condition=A` | Control — summary cards only, no charts |
| `/dashboard?condition=B` | Treatment — full dashboard + study task panel |

**Quick API check:**
```bash
curl http://localhost:5001/api/visualization/datasets
# → {"datasets":["digiklausur","kaggle_asag"]}
```
