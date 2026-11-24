-- =============================================================================
-- Retail Sales Star Schema ETL Load Script (DuckDB)
-- Author: Rajath Gadagkar
-- Description: Extracts raw retail CSV files, denormalizes product hierarchy
--              (products + brands + categories), generates the DimDate calendar
--              dimension, and loads FactSales with computed net & discount revenue.
-- Usage: Run with working directory set to data/retail/ (or via src.warehouse.runner)
-- =============================================================================

-- 1. Load DimCustomer
INSERT INTO DimCustomer
SELECT
    customer_id AS customer_key,
    customer_id,
    first_name,
    last_name,
    city,
    state
FROM read_csv_auto('customers.csv');

-- 2. Load DimStore
INSERT INTO DimStore
SELECT
    store_id AS store_key,
    store_id,
    store_name,
    city,
    state
FROM read_csv_auto('stores.csv');

-- 3. Load DimStaff
INSERT INTO DimStaff
SELECT
    staff_id AS staff_key,
    staff_id,
    first_name,
    last_name
FROM read_csv_auto('staffs.csv');

-- 4. Load DimProduct (Denormalized join of products, brands, and categories)
INSERT INTO DimProduct
SELECT
    p.product_id AS product_key,
    p.product_id,
    p.product_name,
    b.brand_name,
    c.category_name,
    p.model_year,
    p.list_price
FROM read_csv_auto('products.csv') p
JOIN read_csv_auto('brands.csv') b ON p.brand_id = b.brand_id
JOIN read_csv_auto('categories.csv') c ON p.category_id = c.category_id;

-- 5. Generate and Load DimDate (2016-01-01 through 2018-12-31)
INSERT INTO DimDate
SELECT
    CAST(strftime(d, '%Y%m%d') AS INT) AS date_key,
    d AS full_date,
    EXTRACT(year FROM d) AS year,
    EXTRACT(quarter FROM d) AS quarter,
    EXTRACT(month FROM d) AS month,
    strftime(d, '%B') AS month_name,
    EXTRACT(day FROM d) AS day,
    strftime(d, '%A') AS day_of_week
FROM (
    SELECT CAST(generate_series AS DATE) AS d
    FROM generate_series(CAST('2016-01-01' AS DATE), CAST('2018-12-31' AS DATE), INTERVAL 1 DAY)
) AS dates;

-- 6. Load FactSales (Joining order_items with orders and calculating net/discount amounts)
INSERT INTO FactSales
SELECT
    oi.order_id,
    oi.item_id AS order_item_id,
    CAST(strftime(CAST(o.order_date AS DATE), '%Y%m%d') AS INT) AS date_key,
    o.customer_id AS customer_key,
    o.store_id AS store_key,
    o.staff_id AS staff_key,
    oi.product_id AS product_key,
    oi.quantity,
    ROUND(oi.quantity * oi.list_price * (1 - oi.discount), 2) AS sale_amount,
    ROUND(oi.quantity * oi.list_price * oi.discount, 2) AS discount_amount
FROM read_csv_auto('order_items.csv') oi
JOIN read_csv_auto('orders.csv') o ON oi.order_id = o.order_id;
