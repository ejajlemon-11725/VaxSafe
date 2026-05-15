# VaxSafe

VaxSafe is a comprehensive Django-based web application designed to streamline immunization tracking, manage family health records, and improve public health coordination.

## Features

* **User & Profile Management:** Secure registration, login, account verification, and personalized profiles.
* **Family Health Tracking:** Easily add and monitor the vaccination status of multiple family members from a centralized dashboard.
* **Vaccine Scheduling & Reminders:** Log administered vaccines, view upcoming schedules, and receive timely notifications and reminders.
* **Center Locator:** Browse a directory of vaccination centers and view specific center details to coordinate visits.
* **News & Updates:** Stay informed with a dedicated news feed and specific vaccine updates relevant to public health guidelines.

## Technology Stack

* **Backend:** Python, Django framework
* **Database:** SQLite (`db.sqlite3` included for development)
* **Frontend:** HTML, CSS, and JavaScript (integrated via Django Templates)

## Project Structure

* `vaxsafe/`: The core application directory containing the data models, views, forms, and administrative configurations.
* `vaxsafe_app/`: The primary project configuration folder housing settings, ASGI/WSGI configurations, and main URL routing.
* `templates/htmlpages/`: The frontend interface containing all layout files (`base.html`, `nav.html`) and specific page views (e.g., `dashboard.html`, `vaccine_schedule.html`, `centers.html`).
* `media/` & `static/`: Directories for handling user-uploaded files and serving static assets like CSS, JavaScript, and images.

## Local Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd VaxSafe
    ```

2.  **Set up the virtual environment:**
    ```bash
    python -m venv .venv
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    *(Ensure you have a `requirements.txt` file, or install Django manually if not present)*
    ```bash
    pip install django
    # pip install -r requirements.txt
    ```

4.  **Apply database migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```
    Access the application at `http://127.0.0.1:8000/` in your browser.
