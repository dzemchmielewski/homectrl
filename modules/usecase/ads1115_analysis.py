import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# WCS1800
# x_data = np.array([18.11301, 177.9428, 360.311, 533.8663, 317.4659, 699.8464, 1052.788, 81.99622, 94.87803, 110.9846, 154.6735])

# ACS712:
x_data = np.array([14.83164, 235.7323, 513.3156, 767.0297, 445.1949, 975.7985, 1480.301, 108.2657, 128.179, 148.4483, 208.0938])

y_data = np.array([0, 1.12, 2.44, 3.70, 1.95, 4.32, 6.55, 0.75,0.81, 0.825, 0.945])

# Define a few model functions
def linear(x, a, b):
    return a * x + b

def quadratic(x, a, b, c):
    return a * x**2 + b * x + c

def cubic(x, a, b, c, d):
    return a * x**3 + b * x**2 + c * x + d

def log_model(x, a, b):
    return a * np.log(x) + b

def exp_model(x, a, b):
    return a * np.exp(b * x)

# Try curve fitting for each model
models = {
    "linear": (linear, 2),
    "quadratic": (quadratic, 3),
    "cubic": (cubic, 4),
    "logarithmic": (log_model, 2),
}

fit_results = {}

x_fit = np.linspace(min(x_data), max(x_data), 500)

for name, (model, num_params) in models.items():
    try:
        popt, _ = curve_fit(model, x_data, y_data, maxfev=10000)
        y_fit = model(x_fit, *popt)
        mse = np.mean((model(x_data, *popt) - y_data)**2)
        fit_results[name] = {"params": popt, "mse": mse, "y_fit": y_fit}
    except Exception as e:
        fit_results[name] = {"error": str(e)}

fit_results_sorted = sorted(fit_results.items(), key=lambda item: item[1].get("mse", float('inf')))
best_fit = fit_results_sorted[0]

# Plot best fit
best_model_name = best_fit[0]
best_y_fit = best_fit[1]["y_fit"]

plt.scatter(x_data, y_data, color='red', label='Data')
plt.plot(x_fit, best_y_fit, label=f'Best Fit: {best_model_name}')
plt.legend()
plt.title("Best Fit Curve")
plt.xlabel("x")
plt.ylabel("y")
plt.grid(True)
plt.tight_layout()
plt.show()

print(best_fit[0], best_fit[1]["params"], best_fit[1]["mse"])
