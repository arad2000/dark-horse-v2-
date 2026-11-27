-- ============================================================
-- ۰) بررسی کد معرف تکراری (فقط خواندن) — خروجی باید خالی باشد
-- ============================================================
SELECT target_id AS referral_code, count(*) AS times
FROM admin_audit_logs
WHERE target_type = 'referral_code' AND action = 'create_referral_code'
GROUP BY target_id HAVING count(*) > 1;

-- ============================================================
-- ۱) ثبت وضعیت فعلی اسکیما در alembic_version (ایمن، تک‌بار)
--    تأیید شده روی PostgreSQL 16.2 در ۴ حالت
-- ============================================================
DO $$
DECLARE
  dup_codes int;
BEGIN
  IF to_regclass('alembic_version') IS NOT NULL THEN
    RAISE NOTICE 'ALREADY_STAMPED version=%', (SELECT version_num FROM alembic_version);
    RETURN;
  END IF;

  IF to_regclass('users') IS NULL OR to_regclass('micro_motives') IS NULL THEN
    RAISE NOTICE 'SKIPPED database looks empty; the start hook will build the schema';
    RETURN;
  END IF;

  IF to_regclass('uq_admin_audit_referral_code') IS NOT NULL THEN
    CREATE TABLE alembic_version (
      version_num VARCHAR(32) NOT NULL,
      CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
    );
    INSERT INTO alembic_version (version_num) VALUES ('0012_referral_attribution');
    RAISE NOTICE 'STAMPED 0012_referral_attribution (its index already existed)';
    RETURN;
  END IF;

  SELECT count(*) INTO dup_codes
  FROM (
    SELECT target_id FROM admin_audit_logs
    WHERE target_type = 'referral_code' AND action = 'create_referral_code'
    GROUP BY target_id HAVING count(*) > 1
  ) AS d;
  IF dup_codes > 0 THEN
    RAISE EXCEPTION 'DUPLICATE_REFERRAL_CODES % code(s) appear more than once. Resolve them before stamping.', dup_codes;
  END IF;

  CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
  );
  INSERT INTO alembic_version (version_num) VALUES ('0011_otp_request_ip');
  RAISE NOTICE 'STAMPED 0011_otp_request_ip; the start hook will now apply 0012';
END $$;

-- ============================================================
-- ۲) تأیید نتیجه (فقط خواندن)
-- ============================================================
SELECT version_num FROM alembic_version;
