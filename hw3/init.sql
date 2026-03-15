CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);
CREATE TABLE links (
    short_code VARCHAR(20) PRIMARY KEY,
    original_url TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicks_count INTEGER DEFAULT 0
);
CREATE TABLE expired_links (
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(20),
    original_url TEXT,
    expired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(100)
);