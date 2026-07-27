#!/usr/bin/env python3
"""Recompute the paper's cross-dataset pooled meta-analysis with the
dedupd Kaggle numbers. Fixed-effects inverse-variance weighting on d_z,
plus DerSimonian-Laird random-effects.

Per-dataset d_z values (post-Fix-#19 for Kaggle):
  Mohler:      -0.30, n=120
  DigiKlausur: -0.07, n=646
  Kaggle:      -0.01, n=368  (was -0.03 on n=473)
"""
import math
from scipy.stats import norm

# (label, d_z, n)
studies = [
    ("Mohler",      -0.30, 120),
    ("DigiKlausur", -0.07, 646),
    ("Kaggle",      -0.01, 368),
]

# SE of paired d_z ≈ sqrt(1/n + d_z^2 / (2n))
studies = [(l, d, n, math.sqrt(1.0/n + (d*d)/(2*n))) for (l, d, n) in studies]

# Fixed effects: weight = 1/SE^2
w = [1.0/(se*se) for (_,_,_,se) in studies]
d = [d for (_,d,_,_) in studies]
fe = sum(wi*di for wi, di in zip(w, d)) / sum(w)
fe_se = math.sqrt(1.0/sum(w))
fe_lo, fe_hi = fe - 1.96*fe_se, fe + 1.96*fe_se
fe_z = fe / fe_se
fe_p_two = 2 * (1 - norm.cdf(abs(fe_z)))
fe_p_one = 1 - norm.cdf(-fe_z) if fe < 0 else norm.cdf(fe_z)

# Cochran's Q + I^2 for random effects
Q = sum(wi * (di - fe)**2 for wi, di in zip(w, d))
k = len(studies)
I2 = max(0, (Q - (k-1)) / Q) * 100 if Q > 0 else 0.0
tau2 = max(0, (Q - (k-1)) / (sum(w) - sum(wi*wi for wi in w)/sum(w))) if Q > (k-1) else 0.0

# Random effects: new weights include tau^2
w_re = [1.0/(1.0/wi + tau2) for wi in w]
re = sum(wi*di for wi, di in zip(w_re, d)) / sum(w_re)
re_se = math.sqrt(1.0/sum(w_re))
re_lo, re_hi = re - 1.96*re_se, re + 1.96*re_se
re_z = re / re_se
re_p_two = 2 * (1 - norm.cdf(abs(re_z)))
re_p_one = 1 - norm.cdf(-re_z) if re < 0 else norm.cdf(re_z)

print("Per-study:")
for (l, dv, n, se) in studies:
    print(f"  {l:<14} d_z={dv:+.3f}  n={n}  SE={se:.4f}")

print(f"\nCochran Q = {Q:.3f}, I^2 = {I2:.1f}%, tau^2 = {tau2:.4f}")
print(f"\nFixed-effects pool: d_z = {fe:+.3f}  95% CI [{fe_lo:+.3f}, {fe_hi:+.3f}]  "
      f"p_two = {fe_p_two:.3f} / p_one = {fe_p_one:.3f}")
print(f"Random-effects pool: d_z = {re:+.3f}  95% CI [{re_lo:+.3f}, {re_hi:+.3f}]  "
      f"p_two = {re_p_two:.3f} / p_one = {re_p_one:.3f}, I^2 = {I2:.1f}%")
