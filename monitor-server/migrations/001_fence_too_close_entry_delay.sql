-- Migration: fence-too-close-entry-delay
-- ==========================================
-- 新增 electronic_fences 表两列 + fence_event_types 一行
--
-- MySQL 执行方式:
--   mysql -u root -p monitor < monitor-server/migrations/001_fence_too_close_entry_delay.sql
--
-- SQLite 执行方式:
--   sqlite3 monitor.db < monitor-server/migrations/001_fence_too_close_entry_delay.sql

-- ── electronic_fences 新增列 ─────────────────
ALTER TABLE electronic_fences
    ADD COLUMN safe_distance INTEGER NOT NULL DEFAULT 0;

ALTER TABLE electronic_fences
    ADD COLUMN entry_delay_seconds INTEGER NOT NULL DEFAULT 0;

-- ── fence_event_types 新增 TOO_CLOSE ─────────
-- MySQL: INSERT IGNORE; SQLite: INSERT OR IGNORE
INSERT OR IGNORE INTO fence_event_types (id, name) VALUES (2, 'TOO_CLOSE');

-- 如果是 MySQL 执行，用下面这行替换上面的 INSERT OR IGNORE:
-- INSERT IGNORE INTO fence_event_types (id, name) VALUES (2, 'TOO_CLOSE');
