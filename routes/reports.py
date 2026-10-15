import os
import uuid
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from werkzeug.utils import secure_filename
from models.db import query_db, execute_db
from routes.auth import login_required
from services.ai_service import AIService
from services.audit_service import AuditService

reports_bp = Blueprint('reports', __name__)

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']

@reports_bp.route('/report-issue', methods=['GET', 'POST'])
@login_required
def report_issue():
    """Submit a new campus environmental problem with AI categorization & priority."""
    locations = query_db("SELECT * FROM campus_locations WHERE is_active = 1 ORDER BY campus_name, building_name")

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        priority = request.form.get('priority', 'medium').strip()
        location_id = request.form.get('location_id')
        specific_spot = request.form.get('specific_spot', '').strip()
        is_anonymous = 1 if request.form.get('is_anonymous') else 0

        if not title or not description or not specific_spot or not location_id:
            flash("Please complete all required fields.", "danger")
            return render_template('report_issue.html', locations=locations)

        # Handle Photo Upload
        photo_path = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
                unique_name = f"issue_{uuid.uuid4().hex[:12]}.{ext}"
                upload_dir = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, unique_name))
                photo_path = f"/static/uploads/{unique_name}"

        # AI Categorization & Prioritization
        ai_analysis = AIService.analyze_report(title, description, specific_spot)
        final_category = category if category in ['water', 'electricity', 'waste', 'greenery', 'infrastructure'] else ai_analysis['predicted_category']
        final_priority = priority if priority in ['low', 'medium', 'high', 'critical'] else ai_analysis['suggested_priority']

        # Generate unique report number e.g. CP-2026-0042
        now = datetime.datetime.now()
        count_today = query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'] + 1
        report_number = f"CP-{now.year}-{count_today:04d}"

        # Insert Report
        cur = execute_db(
            """INSERT INTO reports (
                report_number, user_id, title, description, category, priority, status,
                location_id, specific_spot, is_anonymous, photo_path, ai_confidence,
                ai_reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?, ?, ?, ?, ?)""",
            (
                report_number,
                None if is_anonymous else g.user['id'],
                title,
                description,
                final_category,
                final_priority,
                location_id,
                specific_spot,
                is_anonymous,
                photo_path,
                ai_analysis['confidence'],
                ai_analysis['reasoning']
            )
        )
        report_id = cur.lastrowid

        # Insert History Log
        execute_db(
            """INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment)
               VALUES (?, ?, NULL, 'submitted', ?)""",
            (report_id, g.user['id'], "Issue reported via CampusPulse. Awaiting facilities verification.")
        )

        # Audit & Award Points
        AuditService.log(g.user['id'], 'SUBMIT_REPORT', 'REPORT', report_id, f"Created report {report_number}")
        AuditService.award_points(g.user['id'], 50, f"Submitted environmental report {report_number}")

        flash(f"Report {report_number} submitted successfully! You earned +50 Green Points. 🌿", "success")
        return redirect(url_for('reports.report_detail', report_id=report_id))

    return render_template('report_issue.html', locations=locations)

@reports_bp.route('/my-reports')
@login_required
def my_reports():
    """List reports filed by the logged-in user."""
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')

    query = """
        SELECT r.*, l.building_name, l.floor, l.zone_or_wing, d.name as dept_name
        FROM reports r
        LEFT JOIN campus_locations l ON r.location_id = l.id
        LEFT JOIN departments d ON r.assigned_department_id = d.id
        WHERE r.user_id = ?
    """
    params = [g.user['id']]

    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)
    if category_filter:
        query += " AND r.category = ?"
        params.append(category_filter)

    query += " ORDER BY r.created_at DESC"
    reports = query_db(query, params)

    return render_template('my_reports.html', reports=reports, current_status=status_filter, current_cat=category_filter)

@reports_bp.route('/reports/<int:report_id>')
def report_detail(report_id):
    """View detailed report status, photo evidence, history timeline, and comments."""
    report = query_db("""
        SELECT r.*, l.campus_name, l.building_name, l.floor, l.zone_or_wing, l.latitude, l.longitude,
               u.full_name as reporter_name, u.email as reporter_email,
               staff.full_name as assigned_staff_name, d.name as assigned_dept_name
        FROM reports r
        LEFT JOIN campus_locations l ON r.location_id = l.id
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN users staff ON r.assigned_to_user_id = staff.id
        LEFT JOIN departments d ON r.assigned_department_id = d.id
        WHERE r.id = ?
    """, (report_id,), one=True)

    if not report:
        flash("Report not found.", "warning")
        return redirect(url_for('main.dashboard'))

    # History timeline
    history = query_db("""
        SELECT h.*, u.full_name as changed_by_name, u.role as changed_by_role
        FROM report_history h
        LEFT JOIN users u ON h.changed_by_user_id = u.id
        WHERE h.report_id = ?
        ORDER BY h.created_at ASC
    """, (report_id,))

    # Comments
    comments = query_db("""
        SELECT c.*, u.full_name, u.role, u.avatar_color
        FROM report_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.report_id = ?
        ORDER BY c.created_at ASC
    """, (report_id,))

    # Maintenance staff list (if current user is staff/admin)
    staff_members = []
    departments = []
    if g.user and g.user['role'] in ('staff', 'admin'):
        staff_members = query_db("SELECT id, full_name, role FROM users WHERE role IN ('staff', 'admin')")
        departments = query_db("SELECT id, name FROM departments")

    return render_template(
        'report_detail.html',
        report=report,
        history=history,
        comments=comments,
        staff_members=staff_members,
        departments=departments
    )

@reports_bp.route('/reports/<int:report_id>/comment', methods=['POST'])
@login_required
def add_comment(report_id):
    """Add a public or internal comment to a report."""
    comment_text = request.form.get('comment', '').strip()
    is_internal = 1 if (request.form.get('is_internal') and g.user['role'] in ('staff', 'admin')) else 0

    if comment_text:
        execute_db(
            "INSERT INTO report_comments (report_id, user_id, comment, is_internal_staff_only) VALUES (?, ?, ?, ?)",
            (report_id, g.user['id'], comment_text, is_internal)
        )
        flash("Comment posted.", "success")

    return redirect(url_for('reports.report_detail', report_id=report_id))

@reports_bp.route('/api/ai/analyze-issue', methods=['POST'])
def api_analyze_issue():
    """AJAX real-time AI classification endpoint."""
    data = request.get_json() or {}
    title = data.get('title', '')
    desc = data.get('description', '')
    spot = data.get('specific_spot', '')

    result = AIService.analyze_report(title, desc, spot)
    return jsonify(result)
