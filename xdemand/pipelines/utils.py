def filter_top_n(sales_df, top_n):
    # Group by 'sku' and sum the 'quantity'
    grouped = sales_df.groupby('sku')['revenue'].sum()
    # Sort the summed quantities in descending order and take the top N
    top_products = grouped.sort_values(ascending=False).head(top_n)

    # Filter the original DataFrame for only the top N SKUs
    sales_df = sales_df[sales_df['sku'].isin(top_products.index)]
    return sales_df
