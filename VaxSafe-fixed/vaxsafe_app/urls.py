from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from vaxsafe import views

urlpatterns = [

    # ─────────────────────────────────────────
    # ADMIN
    # ─────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ─────────────────────────────────────────
    # PUBLIC PAGES
    # ─────────────────────────────────────────
    path('',              views.home,         name='home'),
    path('features/',     views.features,     name='features'),
    path('about/',        views.aboutUs,      name='about'),
    path('contact/',      views.contact,      name='contact'),
    path('contact/send/', views.send_message, name='send_message'),

    # ─────────────────────────────────────────
    # AUTHENTICATION
    # ─────────────────────────────────────────
    path('register/',    views.register,    name='register'),
    path('login/',       views.login_view,  name='login'),
    path('logout/',      views.logout,      name='logout'),
    path('verify-otp/',  views.verify_otp,  name='verify_otp'),
    path('resend-otp/',  views.resend_otp,  name='resend_otp'),

    # ─────────────────────────────────────────
    # DASHBOARD & PROFILE
    # ─────────────────────────────────────────
    path('dashboard/', views.dashboard,    name='dashboard'),
    path('profile/',   views.profile_view, name='profile'),

    # ─────────────────────────────────────────
    # FAMILY MEMBERS
    # ─────────────────────────────────────────
    path('family-members/',
         views.familymembers,        name='familymembers'),
    path('family-members/add/',
         views.addfamilymember,      name='addfamilymember'),
    path('family-members/edit/<int:member_id>/',
         views.edit_family_member,   name='edit_family_member'),
    path('family-members/delete/<int:member_id>/',
         views.delete_family_member, name='delete_family_member'),

    # ─────────────────────────────────────────
    # VACCINE HISTORY
    # ─────────────────────────────────────────
    path('vaccines/history/',
         views.vaccine_history,      name='vaccine_history_self'),
    path('vaccines/history/<int:member_id>/',
         views.vaccine_history,      name='vaccine_history'),

    # ─────────────────────────────────────────
    # VACCINES  (Admin Only for add/edit/delete)
    # ─────────────────────────────────────────
    path('vaccines/',
         views.vaccine_list,          name='vaccine_list'),
    path('vaccines/add/',
         views.add_vaccine,           name='add_vaccine'),
    path('vaccines/schedule/',
         views.vaccine_schedule,      name='vaccine_schedule'),
    path('vaccines/upcoming/',
         views.upcoming_vaccinations, name='upcoming_vaccinations'),
    path('vaccines/overdue/',
         views.overdue_vaccinations,  name='overdue_vaccinations.html'),
    path('vaccines/<int:vaccine_id>/',
         views.vaccine_detail,        name='vaccine_detail'),
    path('vaccines/<int:vaccine_id>/edit/',
         views.edit_vaccine,          name='edit_vaccine'),
    path('vaccines/<int:vaccine_id>/delete/',
         views.delete_vaccine,        name='delete_vaccine'),
    path('vaccines/<int:vaccine_id>/complete/',
         views.mark_vaccine_completed, name='mark_vaccine_completed'),

    # ─────────────────────────────────────────
    # ✅ নতুন: VACCINE REQUESTS (User → Admin)
    # ─────────────────────────────────────────
    path('vaccine-requests/submit/',
         views.submit_vaccine_request, name='submit_vaccine_request'),
    path('vaccine-requests/my/',
         views.my_vaccine_requests,    name='my_vaccine_requests'),

    # Admin Only
    path('vaccine-requests/admin/',
         views.admin_vaccine_requests,  name='admin_vaccine_requests'),
    path('vaccine-requests/<int:pk>/approve/',
         views.approve_vaccine_request, name='approve_vaccine_request'),
    path('vaccine-requests/<int:pk>/reject/',
         views.reject_vaccine_request,  name='reject_vaccine_request'),

    # ─────────────────────────────────────────
    # REMINDERS
    # ─────────────────────────────────────────
    path('reminders/add/',  views.add_reminder,  name='add_reminder'),
    path('reminders/edit/', views.edit_reminder, name='edit_reminder'),
    path('reminders/',
         views.reminder_list,    name='reminder_list'),
    path('reminders/set/',
         views.set_reminder,     name='set_reminder'),
    path('reminders/delete/<int:pk>/',
         views.delete_reminder,  name='delete_reminder'),

    # ─────────────────────────────────────────
    # NOTIFICATIONS
    # ─────────────────────────────────────────
    path('notifications/',
         views.notification_list,   name='notification_list'),
    path('notifications/delete/<int:pk>/',
         views.delete_notification, name='delete_notification'),

    # ─────────────────────────────────────────
    # VACCINATION CENTERS
    # ─────────────────────────────────────────
    path('centers/',
         views.centers,       name='centers'),
    path('centers/<int:center_id>/',
         views.center_detail, name='center_detail'),

    # ✅ নতুন (Task 1): AREA-BASED CENTERS
    path('area-centers/',
         views.area_centers,        name='area_centers'),
    path('area-centers/add/',
         views.add_area_center,     name='add_area_center'),
    path('area-centers/delete/<int:center_id>/',
         views.delete_area_center,  name='delete_area_center'),

    # ─────────────────────────────────────────
    # NEWS
    # ─────────────────────────────────────────
    path('news/',
         views.news_list,   name='news_list'),
    path('news/<slug:slug>/',
         views.news_detail, name='news_detail'),

    # ─────────────────────────────────────────
    # VACCINE UPDATES
    # ─────────────────────────────────────────
    path('vaccine-updates/',
         views.vaccine_updates,       name='vaccine_updates'),
    path('vaccine-updates/create/',
         views.create_vaccine_update, name='create_vaccine_update'),
    path('vaccine-updates/<int:pk>/',
         views.vaccine_update_detail, name='vaccine_update_detail'),
    path('vaccine-updates/<int:pk>/edit/',
         views.edit_vaccine_update,   name='edit_vaccine_update'),

    # ─────────────────────────────────────────
    # FAMILY GROUPS
    # ─────────────────────────────────────────
    path('family/create/',
         views.family_create_view,     name='family_create'),
    path('family/invite/',
         views.family_invite_view,     name='family_invite'),
    path('family/accept/<uuid:token>/',
         views.invitation_accept_view, name='invitation_accept'),
    path('family/transfer-admin/',
         views.admin_transfer_view,    name='admin_transfer'),
    path('family/leave/',
         views.leave_family_view,      name='leave_family'),
    path('family/switch/<int:pk>/',
         views.switch_family_view,     name='switch_family'),
    path('family/upgrade/<int:pk>/',
         views.dependent_upgrade_view, name='dependent_upgrade'),

    # ✅ নতুন (Task 3): PROFILE CLAIM/HANDOFF
    path('family/claimable-profiles/',
         views.claimable_profiles_view, name='claimable_profiles'),
    path('family/claim/<int:member_id>/',
         views.claim_profile_view,      name='claim_profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)