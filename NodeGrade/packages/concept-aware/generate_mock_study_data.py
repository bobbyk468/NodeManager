#!/usr/bin/env python3
"""
Generate realistic mock user-study data for Paper 2 figures.
Based on expected effect sizes from study protocol.
This is a pre-submission mock; replace with real data once study completes.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# Set seed for reproducibility
np.random.seed(42)

# Study parameters
N_TOTAL = 64
N_PER_CONDITION = N_TOTAL // 2

print("=" * 70)
print("MOCK STUDY DATA GENERATION FOR PAPER 2")
print("=" * 70)

# ============================================================================
# FIGURE 8: SUS SCORES
# ============================================================================
print("\n[1/3] Generating SUS Scores data (Figure 8)...")

# SUS is 0-100 scale
# Control condition (text summary only): expect poor usability ~58 (Grade D)
# Treatment condition (full dashboard): expect good usability ~72 (Grade B)

sus_control = np.random.normal(loc=58, scale=18, size=N_PER_CONDITION)
sus_control = np.clip(sus_control, 0, 100)  # Bound to 0-100

sus_treatment = np.random.normal(loc=72, scale=14, size=N_PER_CONDITION)
sus_treatment = np.clip(sus_treatment, 0, 100)  # Bound to 0-100

# Calculate statistics
sus_control_mean = np.mean(sus_control)
sus_control_sd = np.std(sus_control, ddof=1)
sus_treatment_mean = np.mean(sus_treatment)
sus_treatment_sd = np.std(sus_treatment, ddof=1)

# Effect size (Cohen's d)
pooled_sd = np.sqrt((sus_control_sd**2 + sus_treatment_sd**2) / 2)
cohens_d = (sus_treatment_mean - sus_control_mean) / pooled_sd

# Statistical test (t-test)
t_stat, p_value_sus = stats.ttest_ind(sus_treatment, sus_control)

print(f"  Control SUS:   M={sus_control_mean:.1f}, SD={sus_control_sd:.1f}")
print(f"  Treatment SUS: M={sus_treatment_mean:.1f}, SD={sus_treatment_sd:.1f}")
print(f"  Cohen's d: {cohens_d:.2f} (medium-to-large effect)")
print(f"  t-test: t={t_stat:.2f}, p={p_value_sus:.4f} {'*' if p_value_sus < 0.05 else '(n.s.)'}")

# Create Figure 8: SUS Scores bar chart
fig, ax = plt.subplots(figsize=(8, 5))
conditions = ['Control\n(Condition A)', 'Treatment\n(Condition B)']
means = [sus_control_mean, sus_treatment_mean]
sds = [sus_control_sd, sus_treatment_sd]
colors = ['#FF6B6B', '#4ECDC4']

bars = ax.bar(conditions, means, yerr=sds, capsize=10, color=colors, alpha=0.7,
              edgecolor='black', linewidth=1.5, error_kw={'linewidth': 2})

ax.set_ylabel('SUS Score (0-100)', fontsize=12, fontweight='bold')
ax.set_title('System Usability Scale: Control vs. Treatment', fontsize=13, fontweight='bold')
ax.set_ylim([0, 100])
ax.axhline(y=68, color='gray', linestyle='--', linewidth=1, label='Acceptable (68)')
ax.axhline(y=80.3, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Good (80.3)')
ax.legend(loc='upper left', fontsize=9)

# Add value labels on bars
for i, (bar, mean) in enumerate(zip(bars, means)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 3,
            f'{mean:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=11)

# Add p-value annotation
if p_value_sus < 0.05:
    ax.text(0.5, 95, f'p={p_value_sus:.4f} *', ha='center', fontsize=11, fontweight='bold')
else:
    ax.text(0.5, 95, f'p={p_value_sus:.4f} (n.s.)', ha='center', fontsize=11)

ax.grid(axis='y', alpha=0.3, linestyle=':')
plt.tight_layout()
plt.savefig('/Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/usability_sus_scores.png', dpi=300, bbox_inches='tight')
print("  ✓ Saved: usability_sus_scores.png")
plt.close()

# ============================================================================
# FIGURE 9: QUALITATIVE THEMES (Think-Aloud Coding Frequencies)
# ============================================================================
print("\n[2/3] Generating Qualitative Themes data (Figure 9)...")

# Coding categories:
# CA = Causal Attribution (explicit "because I saw in the KG/trace")
# SA = Semantic Alignment (rubric refinement evidence)
# TC = Trust Calibration (confidence in grades)
# II = Interaction Insight (other insights from interaction)

# Expected: Treatment condition shows higher frequency across all codes
coding_categories = ['Causal\nAttribution\n(CA)', 'Semantic\nAlignment\n(SA)',
                    'Trust\nCalibration\n(TC)', 'Interaction\nInsight\n(II)']

# Control: lower frequency across all codes (fewer strategic interactions)
ca_control = 2   # Only 2 explicit causal references
sa_control = 1   # Minimal rubric refinement
tc_control = 3   # Some trust statements
ii_control = 2   # Other insights

# Treatment: higher frequency (rich interactive exploration)
ca_treatment = 11  # Many explicit causal statements ("because the KG showed...")
sa_treatment = 9   # Frequent rubric refinement during session
tc_treatment = 8   # Strong trust calibration behaviors
ii_treatment = 6   # Emergent insights from interaction

control_counts = [ca_control, sa_control, tc_control, ii_control]
treatment_counts = [ca_treatment, sa_treatment, tc_treatment, ii_treatment]

print(f"  Control frequencies:   CA={ca_control}, SA={sa_control}, TC={tc_control}, II={ii_control}")
print(f"  Treatment frequencies: CA={ca_treatment}, SA={sa_treatment}, TC={tc_treatment}, II={ii_treatment}")

# Create Figure 9: Qualitative Themes bar chart (grouped)
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(coding_categories))
width = 0.35

bars1 = ax.bar(x - width/2, control_counts, width, label='Control (A)',
               color='#FF6B6B', alpha=0.7, edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, treatment_counts, width, label='Treatment (B)',
               color='#4ECDC4', alpha=0.7, edgecolor='black', linewidth=1.5)

ax.set_ylabel('Frequency (# of coded segments)', fontsize=12, fontweight='bold')
ax.set_title('Think-Aloud Qualitative Coding: Theme Frequencies by Condition',
             fontsize=13, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(coding_categories, fontsize=10)
ax.legend(fontsize=11, loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle=':')

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=10)

plt.tight_layout()
plt.savefig('/Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/qualitative_themes_bars.png', dpi=300, bbox_inches='tight')
print("  ✓ Saved: qualitative_themes_bars.png")
plt.close()

# ============================================================================
# FIGURE 10: SEMANTIC ALIGNMENT PRE/POST OUTCOMES
# ============================================================================
print("\n[3/3] Generating Semantic Alignment Pre/Post data (Figure 10)...")

# Semantic Alignment (SA) score: 0-1 scale indicating how well rubric covers student concepts
# Pre-study: baseline rubric alignment (typically 0.55-0.65 for under-specified rubrics)
# Post-study: educators refine rubric based on what they learned

pre_baseline = 0.58

# Control: minimal improvement (limited visual evidence to guide rubric refinement)
post_control = np.random.normal(loc=0.62, scale=0.08, size=N_PER_CONDITION)
post_control = np.clip(post_control, 0, 1)
pre_control = np.random.normal(loc=pre_baseline, scale=0.06, size=N_PER_CONDITION)
pre_control = np.clip(pre_control, 0, 1)

# Treatment: larger improvement (structured visual evidence guides targeted refinement)
post_treatment = np.random.normal(loc=0.74, scale=0.09, size=N_PER_CONDITION)
post_treatment = np.clip(post_treatment, 0, 1)
pre_treatment = np.random.normal(loc=pre_baseline, scale=0.06, size=N_PER_CONDITION)
pre_treatment = np.clip(pre_treatment, 0, 1)

# Calculate improvements
improvement_control = np.mean(post_control) - np.mean(pre_control)
improvement_treatment = np.mean(post_treatment) - np.mean(pre_treatment)

print(f"  Control:   pre={np.mean(pre_control):.3f}, post={np.mean(post_control):.3f}, Δ={improvement_control:.3f}")
print(f"  Treatment: pre={np.mean(pre_treatment):.3f}, post={np.mean(post_treatment):.3f}, Δ={improvement_treatment:.3f}")

# Statistical test (paired t-test within each condition, then between-group comparison of improvements)
t_within_control, p_within_control = stats.ttest_rel(post_control, pre_control)
t_within_treatment, p_within_treatment = stats.ttest_rel(post_treatment, pre_treatment)
t_between, p_between = stats.ttest_ind(improvement_treatment, improvement_control)

print(f"  Within-group t-tests:")
print(f"    Control:   t={t_within_control:.2f}, p={p_within_control:.4f}")
print(f"    Treatment: t={t_within_treatment:.2f}, p={p_within_treatment:.4f}")
print(f"  Between-group improvement: t={t_between:.2f}, p={p_between:.4f}")

# Create Figure 10: Pre/Post comparison
fig, ax = plt.subplots(figsize=(10, 5))

x_positions = np.arange(2)
width = 0.35

# Pre scores
pre_means = [np.mean(pre_control), np.mean(pre_treatment)]
pre_sds = [np.std(pre_control, ddof=1), np.std(pre_treatment, ddof=1)]

# Post scores
post_means = [np.mean(post_control), np.mean(post_treatment)]
post_sds = [np.std(post_control, ddof=1), np.std(post_treatment, ddof=1)]

bars1 = ax.bar(x_positions - width/2, pre_means, width, yerr=pre_sds, capsize=8,
               label='Pre-Study (Baseline)', color='#95A5A6', alpha=0.7,
               edgecolor='black', linewidth=1.5, error_kw={'linewidth': 1.5})
bars2 = ax.bar(x_positions + width/2, post_means, width, yerr=post_sds, capsize=8,
               label='Post-Study', color=['#FF6B6B', '#4ECDC4'], alpha=0.7,
               edgecolor='black', linewidth=1.5, error_kw={'linewidth': 1.5})

# Add improvement annotations (arrows)
for i in range(2):
    improvement = improvement_control if i == 0 else improvement_treatment
    x_pos = i
    ax.annotate('', xy=(x_pos + width/2 + 0.02, post_means[i]),
                xytext=(x_pos - width/2 - 0.02, pre_means[i]),
                arrowprops=dict(arrowstyle='->', lw=2, color='black', alpha=0.5))
    ax.text(x_pos + 0.05, (pre_means[i] + post_means[i])/2,
            f'Δ={improvement:.3f}', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

ax.set_ylabel('Semantic Alignment Score (0-1)', fontsize=12, fontweight='bold')
ax.set_title('Primary Outcome: Rubric Semantic Alignment (Pre vs. Post)',
             fontsize=13, fontweight='bold')
ax.set_xticks(x_positions)
ax.set_xticklabels(['Control\n(Condition A)', 'Treatment\n(Condition B)'], fontsize=11)
ax.set_ylim([0, 1.0])
ax.legend(fontsize=11, loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle=':')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.03,
                f'{height:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig('/Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware/docs/figures/study_outcome_semantic_alignment.png', dpi=300, bbox_inches='tight')
print("  ✓ Saved: study_outcome_semantic_alignment.png")
plt.close()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("MOCK DATA SUMMARY")
print("=" * 70)
print(f"""
Figure 8 (SUS Scores):
  • Control (A):   M={sus_control_mean:.1f}, SD={sus_control_sd:.1f} [Grade D: Poor]
  • Treatment (B): M={sus_treatment_mean:.1f}, SD={sus_treatment_sd:.1f} [Grade B: Good]
  • Effect: Cohen's d={cohens_d:.2f}, p={p_value_sus:.4f} {'(SIGNIFICANT)' if p_value_sus < 0.05 else '(n.s.)'}

Figure 9 (Qualitative Themes):
  • Control:   CA={ca_control}, SA={sa_control}, TC={tc_control}, II={ii_control} (Total={sum(control_counts)})
  • Treatment: CA={ca_treatment}, SA={sa_treatment}, TC={tc_treatment}, II={ii_treatment} (Total={sum(treatment_counts)})
  • Interpretation: Treatment shows {sum(treatment_counts)/sum(control_counts):.1f}x higher coding frequency

Figure 10 (Semantic Alignment):
  • Control improvement:   {improvement_control:.3f} (p={p_within_control:.4f})
  • Treatment improvement: {improvement_treatment:.3f} (p={p_within_treatment:.4f})
  • Between-condition: Treatment improvement is {improvement_treatment/improvement_control:.1f}x larger (p={p_between:.4f})

Status: ✓ All three figures generated with realistic mock data.
Note: Replace these numbers with actual study results when user study completes.
""")

print("\n✓ Mock data generation complete. Figures ready for paper submission.")
print("  Replace Figure 8, 9, 10 captions in LaTeX to reference this mock data,")
print("  then update with real data once user study is conducted.")
