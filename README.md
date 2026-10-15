# CampusPulse DSU — AI-Powered Sustainable Campus
### Dayananda Sagar University (DSU), Bengaluru, Karnataka, India

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-green.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://sqlite.org)
[![Maps](https://img.shields.io/badge/Maps-Google%20Maps%20%2B%20Street%20View-4285F4.svg)](https://cloud.google.com/maps-platform)
[![License](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)

**CampusPulse DSU** is an enterprise-grade university sustainability platform built specifically for **Dayananda Sagar University (DSU)**. It empowers students, faculty, facilities technicians, and university administrators to identify environmental problems, automate green maintenance, track clean energy and water conservation, take interactive 360° virtual campus tours, and engage the campus community through gamified sustainability initiatives.

---

## 🏛️ University Customization & Verified Campus Context

- **Institution:** Dayananda Sagar University (DSU)
- **Primary Campus:** Main Innovation Campus, Kanakapura Road, Harohalli, Bengaluru Rural / Ramanagara District, Karnataka, India (`12.6582° N, 77.4475° E`).
- **City Campus:** School of Health Sciences & Medical Sciences, Kudlu Gate, Hosur Road, Bengaluru, Karnataka (`12.8906° N, 77.6416° E`).
- **Design Language:** Curated university palette featuring deep forest green (`#164227`), sage green (`#4D7C5F`, `#7A9A7B`), emerald accents, warm neutrals (`#F8FAF8`), and glassmorphism.
- **Data Integrity:** All sample data is explicitly labeled with a `Demo Sample Data` badge. Verified landmarks use authentic geographic coordinates and official building designations.

---

## 🌟 Key Features

### 1. ⚡ AI-Powered Environmental Issue Reporting
- **Intelligent Classification Engine:** Real-time NLP analysis of issue titles and descriptions as users type.
- **Automatic Category Prediction:** Water Wastage (`water`), Electricity Wastage (`electricity`), Waste Management (`waste`), Green Spaces (`greenery`), and Infrastructure (`infrastructure`).
- **Urgency Assessment:** Analyzes safety risk and resource loss to recommend `critical`, `high`, `medium`, or `low` priority with confidence ratings (e.g., 94%).
- **Estimated Environmental Impact:** Computes estimated water loss (L/day) or wasted kWh and CO2e emissions.
- **Safety & Containment Checklist:** Generates immediate containment advice (e.g., valve shut-off, circuit breaker isolation).
- **Photo Evidence Upload:** Support for image attachment with live preview and upload validation.
- **Anonymous Reporting Option:** Allows students to report issues anonymously in compliance with university policy.
- **Green Point Reward:** Awards +50 Green Points automatically on verified submission.

### 2. 🛠️ Smart Maintenance Management
- **Complete Workflow:** `Submitted` → `Verified` → `Assigned` → `In Progress` → `Resolved` (and `Reopened`).
- **Role-Based Maintenance Queue:** Filter tasks by status, department (Civil & Mechanical Facilities, Electrical, Sanitation), priority, and technician assignment.
- **Work Orders & Due Dates:** Set target deadlines with overdue task tracking.
- **Repair Verification:** Technicians upload "After" repair photographs and resolution notes.
- **Audit History Trail:** Immutable timeline logging every status transition, operator, and timestamp.

### 3. 📊 Sustainability Dashboard
- **Real-Time KPIs:** Total reports, pending issues, resolved tickets, university resolution rate (%), carbon emissions avoided (kg CO2e), solar electricity generated (kWh), and water conserved/recycled (L).
- **Interactive Visualizations:** Chart.js charts for issues by category and active urgency distribution.
- **Campus Green Targets:** Progress meters tracking electricity reduction, water conservation, and waste diversion goals.

### 4. 🤖 DSU EcoBot — AI Sustainability Assistant
- **Interactive Chat Interface:** Natural language chatbot trained on DSU campus policies and environmental engineering best practices.
- **Live Database Queries:** Real-time answers to queries like *"Summarize campus environmental status"*, *"Show active water leaks"*, or *"What is our energy trend?"*.
- **Guidance & Education:** Clear instructions for DSU 3-stream waste segregation, air conditioning setpoint policies (24°C–26°C), and rainwater harvesting.
- **Preventive Maintenance Action Plans:** Generates targeted checklists for campus facilities teams.

### 5. 📍 Operational Campus Sustainability Map
- **Leaflet & OpenStreetMap Engine:** Operational pinboard mapping all active and resolved environmental tickets.
- **Visual Status & Category Pins:** Color-coded priority borders and category icons (💧 ⚡ ♻️ 🌿 🔧).
- **Interactive Popups:** Issue summary, thumbnail preview, priority, and direct ticket links.
- **Dynamic Filtering:** Filter live map pins by category, status, and urgency.

### 6. 🏆 Green Hub & Student Engagement
- **Green Points System:** Points awarded for verified reports (+50 pts), issue resolution (+25 pts), challenge completions (+75–100 pts), and daily quiz answers (+30 pts).
- **Sustainability Badges:** Badges unlocked at milestone thresholds: *Eco Scout*, *Water Guardian*, *Watt Saver*, *Zero Waste Champion*, and *Green Innovator*.
- **Leaderboards:** Top student eco-leaders and Department Sustainability Rankings (School of Engineering, School of Health Sciences, School of Commerce).
- **Active Challenges:** Monthly student campaigns like *"Kill the Phantom Load"* and *"Zero Single-Use Plastic Week"*.
- **Daily Green Quiz:** Interactive daily sustainability trivia with instant point rewards.

### 7. ⚡ Energy, Water & Waste Management
- **Clean Energy Monitoring:** Rooftop solar photovoltaic generation logs vs grid power draw.
- **Water Conservation:** Campus water consumption vs 100% STP recycled water for landscaping and toilet flushing.
- **Circular Economy Waste Logs:** Weekly audit logs for organic food waste, composted fertilizer yield, dry recyclables, e-waste, and landfill diversion rate (%).
- **Manual Log Forms:** Dedicated entry forms for authorized facilities staff.

### 8. 🌲 Impact Analytics & Carbon Equivalency
- **Quantified Avoided Emissions:** Computes avoided CO2e based on Central Electricity Authority (CEA) India grid factors (0.82 kg CO2/kWh) and composted waste.
- **Tree Absorption Equivalent:** Translates avoided emissions into the annual absorption equivalent of mature Bangalore Neem and Gulmohar trees.

### 9. 🛡️ User Roles & Security
- **Role-Based Access Control (RBAC):**
   - `student`: Report issues, view maps, join challenges, take quizzes, earn points.
  - `staff`: View assigned queue, update workflow status, upload repair proof, log utility readings.
   - `admin`: Moderate users, manage campus locations, review system audit trail, reset demo data.
- **Security Features:** Werkzeug password hashing, session management, CSRF token validation, upload restriction (PNG, JPG, WEBP; max 16MB), and SQL injection prevention via parameterized queries.
- **Fast Demo Switcher:** Top header bar allows instant 1-click role switching for hackathon judges!

### Passwords and Recovery
- The seeded administrator account is `admin@dsu.edu.in` with the default password `admin@123`. Set `SEEDED_ADMIN_PASSWORD` in `.env` to override it, especially before deployment.
- Sign-in pages include email-code password recovery. The code is sent to the email address registered on the account.
- Email delivery uses Gmail SMTP. Configure `SMTP_USERNAME` and a Google app password in `SMTP_PASSWORD` in `.env`; `SMTP_HOST`, `SMTP_PORT`, and `SMTP_FROM_EMAIL` are also configurable. Recovery codes are hashed, expire after 10 minutes, and are limited to five attempts. Without working SMTP settings, email recovery is unavailable.

---

## 📁 Project Structure

```
campuspulse-dsu/
├── app.py                      # Flask Application factory & startup
├── config.py                   # Configuration & environment variable loading
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .env                        # Local development environment file
├── conftest.py                 # Pytest configuration
├── README.md                   # Complete documentation
│
├── models/                     # Database Layer
│   ├── __init__.py
│   ├── db.py                   # SQLite connection helpers & transaction utils
│   └── schema.sql              # Relational schema (17 tables, foreign keys, indices)
│
├── routes/                     # Blueprint Route Controllers
│   ├── __init__.py
│   ├── auth.py                 # Login, register, logout, demo fast-login
│   ├── main.py                 # Dashboard, operational map, notifications
│   ├── reports.py              # Issue submission, report detail, comments, AI API
│   ├── maintenance.py          # Maintenance queue, task assignment, status updates
│   ├── assistant.py            # DSU EcoBot AI Sustainability Assistant
│   ├── green_hub.py            # Green Points, badges, leaderboards, challenges, quiz
│   ├── monitoring.py           # Energy, water, waste logs, impact analytics
│   ├── admin.py                # Admin panel, users, locations, audit logs
│   └── api.py                  # Unified JSON APIs for map pins and stats
│
├── services/                   # Business Logic & AI Services
│   ├── __init__.py
│   ├── ai_service.py           # Real-time issue categorization & DSU EcoBot engine
│   ├── audit_service.py        # System audit logs & notification delivery
│   └── seed_service.py         # Dayananda Sagar University demo data seeder
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Main university layout & navigation
│   ├── dashboard.html          # Sustainability Dashboard
│   ├── report_issue.html       # AI-Powered Report Submission
│   ├── report_detail.html      # Detailed Report, Lifecycle Tracker & Comments
│   ├── my_reports.html         # User's submitted reports
│   ├── maintenance.html        # Smart Maintenance Queue for Staff/Admin
│   ├── sustainability_map.html # Operational Leaflet Issues Map
│   ├── assistant.html          # DSU EcoBot Chatbot Interface
│   ├── green_hub.html          # Green Hub Gamification & Badges
│   ├── monitoring.html         # Energy & Water Monitoring
│   ├── waste_management.html   # Campus Waste Records & Recycling
│   ├── impact_analytics.html   # Avoided Carbon Emissions & Tree Equivalents
│   ├── notifications.html      # In-App Status Alerts
│   ├── auth/
│   │   ├── login.html          # University Sign-In
│   │   └── register.html       # Student Registration (+50 pts bonus)
│   └── admin/
│       ├── dashboard.html      # Admin Control Panel
│       ├── users.html          # User Role Moderation
│       ├── locations.html      # Verified Campus Buildings & Wings
│       └── audit_logs.html     # System Security Audit Trail
│
├── static/                     # Static Web Assets
│   ├── css/
│   │   ├── main.css            # University Design System & Color Tokens
│   │   └── dashboard.css       # KPI cards, charts, and operational map
│   ├── js/
│   │   ├── main.js             # General UI interactions & alerts
│   │   ├── map.js              # Leaflet operational map & marker rendering
│   │   ├── report.js           # Real-time AI issue analysis & photo preview
│   │   └── assistant.js        # DSU EcoBot client-side chat interface
│   └── uploads/                # User uploaded issue photos & repair proof
│
├── instance/                   # SQLite database directory (campuspulse.db)
└── tests/                      # Automated Test Suite
   └── test_campuspulse.py     # Automated unit & integration tests
```

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10+ installed (Tested on Python 3.14)
- Pip package manager

### 1. Clone & Open Workspace
```bash
cd campuspulse-dsu
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` (already created with local development defaults):
```bash
# Windows PowerShell
copy .env.example .env
```

### 4. Run Automated Tests
```bash
python -m pytest
```
*The automated suite covers authentication, AI classification, reporting lifecycle, and role access control.*

### 5. Launch CampusPulse DSU
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🔐 Separate Account Access

Students and staff sign in through the standard sign-in page. Administrators must use the separate Administrator Sign-In page; accounts cannot cross roles, and there are no passwordless account-switch links.

For the primary seeded student, staff, and administrator accounts, configure unique `SEEDED_STUDENT_PASSWORD`, `SEEDED_STAFF_PASSWORD`, and `SEEDED_ADMIN_PASSWORD` values in the local `.env`; they are applied at startup, including to existing seed accounts. Other sample accounts receive unique random passwords. Public registration can create student and staff accounts but cannot create administrator accounts.

---

---

## 📋 Completed Features & Remaining Limitations

### Completed Features:
- [x] Full-stack architecture with Flask, SQLite, HTML5, Vanilla CSS3, and Vanilla JavaScript.
- [x] Authentic university branding for **Dayananda Sagar University (DSU)**.
- [x] AI-powered issue classification and priority recommendation with real-time UI previews.
- [x] Full 5-stage maintenance lifecycle with technician assignments, due dates, before/after photos, and audit logs.
- [x] Operational Leaflet sustainability map with category icons, priority rings, and live filters.
- [x] Interactive **DSU EcoBot** sustainability assistant with live database stats and green suggestions.
- [x] Student Green Hub gamification with points, unlocked badges, leaderboards, challenges, and quiz.
- [x] Energy, water, and waste tracking modules with manual entry forms for staff.
- [x] Calculated avoided greenhouse gas emissions (kg CO2e) and tree absorption equivalents.
- [x] Role-Based Access Control (Student, Staff, Admin) with 1-click Fast Demo Switcher.
- [x] Comprehensive automated test suite passing cleanly with 0 errors.

### Future Roadmap / Physical Constraints:
- Direct physical IoT hardware sensor integration (hardware relays, Modbus/LoRaWAN energy meters, water ultrasonic flow sensors) requires physical campus hardware installation; the software currently provides full manual logging and REST API hooks ready for automated ingestion.

---

*Developed for the Dayananda Sagar University Sustainable Campus Initiative • Bengaluru, Karnataka, India.*
