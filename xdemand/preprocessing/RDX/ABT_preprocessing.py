from sklearn.model_selection import train_test_split
import pandas as pd


def make_test_train(df_dsa_abt_w_wos,target,sku=None, learning_type='regression',test_size=0.2):
    if sku is None:
        safe_sku = 'all'
    df_dsa_abt_w_full = df_dsa_abt_w_wos
    df_dsa_abt_w_full = df_dsa_abt_w_full.fillna(0)
    # Assuming df is your DataFrame and it is sorted by date
    df_dsa_abt_w_full_train = pd.DataFrame()
    df_dsa_abt_w_full_test = pd.DataFrame()
    if learning_type == 'regression':
        #df_dsa_abt_w_full = df_dsa_abt_w_full[df_dsa_abt_w_full[target] != 0]

        # Split the data with a 80:20 ratio
        df_dsa_abt_w_full_train, df_dsa_abt_w_full_test = train_test_split(df_dsa_abt_w_full, test_size=test_size)
    elif learning_type == 'forecasting':
        # Sort the data by date
        df_dsa_abt_w_full['new_date'] = df_dsa_abt_w_full['date']
        df_dsa_abt_w_full = df_dsa_abt_w_full.sort_values(by='new_date')
        # Determine the number of data points for the test set
        n_test = int(test_size * len(df_dsa_abt_w_full))
        # Determine the split_date
        split_date = df_dsa_abt_w_full.iloc[-n_test]['new_date']
        # Create the train and test sets
        df_dsa_abt_w_full_train = df_dsa_abt_w_full[df_dsa_abt_w_full['new_date'] < split_date]
        df_dsa_abt_w_full_test = df_dsa_abt_w_full[df_dsa_abt_w_full['new_date'] >= split_date]
        # Drop the date column
        df_dsa_abt_w_full_train = df_dsa_abt_w_full_train.drop('new_date', axis=1)
        df_dsa_abt_w_full_test = df_dsa_abt_w_full_test.drop('new_date', axis=1)

    if df_dsa_abt_w_full_train.shape[0] < 1:
        return

    x_train = df_dsa_abt_w_full_train.drop([target], axis=1, errors='ignore')
    y_train = pd.DataFrame(df_dsa_abt_w_full_train[target])
    y_train.columns = [target]

    x_test = df_dsa_abt_w_full_test.drop([target], axis=1, errors='ignore')
    y_test = pd.DataFrame(df_dsa_abt_w_full_test[target])
    y_test.columns = [target]

    return x_train, x_test, y_train, y_test
