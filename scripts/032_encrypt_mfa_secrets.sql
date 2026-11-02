-- 032: room for encrypted TOTP seeds (Phase 6.3).
-- user_mfa.totp_secret was NVARCHAR(64) for a plain base32 seed. Encrypted
-- values look like enc:v1:<key id>:<base64url(nonce||ciphertext||tag)>
-- (~100 characters), so widen it. Existing plaintext rows keep working and
-- are encrypted in place by backend/scripts/encrypt_mfa_secrets.py.
-- Idempotent and self-verifying.

IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.user_mfa') AND name = 'totp_secret' AND max_length < 1024
)
    ALTER TABLE dbo.user_mfa ALTER COLUMN totp_secret NVARCHAR(512) NOT NULL;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.user_mfa') AND name = 'totp_secret' AND max_length = 1024
)
    RAISERROR('032 failed: dbo.user_mfa.totp_secret is not NVARCHAR(512)', 16, 1);
GO
