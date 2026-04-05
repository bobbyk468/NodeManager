import matplotlib.pyplot as plt
import numpy as np

# Dataset
data = [
    10,
    0,
    268,
    535,
    0,
    0,
    563,
    367,
    703,
    432,
    636,
    109,
    432,
    352,
    458,
    0,
    0,
    620,
    0,
    472,
    510,
    479,
    0,
    214,
    305,
    0,
    0,
    0,
    698,
    0,
    108,
]

# Mean and standard deviation
mean = np.mean(data)
std_dev = np.std(data)

# Bounds for ±2 standard deviations
lower_bound = mean - 2 * std_dev
upper_bound = mean + 2 * std_dev

# Plot
plt.figure(figsize=(10, 6))
plt.hist(data, bins=20, color="blue", alpha=0.7, edgecolor="black")
plt.axvline(mean, color="red", linestyle="dashed", linewidth=2)
plt.axvline(lower_bound, color="green", linestyle="dashed", linewidth=2)
plt.axvline(upper_bound, color="green", linestyle="dashed", linewidth=2)
plt.title("Distribution of data points")
plt.xlabel("Values")
plt.ylabel("Frequency")
plt.grid(True)
plt.show()
