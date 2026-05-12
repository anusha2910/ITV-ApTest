# Aptest - Online MCQ Test Platform

## Overview
Aptest is a full-stack MCQ (Multiple Choice Questions) test platform built with Python Flask. It provides an admin module for question management and a test-taker module for conducting timed assessments across various subjects like Aptitude, Logical Reasoning, English Grammar, and more.

## Current State
- Fully functional application with admin and test-taker modules
- Sample questions pre-loaded for all subjects
- SQLite database for data persistence

## Project Architecture

### Backend (Python Flask)
- `app.py` - Main application file with all routes, models, and business logic
- Uses Flask-SQLAlchemy for database ORM
- Werkzeug for secure password hashing
- SQLite database (`database.db`)

### Frontend
- Bootstrap 5 for responsive UI
- Vanilla JavaScript for interactivity
- Custom CSS in `static/css/style.css`

### Templates (Jinja2)
- `base.html` - Base template with navbar and footer
- `index.html` - Home page with test configuration
- `admin_login.html` - Admin authentication
- `admin_dashboard.html` - Question management dashboard
- `add_question.html` / `edit_question.html` - Question forms
- `upload_csv.html` - Bulk upload interface
- `take_test.html` - Test-taking interface
- `result.html` - Score display
- `review.html` - Answer review page

### Directory Structure
```
├── app.py
├── database.db (auto-generated)
├── templates/
├── static/
│   ├── css/style.css
│   └── sample_questions.csv
├── uploads/
└── README.md
```

## Key Features
1. **Admin Module**: CRUD operations for questions, CSV bulk upload
2. **Test Module**: Subject/difficulty selection, timed tests, auto-save
3. **Results Module**: Score calculation, answer review with highlighting

## Running the Application
```bash
python app.py
```
The app runs on port 5000.

## Default Credentials
- Admin: `admin` / `admin123`

## Recent Changes
- Initial project setup (January 2026)
- Created all templates and static files
- Added sample questions for 5 subjects
