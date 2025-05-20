CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    avatar_url TEXT DEFAULT ''
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
    timestamp DATETIME NOT NULL,
    group_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    text TEXT DEFAULT '',
    attachments TEXT DEFAULT '[]',
    FOREIGN KEY (group_id) REFERENCES group_chat(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES user(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS reminder (
    id TEXT PRIMARY KEY,
    created DATETIME NOT NULL,
    eta DATETIME NOT NULL,
    group_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    command_message_id TEXT NOT NULL,
    sent BOOLEAN DEFAULT 0,
    FOREIGN KEY (group_id) REFERENCES group_chat(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (command_message_id) REFERENCES chat_message(id) ON DELETE CASCADE
);
