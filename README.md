PlaceTrack — Placement Analytics System
DBMS Project | Full Stack Application

---

Architecture

```
placement-analytics/
├── backend/
│   ├── app.py          ← Flask REST API (Python)
│   ├── schema.sql      ← Database schema, triggers, views, indexes
│   └── placement.db    ← SQLite database (auto-generated)
└── frontend/
    └── index.html      ← Complete frontend (HTML/CSS/JS)
```

---

Setup & Run

Prerequisites
```bash
pip install flask flask-cors
```

Start Backend
```bash
cd backend
python app.py
# Server runs at http://localhost:5000
```

Open Frontend
```
Open frontend/index.html in any browser
```

---

Database Schema

Tables
| Table | Purpose |
|-------|---------|
| `departments` | Academic departments |
| `students` | Student master data |
| `companies` | Recruiting companies |
| `drives` | Placement drives per company |
| `applications` | Student ↔ Drive applications |
| `placements` | Final placement records |
| `audit_log` | Auto-generated audit trail |

---

Triggers Implemented

| Trigger | Type | Purpose |
|---------|------|---------|
| `trg_student_placed` | AFTER INSERT on placements | Auto-sets student status → 'placed', adds audit log |
| `trg_no_double_placement` | BEFORE INSERT on placements | Prevents a student from getting 2 offers (assertion) |
| `trg_eligibility_check` | BEFORE INSERT on applications | Validates CGPA & backlogs before allowing application |
| `trg_audit_student_update` | AFTER UPDATE on students | Logs every student record change |
| `trg_audit_app_round` | AFTER UPDATE on applications | Logs every round progression |
| `trg_drive_seats_filled` | AFTER INSERT on placements | Auto-marks drive 'completed' when seats fill up |

---

Views

| View | Description |
|------|-------------|
| `vw_placement_summary` | Dept-wise placement % and package stats |
| `vw_company_stats` | Company applicants vs offers, by drive |
| `vw_student_pipeline` | Full student journey with latest round & offer |

---

Constraints & Assertions

- **CHECK**: `cgpa BETWEEN 0 AND 10`, `package_lpa > 0`, `backlogs >= 0`
- **UNIQUE**: `roll_no`, `email`, `(student_id, drive_id)` in applications
- **NOT NULL**: All critical fields
- **FOREIGN KEY**: Cascade/Restrict rules enforced
- **ENUM-like CHECK**: `status`, `tier`, `round` columns restricted to valid values
- **Assertion (via Trigger)**: No double placement, eligibility on apply

---

Normalization

- **1NF**: All atomic values, single-valued attributes
- **2NF**: No partial functional dependencies
- **3NF**: No transitive dependencies (dept data not repeated in students)
- **BCNF**: Every determinant is a candidate key

---

CRUD Operations

| Entity | Create | Read | Update | Delete |
|--------|--------|------|--------|--------|
| Students | POST /api/students | GET /api/students | PUT /api/students/:id | DELETE /api/students/:id |
| Companies | POST /api/companies | GET /api/companies | PUT /api/companies/:id | DELETE /api/companies/:id |
| Drives | POST /api/drives | GET /api/drives | PUT /api/drives/:id | DELETE /api/drives/:id |
| Applications | POST /api/applications | GET /api/applications | PUT /api/applications/:id/round | — |
| Placements | POST /api/placements | GET /api/placements | — | — |

---

ER Diagram

```
departments ──< students >── applications ──< drives >── companies
                  │                               │
                  └──────── placements ───────────┘
                                │
                            audit_log
```

Cardinality:
- Department → Students: 1:N
- Company → Drives: 1:N
- Student ↔ Drive: M:N (via applications)
- Student → Placement: 1:1 (each student placed max once)

---

Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS |
| Backend | Python 3, Flask, Flask-CORS |
| Database | SQLite 3 (via Python sqlite3) |
| ORM | Raw SQL (demonstrating DBMS concepts) |
