from common.db_connection import engine

def preprocess_marketplace_sales_to_im_sales():
    # Connect to the database
    with engine.connect() as connection:
        # Get a raw DBAPI connection
        raw_connection = connection.connection

        # Get a cursor
        cursor = raw_connection.cursor()

        # Drop the final table if it exists
        cursor.execute("DROP TABLE IF EXISTS tr_im_sku_sales_table")

        # Create the temporary table
        cursor.execute("""
        CREATE TABLE temp_combined_sales_data
        (
            date DATETIME,
            sku VARCHAR(255),
            marketplace VARCHAR(255),
            quantity INT,
            channel VARCHAR(255),
            region VARCHAR(255),
            revenue FLOAT,
            promotional_rebates FLOAT
        )
        """)

        # Fetch distinct marketplace sales tables
        cursor.execute("SELECT DISTINCT marketplace_sales_table FROM look_product_hierarchy")
        marketplace_sales_tables = cursor.fetchall()

        # Iterate over each marketplace sales table
        for row in marketplace_sales_tables:
            marketplace_sales_table = row[0]

            # Dynamic SQL to perform the join and aggregation
            sql = f"""
            INSERT INTO temp_combined_sales_data (date, sku, marketplace, quantity, channel, region, revenue, promotional_rebates)
            SELECT
                asr.CLEAN_DateTime as date,
                lph.im_sku as sku,
                lph.marketplace as marketplace,
                asr.quantity,
                asr.channel,
                asr.region,
                asr.total as revenue,
                asr.promotional_rebates
            FROM
                {marketplace_sales_table} as asr
            JOIN
                look_product_hierarchy as lph ON asr.sku = lph.marketplace_sku
            WHERE
                asr.quantity > 0
                AND asr.[type] = 'Order'
            ORDER BY
                asr.[CLEAN_DateTime],
                lph.im_sku
            """

            # Execute the dynamic SQL
            cursor.execute(sql)

        # Create the final table and insert data from the temporary table
        cursor.execute("SELECT * INTO tr_im_sku_sales_table FROM temp_combined_sales_data")

        # Drop the temporary table
        cursor.execute("DROP TABLE temp_combined_sales_data")

        # Commit the transaction
        raw_connection.commit()

        # Close the cursor
        cursor.close()

    print('Data aggregation complete. Saved to tr_im_sku_sales_table.')
    return True
