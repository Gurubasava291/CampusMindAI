import datetime
from flask import Blueprint, render_template, request, jsonify, g, session
from services.ai_service import AIService
from services.audit_service import AuditService
from models.db import query_db, execute_db

assistant_bp = Blueprint('assistant', __name__)

@assistant_bp.route('/assistant')
def assistant():
    """AI Sustainability Assistant chat interface."""
    user_context = {
        'name': g.user['full_name'] if g.user else 'Campus Guest',
        'role': g.user['role'] if g.user else 'guest',
        'points': g.user['green_points'] if g.user else 0,
        'user_id': g.user['id'] if g.user else None
    }
    rows = query_db("SELECT id, campus_name, building_name, floor, zone_or_wing FROM campus_locations WHERE is_active = 1 ORDER BY campus_name, building_name")
    locations = [dict(row) for row in rows]
    return render_template('assistant.html', user_context=user_context, locations=locations)

@assistant_bp.route('/api/assistant/chat', methods=['POST'])
def chat():
    """AJAX endpoint for AI assistant responses."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    user_context = {
        'user_id': g.user['id'] if g.user else None,
        'name': g.user['full_name'] if g.user else 'Guest',
        'role': g.user['role'] if g.user else 'guest'
    }

    response = AIService.ask_assistant(message, user_context)
    return jsonify(response)

@assistant_bp.route('/api/assistant/analyze-image', methods=['POST'])
def analyze_image():
    """Analyze one uploaded image directly with the configured Groq vision model."""
    image = request.files.get('image')
    if not image or not image.filename:
        return jsonify({'error': 'Choose an image to analyze.'}), 400

    mime_type = image.mimetype
    signatures = {
        'image/png': b'\x89PNG\r\n\x1a\n',
        'image/jpeg': b'\xff\xd8\xff',
        'image/webp': b'RIFF'
    }
    expected_signature = signatures.get(mime_type)
    image_bytes = image.read()
    if not expected_signature or not image_bytes.startswith(expected_signature):
        return jsonify({'error': 'Upload a valid PNG, JPEG, or WebP image.'}), 400
    if mime_type == 'image/webp' and image_bytes[8:12] != b'WEBP':
        return jsonify({'error': 'Upload a valid PNG, JPEG, or WebP image.'}), 400

    try:
        reply = AIService.analyze_image(
            image_bytes,
            mime_type,
            request.form.get('prompt', '').strip()[:1000]
        )
    except ValueError:
        return jsonify({'error': 'Image analysis is not configured. Add a Groq API key to the local environment.'}), 503
    except RuntimeError:
        return jsonify({'error': 'Groq could not analyze the image. Check the API key, model, and connection, then retry.'}), 502

    return jsonify({'reply': reply})

@assistant_bp.route('/api/assistant/quick-report', methods=['POST'])
def quick_report():
    """
    1-Click Ticket Submission directly from the DSU EcoBot conversation.
    Instantly files the report, notifies facilities, and awards +50 Green Points.
    """
    data = request.get_json() or {}
    title = data.get('title', 'Environmental Issue Reported via EcoBot').strip()
    description = data.get('description', '').strip()
    category = data.get('category', 'infrastructure')
    priority = data.get('priority', 'medium')
    location_id = data.get('location_id') or 1
    specific_spot = data.get('specific_spot', 'Reported via AI EcoBot').strip()
    is_anonymous = 1 if data.get('is_anonymous') else 0

    if not description:
        return jsonify({'status': 'error', 'message': 'Problem description is required.'}), 400

    user_id = g.user['id'] if (g.user and not is_anonymous) else None

    # Generate unique ticket number
    now = datetime.datetime.now()
    count_today = query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'] + 1
    report_number = f"CP-{now.year}-{count_today:04d}"

    # Insert report
    cur = execute_db(
        """INSERT INTO reports (
            report_number, user_id, title, description, category, priority, status,
            location_id, specific_spot, is_anonymous, ai_confidence, ai_reasoning
        ) VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?, ?, 0.95, ?)""",
        (
            report_number,
            user_id,
            title,
            description,
            category,
            priority,
            location_id,
            specific_spot,
            is_anonymous,
            "Diagnosed and filed directly via DSU EcoBot Interactive Assistant."
        )
    )
    report_id = cur.lastrowid

    # Add audit history
    execute_db(
        """INSERT INTO report_history (report_id, changed_by_user_id, old_status, new_status, comment)
           VALUES (?, ?, NULL, 'submitted', 'Report filed interactively via DSU EcoBot AI Assistant.')""",
        (report_id, g.user['id'] if g.user else None)
    )

    # Award Green Points if authenticated
    points_awarded = 0
    if g.user:
        AuditService.award_points(g.user['id'], 50, f"Reported issue {report_number} via DSU EcoBot")
        AuditService.log(g.user['id'], 'SUBMIT_REPORT_AI', 'REPORT', report_id, f"Created {report_number} via EcoBot")
        points_awarded = 50

    return jsonify({
        'status': 'success',
        'report_id': report_id,
        'report_number': report_number,
        'points_awarded': points_awarded,
        'message': f"Official Ticket #{report_number} successfully registered with DSU Facilities!"
    })
