#!/usr/bin/env python3
"""
Statistical Analysis Script for ConceptGrade User Study Results

This script analyzes the data collected from N=64 educator study sessions
and computes all primary and secondary outcome measures with statistical tests.

Usage:
    python3 analyze_study_results.py --data data/session_logs/ --output results/

Output:
    - results/statistical_tests.csv
    - results/study_results_tables.tex (for Paper 2)
"""

import json
import csv
import os
import sys
from pathlib import Path
from statistics import mean, stdev
from datetime import datetime

import numpy as np
from scipy import stats

def load_session_logs(log_dir):
    """Load all session JSON logs from directory"""
    logs = []
    log_path = Path(log_dir)

    for log_file in sorted(log_path.glob("*.json")):
        try:
            with open(log_file) as f:
                session_data = json.load(f)
                logs.append({'file': log_file.name, 'data': session_data})
        except:
            print(f"Warning: Invalid JSON in {log_file.name}")
            continue

    return logs

def extract_outcomes(logs):
    """Extract primary and secondary outcomes from logs"""
    outcomes = {
        'task_accuracy_a': [],
        'task_accuracy_b': [],
        'time_to_decision_a': [],
        'time_to_decision_b': [],
        'sus_scores_a': [],
        'sus_scores_b': [],
        'qualitative_ca': [],
        'qualitative_sa': [],
        'qualitative_tc': [],
        'qualitative_ii': []
    }

    for log in logs:
        data = log['data']
        condition = data.get('condition', 'unknown')
        key_suffix = '_a' if condition == 'A' else '_b' if condition == 'B' else None

        if key_suffix:
            # Primary outcomes
            if 'task_accuracy' in data:
                outcomes[f'task_accuracy{key_suffix}'].append(data['task_accuracy'])
            if 'time_to_decision_seconds' in data:
                outcomes[f'time_to_decision{key_suffix}'].append(data['time_to_decision_seconds'])

            # Secondary outcomes
            if 'sus_score' in data:
                outcomes[f'sus_scores{key_suffix}'].append(data['sus_score'])

    return outcomes

def mann_whitney_u_test(group_a, group_b, label):
    """Perform Mann-Whitney U test"""
    if not group_a or not group_b:
        return None

    statistic, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
    cohens_d = (mean(group_a) - mean(group_b)) / np.sqrt((stdev(group_a)**2 + stdev(group_b)**2) / 2)

    return {
        'metric': label,
        'condition_a_mean': mean(group_a),
        'condition_a_sd': stdev(group_a) if len(group_a) > 1 else 0,
        'condition_b_mean': mean(group_b),
        'condition_b_sd': stdev(group_b) if len(group_b) > 1 else 0,
        'u_statistic': statistic,
        'p_value': p_value,
        'cohens_d': cohens_d,
        'significant': 'YES' if p_value < 0.05 else 'NO'
    }

def analyze_study(log_dir, output_dir):
    """Main analysis pipeline"""
    print("\n" + "=" * 80)
    print("CONCEPTGRADE USER STUDY: STATISTICAL ANALYSIS")
    print("=" * 80)

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[1/2] Loading session logs from {log_dir}...")
    logs = load_session_logs(log_dir)
    print(f"      Loaded {len(logs)} session logs")

    if not logs:
        print("ERROR: No session logs found!")
        return

    print(f"\n[2/2] Extracting outcomes and computing statistics...")
    outcomes = extract_outcomes(logs)

    results = []

    # Primary Outcome 1: Task Accuracy
    if outcomes['task_accuracy_a'] and outcomes['task_accuracy_b']:
        test = mann_whitney_u_test(
            outcomes['task_accuracy_a'],
            outcomes['task_accuracy_b'],
            'Task Accuracy (%)'
        )
        if test:
            results.append(test)
            print(f"      Task Accuracy: p={test['p_value']:.4f} ({test['significant']}), d={test['cohens_d']:.2f}")

    # Primary Outcome 2: Time-to-Decision
    if outcomes['time_to_decision_a'] and outcomes['time_to_decision_b']:
        test = mann_whitney_u_test(
            outcomes['time_to_decision_a'],
            outcomes['time_to_decision_b'],
            'Time-to-Decision (sec)'
        )
        if test:
            results.append(test)
            print(f"      Time-to-Decision: p={test['p_value']:.4f} ({test['significant']}), d={test['cohens_d']:.2f}")

    # Secondary Outcome: SUS Scores
    if outcomes['sus_scores_a'] and outcomes['sus_scores_b']:
        test = mann_whitney_u_test(
            outcomes['sus_scores_a'],
            outcomes['sus_scores_b'],
            'SUS Score (0-100)'
        )
        if test:
            results.append(test)
            print(f"      SUS Scores: p={test['p_value']:.4f} ({test['significant']}), d={test['cohens_d']:.2f}")

    # Write results
    print(f"\n      Writing results to {output_dir}/statistical_tests.csv...")
    with open(os.path.join(output_dir, 'statistical_tests.csv'), 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            for result in results:
                writer.writerow(result)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults written to: {output_dir}/statistical_tests.csv")
    print("\nReady to generate Paper 2 Figures 8-10 and Results section.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze ConceptGrade study results")
    parser.add_argument("--data", default="data/session_logs/", help="Session logs directory")
    parser.add_argument("--output", default="results/", help="Output directory")

    args = parser.parse_args()

    try:
        analyze_study(args.data, args.output)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
