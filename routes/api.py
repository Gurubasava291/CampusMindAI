from flask import Blueprint, jsonify, request
from models.db import query_db

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/map-issues')
def map_issues():
    """
    Returns all campus environmental issues formatted for Leaflet & Mapbox.
    Includes location coordinates, category, priority, status, and thumbnails.
    """
    category = request.args.get('category')
    status = request.args.get('status')
    priority = request.args.get('priority')

    query = """
        SELECT r.id, r.report_number, r.title, r.description, r.category,
               r.priority, r.status, r.photo_path, r.resolution_photo_path,
               r.specific_spot, r.created_at,
               l.building_name, l.floor, l.zone_or_wing, l.latitude, l.longitude
        FROM reports r
        JOIN campus_locations l ON r.location_id = l.id
        WHERE 1=1
    """
    params = []

    if category:
        query += " AND r.category = ?"
        params.append(category)
    if status:
        query += " AND r.status = ?"
        params.append(status)
    if priority:
        query += " AND r.priority = ?"
        params.append(priority)

    rows = query_db(query, params)
    issues = [dict(r) for r in rows]

    return jsonify({
        'status': 'success',
        'count': len(issues),
        'issues': issues
    })

@api_bp.route('/stats/summary')
def stats_summary():
    """Returns real-time dashboard KPIs as JSON."""
    total = query_db("SELECT COUNT(*) as c FROM reports", one=True)['c']
    pending = query_db("SELECT COUNT(*) as c FROM reports WHERE status IN ('submitted', 'verified', 'assigned', 'in_progress')", one=True)['c']
    resolved = query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c']
    water_leaks = query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'water' AND status != 'resolved'", one=True)['c']
    elec_waste = query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'electricity' AND status != 'resolved'", one=True)['c']

    return jsonify({
        'total_reports': total,
        'pending_reports': pending,
        'resolved_reports': resolved,
        'resolution_rate': round((resolved / total * 100), 1) if total > 0 else 0,
        'active_water_leaks': water_leaks,
        'active_elec_waste': elec_waste
    })
