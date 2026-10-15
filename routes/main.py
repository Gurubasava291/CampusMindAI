from flask import Blueprint, render_template, request, redirect, url_for, g, jsonify, current_app
from models.db import query_db, execute_db
from routes.auth import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Public welcome screen and first entry point for CampusMindAi."""
    if g.user:
        return redirect(url_for('main.dashboard'))
    return render_template('welcome.html')

@main_bp.route('/dashboard')
def dashboard():
    """
    Primary CampusPulse DSU Sustainability Dashboard.
    Presents university-wide environmental KPIs, active vs resolved issues,
    energy/water metrics, and recent campus reports.
    """
    # Summary KPIs
    total_reports = query_db("SELECT COUNT(*) as c FROM reports", one=True)['c']
    pending_reports = query_db("SELECT COUNT(*) as c FROM reports WHERE status IN ('submitted', 'verified', 'assigned', 'in_progress')", one=True)['c']
    resolved_reports = query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c']
    
    # Active students participating
    active_students = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c']
    total_green_points = query_db("SELECT COALESCE(SUM(green_points), 0) as s FROM users", one=True)['s']

    # Resolution rate
    resolution_rate = round((resolved_reports / total_reports * 100), 1) if total_reports > 0 else 0.0

    # Resource Metrics from logs (Energy & Water)
    total_solar_kwh = query_db("SELECT COALESCE(SUM(solar_generated_kwh), 0) as s FROM energy_readings", one=True)['s']
    total_water_recycled = query_db("SELECT COALESCE(SUM(recycled_water_liters), 0) as s FROM water_readings", one=True)['s']
    total_rainwater = query_db("SELECT COALESCE(SUM(rainwater_harvested_liters), 0) as s FROM water_readings", one=True)['s']
    avg_waste_diverted = query_db("SELECT COALESCE(AVG(landfill_diverted_pct), 85.0) as a FROM waste_records", one=True)['a']

    # Estimated Carbon Emissions Avoided (kg CO2e)
    # Factor: ~0.82 kg CO2e per kWh clean solar generated + ~0.5 kg CO2e per kg composted
    carbon_avoided_kg = round((total_solar_kwh * 0.82) + (resolved_reports * 24.5), 1)

    # Category Breakdown for Chart.js
    category_counts = {
        'water': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'water'", one=True)['c'],
        'electricity': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'electricity'", one=True)['c'],
        'waste': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'waste'", one=True)['c'],
        'greenery': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'greenery'", one=True)['c'],
        'infrastructure': query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'infrastructure'", one=True)['c']
    }

    # Priority breakdown
    priority_counts = {
        'critical': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'critical' AND status != 'resolved'", one=True)['c'],
        'high': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'high' AND status != 'resolved'", one=True)['c'],
        'medium': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'medium' AND status != 'resolved'", one=True)['c'],
        'low': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'low' AND status != 'resolved'", one=True)['c']
    }

    # Recent Reports
    recent_reports = query_db("""
        SELECT r.*, l.building_name, l.floor, u.full_name as reporter_name
        FROM reports r
        LEFT JOIN campus_locations l ON r.location_id = l.id
        LEFT JOIN users u ON r.user_id = u.id
        ORDER BY r.created_at DESC LIMIT 6
    """)

    # Active Goals
    active_goals = query_db("SELECT * FROM sustainability_goals WHERE status = 'in_progress' LIMIT 3")

    return render_template(
        'dashboard.html',
        total_reports=total_reports,
        pending_reports=pending_reports,
        resolved_reports=resolved_reports,
        resolution_rate=resolution_rate,
        active_students=active_students,
        total_green_points=total_green_points,
        total_solar_kwh=round(total_solar_kwh, 1),
        total_water_recycled=round(total_water_recycled, 0),
        total_rainwater=round(total_rainwater, 0),
        avg_waste_diverted=round(avg_waste_diverted, 1),
        carbon_avoided_kg=carbon_avoided_kg,
        category_counts=category_counts,
        priority_counts=priority_counts,
        recent_reports=recent_reports,
        active_goals=active_goals
    )

@main_bp.route('/sustainability-map')
def sustainability_map():
    """
    Interactive Operational Sustainability Map.
    Displays all reported environmental issues mapped with pins, categories,
    priority levels, status filters, and recurring hotspot indicators.
    """
    locations = query_db("SELECT * FROM campus_locations WHERE is_active = 1")
    campus_cfg = {
        'default_lat': current_app.config.get('DEFAULT_CAMPUS_LAT', 12.6582),
        'default_lng': current_app.config.get('DEFAULT_CAMPUS_LNG', 77.4475),
        'default_zoom': current_app.config.get('DEFAULT_MAP_ZOOM', 17)
    }
    return render_template(
        'sustainability_map.html',
        locations=locations,
        campus_cfg=campus_cfg
    )

@main_bp.route('/notifications')
@login_required
def notifications():
    """Display user notifications and mark as read."""
    notifs = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (g.user['id'],)
    )
    # Mark as read
    execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user['id'],))
    return render_template('notifications.html', notifications=notifs)
