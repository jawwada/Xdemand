SELECT *, yhat/1.2 from [stat_running_stock_forecast] where sku = 'WAN-W1B+' and warehouse_code='DE';
select ds, sku, warehouse_code, sum(quantity) as sum_yhat, sum(q_trend) as sum_trend from stat_forecast_quantity_revenue 
where ds>='2024-08-10 00:00:00.000' and sku = 'WAN-W1B+' and warehouse_code='DE' GROUP by ds, sku,warehouse_code;
SELECT sku, warehouse_code, avg(yhat) as avg_yhat, avg(trend) as avg_trend from [stat_running_stock_forecast] 
where sku = 'WAN-W1B+' and warehouse_code='DE' and ds>='2024-08-10 00:00:00.000' group by sku, warehouse_code;