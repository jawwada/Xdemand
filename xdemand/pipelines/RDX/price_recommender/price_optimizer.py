import pandas as pd
from dynaconf import Dynaconf
from xdemand.pipelines.RDX.price_recommender.optuna_optimizer import optuna_optimizer
from xdemand.pipelines.RDX.price_recommender.pr_utils import calculate_adjusted_price_stock


def price_optimizer(df_price_recommender, cf:Dynaconf):
    # Create new Data Frames to store the results
    price_adjustments = pd.DataFrame()
    df_sku_warehouse_info = pd.DataFrame()
    df_price_recommender['q_prime'] = 0.0

    grouper = df_price_recommender.groupby(['sku', 'warehouse_code'])
    for name, group in grouper:
        group_info = dict({
            'sku': name[0],
            'warehouse_code': name[1],
            'ref_price': group['ref_price'].mean(),
            'mean_demand': group['yhat'].mean(),
            'current_stock': group['running_stock_after_forecast'].head(1).item(),
            'understock_days': group['is_understock'].sum(),
            'overstock_days': group['is_overstock'].sum(),
            'price_elasticity': group['price_elasticity'].mean()
        })

        p0= group_info['ref_price'] # Reference price
        r = group_info['price_elasticity'] # Price elasticity
        # Optimize the objective function
        price_rec = optuna_optimizer(name,group, p0, r,cf)
        # q_prime is the adjusted demand after we change the price ['q_prime']= ['yhat'] * (price_prime / p0) ** r
        group['q_prime'] = group['yhat'] * (price_rec/ p0) ** r
        group = calculate_adjusted_price_stock(group)
        group['y_hat_adj'] = group['yhat'].where(group['yhat'] < group['running_stock_after_forecast'], 0)
        group['q_prime_adj'] = group['q_prime'].where(group['q_prime'] < group['running_stock_after_forecast_adj'], 0)
        revenue_before = group['y_hat_adj'].sum() * p0
        revenue_after = group['q_prime_adj'].sum() * price_rec
        # set up the df_sku_warehouse_info

        # Add new columns to the aggregated DataFrame
        group_info['revenue_before'] = revenue_before
        group_info['revenue_after'] = revenue_after
        group_info['price_new'] = price_rec
        group_info['price_old'] = p0
        group_info['opt_stock_level'] = group_info['mean_demand'] * cf.forecast_stock_level
        df_group_info = pd.DataFrame(group_info, index=[0])
        print(revenue_before, revenue_after)
        if price_adjustments.empty:
            price_adjustments = group
            df_sku_warehouse_info = df_group_info

        else:
            price_adjustments = pd.concat([price_adjustments, group])
            df_sku_warehouse_info = pd.concat([df_sku_warehouse_info, df_group_info])
    print(df_sku_warehouse_info.columns)
    return price_adjustments, df_sku_warehouse_info

