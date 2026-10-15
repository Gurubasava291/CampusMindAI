import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models.db import query_db, execute_db
from routes.auth import login_required, role_required
from services.audit_service import AuditService

monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/monitoring/energy-water', methods=['GET', 'POST'])
def energy_water():
    """
    Energy & Water Monitoring dashboard.
    Visualizes daily electrical consumption, solar generation, peak load,
    water consumption, STP recycling, and rainwater harvesting.
    Supports manual meter reading entry for authorized staff.
    """
    if request.method == 'POST':
        if not g.user or g.user['role'] not in ('staff', 'admin'):
            flash("Staff privileges required to log meter readings.", "danger")
            return redirect(url_for('monitoring.energy_water'))

        log_type = request.form.get('log_type')
        reading_date = request.form.get('reading_date') or datetime.date.today().isoformat()
        campus_name = request.form.get('campus_name', 'Main Innovation Campus (Harohalli)')

        if log_type == 'energy':
            bld = request.form.get('building_name', 'Academic Block A (Engineering)')
            meter = request.form.get('meter_name', 'MTR-MAIN')
            kwh = float(request.form.get('kwh_consumed', 0))
            solar = float(request.form.get('solar_generated_kwh', 0))
            peak = float(request.form.get('peak_load_kw', 0))
            notes = request.form.get('notes', '')

            execute_db(
                """INSERT INTO energy_readings (campus_name, building_name, meter_name, reading_date, kwh_consumed, peak_load_kw, solar_generated_kwh, notes, logged_by_user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (campus_name, bld, meter, reading_date, kwh, peak, solar, notes, g.user['id'])
            )
            AuditService.log(g.user['id'], 'LOG_ENERGY', 'ENERGY', None, f"Logged {kwh} kWh for {bld}")
            flash("Energy meter reading logged successfully.", "success")

        elif log_type == 'water':
            loc = request.form.get('location_name', 'Central Hydro Station')
            liters = float(request.form.get('liters_consumed', 0))
            recycled = float(request.form.get('recycled_water_liters', 0))
            rainwater = float(request.form.get('rainwater_harvested_liters', 0))
            leak = 1 if request.form.get('leak_detected') else 0
            notes = request.form.get('notes', '')

            execute_db(
                """INSERT INTO water_readings (campus_name, location_name, reading_date, liters_consumed, recycled_water_liters, rainwater_harvested_liters, leak_detected, notes, logged_by_user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (campus_name, loc, reading_date, liters, recycled, rainwater, leak, notes, g.user['id'])
            )
            AuditService.log(g.user['id'], 'LOG_WATER', 'WATER', None, f"Logged {liters} L for {loc}")
            flash("Water reading logged successfully.", "success")

        return redirect(url_for('monitoring.energy_water'))

    # Query recent readings
    energy_logs = query_db("SELECT * FROM energy_readings ORDER BY reading_date DESC LIMIT 14")
    water_logs = query_db("SELECT * FROM water_readings ORDER BY reading_date DESC LIMIT 14")

    # Aggregates
    totals = {
        'total_solar': query_db("SELECT COALESCE(SUM(solar_generated_kwh), 0) as s FROM energy_readings", one=True)['s'],
        'total_grid_kwh': query_db("SELECT COALESCE(SUM(kwh_consumed), 0) as s FROM energy_readings", one=True)['s'],
        'total_water': query_db("SELECT COALESCE(SUM(liters_consumed), 0) as s FROM water_readings", one=True)['s'],
        'total_recycled': query_db("SELECT COALESCE(SUM(recycled_water_liters), 0) as s FROM water_readings", one=True)['s'],
        'total_rainwater': query_db("SELECT COALESCE(SUM(rainwater_harvested_liters), 0) as s FROM water_readings", one=True)['s']
    }

    return render_template('monitoring.html', energy_logs=energy_logs, water_logs=water_logs, totals=totals)

@monitoring_bp.route('/monitoring/waste', methods=['GET', 'POST'])
def waste_management():
    """Waste management & recycling collection records."""
    if request.method == 'POST':
        if not g.user or g.user['role'] not in ('staff', 'admin'):
            flash("Staff privileges required to log waste collection.", "danger")
            return redirect(url_for('monitoring.waste_management'))

        record_date = request.form.get('record_date') or datetime.date.today().isoformat()
        campus_name = request.form.get('campus_name', 'Main Innovation Campus (Harohalli)')
        organic = float(request.form.get('organic_kg', 0))
        recyclable = float(request.form.get('recyclable_kg', 0))
        ewaste = float(request.form.get('ewaste_kg', 0))
        hazardous = float(request.form.get('hazardous_kg', 0))
        composted = float(request.form.get('composted_kg', 0))

        total_waste = organic + recyclable + ewaste + hazardous
        diverted_pct = round(((composted + recyclable) / total_waste * 100), 1) if total_waste > 0 else 0.0

        execute_db(
            """INSERT INTO waste_records (campus_name, record_date, organic_kg, recyclable_kg, ewaste_kg, hazardous_kg, composted_kg, landfill_diverted_pct, logged_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (campus_name, record_date, organic, recyclable, ewaste, hazardous, composted, diverted_pct, g.user['id'])
        )
        AuditService.log(g.user['id'], 'LOG_WASTE', 'WASTE', None, f"Logged {total_waste} kg waste collection")
        flash("Waste collection record logged successfully.", "success")
        return redirect(url_for('monitoring.waste_management'))

    waste_logs = query_db("SELECT * FROM waste_records ORDER BY record_date DESC LIMIT 12")

    waste_totals = {
        'organic': query_db("SELECT COALESCE(SUM(organic_kg), 0) as s FROM waste_records", one=True)['s'],
        'recyclable': query_db("SELECT COALESCE(SUM(recyclable_kg), 0) as s FROM waste_records", one=True)['s'],
        'ewaste': query_db("SELECT COALESCE(SUM(ewaste_kg), 0) as s FROM waste_records", one=True)['s'],
        'composted': query_db("SELECT COALESCE(SUM(composted_kg), 0) as s FROM waste_records", one=True)['s'],
        'avg_diverted': query_db("SELECT COALESCE(AVG(landfill_diverted_pct), 85.0) as a FROM waste_records", one=True)['a']
    }

    return render_template('waste_management.html', waste_logs=waste_logs, waste_totals=waste_totals)

@monitoring_bp.route('/monitoring/impact')
def impact_analytics():
    """Campus Environmental Impact & Avoided Emissions Analytics."""
    # Calculated statistics
    total_solar_kwh = query_db("SELECT COALESCE(SUM(solar_generated_kwh), 0) as s FROM energy_readings", one=True)['s']
    total_water_recycled = query_db("SELECT COALESCE(SUM(recycled_water_liters), 0) as s FROM water_readings", one=True)['s']
    total_rainwater = query_db("SELECT COALESCE(SUM(rainwater_harvested_liters), 0) as s FROM water_readings", one=True)['s']
    total_composted = query_db("SELECT COALESCE(SUM(composted_kg), 0) as s FROM waste_records", one=True)['s']
    resolved_reports = query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c']

    # Factors
    co2_solar = round(total_solar_kwh * 0.82, 1) # kg CO2e
    co2_waste = round(total_composted * 0.45, 1) # kg CO2e
    co2_leaks_prevented = round(resolved_reports * 24.5, 1)
    total_co2_avoided = round(co2_solar + co2_waste + co2_leaks_prevented, 1)

    trees_equivalent = round(total_co2_avoided / 21.77, 1) # 1 tree absorbs ~21.77 kg CO2/year

    goals = query_db("SELECT * FROM sustainability_goals ORDER BY id ASC")

    return render_template(
        'impact_analytics.html',
        total_co2_avoided=total_co2_avoided,
        co2_solar=co2_solar,
        co2_waste=co2_waste,
        co2_leaks_prevented=co2_leaks_prevented,
        trees_equivalent=trees_equivalent,
        total_water_conserved=round(total_water_recycled + total_rainwater, 0),
        goals=goals
    )
