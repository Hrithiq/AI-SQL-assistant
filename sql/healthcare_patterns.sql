-- =============================================================================
-- Optum Healthcare SQL Patterns
-- Production-grade query templates for Claims, Members, Provider, and Fraud data.
-- All queries are read-only SELECT statements.
-- Optimization notes are inline.
-- =============================================================================


-- =============================================================================
-- 1. CLAIMS — Paid claims with member eligibility validation
-- =============================================================================
-- Optimization: Filter ClaimStatus BEFORE joining to reduce row count early.
--               Use range filter on ClaimDate (sargable) not YEAR() function.
--               WITH (NOLOCK) is acceptable for analytics; drop for audit queries.
-- =============================================================================

SELECT
    c.ClaimKey,
    c.ClaimDate,
    c.Paid_Amount,
    c.DiagnosisCode,
    m.MemberKey,
    m.DateOfBirth,
    m.State,
    p.ProviderNPI,
    p.SpecialtyCode
FROM
    dbo.Claims             c WITH (NOLOCK)
    INNER JOIN dbo.Members m WITH (NOLOCK)
        ON m.MemberKey   = c.MemberKey
    INNER JOIN dbo.Providers p WITH (NOLOCK)
        ON p.ProviderKey = c.ProviderKey
    -- Validate member was eligible on the date of service
    INNER JOIN dbo.MemberEligibility me WITH (NOLOCK)
        ON  me.MemberKey    = m.MemberKey
        AND c.ClaimDate BETWEEN me.EffectiveDate AND me.TerminationDate
WHERE
    c.ClaimStatus   = 'PAID'
    AND c.ClaimDate >= DATEADD(YEAR, -1, GETDATE())   -- Sargable range filter
    -- Avoid: WHERE YEAR(c.ClaimDate) = 2024           -- Non-sargable; kills index seeks
;


-- =============================================================================
-- 2. MEMBERS — Age group cost analysis
-- =============================================================================
-- Optimization: Compute age bucket in a CTE so the GROUP BY is clean.
--               Avoid DATEDIFF in WHERE clauses — pre-filter by ClaimDate instead.
-- =============================================================================

WITH member_with_age AS (
    SELECT
        m.MemberKey,
        m.State,
        CASE
            WHEN DATEDIFF(YEAR, m.DateOfBirth, GETDATE()) < 18  THEN 'Under 18'
            WHEN DATEDIFF(YEAR, m.DateOfBirth, GETDATE()) < 35  THEN '18-34'
            WHEN DATEDIFF(YEAR, m.DateOfBirth, GETDATE()) < 50  THEN '35-49'
            WHEN DATEDIFF(YEAR, m.DateOfBirth, GETDATE()) < 65  THEN '50-64'
            ELSE '65+'
        END AS age_group
    FROM dbo.Members m WITH (NOLOCK)
)
SELECT
    ma.age_group,
    ma.State,
    COUNT(DISTINCT c.ClaimKey)   AS total_claims,
    COUNT(DISTINCT c.MemberKey)  AS unique_members,
    SUM(c.Paid_Amount)           AS total_paid,
    AVG(c.Paid_Amount)           AS avg_paid_per_claim
FROM
    member_with_age              ma
    INNER JOIN dbo.Claims        c WITH (NOLOCK) ON c.MemberKey = ma.MemberKey
WHERE
    c.ClaimStatus  = 'PAID'
    AND c.ClaimDate >= DATEADD(YEAR, -1, GETDATE())
GROUP BY
    ma.age_group,
    ma.State
ORDER BY
    ma.State,
    ma.age_group
;


-- =============================================================================
-- 3. FRAUD — Providers billing significantly above specialty average
-- =============================================================================
-- Optimization: Window AVG over SpecialtyCode instead of a correlated subquery.
--               Correlated subquery would re-scan Claims for every provider row.
-- Compatible with: Snowflake (swap DATEADD for DATEADD('YEAR', -1, CURRENT_DATE()))
-- =============================================================================

WITH provider_summary AS (
    SELECT
        p.ProviderNPI,
        p.SpecialtyCode,
        COUNT(DISTINCT c.MemberKey)                     AS unique_members,
        COUNT(c.ClaimKey)                               AS total_claims,
        SUM(c.Paid_Amount)                              AS total_paid,
        AVG(c.Paid_Amount)                              AS avg_paid_per_claim,
        -- Compare each provider to the average within their specialty
        AVG(SUM(c.Paid_Amount)) OVER (
            PARTITION BY p.SpecialtyCode
        )                                               AS specialty_avg_paid
    FROM
        dbo.Claims    c WITH (NOLOCK)
        INNER JOIN dbo.Providers p WITH (NOLOCK)
            ON p.ProviderKey = c.ProviderKey
    WHERE
        c.ClaimDate >= DATEADD(YEAR, -1, GETDATE())
    GROUP BY
        p.ProviderNPI,
        p.SpecialtyCode
)
SELECT
    ps.*,
    fa.AlertType,
    fa.AlertDate,
    ROUND(ps.total_paid / NULLIF(ps.specialty_avg_paid, 0), 2) AS paid_vs_specialty_ratio
FROM
    provider_summary             ps
    LEFT JOIN dbo.FraudAlerts    fa ON fa.ProviderNPI = ps.ProviderNPI
WHERE
    ps.total_paid > ps.specialty_avg_paid * 2     -- Providers billing 2x their specialty norm
ORDER BY
    paid_vs_specialty_ratio DESC
;


-- =============================================================================
-- 4. PROVIDERS — Top 10 diagnosis codes by total paid (specialty-filtered)
-- =============================================================================
-- Optimization: Use TOP with ORDER BY rather than ROW_NUMBER() in a subquery
--               when you only need a simple top-N without ties handling.
-- =============================================================================

SELECT TOP 10
    c.DiagnosisCode,
    p.SpecialtyCode,
    COUNT(c.ClaimKey)    AS claim_count,
    SUM(c.Paid_Amount)   AS total_paid,
    AVG(c.Paid_Amount)   AS avg_paid
FROM
    dbo.Claims    c WITH (NOLOCK)
    INNER JOIN dbo.Providers p WITH (NOLOCK)
        ON p.ProviderKey = c.ProviderKey
WHERE
    c.ClaimStatus   = 'PAID'
    AND c.ClaimDate >= DATEADD(YEAR, -1, GETDATE())
    AND p.SpecialtyCode = 'CARDIOLOGY'     -- Parameterise as needed
GROUP BY
    c.DiagnosisCode,
    p.SpecialtyCode
ORDER BY
    total_paid DESC
;


-- =============================================================================
-- 5. DATA QUALITY — Members with claims outside eligibility windows
-- =============================================================================
-- Useful for data quality checks and dashboard alerts.
-- Returns members who have paid claims on dates when they were not eligible.
-- =============================================================================

SELECT
    c.ClaimKey,
    c.ClaimDate,
    c.Paid_Amount,
    m.MemberKey,
    m.State,
    me.EffectiveDate,
    me.TerminationDate
FROM
    dbo.Claims    c WITH (NOLOCK)
    INNER JOIN dbo.Members m WITH (NOLOCK)
        ON m.MemberKey = c.MemberKey
    -- Left join to eligibility: NULLs = no matching eligibility window
    LEFT JOIN dbo.MemberEligibility me WITH (NOLOCK)
        ON  me.MemberKey    = m.MemberKey
        AND c.ClaimDate BETWEEN me.EffectiveDate AND me.TerminationDate
WHERE
    c.ClaimStatus  = 'PAID'
    AND me.MemberKey IS NULL              -- Claim with no valid eligibility window
    AND c.ClaimDate >= DATEADD(YEAR, -2, GETDATE())
ORDER BY
    c.ClaimDate DESC
;
