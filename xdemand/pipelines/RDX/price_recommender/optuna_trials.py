import numpy as np
import optuna
import pandas as pd

from config import price_recommendation_settings as cf


def calculate_adjusted_price_stock(df):
    df['running_stock_after_forecast_adj'] = 0.0
    running_stock = 0.0

    # Loop through the DataFrame
    for index, row in df.iterrows():
        # Update running stock
        if index == df.first_valid_index():
            running_stock = row['running_stock_after_forecast'] + row['InTransit_Quantity']
        else:
            running_stock += row['InTransit_Quantity']

        predicted_sales = row['q_prime']

        if running_stock < predicted_sales:
            # If total stock is less than predicted sales, no sales occur
            df.at[index, 'running_stock_after_forecast_adj'] = 0.0
            running_stock = 0.0
        else:
            # Sales occur as predicted
            df.at[index, 'running_stock_after_forecast_adj'] = running_stock - predicted_sales
            running_stock -= predicted_sales

    return df


def optune_run_trials(df_price_recommender, df_sku_info, n_trials):
    # Create a new DataFrame to store the results
    df_sku_warehouse = df_sku_info.reset_index()
    all_adjustments = pd.DataFrame()
    df_price_recommender['q_prime'] = 0.0

    # optuna_storage = f"mssql+pyodbc:///?odbc_connect={optuna_db_params}"
    optuna_storage = "sqlite:///optuna_study.db"
    grouper = df_price_recommender.groupby(['sku', 'warehouse_code'])

    for name, group in grouper:
        sku = name[0]
        warehouse_code = name[1]
        study_name = f"{sku}_{warehouse_code}"  # Create a unique study name
        try:
            optuna.delete_study(study_name=study_name, storage=optuna_storage)
        except:
            pass
        study = optuna.create_study(study_name=study_name, storage=optuna_storage, direction='minimize')

        print(group.head())
        s_opt = df_sku_warehouse.loc[(df_sku_warehouse['sku'] == name[0]) & \
                                     (df_sku_warehouse['warehouse_code'] == name[1])]['opt_stock_level'].values[0]
        print(name)
        p0 = \
            df_sku_warehouse.loc[
                (df_sku_warehouse['sku'] == name[0]) & (df_sku_warehouse['warehouse_code'] == name[1])][
                'ref_price'].values[0]
        r = \
            df_sku_warehouse.loc[
                (df_sku_warehouse['sku'] == name[0]) & (df_sku_warehouse['warehouse_code'] == name[1])][
                'price_elasticity']. \
                values[0]  # Price elasticity
        avg_yhat = group['yhat'].mean()
        print(s_opt, p0, r, avg_yhat)
        # Optimize the objective function
        # put in try except block
        try:
            study.optimize(lambda trial: objective(trial, group, p0, r),
                           n_trials=n_trials)
            print('Best trial parameters:', study.best_trial.params)
            print('Best objective value:', study.best_trial.value)
            # compute revenue before and after
            # q_prime is the adjusted demand after we change the price ['q_prime']= ['yhat'] * (price_prime / p0) ** r
            group['q_prime'] = group['yhat'] * (price_rec / p0) ** r
            group = calculate_adjusted_price_stock(group)
            group['y_hat_adj'] = group['yhat'].where(group['yhat'] < group['running_stock_after_forecast'], 0)
            group['q_prime_adj'] = group['q_prime'].where(group['q_prime'] < group['running_stock_after_forecast_adj'],
                                                          0)

            revenue_before = group['y_hat_adj'].sum() * p0
            revenue_after = group['q_prime_adj'].sum() * price_rec
            df_sku_info.loc[name, 'revenue_before'] = revenue_before
            df_sku_info.loc[name, 'revenue_after'] = revenue_after
            df_sku_info.loc[name, 'price_new'] = price_rec
            df_sku_info.loc[name, 'price_old'] = p0
            df_sku_info.loc[name, 's_opt'] = s_opt
            df_sku_info.loc[name, 'r'] = r
            df_sku_info.loc[name, 'avg_yhat'] = avg_yhat
            df_sku_info.loc[name, 'n_trials'] = n_trials
            print(revenue_before, revenue_after)
            if all_adjustments.empty:
                all_adjustments = group
            else:
                all_adjustments = pd.concat([all_adjustments, group])
        except Exception as e:
            print(f"Error in {name} : {e}")
            continue
    return all_adjustments, df_sku_info


def objective(trial, df, p0, r):
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
