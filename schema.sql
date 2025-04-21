CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    avatar_url TEXT DEFAULT '',
    is_bot BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS group_chat (
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    bot_id TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS membership (
    user_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    PRIMARY KEY (user_id, group_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES group_chat(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_message (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    group_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    text TEXT DEFAULT '',
    attachments TEXT DEFAULT '[]',
    FOREIGN KEY (group_id) REFERENCES group_chat(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES user(id) ON DELETE SET NULL
);
