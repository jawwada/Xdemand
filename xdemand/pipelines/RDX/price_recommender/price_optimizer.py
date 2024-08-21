import pandas as pd
from dynaconf import Dynaconf

from xdemand.pipelines.RDX.price_recommender.optuna_optimizer import optuna_optimizer
from xdemand.pipelines.RDX.price_recommender.pr_utils import get_price_adjustments


def price_optimizer(df_price_recommender, cf: Dynaconf):
    # Create new Data Frames to store the results
    price_adjustments = pd.DataFrame()
    df_sku_warehouse_info = pd.DataFrame()
    df_price_recommender['q_prime'] = 0.0

    grouper = df_price_recommender.groupby(['sku', 'warehouse_code'])
    for name, group in grouper:

        p0 = group['ref_price'].mean()  # Reference price
        r = group['price_elasticity'].mean()  # Price elasticity
        # Optimize the objective function
        price_rec = optuna_optimizer(name, group, p0, r, cf)
        # q_prime is the adjusted demand after we change the price ['q_prime']= ['yhat'] * (price_prime / p0) ** r
        group, df_group_info = get_price_adjustments(name, group, p0, price_rec, r, cf)
        if price_adjustments.empty:
            price_adjustments = group
            df_sku_warehouse_info = df_group_info
        else:
            price_adjustments = pd.concat([price_adjustments, group])
            df_sku_warehouse_info = pd.concat([df_sku_warehouse_info, df_group_info])
    print(df_sku_warehouse_info.columns)
    return price_adjustments, df_sku_warehouse_info
