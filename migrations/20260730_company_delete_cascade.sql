-- Company hard-delete cascade migration for MySQL 8 / InnoDB.
--
-- IMPORTANT
-- 1. Back up the target schema before running this file.
-- 2. DDL statements auto-commit in MySQL, so ROLLBACK cannot undo this migration.
-- 3. Run the whole script in one schema. Do not set FOREIGN_KEY_CHECKS=0.
-- 4. This migration deletes no application data. It only changes FK/check rules.

DELIMITER $$

DROP PROCEDURE IF EXISTS drop_fk_for_column$$
CREATE PROCEDURE drop_fk_for_column(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64)
)
BEGIN
    DECLARE v_constraint_name VARCHAR(64) DEFAULT NULL;

    SELECT kcu.CONSTRAINT_NAME
      INTO v_constraint_name
      FROM information_schema.KEY_COLUMN_USAGE AS kcu
     WHERE kcu.CONSTRAINT_SCHEMA = DATABASE()
       AND kcu.TABLE_NAME = p_table_name
       AND kcu.COLUMN_NAME = p_column_name
       AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
     LIMIT 1;

    IF v_constraint_name IS NOT NULL THEN
        SET @drop_fk_sql = CONCAT(
            'ALTER TABLE `',
            p_table_name,
            '` DROP FOREIGN KEY `',
            v_constraint_name,
            '`'
        );
        PREPARE drop_fk_stmt FROM @drop_fk_sql;
        EXECUTE drop_fk_stmt;
        DEALLOCATE PREPARE drop_fk_stmt;
    END IF;
END$$

DROP PROCEDURE IF EXISTS drop_check_if_exists$$
CREATE PROCEDURE drop_check_if_exists(
    IN p_table_name VARCHAR(64),
    IN p_constraint_name VARCHAR(64)
)
BEGIN
    DECLARE v_exists INT DEFAULT 0;

    SELECT COUNT(*)
      INTO v_exists
      FROM information_schema.TABLE_CONSTRAINTS AS tc
     WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
       AND tc.TABLE_NAME = p_table_name
       AND tc.CONSTRAINT_NAME = p_constraint_name
       AND tc.CONSTRAINT_TYPE = 'CHECK';

    IF v_exists > 0 THEN
        SET @drop_check_sql = CONCAT(
            'ALTER TABLE `',
            p_table_name,
            '` DROP CHECK `',
            p_constraint_name,
            '`'
        );
        PREPARE drop_check_stmt FROM @drop_check_sql;
        EXECUTE drop_check_stmt;
        DEALLOCATE PREPARE drop_check_stmt;
    END IF;
END$$

DELIMITER ;

-- Drop the existing foreign keys without relying on generated constraint names.
CALL drop_fk_for_column('user', 'company_id');
CALL drop_fk_for_column('signup_code', 'company_id');
CALL drop_fk_for_column('signup_code', 'used_by_uid');
CALL drop_fk_for_column('cctv', 'company_id');
CALL drop_fk_for_column('event_category', 'company_id');
CALL drop_fk_for_column('event', 'company_id');
CALL drop_fk_for_column('event', 'category_id');
CALL drop_fk_for_column('event', 'cctv_id');
CALL drop_fk_for_column('checklist', 'company_id');
CALL drop_fk_for_column('checklist', 'event_id');
CALL drop_fk_for_column('checklist', 'uid');
CALL drop_fk_for_column('checklist', 'camera_id');
CALL drop_fk_for_column('board', 'company_id');
CALL drop_fk_for_column('board', 'uid');
CALL drop_fk_for_column('board', 'event_category_id');
CALL drop_fk_for_column('education', 'company_id');
CALL drop_fk_for_column('education_status', 'uid');
CALL drop_fk_for_column('education_status', 'education_id');
CALL drop_fk_for_column('inspection', 'company_id');
CALL drop_fk_for_column('inspection', 'category_id');
CALL drop_fk_for_column('inspection_history', 'company_id');
CALL drop_fk_for_column('inspection_history', 'inspection_id');
CALL drop_fk_for_column('inspection_history', 'uid');
CALL drop_fk_for_column('action_history', 'company_id');
CALL drop_fk_for_column('action_history', 'board_id');
CALL drop_fk_for_column('action_history', 'event_id');
CALL drop_fk_for_column('action_history', 'inspection_history_id');
CALL drop_fk_for_column('action_history', 'category_id');
CALL drop_fk_for_column('action_history', 'handler_uid');
CALL drop_fk_for_column('action_history', 'approver_uid');
CALL drop_fk_for_column('report', 'company_id');
CALL drop_fk_for_column('report', 'uid');
CALL drop_fk_for_column('report_event_map', 'report_id');
CALL drop_fk_for_column('report_event_map', 'event_id');
CALL drop_fk_for_column('report_checklist_map', 'report_id');
CALL drop_fk_for_column('report_checklist_map', 'checklist_id');
CALL drop_fk_for_column('report_inspection_map', 'report_id');
CALL drop_fk_for_column('report_inspection_map', 'inspection_history_id');
CALL drop_fk_for_column('report_action_map', 'report_id');
CALL drop_fk_for_column('report_action_map', 'action_history_id');

-- SET NULL actions require nullable child columns.
ALTER TABLE `board`
    MODIFY COLUMN `uid` BIGINT NULL;

ALTER TABLE `report`
    MODIFY COLUMN `uid` BIGINT NULL;

ALTER TABLE `event`
    MODIFY COLUMN `category_id` BIGINT NULL,
    MODIFY COLUMN `cctv_id` BIGINT NULL;

ALTER TABLE `checklist`
    MODIFY COLUMN `event_id` BIGINT NULL,
    MODIFY COLUMN `uid` BIGINT NULL,
    MODIFY COLUMN `camera_id` BIGINT NULL;

ALTER TABLE `inspection`
    MODIFY COLUMN `category_id` BIGINT NULL;

ALTER TABLE `inspection_history`
    MODIFY COLUMN `inspection_id` BIGINT NULL,
    MODIFY COLUMN `uid` BIGINT NULL;

ALTER TABLE `action_history`
    MODIFY COLUMN `board_id` BIGINT NULL,
    MODIFY COLUMN `event_id` BIGINT NULL,
    MODIFY COLUMN `inspection_history_id` BIGINT NULL,
    MODIFY COLUMN `category_id` BIGINT NULL,
    MODIFY COLUMN `handler_uid` BIGINT NULL,
    MODIFY COLUMN `approver_uid` BIGINT NULL;

-- A referenced source/actor may disappear while the evidence row remains.
-- MySQL does not permit columns used by a referential SET NULL action to also
-- participate in these CHECK constraints. Creation/state validation remains
-- enforced by the FastAPI service layer.
CALL drop_check_if_exists('action_history', 'ck_action_history_source');
CALL drop_check_if_exists('action_history', 'ck_action_history_approver');
CALL drop_check_if_exists('action_history', 'ck_action_history_handler');

-- Direct company ownership: deleting one company removes every tenant row.
ALTER TABLE `user`
    ADD CONSTRAINT `fk_user_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE;

ALTER TABLE `signup_code`
    ADD CONSTRAINT `fk_signup_code_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_signup_code_used_by_user`
    FOREIGN KEY (`used_by_uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL;

ALTER TABLE `cctv`
    ADD CONSTRAINT `fk_cctv_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE;

ALTER TABLE `event_category`
    ADD CONSTRAINT `fk_event_category_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE;

ALTER TABLE `event`
    ADD CONSTRAINT `fk_event_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_event_category`
    FOREIGN KEY (`category_id`) REFERENCES `event_category` (`category_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_event_cctv`
    FOREIGN KEY (`cctv_id`) REFERENCES `cctv` (`cctv_id`)
    ON DELETE SET NULL;

ALTER TABLE `checklist`
    ADD CONSTRAINT `fk_checklist_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_checklist_event`
    FOREIGN KEY (`event_id`) REFERENCES `event` (`event_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_checklist_user`
    FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_checklist_cctv`
    FOREIGN KEY (`camera_id`) REFERENCES `cctv` (`cctv_id`)
    ON DELETE SET NULL;

ALTER TABLE `board`
    ADD CONSTRAINT `fk_board_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_board_user`
    FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_board_event_category`
    FOREIGN KEY (`event_category_id`)
    REFERENCES `event_category` (`category_id`)
    ON DELETE SET NULL;

ALTER TABLE `education`
    ADD CONSTRAINT `fk_education_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE;

ALTER TABLE `education_status`
    ADD CONSTRAINT `fk_education_status_user`
    FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_education_status_education`
    FOREIGN KEY (`education_id`) REFERENCES `education` (`education_id`)
    ON DELETE CASCADE;

ALTER TABLE `inspection`
    ADD CONSTRAINT `fk_inspection_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_inspection_event_category`
    FOREIGN KEY (`category_id`) REFERENCES `event_category` (`category_id`)
    ON DELETE SET NULL;

ALTER TABLE `inspection_history`
    ADD CONSTRAINT `fk_inspection_history_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_inspection_history_inspection`
    FOREIGN KEY (`inspection_id`) REFERENCES `inspection` (`inspection_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_inspection_history_user`
    FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL;

ALTER TABLE `action_history`
    ADD CONSTRAINT `fk_action_history_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_action_history_board`
    FOREIGN KEY (`board_id`) REFERENCES `board` (`board_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_action_history_event`
    FOREIGN KEY (`event_id`) REFERENCES `event` (`event_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_action_history_inspection_history`
    FOREIGN KEY (`inspection_history_id`)
    REFERENCES `inspection_history` (`inspection_history_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_action_history_event_category`
    FOREIGN KEY (`category_id`) REFERENCES `event_category` (`category_id`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_action_history_handler`
    FOREIGN KEY (`handler_uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL,
    ADD CONSTRAINT `fk_action_history_approver`
    FOREIGN KEY (`approver_uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL;

ALTER TABLE `report`
    ADD CONSTRAINT `fk_report_company`
    FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_report_user`
    FOREIGN KEY (`uid`) REFERENCES `user` (`uid`)
    ON DELETE SET NULL;

-- Pure association rows have no meaning after either parent is removed.
ALTER TABLE `report_event_map`
    ADD CONSTRAINT `fk_report_event_map_report`
    FOREIGN KEY (`report_id`) REFERENCES `report` (`report_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_report_event_map_event`
    FOREIGN KEY (`event_id`) REFERENCES `event` (`event_id`)
    ON DELETE CASCADE;

ALTER TABLE `report_checklist_map`
    ADD CONSTRAINT `fk_report_checklist_map_report`
    FOREIGN KEY (`report_id`) REFERENCES `report` (`report_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_report_checklist_map_checklist`
    FOREIGN KEY (`checklist_id`) REFERENCES `checklist` (`checklist_id`)
    ON DELETE CASCADE;

ALTER TABLE `report_inspection_map`
    ADD CONSTRAINT `fk_report_inspection_map_report`
    FOREIGN KEY (`report_id`) REFERENCES `report` (`report_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_report_inspection_map_history`
    FOREIGN KEY (`inspection_history_id`)
    REFERENCES `inspection_history` (`inspection_history_id`)
    ON DELETE CASCADE;

ALTER TABLE `report_action_map`
    ADD CONSTRAINT `fk_report_action_map_report`
    FOREIGN KEY (`report_id`) REFERENCES `report` (`report_id`)
    ON DELETE CASCADE,
    ADD CONSTRAINT `fk_report_action_map_action`
    FOREIGN KEY (`action_history_id`)
    REFERENCES `action_history` (`action_history_id`)
    ON DELETE CASCADE;

DROP PROCEDURE IF EXISTS drop_fk_for_column;
DROP PROCEDURE IF EXISTS drop_check_if_exists;

-- Verification: all rows below should show CASCADE or SET NULL as designed.
SELECT
    rc.TABLE_NAME,
    kcu.COLUMN_NAME,
    rc.REFERENCED_TABLE_NAME,
    rc.DELETE_RULE
FROM information_schema.REFERENTIAL_CONSTRAINTS AS rc
JOIN information_schema.KEY_COLUMN_USAGE AS kcu
  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
 AND rc.TABLE_NAME = kcu.TABLE_NAME
WHERE rc.CONSTRAINT_SCHEMA = DATABASE()
  AND (
      rc.REFERENCED_TABLE_NAME = 'company'
      OR rc.TABLE_NAME IN (
          'education_status',
          'report_event_map',
          'report_checklist_map',
          'report_inspection_map',
          'report_action_map'
      )
  )
ORDER BY rc.TABLE_NAME, kcu.COLUMN_NAME;
