from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from models.db import query_db, execute_db
from routes.auth import login_required
from services.audit_service import AuditService

green_hub_bp = Blueprint('green_hub', __name__)

@green_hub_bp.route('/green-hub')
def green_hub():
    """
    Green Hub & Student Engagement Center.
    Presents student green points, badges, campus challenges, leaderboards, and quizzes.
    """
    # Current user's badges
    user_badges = []
    user_challenges = {}
    if g.user:
        user_badges = query_db("""
            SELECT b.*, ub.awarded_at 
            FROM green_badges b
            JOIN user_badges ub ON b.id = ub.badge_id
            WHERE ub.user_id = ?
        """, (g.user['id'],))

        participations = query_db(
            "SELECT challenge_id, status FROM challenge_participations WHERE user_id = ?",
            (g.user['id'],)
        )
        user_challenges = {p['challenge_id']: p['status'] for p in participations}

    all_badges = query_db("SELECT * FROM green_badges ORDER BY points_threshold ASC")

    # Student Leaderboard
    student_leaderboard = query_db("""
        SELECT u.id, u.full_name, u.green_points, u.avatar_color, d.name as dept_name
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        WHERE u.role = 'student'
        ORDER BY u.green_points DESC LIMIT 10
    """)

    # Department Leaderboard
    dept_leaderboard = query_db("""
        SELECT d.id, d.name, d.code, 
               COALESCE(SUM(u.green_points), 0) as total_points,
               COUNT(u.id) as student_count
        FROM departments d
        LEFT JOIN users u ON d.id = u.department_id AND u.role = 'student'
        GROUP BY d.id
        ORDER BY total_points DESC
    """)

    # Active Challenges
    challenges = query_db("SELECT * FROM challenges WHERE is_active = 1 ORDER BY points_reward DESC")

    return render_template(
        'green_hub.html',
        all_badges=all_badges,
        user_badges=user_badges,
        user_challenges=user_challenges,
        student_leaderboard=student_leaderboard,
        dept_leaderboard=dept_leaderboard,
        challenges=challenges
    )

@green_hub_bp.route('/challenges/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    """Join an active sustainability challenge."""
    challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
    if not challenge:
        flash("Challenge not found.", "warning")
        return redirect(url_for('green_hub.green_hub'))

    existing = query_db(
        "SELECT * FROM challenge_participations WHERE challenge_id = ? AND user_id = ?",
        (challenge_id, g.user['id']),
        one=True
    )
    if not existing:
        execute_db(
            "INSERT INTO challenge_participations (challenge_id, user_id, status) VALUES (?, ?, 'joined')",
            (challenge_id, g.user['id'])
        )
        execute_db("UPDATE challenges SET participants_count = participants_count + 1 WHERE id = ?", (challenge_id,))
        AuditService.notify(
            g.user['id'],
            f"Joined Challenge: {challenge['title']}",
            f"You joined the '{challenge['title']}' challenge! Complete tasks to earn +{challenge['points_reward']} Green Points.",
            link=url_for('green_hub.green_hub')
        )
        flash(f"You have joined '{challenge['title']}'! Good luck! 🌱", "success")
    else:
        flash("You are already participating in this challenge.", "info")

    return redirect(url_for('green_hub.green_hub'))

@green_hub_bp.route('/challenges/<int:challenge_id>/complete', methods=['POST'])
@login_required
def complete_challenge(challenge_id):
    """Mark a challenge as completed and claim green points."""
    challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
    if not challenge:
        flash("Challenge not found.", "warning")
        return redirect(url_for('green_hub.green_hub'))

    notes = request.form.get('proof_notes', 'Completed green challenge tasks.')

    execute_db(
        """UPDATE challenge_participations 
           SET status = 'completed', proof_notes = ?, completed_at = CURRENT_TIMESTAMP
           WHERE challenge_id = ? AND user_id = ?""",
        (notes, challenge_id, g.user['id'])
    )

    AuditService.award_points(g.user['id'], challenge['points_reward'], f"Completed challenge: {challenge['title']}")
    flash(f"Awesome! You completed '{challenge['title']}' and earned +{challenge['points_reward']} Green Points! 🏅", "success")
    return redirect(url_for('green_hub.green_hub'))

@green_hub_bp.route('/api/quiz/submit', methods=['POST'])
@login_required
def submit_quiz():
    """Submit daily sustainability quiz answers and award points."""
    data = request.get_json() or {}
    score = int(data.get('score', 0))
    total = int(data.get('total', 4))

    if score > 0:
        points_to_award = score * 10
        AuditService.award_points(g.user['id'], points_to_award, f"Scored {score}/{total} on DSU Sustainability Quiz")
        return jsonify({
            'status': 'success',
            'points_awarded': points_to_award,
            'message': f"Great job! You earned +{points_to_award} Green Points!"
        })

    return jsonify({'status': 'success', 'points_awarded': 0, 'message': 'Keep learning about campus sustainability!'})
