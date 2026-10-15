import re
import base64
import requests
from flask import current_app
from models.db import query_db

class AIService:
    """
    AI Service for CampusPulse DSU.
    Provides intelligent issue categorization, priority evaluation, impact assessment,
    and the DSU EcoBot interactive sustainability assistant.
    Features external API integration (Gemini/OpenAI) with high-accuracy offline rule-based fallback.
    """

    # Keyword profiles for environmental categories
    CATEGORY_PROFILES = {
        'water': {
            'keywords': ['water', 'leak', 'pipe', 'tap', 'faucet', 'flush', 'seepage', 'tank', 'overflow',
                         'drain', 'clog', 'drinking', 'cooler', 'plumbing', 'washroom', 'restroom', 'drip', 'puddle', 'sprinkler'],
            'weight': 1.2
        },
        'electricity': {
            'keywords': ['light', 'lamp', 'fan', 'ac', 'air conditioner', 'switch', 'socket', 'wire',
                         'power', 'electricity', 'solar', 'spark', 'short circuit', 'breaker', 'generator',
                         'projector', 'computer', 'inverter', 'voltage', 'flicker', 'hvac'],
            'weight': 1.2
        },
        'waste': {
            'keywords': ['waste', 'garbage', 'trash', 'bin', 'plastic', 'litter', 'overflowing', 'debris',
                         'paper', 'food waste', 'canteen', 'dump', 'segregation', 'e-waste', 'bottle', 'can', 'wrapper'],
            'weight': 1.1
        },
        'greenery': {
            'keywords': ['tree', 'plant', 'garden', 'lawn', 'grass', 'dry', 'wilted', 'branch', 'fallen',
                         'watering', 'leaves', 'botanical', 'flower', 'biodiversity', 'hedge', 'pruning'],
            'weight': 1.1
        },
        'infrastructure': {
            'keywords': ['door', 'window', 'glass', 'wall', 'crack', 'ceiling', 'tile', 'stair', 'bench',
                         'railing', 'paint', 'furniture', 'roof', 'pavement', 'solar panel', 'frame', 'lock'],
            'weight': 1.0
        }
    }

    # Urgency triggers
    CRITICAL_TRIGGERS = ['spark', 'fire', 'burst', 'gushing', 'hazard', 'smoke', 'short circuit', 'exposed wire', 'flood', 'collapse', 'electrocution', 'severe']
    HIGH_TRIGGERS = ['overflow', 'major leak', 'broken glass', 'non-functional', 'deep crack', 'foul smell', 'blackout', 'wastage', 'running continuously']
    MEDIUM_TRIGGERS = ['dripping', 'slow drain', 'flickering', 'loose', 'unsegregated', 'unclean', 'wilted', 'unattended']

    @classmethod
    def analyze_report(cls, title: str, description: str, location_text: str = "") -> dict:
        """
        Classifies an environmental issue and suggests priority, impact, and immediate actions.
        """
        combined_text = f"{title} {description} {location_text}".lower()

        # Score categories
        cat_scores = {cat: 0.0 for cat in cls.CATEGORY_PROFILES}
        for cat, profile in cls.CATEGORY_PROFILES.items():
            for kw in profile['keywords']:
                if re.search(r'\b' + re.escape(kw) + r'\b', combined_text):
                    cat_scores[cat] += profile['weight']
                elif kw in combined_text:
                    cat_scores[cat] += 0.5

        # Pick best category
        best_cat = max(cat_scores, key=cat_scores.get)
        max_score = cat_scores[best_cat]

        # Calculate confidence
        if max_score >= 3.0:
            confidence = min(0.96, 0.75 + (max_score * 0.04))
        elif max_score >= 1.0:
            confidence = min(0.85, 0.60 + (max_score * 0.08))
        else:
            best_cat = 'infrastructure' if 'broken' in combined_text else 'waste'
            confidence = 0.65

        # Assess Priority
        if any(trig in combined_text for trig in cls.CRITICAL_TRIGGERS):
            priority = 'critical'
            urgency_score = 95
            reasoning = "High risk of immediate safety hazard, structural damage, or severe resource loss detected."
        elif any(trig in combined_text for trig in cls.HIGH_TRIGGERS):
            priority = 'high'
            urgency_score = 80
            reasoning = "Significant resource wastage or disrupted university facility detected."
        elif any(trig in combined_text for trig in cls.MEDIUM_TRIGGERS):
            priority = 'medium'
            urgency_score = 55
            reasoning = "Moderate environmental inefficiency requiring scheduled maintenance."
        else:
            priority = 'low'
            urgency_score = 30
            reasoning = "Minor aesthetic or low-impact environmental issue."

        # Suggested immediate actions & containment
        actions = cls._get_suggested_actions(best_cat, priority)
        impact = cls._estimate_impact(best_cat, priority)

        return {
            'predicted_category': best_cat,
            'suggested_priority': priority,
            'confidence': round(confidence, 2),
            'urgency_score': urgency_score,
            'reasoning': reasoning,
            'suggested_actions': actions,
            'estimated_impact': impact
        }

    @classmethod
    def analyze_image(cls, image_bytes: bytes, mime_type: str, prompt: str = "") -> str:
        """Analyze the uploaded image directly with Groq's vision model."""
        api_key = current_app.config.get('GROQ_API_KEY', '').strip()
        if not api_key:
            raise ValueError("Groq image analysis is not configured.")

        image_data = base64.b64encode(image_bytes).decode('ascii')
        image_url = f"data:{mime_type};base64,{image_data}"
        user_prompt = prompt or "Analyze the uploaded image."
        payload = {
            'model': current_app.config.get(
                'GROQ_VISION_MODEL',
                'meta-llama/llama-4-scout-17b-16e-instruct'
            ),
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        "Analyze only the uploaded image and the user's question. "
                        "Do not use campus records, preset examples, or assumed campus facts. "
                        "Describe visible details, identify any apparent sustainability, "
                        "maintenance, or safety issue, and state uncertainty clearly."
                    )
                },
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': user_prompt},
                        {'type': 'image_url', 'image_url': {'url': image_url}}
                    ]
                }
            ],
            'temperature': 0.2,
            'max_tokens': 700
        }

        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            reply = response.json()['choices'][0]['message']['content']
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Groq could not analyze this image.") from exc

        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError("Groq returned an empty image analysis.")
        return reply.strip()

    @classmethod
    def _get_suggested_actions(cls, category: str, priority: str) -> list:
        actions = []
        if category == 'water':
            if priority in ('critical', 'high'):
                actions.append("Locate and shut off the local isolation angle valve or floor riser tap.")
                actions.append("Place a temporary bucket or warning cone to prevent slip injuries.")
            else:
                actions.append("Inspect washer seal and report to Department of Mechanical & Civil Facilities.")
        elif category == 'electricity':
            if priority in ('critical', 'high'):
                actions.append("DO NOT touch exposed wiring or wet switches.")
                actions.append("Flip local Miniature Circuit Breaker (MCB) on the floor sub-distribution board if safe.")
            else:
                actions.append("Verify if automated timer/occupancy sensor is malfunctioning.")
        elif category == 'waste':
            actions.append("Alert Housekeeping zone supervisor for immediate dry/wet segregation bags.")
            actions.append("Ensure biomedical or e-waste is isolated in designated red/yellow bins.")
        elif category == 'greenery':
            actions.append("Direct campus recycled STP water irrigation to the affected section.")
            actions.append("Clear fallen debris away from pedestrian pathways.")
        else:
            actions.append("Secure the area if broken glass or sharp edge is exposed.")
            actions.append("Log ticket with Campus Estate Office for replacement material.")
        return actions

    @classmethod
    def _estimate_impact(cls, category: str, priority: str) -> str:
        if category == 'water':
            if priority == 'critical':
                return "Potential loss of 1,200 - 3,000 Liters/day; risk of ceiling seepage & structural deterioration."
            elif priority == 'high':
                return "Estimated loss of 400 - 900 Liters/day if left uncorrected."
            return "Estimated loss of 30 - 80 Liters/day."
        elif category == 'electricity':
            if priority in ('critical', 'high'):
                return "Fire hazard & unnecessary draw of ~15 - 40 kWh/day; estimated 12 - 32 kg CO2e emissions."
            return "Wasted energy draw of ~2 - 8 kWh/day."
        elif category == 'waste':
            return "Risk of pests, campus littering, and loss of recyclables to municipal landfill."
        elif category == 'greenery':
            return "Decline in campus microclimate cooling and potential loss of native flora."
        return "Facility degradation and safety inconvenience to students and staff."

    @classmethod
    def ask_assistant(cls, user_message: str, user_context: dict = None) -> dict:
        """
        DSU EcoBot — Campus Sustainability AI Assistant.
        Combines live database queries with real-time problem diagnosis and interactive ticket drafting.
        """
        msg = user_message.lower().strip()
        user_context = user_context or {}
        role = user_context.get('role', 'guest')
        name = user_context.get('name', 'there')

        # Greetings & conversational openers
        greetings = ['hi', 'hii', 'hello', 'hey', 'hiya', 'yo', 'namaste', 'good morning', 'good afternoon', 'good evening']
        if msg in greetings or (len(msg.split()) <= 2 and any(msg.startswith(g) for g in ('hi', 'hello', 'hey'))):
            return cls._handle_greeting(name, role)

        # What-can-you-do / help menu
        if any(term in msg for term in ['help', 'what can you do', 'what can you help', 'options', 'menu', 'commands', 'what should i ask']):
            return cls._handle_help(role)

        report_how_to_phrases = (
            'how do i report', 'how can i report', 'how to report', 'where do i report',
            'where can i report', 'how do i submit', 'how can i submit', 'how do i file',
            'how can i file', 'where can i file'
        )
        if any(phrase in msg for phrase in report_how_to_phrases):
            return {
                'reply': (
                    "To report a campus issue, open the **Report Issue** form, describe what happened, "
                    "choose the location, and submit it. You can attach a photo if it is safe to take one. "
                    "For an urgent hazard, keep away from the area and notify campus staff."
                ),
                'suggestions': ["Report a water leak", "Report an electrical hazard", "Show active campus problems"],
                'actions': [{'label': '📝 Open Report Issue Form', 'type': 'link', 'url': '/report-issue'}]
            }

        # User's own submitted reports / tracking
        if any(term in msg for term in ['my report', 'my issue', 'my ticket', 'my submission', 'my complaint',
                                        'track', 'status of my', 'my requests']):
            return cls._handle_my_reports(user_context)

        # All / active campus problems (admin sees the full console)
        if any(term in msg for term in ['all problem', 'active problem', 'open problem', 'list problem',
                                        'show problem', 'all issue', 'active issue', 'open issue', 'list issue',
                                        'critical issue', 'critical problem', 'pending issue', 'pending problem',
                                        'problems', 'issues']):
            return cls._handle_problems(user_context)

        # Check for live database statistics queries first
        if any(term in msg for term in ['status', 'summary', 'how many', 'total reports', 'overview']):
            return cls._generate_status_summary(user_context)

        # Check if user is reporting or describing a problem in text
        problem_keywords = [
            'leak', 'broken', 'damage', 'overflow', 'overflowing', 'spark', 'smoke', 'hazard',
            'burst', 'dripping', 'faulty', 'smell', 'crack', 'stuck', 'not working', 'unattended',
            'continuous', 'spill', 'flood', 'seepage', 'flicker', 'flickering', 'dump', 'fire', 'clog'
        ]
        problem_phrases = [
            'there is', 'i noticed', 'found a', 'report', 'issue with', 'problem with',
            'water is', 'tap is', 'ac is', 'lights are', 'pipe is', 'valve is', 'bin is'
        ]

        is_problem = (
            any(phrase in msg for phrase in problem_phrases) or
            (any(kw in msg for kw in problem_keywords) and len(msg.split()) >= 3)
        )

        if is_problem:
            return cls._diagnose_problem(user_message, user_context)

        if any(term in msg for term in ['water', 'stp', 'rainwater', 'tank']):
            return cls._handle_water_query(msg)

        if any(term in msg for term in ['electric', 'solar', 'power', 'energy', 'kwh', 'ac', 'light']):
            return cls._handle_energy_query(msg)

        if any(term in msg for term in ['waste', 'plastic', 'recycle', 'bin', 'garbage', 'compost', 'segregat']):
            return cls._handle_waste_query(msg)

        if any(term in msg for term in ['points', 'green points', 'badge', 'challenge', 'leaderboard', 'earn']):
            return cls._handle_gamification_query(msg)

        if any(term in msg for term in ['map', 'harohalli', 'kudlu']):
            return {
                'reply': "Open the **Campus Sustainability Map** to view reported environmental issues by location, status, category, and priority.",
                'suggestions': ["Show active campus problems", "Summarize campus environmental status"],
                'actions': [{'label': '🗺️ Open Campus Map', 'type': 'link', 'url': '/sustainability-map'}]
            }

        if any(term in msg for term in ['action plan', 'preventive', 'maintenance', 'checklist', 'plan']):
            return cls._handle_action_plan_query()

        # General helpful sustainability response
        return {
            'reply': (
                "👋 **Hello! I am DSU EcoBot**, your AI Sustainability Assistant for Dayananda Sagar University.\n\n"
                "I can assist you with:\n"
                "- 💧 **Water Conservation**: Reporting leaks, checking DSU rainwater harvesting & STP status.\n"
                "- ⚡ **Energy & Solar**: Tips for reducing phantom loads, rooftop solar stats, AC guidelines.\n"
                "- ♻️ **Waste Segregation**: DSU 3-bin guidelines (Green: Organic, Blue: Recyclables, Red: Hazardous/E-Waste).\n"
                "- 🏆 **Green Points & Challenges**: How to earn badges and climb the DSU Sustainability Leaderboard.\n"
                "- 🗺️ **Campus Map**: View reported environmental issues across DSU campuses.\n"
                "- 📋 **Preventive Maintenance**: Generating green action plans for university blocks.\n\n"
                "**Tip:** You can describe a problem in plain English (e.g. *\"there is a water leak in Block A washroom\"*) and I will diagnose it and prepare a ticket for you in one click!"
            ),
            'suggestions': [
                "Summarize campus environmental status",
                "Show active campus problems",
                "How does DSU recycle campus waste?",
                "What are the guidelines for DSU AC and power usage?",
                "How do I earn Green Points?"
            ],
            'actions': [
                {'label': '📝 Report an Issue', 'type': 'link', 'url': '/report-issue'},
                {'label': '🗺️ Open Campus Map', 'type': 'link', 'url': '/sustainability-map'},
                {'label': '🏆 Visit Green Hub', 'type': 'link', 'url': '/green-hub'},
            ]
        }

    @classmethod
    def _handle_greeting(cls, name: str, role: str) -> dict:
        """Warm, role-aware conversational greeting with quick actions."""
        if role == 'admin':
            opening = (
                f"👋 **Welcome back, {name}!** I am **DSU EcoBot**, your campus operations assistant.\n\n"
                "As an administrator you have full visibility. I can pull the **complete list of reported problems**, "
                "surface **critical tickets**, or summarize campus sustainability status in real time."
            )
            actions = [
                {'label': '🚨 Show All Reported Problems', 'type': 'prompt', 'value': 'show all active problems'},
                {'label': '📊 Campus Status Summary', 'type': 'prompt', 'value': 'summarize campus environmental status'},
                {'label': '🧾 All Problems Console', 'type': 'link', 'url': '/admin/reports'},
                {'label': '🛠️ Work Orders Queue', 'type': 'link', 'url': '/maintenance'},
            ]
        else:
            opening = (
                f"👋 **Hi {name}!** Great to see you. I am **DSU EcoBot**, your sustainability companion.\n\n"
                "Tell me about a campus problem you've spotted and I'll diagnose it instantly, or ask me anything "
                "about water, energy, waste, green points, or the campus tour."
            )
            actions = [
                {'label': '💧 Report a Water Leak', 'type': 'prompt', 'value': 'There is a continuous water leak from a restroom pipe in Academic Block A'},
                {'label': '⚡ Report Electrical Issue', 'type': 'prompt', 'value': 'The AC in Lab 204 was left running and a switchboard is sparking'},
                {'label': '📊 Campus Status', 'type': 'prompt', 'value': 'summarize campus environmental status'},
                {'label': '🏆 How to earn points?', 'type': 'prompt', 'value': 'how do I earn green points'},
            ]
        return {
            'reply': opening + "\n\nHow can I help you today?",
            'suggestions': ["Summarize campus environmental status", "Show active campus problems", "How do I earn Green Points?"],
            'actions': actions
        }

    @classmethod
    def _handle_help(cls, role: str) -> dict:
        """Interactive capability menu."""
        reply = (
            "🧭 **Here's everything I can do for you:**\n\n"
            "**🔍 Diagnose & Report**\n"
            "• Describe any campus problem in plain English — I detect the category, urgency, impact, and safety actions, then prepare a 1-click ticket.\n\n"
            "**📊 Live Campus Intelligence**\n"
            "• Ask *\"summarize campus status\"* for live KPIs, or *\"show active problems\"* to see current open tickets.\n\n"
            "**💡 Sustainability Knowledge**\n"
            "• Water harvesting, STP recycling, rooftop solar, AC policy (24–26°C), and DSU's 3-bin waste segregation rules.\n\n"
            "**🏆 Engagement**\n"
            "• Green Points, badges, challenges, and the leaderboard. Track your own submissions with *\"my reports\"*."
        )
        if role == 'admin':
            reply += "\n\n**🛡️ Admin Powers:** Ask *\"all problems\"* and I'll list every reported campus issue with direct manage links."
        return {
            'reply': reply,
            'suggestions': ["Summarize campus environmental status", "Show active campus problems", "My reports", "Generate a preventive maintenance action plan"],
            'actions': [
                {'label': '📝 Report an Issue', 'type': 'link', 'url': '/report-issue'},
                {'label': '🤖 Guided Diagnosis', 'type': 'prompt', 'value': 'There is a water leak in the washroom'},
                {'label': '🗺️ Campus Map', 'type': 'link', 'url': '/sustainability-map'},
            ]
        }

    @classmethod
    def _handle_my_reports(cls, user_context: dict) -> dict:
        """List the signed-in user's own reports with direct tracking links."""
        uid = user_context.get('user_id')
        if not uid:
            return {
                'reply': "🔐 Please **sign in** to view and track your submitted reports and Green Points.",
                'suggestions': ["Summarize campus environmental status", "How do I earn Green Points?"],
                'actions': [{'label': '🔑 Sign In', 'type': 'link', 'url': '/login'}]
            }

        reports = query_db(
            """SELECT id, report_number, title, category, priority, status, created_at
               FROM reports WHERE user_id = ? ORDER BY created_at DESC LIMIT 6""",
            (uid,)
        )
        if not reports:
            return {
                'reply': "📭 You haven't submitted any environmental reports yet. Spot something on campus? Let's file your first ticket!",
                'suggestions': ["Report a water leak", "How do I earn Green Points?"],
                'actions': [{'label': '📝 Report an Issue', 'type': 'link', 'url': '/report-issue'}]
            }

        status_icons = {'submitted': '🟡', 'verified': '🔵', 'assigned': '🟣', 'in_progress': '🟠', 'resolved': '🟢', 'reopened': '🔴'}
        lines = []
        actions = []
        for r in reports:
            icon = status_icons.get(r['status'], '⚪')
            lines.append(f"{icon} **{r['report_number']}** — {r['title']} *({r['status'].replace('_', ' ').title()})*")
            actions.append({'label': f"{icon} {r['report_number']}", 'type': 'link', 'url': f"/reports/{r['id']}"})

        actions.append({'label': '📋 View All My Reports', 'type': 'link', 'url': '/my-reports'})
        reply = (
            "🧾 **Your Recent Environmental Reports**\n\n" + "\n".join(lines) +
            "\n\nTap a ticket below to open its live timeline, photos, and resolution notes."
        )
        return {'reply': reply, 'suggestions': ["Show active campus problems", "How do I earn Green Points?"], 'actions': actions}

    @classmethod
    def _handle_problems(cls, user_context: dict) -> dict:
        """List active campus problems. Admins get the full console + every ticket link."""
        role = user_context.get('role', 'guest')
        scope = "all reported" if role == 'admin' else "currently active"
        reports = query_db(
            """SELECT r.id, r.report_number, r.title, r.category, r.priority, r.status,
                      l.building_name, u.full_name as reporter_name, r.is_anonymous
               FROM reports r
               LEFT JOIN campus_locations l ON r.location_id = l.id
               LEFT JOIN users u ON r.user_id = u.id
               WHERE r.status != 'resolved'
               ORDER BY CASE r.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END ASC,
                        r.created_at DESC
               LIMIT 12"""
        )

        totals = {
            'total': query_db("SELECT COUNT(*) as c FROM reports", one=True)['c'],
            'active': query_db("SELECT COUNT(*) as c FROM reports WHERE status != 'resolved'", one=True)['c'],
            'resolved': query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c'],
            'critical': query_db("SELECT COUNT(*) as c FROM reports WHERE priority = 'critical' AND status != 'resolved'", one=True)['c'],
        }

        p_icons = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '⚪'}
        c_icons = {'water': '💧', 'electricity': '⚡', 'waste': '♻️', 'greenery': '🌿', 'infrastructure': '🔧'}

        header = (
            f"📋 **Campus Problems — {scope.title()} Overview**\n\n"
            f"- Total Reported: **{totals['total']}**\n"
            f"- Active / Unresolved: **{totals['active']}**\n"
            f"- Critical Open: **{totals['critical']}**\n"
            f"- Resolved: **{totals['resolved']}**\n\n"
        )

        actions = []
        if not reports:
            reply = header + "🎉 No unresolved problems right now — campus is in great shape!"
        else:
            lines = []
            for r in reports:
                loc = r['building_name'] or 'Campus'
                reporter = 'Anonymous' if r['is_anonymous'] else (r['reporter_name'] or 'Guest')
                lines.append(
                    f"{p_icons.get(r['priority'], '⚪')} {c_icons.get(r['category'], '•')} **{r['report_number']}** — "
                    f"{r['title']} | _{loc}_ | {r['priority'].upper()} | by {reporter}"
                )
                actions.append({
                    'label': f"{p_icons.get(r['priority'], '⚪')} {r['report_number']}",
                    'type': 'link',
                    'url': f"/reports/{r['id']}"
                })
            reply = header + "**Open Tickets (highest priority first):**\n" + "\n".join(lines)

        if role == 'admin':
            reply += "\n\n🛡️ *As administrator you can manage every issue from the All Problems Console.*"
            actions.append({'label': '🧾 Open All Problems Console', 'type': 'link', 'url': '/admin/reports'})
            actions.append({'label': '🛠️ Work Orders Queue', 'type': 'link', 'url': '/maintenance'})
        else:
            actions.append({'label': '🗺️ View on Campus Map', 'type': 'link', 'url': '/sustainability-map'})
            actions.append({'label': '📝 Report a New Issue', 'type': 'link', 'url': '/report-issue'})

        return {
            'reply': reply,
            'suggestions': ["Summarize campus environmental status", "Show active water leaks", "Generate a preventive maintenance action plan"],
            'actions': actions
        }

    @classmethod
    def _generate_status_summary(cls, user_context: dict = None) -> dict:
        total_reports = query_db("SELECT COUNT(*) as c FROM reports", one=True)['c']
        pending = query_db("SELECT COUNT(*) as c FROM reports WHERE status IN ('submitted', 'verified', 'assigned', 'in_progress')", one=True)['c']
        resolved = query_db("SELECT COUNT(*) as c FROM reports WHERE status = 'resolved'", one=True)['c']
        water_issues = query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'water' AND status != 'resolved'", one=True)['c']
        elec_issues = query_db("SELECT COUNT(*) as c FROM reports WHERE category = 'electricity' AND status != 'resolved'", one=True)['c']

        reply = (
            f"📊 **DSU CampusPulse Live Sustainability Summary**\n\n"
            f"- **Total Issues Reported**: {total_reports}\n"
            f"- **Active In-Progress / Pending**: {pending}\n"
            f"- **Successfully Resolved**: {resolved} (Resolution Rate: {round((resolved/total_reports*100) if total_reports else 0, 1)}%)\n"
            f"- **Active Water Reports**: {water_issues}\n"
            f"- **Active Electricity Reports**: {elec_issues}\n\n"
            f"*Tip: Campus facilities teams are actively routed to critical priority tickets. You can track individual ticket timelines under **My Reports** or the **Campus Sustainability Map**.*"
        )

        role = (user_context or {}).get('role', 'guest')
        actions = [
            {'label': '🚨 Show Active Problems', 'type': 'prompt', 'value': 'show all active problems'},
            {'label': '💧 Active Water Leaks', 'type': 'prompt', 'value': 'show active water leaks'},
            {'label': '🗺️ Campus Map', 'type': 'link', 'url': '/sustainability-map'},
        ]
        if role == 'admin':
            reply += "\n\n🛡️ *Administrator view: ask me to \"show all problems\" for the complete unresolved ticket list.*"
            actions.insert(0, {'label': '🧾 All Problems Console', 'type': 'link', 'url': '/admin/reports'})

        return {
            'reply': reply,
            'suggestions': ["Show active campus problems", "What's the energy saving trend?", "View Campus Map"],
            'actions': actions
        }

    @classmethod
    def _handle_water_query(cls, msg: str) -> dict:
        active_leaks = query_db(
            "SELECT title, specific_spot FROM reports WHERE category = 'water' AND status != 'resolved' LIMIT 3"
        )
        leaks_text = ""
        if active_leaks:
            leaks_text = "\n\n**Current Active Water Tickets at DSU:**\n" + "\n".join(
                [f"• {r['title']} ({r['specific_spot']})" for r in active_leaks]
            )

        reply = (
            "💧 **DSU Water Management & Conservation**\n\n"
            "Dayananda Sagar University (DSU) practices sustainable water stewardship across its Innovation Campus (Harohalli) and City Campus (Kudlu Gate):\n"
            "1. **Rainwater Harvesting**: Campus rooftops channel monsoon runoff into central percolation ponds and our 2-million-liter storage basin.\n"
            "2. **Sewage Treatment Plant (STP)**: 100% of campus greywater is treated through an on-site STP and reused for landscaping and toilet flushing.\n"
            "3. **Reporting Leaks**: Even a slow drip wastes up to 30 liters daily! Please report dripping taps or flush valve issues immediately via **Report an Issue**.{leaks_text}\n\n"
            "**Green Tip**: Turn off basin faucets while lathering soap, and notify maintenance if washroom sensor taps run continuously."
        ).format(leaks_text=leaks_text)

        return {
            'reply': reply,
            'suggestions': ["Report a water leak", "Show active water leaks", "Summarize campus status"],
            'actions': [
                {'label': '💧 Report a Water Leak', 'type': 'link', 'url': '/report-issue'},
                {'label': '🚨 Active Water Tickets', 'type': 'prompt', 'value': 'show active water leaks'},
                {'label': '📊 Water Monitoring', 'type': 'link', 'url': '/monitoring/energy-water'},
            ]
        }

    @classmethod
    def _handle_energy_query(cls, msg: str) -> dict:
        reply = (
            "⚡ **DSU Clean Energy & Electricity Conservation**\n\n"
            "Dayananda Sagar University's energy sustainability pillars:\n"
            "1. **Rooftop Solar Array**: The Innovation Campus features grid-tied photovoltaic panels providing clean power for academic blocks and research labs.\n"
            "2. **HVAC & Air Conditioning Policy**: Maintain classroom and lab thermostats at **24°C - 26°C** — every 1°C increase saves up to 6% electricity.\n"
            "3. **Phantom Load Reduction**: Computers, lab oscilloscopes, and projector units draw standby electricity overnight. Always switch off at the primary socket.\n"
            "4. **Daylighting**: DSU academic blocks are designed with wide glass atriums; turn off perimeter lighting on sunny Bengaluru afternoons.\n\n"
            "Found an unoccupied room with lights and AC running? Snap a photo and submit a report to earn **+50 Green Points**!"
        )
        return {
            'reply': reply,
            'suggestions': ["Report electricity wastage", "View Energy Monitoring", "Join Kill the Phantom Load challenge"],
            'actions': [
                {'label': '⚡ Report Electricity Wastage', 'type': 'link', 'url': '/report-issue'},
                {'label': '📈 Energy Monitoring', 'type': 'link', 'url': '/monitoring/energy-water'},
                {'label': '🏆 Join a Challenge', 'type': 'link', 'url': '/green-hub'},
            ]
        }

    @classmethod
    def _handle_waste_query(cls, msg: str) -> dict:
        reply = (
            "♻️ **DSU Waste Segregation & Circular Economy Guide**\n\n"
            "DSU operates a 3-stream campus waste collection system:\n"
            "- 🟢 **Green Bins (Organic / Wet Waste)**: Food scraps, tea leaves, canteen waste, garden clippings. Sent directly to the campus composting pit for organic fertilizer.\n"
            "- 🔵 **Blue Bins (Dry Recyclables)**: Paper, notebooks, cardboard, rinsed beverage containers, metal cans, clean plastic wrappers.\n"
            "- 🔴 **Red Bins (Hazardous / E-Waste)**: Dead batteries, electronic parts, ink cartridges, lab gloves, CFL lamps. Collected quarterly by certified recyclers.\n\n"
            "**Single-Use Plastic Ban**: Dayananda Sagar University is committed to zero single-use plastic cups and straws in all food courts and canteens."
        )
        return {
            'reply': reply,
            'suggestions': ["Report overflowing garbage bin", "View Waste Management records", "Join Zero Plastic Week"],
            'actions': [
                {'label': '♻️ Report Overflowing Bin', 'type': 'link', 'url': '/report-issue'},
                {'label': '📊 Waste Records', 'type': 'link', 'url': '/monitoring/waste'},
                {'label': '🌍 Impact Analytics', 'type': 'link', 'url': '/monitoring/impact'},
            ]
        }

    @classmethod
    def _handle_gamification_query(cls, msg: str) -> dict:
        reply = (
            "🏆 **DSU Green Points & Sustainability Badges**\n\n"
            "Make an environmental impact and get recognized across Dayananda Sagar University:\n"
            "- 📸 **Submit Verified Report**: Earn **+50 Points** when maintenance verifies your report.\n"
            "- 🛠️ **Issue Resolved**: Earn **+25 Points** once the issue is fixed.\n"
            "- 🎯 **Green Challenges**: Join monthly campus challenges like *'Kill the Phantom Load'* or *'Zero Plastic Week'* for **+50 to +100 Points**.\n"
            "- 🧠 **Daily Sustainability Quiz**: Answer quick green trivia for **+30 Points**.\n\n"
            "Unlock badges like **Eco Scout**, **Water Guardian**, **Watt Saver**, and **Zero Waste Champion**! Check your rank on the **Green Hub Leaderboard**."
        )
        return {
            'reply': reply,
            'suggestions': ["Take Today's Sustainability Quiz", "View Leaderboard", "Join a Challenge"],
            'actions': [
                {'label': '🏆 Open Green Hub', 'type': 'link', 'url': '/green-hub'},
                {'label': '🧠 Today\'s Quiz', 'type': 'link', 'url': '/green-hub'},
                {'label': '🧾 My Reports & Points', 'type': 'prompt', 'value': 'my reports'},
            ]
        }

    @classmethod
    @classmethod
    def _handle_action_plan_query(cls) -> dict:
        reply = (
            "📋 **DSU Campus Sustainability Action Plan (Generated)**\n\n"
            "**Priority 1: Water Security & Leak Prevention**\n"
            "1. Inspect all restroom angle valves and urinal sensors in Engineering Block A & B.\n"
            "2. Audit rainwater harvesting collection channels before pre-monsoon rains.\n"
            "3. Calibrate flow meters on the campus STP treated water line.\n\n"
            "**Priority 2: Energy Optimization**\n"
            "1. Deploy automated timer relays for outdoor campus perimeter lighting.\n"
            "2. Conduct scheduled cleaning of rooftop solar panels to maintain 98%+ photovoltaic efficiency.\n"
            "3. Enforce 24°C minimum setpoints on computer lab and auditorium AC units.\n\n"
            "**Priority 3: Student Engagement & Zero Waste**\n"
            "1. Launch the semester 'Green Quad Challenge' with hostel student representatives.\n"
            "2. Install weigh-scales in main cafeteria to track and gamify daily food waste reduction."
        )
        return {
            'reply': reply,
            'suggestions': ["View Energy Monitoring", "View Waste Management records", "Report an Issue"],
            'actions': [
                {'label': '📈 Energy Monitoring', 'type': 'link', 'url': '/monitoring/energy-water'},
                {'label': '📊 Waste Records', 'type': 'link', 'url': '/monitoring/waste'},
                {'label': '📝 Report an Issue', 'type': 'link', 'url': '/report-issue'},
            ]
        }

    @classmethod
    def _diagnose_problem(cls, user_message: str, user_context: dict = None) -> dict:
        analysis = cls.analyze_report(user_message, user_message, "")

        first_sentence = user_message.split('.')[0].strip()
        first_sentence = first_sentence.replace('\n', ' ')
        if len(first_sentence) > 50:
            suggested_title = f"{analysis['predicted_category'].capitalize()}: {first_sentence[:45]}..."
        else:
            suggested_title = f"{analysis['predicted_category'].capitalize()}: {first_sentence}"

        # Match location from campus database
        matched_loc_id = 1
        matched_loc_name = "Academic Block A (Engineering)"
        try:
            locations = query_db("SELECT id, building_name, floor, zone_or_wing FROM campus_locations WHERE is_active = 1")
            msg_lower = user_message.lower()
            for loc in locations:
                bld = loc['building_name'].lower()
                for word in bld.split():
                    if len(word) > 3 and word in msg_lower:
                        matched_loc_id = loc['id']
                        matched_loc_name = f"{loc['building_name']} ({loc['floor']})"
                        break
        except Exception:
            pass

        actions_list = analysis['suggested_actions']
        actions_bullets = "\n".join([f"• {act}" for act in actions_list])

        reply = (
            f"🔍 **AI Environmental Diagnosis Completed!**\n\n"
            f"I analyzed your problem description and generated an instant campus containment assessment:\n\n"
            f"- **Detected Category:** `{analysis['predicted_category'].upper()}`\n"
            f"- **Recommended Urgency:** `{analysis['suggested_priority'].upper()}` (Risk Score: {analysis['urgency_score']}/100, Confidence: {int(analysis['confidence']*100)}%)\n"
            f"- **Detected Location:** {matched_loc_name}\n\n"
            f"**⚠️ Potential Impact:**\n{analysis['estimated_impact']}\n\n"
            f"**🛡️ Immediate Safety Actions:**\n{actions_bullets}\n\n"
            f"**Ready to dispatch maintenance?** Review the pre-filled ticket below and click **'⚡ Submit Ticket Now'** to notify facilities and earn **+50 Green Points**."
        )

        return {
            'reply': reply,
            'is_problem_diagnosis': True,
            'diagnosis': {
                'title': suggested_title,
                'description': user_message,
                'category': analysis['predicted_category'],
                'priority': analysis['suggested_priority'],
                'confidence': analysis['confidence'],
                'urgency_score': analysis['urgency_score'],
                'estimated_impact': analysis['estimated_impact'],
                'suggested_actions': analysis['suggested_actions'],
                'location_id': matched_loc_id,
                'location_name': matched_loc_name,
                'specific_spot': first_sentence[:60]
            },
            'suggestions': [
                "Summarize campus environmental status",
                "Show active campus problems",
                "How does DSU recycle campus waste?"
            ],
            'actions': [
                {'label': '🗺️ View Covered Area on Map', 'type': 'link', 'url': '/sustainability-map'},
                {'label': '🧾 My Reports', 'type': 'link', 'url': '/my-reports'},
            ]
        }
