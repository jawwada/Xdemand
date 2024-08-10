# Price Elasticity Documentation

## Introduction

This document provides an in-depth explanation of the process and methodology used to calculate the price elasticity of demand for products (SKUs), particularly after adjusting for seasonal effects and trends. Price elasticity is a crucial metric for understanding how the quantity demanded of a product responds to changes in its price. Directly calculating price elasticity without adjusting for external factors such as seasonality and trends can lead to misleading conclusions. This document outlines how these adjustments are made to ensure that the elasticity reflects the true impact of price changes on demand.

## Understanding Price Elasticity

### What is Price Elasticity?

Price elasticity of demand measures the responsiveness of the quantity demanded to changes in price. It is mathematically defined as:

\[
\text{Price Elasticity} = \frac{\%\text{ Change in Quantity Demanded}}{\%\text{ Change in Price}}
\]

This metric helps to understand how sensitive customers are to price changes. For instance, a price elasticity of -1.5 suggests that a 1% increase in price would result in a 1.5% decrease in the quantity demanded.

### Why is Adjusting for Seasonality and Trends Important?

Sales data often exhibits seasonal patterns and long-term trends. Seasonality refers to predictable fluctuations in demand that occur at regular intervals (e.g., increased sales during holidays), while trends represent the overall direction of sales over time (e.g., growth due to market expansion).

Failing to adjust for these factors can result in incorrect estimates of price elasticity. For example, an increase in sales during a seasonally strong period might be incorrectly attributed to a price change rather than the seasonal pattern. Similarly, sales growth driven by a positive trend could be misinterpreted as a response to price adjustments.

### Impact of Adjusting for Seasonality and Trends

By adjusting for seasonality and trends, the price elasticity calculation ensures that the results reflect the true relationship between price and demand, free from external influences. This provides a more accurate basis for making pricing decisions.

## Methodology

### Time Series Decomposition

The process begins by decomposing the sales data into three components: trend, seasonality, and residual. This decomposition is performed using a multiplicative model, which assumes the observed sales data can be represented as:

\[
Q_t = T_t \times S_t \times R_t
\]

Where:
- \(Q_t\) is the observed quantity sold at time \(t\),
- \(T_t\) is the trend component, capturing the long-term movement,
- \(S_t\) is the seasonal component, capturing regular patterns,
- \(R_t\) is the residual component, capturing random fluctuations.

### Adjusting for Trend and Seasonality

Once the data is decomposed, the quantity sold is adjusted by removing the trend and seasonal components:

\[
Q^{\text{adj}}_t = \frac{Q_t}{T_t \times S_t}
\]

This adjusted quantity, \(Q^{\text{adj}}_t\), represents the demand after accounting for external effects, providing a more accurate dataset for price elasticity analysis.

### Log-Log Linear Regression

After adjustment, a log-log linear regression model is applied to estimate price elasticity. The log-log model is chosen because it allows for direct interpretation of the regression coefficient as price elasticity:

\[
\log(Q^{\text{adj}}_t) = \beta_0 + \beta_1 \log(P_t) + \epsilon_t
\]

Where:
- \(Q^{\text{adj}}_t\) is the seasonally and trend-adjusted quantity,
- \(P_t\) is the price,
- \(\beta_0\) is the intercept,
- \(\beta_1\) is the price elasticity,
- \(\epsilon_t\) is the error term.

### Calculating Price Elasticity

The regression coefficient \(\beta_1\) directly represents the price elasticity:

- **Elastic Demand** (\(\beta_1 < -1\)): Indicates that demand is highly responsive to price changes.
- **Inelastic Demand** (\(-1 < \beta_1 < 0\)): Indicates that demand is less responsive to price changes.
- **Positive Elasticity** (\(\beta_1 > 0\)): Indicates unusual cases where demand increases with price.

### SKU-Based Elasticity

The elasticity calculation is performed on a SKU-by-SKU basis. This SKU-specific analysis provides granular insights into how each product responds to price changes. The results are not aggregated across regions or warehouses, allowing for more tailored pricing strategies.

## Detailed Explanation and Concerns

### Interpreting the Price Elasticity Coefficient

The price elasticity coefficient measures how sensitive the quantity demanded of a product is to changes in its price:

- **Elastic Demand** (\(\beta_1 < -1\)): A 1% increase in price results in a more than 1% decrease in quantity demanded, potentially reducing revenue.
- **Inelastic Demand** (\(-1 < \beta_1 < 0\)): A 1% increase in price results in a less than 1% decrease in quantity demanded, often leading to increased revenue.
- **Unit Elasticity** (\(\beta_1 = -1\)): A 1% increase in price leads to a 1% decrease in quantity demanded, with no net change in revenue.
- **Positive Elasticity** (\(\beta_1 > 0\)): Indicates counterintuitive situations where demand increases with price. This could suggest the presence of Veblen goods or other market anomalies.

### Why Not Use Percent Changes Directly?

In standard linear regression, the coefficient \(\beta_1\) represents a unit change, not a percentage change. To interpret \(\beta_1\) as elasticity in a linear model, you would need to calculate:

\[
\text{Elasticity} = \beta_1 \times \frac{\bar{P}}{\bar{Q}}
\]

Where \(\bar{P}\) and \(\bar{Q}\) are the mean price and mean quantity. However, using a log-log model simplifies this by directly interpreting the regression coefficient as elasticity.

### Addressing Seasonality and Trend Concerns

Seasonality and trends can obscure the true relationship between price and demand. By adjusting for these factors, the calculation provides a clearer view of how price changes impact demand, leading to more accurate pricing decisions.

### Application and Use Cases

This approach is particularly useful for businesses needing to understand how different products respond to price changes. By calculating elasticity on a SKU basis, businesses can tailor their pricing strategies to individual products, maximizing revenue while maintaining market competitiveness.

## Handling Extreme Elasticity Values

### Identifying Extreme Values

Extreme elasticity values, whether very high (positive or negative) or close to zero, can arise due to various factors. It is essential to identify these values to ensure reliable and interpretable data.

### Validating Data

- **Check Data Quality**: Ensure the data is accurate and clean, with no errors or outliers that could distort the elasticity calculation.
- **Review Model Assumptions**: Verify that the model is correctly specified, with all relevant variables included.

### Managing Outliers

- **Capping**: Set thresholds for elasticity values to prevent outliers from skewing the analysis.
- **Winsorization**: Replace extreme values with boundary values to limit their impact.

### Robust Regression Techniques

- **Use Robust Regression**: Consider using robust regression methods to reduce the influence of outliers on the results.
- **Quantile Regression**: For frequent extreme values, quantile regression can provide a more complete view of elasticity.

### Contextual Interpretation

- **Understand Market Context**: Evaluate whether extreme elasticity values make sense within the specific market context.
- **Scenario Analysis**: Conduct scenario analyses to understand the implications of extreme elasticity values on business decisions.

## Conclusion

The price elasticity analysis outlined in this document provides a robust method for calculating elasticity after adjusting for seasonality and trends. By isolating the impact of price changes on demand, the analysis offers actionable insights for optimizing pricing strategies. The SKU-specific approach ensures that businesses can make informed decisions at a granular level, responding effectively to market dynamics and consumer behavior.
