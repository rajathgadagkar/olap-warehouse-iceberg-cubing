-- =============================================================================
-- Business Insight Verification Queries (DuckDB)
-- Author: Rajath Gadagkar
-- Description: Validates headline KPIs, revenue concentration, category share,
--              brand dominance, and the April 2018 revenue anomaly.
-- =============================================================================

-- 1. Annual Revenue Summary (2016 - 2018)
SELECT
    d.year,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY d.year
ORDER BY d.year;

-- 2. Monthly Revenue Breakdown for 2018 (April Anomaly Inspection)
SELECT
    d.month,
    d.month_name,
    ROUND(SUM(fs.sale_amount), 2) AS monthly_revenue
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
WHERE d.year = 2018
GROUP BY d.month, d.month_name
ORDER BY d.month;

-- 3. Top 2 Product Categories and Share of Total Revenue
WITH CategorySales AS (
    SELECT
        p.category_name,
        SUM(fs.sale_amount) AS category_revenue
    FROM FactSales fs
    JOIN DimProduct p ON fs.product_key = p.product_key
    GROUP BY p.category_name
),
TotalSales AS (
    SELECT SUM(sale_amount) AS total_revenue FROM FactSales
)
SELECT
    cs.category_name,
    ROUND(cs.category_revenue, 2) AS category_revenue,
    ROUND((cs.category_revenue / ts.total_revenue) * 100, 2) AS percentage_of_total
FROM CategorySales cs, TotalSales ts
ORDER BY cs.category_revenue DESC
LIMIT 2;

-- 4a. Top Brands in Mountain Bikes & Road Bikes
SELECT
    p.brand_name,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
WHERE p.category_name IN ('Mountain Bikes', 'Road Bikes')
GROUP BY p.brand_name
ORDER BY total_revenue DESC
LIMIT 3;

-- 4b. Top Brands in Cruisers & Children Bicycles
SELECT
    p.brand_name,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
WHERE p.category_name IN ('Cruisers Bicycles', 'Children Bicycles')
GROUP BY p.brand_name
ORDER BY total_revenue DESC
LIMIT 3;

-- 5. Store Revenue Concentration
WITH StoreSales AS (
    SELECT
        s.store_name,
        SUM(fs.sale_amount) AS store_revenue
    FROM FactSales fs
    JOIN DimStore s ON fs.store_key = s.store_key
    GROUP BY s.store_name
),
TotalSales AS (
    SELECT SUM(sale_amount) AS total_revenue FROM FactSales
)
SELECT
    ss.store_name,
    ROUND(ss.store_revenue, 2) AS store_revenue,
    ROUND((ss.store_revenue / ts.total_revenue) * 100, 2) AS percentage_of_total
FROM StoreSales ss, TotalSales ts
ORDER BY ss.store_revenue DESC;

-- 6. Top Sales Staff Share of Total Revenue
WITH StaffSales AS (
    SELECT
        sf.first_name || ' ' || sf.last_name AS staff_name,
        SUM(fs.sale_amount) AS staff_revenue
    FROM FactSales fs
    JOIN DimStaff sf ON fs.staff_key = sf.staff_key
    GROUP BY staff_name
),
TotalSales AS (
    SELECT SUM(sale_amount) AS total_revenue FROM FactSales
)
SELECT
    ss.staff_name,
    ROUND(ss.staff_revenue, 2) AS staff_revenue,
    ROUND((ss.staff_revenue / ts.total_revenue) * 100, 2) AS percentage_of_total
FROM StaffSales ss, TotalSales ts
ORDER BY ss.staff_revenue DESC
LIMIT 3;
