/* =====================================================================
   009_branch_offer_toggle.sql
   Per-branch "Offer tracking" configuration toggle.

   Spec: "Ensure the Offer feature can be optionally streamlined or
   toggled per tenant if a company only performs sourcing and hand-offs
   without tracking formal job offers." Branches are the per-tenant
   unit in this schema, so the toggle lives here.

   Tri-state: NULL = inherit default (enabled). 1 = enabled.
   0 = disabled (create-offer is rejected; historical offers remain
   visible read-only). Existing branches are backfilled to 1 so current
   behaviour is unchanged.
   ===================================================================== */

IF OBJECT_ID(N'dbo.branches', N'U') IS NULL
BEGIN
  RAISERROR (N'Table dbo.branches does not exist; run 001 schema first.', 16, 1);
  RETURN;
END;

IF COL_LENGTH(N'dbo.branches', N'offers_enabled') IS NULL
BEGIN
  ALTER TABLE dbo.branches
    ADD offers_enabled BIT NULL;
END;
GO

/* Backfill: every branch existing at migration time keeps offer
   tracking enabled so no current workflow changes. */
UPDATE dbo.branches
SET offers_enabled = 1
WHERE offers_enabled IS NULL;
GO
