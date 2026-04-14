"""
Placement Analytics System — Flask Backend
Full CRUD + DBMS concepts: triggers, views, constraints, audit log
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
import sqlite3, os, json

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "placement.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# ─────────────────────────────────────
#  DB CONNECTION HELPERS
# ─────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db: db.close()

def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def mutate(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def rows_to_list(rows):
    return [dict(r) for r in rows]

def init_db():
    with app.app_context():
        db = sqlite3.connect(DB_PATH)
        db.execute("PRAGMA foreign_keys = ON")
        with open(SCHEMA_PATH, 'r') as f:
            db.executescript(f.read())
        # Seed data if empty
        if not db.execute("SELECT 1 FROM departments LIMIT 1").fetchone():
            seed_data(db)
        db.commit()
        db.close()

def seed_data(db):
    depts = [
        ("Computer Science", "Dr. Sharma"),
        ("Information Technology", "Dr. Mehta"),
        ("Electronics & Comm.", "Dr. Rao"),
        ("Mechanical", "Dr. Nair"),
        ("Civil", "Dr. Iyer"),
    ]
    db.executemany("INSERT INTO departments(dept_name,hod_name) VALUES(?,?)", depts)

    students = [
        ("CS001","Aarav Patel","aarav@college.edu",1,8.9,0,2024,"9876543210"),
        ("CS002","Sneha Reddy","sneha@college.edu",1,7.5,1,2024,"9876543211"),
        ("CS003","Karan Joshi","karan@college.edu",1,9.2,0,2024,"9876543212"),
        ("IT001","Priya Singh","priya@college.edu",2,8.1,0,2024,"9876543213"),
        ("IT002","Rahul Kumar","rahul@college.edu",2,6.8,2,2024,"9876543214"),
        ("EC001","Ananya Nair","ananya@college.edu",3,8.5,0,2024,"9876543215"),
        ("EC002","Vikram Shah","vikram@college.edu",3,7.2,1,2024,"9876543216"),
        ("ME001","Rohit Gupta","rohit@college.edu",4,7.8,0,2024,"9876543217"),
        ("CS004","Divya Menon","divya@college.edu",1,9.5,0,2024,"9876543218"),
        ("IT003","Arjun Das","arjun@college.edu",2,8.3,0,2024,"9876543219"),
    ]
    db.executemany(
        "INSERT INTO students(roll_no,name,email,dept_id,cgpa,backlogs,batch_year,phone) VALUES(?,?,?,?,?,?,?,?)",
        students
    )

    companies = [
        ("Google","Technology","Tier-1","https://google.com","hr@google.com"),
        ("TCS","IT Services","Tier-2","https://tcs.com","hr@tcs.com"),
        ("Infosys","IT Services","Tier-2","https://infosys.com","hr@infosys.com"),
        ("Amazon","E-Commerce","Tier-1","https://amazon.com","hr@amazon.com"),
        ("Wipro","IT Services","Tier-3","https://wipro.com","hr@wipro.com"),
        ("Microsoft","Technology","Tier-1","https://microsoft.com","hr@microsoft.com"),
    ]
    db.executemany(
        "INSERT INTO companies(name,sector,tier,website,hr_contact) VALUES(?,?,?,?,?)",
        companies
    )

    drives = [
        (1,"2024-03-10","SWE",42.0,7.5,0,5,"completed"),
        (2,"2024-03-15","Systems Engineer",7.0,6.0,2,20,"completed"),
        (3,"2024-03-20","Associate Engineer",6.5,6.0,2,15,"completed"),
        (4,"2024-04-01","SDE-1",35.0,8.0,0,8,"upcoming"),
        (5,"2024-04-05","Developer",5.5,6.0,3,25,"upcoming"),
        (6,"2024-04-10","SDE-2",55.0,8.5,0,3,"upcoming"),
    ]
    db.executemany(
        "INSERT INTO drives(company_id,drive_date,role,package_lpa,min_cgpa,max_backlogs,seats,status) VALUES(?,?,?,?,?,?,?,?)",
        drives
    )

    # Applications (bypass trigger by inserting directly)
    apps = [
        (1,1),(2,2),(3,1),(4,1),(5,2),(6,1),(7,2),(8,3),(9,1),(10,2),
        (3,2),(4,2),(1,3),(6,3),(9,3),
    ]
    for sid, did in apps:
        try:
            db.execute("INSERT INTO applications(student_id,drive_id,round) VALUES(?,?,'Applied')", (sid, did))
        except: pass

    # Update some rounds
    rounds = [
        (1,1,"Selected"),(3,1,"Selected"),(9,1,"Selected"),
        (4,1,"HR"),(6,1,"Technical"),
        (2,2,"Selected"),(5,2,"Selected"),(7,2,"Rejected"),
    ]
    for sid, did, rnd in rounds:
        db.execute("UPDATE applications SET round=? WHERE student_id=? AND drive_id=?", (rnd, sid, did))

    # Placements (bypass double-placement trigger for seed)
    placements_data = [
        (1,1,"2024-03-12",42.0),(3,1,"2024-03-12",42.0),(9,1,"2024-03-12",42.0),
        (2,2,"2024-03-17",7.0),(5,2,"2024-03-17",7.0),
    ]
    for sid, did, dt, pkg in placements_data:
        try:
            db.execute("INSERT INTO placements(student_id,drive_id,offer_date,package_lpa) VALUES(?,?,?,?)",
                      (sid, did, dt, pkg))
            db.execute("UPDATE students SET status='placed' WHERE student_id=?", (sid,))
        except: pass


# ─────────────────────────────────────
#  DASHBOARD / ANALYTICS
# ─────────────────────────────────────

@app.route("/api/dashboard")
def dashboard():
    stats = {
        "total_students": query("SELECT COUNT(*) c FROM students", one=True)["c"],
        "placed_students": query("SELECT COUNT(*) c FROM placements", one=True)["c"],
        "total_companies": query("SELECT COUNT(*) c FROM companies", one=True)["c"],
        "active_drives": query("SELECT COUNT(*) c FROM drives WHERE status IN ('upcoming','ongoing')", one=True)["c"],
        "avg_package": round(query("SELECT AVG(package_lpa) v FROM placements", one=True)["v"] or 0, 2),
        "highest_package": query("SELECT MAX(package_lpa) v FROM placements", one=True)["v"] or 0,
        "dept_summary": rows_to_list(query("SELECT * FROM vw_placement_summary")),
        "company_stats": rows_to_list(query("SELECT * FROM vw_company_stats")),
        "recent_placements": rows_to_list(query("""
            SELECT s.name, c.name company, p.package_lpa, p.offer_date
            FROM placements p
            JOIN students s ON s.student_id=p.student_id
            JOIN drives d ON d.drive_id=p.drive_id
            JOIN companies c ON c.company_id=d.company_id
            ORDER BY p.offer_date DESC LIMIT 5
        """)),
        "package_distribution": rows_to_list(query("""
            SELECT 
                CASE WHEN p.package_lpa < 5 THEN '<5 LPA'
                     WHEN p.package_lpa < 10 THEN '5-10 LPA'
                     WHEN p.package_lpa < 20 THEN '10-20 LPA'
                     ELSE '>20 LPA' END AS range,
                COUNT(*) AS count
            FROM placements p GROUP BY range
        """)),
    }
    return jsonify(stats)

# ─────────────────────────────────────
#  STUDENTS CRUD
# ─────────────────────────────────────

@app.route("/api/students")
def get_students():
    search = request.args.get("search","")
    dept = request.args.get("dept","")
    status = request.args.get("status","")
    sql = "SELECT * FROM vw_student_pipeline WHERE 1=1"
    args = []
    if search:
        sql += " AND (name LIKE ? OR roll_no LIKE ?)"
        args += [f"%{search}%", f"%{search}%"]
    if dept:
        sql += " AND dept_name=?"
        args.append(dept)
    if status:
        sql += " AND status=?"
        args.append(status)
    return jsonify(rows_to_list(query(sql, args)))

@app.route("/api/students/<int:sid>")
def get_student(sid):
    s = query("SELECT * FROM students WHERE student_id=?", (sid,), one=True)
    if not s: return jsonify({"error":"Not found"}), 404
    apps = rows_to_list(query("""
        SELECT a.*, c.name company, d.role, d.package_lpa, d.drive_date
        FROM applications a
        JOIN drives d ON d.drive_id=a.drive_id
        JOIN companies c ON c.company_id=d.company_id
        WHERE a.student_id=?
    """, (sid,)))
    return jsonify({**dict(s), "applications": apps})

@app.route("/api/students", methods=["POST"])
def create_student():
    d = request.json
    try:
        sid = mutate("""
            INSERT INTO students(roll_no,name,email,dept_id,cgpa,backlogs,batch_year,phone)
            VALUES(?,?,?,?,?,?,?,?)
        """, (d["roll_no"],d["name"],d["email"],d["dept_id"],
              d["cgpa"],d.get("backlogs",0),d["batch_year"],d.get("phone","")))
        mutate("INSERT INTO audit_log(table_name,operation,record_id,details) VALUES('students','INSERT',?,?)",
               (sid, f"New student {d['name']} added"))
        return jsonify({"message":"Student created","id":sid}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

@app.route("/api/students/<int:sid>", methods=["PUT"])
def update_student(sid):
    d = request.json
    try:
        mutate("""
            UPDATE students SET name=?,email=?,cgpa=?,backlogs=?,phone=?,dept_id=?
            WHERE student_id=?
        """, (d["name"],d["email"],d["cgpa"],d["backlogs"],d.get("phone",""),d["dept_id"],sid))
        return jsonify({"message":"Updated"})
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

@app.route("/api/students/<int:sid>", methods=["DELETE"])
def delete_student(sid):
    mutate("DELETE FROM students WHERE student_id=?", (sid,))
    return jsonify({"message":"Deleted"})

# ─────────────────────────────────────
#  COMPANIES CRUD
# ─────────────────────────────────────

@app.route("/api/companies")
def get_companies():
    return jsonify(rows_to_list(query("SELECT * FROM companies ORDER BY tier, name")))

@app.route("/api/companies", methods=["POST"])
def create_company():
    d = request.json
    try:
        cid = mutate("INSERT INTO companies(name,sector,tier,website,hr_contact) VALUES(?,?,?,?,?)",
                     (d["name"],d["sector"],d["tier"],d.get("website",""),d.get("hr_contact","")))
        return jsonify({"message":"Company created","id":cid}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

@app.route("/api/companies/<int:cid>", methods=["PUT"])
def update_company(cid):
    d = request.json
    mutate("UPDATE companies SET name=?,sector=?,tier=?,website=?,hr_contact=? WHERE company_id=?",
           (d["name"],d["sector"],d["tier"],d.get("website",""),d.get("hr_contact",""),cid))
    return jsonify({"message":"Updated"})

@app.route("/api/companies/<int:cid>", methods=["DELETE"])
def delete_company(cid):
    mutate("DELETE FROM companies WHERE company_id=?", (cid,))
    return jsonify({"message":"Deleted"})

# ─────────────────────────────────────
#  DRIVES CRUD
# ─────────────────────────────────────

@app.route("/api/drives")
def get_drives():
    return jsonify(rows_to_list(query("""
        SELECT d.*, c.name company_name, c.tier, c.sector,
               COUNT(a.app_id) applicants
        FROM drives d
        JOIN companies c ON c.company_id=d.company_id
        LEFT JOIN applications a ON a.drive_id=d.drive_id
        GROUP BY d.drive_id ORDER BY d.drive_date DESC
    """)))

@app.route("/api/drives", methods=["POST"])
def create_drive():
    d = request.json
    try:
        did = mutate("""
            INSERT INTO drives(company_id,drive_date,role,package_lpa,min_cgpa,max_backlogs,seats,description)
            VALUES(?,?,?,?,?,?,?,?)
        """, (d["company_id"],d["drive_date"],d["role"],d["package_lpa"],
              d.get("min_cgpa",6.0),d.get("max_backlogs",0),d.get("seats",0),d.get("description","")))
        return jsonify({"message":"Drive created","id":did}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

@app.route("/api/drives/<int:did>", methods=["PUT"])
def update_drive(did):
    d = request.json
    mutate("""
        UPDATE drives SET role=?,package_lpa=?,min_cgpa=?,max_backlogs=?,seats=?,status=?,description=?
        WHERE drive_id=?
    """, (d["role"],d["package_lpa"],d.get("min_cgpa",6.0),
          d.get("max_backlogs",0),d.get("seats",0),d.get("status","upcoming"),
          d.get("description",""),did))
    return jsonify({"message":"Updated"})

@app.route("/api/drives/<int:did>", methods=["DELETE"])
def delete_drive(did):
    mutate("DELETE FROM drives WHERE drive_id=?", (did,))
    return jsonify({"message":"Deleted"})

# ─────────────────────────────────────
#  APPLICATIONS
# ─────────────────────────────────────

@app.route("/api/applications")
def get_applications():
    drive_id = request.args.get("drive_id")
    sql = """
        SELECT a.*, s.name student_name, s.roll_no, s.cgpa,
               c.name company, d.role
        FROM applications a
        JOIN students s ON s.student_id=a.student_id
        JOIN drives d ON d.drive_id=a.drive_id
        JOIN companies c ON c.company_id=d.company_id
    """
    args = []
    if drive_id:
        sql += " WHERE a.drive_id=?"
        args.append(drive_id)
    sql += " ORDER BY a.applied_at DESC"
    return jsonify(rows_to_list(query(sql, args)))

@app.route("/api/applications", methods=["POST"])
def create_application():
    d = request.json
    try:
        aid = mutate("INSERT INTO applications(student_id,drive_id) VALUES(?,?)",
                     (d["student_id"], d["drive_id"]))
        return jsonify({"message":"Applied successfully","id":aid}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

@app.route("/api/applications/<int:aid>/round", methods=["PUT"])
def update_round(aid):
    d = request.json
    mutate("UPDATE applications SET round=?,notes=? WHERE app_id=?",
           (d["round"], d.get("notes",""), aid))
    return jsonify({"message":"Round updated"})

# ─────────────────────────────────────
#  PLACEMENTS
# ─────────────────────────────────────

@app.route("/api/placements")
def get_placements():
    return jsonify(rows_to_list(query("""
        SELECT p.*, s.name student_name, s.roll_no, d.dept_name,
               c.name company, c.tier, dr.role, dr.drive_date
        FROM placements p
        JOIN students s ON s.student_id=p.student_id
        JOIN departments d ON d.dept_id=s.dept_id
        JOIN drives dr ON dr.drive_id=p.drive_id
        JOIN companies c ON c.company_id=dr.company_id
        ORDER BY p.offer_date DESC
    """)))

@app.route("/api/placements", methods=["POST"])
def create_placement():
    d = request.json
    try:
        pid = mutate("""
            INSERT INTO placements(student_id,drive_id,offer_date,package_lpa,offer_letter)
            VALUES(?,?,?,?,?)
        """, (d["student_id"],d["drive_id"],d["offer_date"],d["package_lpa"],d.get("offer_letter","")))
        return jsonify({"message":"Placement recorded","id":pid}), 201
    except sqlite3.IntegrityError as e:
        return jsonify({"error":str(e)}), 400

# ─────────────────────────────────────
#  DEPARTMENTS & AUDIT LOG
# ─────────────────────────────────────

@app.route("/api/departments")
def get_departments():
    return jsonify(rows_to_list(query("SELECT * FROM departments ORDER BY dept_name")))

@app.route("/api/audit-log")
def get_audit_log():
    return jsonify(rows_to_list(query("SELECT * FROM audit_log ORDER BY logged_at DESC LIMIT 50")))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
