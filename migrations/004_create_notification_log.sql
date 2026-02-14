-- Migration: Create notification tracking table
-- Date: 2026-02-13
-- Description: Track which notifications were sent to prevent spam

CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_id TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opened BOOLEAN DEFAULT 0,
    clicked BOOLEAN DEFAULT 0,

    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
);

CREATE INDEX idx_notif_user ON notification_log(user_id, notification_id);
CREATE INDEX idx_notif_sent ON notification_log(sent_at);
