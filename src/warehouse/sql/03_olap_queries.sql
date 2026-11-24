-- =============================================================================
-- OLAP Analytical Query Suite (DuckDB)
-- Author: Rajath Gadagkar
-- Description: Eight multidimensional OLAP queries using ROLLUP, CUBE, and
--              window functions for time-series, product, customer, store,
--              and staff performance analysis.
-- =============================================================================

-- Q1: Hierarchical Revenue Drill-Down (Year -> Quarter -> Month) using ROLLUP
SELECT
    d.year,
    d.quarter,
    d.month,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY ROLLUP(d.year, d.quarter, d.month)
ORDER BY d.year, d.quarter, d.month;

-- Q2: Peak Revenue Month per Year using Window Ranking
WITH MonthlySales AS (
    SELECT
        d.year,
        d.month_name,
        ROUND(SUM(fs.sale_amount), 2) AS monthly_revenue,
        ROW_NUMBER() OVER(PARTITION BY d.year ORDER BY SUM(fs.sale_amount) DESC) AS rn
    FROM FactSales fs
    JOIN DimDate d ON fs.date_key = d.date_key
    GROUP BY d.year, d.month_name
)
SELECT
    year,
    month_name,
    monthly_revenue
FROM MonthlySales
WHERE rn = 1
ORDER BY year;

-- Q3: Revenue Ranking by Product Category
SELECT
    p.category_name,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY p.category_name
ORDER BY total_revenue DESC;

-- Q4: Category -> Product Drill-Down using ROLLUP
SELECT
    p.category_name,
    p.product_name,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
GROUP BY ROLLUP(p.category_name, p.product_name)
ORDER BY p.category_name, total_revenue DESC;

-- Q5: Multidimensional Sales Cube across (Brand, Category, Year)
SELECT
    p.brand_name,
    p.category_name,
    d.year,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY CUBE(p.brand_name, p.category_name, d.year)
ORDER BY p.brand_name, p.category_name, d.year;

-- Q6: Top 5 High-Value Customers by Total Purchase Amount
SELECT
    c.first_name || ' ' || c.last_name AS customer_name,
    c.city,
    c.state,
    ROUND(SUM(fs.sale_amount), 2) AS total_purchase_amount
FROM FactSales fs
JOIN DimCustomer c ON fs.customer_key = c.customer_key
GROUP BY customer_name, c.city, c.state
ORDER BY total_purchase_amount DESC
LIMIT 5;

-- Q7: Top-Performing Sales Staff Member per Store
WITH StaffSales AS (
    SELECT
        st.store_name,
        sf.first_name || ' ' || sf.last_name AS staff_name,
        ROUND(SUM(fs.sale_amount), 2) AS total_sales,
        RANK() OVER(PARTITION BY st.store_name ORDER BY SUM(fs.sale_amount) DESC) AS sales_rank
    FROM FactSales fs
    JOIN DimStaff sf ON fs.staff_key = sf.staff_key
    JOIN DimStore st ON fs.store_key = st.store_key
    GROUP BY st.store_name, staff_name
)
SELECT
    store_name,
    staff_name,
    total_sales
FROM StaffSales
WHERE sales_rank = 1
ORDER BY total_sales DESC;

-- Q8: Multidimensional Sales Cube across (Category, Store, Year)
SELECT
    p.category_name,
    s.store_name,
    d.year,
    ROUND(SUM(fs.sale_amount), 2) AS total_revenue
FROM FactSales fs
JOIN DimProduct p ON fs.product_key = p.product_key
JOIN DimStore s ON fs.store_key = s.store_key
JOIN DimDate d ON fs.date_key = d.date_key
GROUP BY CUBE(p.category_name, s.store_name, d.year)
ORDER BY p.category_name, s.store_name, d.year;
