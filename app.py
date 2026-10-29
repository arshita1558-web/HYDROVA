import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-demo-secret-change-before-deployment")
DATABASE = os.path.join(os.path.dirname(__file__), "aquaalert.db")

# For a local classroom demo only. Set AQUAADMIN_PASSWORD to a stronger value before sharing.
ADMIN_PASSWORD = os.environ.get("AQUAADMIN_PASSWORD", "AquaDemo123!")
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

SYMPTOM_OPTIONS = [
    "Diarrhoea", "Vomiting", "Fever", "Stomach pain", "Nausea", "Other"
]
AGE_GROUPS = ["Under 5", "5–17", "18–59", "60+", "Not recorded"]
WATER_RESULTS = ["Safe", "Unsafe", "Needs retesting", "Not tested"]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS symptom_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                village TEXT NOT NULL,
                report_date TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                age_group TEXT NOT NULL DEFAULT 'Not recorded',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS water_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                village TEXT NOT NULL,
                test_date TEXT NOT NULL,
                result TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                village TEXT NOT NULL,
                alert_date TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(village, alert_date, alert_type)
            );
        """)
        db.commit()


def create_or_refresh_alerts():
    """Create review alerts from simple rules; these are not medical diagnoses."""
    today = date.today()
    recent_start = (today - timedelta(days=2)).isoformat()
    baseline_start = (today - timedelta(days=9)).isoformat()
    baseline_end = (today - timedelta(days=3)).isoformat()

    with get_db() as db:
        villages = db.execute("""
            SELECT village FROM symptom_reports
            UNION
            SELECT village FROM water_reports
        """).fetchall()

        for item in villages:
            village = item["village"]

            recent_count = db.execute("""
                SELECT COUNT(*) AS n FROM symptom_reports
                WHERE village = ? AND report_date BETWEEN ? AND ?
            """, (village, recent_start, today.isoformat())).fetchone()["n"]

            baseline_count = db.execute("""
                SELECT COUNT(*) AS n FROM symptom_reports
                WHERE village = ? AND report_date BETWEEN ? AND ?
            """, (village, baseline_start, baseline_end)).fetchone()["n"]

            # Simple demo rule: at least 5 reports in the last 3 days and
            # at least twice the expected count based on the previous 7 days.
            expected_recent = baseline_count / 7 * 3
            unusual_increase = recent_count >= 5 and (
                baseline_count == 0 or recent_count >= max(5, 2 * expected_recent)
            )

            if unusual_increase:
                message = (
                    f"{recent_count} symptom reports were recorded in the last 3 days. "
                    "Please review the reports and investigate if appropriate."
                )
                db.execute("""
                    INSERT OR IGNORE INTO alerts
                    (village, alert_date, alert_type, message, status)
                    VALUES (?, ?, 'Symptom increase', ?, 'Open')
                """, (village, today.isoformat(), message))

            unsafe = db.execute("""
                SELECT COUNT(*) AS n FROM water_reports
                WHERE village = ? AND result = 'Unsafe'
                  AND test_date >= ?
            """, (village, (today - timedelta(days=14)).isoformat())).fetchone()["n"]

            if unsafe:
                message = (
                    "A water report is marked Unsafe within the last 14 days. "
                    "A qualified local authority should verify the result and decide next steps."
                )
                db.execute("""
                    INSERT OR IGNORE INTO alerts
                    (village, alert_date, alert_type, message, status)
                    VALUES (?, ?, 'Water quality', ?, 'Open')
                """, (village, today.isoformat(), message))

        db.commit()


@app.context_processor
def inject_globals():
    return {"today": date.today().isoformat()}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin panel.", "info")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    create_or_refresh_alerts()
    with get_db() as db:
        symptom_total = db.execute("SELECT COUNT(*) FROM symptom_reports").fetchone()[0]
        water_total = db.execute("SELECT COUNT(*) FROM water_reports").fetchone()[0]
        open_alerts = db.execute("SELECT COUNT(*) FROM alerts WHERE status = 'Open'").fetchone()[0]
        village_total = db.execute("""
            SELECT COUNT(*) FROM (
                SELECT village FROM symptom_reports UNION SELECT village FROM water_reports
            )
        """).fetchone()[0]
        recent_reports = db.execute("""
            SELECT id, village, report_date, symptoms, 'Symptom' AS report_type
            FROM symptom_reports
            UNION ALL
            SELECT id, village, test_date AS report_date, result AS symptoms, 'Water' AS report_type
            FROM water_reports
            ORDER BY report_date DESC LIMIT 6
        """).fetchall()
        alerts = db.execute("""
            SELECT * FROM alerts ORDER BY
            CASE status WHEN 'Open' THEN 0 WHEN 'Reviewed' THEN 1 ELSE 2 END,
            alert_date DESC LIMIT 5
        """).fetchall()
    return render_template(
        "index.html", symptom_total=symptom_total, water_total=water_total,
        open_alerts=open_alerts, village_total=village_total,
        recent_reports=recent_reports, alerts=alerts
    )


@app.route("/report", methods=["GET", "POST"])
def report_symptoms():
    if request.method == "POST":
        village = request.form.get("village", "").strip()
        report_date = request.form.get("report_date", "").strip()
        symptoms = request.form.getlist("symptoms")
        age_group = request.form.get("age_group", "Not recorded")
        notes = request.form.get("notes", "").strip()[:500]

        try:
            parsed_date = date.fromisoformat(report_date)
            valid_date = parsed_date <= date.today() and parsed_date >= date.today() - timedelta(days=90)
        except ValueError:
            valid_date = False

        if not village or len(village) > 100:
            flash("Enter a village or community name (up to 100 characters).", "error")
        elif not valid_date:
            flash("Choose a valid date within the last 90 days.", "error")
        elif not symptoms or any(s not in SYMPTOM_OPTIONS for s in symptoms):
            flash("Choose at least one symptom.", "error")
        elif age_group not in AGE_GROUPS:
            flash("Choose a valid age group.", "error")
        else:
            with get_db() as db:
                db.execute("""
                    INSERT INTO symptom_reports (village, report_date, symptoms, age_group, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (village, report_date, ", ".join(symptoms), age_group, notes))
                db.commit()
            create_or_refresh_alerts()
            flash("Symptom report saved. It will be included in community trend monitoring.", "success")
            return redirect(url_for("report_symptoms"))

    return render_template("report.html", symptom_options=SYMPTOM_OPTIONS, age_groups=AGE_GROUPS)


@app.route("/water", methods=["GET", "POST"])
def water_report():
    if request.method == "POST":
        village = request.form.get("village", "").strip()
        test_date = request.form.get("test_date", "").strip()
        result = request.form.get("result", "")
        notes = request.form.get("notes", "").strip()[:500]

        try:
            parsed_date = date.fromisoformat(test_date)
            valid_date = parsed_date <= date.today() and parsed_date >= date.today() - timedelta(days=90)
        except ValueError:
            valid_date = False

        if not village or len(village) > 100:
            flash("Enter a village or community name (up to 100 characters).", "error")
        elif not valid_date:
            flash("Choose a valid date within the last 90 days.", "error")
        elif result not in WATER_RESULTS:
            flash("Choose a valid water-testing result.", "error")
        else:
            with get_db() as db:
                db.execute("""
                    INSERT INTO water_reports (village, test_date, result, notes)
                    VALUES (?, ?, ?, ?)
                """, (village, test_date, result, notes))
                db.commit()
            create_or_refresh_alerts()
            flash("Water-quality report saved.", "success")
            return redirect(url_for("water_report"))

    return render_template("water.html", water_results=WATER_RESULTS)


@app.route("/alerts")
def alerts_page():
    create_or_refresh_alerts()
    with get_db() as db:
        alerts = db.execute("""
            SELECT * FROM alerts
            ORDER BY CASE status WHEN 'Open' THEN 0 WHEN 'Reviewed' THEN 1 ELSE 2 END,
                     alert_date DESC
        """).fetchall()
    return render_template("alerts.html", alerts=alerts)


@app.route("/analytics")
def analytics():
    with get_db() as db:
        daily = db.execute("""
            SELECT report_date AS day, COUNT(*) AS total
            FROM symptom_reports
            WHERE report_date >= ?
            GROUP BY report_date ORDER BY report_date
        """, ((date.today() - timedelta(days=13)).isoformat(),)).fetchall()
        by_village = db.execute("""
            SELECT village, COUNT(*) AS total
            FROM symptom_reports GROUP BY village ORDER BY total DESC LIMIT 8
        """).fetchall()
        water = db.execute("""
            SELECT result, COUNT(*) AS total FROM water_reports GROUP BY result
        """).fetchall()
    return render_template("analytics.html", daily=daily, by_village=by_village, water=water)


@app.route("/awareness")
def awareness():
    return render_template("awareness.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("You are logged in.", "success")
            return redirect(url_for("admin"))
        flash("Incorrect password.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    create_or_refresh_alerts()
    with get_db() as db:
        symptoms = db.execute("SELECT * FROM symptom_reports ORDER BY report_date DESC, id DESC").fetchall()
        water = db.execute("SELECT * FROM water_reports ORDER BY test_date DESC, id DESC").fetchall()
        alerts = db.execute("SELECT * FROM alerts ORDER BY alert_date DESC, id DESC").fetchall()
    return render_template("admin.html", symptoms=symptoms, water=water, alerts=alerts)


@app.route("/admin/alert/<int:alert_id>", methods=["POST"])
@admin_required
def update_alert(alert_id):
    status = request.form.get("status", "")
    if status not in ["Open", "Reviewed", "Resolved"]:
        flash("Invalid alert status.", "error")
    else:
        with get_db() as db:
            db.execute("UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id))
            db.commit()
        flash("Alert status updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/seed-demo", methods=["POST"])
@admin_required
def seed_demo():
    """Add clearly fictional sample records so charts can be demonstrated."""
    today = date.today()
    villages = ["Demo Village A", "Demo Village B"]
    with get_db() as db:
        # Only seed once to avoid duplicate demo data on repeated clicks.
        already_seeded = db.execute(
            "SELECT COUNT(*) FROM symptom_reports WHERE village LIKE 'Demo Village %'"
        ).fetchone()[0]
        if already_seeded:
            flash("Demo data already exists. No additional sample rows were added.", "info")
        else:
            for offset in range(0, 10):
                day = (today - timedelta(days=offset)).isoformat()
                count = (1 if offset > 2 else 3) if offset < 7 else 1
                for _ in range(count):
                    db.execute("""
                        INSERT INTO symptom_reports (village, report_date, symptoms, age_group, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (villages[0], day, "Diarrhoea", "18–59", "Fictional demo record"))
            for offset in range(0, 5):
                day = (today - timedelta(days=offset)).isoformat()
                for _ in range(2 if offset < 3 else 1):
                    db.execute("""
                        INSERT INTO symptom_reports (village, report_date, symptoms, age_group, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (villages[1], day, "Fever, Stomach pain", "5–17", "Fictional demo record"))
            db.execute("""
                INSERT INTO water_reports (village, test_date, result, notes)
                VALUES (?, ?, ?, ?)
            """, ("Demo Village A", today.isoformat(), "Needs retesting", "Fictional demo record"))
            db.commit()
            create_or_refresh_alerts()
            flash("Fictional demo data added successfully.", "success")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
