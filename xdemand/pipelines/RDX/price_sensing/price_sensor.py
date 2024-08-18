from datetime import datetime, timedelta
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from common.local_constants import region_warehouse_codes
from config import price_sensing_settings as cf
from common.cache_manager_joblib import CacheManagerJoblib as CacheManager

class PriceSensor:
    def __init__(self, price_col: str = cf.price_col,
                 days_before: int = cf.days_before,
                 log_normal_regression: bool = cf.log_normal_regression):
        self.price_col = price_col
        self.cache_manager = CacheManager()
        self.days_before = days_before
        self.log_normal_regression = log_normal_regression
        self.logger = logging.getLogger(__name__)
    def process_reference_price(self):
        df_price_reference = self.cache_manager.query_price_reference()
        df_price_reference['warehouse_code'] = df_price_reference['region'].map(region_warehouse_codes)
        df_price_reference.drop(columns=['region'], inplace=True)
        return df_price_reference.groupby(['sku', 'warehouse_code']).agg({'price': 'mean'}).reset_index()

    def daily_sales_price_sensing_transform(self, df_dsa):
        df_dsa['date'] = pd.to_datetime(df_dsa['date'])
        df_dsa[self.price_col] = (df_dsa['revenue'] - df_dsa['promotional rebates']) / (df_dsa['quantity'] + 0.000001)
        return df_dsa

    def std_price_regression(self, df_dsa, compute_elasticity=True):
        target = cf.target
        regressor = self.price_col
        days_ago = datetime.today() - timedelta(days=self.days_before)
        df_filtered = df_dsa[df_dsa['date'] > days_ago]
        unique_skus = df_filtered['sku'].unique()
        all_regressions_list = []
        elasticity_results = []
        for sku in unique_skus:
            df_sku = df_filtered[df_filtered['sku'] == sku]
            unique_wh = df_sku['warehouse_code'].unique()
            for warehouse in unique_wh:
                try:
                    df_sku_wh = df_sku[df_sku['warehouse_code'] == warehouse].copy()
                    df_sku_wh.dropna(subset=[target, regressor], inplace=True)

                    mean_regresor = df_sku_wh[self.price_col].mean()
                    std_regresor = df_sku_wh[regressor].std()
                    lower_bound = mean_regresor - cf.regressor_lower_bound * std_regresor
                    upper_bound = max(mean_regresor + cf.regressor_upper_bound * std_regresor, 0)
                    X = np.linspace(lower_bound, upper_bound, 100)[::-1].reshape(-1, 1)

                    target_col = df_sku_wh[target]
                    mean_target = target_col.mean()
                    std_target = target_col.std()
                    lower_bound = mean_target - cf.target_lower_bound * std_target
                    upper_bound = max(mean_target + cf.target_lower_bound * std_target, 0)
                    y = np.linspace(lower_bound, upper_bound, 100).reshape(-1, 1)
                    small_positive_number = 1e-10
                    y = np.where((y > 0) & (~np.isnan(y)), y, small_positive_number)
                    y = np.log(y) if self.log_normal_regression else y

                    model = LinearRegression()
                    model.fit(X, y)
                    X_pred = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
                    y_pred = model.predict(X_pred)
                    y_pred = np.where((y_pred > 0) & (~np.isnan(y_pred)), y_pred, small_positive_number)
                    y_pred = np.exp(y_pred) if self.log_normal_regression else y_pred

                    for id, x_val, y_val in zip(range(100), X_pred, y_pred):
                        all_regressions_list.append({
                            'idx': id, 'sku': sku, 'warehouse_code': warehouse,
                            'x_pred': x_val.item(), 'y_pred': y_val.item()
                        })
                    if not compute_elasticity:
                        continue
                    # Calculate elasticity at the mean price and mean quantity
                    beta_1 = model.coef_[0]
                    mean_price = X.mean()
                    mean_quantity = y.mean()
                    elasticity = beta_1 * (mean_price / mean_quantity)
                    # Store the SKU, warehouse code, and the calculated elasticity
                    elasticity_results.append(
                        {'sku': sku, 'warehouse_code': warehouse, 'price_elasticity': elasticity})
                except Exception as e:
                    self.logger.info(f"Data not available for sku {sku} and warehouse {warehouse}: {e}")
                    continue

        all_regressions = pd.DataFrame(all_regressions_list)
        all_regressions['measure_sense'] = target
        all_regressions['type_sense'] = regressor
        all_regressions['last_data_seen'] = df_filtered['date'].max()
        all_regressions['log_normal_regression'] = self.log_normal_regression
        return all_regressions, pd.DataFrame(elasticity_results)
