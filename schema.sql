-- ============================================================
--  PLACEMENT ANALYTICS SYSTEM — DATABASE SCHEMA
--  Includes: Tables, Views, Triggers, Indexes, Constraints
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────
--  CORE TABLES
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS departments (
    dept_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name   TEXT NOT NULL UNIQUE,
    hod_name    TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS students (
    student_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no      TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    dept_id      INTEGER NOT NULL REFERENCES departments(dept_id) ON DELETE RESTRICT,
    cgpa         REAL NOT NULL CHECK(cgpa >= 0.0 AND cgpa <= 10.0),
    backlogs     INTEGER DEFAULT 0 CHECK(backlogs >= 0),
    batch_year   INTEGER NOT NULL,
    phone        TEXT,
    status       TEXT DEFAULT 'active' CHECK(status IN ('active','placed','opted_out')),
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS companies (
    company_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    sector       TEXT NOT NULL,
    tier         TEXT NOT NULL CHECK(tier IN ('Tier-1','Tier-2','Tier-3')),
    website      TEXT,
    hr_contact   TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drives (
    drive_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    drive_date      TEXT NOT NULL,
    role            TEXT NOT NULL,
    package_lpa     REAL NOT NULL CHECK(package_lpa > 0),
    min_cgpa        REAL DEFAULT 6.0 CHECK(min_cgpa >= 0 AND min_cgpa <= 10.0),
    max_backlogs    INTEGER DEFAULT 0,
    seats           INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'upcoming' CHECK(status IN ('upcoming','ongoing','completed','cancelled')),
    description     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    app_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    drive_id      INTEGER NOT NULL REFERENCES drives(drive_id) ON DELETE CASCADE,
    applied_at    TEXT DEFAULT (datetime('now')),
    round         TEXT DEFAULT 'Applied' CHECK(round IN ('Applied','Aptitude','GD','Technical','HR','Selected','Rejected')),
    notes         TEXT,
    UNIQUE(student_id, drive_id)
);

CREATE TABLE IF NOT EXISTS placements (
    placement_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL UNIQUE REFERENCES students(student_id) ON DELETE CASCADE,
    drive_id      INTEGER NOT NULL REFERENCES drives(drive_id) ON DELETE CASCADE,
    offer_date    TEXT NOT NULL,
    package_lpa   REAL NOT NULL CHECK(package_lpa > 0),
    offer_letter  TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT NOT NULL,
    operation   TEXT NOT NULL,
    record_id   INTEGER,
    details     TEXT,
    logged_at   TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
--  TRIGGERS
-- ─────────────────────────────────────────────

-- TRIGGER 1: Auto-update student status to 'placed' on placement insert
CREATE TRIGGER IF NOT EXISTS trg_student_placed
AFTER INSERT ON placements
BEGIN
    UPDATE students SET status = 'placed', updated_at = datetime('now')
    WHERE student_id = NEW.student_id;
    INSERT INTO audit_log(table_name, operation, record_id, details)
    VALUES('placements', 'INSERT', NEW.placement_id,
           'Student ' || NEW.student_id || ' placed via drive ' || NEW.drive_id);
END;

-- TRIGGER 2: Prevent double placement
CREATE TRIGGER IF NOT EXISTS trg_no_double_placement
BEFORE INSERT ON placements
BEGIN
    SELECT RAISE(ABORT, 'Student is already placed in another company.')
    WHERE EXISTS (SELECT 1 FROM placements WHERE student_id = NEW.student_id);
END;

-- TRIGGER 3: Enforce eligibility on application (CGPA & backlogs check)
CREATE TRIGGER IF NOT EXISTS trg_eligibility_check
BEFORE INSERT ON applications
BEGIN
    SELECT RAISE(ABORT, 'Student does not meet eligibility criteria (CGPA or backlogs).')
    WHERE EXISTS (
        SELECT 1 FROM students s
        JOIN drives d ON d.drive_id = NEW.drive_id
        WHERE s.student_id = NEW.student_id
          AND (s.cgpa < d.min_cgpa OR s.backlogs > d.max_backlogs)
    );
END;

-- TRIGGER 4: Audit log on student update
CREATE TRIGGER IF NOT EXISTS trg_audit_student_update
AFTER UPDATE ON students
BEGIN
    UPDATE students SET updated_at = datetime('now') WHERE student_id = NEW.student_id;
    INSERT INTO audit_log(table_name, operation, record_id, details)
    VALUES('students', 'UPDATE', NEW.student_id,
           'Status changed to ' || NEW.status);
END;

-- TRIGGER 5: Audit on application round change
CREATE TRIGGER IF NOT EXISTS trg_audit_app_round
AFTER UPDATE OF round ON applications
BEGIN
    INSERT INTO audit_log(table_name, operation, record_id, details)
    VALUES('applications', 'UPDATE', NEW.app_id,
           'Round updated to ' || NEW.round || ' for student ' || NEW.student_id);
END;

-- TRIGGER 6: Auto-update drive status to completed when all seats filled
CREATE TRIGGER IF NOT EXISTS trg_drive_seats_filled
AFTER INSERT ON placements
BEGIN
    UPDATE drives SET status = 'completed'
    WHERE drive_id = NEW.drive_id
      AND seats > 0
      AND (SELECT COUNT(*) FROM placements WHERE drive_id = NEW.drive_id) >= seats;
END;

-- ─────────────────────────────────────────────
--  VIEWS
-- ─────────────────────────────────────────────

CREATE VIEW IF NOT EXISTS vw_placement_summary AS
SELECT
    d.dept_name,
    COUNT(DISTINCT s.student_id)                               AS total_students,
    COUNT(DISTINCT p.student_id)                               AS placed_students,
    ROUND(COUNT(DISTINCT p.student_id) * 100.0 /
          NULLIF(COUNT(DISTINCT s.student_id), 0), 2)          AS placement_pct,
    ROUND(AVG(p.package_lpa), 2)                              AS avg_package,
    MAX(p.package_lpa)                                         AS highest_package,
    MIN(p.package_lpa)                                         AS lowest_package
FROM departments d
LEFT JOIN students s ON s.dept_id = d.dept_id
LEFT JOIN placements p ON p.student_id = s.student_id
GROUP BY d.dept_id;

CREATE VIEW IF NOT EXISTS vw_company_stats AS
SELECT
    c.name AS company_name, c.tier, c.sector,
    COUNT(DISTINCT a.student_id)   AS applicants,
    COUNT(DISTINCT p.student_id)   AS offers_made,
    d.package_lpa,
    d.role,
    d.drive_date
FROM companies c
JOIN drives d ON d.company_id = c.company_id
LEFT JOIN applications a ON a.drive_id = d.drive_id
LEFT JOIN placements p ON p.drive_id = d.drive_id
GROUP BY c.company_id, d.drive_id;

CREATE VIEW IF NOT EXISTS vw_student_pipeline AS
SELECT
    s.student_id, s.roll_no, s.name, d.dept_name,
    s.cgpa, s.backlogs, s.status,
    COUNT(a.app_id)      AS total_applications,
    MAX(a.round)         AS latest_round,
    p.package_lpa        AS offer_package,
    c.name               AS placed_company
FROM students s
JOIN departments d ON d.dept_id = s.dept_id
LEFT JOIN applications a ON a.student_id = s.student_id
LEFT JOIN placements p ON p.student_id = s.student_id
LEFT JOIN drives dr ON dr.drive_id = p.drive_id
LEFT JOIN companies c ON c.company_id = dr.company_id
GROUP BY s.student_id;

-- ─────────────────────────────────────────────
--  INDEXES
-- ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_students_dept    ON students(dept_id);
CREATE INDEX IF NOT EXISTS idx_students_status  ON students(status);
CREATE INDEX IF NOT EXISTS idx_applications_stu ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_drv ON applications(drive_id);
CREATE INDEX IF NOT EXISTS idx_placements_drive ON placements(drive_id);
CREATE INDEX IF NOT EXISTS idx_drives_company   ON drives(company_id);
CREATE INDEX IF NOT EXISTS idx_drives_date      ON drives(drive_date);
