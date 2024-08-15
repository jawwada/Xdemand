import pandas as pd
from xiom_optimized.utils.data_fetcher import ph_data

def filter_data(filter_state, selected_channel=None,selected_warehouse=None,
                selected_region=None, selected_category=None,
                selected_subcategory=None, selected_group1=None, selected_group2=None):

    mask = pd.Series([True] * len(filter_state))
    filter_state.index = filter_state.index.astype(int)

    if selected_channel:
        mask &= (filter_state['channel'] == selected_channel)
    if selected_warehouse:
        mask &= (filter_state['warehouse_code'] == selected_warehouse)
    if selected_region:
        mask &= (filter_state['region'] == selected_region)
    if selected_category:
        mask &= (filter_state['level_1'] == selected_category)
    if selected_subcategory:
        mask &= (filter_state['level_2'] == selected_subcategory)
    if selected_group1:
        mask &= (filter_state['level_3'] == selected_group1)
    if selected_group2:
        mask &= (filter_state['level_4'] == selected_group2)
    return ph_data[mask].to_json(date_format='iso', orient='split')


def get_unique_values(column_name):
    return ph_data[column_name].unique().tolist()


def format_sql_values(values):
    if len(values) == 1:
        return f"('{values[0]}')"
    else:
        return str(tuple(values))
def format_sql_values(values):
    if len(values) == 1:
        return f"('{values[0]}')"
    else:
        return str(tuple(values))


