-- ==============================================================================
-- CampusPulse DSU — Database Schema
-- Dayananda Sagar University (DSU), Bengaluru, Karnataka, India
-- SQLite3 with Foreign Keys & Indices
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- 1. Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    contact_email TEXT,
    building_location TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    password_hash TEXT NOT NULL,
    password_changed_at TEXT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'staff', 'admin')),
    department_id INTEGER,
    campus TEXT DEFAULT 'Main Innovation Campus (Harohalli)',
    green_points INTEGER DEFAULT 0,
    avatar_color TEXT DEFAULT '#2E7D32',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS password_recovery_codes (
    user_id INTEGER PRIMARY KEY,
    code_hash TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Verified Campus Locations
CREATE TABLE IF NOT EXISTS campus_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT NOT NULL,
    building_name TEXT NOT NULL,
    floor TEXT NOT NULL,
    zone_or_wing TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tour Stops (Virtual Campus Tour & Google Street View)
CREATE TABLE IF NOT EXISTS tour_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    heading REAL DEFAULT 0.0,
    pitch REAL DEFAULT 0.0,
    zoom INTEGER DEFAULT 1,
    description TEXT NOT NULL,
    sustainability_tip TEXT,
    image_url TEXT,
    google_maps_url TEXT,
    display_order INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Environmental Reports
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_number TEXT NOT NULL UNIQUE,
    user_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('water', 'electricity', 'waste', 'greenery', 'infrastructure')),
    priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'submitted' CHECK(status IN ('submitted', 'verified', 'assigned', 'in_progress', 'resolved', 'reopened')),
    location_id INTEGER,
    specific_spot TEXT NOT NULL,
    is_anonymous INTEGER DEFAULT 0,
    photo_path TEXT,
    resolution_photo_path TEXT,
    resolution_notes TEXT,
    ai_confidence REAL DEFAULT 0.0,
    ai_reasoning TEXT,
    assigned_to_user_id INTEGER,
    assigned_department_id INTEGER,
    due_date TEXT,
    resolved_at TIMESTAMP,
    is_demo_sample INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES campus_locations(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- 6. Report Status History / Audit Trail
CREATE TABLE IF NOT EXISTS report_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    changed_by_user_id INTEGER,
    old_status TEXT,
    new_status TEXT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Report Comments & Repair Notes
CREATE TABLE IF NOT EXISTS report_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    is_internal_staff_only INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. Energy Readings (Manual logs & IoT future-ready)
CREATE TABLE IF NOT EXISTS energy_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT NOT NULL,
    building_name TEXT NOT NULL,
    meter_name TEXT NOT NULL,
    reading_date TEXT NOT NULL,
    kwh_consumed REAL NOT NULL,
    peak_load_kw REAL DEFAULT 0.0,
    solar_generated_kwh REAL DEFAULT 0.0,
    notes TEXT,
    is_demo_sample INTEGER DEFAULT 0,
    logged_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (logged_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 9. Water Readings & Leak Logs
CREATE TABLE IF NOT EXISTS water_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT NOT NULL,
    location_name TEXT NOT NULL,
    reading_date TEXT NOT NULL,
    liters_consumed REAL NOT NULL,
    recycled_water_liters REAL DEFAULT 0.0,
    rainwater_harvested_liters REAL DEFAULT 0.0,
    leak_detected INTEGER DEFAULT 0,
    notes TEXT,
    is_demo_sample INTEGER DEFAULT 0,
    logged_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (logged_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 10. Waste Records
CREATE TABLE IF NOT EXISTS waste_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name TEXT NOT NULL,
    record_date TEXT NOT NULL,
    organic_kg REAL NOT NULL DEFAULT 0.0,
    recyclable_kg REAL NOT NULL DEFAULT 0.0,
    ewaste_kg REAL NOT NULL DEFAULT 0.0,
    hazardous_kg REAL NOT NULL DEFAULT 0.0,
    composted_kg REAL NOT NULL DEFAULT 0.0,
    landfill_diverted_pct REAL DEFAULT 0.0,
    is_demo_sample INTEGER DEFAULT 0,
    logged_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (logged_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 11. Sustainability Goals
CREATE TABLE IF NOT EXISTS sustainability_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    target_value REAL NOT NULL,
    current_value REAL NOT NULL DEFAULT 0.0,
    unit TEXT NOT NULL,
    deadline TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'in_progress',
    is_demo_sample INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Green Badges
CREATE TABLE IF NOT EXISTS green_badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL,
    points_threshold INTEGER NOT NULL DEFAULT 0
);

-- 13. User Badges
CREATE TABLE IF NOT EXISTS user_badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    badge_id INTEGER NOT NULL,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, badge_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES green_badges(id) ON DELETE CASCADE
);

-- 14. Challenges
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    points_reward INTEGER NOT NULL DEFAULT 50,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'bi-award',
    participants_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Challenge Participations
CREATE TABLE IF NOT EXISTS challenge_participations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'joined' CHECK(status IN ('joined', 'completed')),
    proof_notes TEXT,
    completed_at TIMESTAMP,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(challenge_id, user_id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 16. In-App Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 17. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Performance Indices
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_category ON reports(category);
CREATE INDEX IF NOT EXISTS idx_reports_priority ON reports(priority);
CREATE INDEX IF NOT EXISTS idx_reports_location ON reports(location_id);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_tour_stops_order ON tour_stops(display_order);
