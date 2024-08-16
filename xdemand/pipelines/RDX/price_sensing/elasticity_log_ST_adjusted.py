import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.seasonal import seasonal_decompose


def decompose_and_adjust(group, quantity_col='quantity'):
    # Decompose the time series for quantity
    decomposition = seasonal_decompose(group[quantity_col], model='multiplicative', period=7,
                                       extrapolate_trend='freq')

    # Extract the trend and seasonal components
    trend = decomposition.trend
    seasonal = decomposition.seasonal

    # Adjust the quantity by removing both trend and seasonality
    group['Seasonally_Trend_Adjusted_Quantity'] = group[quantity_col] / (trend * seasonal)

    # Handle missing values after decomposition
    group['Seasonally_Trend_Adjusted_Quantity'].fillna(method='bfill', inplace=True)
    group['Seasonally_Trend_Adjusted_Quantity'].fillna(method='ffill', inplace=True)

    return group


def get_price_elasticity(df_dsa, date_col='date'):
    # Ensure the date column is in datetime format
    df_dsa[date_col] = pd.to_datetime(df_dsa[date_col])

    # Sort data by date
    df_dsa = df_dsa.sort_values(by=[date_col])

    # remove may through august
    df_dsa['month'] = df_dsa[date_col].dt.month
    df_dsa = df_dsa[(df_dsa['month'] < 5) | (df_dsa['month'] > 8)]
    # To store the results
    elasticity_results = []

    # Apply the decomposition and adjustment by SKU, region, and channel
    df_dsa = df_dsa.groupby(['sku', 'warehouse_code', 'channel']).apply(decompose_and_adjust).reset_index(drop=True)

    # Calculate elasticity for each SKU and warehouse
    for (sku, warehouse_code), group in df_dsa.groupby(['sku', 'warehouse_code']):
        # Prepare the data for the linear regression model
        X = group[['price']]
        # y = group['Seasonally_Trend_Adjusted_Quantity']
        y = np.log(group['quantity'] + 1)

        # Fit the linear regression model
        model = LinearRegression()
        model.fit(X, y)

        # Coefficient from the regression model
        beta_1 = model.coef_[0]

        # Calculate elasticity at the mean price and mean adjusted quantity
        mean_price = group['price'].mean()
        mean_quantity = group['Seasonally_Trend_Adjusted_Quantity'].mean()
        elasticity = beta_1 * (mean_price / mean_quantity)
        # Store the SKU, warehouse code, and the calculated elasticity
        elasticity_results.append({'sku': sku, 'warehouse_code': warehouse_code, 'price_elasticity': elasticity})

    # Convert the results into a DataFrame
    reg_coef_df = pd.DataFrame(elasticity_results)
    return reg_coef_df
