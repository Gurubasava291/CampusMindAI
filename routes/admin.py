from flask import Blueprint, render_template, request, redirect, url_for, flash, g
import re
from models.db import query_db, execute_db
from routes.auth import login_required, role_required
from services.audit_service import AuditService
from services.seed_service import seed_database

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@role_required('admin')
def dashboard():
    """Admin Control Panel Home."""
    stats = {
        'users': query_db("SELECT COUNT(*) as c FROM users", one=True)['c'],
        'reports': query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'],
        'locations': query_db("SELECT COUNT(*) as c FROM campus_locations", one=True)['c'],
        'logs': query_db("SELECT COUNT(*) as c FROM audit_logs", one=True)['c']
    }
    recent_logs = query_db("""
        SELECT a.*, u.full_name as user_name
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC LIMIT 10
    """)
    return render_template('admin/dashboard.html', stats=stats, recent_logs=recent_logs)

@admin_bp.route('/admin/reports')
@login_required
@role_required('admin')
def all_reports():
    """All Problems Console: every environmental issue filed across the university."""
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    category_filter = request.args.get('category')

    query = """
        SELECT r.*, l.building_name, l.floor, l.zone_or_wing,
               u.full_name as reporter_name, d.name as dept_name,
               staff.full_name as assigned_staff_name
        FROM reports r
        LEFT JOIN campus_locations l ON r.location_id = l.id
        LEFT JOIN users u ON r.user_id = u.id
        LEFT JOIN departments d ON r.assigned_department_id = d.id
        LEFT JOIN users staff ON r.assigned_to_user_id = staff.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)
    if priority_filter:
        query += " AND r.priority = ?"
        params.append(priority_filter)
    if category_filter:
        query += " AND r.category = ?"
        params.append(category_filter)

    query += """
        ORDER BY
            CASE r.priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END ASC,
            r.created_at DESC
    """
    all_reports = query_db(query, params)

    counts = {
        'total': query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'],
        'pending': query_db("SELECT COUNT(*) as c FROM reports WHERE status IN ('submitted', 'verified', 'assigned', 'in_progress')", one=True)['c'],
        'resolved': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c'],
        'critical': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'critical'", one=True)['c'],
        'water': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'water'", one=True)['c'],
        'electricity': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'electricity'", one=True)['c'],
        'waste': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'waste'", one=True)['c'],
        'greenery': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'greenery'", one=True)['c'],
        'infrastructure': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'infrastructure'", one=True)['c'],
    }

    return render_template(
        'admin/reports.html',
        reports=all_reports,
        counts=counts,
        current_status=status_filter,
        current_priority=priority_filter,
        current_category=category_filter
    )

@admin_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def users():
    """Manage users, roles, and status."""
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        if action == 'update_role':
            new_role = request.form.get('role')
            if new_role in ('student', 'staff', 'admin'):
                execute_db("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
                AuditService.log(g.user['id'], 'UPDATE_USER_ROLE', 'USER', user_id, f"Role changed to {new_role}")
                flash("User role updated.", "success")
        elif action == 'update_phone':
            phone_number = request.form.get('phone_number', '').strip()
            if not phone_number or re.fullmatch(r"\+?[0-9]{8,15}", phone_number):
                execute_db("UPDATE users SET phone_number = ? WHERE id = ?", (phone_number or None, user_id))
                flash("Recovery phone updated.", "success")
            else:
                flash("Enter a valid phone number with country code.", "danger")
        elif action == 'toggle_status':
            curr = query_db("SELECT is_active FROM users WHERE id = ?", (user_id,), one=True)
            if curr:
                new_state = 0 if curr['is_active'] else 1
                execute_db("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
                flash("User status toggled.", "info")

        return redirect(url_for('admin.users'))

    all_users = query_db("""
        SELECT u.*, d.name as dept_name
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        ORDER BY u.created_at DESC
    """)
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/admin/locations', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def locations():
    """Manage campus building locations."""
    if request.method == 'POST':
        campus = request.form.get('campus_name')
        building = request.form.get('building_name')
        floor = request.form.get('floor')
        wing = request.form.get('zone_or_wing')
        lat = float(request.form.get('latitude', 12.6582))
        lng = float(request.form.get('longitude', 77.4475))

        execute_db(
            """INSERT INTO campus_locations (campus_name, building_name, floor, zone_or_wing, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (campus, building, floor, wing, lat, lng)
        )
        flash("Location added.", "success")
        return redirect(url_for('admin.locations'))

    locs = query_db("SELECT * FROM campus_locations ORDER BY campus_name, building_name, floor")
    return render_template('admin/locations.html', locations=locs)

@admin_bp.route('/admin/audit-logs')
@login_required
@role_required('admin')
def audit_logs():
    """System-wide audit trail."""
    logs = query_db("""
        SELECT a.*, u.full_name as user_name, u.role as user_role
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC LIMIT 100
    """)
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/admin/seed-demo', methods=['POST'])
@login_required
@role_required('admin')
def seed_demo():
    """Reset and re-seed demo data."""
    res = seed_database(force=True)
    flash(res['message'], "success")
    return redirect(url_for('admin.dashboard'))
