from flask import request, session
from models.db import query_db, execute_db

class AuditService:
    """Service to track audit logs and deliver user notifications."""

    @classmethod
    def log(cls, user_id: int, action: str, entity_type: str, entity_id: int = None, details: str = ""):
        """Create an audit log record."""
        ip = request.remote_addr if request else "127.0.0.1"
        execute_db(
            """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, action, entity_type, entity_id, details, ip)
        )

    @classmethod
    def notify(cls, user_id: int, title: str, message: str, link: str = None):
        """Create an in-app notification for a user."""
        execute_db(
            """INSERT INTO notifications (user_id, title, message, link)
               VALUES (?, ?, ?, ?)""",
            (user_id, title, message, link)
        )

    @classmethod
    def award_points(cls, user_id: int, points: int, reason: str = ""):
        """Award green points to a student and check for badge eligibility."""
        if not user_id or points <= 0:
            return
        
        execute_db(
            "UPDATE users SET green_points = green_points + ? WHERE id = ?",
            (points, user_id)
        )
        
        user = query_db("SELECT id, username, green_points FROM users WHERE id = ?", (user_id,), one=True)
        if not user:
            return
            
        current_points = user['green_points']
        cls.notify(
            user_id,
            f"+{points} Green Points Awarded!",
            f"You earned {points} points for: {reason}. Total balance: {current_points} pts."
        )

        # Check badge eligibility
        badges = query_db("SELECT * FROM green_badges WHERE points_threshold <= ?", (current_points,))
        for b in badges:
            already = query_db(
                "SELECT 1 FROM user_badges WHERE user_id = ? AND badge_id = ?",
                (user_id, b['id']),
                one=True
            )
            if not already:
                execute_db(
                    "INSERT OR IGNORE INTO user_badges (user_id, badge_id) VALUES (?, ?)",
                    (user_id, b['id'])
                )
                cls.notify(
                    user_id,
                    f"🎖️ New Badge Unlocked: {b['name']}!",
                    f"Congratulations! You unlocked the '{b['name']}' badge ({b['description']}).",
                    link="/green-hub"
                )
