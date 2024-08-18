import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.seasonal import seasonal_decompose
import logging
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class PriceElasticityCalculator:
    def __init__(self, date_col='date', quantity_col='quantity', price_col='price',
                 period=365, model='additive', remove_months=True,
                 remove_months_window=(5, 6, 7, 8)):
        self.date_col = date_col
        self.quantity_col = quantity_col
        self.price_col = price_col
        self.period = period
        self.model = model
        self.remove_months = remove_months
        self.remove_months_window = remove_months_window
        self.price_col = price_col

    def decompose_and_adjust(self, group):
        # Decompose the time series for quantity
        decomposition = seasonal_decompose(group[self.quantity_col], model=self.model, period=self.period,
                                           extrapolate_trend='freq')

        # Extract the trend and seasonal components
        trend = decomposition.trend
        seasonal = decomposition.seasonal
        if self.model == 'additive':
            group['Seasonally_Trend_Adjusted_Quantity'] = group[self.quantity_col] -  seasonal
        else:
            group['Seasonally_Trend_Adjusted_Quantity'] = group[self.quantity_col] / seasonal

        # Adjust the quantity by removing both trend and seasonality


        # Handle missing values after decomposition
        group['Seasonally_Trend_Adjusted_Quantity'].fillna(method='bfill', inplace=True)
        group['Seasonally_Trend_Adjusted_Quantity'].fillna(method='ffill', inplace=True)

        return group

    def get_price_elasticity(self, df_dsa, date_col='date', plot_parameters=False):
        # Ensure the date column is in datetime format
        df_dsa[date_col] = pd.to_datetime(df_dsa[date_col])

        # Sort data by date
        df_dsa = df_dsa.sort_values(by=[date_col])

        # Remove specified months if enabled
        if self.remove_months:
            df_dsa['month'] = df_dsa[date_col].dt.month
            df_dsa = df_dsa[~df_dsa['month'].isin(self.remove_months_window)]

        # To store the results
        elasticity_results = []
        try:
            # Apply the decomposition and adjustment by SKU, region, and channel
            df_dsa = df_dsa.groupby(['sku', 'warehouse_code']).apply(self.decompose_and_adjust).reset_index(drop=True)
        except Exception as e:
            logger.error(f"Error during decomposition: {e}")
            df_dsa['Seasonally_Trend_Adjusted_Quantity'] = df_dsa[self.quantity_col]

        # Calculate elasticity for each SKU and warehouse
        for (sku, warehouse_code), group in df_dsa.groupby(['sku', 'warehouse_code']):
            try:
                # Prepare the data for the linear regression model
                X = group[[self.price_col]]
                y = np.log(group['Seasonally_Trend_Adjusted_Quantity'] + 1)

                # Fit the linear regression model
                model = LinearRegression()
                model.fit(X, y)

                # Coefficient from the regression model
                beta_1 = model.coef_[0]

                # Calculate elasticity at the mean price and mean adjusted quantity
                mean_price = group[self.price_col].mean()
                mean_quantity = group['Seasonally_Trend_Adjusted_Quantity'].mean()
                elasticity = beta_1 * (mean_price / mean_quantity)
                logger.info(f"SKU {sku}, Warehouse {warehouse_code}: Price Elasticity = {elasticity}")
                # Store the SKU, warehouse code, and the calculated elasticity
                elasticity_results.append({'sku': sku, 'warehouse_code': warehouse_code, 'price_elasticity': elasticity})

                if plot_parameters:
                    self.plot_parameters(X, y, title=f"SKU {sku}, Warehouse {warehouse_code}")

            except Exception as e:
                logger.error(f"Error calculating elasticity for SKU {sku}, warehouse {warehouse_code}: {e}")

        # Convert the results into a DataFrame
        reg_coef_df = pd.DataFrame(elasticity_results)
        return reg_coef_df

    def plot_parameters(self, X, y, title='Price Elasticity Regression'):
        plt.figure(figsize=(12, 6))
        plt.plot(X,y, label='Quantity')
        plt.title(f"Price Elasticity Regression: {title}")
        plt.xlabel('Date')
        plt.ylabel('Quantity')
        plt.legend()
        plt.tight_layout()
        plt.show()