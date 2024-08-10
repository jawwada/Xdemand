import numpy as np
import optuna
import pandas as pd
from dynaconf import Dynaconf
from xdemand.pipelines.RDX.price_recommender.pr_utils import calculate_adjusted_price_stock

def optuna_optimizer(name, group, p0, r, cf: Dynaconf):
    # at this point we have only one sku and warehouse
    sku= group['sku'].unique()
    warehouse_code = group['warehouse_code'].unique()
    study_name = f"{sku}_{warehouse_code}"
    #optuna_storage = f"mssql+pyodbc:///?odbc_connect={optuna_db_params}"
    optuna_storage = "sqlite:///optuna_study.db"
    try:
        optuna.delete_study(study_name=study_name, storage=optuna_storage)
    except:
        pass
    study = optuna.create_study(study_name=study_name, storage=optuna_storage, direction='minimize')
    n_trials= cf.n_trials
    try:
        study.optimize(lambda trial: objective(trial, group, p0, r, cf),
                       n_trials=n_trials)
        print('Best trial parameters:', study.best_trial.params)
        print('Best objective value:', study.best_trial.value)
    except Exception as e:
        print(f"Error in {name} : {e}")
    return study.best_trial.params['price']

def objective(trial, df, p0, r, cf):
    try:
        trial_df = df.copy(deep=True)
        trial_df = trial_df[trial_df['ds'] < trial_df['ds'].min() + pd.Timedelta(days=cf.forecast_stock_level)]

        price_prime = trial.suggest_float('price', cf.price_lower_bound * p0, cf.price_upper_bound * p0)
        # Calculate the new quantity (q_prime)
        # q_prime = yhat * (price_prime / p0) ** price_elasticity #chat gpt 4
        # Suggesting prices for each day within the allowed range
        trial_df['q_prime'] = trial_df['yhat'] * (price_prime / p0) ** r
        # Applying the calculate_stock function
        trial_df = calculate_adjusted_price_stock(trial_df)
        # Calculating the objective value: difference between
        trial_df['adjusted_revenue'] = trial_df['q_prime'] * price_prime
        in_stock_df = trial_df[trial_df['running_stock_after_forecast_adj'] > cf.opt_stock_level]
        objective_value = -in_stock_df['adjusted_revenue'].sum()
        # question how to incorporate the stock level
        # Define the stock penalty coefficient

        # Apply the penalty: count the number of stockout events and multiply by the penalty coefficient
        # Ensure that the boolean Series has the same index as the DataFrame
        # get the trail_df where date is less than min_date + cf.forecast_stock_level
        stockout_days = trial_df.loc[trial_df['running_stock_after_forecast_adj'] < cf.opt_stock_level].index
        if stockout_days.empty:
            stock_penalty = 0
        else:
            missing_revenue = trial_df.loc[stockout_days, 'yhat'].sum()
            stock_penalty = cf.stockout_penalty * len(stockout_days) + missing_revenue
        # Add the penalty to the objective value
        objective_value += stock_penalty
        return objective_value
    except Exception as e:
        print(f"Error in objective : {e}")
        return np.inf
