-- =====================================================================
-- Snowflake + Azure Blob Storage integration
-- =====================================================================
-- This project uses Azure Blob Storage as the raw-data landing zone.
-- The storage integration avoids storing Azure credentials in Snowflake.
--
-- 1. Create the integration.
-- 2. Run DESC STORAGE INTEGRATION to retrieve the Snowflake application
--    details if your Azure tenant requires admin consent.
-- 3. Grant the Snowflake service principal Storage Blob Data Contributor
--    on the Azure storage account/container.
-- 4. Run 03_stage_and_formats.sql.
--
-- Replace the tenant ID and storage URL with your own values.
-- Never commit client secrets or passwords.
-- =====================================================================

USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE STORAGE INTEGRATION ZOMATO_AZURE_INT
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  AZURE_TENANT_ID = '<AZURE_TENANT_ID>'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = (
    'azure://<STORAGE_ACCOUNT>.blob.core.windows.net/<CONTAINER>/'
  );

DESC STORAGE INTEGRATION ZOMATO_AZURE_INT;

-- After the Azure service principal has the required RBAC permission,
-- the integration can be used by the external stage in step 03.
