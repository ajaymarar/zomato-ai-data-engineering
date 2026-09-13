-- =====================================================================
-- Load RAW tables from Azure Blob Storage
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE DATABASE ZOMATO;
USE SCHEMA RAW;
USE WAREHOUSE ZOMATO_WH;

-- Dimensions: tolerate malformed source rows.
COPY INTO RAW.restaurants FROM @ZOMATO_RAW_STAGE/restaurants/  ON_ERROR = 'CONTINUE';
COPY INTO RAW.users       FROM @ZOMATO_RAW_STAGE/users/        ON_ERROR = 'CONTINUE';
COPY INTO RAW.food        FROM @ZOMATO_RAW_STAGE/food/         ON_ERROR = 'CONTINUE';
COPY INTO RAW.menu        FROM @ZOMATO_RAW_STAGE/menu/         ON_ERROR = 'CONTINUE';

-- Facts: generated source data is expected to be clean, so keep loading strict.
COPY INTO RAW.orders      FROM @ZOMATO_RAW_STAGE/orders/       ON_ERROR = 'ABORT_STATEMENT';
COPY INTO RAW.order_items FROM @ZOMATO_RAW_STAGE/order_items/  ON_ERROR = 'ABORT_STATEMENT';
COPY INTO RAW.reviews     FROM @ZOMATO_RAW_STAGE/reviews/      ON_ERROR = 'ABORT_STATEMENT';

-- Sanity check.
SELECT 'restaurants' AS table_name, COUNT(*) AS row_count FROM RAW.restaurants
UNION ALL SELECT 'users', COUNT(*) FROM RAW.users
UNION ALL SELECT 'food', COUNT(*) FROM RAW.food
UNION ALL SELECT 'menu', COUNT(*) FROM RAW.menu
UNION ALL SELECT 'orders', COUNT(*) FROM RAW.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM RAW.order_items
UNION ALL SELECT 'reviews', COUNT(*) FROM RAW.reviews
ORDER BY table_name;

-- Validated project load:
-- restaurants 148,541 | users 100,000 | food 371,561 | menu 1,179,936
-- orders 10,000,000 | order_items 22,998,179 | reviews 300,000
