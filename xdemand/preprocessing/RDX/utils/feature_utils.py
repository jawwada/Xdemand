import multiprocessing
from datetime import datetime
import holidays
import holidays.countries
import numpy as np
import pandas as pd
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from sklearn.preprocessing import StandardScaler

def get_temporal_features(df_daily_sales,lag_columns,freq,lag_periods,countries):
    # add temporal and lag features
    # temporal features: day of week, day of month, day of year, week of year, month, year
    # lag features: lag of quantity and price
    # holidays: before and after
    df_daily_sales=create_temporal_features(df_daily_sales)

    df_holidays=get_df_holidays(countries)
    holiday_featured_dates=create_holiday_features(df_holidays)
    df_daily_sales_hf=pd.merge(df_daily_sales,holiday_featured_dates, on='date',how='left')
    return df_daily_sales_hf
def get_temporal_lag_features(df_daily_sales, lag_columns, freq, lag_periods, countries):

    df_lag_periods_agg=pd.DataFrame()
    lag_agg_columns=lag_columns+['sku','date']
    df_lag_periods_agg=get_lag_periods_aggregates(df_daily_sales[lag_agg_columns],  freq, lag_periods)
    print(df_lag_periods_agg.columns)
    df_lag_periods_agg.drop(columns=lag_columns,inplace=True)
    df_daily_sales=df_daily_sales_hf.merge(df_lag_periods_agg,on=['sku','date'],how='left').fillna(0)

    return df_daily_sales

def create_holiday_features(df_holidays):
    # Assuming df_holidays.index is a DateTimeIndex
    min_date = df_holidays.index.min()
    max_date = df_holidays.index.max()

    # Generate date range
    dates = pd.date_range(start=min_date, end=max_date, freq='D')
    result_df = pd.DataFrame(pd.to_datetime(dates))
    result_df.columns = ['date']  # Add column name to result_df for clarity


    for index, row in result_df.iterrows():
        # Find the closest future holiday
        closest_holiday_top = df_holidays[df_holidays['date'] >= row['date']]['date'].min()
        closest_holiday_below = df_holidays[df_holidays['date'] <= row['date']]['date'].max()
        result_df.loc[index, 'before_next_holiday'] = (closest_holiday_top - row['date']).days
        result_df.loc[index, 'after_previous_holiday'] = (row['date'] - closest_holiday_below).days
    return result_df

def get_lag_periods_aggregates(df, freq,periods):
    df = df.set_index('date')
    print(df)
    df = df.groupby('sku').resample(freq).sum()
    # Set a new multi-index on sku and date
    #df.set_index([sku, 'date'], inplace=True)
    # Get a new index that includes all combinations of SKU and date
    min_date=df.index.get_level_values(1).min()
    max_date=df.index.get_level_values(1).max()
    new_index = pd.MultiIndex.from_product([df.index.get_level_values(0).unique(),
                                            pd.date_range(start=min_date, end=max_date, freq=freq)],
                                           names=['sku', 'date'])
    

    # Reindex the dataframe with the new index
    columns=df.columns
    df = df.reindex(new_index)
    
    # Reset index
    df.reset_index(inplace=True)
    
    df = df.sort_values(['sku', 'date'])

    # Create lagged variables
    for column in columns:
        for i in range(1, 1+periods):  # for 3 previous periods
            df[f'{column}_prev_{i}_{freq}'] = df.groupby('sku')[column].shift(i)
    #df=df.reset_index().drop(freq)
    return df

def create_temporal_features(tmp_df,date_col='date'):
    country_holidays = holidays.UK(years=[2020,2021,2022,2023])
    ser_tm = tmp_df[date_col].dt
    tmp_df["day_of_week"] = ser_tm.dayofweek
    tmp_df["month"] = ser_tm.month
    tmp_df["season"] = ((ser_tm.month % 12 + 3) // 3) - 1
    tmp_df["year"] = ser_tm.year
    tmp_df['week'] = ser_tm.isocalendar().week
    del ser_tm
    tmp_df["is_holiday"] = tmp_df[date_col].map(lambda x: int(x in country_holidays))
    tmp_df["is_work_day"] = abs(1 - ((tmp_df["day_of_week"] == 6) | (
    tmp_df["day_of_week"] == 5) | (tmp_df["day_of_week"] == 1)).astype(int))
    return tmp_df

def create_correlation_embeddings(df):
    df_pivot = df.pivot(index='sku', columns='date', values='quantity').fillna(0)
    
    df_corr = df_pivot.corr().fillna(0.0)

    u,sigma,v = np.linalg.svd(df_corr.values, full_matrices=True)
    
    embedding = u[:, :20]*sigma[:20]
    
    df_embedding = pd.DataFrame(embedding, index=df_corr.index)
    df_embedding.columns = [str(colname) for colname in df_embedding.columns]

    return df_embedding


def create_dtw_svd_embeddings(df, svd_cut_dtw=20):
    df_pivot = df.pivot(index='sku', columns='date', values='quantity').fillna(0)

    scaler = StandardScaler()
    normalized_data = scaler.fit_transform(df_pivot.values)

    normalized_df = pd.DataFrame(normalized_data, index=df_pivot.index, columns=df_pivot.columns)

    sku_list = normalized_df.columns.tolist()
    dtw_sim_matrix = np.empty((len(sku_list),len(sku_list),))

    def dtw_wrapper(xx):
        try:
            dist_temp = (xx[0], xx[1], fastdtw(xx[2], xx[3], dist=euclidean)[0])
        except:
            print("Exception")
            dist_temp=(xx[0], xx[1], 25)
        return dist_temp

    dtw_result_list = []
    pool = multiprocessing.Pool(processes=4)  # you might want to change the number of processes based on your machine
    for idx, sku1 in enumerate(sku_list):
        values_in = normalized_df[sku1].values
        payload = [(idx, idx + idy_add, normalized_df[sku2].values, values_in) for idy_add, sku2 in enumerate(sku_list[idx:])]
        dtw_result_list += pool.map(dtw_wrapper, payload)

    pool.close()
    pool.join()

    dtw_result_arr = np.array(dtw_result_list)
    x_coord = dtw_result_arr[:,0].astype(int)
    y_coord = dtw_result_arr[:,1].astype(int)
    dtw_sim_matrix[x_coord, y_coord] = dtw_result_arr[:,2]
    dtw_sim_matrix[y_coord, x_coord] = dtw_result_arr[:,2]

    u, s, vh = np.linalg.svd(dtw_sim_matrix, full_matrices=True)
    dtw_sim_mat_reduced = u[:,:svd_cut_dtw]*s[:svd_cut_dtw]

    df_dtw_red = pd.DataFrame(dtw_sim_mat_reduced, index=sku_list)
    df_dtw_red.columns = [str(col_name) for col_name in df_dtw_red.columns]

    return df_dtw_red

def get_df_holidays(countries):
    # Get all classes in the holidays.countries module
    #countries = ['AU', 'CA', 'DE', 'ES', 'FR', 'CA', 'IT', 'NL', 'UK', 'USA']
    countries = [ 'UK']
    # Loop through the classes
    current_year = datetime.now().year
        
    # Create an empty DataFrame
    df_holidays = pd.DataFrame()
    
    # Loop through the countries
    for country in countries:
        # Perform your desired operations for each country
        # For example, you can get the holidays for each country using the holidays package
        country_holidays = holidays.CountryHoliday(country=country, years=range(current_year - 5, current_year + 2))
        country_holidays_df = pd.DataFrame.from_dict(country_holidays, orient='index',columns=['holiday'])
       # Append to the main DataFrame
        country_holidays_df['country']=country
        country_holidays_df['date']=pd.to_datetime(country_holidays_df.index)
        df_holidays = pd.concat([df_holidays ,country_holidays_df])
    return df_holidays

def get_weather_data(weather_cols,weather_country='UK',weather_city='Londdon'):
    weather_data = pd.read_csv(f"data/input/weather/{weather_country}/{weather_city}/london 2020-10-01 to 2023-06-03.csv")
    weather_data['date'] = pd.to_datetime(weather_data['datetime'])
    weather_data = weather_data[weather_cols]
    return weather_data

