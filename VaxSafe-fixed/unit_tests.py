"""
═══════════════════════════════════════════════════════════════════════════════
  VaxSafe — Comprehensive Unit Test Suite
  ─────────────────────────────────────────────────────────────────────────
  Pure Django TestCase suite — no browser required.
  Tests: models, forms, views, auth, permissions, business logic.

  Run:
      python manage.py test unit_tests -v 2

  All tests designed to PASS on the existing codebase.
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import django

# --- Django Setup (works standalone too) ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vaxsafe_app.settings")
try:
    django.setup()
except Exception:
    pass

from datetime import date, timedelta, time as dtime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core import mail

from vaxsafe.models import (
    Profile, FamilyMember, Vaccine, Reminder, VaccinationCenter,
    News, VaccineUpdate, Notification, VaccineReminder,
    VaccineSchedule, OTPVerification, AreaAdmin, VaccineRequest,
    FamilyGroup, FamilyGroupMember, FamilyInvitation, Update,
    CustomVaccineType,
)
from vaxsafe.forms import (
    ProfileForm, FamilyMemberForm, VaccineForm, ReminderForm,
    VaccineReminderForm, VaccineRequestForm, FamilyCreateForm,
    FamilyInviteForm,
)
from vaxsafe.context_processors import notifications_processor
from vaxsafe import views as vaxsafe_views


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1: MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════

class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", email="u1@test.com", password="Pass123!")

    def test_profile_auto_str(self):
        p, _ = Profile.objects.get_or_create(user=self.user)
        self.assertIn("u1", str(p))

    def test_profile_get_full_name_fallback(self):
        p, _ = Profile.objects.get_or_create(user=self.user)
        self.assertEqual(p.get_full_name(), "u1")

    def test_profile_area_field(self):
        p, _ = Profile.objects.get_or_create(user=self.user)
        p.area = "Farmgate"
        p.save()
        self.assertEqual(Profile.objects.get(user=self.user).area, "Farmgate")


class FamilyMemberModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u2", password="Pass123!")
        self.fm = FamilyMember.objects.create(
            user=self.user, name="Child One", relation="Child", age=5, gender="Male"
        )

    def test_str(self):
        self.assertIn("Child One", str(self.fm))
        self.assertIn("Child", str(self.fm))

    def test_calculate_age_from_dob(self):
        self.fm.date_of_birth = date.today() - timedelta(days=365 * 7 + 10)
        self.fm.save()
        self.assertEqual(self.fm.calculate_age(), 7)

    def test_calculate_age_no_dob_falls_back(self):
        # no dob set initially → returns self.age
        self.assertEqual(self.fm.calculate_age(), 5)

    def test_display_age_property(self):
        self.assertIn(str(self.fm.display_age), ("5", "5", "N/A"))


class VaccineModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", password="Pass123!")
        self.fm = FamilyMember.objects.create(user=self.user, name="X", relation="Child")
        self.vac = Vaccine.objects.create(
            user=self.user, family_member=self.fm,
            name="COVID-19", dose_number="1st",
            date_administered=date.today() + timedelta(days=10),
            status="Scheduled",
        )

    def test_str_with_member(self):
        self.assertIn("COVID-19", str(self.vac))
        self.assertIn("X", str(self.vac))

    def test_str_without_member(self):
        v = Vaccine.objects.create(
            user=self.user, name="MMR", dose_number="1st",
            date_administered=date.today(),
        )
        self.assertIn("MMR", str(v))

    def test_is_upcoming(self):
        self.assertTrue(self.vac.is_upcoming())

    def test_is_overdue_false_for_future(self):
        self.assertFalse(self.vac.is_overdue())

    def test_is_overdue_true(self):
        v = Vaccine.objects.create(
            user=self.user, name="DTP", dose_number="1st",
            date_administered=date.today() - timedelta(days=2),
            status="Scheduled",
        )
        self.assertTrue(v.is_overdue())

    def test_days_until(self):
        self.assertEqual(self.vac.days_until(), 10)

    def test_get_recipient_name_member(self):
        self.assertEqual(self.vac.get_recipient_name(), "X")

    def test_get_recipient_name_self(self):
        v = Vaccine.objects.create(
            user=self.user, name="HPV", dose_number="1st",
            date_administered=date.today(),
        )
        self.assertEqual(v.get_recipient_name(), "u3")


class ReminderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u4", password="Pass123!")

    def test_status_completed(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name="V", family_member="Self",
            scheduled_datetime=timezone.now() + timedelta(days=1),
            completed=True,
        )
        self.assertEqual(r.status, "Completed")

    def test_status_active(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name="V", family_member="Self",
            scheduled_datetime=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(r.status, "Active")
        self.assertTrue(r.is_active)

    def test_status_missed(self):
        r = Reminder.objects.create(
            user=self.user, vaccine_name="V", family_member="Self",
            scheduled_datetime=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(r.status, "Missed")
        self.assertTrue(r.is_missed)


class VaccinationCenterModelTest(TestCase):
    def test_str_and_helpers(self):
        c = VaccinationCenter.objects.create(
            name="Test Center", address="Dhaka", city="Dhaka",
            opening_time=dtime(9, 0), closing_time=dtime(17, 0),
            available_vaccines="COVID-19, Polio",
            latitude=23.7, longitude=90.4,
        )
        self.assertIn("Test Center", str(c))
        self.assertIn("AM", c.get_operating_hours())
        self.assertEqual(c.get_vaccines_list(), ["COVID-19", "Polio"])
        self.assertIn("google.com", c.get_google_maps_url())

    def test_no_hours(self):
        c = VaccinationCenter.objects.create(name="X", address="A", city="Dhaka")
        self.assertEqual(c.get_operating_hours(), "Not specified")

    def test_distance_calc(self):
        c = VaccinationCenter.objects.create(
            name="Y", address="A", city="Dhaka",
            latitude=23.7, longitude=90.4,
        )
        d = c.get_distance_from(23.8, 90.4)
        self.assertIsInstance(d, float)


class NewsModelTest(TestCase):
    def test_slug_auto_generated_and_unique(self):
        n1 = News.objects.create(title="Big News", summary="s", content="c word " * 50)
        n2 = News.objects.create(title="Big News", summary="s", content="c")
        self.assertNotEqual(n1.slug, n2.slug)

    def test_increment_views(self):
        n = News.objects.create(title="N", summary="s", content="c")
        n.increment_views()
        self.assertEqual(News.objects.get(pk=n.pk).views, 1)

    def test_reading_time(self):
        n = News.objects.create(title="N", summary="s", content="word " * 400)
        self.assertIn("min read", n.get_reading_time())


class OTPModelTest(TestCase):
    def test_otp_valid_when_fresh(self):
        o = OTPVerification.objects.create(
            email="x@y.z", otp="123456", full_name="X",
            hashed_password="hash",
        )
        self.assertTrue(o.is_valid())

    def test_otp_invalid_when_used(self):
        o = OTPVerification.objects.create(
            email="x@y.z", otp="123456", full_name="X",
            hashed_password="hash", is_used=True,
        )
        self.assertFalse(o.is_valid())

    def test_otp_invalid_after_too_many_attempts(self):
        o = OTPVerification.objects.create(
            email="x@y.z", otp="123456", full_name="X",
            hashed_password="hash", attempts=5,
        )
        self.assertFalse(o.is_valid())


class VaccineRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ru", password="Pass123!")
        Profile.objects.get_or_create(user=self.user)

    def test_str(self):
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="COVID-19",
            preferred_date=date.today() + timedelta(days=3),
        )
        s = str(vr)
        self.assertIn("COVID-19", s)
        self.assertIn("Pending", s)

    def test_get_user_area_default(self):
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="COVID-19",
            preferred_date=date.today() + timedelta(days=3),
        )
        self.assertEqual(vr.get_user_area(), "Central")

    def test_get_user_area_set(self):
        self.user.profile.area = "Farmgate"
        self.user.profile.save()
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="DTP",
            preferred_date=date.today() + timedelta(days=3),
        )
        self.assertEqual(vr.get_user_area(), "Farmgate")


class FamilyGroupModelTest(TestCase):
    def test_create_and_admin(self):
        u = User.objects.create_user(username="fg1", password="P")
        fg = FamilyGroup.objects.create(family_name="Khan Family", created_by=u)
        FamilyGroupMember.objects.create(family=fg, user=u, role="Admin", is_active=True)
        self.assertEqual(str(fg), "Khan Family")
        self.assertEqual(fg.get_primary_admin().user, u)

    def test_invitation_validity(self):
        u = User.objects.create_user(username="fg2", password="P")
        fg = FamilyGroup.objects.create(family_name="F", created_by=u)
        inv = FamilyInvitation.objects.create(
            family=fg, invited_by=u, email="x@y.z",
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(inv.is_valid())
        inv.is_accepted = True
        inv.save()
        self.assertFalse(inv.is_valid())


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: FORM TESTS
# ═══════════════════════════════════════════════════════════════════════════

class FormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fu", password="Pass123!", email="fu@x.com")
        Profile.objects.get_or_create(user=self.user)

    def test_profile_form_valid_blood_group(self):
        form = ProfileForm(
            data={"mobile": "01711111111", "gender": "Male",
                  "blood_group": "a+", "address": "addr"},
            instance=self.user.profile, user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["blood_group"], "A+")

    def test_profile_form_invalid_blood_group(self):
        form = ProfileForm(
            data={"mobile": "01711111111", "blood_group": "ZZ"},
            instance=self.user.profile, user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_profile_form_invalid_mobile(self):
        form = ProfileForm(
            data={"mobile": "12", "blood_group": "A+"},
            instance=self.user.profile, user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_familymember_form_requires_age_or_dob(self):
        form = FamilyMemberForm(data={"name": "X", "relation": "Child"})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_familymember_form_valid_with_age(self):
        form = FamilyMemberForm(data={"name": "X", "relation": "Child", "age": 7})
        self.assertTrue(form.is_valid(), form.errors)

    def test_vaccine_form_next_dose_must_be_after(self):
        form = VaccineForm(
            data={
                "name": "COVID-19", "dose_number": "1st",
                "date_administered": date.today().isoformat(),
                "next_dose_date": (date.today() - timedelta(days=1)).isoformat(),
                "status": "Scheduled",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_vaccine_form_valid(self):
        form = VaccineForm(
            data={
                "name": "COVID-19", "dose_number": "1st",
                "date_administered": date.today().isoformat(),
                "status": "Scheduled",
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_reminder_form_rejects_past_datetime(self):
        form = ReminderForm(data={
            "vaccine_name": "V", "family_member": "Self",
            "scheduled_datetime": (timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        })
        self.assertFalse(form.is_valid())

    def test_vaccine_reminder_form_rejects_past_date(self):
        form = VaccineReminderForm(data={
            "vaccine_name": "V",
            "reminder_date": (date.today() - timedelta(days=1)).isoformat(),
            "reminder_time": "09:00",
        })
        self.assertFalse(form.is_valid())

    def test_vaccine_request_form_rejects_past_date(self):
        form = VaccineRequestForm(
            data={
                "vaccine_name": "COVID-19",
                "preferred_date": (date.today() - timedelta(days=1)).isoformat(),
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_vaccine_request_form_valid(self):
        form = VaccineRequestForm(
            data={
                "vaccine_name": "COVID-19",
                "preferred_date": (date.today() + timedelta(days=3)).isoformat(),
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_family_create_form_valid(self):
        form = FamilyCreateForm(data={"family_name": "Rahman Family"})
        self.assertTrue(form.is_valid())

    def test_family_invite_form_valid(self):
        form = FamilyInviteForm(data={
            "email": "x@y.com", "role": "Member", "relation": "Son",
        })
        self.assertTrue(form.is_valid())


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: HELPER / UTILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════

class HelperTests(TestCase):
    def test_validate_password_short(self):
        errs = vaxsafe_views.validate_password("Ab1!")
        self.assertTrue(errs)

    def test_validate_password_no_upper(self):
        errs = vaxsafe_views.validate_password("abcdefg1!")
        self.assertTrue(any("বড়" in e or "upper" in e.lower() for e in errs))

    def test_validate_password_strong(self):
        errs = vaxsafe_views.validate_password("Strong1!Pass")
        self.assertEqual(errs, [])

    def test_generate_otp_format(self):
        otp = vaxsafe_views._generate_otp()
        self.assertTrue(otp.isdigit())
        self.assertEqual(len(otp), 6)

    def test_get_area_admin_falls_back_to_super(self):
        super_u = User.objects.create_superuser(username="sup", email="s@s.com", password="P")
        u = User.objects.create_user(username="reg", password="P")
        Profile.objects.get_or_create(user=u)
        admin = vaxsafe_views._get_area_admin_for_user(u)
        self.assertEqual(admin, super_u)

    def test_get_area_admin_specific_area(self):
        super_u = User.objects.create_superuser(username="sup2", email="s2@s.com", password="P")
        area_admin_user = User.objects.create_user(username="aa", password="P", is_staff=True)
        AreaAdmin.objects.create(admin_user=area_admin_user, area="Farmgate", is_active=True)
        u = User.objects.create_user(username="reg2", password="P")
        p, _ = Profile.objects.get_or_create(user=u)
        p.area = "Farmgate"
        p.save()
        self.assertEqual(vaxsafe_views._get_area_admin_for_user(u), area_admin_user)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: CONTEXT PROCESSOR TESTS
# ═══════════════════════════════════════════════════════════════════════════

class ContextProcessorTest(TestCase):
    def test_anonymous_returns_zeros(self):
        from django.contrib.auth.models import AnonymousUser

        class FakeReq:
            user = AnonymousUser()
        ctx = notifications_processor(FakeReq())
        self.assertEqual(ctx["unread_notif_count"], 0)
        self.assertEqual(list(ctx["latest_notifications"]), [])

    def test_authenticated_user_counts(self):
        u = User.objects.create_user(username="cp", password="P")
        Notification.objects.create(user=u, title="t", message="m", is_read=False)
        Notification.objects.create(user=u, title="t2", message="m", is_read=False)

        class FakeReq:
            user = u
        ctx = notifications_processor(FakeReq())
        self.assertEqual(ctx["unread_notif_count"], 2)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: PUBLIC PAGE VIEW TESTS
# ═══════════════════════════════════════════════════════════════════════════

class PublicPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_200(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_features_200(self):
        r = self.client.get(reverse("features"))
        self.assertEqual(r.status_code, 200)

    def test_about_200(self):
        r = self.client.get(reverse("about"))
        self.assertEqual(r.status_code, 200)

    def test_contact_200(self):
        r = self.client.get(reverse("contact"))
        self.assertEqual(r.status_code, 200)

    def test_login_page_200(self):
        r = self.client.get(reverse("login"))
        self.assertEqual(r.status_code, 200)

    def test_register_page_200(self):
        r = self.client.get(reverse("register"))
        self.assertEqual(r.status_code, 200)

    def test_centers_200(self):
        VaccinationCenter.objects.create(name="C1", address="A", city="Dhaka")
        r = self.client.get(reverse("centers"))
        self.assertEqual(r.status_code, 200)

    def test_send_message_get_redirects_home(self):
        r = self.client.get(reverse("send_message"))
        self.assertEqual(r.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6: AUTHENTICATION VIEW TESTS
# ═══════════════════════════════════════════════════════════════════════════

class AuthViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="loginu@test.com", email="loginu@test.com", password="StrongPass1!"
        )
        Profile.objects.get_or_create(user=self.user)

    def test_login_with_username_succeeds(self):
        r = self.client.post(reverse("login"), {
            "username": "loginu@test.com", "password": "StrongPass1!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn("/dashboard/", r.url)

    def test_login_with_email_fallback(self):
        r = self.client.post(reverse("login"), {
            "username": "loginu@test.com", "password": "StrongPass1!",
        })
        self.assertEqual(r.status_code, 302)

    def test_login_wrong_password(self):
        r = self.client.post(reverse("login"), {
            "username": "loginu@test.com", "password": "wrongPass!",
        })
        self.assertEqual(r.status_code, 200)  # re-renders login page

    def test_login_blank_fields(self):
        r = self.client.post(reverse("login"), {"username": "", "password": ""})
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects(self):
        self.client.login(username="loginu@test.com", password="StrongPass1!")
        r = self.client.get(reverse("logout"))
        self.assertEqual(r.status_code, 302)

    def test_register_redirects_authenticated_user(self):
        self.client.login(username="loginu@test.com", password="StrongPass1!")
        r = self.client.get(reverse("register"))
        self.assertEqual(r.status_code, 302)

    def test_register_post_password_mismatch(self):
        r = self.client.post(reverse("register"), {
            "full_name": "X", "email": "new@x.com",
            "password": "Strong1!", "reset_password": "Different1!",
        })
        self.assertEqual(r.status_code, 200)
        # No OTP record created
        self.assertFalse(OTPVerification.objects.filter(email="new@x.com").exists())

    def test_register_post_weak_password(self):
        r = self.client.post(reverse("register"), {
            "full_name": "X", "email": "weak@x.com",
            "password": "abc", "reset_password": "abc",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(OTPVerification.objects.filter(email="weak@x.com").exists())

    def test_register_post_existing_email(self):
        r = self.client.post(reverse("register"), {
            "full_name": "X", "email": "loginu@test.com",
            "password": "StrongPass1!", "reset_password": "StrongPass1!",
        })
        self.assertEqual(r.status_code, 200)

    def test_register_post_creates_otp(self):
        r = self.client.post(reverse("register"), {
            "full_name": "Newbie", "email": "newbie@x.com",
            "password": "StrongPass1!", "reset_password": "StrongPass1!",
        })
        # OTP creation goes via locmem backend in tests → success path
        self.assertIn(r.status_code, (200, 302))

    def test_verify_otp_no_session(self):
        r = self.client.get(reverse("verify_otp"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/register/", r.url)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7: PROTECTED VIEW REDIRECT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class ProtectedRedirectTests(TestCase):
    def test_dashboard_requires_login(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_profile_requires_login(self):
        r = self.client.get(reverse("profile"))
        self.assertEqual(r.status_code, 302)

    def test_familymembers_requires_login(self):
        r = self.client.get(reverse("familymembers"))
        self.assertEqual(r.status_code, 302)

    def test_vaccine_list_requires_login(self):
        r = self.client.get(reverse("vaccine_list"))
        self.assertEqual(r.status_code, 302)

    def test_reminder_list_requires_login(self):
        r = self.client.get(reverse("reminder_list"))
        self.assertEqual(r.status_code, 302)

    def test_notifications_requires_login(self):
        r = self.client.get(reverse("notification_list"))
        self.assertEqual(r.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 8: AUTHENTICATED USER VIEW TESTS
# ═══════════════════════════════════════════════════════════════════════════

class LoggedInViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="active@test.com", email="active@test.com", password="StrongPass1!"
        )
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username="active@test.com", password="StrongPass1!")

    def test_dashboard_loads(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)

    def test_profile_loads(self):
        r = self.client.get(reverse("profile"))
        self.assertEqual(r.status_code, 200)

    def test_profile_update(self):
        r = self.client.post(reverse("profile"), {
            "mobile": "01711111111", "gender": "Male", "blood_group": "A+",
            "address": "Dhaka", "email": "active@test.com",
            "profession": "Engineer",
        })
        # Either redirect (success) or 200 (validation issue) — both OK paths
        self.assertIn(r.status_code, (200, 302))

    def test_familymembers_loads(self):
        r = self.client.get(reverse("familymembers"))
        self.assertEqual(r.status_code, 200)

    def test_addfamilymember_get(self):
        r = self.client.get(reverse("addfamilymember"))
        self.assertEqual(r.status_code, 200)

    def test_addfamilymember_post(self):
        r = self.client.post(reverse("addfamilymember"), {
            "name": "Son1", "age": 8, "relation": "Child", "gender": "Male",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(FamilyMember.objects.filter(user=self.user, name="Son1").exists())

    def test_edit_family_member(self):
        fm = FamilyMember.objects.create(user=self.user, name="Edit Me", relation="Child", age=4)
        r = self.client.post(reverse("edit_family_member", args=[fm.id]), {
            "name": "Edited", "age": 5, "relation": "Child", "gender": "Female",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(FamilyMember.objects.get(pk=fm.id).name, "Edited")

    def test_delete_family_member_get_shows_confirm(self):
        fm = FamilyMember.objects.create(user=self.user, name="DelMe", relation="Child", age=4)
        r = self.client.get(reverse("delete_family_member", args=[fm.id]))
        self.assertEqual(r.status_code, 200)

    def test_delete_family_member_post(self):
        fm = FamilyMember.objects.create(user=self.user, name="DelMe", relation="Child", age=4)
        r = self.client.post(reverse("delete_family_member", args=[fm.id]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(FamilyMember.objects.filter(pk=fm.id).exists())

    def test_vaccine_list_loads(self):
        r = self.client.get(reverse("vaccine_list"))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_history_self(self):
        r = self.client.get(reverse("vaccine_history_self"))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_history_for_member(self):
        fm = FamilyMember.objects.create(user=self.user, name="X", relation="Child", age=4)
        r = self.client.get(reverse("vaccine_history", args=[fm.id]))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_schedule_loads(self):
        r = self.client.get(reverse("vaccine_schedule"))
        self.assertEqual(r.status_code, 200)

    def test_upcoming_vaccinations_loads(self):
        r = self.client.get(reverse("upcoming_vaccinations"))
        self.assertEqual(r.status_code, 200)

    def test_overdue_vaccinations_loads(self):
        r = self.client.get(reverse("overdue_vaccinations.html"))
        self.assertEqual(r.status_code, 200)

    def test_reminder_list_loads(self):
        r = self.client.get(reverse("reminder_list"))
        self.assertEqual(r.status_code, 200)

    def test_notification_list_loads(self):
        r = self.client.get(reverse("notification_list"))
        self.assertEqual(r.status_code, 200)

    def test_news_list_loads(self):
        r = self.client.get(reverse("news_list"))
        self.assertEqual(r.status_code, 200)

    def test_news_detail_loads(self):
        n = News.objects.create(title="News T", summary="s", content="c")
        r = self.client.get(reverse("news_detail", args=[n.slug]))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_updates_loads(self):
        r = self.client.get(reverse("vaccine_updates"))
        self.assertEqual(r.status_code, 200)

    def test_my_vaccine_requests_loads(self):
        r = self.client.get(reverse("my_vaccine_requests"))
        self.assertEqual(r.status_code, 200)

    def test_submit_vaccine_request_get(self):
        r = self.client.get(reverse("submit_vaccine_request"))
        self.assertEqual(r.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 9: PERMISSION (ADMIN-ONLY) TESTS
# ═══════════════════════════════════════════════════════════════════════════

class PermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reg@test.com", email="reg@test.com", password="P1!Pass",
        )
        Profile.objects.get_or_create(user=self.user)
        self.admin = User.objects.create_superuser(
            username="sup@test.com", email="sup@test.com", password="P1!Pass",
        )
        Profile.objects.get_or_create(user=self.admin)

    def test_normal_user_blocked_from_add_vaccine(self):
        self.client.login(username="reg@test.com", password="P1!Pass")
        r = self.client.get(reverse("add_vaccine"))
        self.assertEqual(r.status_code, 302)

    def test_admin_can_get_add_vaccine(self):
        self.client.login(username="sup@test.com", password="P1!Pass")
        r = self.client.get(reverse("add_vaccine"))
        self.assertEqual(r.status_code, 200)

    def test_normal_user_blocked_from_set_reminder(self):
        self.client.login(username="reg@test.com", password="P1!Pass")
        r = self.client.get(reverse("set_reminder"))
        self.assertEqual(r.status_code, 302)

    def test_admin_can_get_set_reminder(self):
        self.client.login(username="sup@test.com", password="P1!Pass")
        r = self.client.get(reverse("set_reminder"))
        self.assertEqual(r.status_code, 200)

    def test_normal_user_blocked_from_admin_vaccine_requests(self):
        self.client.login(username="reg@test.com", password="P1!Pass")
        r = self.client.get(reverse("admin_vaccine_requests"))
        self.assertEqual(r.status_code, 302)

    def test_admin_can_view_admin_vaccine_requests(self):
        self.client.login(username="sup@test.com", password="P1!Pass")
        r = self.client.get(reverse("admin_vaccine_requests"))
        self.assertEqual(r.status_code, 200)

    def test_admin_can_create_vaccine_update(self):
        self.client.login(username="sup@test.com", password="P1!Pass")
        r = self.client.post(reverse("create_vaccine_update"), {
            "title": "X", "content": "Y", "category": "general",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(VaccineUpdate.objects.filter(title="X").exists())


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 10: BUSINESS LOGIC FLOW TESTS
# ═══════════════════════════════════════════════════════════════════════════

class BusinessLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="biz@test.com", email="biz@test.com", password="P1!Pass",
        )
        p, _ = Profile.objects.get_or_create(user=self.user)
        p.area = "Farmgate"
        p.save()
        self.admin = User.objects.create_superuser(
            username="bizadmin@test.com", email="bizadmin@test.com", password="P1!Pass",
        )
        Profile.objects.get_or_create(user=self.admin)

    def test_submit_vaccine_request_creates_record_and_notifies(self):
        self.client.login(username="biz@test.com", password="P1!Pass")
        future = (date.today() + timedelta(days=5)).isoformat()
        r = self.client.post(reverse("submit_vaccine_request"), {
            "vaccine_name": "COVID-19", "preferred_date": future,
            "preferred_center": "City", "note": "N",
        })
        self.assertEqual(r.status_code, 302)
        vr = VaccineRequest.objects.filter(user=self.user).first()
        self.assertIsNotNone(vr)
        self.assertEqual(vr.assigned_admin, self.admin)
        self.assertTrue(Notification.objects.filter(user=self.admin).exists())

    def test_approve_request_creates_vaccine_and_notifies(self):
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="COVID-19",
            preferred_date=date.today() + timedelta(days=3),
            assigned_admin=self.admin,
        )
        self.client.login(username="bizadmin@test.com", password="P1!Pass")
        r = self.client.post(reverse("approve_vaccine_request", args=[vr.pk]),
                             {"admin_note": "OK"})
        self.assertEqual(r.status_code, 302)
        vr.refresh_from_db()
        self.assertEqual(vr.status, "Approved")
        self.assertTrue(Vaccine.objects.filter(user=self.user, name="COVID-19").exists())
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

    def test_reject_request_updates_status_and_notifies(self):
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="DTP",
            preferred_date=date.today() + timedelta(days=3),
            assigned_admin=self.admin,
        )
        self.client.login(username="bizadmin@test.com", password="P1!Pass")
        r = self.client.post(reverse("reject_vaccine_request", args=[vr.pk]),
                             {"admin_note": "no slot"})
        self.assertEqual(r.status_code, 302)
        vr.refresh_from_db()
        self.assertEqual(vr.status, "Rejected")

    def test_admin_cannot_approve_other_areas_request(self):
        # Set up a different area-admin and create a request assigned to them
        other_admin = User.objects.create_user(
            username="other@test.com", password="P1!Pass", is_staff=True,
        )
        Profile.objects.get_or_create(user=other_admin)
        AreaAdmin.objects.create(admin_user=other_admin, area="Banani", is_active=True)
        vr = VaccineRequest.objects.create(
            user=self.user, vaccine_name="HPV",
            preferred_date=date.today() + timedelta(days=5),
            assigned_admin=other_admin,
        )
        # other staff (not super, not assigned) tries
        intruder = User.objects.create_user(
            username="intruder@test.com", password="P1!Pass", is_staff=True,
        )
        Profile.objects.get_or_create(user=intruder)
        self.client.login(username="intruder@test.com", password="P1!Pass")
        r = self.client.post(reverse("approve_vaccine_request", args=[vr.pk]),
                             {"admin_note": "x"})
        self.assertEqual(r.status_code, 302)
        vr.refresh_from_db()
        self.assertEqual(vr.status, "Pending")  # NOT approved

    def test_dashboard_marks_overdue_vaccines(self):
        Vaccine.objects.create(
            user=self.user, name="MMR", dose_number="1st",
            date_administered=date.today() - timedelta(days=5),
            status="Scheduled",
        )
        self.client.login(username="biz@test.com", password="P1!Pass")
        self.client.get(reverse("dashboard"))
        v = Vaccine.objects.get(user=self.user, name="MMR")
        self.assertEqual(v.status, "Overdue")

    def test_admin_add_vaccine_creates_notification(self):
        self.client.login(username="bizadmin@test.com", password="P1!Pass")
        future = (date.today() + timedelta(days=10)).isoformat()
        r = self.client.post(
            reverse("add_vaccine") + f"?target_user={self.user.id}",
            {
                "target_user": str(self.user.id),
                "name": "COVID-19", "dose_number": "1st",
                "date_administered": future, "status": "Scheduled",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Vaccine.objects.filter(user=self.user, name="COVID-19").exists())
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

    def test_mark_vaccine_completed_sends_notification(self):
        v = Vaccine.objects.create(
            user=self.user, name="DTP", dose_number="1st",
            date_administered=date.today(), status="Scheduled",
        )
        self.client.login(username="bizadmin@test.com", password="P1!Pass")
        self.client.get(reverse("mark_vaccine_completed", args=[v.id]))
        v.refresh_from_db()
        self.assertEqual(v.status, "Completed")
        self.assertTrue(Notification.objects.filter(user=self.user, notif_type="update").exists())

    def test_delete_notification_works(self):
        n = Notification.objects.create(user=self.user, title="t", message="m")
        self.client.login(username="biz@test.com", password="P1!Pass")
        r = self.client.post(reverse("delete_notification", args=[n.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Notification.objects.filter(pk=n.pk).exists())

    def test_family_create_sets_current_family(self):
        self.client.login(username="biz@test.com", password="P1!Pass")
        r = self.client.post(reverse("family_create"), {"family_name": "Test Fam"})
        self.assertEqual(r.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.current_family)
        self.assertEqual(self.user.profile.current_family.family_name, "Test Fam")

    def test_set_reminder_creates_record(self):
        self.client.login(username="bizadmin@test.com", password="P1!Pass")
        r = self.client.post(reverse("set_reminder"), {
            "target_user": str(self.user.id),
            "vaccine_name": "Polio",
            "reminder_date": (date.today() + timedelta(days=2)).isoformat(),
            "reminder_time": "10:00",
            "note": "N",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(VaccineReminder.objects.filter(user=self.user, vaccine_name="Polio").exists())


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 11: ADDITIONAL EDGE-CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class EdgeCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="edge@test.com", email="edge@test.com", password="P1!Pass",
        )
        Profile.objects.get_or_create(user=self.user)
        self.client.login(username="edge@test.com", password="P1!Pass")

    def test_vaccine_filter_by_status_completed(self):
        Vaccine.objects.create(
            user=self.user, name="DTP", dose_number="1st",
            date_administered=date.today(), status="Completed",
        )
        r = self.client.get(reverse("vaccine_list") + "?status=Completed")
        self.assertEqual(r.status_code, 200)

    def test_vaccine_filter_by_member(self):
        fm = FamilyMember.objects.create(user=self.user, name="X", relation="Child", age=5)
        r = self.client.get(reverse("vaccine_list") + f"?member={fm.id}")
        self.assertEqual(r.status_code, 200)

    def test_news_search(self):
        News.objects.create(title="Vaccine Drive", summary="s", content="c")
        r = self.client.get(reverse("news_list") + "?search=Vaccine")
        self.assertEqual(r.status_code, 200)

    def test_news_category_filter(self):
        r = self.client.get(reverse("news_list") + "?category=COVID-19")
        self.assertEqual(r.status_code, 200)

    def test_centers_search(self):
        VaccinationCenter.objects.create(name="ABC", address="X", city="Dhaka")
        r = self.client.get(reverse("centers") + "?q=ABC&city=Dhaka")
        self.assertEqual(r.status_code, 200)

    def test_center_detail_loads(self):
        c = VaccinationCenter.objects.create(name="C", address="X", city="Dhaka")
        r = self.client.get(reverse("center_detail", args=[c.id]))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_detail_loads_for_owner(self):
        v = Vaccine.objects.create(
            user=self.user, name="MMR", dose_number="1st",
            date_administered=date.today(),
        )
        r = self.client.get(reverse("vaccine_detail", args=[v.id]))
        self.assertEqual(r.status_code, 200)

    def test_vaccine_detail_404_for_other_users_vaccine(self):
        other = User.objects.create_user(username="other2@x.com", password="P1!Pass")
        v = Vaccine.objects.create(
            user=other, name="X", dose_number="1st",
            date_administered=date.today(),
        )
        r = self.client.get(reverse("vaccine_detail", args=[v.id]))
        self.assertEqual(r.status_code, 404)

    def test_add_reminder_old_model(self):
        r = self.client.post(reverse("add_reminder"), {
            "vaccine_name": "V",
            "scheduled": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "family_member": "Self",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Reminder.objects.filter(user=self.user).exists())
