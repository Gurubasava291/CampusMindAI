from .auth import auth_bp
from .main import main_bp
from .reports import reports_bp
from .maintenance import maintenance_bp
from .assistant import assistant_bp
from .green_hub import green_hub_bp
from .monitoring import monitoring_bp
from .admin import admin_bp
from .api import api_bp

__all__ = [
    'auth_bp',
    'main_bp',
    'reports_bp',
    'maintenance_bp',
    'assistant_bp',
    'green_hub_bp',
    'monitoring_bp',
    'admin_bp',
    'api_bp'
]
