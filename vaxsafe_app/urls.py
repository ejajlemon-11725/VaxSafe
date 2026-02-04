# urls.py - Complete and Optimized with Centers and News
"""
URL configuration for VaxSafe project.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from vaxsafe import views

urlpatterns = [
    # =====================================================
    # ADMIN
    # =====================================================
    path('admin/', admin.site.urls, name='admin'),

    # =====================================================
    # PUBLIC PAGES
    # =====================================================
    path('', views.home, name='home'),
    path('features/', views.features, name='features'),
    path('aboutUs/', views.aboutUs, name='aboutUs'),
    path('contact/', views.contact, name='contact'),
    path("send-message/", views.send_message, name="send_message"),

    # =====================================================
    # AUTHENTICATION
    # =====================================================
    path('register/', views.register, name='register'),
    path("verify/", views.verify, name="verify"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout, name='logout'),
    path('verify-email/', views.verify_email, name='verify_email'),

    # =====================================================
    # DASHBOARD & PROFILE
    # =====================================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),

    # =====================================================
    # FAMILY MEMBERS MANAGEMENT
    # =====================================================
    path("familymembers/", views.familymembers, name="familymembers"),
    path("familymembers/add/", views.addfamilymember, name="addfamilymember"),
    path('familymembers/<int:member_id>/edit/', views.edit_family_member, name='edit_family_member'),
    path('familymembers/<int:member_id>/delete/', views.delete_family_member, name='delete_family_member'),

    # =====================================================
    # VACCINE MANAGEMENT
    # =====================================================
    path('vaccine/add/', views.add_vaccine, name='add_vaccine'),
    path('vaccine/schedule/', views.vaccine_schedule, name='vaccine_schedule'),
    path('vaccine/<int:vaccine_id>/', views.vaccine_detail, name='vaccine_detail'),
    path('vaccine/<int:vaccine_id>/edit/', views.edit_vaccine, name='edit_vaccine'),
    path('vaccine/<int:vaccine_id>/delete/', views.delete_vaccine, name='delete_vaccine'),
    path('vaccine/upcoming/', views.upcoming_vaccinations, name='upcoming_vaccinations'),
    path('vaccine/overdue/', views.overdue_vaccinations, name='overdue_vaccinations'),

    # =====================================================
    # REMINDERS
    # =====================================================
    path('reminders/', views.reminder, name='reminder'),
    path('reminders/add/', views.add_reminder, name='add_reminder'),
    path('reminders/edit/', views.edit_reminder, name='edit_reminder'),

    # =====================================================
    # VACCINATION CENTERS (UPDATED)
    # =====================================================
    path('centers/', views.centers, name='centers'),
    path('centers/<int:center_id>/', views.center_detail, name='center_detail'),

    # =====================================================
    # NEWS & UPDATES (NEW)
    # =====================================================
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
]

# =====================================================
# STATIC & MEDIA FILES (Development Only)
# =====================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# =====================================================
# URL REFERENCE GUIDE
# =====================================================
"""
QUICK URL REFERENCE:

Public Pages:
-------------
/                           → Home
/features/                  → Features
/aboutUs/                   → About Us
/contact/                   → Contact

Authentication:
--------------
/register/                  → User Registration
/verify/                    → OTP Verification
/login/                     → Login
/logout/                    → Logout

Dashboard:
----------
/dashboard/                 → Main Dashboard
/profile/                   → User Profile

Family Members:
--------------
/familymembers/             → List Family Members
/familymembers/add/         → Add Family Member
/familymembers/<id>/edit/   → Edit Family Member
/familymembers/<id>/delete/ → Delete Family Member

Vaccines:
--------
/vaccine/add/               → Add Vaccine
/vaccine/schedule/          → Vaccine Schedule
/vaccine/<id>/              → Vaccine Details
/vaccine/<id>/edit/         → Edit Vaccine
/vaccine/<id>/delete/       → Delete Vaccine
/vaccine/upcoming/          → Upcoming Vaccinations
/vaccine/overdue/           → Overdue Vaccinations

Reminders:
---------
/reminders/                 → List Reminders
/reminders/add/             → Add Reminder
/reminders/edit/            → Edit Reminders

Vaccination Centers:
-------------------
/centers/                   → List All Centers
/centers/<id>/              → Center Details

News & Updates:
--------------
/news/                      → All News Articles
/news/<slug>/               → News Article Detail

Admin:
------
/admin/                     → Django Admin
"""