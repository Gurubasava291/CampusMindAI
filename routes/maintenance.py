import os
import uuid
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from werkzeug.utils import secure_filename
from models.db import query_db, execute_db
from routes.auth import login_required, role_required
from services.audit_service import AuditService

maintenance_bp = Blueprint('maintenance', __name__)

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']

@maintenance_bp.route('/maintenance')
@login_required
@role_required('staff', 'admin')
def maintenance_queue():
    """
    Staff & Admin Maintenance Task Queue.
    Filter by status, department, priority, and assigned staff.
    """
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    dept_filter = request.args.get('department')
    assigned_filter = request.args.get('assigned')

    query = """
        SELECT r.*, l.building_name, l.floor, l.zone_or_wing,
               d.name as dept_name, staff.full_name as assigned_staff_name,
               u.full_name as reporter_name
        FROM reports r
        LEFT JOIN campus_locations l ON r.location_id = l.id
        LEFT JOIN departments d ON r.assigned_department_id = d.id
        LEFT JOIN users staff ON r.assigned_to_user_id = staff.id
        LEFT JOIN users u ON r.user_id = u.id
        WHERE 1=1
    """
    params = []

    # If staff, optionally default to their assigned tasks or all
    if assigned_filter == 'me':
        query += " AND r.assigned_to_user_id = ?"
        params.append(g.user['id'])
    elif assigned_filter:
        query += " AND r.assigned_to_user_id = ?"
        params.append(assigned_filter)

    if status_filter:
        query += " AND r.status = ?"
        params.append(status_filter)
    if priority_filter:
        query += " AND r.priority = ?"
        params.append(priority_filter)
    if dept_filter:
        query += " AND r.assigned_department_id = ?"
        params.append(dept_filter)

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
    tasks = query_db(query, params)

    # Queue Metrics
    counts = {
        'total': query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'],
        'submitted': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'submitted'", one=True)['c'],
        'assigned': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'assigned'", one=True)['c'],
        'in_progress': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'in_progress'", one=True)['c'],
        'resolved': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c'],
        'critical': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'critical' AND status != 'resolved'", one=True)['c']
    }

    departments = query_db("SELECT * FROM departments")
    staff_members = query_db("SELECT id, full_name FROM users WHERE role IN ('staff', 'admin')")

    return render_template(
        'maintenance.html',
        tasks=tasks,
        counts=counts,
        departments=departments,
        staff_members=staff_members,
        current_status=status_filter,
        current_priority=priority_filter,
        current_dept=dept_filter,
        current_assigned=assigned_filter
    )

@maintenance_bp.route('/maintenance/assign/<int:report_id>', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def assign_task(report_id):
    """Assign report to a staff member or department with a due date."""
    staff_id = request.form.get('assigned_to_user_id') or None
    dept_id = request.form.get('assigned_department_id') or None
    due_date = request.form.get('due_date') or None
    priority = request.form.get('priority')

    report = query_db("SELECT * FROM reports WHERE id = ?", (report_id,), one=True)
    if not report:
        flash("Report not found.", "warning")
        return redirect(url_for('maintenance.maintenance_queue'))

    updates = []
    params = []

    if staff_id:
        updates.append("assigned_to_user_id = ?")
        params.append(staff_id)
    if dept_id:
        updates.append("assigned_department_id = ?")
        params.append(dept_id)
    if due_date:
        updates.append("due_date = ?")
        params.append(due_date)
    if priority:
        updates.append("priority = ?")
        params.append(priority)

    # Automatically advance to 'assigned' if currently 'submitted' or 'verified'
    new_status = report['status']
    if report['status'] in ('submitted', 'verified'):
        new_status = 'assigned'
        updates.append("status = 'assigned'")

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(report_id)

    execute_db(f"UPDATE reports SET {', '.join(updates)} WHERE id = ?", params)

    # Log in history
    staff_name = "Department Staff"
    if staff_id:
        u = query_db("SELECT full_name FROM users WHERE id = ?", (staff_id,), one=True)
        if u:
            staff_name = u['full_name']

    execute_db(
        """INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment)
           VALUES (?, ?, ?, ?, ?)""",
        (report_id, g.user['id'], report['status'], new_status, f"Assigned to {staff_name}. Due: {due_date or 'Standard turnaround'}.")
    )

    if staff_id and int(staff_id) != g.user['id']:
        AuditService.notify(
            int(staff_id),
            f"New Task Assigned: {report['report_number']}",
            f"You have been assigned issue: '{report['title']}'. Due date: {due_date or 'ASAP'}.",
            link=url_for('reports.report_detail', report_id=report_id)
        )

    AuditService.log(g.user['id'], 'ASSIGN_REPORT', 'REPORT', report_id, f"Assigned {report['report_number']} to user {staff_id}")
    flash(f"Task {report['report_number']} assigned successfully.", "success")
    return redirect(url_for('reports.report_detail', report_id=report_id))

@maintenance_bp.route('/maintenance/update-status/<int:report_id>', methods=['POST'])
@login_required
@role_required('staff', 'admin')
def update_status(report_id):
    """Update report workflow status (verified, in_progress, resolved, reopened)."""
    new_status = request.form.get('new_status')
    comment = request.form.get('comment', '').strip()

    valid_statuses = ['submitted', 'verified', 'assigned', 'in_progress', 'resolved', 'reopened']
    if new_status not in valid_statuses:
        flash("Invalid status transition.", "danger")
        return redirect(url_for('reports.report_detail', report_id=report_id))

    report = query_db("SELECT * FROM reports WHERE id = ?", (report_id,), one=True)
    if not report:
        flash("Report not found.", "warning")
        return redirect(url_for('maintenance.maintenance_queue'))

    old_status = report['status']

    # Handle resolution photo if resolving
    resolution_photo = report['resolution_photo_path']
    if 'resolution_photo' in request.files:
        file = request.files['resolution_photo']
        if file and file.filename and allowed_file(file.filename):
            ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
            fname = f"res_{uuid.uuid4().hex[:12]}.{ext}"
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], fname))
            resolution_photo = f"/static/uploads/{fname}"

    resolved_at = datetime.datetime.now().isoformat() if new_status == 'resolved' else None

    execute_db(
        """UPDATE reports 
           SET status = ?, resolution_notes = COALESCE(?, resolution_notes),
               resolution_photo_path = COALESCE(?, resolution_photo_path),
               resolved_at = CASE WHEN ? = 'resolved' THEN CURRENT_TIMESTAMP ELSE resolved_at END,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (new_status, comment if new_status == 'resolved' else None, resolution_photo, new_status, report_id)
    )

    # Insert status history
    execute_db(
        """INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment)
           VALUES (?, ?, ?, ?, ?)""",
        (report_id, g.user['id'], old_status, new_status, comment or f"Status changed from {old_status} to {new_status}")
    )

    # Notify student reporter
    if report['user_id']:
        AuditService.notify(
            report['user_id'],
            f"Update on Report {report['report_number']}: {new_status.replace('_', ' ').title()}",
            f"Your report '{report['title']}' is now {new_status.replace('_', ' ')}." + (f" Note: {comment}" if comment else ""),
            link=url_for('reports.report_detail', report_id=report_id)
        )
        if new_status == 'resolved':
            AuditService.award_points(report['user_id'], 25, f"Resolution of your report {report['report_number']}")

    AuditService.log(g.user['id'], 'UPDATE_STATUS', 'REPORT', report_id, f"Changed status to {new_status}")
    flash(f"Status for {report['report_number']} updated to {new_status.upper()}.", "success")
    return redirect(url_for('reports.report_detail', report_id=report_id))
