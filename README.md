# AquaAlert — beginner-friendly Flask project

AquaAlert is a **local educational prototype** for community symptom reporting, water-quality reporting, trend charts, and potential-risk alerts.

> Important: The app does not diagnose people or confirm disease outbreaks. Alerts are simple rules intended to help a trained human reviewer decide whether follow-up is needed. Use fictional data for demos. Do not enter real patient-identifying information.

## 1. What you need

- A laptop with VS Code
- Python 3.10 or newer
- Internet for the first-time Flask installation

## 2. Open the project

1. Extract `AquaAlert.zip`.
2. Open VS Code.
3. Choose **File → Open Folder** and select the `AquaAlert` folder.
4. Open **Terminal → New Terminal**.

## 3. Create a virtual environment

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, try Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install Flask

```bash
python -m pip install -r requirements.txt
```

## 5. Run AquaAlert

```bash
python app.py
```

Open this address in your browser:

http://127.0.0.1:5000

Keep the terminal open while you use the website. To stop it, press **Ctrl + C** in the terminal.

## 6. Admin login

- Open **Admin** in the navigation bar.
- Demo password: `AquaDemo123!`
- The admin can view reports, change alert statuses, and add fictional demo data.

For a local demonstration, this default is convenient. **Do not deploy the app publicly with the demo password.** Before any real deployment, set a strong `AQUAADMIN_PASSWORD` and `FLASK_SECRET_KEY` environment variable, use HTTPS, add proper user accounts and access controls, and arrange an appropriate privacy/security review.

### Set environment variables in PowerShell before running

```powershell
$env:AQUAADMIN_PASSWORD = "use-a-long-unique-password"
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-secret"
python app.py
```

These values apply to that terminal session. Choose your own secrets and never commit them to a public repository.

## 7. How to demonstrate it

1. Open **Admin → Login**.
2. Click **Add fictional demo data**.
3. Visit **Dashboard** and **Analytics** to see the sample reports.
4. Visit **Alerts** to see potential-risk flags.
5. Submit a symptom report at **Report symptoms**.
6. Submit a water report at **Water quality**.
7. Return to **Admin** and change an alert to Reviewed or Resolved.

Demo records are explicitly marked as fictional. The database file `aquaalert.db` is created automatically beside `app.py`.

## 8. How the project works

- **HTML templates** in `templates/` define each page.
- **CSS and JavaScript** in `static/` control the look and chart behaviour.
- **Flask (`app.py`)** handles page requests, checks form inputs, and runs the early-warning rules.
- **SQLite (`aquaalert.db`)** stores symptom reports, water reports, and alerts.
- **Chart.js** draws charts on the analytics page using a CDN, so charts need an internet connection.

### Early-warning rule in this prototype

The app flags a village when at least five symptom reports were entered for the last three days and that number is at least twice the expected count based on the previous seven days. It also flags an `Unsafe` water test entered within the previous 14 days.

This is a simple demonstration rule, **not a medically validated threshold**. Real public-health use would require domain-expert review, validated data, privacy safeguards, and official response procedures.

## 9. Troubleshooting

- **`python` is not recognized:** install Python from https://www.python.org/downloads/ and select “Add Python to PATH” during installation. Restart VS Code.
- **`No module named flask`:** activate `.venv`, then run `python -m pip install -r requirements.txt`.
- **PowerShell activation is blocked:** use the Command Prompt activation command above, or select Command Prompt as the VS Code terminal profile.
- **Port 5000 is already in use:** close the other app using it, or change the final line in `app.py` to `app.run(debug=True, port=5001)` and open `http://127.0.0.1:5001`.
- **Charts do not appear:** check your internet connection because Chart.js is loaded from a CDN.

## 10. Suggested improvements for a future version

- Individual staff accounts and role-based access
- CSV export for authorized officials
- More rigorous anomaly detection reviewed by public-health professionals
- Local language support and low-bandwidth/mobile-friendly design
- Automated notifications only after a safe, consent-based notification process is designed
