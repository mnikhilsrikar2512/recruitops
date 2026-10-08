/* =====================================================================
   020_offer_threshold.sql — Phase 4.8 (decision D-06): a company setting
   for when an offer needs approval.

   tenants.offer_approval_threshold: an offer whose total (CTC + signing
   bonus) is ABOVE the threshold goes to approval; at or below it the offer
   is approved straight away. Default 0 = every paid offer needs approval,
   which is today's behaviour, so nothing changes until a company sets it.
   Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.tenants', N'offer_approval_threshold') IS NULL
  ALTER TABLE dbo.tenants ADD offer_approval_threshold DECIMAL(18, 2) NOT NULL
    CONSTRAINT DF_tenants_offer_approval_threshold DEFAULT (0);
GO

IF OBJECT_ID(N'dbo.CK_tenants_offer_approval_threshold', N'C') IS NULL
  ALTER TABLE dbo.tenants ADD CONSTRAINT CK_tenants_offer_approval_threshold CHECK (offer_approval_threshold >= 0);
GO
