-- =============================================================================
-- Retail Sales Star Schema DDL (DuckDB)
-- Author: Rajath Gadagkar
-- Description: Defines five conformed dimension tables and a central FactSales
--              table optimized for OLAP aggregations, ROLLUP, and CUBE queries.
-- =============================================================================

-- Dimension: Calendar Date (2016-2018)
CREATE TABLE IF NOT EXISTS DimDate (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL
);

-- Dimension: Customer
CREATE TABLE IF NOT EXISTS DimCustomer (
    customer_key INT PRIMARY KEY,
    customer_id INT NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    city VARCHAR(255),
    state VARCHAR(50)
);

-- Dimension: Store Location
CREATE TABLE IF NOT EXISTS DimStore (
    store_key INT PRIMARY KEY,
    store_id INT NOT NULL,
    store_name VARCHAR(255),
    city VARCHAR(255),
    state VARCHAR(50)
);

-- Dimension: Sales Staff
CREATE TABLE IF NOT EXISTS DimStaff (
    staff_key INT PRIMARY KEY,
    staff_id INT NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255)
);

-- Dimension: Product (Denormalized with Brand & Category for OLAP speed)
CREATE TABLE IF NOT EXISTS DimProduct (
    product_key INT PRIMARY KEY,
    product_id INT NOT NULL,
    product_name VARCHAR(255),
    brand_name VARCHAR(255),
    category_name VARCHAR(255),
    model_year INT,
    list_price DECIMAL(10, 2)
);

-- Fact Table: Order-Line Sales Transactions
CREATE TABLE IF NOT EXISTS FactSales (
    order_id INT NOT NULL,
    order_item_id INT NOT NULL,
    date_key INT REFERENCES DimDate(date_key),
    customer_key INT REFERENCES DimCustomer(customer_key),
    store_key INT REFERENCES DimStore(store_key),
    staff_key INT REFERENCES DimStaff(staff_key),
    product_key INT REFERENCES DimProduct(product_key),
    quantity INT NOT NULL,
    sale_amount DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);
