-- =====================================================================
-- Snowflake external stage + CSV format on Azure Blob Storage
-- =====================================================================
USE ROLE ACCOUNTADMIN;
USE DATABASE ZOMATO;
USE SCHEMA RAW;

CREATE OR REPLACE FILE FORMAT ZOMATO.RAW.CSV_FMT
  TYPE = 'CSV'
  COMPRESSION = 'AUTO'
  FIELD_DELIMITER = ','
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  SKIP_HEADER = 1
  EMPTY_FIELD_AS_NULL = TRUE
  NULL_IF = ('', '\\N', 'NULL')
  TRIM_SPACE = FALSE
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

-- Upload the seven CSVs under:
-- raw/restaurants/
-- raw/users/
-- raw/food/
-- raw/menu/
-- raw/orders/
-- raw/order_items/
-- raw/reviews/
--
-- Replace the storage account and container with your Azure values.
CREATE OR REPLACE STAGE ZOMATO.RAW.ZOMATO_RAW_STAGE
  STORAGE_INTEGRATION = ZOMATO_AZURE_INT
  URL = 'azure://<STORAGE_ACCOUNT>.blob.core.windows.net/<CONTAINER>/raw/'
  FILE_FORMAT = ZOMATO.RAW.CSV_FMT;

-- Confirm Snowflake can see the uploaded files.
LIST @ZOMATO.RAW.ZOMATO_RAW_STAGE;
