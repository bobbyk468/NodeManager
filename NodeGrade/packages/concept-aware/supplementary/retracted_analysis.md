# Retracted Analysis — Historical Record (Supplementary Materials)

*Moved out of the main submission on 2026-08-17 as part of
preparing the manuscript for submission. This file preserves, verbatim and
unmodified, all material computed on the retracted fabricated 120-sample/
10-question Mohler fixture (see `REPRODUCIBILITY.md` for the full incident
record: what was fabricated, how it was discovered, and what was
corrected). None of the numbers, tables, or figures below should be cited
as evidence — they are retained only so the experimental-design record
remains inspectable, consistent with this project's retract-don't-delete
policy.*

*The main paper (`paper/main.tex`) contains a one-sentence pointer to this
file at each point where this material used to appear inline.*

---

## Block 1 — "Dataset and Evaluation Protocol" (originally Experimental
Setup subsection of the full draft)

This subsection, in its entirety, described the retracted fabricated
120-sample/10-question fixture rather than the real evaluation protocol.
The real dataset and protocol (46 real questions, 1,262 real responses,
`nkazi/MohlerASAG`) are described in the main paper's Results section.
Note: the closing "Comparability note" paragraph in this block (about
published Mohler 2011/Sultan 2016 baselines using the full 630-sample
dataset with different splits) is a generic external-comparability caveat,
not itself about the fabrication — it may be worth re-adding to the main
paper's Baselines or Related Work discussion separately if that caveat is
still needed there.

```latex
\subsection{Dataset and Evaluation Protocol: Retracted Fabricated-Data Methodology (2026-07-28)}
\label{subsec:dataset_protocol}

\textbf{Correction.} This subsection describes the retracted fabricated
120-sample/10-question fixture (see REPRODUCIBILITY.md), not the real
dataset this paper's results are computed on; none of its statistics
(the $n=30$/$n=90$ split, the $10$-question LOOCV claim, the $32.4\%$
MAE figure, the tie decomposition) describe the actual evaluation. The
real dataset and protocol are in \S\ref{sec:results}: the real,
KG-aligned Mohler subset has $46$ questions and $1{,}262$ responses
(variably $24$--$31$ per question), sourced from
\texttt{nkazi/MohlerASAG}, evaluated as one full sample with no
held-out split. We retain this subsection unmodified for the
experimental-design record only; cite \S\ref{sec:results} and
\S\ref{subsec:crossdataset_sig} instead.

We evaluate on the Mohler et al.\ (2011) CS short answer grading benchmark
\cite{mohler2011}, which despite its age remains the de-facto standard
CS-domain ASAG benchmark with rich KG-alignable concepts; contemporary
alternatives (SemEval-2013 BEETLE \cite{dzikovska2013}, ASAP-SAS) cover
physics tutoring or essay-style answers and lack the data-structures
concept-graph alignment our pipeline requires. We extend the analysis to
two additional datasets (DigiKlausur \cite{kishaan2020digiklausur}, Kaggle ASAG) in
\S\ref{subsec:crossdataset_sig} to characterise boundary behaviour
outside the in-domain regime. The full benchmark contains 630 responses across 87 questions;
we focus on the KG-aligned subset of 120 responses spanning 10 questions on
Data Structures topics (linked lists, arrays, stacks, binary search trees, BFS/DFS,
hash tables)---topics for which our expert KG provides complete coverage; the
embedded dataset module (\texttt{datasets/mohler\_loader.py}) records 12
responses per question. Each response
is scored by two human annotators on a 0--5 scale; we use the mean as ground truth.

\textbf{Scope of evaluation (selection note).} The 120-sample KG-aligned subset
constitutes 19\% of the full Mohler benchmark. This subset was selected
\emph{a priori} based on KG coverage---not based on observed system
performance---and the selection criteria (Data Structures topics with complete
KG coverage) were fixed before any predictions were generated. Nevertheless,
the resulting evaluation tests ConceptGrade under \emph{favorable conditions}
where the KG provides full conceptual coverage; performance on Mohler questions
outside the KG-aligned subset is, by construction, undefined for our method and
is not reported. We therefore frame all Mohler results as ``performance under
KG-aligned conditions'' rather than as full-benchmark performance, and we
cross-validate generalization on two independent datasets (DigiKlausur,
Kaggle ASAG; Paper~2, Section~A.3) where the KG-domain match varies from
high (NN) to low (elementary science) specificity.

\textbf{Partition protocol.} The 120 samples are partitioned into a \emph{development
set} ($n = 30$, 25\%) and a \emph{test set} ($n = 90$, 75\%), stratified by question
to preserve score distribution \emph{and to ensure that each question contributes
the same proportional split} (so that no question is exclusively in dev or test).
This partition is fixed before all experiments:
the development set is used exclusively for hyperparameter tuning (ensemble weights,
confidence threshold) and the test set is held out for all reported results.
No sample appears in both partitions.

\textbf{This is a response-level held-out split, not a question-level
held-out split, and the two support different claims.} Because every one
of the 10 questions contributes responses to both the development and test
partitions, the tuned synthesis weights and confidence threshold could in
principle exploit question-specific score distributions, rubric phrasing,
and KG-coverage patterns that are shared between the two partitions. The
$n=90$ test-split result therefore demonstrates generalization to
\emph{new student responses on already-seen questions} (interpolation
within a known question set), not generalization to \emph{novel,
previously-unseen questions}. The leave-one-question-out (LOOCV) analysis
reported below (\S\ref{subsec:significance}) is a sensitivity check on
whether the \emph{significance test} is fragile to any single question's
contribution --- it does not retune the synthesis weights per fold and
therefore does not constitute a question-held-out cross-validation of the
\emph{model}. No experiment in this paper currently tests whether the
tuned weights generalize to a genuinely unseen question; this requires a
proper $k$-fold question-level cross-validation (tune on 9 questions,
evaluate on the 10th, repeated 10 ways) and is explicit future work
(\S\ref{sec:limitations}).

\textbf{Sample-size rationale.} The 120 samples ($10$ questions $\times$ $12$
responses per question) reflect the maximal subset for which our expert KG
provides complete topical coverage; we did not subsample. With the observed
paired effect size ($d_z \approx 0.30$ on response-level absolute errors), the
full sample ($n = 120$) achieves post-hoc power $\approx 0.94$ at $\alpha = 0.05$
(one-tailed) for the primary Wilcoxon test, computed via the normal-approximation
formula $\Phi\bigl(|d_z|\sqrt{n} - z_{1-\alpha}\bigr)$.

\textbf{Sample independence and clustering.} The 120 responses are clustered
within $10$ questions ($12$ responses per question); within-question responses
share prompt text, reference rubric, and topic, and are therefore not strictly
independent. Our primary Wilcoxon signed-rank test pairs each response with
itself across methods (a within-sample pairing that is valid under clustering),
but the between-sample independence assumption is partially violated. We
therefore report three additional sensitivity analyses.

\emph{(i) Question-level clustered Wilcoxon.} Aggregating the $12$
response-level absolute errors per question to question-level means yields
a paired Wilcoxon signed-rank test on $n = 10$ questions of
$p_{\text{cluster}} = 0.0244$ (one-tailed) / $0.0488$ (two-tailed),
preserving the directional conclusion.

\emph{(ii) Leave-one-question-out (LOOCV) on the clustered test.} Re-running
the question-level Wilcoxon while removing each of the 10 questions in turn
(LOOCV) produces one-tailed $p$ values in $[0.0039,\,0.0488]$ and two-tailed
$p$ values in $[0.0078,\,0.0977]$. \textbf{All 10 LOOCV folds remain
significant at one-tailed $\alpha = 0.05$;} only 1 of 10 folds clears
significance at two-tailed $\alpha = 0.05$. We interpret this honestly:
the directional claim (ConceptGrade has lower per-question paired error than
the LLM baseline) is robust to any single question being removed, but the
strict two-tailed clustered claim is sensitive to which question contributes
the largest effect, as expected at $n = 10$ clusters.

\emph{(iii) Tie decomposition (not outcome-conditioned subset).} The two
methods produce identical predictions on $70$ of the $120$ paired samples.
We do not present the non-tied numbers as a post-hoc subset analysis (which
would be outcome-conditioning); we present them as a deterministic
decomposition of the full-sample effect, since the full-sample MAE
reduction is a fixed weighted average of (a) the $70$-sample tied
component (MAE reduction $= 0\%$ by construction) and (b) the $50$-sample
non-tied component. On the non-tied component, the MAE reduction is
\textbf{50.7\%} (C\_LLM $0.507$ vs.\ C5\_fix $0.250$), paired Cohen's
$d_z = 0.48$\footnote{Throughout, $d_z$ denotes paired Cohen's $d_z$
(mean paired difference divided by SD of paired differences). Cohen's
classical small/medium/large benchmarks (0.2/0.5/0.8) were defined for
unpaired $d$ and apply to $d_z$ only after the conversion
$d_{\text{unpaired-equivalent}} \approx d_z \sqrt{2/(1-\rho)}$ for
paired-error correlation $\rho$. For typical grading correlations
$\rho \in [0.4, 0.6]$, our $d_z = 0.30$ on full Mohler corresponds to
unpaired-equivalent $d \approx 0.55$--$0.67$ (medium), and the non-tied
$d_z = 0.48$ corresponds to unpaired-equivalent $d \approx 0.88$--$1.07$
(large). We report $d_z$ directly throughout to avoid an unverifiable
$\rho$ assumption; the unpaired-equivalent magnitudes are given only for
Cohen-rule readers.} (medium effect), and the Wilcoxon $p$ is essentially
unchanged ($p = 0.0026$ two-tailed / $0.0013$ one-tailed). The
identity $0.324 = (70 \times 0 + 50 \times 0.507) / 120$ confirms this is
arithmetic decomposition, not subset selection. The 50-sample non-tied
component is itself significant at $p_{\text{one}} = 0.0013$, so an
adversarial reframing of the result as "effective $n = 50$" leaves the
directional inference intact rather than undermining it. \textbf{Tie
composition (anti-cheating disclosure):} Of the $70$ tied samples,
$31$ have both predictions \emph{exactly correct} (zero error each) and
$39$ have both predictions wrong by the \emph{same} amount; in the
latter category the absolute error is small ($37$ samples at
$|\text{err}| = 0.5$, $2$ samples at $1.0$, and \emph{zero} samples at
$|\text{err}| > 1.0$). The mean absolute error on tied samples is $0.204$,
versus $0.507$ (C\_LLM) and $0.250$ (C5\_fix) on non-tied samples. The
``ties'' are therefore not pathological samples where both methods fail
catastrophically by identical large amounts; they are mostly easy
correctness or mild small-error agreement. We treat the
full-sample $32.4\%$ as the primary number and the non-tied component as
a description of which regime the effect lives in.

We treat the response-level $p_{\text{response}} = 0.0026$ (two-tailed; $0.0013$
one-tailed) as our primary estimate (consistent with the original Mohler
evaluation protocol). All estimates above were computed from the actual
paired-error vectors on the full $n=120$ KG-aligned subset by the script
\texttt{compute\_clustered\_significance.py} in the supplementary materials;
the full LOOCV $p$ vector is reported in the JSON output for reviewer
inspection.

\emph{(iv) Variance-approximation note for the cross-dataset pool.} The
meta-analysis in \S\ref{subsec:crossdataset_sig} uses the Hedges--Olkin
unpaired-$d$ variance approximation
$\widehat{\text{var}}(d_z) \approx 1/n + d_z^2/(2n)$, which is the
common-practice large-sample formula. For paired $d_z$ the exact variance
also depends on the within-subject correlation
$\rho_{\text{err}} = \text{corr}(|h - \hat{y}_{\text{C\_LLM}}|, |h -
\hat{y}_{\text{C5}}|)$, so the inverse-variance weights and pooled CI in
\S\ref{subsec:crossdataset_sig} are approximate. We verified that
recomputing the pool under $\rho_{\text{err}} \in \{0.3, 0.5, 0.7\}$
changes the pooled $d_z$ by less than $0.01$ and never moves either the
fixed-effects or random-effects significance verdict; the approximation is
not the binding step.

\textbf{Comparability note.} Published results on the Mohler benchmark (Mohler 2011,
Sultan 2016) were computed on the full 630-sample dataset with different
train/test splits. Direct numerical comparison should be interpreted with caution,
as evaluation sets differ. We include them in Table~\ref{tab:main_results} as
reference points for historical context, not as head-to-head competition.
```

---

## Block 2 — Full Appendix: "Retracted Fabricated-Data Analysis (Historical
Record)"

This is the complete appendix from the full draft, containing every
figure, table, and sub-ablation computed on the fabricated fixture. It
was already labeled and isolated as an appendix prior to this pass; it is
reproduced here verbatim for the supplementary materials rather than
included in the submitted manuscript itself.

```latex
\appendices
\section{Retracted Fabricated-Data Analysis (Historical Record)}
\label{app:retracted}

Everything in this appendix was computed on a hand-authored, fabricated
120-sample/10-question fixture rather than the real Mohler et al.\
(2011) benchmark; see REPRODUCIBILITY.md for the full incident record.
All point estimates, $p$-values, confidence intervals, and underlying
data are retained exactly as originally computed for the
experimental-design record --- \textbf{none of them should be cited as
evidence.} The five retracted figures in this appendix were given a
purely cosmetic recolor pass in this revision, to a consistent palette
matching the rest of the paper's figures; no data point, axis value, or
label text was changed in that pass. The paper's real, corrected
results are reported throughout the main text (Sections
\ref{sec:results}--\ref{sec:ablation}).

\subsection{Statistical Significance: Retracted Fabricated-Data Analysis (2026-07-28)}
\label{subsec:significance}

\textbf{Correction: this entire subsection, through the end of
\S\ref{subsec:ci_analysis}, analyses the fabricated 120-sample fixture
documented in REPRODUCIBILITY.md, not real data.} It predates the
real-data correction and was not updated when \S\ref{sec:results}'s
Main Evaluation and \S\ref{subsec:crossdataset_sig}'s Cross-Dataset
Boundary Characterisation were rewritten with real Mohler numbers; we
retain it below, unmodified, for the experimental-design record only ---
\textbf{none of the $n=120$/$n=90$ point estimates, $p$-values, or CIs
in this subsection or the next should be cited as evidence}. The real,
authoritative significance result is already reported in
\S\ref{sec:results} (response-level Wilcoxon $p<0.0001$, $n=1{,}262$;
question-clustered $p=0.111$ two-tailed / $0.056$ one-tailed, $46$ real
questions) and \S\ref{subsec:crossdataset_sig} (Table~\ref{tab:crossdataset_sensitivity}).

\textbf{This subsection analyses the full $n=120$ KG-aligned sample}
(the tie structure below is a full-sample property; the held-out $n=90$
test split reported as primary in Table~\ref{tab:main_results} has a
different tie count, $47$, and is analysed separately in
\S\ref{subsec:ci_analysis}). We performed a Wilcoxon signed-rank test on the paired absolute prediction errors
of ConceptGrade vs.\ the LLM baseline (\texttt{scipy.stats.wilcoxon},
$n_{\text{nonzero}} = 50$ after dropping $70$ tied predictions). ConceptGrade
achieves a mean absolute error (MAE) of $0.223$, compared to $0.330$ for the LLM
baseline---a $32.4\%$ reduction that is statistically significant
($W_+ = 344$, two-tailed $p = 0.0026$; one-tailed $p = 0.0013$ for the
pre-registered directional alternative $\text{error}_{\text{C5}} <
\text{error}_{\text{C\_LLM}}$). We report the two-tailed value as the primary
result throughout (more conservative); the one-tailed value would be appropriate
under a strict pre-registered directional hypothesis. The held-out test-split
comparison ($n=90$, $34.0\%$ reduction, two-tailed $p=0.0053$) is consistent
in direction and magnitude.

\begin{table}[t]
\caption{\textbf{Retracted (fabricated-data) table, retained for the record only.}
Wilcoxon Signed-Rank Test: ConceptGrade vs.\ LLM Baseline. $W_+$ = sum
of positive signed ranks (over $50$ non-zero paired differences after dropping
$70$ ties). Both two-tailed and one-tailed (directional, $\text{err}_{\text{C5}}
< \text{err}_{\text{C\_LLM}}$) $p$-values reported.}
\label{tab:significance}
\centering
\begin{tabular}{lccc}
\toprule
\textbf{Comparison} & \textbf{$W_+$} & \textbf{$p$ (two-tailed)} & \textbf{$p$ (one-tailed)} \\
\midrule
$|\text{err}_{\text{C5}}|$ vs $|\text{err}_{\text{C\_LLM}}|$ & 344 & 0.0026 ** & 0.0013 ** \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Preliminary Bar-Chart and Scatter Figures}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fig2_evaluation_results.png}
  \caption{\textbf{Retracted preliminary figure, retained for the record
           only.} This $n=30$ offline validation predates and is
           unrelated to the corrected real-data result in
           Table~\ref{tab:main_results}; it was computed on the same
           fabricated fixture documented in REPRODUCIBILITY.md and
           should not be read as evidence. Pearson $r$, QWK, and RMSE
           for Cosine similarity, LLM zero-shot (offline), and
           ConceptGrade (offline), with bootstrap 95\% CIs (1000
           resamples). Regenerating this figure on real data is future
           work.}
  \label{fig:results}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fig4_score_analysis.png}
  \caption{\textbf{Retracted preliminary figure, retained for the record
           only.} Predicted vs.\ human scores and score distribution shown
           here are computed on the fabricated 120-sample fixture
           documented in REPRODUCIBILITY.md, not the real data underlying
           Table~\ref{tab:main_results}. Regenerating this figure on the
           real $n=1{,}262$ sample is future work.}
  \label{fig:scatter}
\end{figure}

\subsection{Remaining Bootstrap CI Rows}

\begin{table}[t]
\caption{\textbf{Retracted (fabricated-data) rows, retained for the record only.}
Bootstrap 95\% CIs for MAE reduction, continued from Table~\ref{tab:bootstrap_test}'s
real Mohler-test row above. Mohler-all is the fabricated 120-sample fixture;
DigiKlausur/Kaggle here predate deduplication. Should not be read as evidence.}
\label{tab:bootstrap_test_retracted}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{lcccc}
\toprule
\textbf{Dataset} & $n$ / $Q$ & \textbf{Point} & \textbf{Sample 95\%} & \textbf{Cluster 95\%} \\
\midrule
Mohler all   & 120 / 10 & $32.4\%$ & $[14.6\%,\,46.7\%]$ & $[8.4\%,\,49.9\%]$ \\
DigiKlausur  & 646 / 17 & $4.9\%$  & $[-0.9\%,\,10.3\%]$ & $[-10.0\%,\,16.1\%]$ \\
Kaggle ASAG  & 473 /150 & $2.4\%$  & $[-5.4\%,\,9.5\%]$  & $[-6.5\%,\,10.2\%]$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Per-Question Breakdown and Confidence-Interval Figure}

\textbf{Per-question robustness check.} A reviewer may reasonably ask
whether the $32.4\%$ MAE reduction is driven by one or two outlier
questions. We computed the per-question paired MAE comparison on the full
$n = 120$ Mohler subset (Table~\ref{tab:per_question}). ConceptGrade
beats the LLM baseline on $\boldsymbol{8}$ of $\boldsymbol{10}$
questions; the two losses (Q4: $-20.0\%$, Q10: $-92.3\%$) occur on the
two questions where the LLM baseline already achieves its lowest
absolute MAE ($0.21$ and $0.16$ respectively), so the percentage swings
are mathematically large but the absolute differences are tiny
($\Delta \text{MAE} = +0.04$ and $+0.15$ in C\_LLM's favour). The two
largest C5 wins are on the two hardest questions for the LLM baseline:
Q2 ($\Delta\text{MAE} = -0.42$, $76.9\%$ reduction) and Q9
($\Delta\text{MAE} = -0.23$, $41.2\%$ reduction). The result is not
driven by an outlier question.

\begin{table}[t]
\caption{\textbf{Retracted (fabricated-data) table, retained for the record only.}
Per-question MAE on the full $n = 120$ Mohler subset.
$\Delta$MAE $> 0 =$ ConceptGrade better. ConceptGrade beats the LLM
baseline on $8 / 10$ questions.}
\label{tab:per_question}
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lccccc}
\toprule
\textbf{Q} & $n$ & \textbf{C\_LLM} & \textbf{C5\_fix} & \textbf{$\Delta$MAE} & \textbf{Reduction} \\
\midrule
Q1  & 12 & 0.438 & 0.271 & $+0.167$ & $+38.1\%$ \\
Q2  & 12 & 0.542 & 0.125 & $+0.417$ & $\boldsymbol{+76.9\%}$ \\
Q3  & 12 & 0.354 & 0.271 & $+0.083$ & $+23.5\%$ \\
Q4  & 12 & 0.208 & 0.250 & $-0.042$ & $-20.0\%$ \\
Q5  & 12 & 0.275 & 0.167 & $+0.108$ & $+39.4\%$ \\
Q6  & 12 & 0.358 & 0.250 & $+0.108$ & $+30.2\%$ \\
Q7  & 12 & 0.188 & 0.125 & $+0.062$ & $+33.3\%$ \\
Q8  & 12 & 0.208 & 0.125 & $+0.083$ & $+40.0\%$ \\
Q9  & 12 & 0.567 & 0.333 & $+0.233$ & $\boldsymbol{+41.2\%}$ \\
Q10 & 12 & 0.163 & 0.313 & $-0.150$ & $-92.3\%$ \\
\bottomrule
\end{tabular}
\end{table}

\textbf{The $r=0.982$/QWK$=0.975$ figures below, and the reference to
Table~\ref{tab:main_results} in the sentence that originally accompanied
them, are fabricated-data-era numbers left over from before the
real-data correction; Table~\ref{tab:main_results} in fact reports the
real $r=0.7841$/QWK$=0.5237$.} We retain the sentence and figure below
for the record only.

For Pearson $r$ and QWK we retain the dev-set reporting in
Fig.~\ref{fig:ci} for backward compatibility with earlier versions; the
test-set point estimates were reported as $r = 0.982$ and
$\text{QWK} = 0.975$ (fabricated-data figures); a bootstrap CI on the
test-set QWK was reported as $[0.942, 0.997]$.

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fig10_confidence_intervals.png}
  \caption{\textbf{Retracted (fabricated-data) figure, retained for the record only.}
           Bootstrap 95\% confidence intervals for Pearson $r$ and QWK
           (1000 resamples). ConceptGrade's lower CI bound for Pearson $r$
           (0.922) aligns closely with the LLM Zero-Shot's point estimate.}
  \label{fig:ci}
\end{figure}

\textbf{End of retracted fabricated-data subsections.} Everything from
\S\ref{subsec:significance} to this point analysed the fabricated
120-sample fixture. The next section (Ablation Study) returns to a mix
of retracted fabricated-data content (clearly labeled) and the real-data
3-condition ablation added 2026-07-28.

\subsection{Signal-Source Sub-Ablation}

\textbf{Signal-source ablation (REAL-2): retracted (2026-07-28), despite
its name.} \textbf{Correction: despite being labeled ``REAL-2,'' this
sub-ablation was computed on the fabricated 120-sample fixture, not real
data, and carried no retraction label until this correction pass. Its
conclusion below --- that concept-coverage alone slightly
\emph{outperforms} the full system, implying the Verifier contributes
nothing --- directly contradicts the real-data 3-condition ablation
above, which found the opposite: the pre-verifier KG-grounded score is
dramatically worse than baseline, and the Verifier drives essentially
all of the real accuracy.} We retain the retracted text below for the
record; \textbf{it should not be cited}. To test whether the headline
$32.4\%$ MAE reduction (fabricated-data figure) was carried by the
high-reliability concept-coverage signal or by the lower-reliability
misconception taxonomy and SOLO/Bloom proxies, we ran a dual-component
ablation in which Gemini grades each
answer twice from disjoint context: \texttt{concepts\_only} (matched
concepts + chain coverage; \emph{no} SOLO/Bloom/misconceptions) and
\texttt{taxonomy\_only} (SOLO + Bloom level; \emph{no} concept lists).
Both ablations use the same model and same human ground truth as the full
system. Results on the fabricated $n = 120$ Mohler fixture:

\begin{itemize}
\item \texttt{C\_LLM} (no KG):                 MAE $= 0.330$
\item \texttt{taxonomy\_only} (SOLO + Bloom):  MAE $= 0.229$  ($30.6\%$ reduction)
\item \texttt{C5\_fix} (full system):          MAE $= 0.223$  ($32.4\%$ reduction)
\item \texttt{concepts\_only} (KG concepts only): MAE $= 0.217$  ($\boldsymbol{34.2\%}$ reduction)
\end{itemize}

The (retracted) headline result was that the concept-coverage signal \emph{alone}
slightly outperforms the full integrated system, while the misconception
taxonomy (machine-IRR $\kappa = 0.54$, moderate agreement after the
construct-validity fix described in \S\ref{subsec:trm_algorithm})
contributes no measurable score improvement. \textbf{This does not hold on
real data} (Table~\ref{tab:ablation_real}): the real-data pre-verifier
KG score is far worse than baseline, not slightly better than the full
system, and the concept-coverage signal alone is nowhere near sufficient
--- the Verifier stage is what makes the real result work at all.


\subsection{Superseded 7-Condition Ablation Table and Figures}

\begin{table}[t]
\caption{\textbf{Retracted (fabricated-data) table, superseded by Table~\ref{tab:ablation_real} above.}
         Ablation Study Results. $\Delta$QWK and $\Delta r$ are drops from the
         full model when each component is removed. Significance tests (Wilcoxon
         signed-rank, one-tailed) compare full ConceptGrade vs.\ each ablation.
         \textbf{Note:} Ablation evaluated on development split ($n = 30$) to
         assess component sensitivity; main evaluation in Table~\ref{tab:main_results}
         uses the held-out test set ($n = 90$). Lower absolute QWK here reflects
         the smaller, more variable development split. These $n=30$/$n=90$ splits
         and the weights in Eq.~\ref{eq:composite} come from the retracted
         fabricated 120-sample fixture and have not been re-verified on real data;
         retained for the experimental-design record only.}
\label{tab:ablation}
\centering
\footnotesize
\begin{tabular}{lccccc}
\toprule
\textbf{Condition} & \textbf{$r$} & \textbf{$\Delta r$} &
\textbf{QWK} & \textbf{$\Delta$QWK} & \textbf{Sig.} \\
\midrule
Full Model           & 0.954 & —        & 0.721 & —        & — \\
$-$ Concept Cov.     & 0.895 & $-0.059$ & 0.305 & $-0.416$ & *** \\
$-$ SOLO Proxy       & 0.933 & $-0.021$ & 0.525 & $-0.196$ & *** \\
$-$ Depth/Bloom's    & 0.964 & $+0.010$ & 0.571 & $-0.150$ & ** \\
$-$ Cosine Sim.      & 0.954 & $+0.001$ & 0.604 & $-0.117$ & ** \\
$-$ Misc.\ Acc.      & 0.951 & $-0.003$ & 0.746 & $+0.025$ & n.s. \\
Cosine-Only          & 0.565 & $-0.389$ & 0.087 & $-0.634$ & *** \\
\midrule
\multicolumn{6}{l}{*** $p{<}0.001$, ** $p{<}0.01$, n.s.\ $p{>}0.05$} \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fig9_component_importance.png}
  \caption{\textbf{Retracted (fabricated-data) figure, retained for the record
           only.} Visualizes the same $n=30$ fabricated-fixture ablation as
           Table~\ref{tab:ablation} above, superseded by the real-data
           3-condition ablation (Table~\ref{tab:ablation_real}); should not
           be read as evidence. Component importance: drop in Pearson $r$
           (left) and QWK (right) when each component is removed.}
  \label{fig:importance}
\end{figure}

\begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/fig3_ablation_study.png}
  \caption{\textbf{Retracted (fabricated-data) figure, retained for the record
           only.} Visualizes the same $n=30$ fabricated-fixture ablation as
           Table~\ref{tab:ablation} above; should not be read as evidence.
           Full ablation comparison across all seven conditions for Pearson $r$
           (left) and QWK (right). The dashed line marks the full model baseline.}
  \label{fig:ablation}
\end{figure}

\subsection{Ensemble Weight Selection: Retracted (2026-07-28)}

\textbf{This subsection is retracted in full.} It previously described a
grid-search tuning procedure over $(\alpha,\beta,\gamma)$ weights
combining coverage/accuracy/integration into a standalone ``overall
comparison score'' (the equation formerly labelled \texttt{eq:overall}),
reporting a tuned QWK of $0.9748$ (itself a fabricated-data-era number,
inconsistent with the real headline QWK of $0.524$ in
Table~\ref{tab:main_results}). While auditing the codebase to write the
real-data ablation (\S\ref{sec:ablation}), we found no code path in
\texttt{conceptgrade/pipeline.py} that computes this $(\alpha,\beta,\gamma)$
combination as a separate, tuned step at all --- see the correction note
in \S\ref{subsec:comparison}. There is consequently no ensemble-weight
grid search to report: the weights actually used by the code are the
fixed constants in Eq.~\ref{eq:kgformula} and Eq.~\ref{eq:composite}
(\S\ref{subsec:synthesis}), not a tuned hyperparameter. We retract this
subsection rather than attempt to retrofit a plausible-sounding
justification for numbers that do not correspond to any real procedure.

\subsection{Grounding Density Analysis: Retracted (2026-07-28)}

\textbf{Correction: this subsection presents the fabricated 120-sample
fixture's zero-grounding analysis (Table~\ref{tab:grounding_density})
without a retraction label, and its results are not verified on real
data.} Unlike the other fabricated-data content in this paper,
re-verifying this analysis genuinely requires new LLM calls (LRM/TRM
reasoning-trace generation was never collected for the real 1{,}262-sample
data --- see REPRODUCIBILITY.md's "Still open" list) and cannot be
recomputed offline from already-cached data, unlike the ablation and
sensitivity sweeps elsewhere in this paper. Paper 2's equivalent table
(\S"Accuracy Stratified by Grounding Density") is already correctly
captioned "Retracted... pending re-verification"; this subsection was
missed during that reconciliation pass and is fixed here for
consistency. We retain the analysis below, unmodified, for the
experimental-design record only --- \textbf{none of its numbers should
be cited as evidence}.

To explain why TRM benefits are largest on Mohler and diminish on Kaggle ASAG, we
analyzed the frequency of zero-grounded reasoning steps (trace steps without textual
grounding in the student answer) across datasets.

\textit{The zero-grounding measurement protocol and Algorithm~1 that
define this check are real, currently-used methodology (part of the
Verifier confidence weighting, Eq.~7) and have been moved to
\S\ref{subsec:trm_algorithm} in the main body, where the algorithm is
first used. Only the results below (Table~\ref{tab:grounding_density},
computed on the fabricated fixture) remain retracted.}


\textbf{Results:} Analysis of the frequency of zero-grounded reasoning steps across
datasets:

\begin{table}[h]
\caption{\textbf{Retracted (fabricated-data) table, retained for the record only.}
         Zero-Grounding Frequency and TRM Effectiveness. Percentage of trace steps
         lacking sufficient textual grounding (LCS match ratio $< 0.75$) in student
         answers, with corresponding MAE improvements and statistical significance.}
\label{tab:grounding_density}
\centering
\footnotesize
\begin{tabular}{lcccc}
\toprule
\textbf{Dataset} & \textbf{$n$} & \textbf{ZG\%} & \textbf{95\% CI} &
\textbf{MAE$\downarrow$} \\
\midrule
Mohler (CS)  & 120 & 7.2  & [4.1, 10.3]\%  & 32.4\% ($p{=}0.003$) \\
DigiKlausur  & 188 & 17.8 & [13.2, 22.4]\% & 4.9\% ($p{=}0.0489$) \\
Kaggle ASAG  & 100 & 30.6 & [21.0, 40.2]\% & 2.4\% (n.s.) \\
\bottomrule
\multicolumn{5}{l}{ZG\% = zero-grounding frequency. $p$ = Wilcoxon.}
\end{tabular}
\end{table}

This pattern (Table~\ref{tab:grounding_density}) reveals a mechanism underlying TRM's
effectiveness. When the LLM's reasoning trace is sufficiently grounded in the
student's actual text (grounding density $\geq 75\%$, i.e., zero-grounding frequency
$\leq 25\%$), TRM's structural validation against the knowledge graph provides
strong signal for grade refinement. Conversely, when LLM hallucinations
are prevalent (low grounding density), the system is forced to reweight reasoning
steps that lack textual evidence, reducing the marginal value of structural
grounding. This explains why Kaggle ASAG shows diminished returns: the more
colloquial language and domain-specific jargon in elementary science responses
makes it harder for the LLM to generate traces that align with our formal KG,
resulting in higher zero-grounding frequency and correspondingly lower TRM impact.

The implication is that TRM is most effective as a complementary signal in domains
where formal terminology is well-established and students use it consistently. In
domains where student vocabulary diverges significantly from formal domain models,
richer knowledge graphs or domain-specific pre-processing may be necessary.
```
