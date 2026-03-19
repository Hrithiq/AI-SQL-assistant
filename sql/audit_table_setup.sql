-- =============================================================================
-- Audit Table Setup
-- Run this ONCE against your SQL Server instance before using audit_logger.py.
-- Required for HIPAA audit trails and SOC 2 compliance.
-- =============================================================================

IF NOT EXISTS (
    SELECT 1
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'dbo'
      AND TABLE_NAME   = 'AI_QueryCorrections'
)
BEGIN
    CREATE TABLE dbo.AI_QueryCorrections (
        CorrectionID   INT            IDENTITY(1,1) PRIMARY KEY,
        OriginalSQL    NVARCHAR(MAX)  NOT NULL,
        ErrorMessage   NVARCHAR(2000) NOT NULL,
        Diagnosis      NVARCHAR(1000) NOT NULL,
        CorrectedSQL   NVARCHAR(MAX)  NOT NULL,
        AnalystUser    NVARCHAR(256)  NOT NULL,
        CorrectedAt    DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
    );

    -- Index for filtering by analyst and date range (common audit query pattern)
    CREATE NONCLUSTERED INDEX IX_AI_QueryCorrections_User_Date
        ON dbo.AI_QueryCorrections (AnalystUser, CorrectedAt DESC);

    PRINT 'Created dbo.AI_QueryCorrections and index.';
END
ELSE
BEGIN
    PRINT 'dbo.AI_QueryCorrections already exists. No action taken.';
END
;
