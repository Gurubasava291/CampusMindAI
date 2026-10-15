import datetime
import secrets
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash
from models.db import get_db, query_db, execute_db


def rotate_legacy_seed_passwords():
    """Replace legacy demo passwords and apply configured seed credentials."""
    seeded_accounts = [
        ('admin@dsu.edu.in', 'admin', 'admin123', 'SEEDED_ADMIN_PASSWORD'),
        ('staff.plumbing@dsu.edu.in', 'staff', 'staff123', 'SEEDED_STAFF_PASSWORD'),
        ('staff.electric@dsu.edu.in', 'staff', 'staff123', None),
        ('staff.sanitation@dsu.edu.in', 'staff', 'staff123', None),
        ('student@dsu.edu.in', 'student', 'student123', 'SEEDED_STUDENT_PASSWORD'),
        ('arjun.kumar@dsu.edu.in', 'student', 'student123', None),
        ('sneha.patel@dsu.edu.in', 'student', 'student123', None),
        ('karthik.m@dsu.edu.in', 'student', 'student123', None)
    ]

    for email, role, legacy_password, config_key in seeded_accounts:
        user = query_db(
            "SELECT id, password_hash, password_changed_at FROM users WHERE email = ? AND role = ?",
            (email, role),
            one=True
        )
        if not user:
            continue
        if user['password_changed_at']:
            continue

        configured_password = current_app.config.get(config_key) if config_key else None
        has_legacy_password = check_password_hash(user['password_hash'], legacy_password)
        has_configured_password = (
            configured_password and check_password_hash(user['password_hash'], configured_password)
        )
        if configured_password and not has_configured_password:
            replacement = configured_password
        elif has_legacy_password:
            replacement = secrets.token_urlsafe(32)
        else:
            continue
        execute_db(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(replacement), user['id'])
        )


def _seed_password_hash(config_key=None):
    password = current_app.config.get(config_key) if config_key else None
    return generate_password_hash(password or secrets.token_urlsafe(32))

def seed_database(force=False):
    """
    Populate database with rich, realistic sample data for Dayananda Sagar University.
    All sample data is explicitly tagged (is_demo_sample = 1).
    """
    db = get_db()

    # Check if already seeded
    existing_users = query_db("SELECT COUNT(*) as c FROM users", one=True)['c']
    if existing_users > 0 and not force:
        return {"status": "already_seeded", "message": "Database already contains data."}

    # Clear existing if force
    if force:
        tables = [
            'audit_logs', 'notifications', 'challenge_participations', 'challenges',
            'user_badges', 'green_badges', 'sustainability_goals', 'waste_records',
            'water_readings', 'energy_readings', 'report_comments', 'report_history',
            'reports', 'tour_stops', 'campus_locations', 'users', 'departments'
        ]
        for tbl in tables:
            db.execute(f"DELETE FROM {tbl};")
            db.execute(f"DELETE FROM sqlite_sequence WHERE name='{tbl}';")
        db.commit()

    # 1. Departments
    depts = [
        ("Department of Mechanical & Civil Facilities", "FAC-MECH", "facilities.civil@dsu.edu.in", "Estate Maintenance Building, Harohalli"),
        ("Electrical Maintenance & Renewable Energy", "FAC-ELEC", "electrical.cell@dsu.edu.in", "Substation Complex, Harohalli"),
        ("Campus Greenery, Grounds & Landscaping", "FAC-GRN", "greenery@dsu.edu.in", "Horticulture Wing, Harohalli"),
        ("Housekeeping, Sanitation & Waste Management", "FAC-SAN", "sanitation@dsu.edu.in", "Central Utility Block, Harohalli"),
        ("School of Engineering", "DSU-SOE", "soe.office@dsu.edu.in", "Academic Block A, Harohalli"),
        ("School of Health Sciences", "DSU-SHS", "shs.office@dsu.edu.in", "City Campus, Kudlu Gate"),
        ("School of Commerce & Management Studies", "DSU-SCM", "scms.office@dsu.edu.in", "Academic Block B, Harohalli"),
    ]
    for name, code, email, loc in depts:
        db.execute(
            "INSERT INTO departments (name, code, contact_email, building_location) VALUES (?, ?, ?, ?)",
            (name, code, email, loc)
        )
    db.commit()

    # 2. Users (Admin, Staff, Students)
    pwd_admin = _seed_password_hash('SEEDED_ADMIN_PASSWORD')
    pwd_staff = _seed_password_hash('SEEDED_STAFF_PASSWORD')
    pwd_student = _seed_password_hash('SEEDED_STUDENT_PASSWORD')

    users_data = [
        # Admin
        ("admin", "admin@dsu.edu.in", pwd_admin, "Dr. K. S. Sridhar", "admin", 1, "Main Innovation Campus (Harohalli)", 850, "#1E3F20"),
        # Staff
        ("staff_plumbing", "staff.plumbing@dsu.edu.in", pwd_staff, "Naveen Kumar (Facilities)", "staff", 1, "Main Innovation Campus (Harohalli)", 420, "#2E7D32"),
        ("staff_electric", "staff.electric@dsu.edu.in", _seed_password_hash(), "Ramesh Gowda (Electrical)", "staff", 2, "Main Innovation Campus (Harohalli)", 390, "#1565C0"),
        ("staff_sanitation", "staff.sanitation@dsu.edu.in", _seed_password_hash(), "Muniraju V. (Housekeeping)", "staff", 4, "Main Innovation Campus (Harohalli)", 280, "#6A1B9A"),
        # Students
        ("student", "student@dsu.edu.in", pwd_student, "Pooja Rao", "student", 5, "Main Innovation Campus (Harohalli)", 320, "#2E7D32"),
        ("arjun_kumar", "arjun.kumar@dsu.edu.in", _seed_password_hash(), "Arjun Kumar", "student", 5, "Main Innovation Campus (Harohalli)", 210, "#00897B"),
        ("sneha_patel", "sneha.patel@dsu.edu.in", _seed_password_hash(), "Sneha Patel", "student", 6, "City Campus (Kudlu Gate)", 540, "#D81B60"),
        ("karthik_m", "karthik.m@dsu.edu.in", _seed_password_hash(), "Karthik Menon", "student", 7, "Main Innovation Campus (Harohalli)", 160, "#FB8C00"),
    ]
    for u, em, pw, fn, r, dep, camp, pts, col in users_data:
        db.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role, department_id, campus, green_points, avatar_color)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (u, em, pw, fn, r, dep, camp, pts, col)
        )
    db.commit()

    # 3. Campus Locations
    locations = [
        ("Main Innovation Campus (Harohalli)", "Academic Block A (Engineering)", "Ground Floor", "North Restroom Wing", 12.6585, 77.4472),
        ("Main Innovation Campus (Harohalli)", "Academic Block A (Engineering)", "2nd Floor", "IoT & Embedded Systems Lab 204", 12.6586, 77.4474),
        ("Main Innovation Campus (Harohalli)", "Academic Block A (Engineering)", "3rd Floor", "Lecture Hall 302", 12.6587, 77.4473),
        ("Main Innovation Campus (Harohalli)", "Academic Block B (Basic Sciences)", "1st Floor", "Corridor Central Atrium", 12.6590, 77.4478),
        ("Main Innovation Campus (Harohalli)", "Central Research & Innovation Hub", "Ground Floor", "Makerspace & Prototyping Bay", 12.6580, 77.4480),
        ("Main Innovation Campus (Harohalli)", "Dr. Premachandra Sagar Auditorium", "Plaza", "Outdoor Amphitheatre Walkway", 12.6578, 77.4468),
        ("Main Innovation Campus (Harohalli)", "Student Food Court & Dining", "Courtyard", "Waste Collection Quadrangle", 12.6575, 77.4485),
        ("Main Innovation Campus (Harohalli)", "Sports Complex & Hostel Block", "Entrance", "East Lawn & Bicycle Parking", 12.6568, 77.4490),
        ("City Campus (Kudlu Gate)", "School of Health Sciences", "2nd Floor", "Biochemistry Wing", 12.8906, 77.6416),
        ("City Campus (Kudlu Gate)", "Administrative Block", "Ground Floor", "Main Reception & Visitor Lounge", 12.8908, 77.6418),
    ]
    for camp, bld, fl, zn, lat, lng in locations:
        db.execute(
            """INSERT INTO campus_locations (campus_name, building_name, floor, zone_or_wing, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (camp, bld, fl, zn, lat, lng)
        )
    db.commit()

    # 4. Badges
    badges = [
        ("SCOUT", "Eco Scout", "Awarded for reporting your first verified environmental issue.", "bi-patch-check-fill", 50),
        ("WATER_GUARD", "Water Guardian", "Recognizes active reporting and conservation of campus water resources.", "bi-droplet-fill", 150),
        ("WATT_SAVER", "Watt Saver", "Helped campus prevent electrical wastage and phantom loads.", "bi-lightning-charge-fill", 250),
        ("ZERO_WASTE", "Zero Waste Champion", "Mastered waste segregation and led recycling campaigns.", "bi-recycle", 350),
        ("INNOVATOR", "Green Innovator", "Achieved top sustainability engagement across Dayananda Sagar University.", "bi-trophy-fill", 500),
    ]
    for code, name, desc, icon, thresh in badges:
        db.execute(
            "INSERT INTO green_badges (code, name, description, icon, points_threshold) VALUES (?, ?, ?, ?, ?)",
            (code, name, desc, icon, thresh)
        )
    db.commit()

    # Award initial badges to seeded students
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (5, 1)") # Pooja: Eco Scout
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (5, 2)") # Pooja: Water Guardian
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (5, 3)") # Pooja: Watt Saver
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (7, 1)") # Sneha: Eco Scout
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (7, 2)") # Sneha: Water Guardian
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (7, 3)") # Sneha: Watt Saver
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (7, 4)") # Sneha: Zero Waste
    db.execute("INSERT INTO user_badges (user_id, badge_id) VALUES (7, 5)") # Sneha: Green Innovator
    db.commit()

    # 6. Environmental Reports with complete lifecycle
    reports = [
        (
            "CP-2026-0001", 5, "Continuous Urinal Flush Valve Seepage",
            "Urinal sensor valve is stuck open in continuous flush mode, losing water continuously onto the floor.",
            "water", "high", "resolved", 1, "3rd stall from entrance", 0,
            0.94, "High volume continuous freshwater loss detected; valve diaphragm failure.",
            2, 1, "2026-10-12", "2026-10-13 14:30:00",
            "Replaced solenoid sensor coil and calibrated timer delay to 4 seconds. Tested seal.", 1
        ),
        (
            "CP-2026-0002", 6, "3x High-Power Split AC Units Left Running Overnight",
            "IoT Lab was locked after 6 PM yesterday but all three 2-ton cassette AC units remained powered at 18C.",
            "electricity", "high", "resolved", 2, "Room 204 Main Lab", 0,
            0.92, "High phantom cooling load in unoccupied lab; thermostat set below recommended 24C.",
            3, 2, "2026-10-13", "2026-10-14 10:15:00",
            "Turned off ACs, installed automated digital timer relay on power distribution sub-board.", 1
        ),
        (
            "CP-2026-0003", 5, "Overflown Dry Waste Bin with Plastic Wrappers",
            "Blue recycling bin outside Food Court courtyard is overflowing with disposable cutlery and cartons.",
            "waste", "medium", "in_progress", 7, "Courtyard East Corner", 0,
            0.89, "Collection frequency exceeded by midday lunch rush. Requires additional secondary bin.",
            4, 4, "2026-10-16", None,
            None, 1
        ),
        (
            "CP-2026-0004", 7, "Underground Irrigation Pipe Leak near Amphitheatre",
            "Recycled STP sprinkler line has cracked along the stone pathway; water bubbling up through grass.",
            "water", "critical", "assigned", 6, "Pathway border near Gulmohar tree", 0,
            0.96, "Pressurized pipe rupture risk undermining pathway pavers and causing lawn waterlogging.",
            2, 1, "2026-10-15", None,
            None, 1
        ),
        (
            "CP-2026-0005", 8, "Flickering High-Bay LED Lights in Prototyping Bay",
            "Four overhead LED lamps in Makerspace are rapidly flickering, causing visual strain and buzzing noise.",
            "electricity", "medium", "verified", 5, "Bay Area 2B", 0,
            0.87, "Probable LED driver capacitor failure or loose phase wiring.",
            None, 2, "2026-10-17", None,
            None, 1
        ),
        (
            "CP-2026-0006", None, "Unsegregated Chemical Solvent Containers Left Uncapped",
            "Empty acetone and ethanol reagent bottles placed in standard cardboard waste bin instead of chemical cage.",
            "waste", "high", "assigned", 9, "Biochemistry Lab Wash Area", 1,
            0.91, "Hazardous waste containment violation; volatile organic fumes in indoor teaching area.",
            4, 4, "2026-10-15", None,
            None, 1
        ),
        (
            "CP-2026-0007", 5, "Damaged Solar Inverter Rain Cover on Roof A",
            "Protective polycarbonate weather canopy for Solar Inverter 2 has come loose in wind.",
            "infrastructure", "medium", "submitted", 8, "Rooftop Solar Plant A", 0,
            0.85, "Pre-monsoon wind hazard; water ingress risk to electrical components.",
            None, 2, "2026-10-18", None,
            None, 1
        )
    ]

    for rep in reports:
        num, uid, title, desc, cat, prio, st, loc_id, spot, anon, conf, reas, assigned_u, assigned_d, due, res_at, notes, is_demo = rep
        db.execute(
            """INSERT INTO reports (
                report_number, user_id, title, description, category, priority, status,
                location_id, specific_spot, is_anonymous, ai_confidence, ai_reasoning,
                assigned_to_user_id, assigned_department_id, due_date, resolved_at,
                resolution_notes, is_demo_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (num, uid, title, desc, cat, prio, st, loc_id, spot, anon, conf, reas, assigned_u, assigned_d, due, res_at, notes, is_demo)
        )
        report_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Audit history for each
        db.execute(
            "INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment) VALUES (?, ?, ?, ?, ?)",
            (report_id, uid or 1, None, 'submitted', "Initial environmental report submitted via CampusPulse.")
        )
        if st in ('verified', 'assigned', 'in_progress', 'resolved'):
            db.execute(
                "INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment) VALUES (?, ?, ?, ?, ?)",
                (report_id, 1, 'submitted', 'verified', "Report validated by Campus Facilities Coordinator.")
            )
        if st in ('assigned', 'in_progress', 'resolved'):
            db.execute(
                "INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment) VALUES (?, ?, ?, ?, ?)",
                (report_id, 1, 'verified', 'assigned', f"Assigned to maintenance technician with due date {due}.")
            )
        if st in ('in_progress', 'resolved'):
            db.execute(
                "INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment) VALUES (?, ?, ?, ?, ?)",
                (report_id, assigned_u or 2, 'assigned', 'in_progress', "Technician arrived on-site with replacement parts.")
            )
        if st == 'resolved':
            db.execute(
                "INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment) VALUES (?, ?, ?, ?, ?)",
                (report_id, assigned_u or 2, 'in_progress', 'resolved', notes or "Repairs verified and completed successfully.")
            )
    db.commit()

    # 7. Energy Readings (Past 7 days)
    for i in range(7, 0, -1):
        dt = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        kwh = round(1420.0 + (i * 25) - (15 if i % 2 == 0 else -20), 1)
        solar = round(480.0 + (i * 12) + (30 if i % 3 == 0 else -10), 1)
        peak = round(165.0 + (i * 2.5), 1)
        db.execute(
            """INSERT INTO energy_readings (campus_name, building_name, meter_name, reading_date, kwh_consumed, peak_load_kw, solar_generated_kwh, notes, is_demo_sample, logged_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 3)""",
            ("Main Innovation Campus (Harohalli)", "Academic Block A (Engineering)", "MTR-BLKA-MAIN", dt, kwh, peak, solar, "Daily main feeder log with rooftop solar generation.")
        )
    db.commit()

    # 8. Water Readings (Past 7 days)
    for i in range(7, 0, -1):
        dt = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        liters = 24500 - (i * 350)
        recycled = 11200 + (i * 180)
        rainwater = 4500 if i > 3 else 0
        db.execute(
            """INSERT INTO water_readings (campus_name, location_name, reading_date, liters_consumed, recycled_water_liters, rainwater_harvested_liters, leak_detected, notes, is_demo_sample, logged_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, 1, 2)""",
            ("Main Innovation Campus (Harohalli)", "Central Hydro-Distribution Pump", dt, liters, recycled, rainwater, "Standard daily automated meter logging.")
        )
    db.commit()

    # 9. Waste Records (Past 4 weeks)
    for i in range(4, 0, -1):
        dt = (datetime.date.today() - datetime.timedelta(weeks=i)).isoformat()
        db.execute(
            """INSERT INTO waste_records (campus_name, record_date, organic_kg, recyclable_kg, ewaste_kg, hazardous_kg, composted_kg, landfill_diverted_pct, is_demo_sample, logged_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 4)""",
            ("Main Innovation Campus (Harohalli)", dt, 380.0 + (i * 15), 240.0 + (i * 20), 18.5, 6.0, 350.0, 84.5 + (i * 0.8))
        )
    db.commit()

    # 10. Sustainability Goals
    goals = [
        ("Reduce Grid Electricity Consumption by 15%", "energy", 15.0, 11.2, "% reduction", "2026-12-31", "Expand rooftop solar arrays on Academic Block B and enforce lab AC setpoints.", "in_progress", 1),
        ("Conserve 500,000 Liters of Freshwater Monthly", "water", 500000.0, 420000.0, "Liters", "2026-11-30", "Through active leak reporting, aerator retrofit, and 100% STP treated water irrigation.", "in_progress", 1),
        ("Achieve 90% Campus Waste Diversion Rate", "waste", 90.0, 85.5, "% diverted", "2026-12-15", "Eliminate single-use plastics and increase organic composting yield.", "in_progress", 1),
        ("Tag and Map 500 Campus Trees on DSU GIS", "greenery", 500.0, 340.0, "Trees tagged", "2026-11-15", "Student botany and environmental engineering inventory initiative.", "in_progress", 1),
    ]
    for title, cat, tgt, curr, unit, dline, desc, st, demo in goals:
        db.execute(
            """INSERT INTO sustainability_goals (title, category, target_value, current_value, unit, deadline, description, status, is_demo_sample)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, cat, tgt, curr, unit, dline, desc, st, demo)
        )
    db.commit()

    # 11. Active Green Challenges
    challenges = [
        ("Kill the Phantom Load Challenge", "electricity", "Unplug computer lab monitors, chargers, and projectors before leaving for the weekend. Snap a photo of your green lab.", 75, "2026-10-01", "2026-10-31", "bi-plug-fill", 48, 1),
        ("Zero Single-Use Plastic Week", "waste", "Use reusable steel bottles and carry cotton bags across all DSU food courts and bookshops.", 100, "2026-10-10", "2026-10-24", "bi-cup-straw", 82, 1),
        ("DSU Harohalli Tree Tagging Drive", "greenery", "Join the Horticulture team to record species, canopy size, and QR-tag native trees around the Amphitheatre.", 150, "2026-10-15", "2026-11-05", "bi-tree-fill", 36, 1),
        ("Water Sentinel: Report 2 Leaks", "water", "Identify and report at least two dripping faucets or faulty flush valves in academic rest facilities.", 120, "2026-10-01", "2026-10-31", "bi-droplet-half", 29, 1),
    ]
    for title, cat, desc, pts, sdt, edt, icon, pcount, act in challenges:
        db.execute(
            """INSERT INTO challenges (title, category, description, points_reward, start_date, end_date, icon, participants_count, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, cat, desc, pts, sdt, edt, icon, pcount, act)
        )
    db.commit()

    # Initial challenge participation
    db.execute("INSERT OR IGNORE INTO challenge_participations (challenge_id, user_id, status) VALUES (1, 5, 'completed')")
    db.execute("INSERT OR IGNORE INTO challenge_participations (challenge_id, user_id, status) VALUES (2, 5, 'joined')")
    db.execute("INSERT OR IGNORE INTO challenge_participations (challenge_id, user_id, status) VALUES (2, 7, 'completed')")
    db.commit()

    # 12. Initial Notifications
    db.execute(
        """INSERT INTO notifications (user_id, title, message, link)
           VALUES (?, ?, ?, ?)""",
        (5, "Report CP-2026-0001 Resolved", "Your report regarding urinal seepage in Block A has been repaired and verified by Naveen Kumar.", "/reports/1")
    )
    db.execute(
        """INSERT INTO notifications (user_id, title, message, link)
           VALUES (?, ?, ?, ?)""",
        (5, "Welcome to CampusPulse DSU!", "Report campus environmental issues and earn green points.", "/report-issue")
    )
    db.commit()

    # 13. Audit Log
    db.execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (1, 'SYSTEM_INIT', 'SYSTEM', 1, 'Seeded Dayananda Sagar University demo database with verified records.', '127.0.0.1')"""
    )
    db.commit()

    return {"status": "success", "message": "Successfully seeded Dayananda Sagar University demo database."}
