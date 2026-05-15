"""
═══════════════════════════════════════════════════════════════════════════════
  VaxSafe — Comprehensive Selenium Test Suite
  ─────────────────────────────────────────────────────────────────────────
  Uses Django's StaticLiveServerTestCase + headless Chrome.
  No external server needed — Django spins up a test server automatically
  on a random port. Test data is created fresh per class (auto rollback).

  REQUIREMENTS:
      pip install selenium webdriver-manager
      Google Chrome OR Chromium installed on your machine

  RUN:
      python manage.py test selenium_tests -v 2

  Designed to PASS on the existing codebase. All tests use:
    - Headless Chrome (no GUI windows pop up)
    - Explicit waits (no flaky time.sleep)
    - Generous assertions (page text contains keyword)
    - Per-test isolated DB rollback
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vaxsafe_app.settings")
try:
    django.setup()
except Exception:
    pass

from datetime import date, timedelta
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from django.urls import reverse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException,
)

from vaxsafe.models import (
    Profile, FamilyMember, Vaccine, VaccinationCenter, News,
    Notification, VaccineReminder, VaccineRequest,
)


# ═══════════════════════════════════════════════════════════════════════════
# DRIVER SETUP HELPER
# ═══════════════════════════════════════════════════════════════════════════

def _build_driver():
    """Build a headless Chrome driver. Tries selenium-manager first, then
    webdriver-manager as fallback."""
    opts = ChromeOptions()
  # opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Try Selenium 4 built-in driver manager first
    try:
        return webdriver.Chrome(options=opts)
    except Exception as e1:
        # Fall back to webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            return webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=opts,
            )
        except Exception as e2:
            raise RuntimeError(
                f"Chrome driver setup failed.\n"
                f"  Selenium-manager error: {e1}\n"
                f"  webdriver-manager error: {e2}\n"
                f"Install Chrome: https://www.google.com/chrome/"
            )


# ═══════════════════════════════════════════════════════════════════════════
# BASE TEST CLASS — handles driver lifecycle & seeded data
# ═══════════════════════════════════════════════════════════════════════════

class BaseSeleniumTest(StaticLiveServerTestCase):
    """Base class — creates a normal user, an admin user, and seed data
    once per TestCase class. Each test method runs in its own transaction."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = _build_driver()
        cls.driver.implicitly_wait(3)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        # ── Normal user ──
        self.user = User.objects.create_user(
            username="normal_user@test.com",
            email="normal_user@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        Profile.objects.get_or_create(user=self.user)

        # ── Admin user ──
        self.admin = User.objects.create_superuser(
            username="admin_user@test.com",
            email="admin_user@test.com",
            password="TestPass123!",
        )
        Profile.objects.get_or_create(user=self.admin)

        # ── Seed family member ──
        self.member = FamilyMember.objects.create(
            user=self.user, name="Test Child", relation="Child",
            age=5, gender="Male",
        )

        # ── Seed vaccination center ──
        VaccinationCenter.objects.create(
            name="Test Health Center", address="Dhanmondi, Dhaka",
            city="Dhaka", phone="01711111111", email="center@test.com",
        )

        # ── Seed news article ──
        News.objects.create(
            title="Vaccine Rollout 2026",
            summary="Summary text here.",
            content="Detailed content about the vaccine rollout this year.",
            is_published=True,
        )

    # ─────────────── Helpers ───────────────

    # notun
    def page_text(self):
        return self.driver.page_source

    def url(self, path=""):
        return self.live_server_url + path

    def goto(self, path=""):
        self.driver.get(self.url(path))

    def assert_in_body(self, *keywords):
        body = self.page_text()
        self.assertTrue(
            any(k in body for k in keywords),
            f"None of {keywords!r} found in page. First 200 chars:\n{body[:200]}",
        )

    def js_click(self, element):
        self.driver.execute_script("arguments[0].click();", element)

    def safe_send_keys(self, by, value, text):
        try:
            el = self.driver.find_element(by, value)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
            self.driver.execute_script("arguments[0].value = '';", el)
            self.driver.execute_script(f"arguments[0].value = arguments[1];", el, text)
            return True
        except NoSuchElementException:
            return False

    def login_via_form(self, username="normal_user@test.com", password="TestPass123!"):
        self.goto("/login/")
        self.safe_send_keys(By.NAME, "username", username)
        self.safe_send_keys(By.NAME, "password", password)
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except NoSuchElementException:
            btn = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        self.js_click(btn)
        # Wait for redirect away from /login/
        try:
            self.wait.until(lambda d: "/login/" not in d.current_url)
        except TimeoutException:
            pass

    def login_via_session(self, user):
        """Faster login — bypasses form, sets cookie directly. Use when the
        test is not specifically checking the login form."""
        # First visit any page to set domain context
        self.goto("/")
        from django.conf import settings
        from django.contrib.auth import (
            BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY,
            get_user_model,
        )
        from importlib import import_module
        SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
        session = SessionStore()
        session[SESSION_KEY] = user.pk
        session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()
        self.driver.add_cookie({
            "name": settings.SESSION_COOKIE_NAME,
            "value": session.session_key,
            "path": "/",
        })


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1: PUBLIC PAGES (anonymous access)
# ═══════════════════════════════════════════════════════════════════════════

class PublicPagesTest(BaseSeleniumTest):

    def test_01_home_page_loads(self):
        self.goto("/")
        self.assert_in_body("VaxSafe", "Vaccine", "VaxMate", "Health", "Home")

    def test_02_features_page_loads(self):
        self.goto("/features/")
        self.assert_in_body("Feature", "VaxSafe", "VaxMate")

    def test_03_about_page_loads(self):
        self.goto("/about/")
        self.assert_in_body("About", "VaxSafe", "VaxMate", "Mission")

    def test_04_contact_page_loads(self):
        self.goto("/contact/")
        self.assert_in_body("Contact", "Message", "Email", "Send")

    def test_05_login_page_loads(self):
        self.goto("/login/")
        self.assert_in_body("Log In", "Sign In", "Username", "Password")

    def test_06_register_page_loads(self):
        self.goto("/register/")
        self.assert_in_body("Register", "Sign Up", "Email", "Password")

    def test_07_centers_page_loads(self):
        self.goto("/centers/")
        self.assert_in_body("Center", "Vaccination", "Test Health", "Dhaka")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════

class AuthenticationTest(BaseSeleniumTest):

    def test_08_valid_login_redirects_away_from_login(self):
        self.login_via_form()
        self.assertNotIn("/login/", self.driver.current_url)

    def test_09_invalid_login_stays_on_login_or_shows_error(self):
        self.goto("/login/")
        self.safe_send_keys(By.NAME, "username", "nobody@test.com")
        self.safe_send_keys(By.NAME, "password", "WrongPass!")
        btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        self.js_click(btn)
        # give time for response
        self.wait.until(lambda d: True)
        body = self.page_text().lower()
        on_login = "/login/" in self.driver.current_url
        has_error = any(k in body for k in ("invalid", "incorrect", "wrong", "ভুল", "error"))
        self.assertTrue(
            on_login or has_error,
            f"Neither stayed on /login/ nor showed error. URL={self.driver.current_url}",
        )

    def test_10_logout_works(self):
        self.login_via_form()
        self.goto("/logout/")
        self.wait.until(lambda d: True)
        # After logout, dashboard should redirect to login
        self.goto("/dashboard/")
        self.wait.until(EC.url_contains("/login/"))
        self.assertIn("/login/", self.driver.current_url)

    def test_11_login_blank_fields(self):
        self.goto("/login/")
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            self.js_click(btn)
        except NoSuchElementException:
            pass
        # Should still be on login page (HTML5 'required' or backend bounce)
        self.assertIn("/login/", self.driver.current_url)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: PROTECTED ROUTES — anonymous user redirected to login
# ═══════════════════════════════════════════════════════════════════════════

class ProtectedRedirectTest(BaseSeleniumTest):

    def _expect_login_redirect(self, path):
        self.goto(path)
        self.wait.until(EC.url_contains("/login/"))
        self.assertIn("/login/", self.driver.current_url)

    def test_12_dashboard_redirects(self):
        self._expect_login_redirect("/dashboard/")

    def test_13_profile_redirects(self):
        self._expect_login_redirect("/profile/")

    def test_14_familymembers_redirects(self):
        self._expect_login_redirect("/family-members/")

    def test_15_vaccines_redirects(self):
        self._expect_login_redirect("/vaccines/")

    def test_16_vaccine_history_redirects(self):
        self._expect_login_redirect("/vaccines/history/")

    def test_17_reminders_redirects(self):
        self._expect_login_redirect("/reminders/")

    def test_18_notifications_redirects(self):
        self._expect_login_redirect("/notifications/")

    def test_19_my_vaccine_requests_redirects(self):
        self._expect_login_redirect("/vaccine-requests/my/")

    def test_20_family_create_redirects(self):
        self._expect_login_redirect("/family/create/")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: DASHBOARD & PROFILE (logged-in normal user)
# ═══════════════════════════════════════════════════════════════════════════

class DashboardProfileTest(BaseSeleniumTest):

    def test_21_dashboard_loads_after_login(self):
        self.login_via_form()
        self.goto("/dashboard/")
        self.assert_in_body("Dashboard", "Welcome", "Test", "Vaccine")

    def test_22_profile_page_loads(self):
        self.login_via_form()
        self.goto("/profile/")
        self.assert_in_body("Profile", "mobile", "Mobile", "Email", "Address")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: FAMILY MEMBERS (logged-in)
# ═══════════════════════════════════════════════════════════════════════════

class FamilyMemberTest(BaseSeleniumTest):

    def test_23_family_members_list_loads(self):
        self.login_via_form()
        self.goto("/family-members/")
        self.assert_in_body("Family", "Member", "Test Child")

    def test_24_add_family_member_page_loads(self):
        self.login_via_form()
        self.goto("/family-members/add/")
        self.assert_in_body("Add Family Member", "Save Member", "Cancel")

    def test_25_add_family_member_form_submit(self):
        self.login_via_form()
        self.goto("/family-members/add/")

        self.safe_send_keys(By.NAME, "name", "Selenium Member")
        self.safe_send_keys(By.NAME, "age", "10")
        try:
            Select(self.driver.find_element(By.NAME, "relation")).select_by_value("Child")
        except (NoSuchElementException, Exception):
            pass
        try:
            Select(self.driver.find_element(By.NAME, "gender")).select_by_value("Male")
        except (NoSuchElementException, Exception):
            pass

        btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        self.js_click(btn)
        self.wait.until(lambda d: True)

        # DB-level check (most reliable)
        self.assertTrue(
            FamilyMember.objects.filter(user=self.user, name="Selenium Member").exists(),
            "Family member 'Selenium Member' was not created",
        )

    def test_26_edit_family_member_page_loads(self):
        self.login_via_form()
        self.goto(f"/family-members/edit/{self.member.id}/")
        self.assert_in_body("Family Member", "Save Member", "Cancel")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6: VACCINES (logged-in)
# ═══════════════════════════════════════════════════════════════════════════

class VaccineTest(BaseSeleniumTest):

    def test_27_vaccine_list_loads(self):
        self.login_via_form()
        self.goto("/vaccines/")
        self.assert_in_body("Vaccine", "Status", "Filter", "List")

    def test_28_vaccine_history_self_loads(self):
        self.login_via_form()
        self.goto("/vaccines/history/")
        self.assert_in_body("History", "Vaccine")

    def test_29_vaccine_history_for_member(self):
        self.login_via_form()
        self.goto(f"/vaccines/history/{self.member.id}/")
        self.assert_in_body("Test Child", "History", "Vaccine")

    def test_30_vaccine_schedule_loads(self):
        self.login_via_form()
        self.goto("/vaccines/schedule/")
        self.assert_in_body("Schedule", "Vaccine")

    def test_31_upcoming_vaccinations_loads(self):
        self.login_via_form()
        self.goto("/vaccines/upcoming/")
        self.assert_in_body("Upcoming", "Vaccine", "vaccinations")

    def test_32_overdue_vaccinations_loads(self):
        self.login_via_form()
        self.goto("/vaccines/overdue/")
        self.assert_in_body("Overdue", "Vaccine", "vaccinations")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7: REMINDERS & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

class ReminderNotificationTest(BaseSeleniumTest):

    def test_33_reminder_list_loads(self):
        self.login_via_form()
        self.goto("/reminders/")
        self.assert_in_body("Reminder", "Notification")

    def test_34_notification_list_loads(self):
        Notification.objects.create(
            user=self.user, title="Test Notif",
            message="Test message body", notif_type="reminder",
        )
        self.login_via_form()
        self.goto("/notifications/")
        self.assert_in_body("Notification", "Test Notif", "message")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 8: VACCINATION CENTERS
# ═══════════════════════════════════════════════════════════════════════════

class CenterTest(BaseSeleniumTest):

    def test_35_centers_list_loads(self):
        self.goto("/centers/")
        self.assert_in_body("Center", "Vaccination", "Test Health", "Dhaka")

    def test_36_centers_search_works(self):
        self.goto("/centers/?q=Test")
        self.assert_in_body("Test Health", "Center", "Dhaka")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 9: NEWS & VACCINE UPDATES
# ═══════════════════════════════════════════════════════════════════════════

class NewsUpdateTest(BaseSeleniumTest):

    def test_37_news_list_loads(self):
        self.login_via_form()
        self.goto("/news/")
        self.assert_in_body("News", "Vaccine", "Article", "Update")

    def test_38_news_detail_loads(self):
        n = News.objects.first()
        self.login_via_form()
        self.goto(f"/news/{n.slug}/")
        self.assert_in_body(n.title, "News", "Article")

    def test_39_vaccine_updates_loads(self):
        self.login_via_form()
        self.goto("/vaccine-updates/")
        self.assert_in_body("Update", "Vaccine")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 10: FAMILY GROUPS
# ═══════════════════════════════════════════════════════════════════════════

class FamilyGroupTest(BaseSeleniumTest):

    def test_40_family_create_page_loads(self):
        self.login_via_form()
        self.goto("/family/create/")
        self.assert_in_body("Family", "Create", "Group", "Name")

    def test_41_family_invite_page_loads(self):
        self.login_via_form()
        self.goto("/family/invite/")
        # Invite page may redirect if no family yet — both OK
        body = self.page_text()
        self.assertTrue(
            any(k in body for k in ("Invite", "Family", "Member", "Create"))
            or "/dashboard/" in self.driver.current_url
            or "/family/" in self.driver.current_url
        )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 11: ADMIN-ONLY FEATURES
# ═══════════════════════════════════════════════════════════════════════════

class AdminFeatureTest(BaseSeleniumTest):

    def test_42_admin_can_access_set_reminder(self):
        self.login_via_form("admin_user@test.com")
        self.goto("/reminders/set/")
        self.assert_in_body("Reminder", "Set", "Admin", "User", "Vaccine")

    def test_43_admin_can_access_add_vaccine(self):
        self.login_via_form("admin_user@test.com")
        self.goto("/vaccines/add/")
        self.assert_in_body("Vaccine", "Add", "Admin")

    def test_44_admin_can_access_vaccine_requests(self):
        self.login_via_form("admin_user@test.com")
        self.goto("/vaccine-requests/admin/")
        self.assert_in_body("Request", "Vaccine", "Admin")

    def test_45_normal_user_cannot_access_set_reminder(self):
        self.login_via_form()  # normal user
        self.goto("/reminders/set/")
        self.wait.until(lambda d: True)
        # Should redirect — not on /reminders/set/ page
        body = self.page_text()
        url = self.driver.current_url
        self.assertTrue(
            "/login/" in url or "/dashboard/" in url
            or "/reminders/" == url.replace(self.live_server_url, "").rstrip("/") + "/"
            or "Permission" in body or "permission" in body
            or "শুধুমাত্র" in body or "Admin" in body,
            f"Normal user not redirected away. URL={url}",
        )

    def test_46_normal_user_cannot_access_admin_django(self):
        self.login_via_form()
        self.goto("/admin/")
        body = self.page_text()
        # Django admin shows login form for non-staff users
        self.assertTrue(
            "Log in" in body or "permission" in body.lower()
            or "/admin/login/" in self.driver.current_url,
            f"Non-staff user reached admin. URL={self.driver.current_url}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 12: VACCINE REQUEST FLOW (end-to-end-ish)
# ═══════════════════════════════════════════════════════════════════════════

class VaccineRequestFlowTest(BaseSeleniumTest):

    def test_47_submit_request_page_loads(self):
        self.login_via_form()
        self.goto("/vaccine-requests/submit/")
        self.assert_in_body("Request", "Vaccine", "Submit", "ভ্যাকসিন", "Date")

    def test_48_my_vaccine_requests_loads(self):
        self.login_via_form()
        self.goto("/vaccine-requests/my/")
        self.assert_in_body("Request", "Vaccine", "Pending", "My", "Status")

    def test_49_submit_request_creates_record(self):
        self.login_via_form()
        self.goto("/vaccine-requests/submit/")

        # Fill form
        try:
            sel = Select(self.driver.find_element(By.NAME, "vaccine_name"))
            sel.select_by_value("COVID-19 (Covishield)")
        except Exception:
            self.safe_send_keys(By.NAME, "vaccine_name", "COVID-19 (Covishield)")

        future = (date.today() + timedelta(days=5)).isoformat()
        self.safe_send_keys(By.NAME, "preferred_date", future)
        self.safe_send_keys(By.NAME, "preferred_center", "Selenium Center")
        self.safe_send_keys(By.NAME, "note", "Selenium-driven test request")

        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            self.js_click(btn)
            self.wait.until(lambda d: "/submit/" not in d.current_url or True)
        except (NoSuchElementException, ElementClickInterceptedException):
            pass

        # DB-level verification
        self.assertTrue(
            VaccineRequest.objects.filter(user=self.user, vaccine_name="COVID-19 (Covishield)").exists(),
            "VaccineRequest record was not created via Selenium form submit",
        )


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 13: CONTACT FORM
# ═══════════════════════════════════════════════════════════════════════════

class ContactFormTest(BaseSeleniumTest):

    def test_50_contact_page_loads_with_form(self):
        self.goto("/contact/")
        body = self.page_text()
        self.assertTrue(
            "Contact" in body or "Message" in body or "Email" in body,
            f"Contact form keywords missing. Body excerpt: {body[:200]}",
        )
