DROP VIEW IF EXISTS agg_im_sku_daily_sales;
GO

CREATE VIEW agg_im_sku_daily_sales AS
SELECT
    CONVERT(date, [date]) AS [date],  -- Convert datetime to date
    sku,
    region,
    channel,
    SUM([Promotional_Rebates]) AS [promotional rebates],
    SUM([quantity]) AS [quantity],
    SUM(revenue) AS [revenue],
    SUM(revenue)/NULLIF(SUM(quantity), 0) AS [price] -- Handle division by zero
FROM [dbo].[tr_im_sku_sales_table]
GROUP BY CONVERT(date, [date]), sku, channel, region;
GO


Drop VIEW if exists product_hierarchy_sales_ui;
GO
CREATE VIEW product_hierarchy_sales_ui AS
SELECT t.[im_sku] as sku
      ,t.[level_1]
      ,t.[level_2]
      ,t.[level_3]
      ,t.[level_4]
      ,t.[level_5]
      ,t.[channel]
      ,t.[region]
      ,SUM(CASE WHEN s.[date] >= DATEADD(MONTH, -3, GETDATE()) THEN s.[revenue] ELSE 0 END) AS sum_sales_3_months
      ,SUM(CASE WHEN s.[date] >= DATEADD(MONTH, -12, GETDATE()) THEN s.[revenue] ELSE 0 END) AS sum_sales_1_year
      ,SUM(CASE WHEN s.[date] >= DATEADD(MONTH, -3, GETDATE()) THEN s.[quantity] ELSE 0 END) AS orders_3_months
      ,SUM(CASE WHEN s.[date] >= DATEADD(MONTH, -12, GETDATE()) THEN s.[quantity] ELSE 0 END) AS orders_1_year
FROM [dbo].[look_product_hierarchy] t
LEFT JOIN [dbo].[agg_im_sku_daily_sales] s ON t.im_sku = s.sku
GROUP BY sku,t.[im_sku]
        ,t.[level_1]
        ,t.[level_2]
        ,t.[level_3]
        ,t.[level_4]
        ,t.[level_5]
        ,t.[channel]
        ,t.[region] ;
GO
DROP VIEW IF EXISTS sku_daily_aggregation_sales_ui;
GO
DROP VIEW IF EXISTS sku_weekly_aggregation_sales_ui;
GO
DROP VIEW IF EXISTS sku_monthly_aggregation_sales_ui;

GO
CREATE VIEW agg_im_sku_weekly_sales AS
SELECT
    DATEADD(week, DATEDIFF(week, 0, [date]), 0) AS [date], -- Get the Monday of the week to which the date belongs
    sku,
    region,
    channel,
    SUM([promotional rebates]) AS [promotional rebates],
    SUM([quantity]) AS [quantity],
    SUM(revenue) AS [revenue],
    SUM(revenue)/NULLIF(SUM(quantity), 0) AS [price] -- Use NULLIF to avoid division by zero
FROM [dbo].[agg_im_sku_daily_sales]
WHERE [date] >= DATEADD(WEEK, -156, GETDATE())
GROUP BY DATEADD(week, DATEDIFF(week, 0, [date]), 0), sku, channel, region;

GO


CREATE VIEW agg_im_sku_monthly_sales AS
SELECT DATEFROMPARTS(YEAR([date]), MONTH([date]), 1) AS [date],
    sku,
    region,
    channel,
    SUM([promotional rebates]) AS [promotional rebates],
    SUM([quantity]) AS [quantity],
    SUM(revenue) AS [revenue],
    SUM(revenue)/NULLIF(SUM(quantity), 0) AS [price] -- Use NULLIF to avoid division by zero
FROM [dbo].[agg_im_sku_daily_sales]
WHERE [date] >= DATEADD(YEAR, -3, GETDATE())
GROUP BY [sku], DATEFROMPARTS(YEAR([date]), MONTH([date]), 1), region, channel;


GO
Drop View if exists stat_forecast_quantity_revenue;
Go

Create View stat_forecast_quantity_revenue as
SELECT
    q.sku,
    q.region as region,
    q.warehouse_code as warehouse_code,
    q.ds,
    q.yhat AS quantity,
    q.yhat_upper AS q_upper,
    q.yhat_lower AS q_lower,
    q.trend as q_trend,
    q.weekly AS q_weekly,
    q.yearly AS q_yearly,
    r.yhat AS revenue,
    r.yhat_upper AS r_upper,
    r.yhat_lower AS r_lower,
    r.trend as r_trend,
    r.weekly AS r_weekly,
    r.yearly AS r_yearly
FROM [dbo].[stat_forecast_data_quantity] q
INNER JOIN [dbo].[stat_forecast_data_revenue] r
    ON q.ds = r.ds
    AND q.sku = r.sku
    AND q.region = r.region;


GO
Drop View if exists stat_weekly_forecast_quantity_revenue;

GO
CREATE VIEW stat_weekly_forecast_quantity_revenue AS
SELECT
    sku,
    region,
    warehouse,
    DATEADD(week, DATEDIFF(week, 0, ds), 0) AS ds, -- Calculate the start of the week and name it 'ds'
    SUM(quantity) AS quantity,
    SUM(q_upper) AS q_upper,
    SUM(q_lower) AS q_lower,

    SUM(revenue) AS revenue,
    SUM(r_upper) AS r_upper,
    SUM(r_lower) AS r_lower
FROM [dbo].[stat_forecast_quantity_revenue]
GROUP BY sku, region, warehouse, DATEADD(week, DATEDIFF(week, 0, ds), 0);

GO
Drop View if exists stat_running_stock_forecast;
GO

CREATE VIEW stat_weekly_running_stock_forecast AS
SELECT
    sku,
    DATEADD(week, DATEDIFF(week, 0, ds), 0) AS ds, -- Start of the week for ds
    warehouse_code,
    SUM(yhat) AS yhat,
    Min(running_stock_after_forecast) AS running_stock_after_forecast,
    Min(DATEADD(week, DATEDIFF(week, 0, Expected_Arrival_Date), 0)) AS Expected_Arrival_Date, -- Start of the week for Expected_Arrival_Date
    SUM(InTransit_Quantity) AS InTransit_Quantity,
    MIN(status_date) AS status_date -- or MAX(status_date)
FROM [dbo].[stat_running_stock_forecast]
GROUP BY sku, warehouse_code, DATEADD(week, DATEDIFF(week, 0, ds), 0);
