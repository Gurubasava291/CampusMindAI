import pytest
import os
import tempfile
import base64
from io import BytesIO
from app import create_app
from config import TestingConfig
from models.db import init_db, get_db, query_db, execute_db
from services.seed_service import rotate_legacy_seed_passwords, seed_database
from services.ai_service import AIService
from werkzeug.security import check_password_hash, generate_password_hash

@pytest.fixture
def app():
    # Use temporary file for test database
    db_fd, db_path = tempfile.mkstemp()
    TestingConfig.DATABASE_PATH = db_path

    app = create_app(TestingConfig)

    with app.app_context():
        init_db()
        seed_database(force=True)

    yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def test_database_seeded(app):
    with app.app_context():
        user_count = query_db("SELECT COUNT(*) as c FROM users", one=True)['c']
        assert user_count >= 5

def test_dashboard_access(client):
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b"Dayananda Sagar University" in response.data
    assert b"Sustainability Dashboard" in response.data

def test_cat_status(client):
    response = client.get('/api/cat')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == 'Backend is running'

def test_guest_home_offers_sign_in_and_registration(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"CampusMindAi" in response.data
    assert b'href="/login"' in response.data
    assert b'href="/register"' in response.data

def test_virtual_tour_routes_are_removed(client):
    assert client.get('/virtual-tour').status_code == 404
    assert client.get('/api/tour-stops').status_code == 404
    assert client.get('/admin/tour-stops').status_code == 404

def test_ai_categorization_engine():
    # Water leak test
    res_water = AIService.analyze_report("Pipe burst in rest facility", "Water gushing from 3rd floor washroom angle valve")
    assert res_water['predicted_category'] == 'water'
    assert res_water['suggested_priority'] in ('high', 'critical')
    assert res_water['confidence'] >= 0.8

    # Electricity test
    res_elec = AIService.analyze_report("Exposed sparks in AC switchboard", "Sparking outlet with smoke in Lab 204")
    assert res_elec['predicted_category'] == 'electricity'
    assert res_elec['suggested_priority'] == 'critical'

    # Waste test
    res_waste = AIService.analyze_report("Overflowing food waste bin", "Canteen bins full of plastic wrappers and garbage")
    assert res_waste['predicted_category'] == 'waste'

def test_ecobot_assistant(client):
    response = client.post('/api/assistant/chat', json={'message': 'Summarize campus environmental status'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'reply' in data
    assert 'DSU CampusPulse Live Sustainability Summary' in data['reply']


def test_ecobot_separates_report_help_from_problem_diagnosis(client):
    how_to = client.post('/api/assistant/chat', json={'message': 'How can I report an issue?'})
    assert how_to.status_code == 200
    how_to_data = how_to.get_json()
    assert 'Report Issue' in how_to_data['reply']
    assert 'diagnosis' not in how_to_data
    assert how_to_data['actions'][0]['url'] == '/report-issue'

    incident = client.post('/api/assistant/chat', json={'message': 'There is a water leak in the washroom'})
    assert incident.status_code == 200
    incident_data = incident.get_json()
    assert incident_data['diagnosis']['category'] == 'water'

def test_assistant_image_uses_uploaded_image_with_groq(client, app, monkeypatch):
    image_bytes = b'\x89PNG\r\n\x1a\nimage-data'
    captured_request = {}
    app.config['GROQ_API_KEY'] = 'test-key'
    app.config['GROQ_VISION_MODEL'] = 'test-vision-model'

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {'choices': [{'message': {'content': 'A visible pipe is leaking.'}}]}

    def fake_post(url, **kwargs):
        captured_request['url'] = url
        captured_request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr('services.ai_service.requests.post', fake_post)
    response = client.post(
        '/api/assistant/analyze-image',
        data={
            'prompt': 'What is visible?',
            'image': (BytesIO(image_bytes), 'leak.png', 'image/png')
        },
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    assert response.get_json()['reply'] == 'A visible pipe is leaking.'
    request_payload = captured_request['json']
    assert captured_request['url'] == 'https://api.groq.com/openai/v1/chat/completions'
    assert request_payload['model'] == 'test-vision-model'
    assert request_payload['messages'][1]['content'][1]['image_url']['url'].endswith(
        base64.b64encode(image_bytes).decode('ascii')
    )
    assert 'Do not use campus records' in request_payload['messages'][0]['content']

def test_assistant_image_requires_groq_key(client, app):
    app.config['GROQ_API_KEY'] = ''
    response = client.post(
        '/api/assistant/analyze-image',
        data={'image': (BytesIO(b'\x89PNG\r\n\x1a\nimage-data'), 'photo.png', 'image/png')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 503
    assert 'not configured' in response.get_json()['error']

def test_legacy_seed_passwords_are_rotated(app):
    with app.app_context():
        admin = query_db("SELECT id FROM users WHERE email = ?", ('admin@dsu.edu.in',), one=True)
        execute_db(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash('admin123'), admin['id'])
        )
        rotate_legacy_seed_passwords()
        password_hash = query_db(
            "SELECT password_hash FROM users WHERE id = ?",
            (admin['id'],),
            one=True
        )['password_hash']

    assert check_password_hash(password_hash, TestingConfig.SEEDED_ADMIN_PASSWORD)
    assert not check_password_hash(password_hash, 'admin123')

def test_login_and_role_access(client):
    student_credentials = {
        'login_input': 'student@dsu.edu.in',
        'password': TestingConfig.SEEDED_STUDENT_PASSWORD
    }
    admin_credentials = {
        'login_input': 'admin@dsu.edu.in',
        'password': TestingConfig.SEEDED_ADMIN_PASSWORD
    }

    assert client.get('/demo-login/student').status_code == 404
    assert client.get('/demo-login/admin').status_code == 404

    student_on_admin_portal = client.post('/admin/login', data=student_credentials)
    assert student_on_admin_portal.status_code == 200
    with client.session_transaction() as session:
        assert 'user_id' not in session

    student_password_on_another_account = client.post(
        '/login',
        data={'login_input': 'arjun.kumar@dsu.edu.in', 'password': TestingConfig.SEEDED_STUDENT_PASSWORD}
    )
    assert b"Invalid email/username or password" in student_password_on_another_account.data

    admin_on_student_portal = client.post('/login', data=admin_credentials, follow_redirects=True)
    assert b"separate Admin portal" in admin_on_student_portal.data
    with client.session_transaction() as session:
        assert 'user_id' not in session

    res = client.post('/login', data=student_credentials, follow_redirects=True)
    assert res.status_code == 200
    assert b"Pooja Rao" in res.data

    # Student cannot access /admin
    res_admin = client.get('/admin', follow_redirects=True)
    assert b"Access denied" in res_admin.data

    # Logout
    client.get('/logout', follow_redirects=True)

    # Administrator must use the separate admin portal
    # Login as admin via dedicated portal
    client.post('/admin/login', data=admin_credentials, follow_redirects=True)
    res_admin_ok = client.get('/admin')
    assert res_admin_ok.status_code == 200
    assert b"Administration Control Panel" in res_admin_ok.data

    # Admin can access the All Problems console
    res_problems = client.get('/admin/reports')
    assert res_problems.status_code == 200
    assert b"All Problems Console" in res_problems.data


def test_admin_login_accepts_requested_password(client, app):
    with app.app_context():
        admin = query_db("SELECT id FROM users WHERE email = ?", ('admin@dsu.edu.in',), one=True)
        execute_db(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash('admin@123'), admin['id'])
        )

    response = client.post(
        '/admin/login',
        data={'login_input': 'admin@dsu.edu.in', 'password': 'admin@123'},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Administration Control Panel" in response.data


def test_email_code_password_recovery(client, app, monkeypatch):
    sent_emails = []

    def fake_send_email(recipient, code):
        sent_emails.append((recipient, code))
        return True

    monkeypatch.setattr('routes.auth.send_recovery_email', fake_send_email)
    with app.app_context():
        student = query_db("SELECT id FROM users WHERE email = ?", ('student@dsu.edu.in',), one=True)
        execute_db("UPDATE users SET email = ? WHERE id = ?", ('student@gmail.com', student['id']))

    response = client.post(
        '/forgot-password',
        data={'action': 'send_code', 'identifier': 'student@gmail.com'},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert sent_emails[0][0] == 'student@gmail.com'
    code = sent_emails[0][1]

    response = client.post(
        '/forgot-password',
        data={
            'action': 'reset_password',
            'identifier': 'student@gmail.com',
            'code': code,
            'password': 'new-password-123',
            'confirm_password': 'new-password-123'
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Your password has been reset" in response.data

    restarted_app = create_app(TestingConfig)
    with restarted_app.app_context():
        student = query_db("SELECT password_hash FROM users WHERE email = ?", ('student@gmail.com',), one=True)
        assert check_password_hash(student['password_hash'], 'new-password-123')


def test_registration_rejects_non_numeric_phone(client):
    response = client.post('/register', data={
        'full_name': 'Test Student',
        'username': 'test_student',
        'email': 'test.student@dsu.edu.in',
        'phone_number': '+91abc9876543210',
        'password': 'test-password-123'
    })
    assert response.status_code == 200
    assert b"Enter a valid phone number" in response.data
