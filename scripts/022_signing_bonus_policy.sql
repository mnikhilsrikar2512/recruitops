/* =====================================================================
   022_signing_bonus_policy.sql — Phase 4.13 (decision D-4.13): not every
   company or client pays a signing bonus.

   Two switches, on the company (tenants) and on each client
   (client_companies):
     offers_signing_bonus         — the offer form shows / accepts a bonus
     bonus_counts_against_budget  — the bonus is added to CTC when the offer
                                    is compared with the budget / threshold
   A company hiring for itself (internal requisition) uses the company
   switches. A requisition for a client uses the client's switches; a NULL
   client switch inherits the company's.

   Defaults for NEW companies: bonus off, counts on. Companies that exist
   when this runs keep today's behaviour (bonus on). Idempotent.
   ===================================================================== */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH(N'dbo.tenants', N'offers_signing_bonus') IS NULL
BEGIN
  ALTER TABLE dbo.tenants ADD offers_signing_bonus BIT NOT NULL
    CONSTRAINT DF_tenants_offers_signing_bonus DEFAULT (0);
  EXEC(N'UPDATE dbo.tenants SET offers_signing_bonus = 1;');
END;
GO

IF COL_LENGTH(N'dbo.tenants', N'bonus_counts_against_budget') IS NULL
  ALTER TABLE dbo.tenants ADD bonus_counts_against_budget BIT NOT NULL
    CONSTRAINT DF_tenants_bonus_counts_against_budget DEFAULT (1);
GO

IF COL_LENGTH(N'dbo.client_companies', N'offers_signing_bonus') IS NULL
  ALTER TABLE dbo.client_companies ADD offers_signing_bonus BIT NULL;
GO

IF COL_LENGTH(N'dbo.client_companies', N'bonus_counts_against_budget') IS NULL
  ALTER TABLE dbo.client_companies ADD bonus_counts_against_budget BIT NULL;
GO
