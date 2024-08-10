Drop table if exists tr_im_sku_sales_table;

-- Temporary table to hold combined sales data
CREATE TABLE temp_combined_sales_data
(
    date DATETIME,
    sku VARCHAR(255),
    marketplace VARCHAR(255),
    quantity INT,
    channel VARCHAR(255),
    region VARCHAR(255),
    revenue FLOAT,
    promotional_rebates Float
);

-- Variable to hold the name of the current marketplace sales table
DECLARE @marketplace_sales_table NVARCHAR(255);
DECLARE @sql NVARCHAR(MAX);

-- Cursor to iterate over each company's marketplace sales table
DECLARE company_cursor CURSOR FOR
    SELECT DISTINCT marketplace_sales_table
    FROM look_product_hierarchy;

OPEN company_cursor;
FETCH NEXT FROM company_cursor INTO @marketplace_sales_table;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- Dynamic SQL to perform the join and aggregation for each marketplace sales table

SET @sql = N'
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
        ' + QUOTENAME(@marketplace_sales_table) + N' as asr
    JOIN
        look_product_hierarchy as lph ON asr.sku = lph.marketplace_sku
    WHERE
        asr.quantity > 0
        AND asr.[type] = ''Order''
    ORDER BY
        asr.[CLEAN_DateTime],
        lph.im_sku
';

    -- Execute the dynamic SQL
    EXEC sp_executesql @sql;

    FETCH NEXT FROM company_cursor INTO @marketplace_sales_table;
END

CLOSE company_cursor;
DEALLOCATE company_cursor;


-- Create final table and insert data from the temporary table
SELECT * INTO tr_im_sku_sales_table FROM temp_combined_sales_data;

-- Drop the temporary table
DROP TABLE temp_combined_sales_data;

PRINT 'Data aggregation complete. Saved to tr_im_sku_sales_table.';