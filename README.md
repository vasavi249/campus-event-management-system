# Campus Event Management System

A full-stack event management web application built with **Django**, **Django REST Framework (DRF)**, **HTML5/CSS3 (Glassmorphism UI)**, and **JavaScript**.

---

## 🌟 Key Features & Role Portals

- **Global Admin Panel (`/dashboard/admin/`)**:
  - Direct event creation with banner poster and certificate template uploads.
  - Category, venue, deadline, fee, and status management.
  - Live search & filter across all campus events.
  - Quick event banner updates and 1-click event deletion.

- **Faculty Panel (`/dashboard/faculty/`)**:
  - Department-scoped student attendance verification.
  - Approval/rejection workflow restricted strictly to faculty members belonging to the same department as the student (`student.department == faculty.department`).

- **Student Portal (`/dashboard/student/` & `/`)**:
  - Category-grouped event catalog with search filtering.
  - Paid/free event registration with unique ticket codes (`EVT-XXXXXX`).
  - Interactive Digital QR Passes for venue entry.
  - Visual certificate viewer with custom uploaded templates and 1-click PDF/Print export.

- **Organizer Console (`/dashboard/organizer/`)**:
  - Event proposal creation & participant tracking.
  - Real-time gate check-in terminal.

---

## 🔐 Default Demo Logins

| Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full System Control (`/dashboard/admin/` & `/admin/`) |
| **Faculty** | `faculty` | `faculty123` | CSE Department Attendance Approvals (`/dashboard/faculty/`) |
| **Organizer** | `organizer` | `organizer123` | Event Creation & Gate Check-in (`/dashboard/organizer/`) |
| **Student** | `student` | `student123` | Event Registration, Digital Pass & Certificates (`/dashboard/student/`) |

---

## 🚀 Quick Setup Guide (For New Clone / Deployment)

### 1. Clone Repository
```bash
git clone <your-repository-url>
cd "Event management system"
```

### 2. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Sample Data & Demo Accounts
```bash
python load_sample_data.py
```

### 6. Run Development Server
```bash
python manage.py runserver 8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

---

## 📋 Pre-Push & Pre-Deployment Checklist

Before executing `git push origin main`:

1. **Verify Unit Tests Pass**:
   ```bash
   python manage.py test events
   ```
2. **Collect Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```
3. **Seed Script Verification**:
   Make sure `load_sample_data.py` runs cleanly on fresh databases.
4. **Git Tracking Check**:
   Ensure temporary files (`.db`, `__pycache__`, virtualenv) are excluded via `.gitignore`.
