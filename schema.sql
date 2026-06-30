-- ============================================================
-- GRAND REUNION TOUR (GRT 2006-2007) DATABASE SCHEMA
-- ============================================================
CREATE DATABASE IF NOT EXISTS grt_reunion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE grt_reunion;

-- ---------------- ROLES & PERMISSIONS ----------------
CREATE TABLE roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,         -- owner, admin, classmate
    description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(80) NOT NULL UNIQUE,         -- e.g. manage_users, manage_gallery
    description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- USERS / ADMINS ----------------
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,          -- NULL until classmate sets one via invite
    role_id INT NOT NULL,
    avatar_then VARCHAR(255),                 -- 2006 photo
    avatar_now VARCHAR(255),                  -- 2026 photo
    phone VARCHAR(40),
    bio TEXT,
    quote TEXT,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX idx_users_email (email),
    INDEX idx_users_role (role_id)
) ENGINE=InnoDB;

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    last_login DATETIME,
    failed_attempts INT DEFAULT 0,
    locked_until DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE password_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    used TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- SESSIONS / LOGS ----------------
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,               -- secure random session token
    user_id INT NOT NULL,
    ip_address VARCHAR(64),
    user_agent VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    email_attempted VARCHAR(150),
    success TINYINT(1),
    ip_address VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(150) NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------- INVITATIONS (MAGIC LINKS) ----------------
CREATE TABLE invitations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(128) NOT NULL UNIQUE,
    email VARCHAR(150),
    created_by INT NOT NULL,
    qr_code_path VARCHAR(255),
    expires_at DATETIME NOT NULL,
    revoked TINYINT(1) DEFAULT 0,
    used_by INT NULL,
    used_at DATETIME NULL,
    resend_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (used_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_invite_token (token)
) ENGINE=InnoDB;

-- ---------------- STUDENTS (DIRECTORY PROFILE EXTENSION) ----------------
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    batch_year VARCHAR(20) DEFAULT '2006-2007',
    city VARCHAR(100),
    profession VARCHAR(150),
    company VARCHAR(150),
    school_memory TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_students_city (city)
) ENGINE=InnoDB;

-- ---------------- ALBUMS / PHOTOS / TAGS ----------------
CREATE TABLE albums (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    cover_photo VARCHAR(255),
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE photos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    album_id INT NOT NULL,
    uploaded_by INT NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    caption VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    photo_id INT NOT NULL,
    tagged_user_id INT NOT NULL,
    x_position DECIMAL(5,2),
    y_position DECIMAL(5,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
    FOREIGN KEY (tagged_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- EVENTS / RSVP ----------------
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    venue VARCHAR(255),
    map_lat DECIMAL(10,6),
    map_lng DECIMAL(10,6),
    hotel_name VARCHAR(150),
    hotel_details TEXT,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME,
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE rsvps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    status ENUM('going','not_going','maybe') DEFAULT 'maybe',
    guests INT DEFAULT 0,
    responded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_event_user (event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- ANNOUNCEMENTS ----------------
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    body TEXT NOT NULL,
    created_by INT NOT NULL,
    pinned TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

-- ---------------- MESSAGE BOARD / COMMENTS / LIKES ----------------
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    target_type ENUM('photo','message','announcement','career') NOT NULL,
    target_id INT NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_comments_target (target_type, target_id)
) ENGINE=InnoDB;

CREATE TABLE likes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    target_type ENUM('photo','message','announcement','career') NOT NULL,
    target_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_like (user_id, target_type, target_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_likes_target (target_type, target_id)
) ENGINE=InnoDB;

-- ---------------- LOST & FOUND ----------------
CREATE TABLE lost_found (
    id INT PRIMARY KEY AUTO_INCREMENT,
    posted_by INT NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    description TEXT,
    photo_path VARCHAR(255),
    status ENUM('lost','found','claimed') DEFAULT 'lost',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (posted_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- CAREER OPPORTUNITIES ----------------
CREATE TABLE career_opportunities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    posted_by INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    company VARCHAR(150),
    description TEXT,
    location VARCHAR(150),
    link VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (posted_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------- NOTIFICATIONS ----------------
CREATE TABLE notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    body TEXT,
    is_read TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notif_user (user_id, is_read)
) ENGINE=InnoDB;

-- ---------------- SETTINGS / BACKUPS ----------------
CREATE TABLE settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE backups (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_path VARCHAR(255) NOT NULL,
    created_by INT,
    size_bytes BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------- SEED DATA ----------------
INSERT INTO roles (name, description) VALUES
('owner', 'Full administrative control'),
('admin', 'Administrative control'),
('classmate', 'Standard reunion member');

INSERT INTO permissions (code, description) VALUES
('manage_users','Create/edit/delete users'),
('manage_settings','Edit website settings'),
('manage_content','Manage gallery, events, announcements'),
('manage_invitations','Generate and manage invites'),
('view_analytics','View analytics dashboard'),
('manage_backups','Create and restore backups');

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'owner';

INSERT INTO settings (setting_key, setting_value) VALUES
('site_title', 'Grand Reunion Tour 2006-2007'),
('reunion_date', '2026-12-19 18:00:00'),
('theme', 'luxury-glass-dark');
