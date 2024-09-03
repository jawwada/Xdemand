Sure, here's a LinkedIn post about your experience and the solution you developed:

---

🔍 **Exploring Optimization in Inventory Management**

Last year, while working for an online retailer, I encountered an intriguing problem related to inventory management and demand forecasting. The goal was to maximize revenues over a 90-day period by adjusting prices and quantities, all while considering constraints on stock levels and incorporating incoming shipments. 📦💼

Today, I had the opportunity to sit down with a couple of friends to discuss this challenge. Their insightful observations and collaborative spirit helped refine our approach, and we now have a well-behaved solution that tackles this complex problem. 🤝💡

Here's a glimpse into our approach:

**Context:**  
The objective is to maximize the sum of revenues over 90 days by adjusting prices and quantities. We need to account for constraints related to stock levels and manage shipments arriving on specific days.

**Formulation:**  
We defined our variables, constraints, and objective function:
- **Objective:** Maximize the sum of daily revenues.
- **Constraints:** Maintain stock levels, and ensure prices remain within a reasonable range.

**Mathematical Nature:**  
This problem is a quadratic programming problem due to the quadratic term in the objective function.

**Solution:**  
Using Python's SciPy library, we implemented an optimization solver that accounts for all the constraints and finds the optimal prices and quantities for each day.

Here's the key snippet of our Python code:

```python
import numpy as np
from scipy.optimize import minimize

# Parameters
Q_0 = 100  # Initial forecasted quantity sold per day
P_0 = 10   # Initial price
alpha = 0.5  # Correlation of price to quantity sold change
S_0 = 1000  # Initial stock
S_min = 100  # Minimum stock required
T = 90  # Number of days
k = 0.2  # Allowed percentage change in price

# Shipments arriving on specific days
shipments = [(10, 200), (30, 300), (60, 150)]
shipment_days = [shipment[0] for shipment in shipments]
shipment_quantities = [shipment[1] for shipment in shipments]

# Bounds for P_t
P_min = P_0 * (1 - k)
P_max = P_0 * (1 + k)
bounds = [(P_min, P_max) for _ in range(T)]

# Objective function to maximize (negative of sum of revenues)
def objective(P):
    Q = Q_0 - alpha * (P - P_0)
    revenue = np.sum(Q * P)
    return -revenue  # Negative for minimization

# Constraint: stock level on each day should be >= minimum stock
def stock_constraint(P):
    S_t = S_0
    for t in range(T):
        Q_t = Q_0 - alpha * (P[t] - P_0)
        if t + 1 in shipment_days:
            S_t += shipment_quantities[shipment_days.index(t + 1)]
        S_t -= Q_t
        if S_t < S_min:
            return S_t - S_min
    return 0

# Constraints dictionary
constraints = {'type': 'ineq', 'fun': stock_constraint}

# Initial guess for P_t
P_initial = np.full(T, P_0)

# Solve the optimization problem
result = minimize(objective, P_initial, bounds=bounds, constraints=constraints)

# Check if the optimization was successful
if result.success:
    optimal_P = result.x
    optimal_Q = Q_0 - alpha * (optimal_P - P_0)
    total_revenue = np.sum(optimal_Q * optimal_P)
    print(f"Optimal Prices: {optimal_P}")
    print(f"Total Revenue: {total_revenue}")
else:
    print("Optimization failed:", result.message)
```

This project was a fantastic opportunity to dive deep into the world of optimization, blending theoretical knowledge with practical applications. A big thanks to my friends for their valuable input and collaboration! 🌟

If you're interested in discussing more about inventory management, demand forecasting, or optimization techniques, feel free to reach out. Let's connect and exchange ideas! 💬🔗

#InventoryManagement #Optimization #DemandForecasting #Python #Collaboration #SupplyChain

---

Feel free to adjust the content to better fit your personal style and professional experience!