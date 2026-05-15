import re
import json
import random
import time
from datetime import timedelta
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Count, Q

from .models import (
    Profile, FamilyMember, FamilyGroupMember, FamilyGroup,
    FamilyInvitation, Reminder, Update, Vaccine,
    VaccinationCenter, News, VaccineUpdate,
    Notification, VaccineReminder, VaccineSchedule, OTPVerification,
    # ✅ FIXED: এই দুটো import যোগ করা হয়েছে
    VaccineRequest, AreaAdmin,
)
from .forms import (
    ProfileForm, FamilyMemberForm, VaccineForm,
    FamilyCreateForm, FamilyInviteForm, AdminTransferForm,
    VaccineReminderForm,
    VaccineApplicationForm,
    # ✅ FIXED: VaccineRequestForm import যোগ করা হয়েছে
    VaccineRequestForm,
)

# =====================================================
# 🔔 NOTIFICATION HELPER FUNCTIONS
# =====================================================

def _send_vaccine_scheduled_notification(vaccine, target_user):
    recipient_name = vaccine.get_recipient_name()
    title = f"💉 {vaccine.name} — {vaccine.dose_number} নির্ধারিত"
    msg_lines = [
        f"Admin আপনার / আপনার পরিবারের সদস্য ({recipient_name}) এর জন্য",
        f"{vaccine.name} ({vaccine.dose_number}) টিকা",
        f"📅 তারিখ: {vaccine.date_administered.strftime('%d %B %Y')}",
    ]
    if vaccine.next_dose_date:
        msg_lines.append(f"📌 পরবর্তী ডোজ: {vaccine.next_dose_date.strftime('%d %B %Y')}")
    if vaccine.location:
        msg_lines.append(f"📍 স্থান: {vaccine.location}")
    if vaccine.healthcare_provider:
        msg_lines.append(f"👨‍⚕️ স্বাস্থ্যকর্মী: {vaccine.healthcare_provider}")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='reminder')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — {vaccine.name} টিকা নির্ধারিত",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe Vaccination Management",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (vaccine scheduled): {e}")


def _send_vaccine_completed_notification(vaccine):
    target_user    = vaccine.user
    recipient_name = vaccine.get_recipient_name()
    title = f"✅ {vaccine.name} — {vaccine.dose_number} সম্পন্ন!"
    msg_lines = [
        f"অভিনন্দন! {recipient_name} এর {vaccine.name} ({vaccine.dose_number})",
        "টিকা সফলভাবে সম্পন্ন হয়েছে।",
    ]
    if vaccine.next_dose_date:
        msg_lines += [
            "",
            f"📅 পরবর্তী ডোজের তারিখ: {vaccine.next_dose_date.strftime('%d %B %Y')}",
            "অনুগ্রহ করে এই তারিখে টিকা নিতে ভুলবেন না।",
        ]
    else:
        msg_lines.append("\n🎉 এটি এই টিকার সর্বশেষ ডোজ ছিল।")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='update')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — {vaccine.name} {vaccine.dose_number} সম্পন্ন",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (vaccine completed): {e}")


def _send_reminder_notification(vr, target_user):
    recipient = vr.get_recipient_name()
    title = f"⏰ রিমাইন্ডার: {vr.vaccine_name}"
    msg_lines = [
        f"Admin '{recipient}' এর জন্য '{vr.vaccine_name}' টিকার রিমাইন্ডার সেট করেছেন।",
        f"📅 তারিখ: {vr.reminder_date.strftime('%d %B %Y')}",
        f"⏰ সময়: {vr.reminder_time.strftime('%I:%M %p')}",
    ]
    if vr.note:
        msg_lines.append(f"📝 নোট: {vr.note}")
    full_msg = "\n".join(msg_lines)
    Notification.objects.create(user=target_user, title=title, message=full_msg, notif_type='reminder')
    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — রিমাইন্ডার: {vr.vaccine_name} ({recipient})",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Email error (reminder): {e}")


# =====================================================
# ✅ নতুন (Task 2): AUTO-SCHEDULE NEXT DOSE HELPER
# =====================================================

# একই vaccine এর dose order — পরের dose কোনটা সেটা বের করতে
_DOSE_ORDER = ['1st', '2nd', '3rd', 'Booster']

def _get_next_dose_label(current_dose):
    """'1st' → '2nd', '2nd' → '3rd', '3rd' → 'Booster', বাকি সব → None"""
    try:
        idx = _DOSE_ORDER.index(current_dose)
        if idx + 1 < len(_DOSE_ORDER):
            return _DOSE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def _auto_schedule_next_dose(vaccine):
    """
    প্রথম/আগের dose-টা সেভ হলে এই function call হবে।
    VaccineSchedule lookup করে interval_days বের করবে, next_dose_date set করবে,
    এবং পরের dose-এর জন্য একটা নতুন Scheduled Vaccine record তৈরি করবে।

    Return: (next_vaccine_obj | None, message_str)
    """
    # Single Dose / Booster শেষ → আর কিছু লাগবে না
    if vaccine.dose_number in ('Single',):
        return None, "Single Dose — no next dose."

    next_dose_label = _get_next_dose_label(vaccine.dose_number)
    if not next_dose_label:
        return None, "এটি শেষ ডোজ — পরের কোনো ডোজ নেই।"

    # VaccineSchedule থেকে interval বের করো (current dose এর interval = এই dose এর পর কতদিন)
    interval_days = None
    schedule_obj  = None
    try:
        schedule_obj = VaccineSchedule.objects.get(
            vaccine_name=vaccine.name,
            dose_number=vaccine.dose_number,
            is_active=True,
        )
        interval_days = schedule_obj.interval_days
    except VaccineSchedule.DoesNotExist:
        # ডিফল্ট fallback: কিছু common vaccines এর জন্য
        DEFAULTS = {
            'COVID-19':    {'1st': 28, '2nd': 180, '3rd': 365},
            'Hepatitis B': {'1st': 30, '2nd': 150, '3rd': 0},
            'Polio':       {'1st': 60, '2nd': 60,  '3rd': 0},
            'DTP':         {'1st': 60, '2nd': 60,  '3rd': 0},
            'MMR':         {'1st': 90, '2nd': 0},
            'HPV':         {'1st': 60, '2nd': 120},
            'Hepatitis A': {'1st': 180},
            'Influenza':   {'1st': 365},
        }
        interval_days = DEFAULTS.get(vaccine.name, {}).get(vaccine.dose_number, 30)

    if not interval_days or interval_days <= 0:
        return None, "এই ডোজের পর কোনো interval সেট নেই।"

    # next_dose_date যদি আগে থেকে না থাকে, তাহলে calculate করো
    if not vaccine.next_dose_date:
        vaccine.next_dose_date = vaccine.date_administered + timedelta(days=interval_days)
        vaccine.save(update_fields=['next_dose_date'])

    # ডুপ্লিকেট check — একই date এ একই vaccine + dose আগে থেকেই থাকলে আর তৈরি করব না
    existing = Vaccine.objects.filter(
        user=vaccine.user,
        family_member=vaccine.family_member,
        name=vaccine.name,
        dose_number=next_dose_label,
        date_administered=vaccine.next_dose_date,
    ).first()
    if existing:
        return existing, "পরের ডোজ আগে থেকেই scheduled আছে।"

    # নতুন next dose record তৈরি করো
    next_vaccine = Vaccine.objects.create(
        user                = vaccine.user,
        family_member       = vaccine.family_member,
        name                = vaccine.name,
        dose_number         = next_dose_label,
        date_administered   = vaccine.next_dose_date,
        location            = vaccine.location or '',
        healthcare_provider = vaccine.healthcare_provider or '',
        status              = 'Scheduled',
        notes               = (
            f"✨ Auto-scheduled. {vaccine.dose_number} dose ({vaccine.date_administered}) "
            f"এর {interval_days} দিন পর।"
        ),
    )

    return next_vaccine, f"✅ পরের ডোজ ({next_dose_label}) auto-schedule হয়েছে {vaccine.next_dose_date} এ।"


def _send_next_dose_auto_notification(prev_vaccine, next_vaccine, target_user):
    """Next dose auto-schedule হলে user কে notification পাঠাও।"""
    recipient = next_vaccine.get_recipient_name()
    title = f"🔔 পরের ডোজ Auto-Scheduled: {next_vaccine.name} ({next_vaccine.dose_number})"
    msg_lines = [
        f"আপনার / {recipient} এর '{next_vaccine.name}' টিকার পরের ডোজ",
        f"স্বয়ংক্রিয়ভাবে নির্ধারণ করা হয়েছে।",
        "",
        f"💉 ডোজ: {next_vaccine.dose_number}",
        f"📅 তারিখ: {next_vaccine.date_administered.strftime('%d %B %Y')}",
        f"📋 আগের ডোজ: {prev_vaccine.dose_number} — {prev_vaccine.date_administered.strftime('%d %B %Y')}",
    ]
    if next_vaccine.location:
        msg_lines.append(f"📍 স্থান: {next_vaccine.location}")
    msg_lines.append("")
    msg_lines.append("ℹ️ Admin চাইলে এই তারিখ পরিবর্তন করতে পারবেন।")
    full_msg = "\n".join(msg_lines)

    Notification.objects.create(
        user=target_user,
        title=title,
        message=full_msg,
        notif_type='reminder',
    )

    if target_user.email:
        try:
            send_mail(
                subject=f"VaxSafe — পরের ডোজ Auto-Schedule: {next_vaccine.name}",
                message=f"{title}\n\n{full_msg}\n\n---\nVaxSafe Auto Scheduling",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"[VaxSafe] Auto-schedule email error: {e}")


# =====================================================
# HELPER: সব user এর family members → JSON
# =====================================================

def _build_user_family_json(all_users):
    data = {}
    for u in all_users:
        members = FamilyMember.objects.filter(user=u).order_by('name')
        data[str(u.id)] = [
            {'id': m.id, 'name': f"{m.name} ({m.relation})"}
            for m in members
        ]
    return json.dumps(data)


# =====================================================
# AUTHENTICATION
# =====================================================

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Password কমপক্ষে ৮ character হতে হবে।")
    if not re.search(r'[A-Z]', password):
        errors.append("কমপক্ষে একটি বড় হাতের অক্ষর (A-Z) দিতে হবে।")
    if not re.search(r'[a-z]', password):
        errors.append("কমপক্ষে একটি ছোট হাতের অক্ষর (a-z) দিতে হবে।")
    if not re.search(r'[0-9]', password):
        errors.append("কমপক্ষে একটি সংখ্যা (0-9) দিতে হবে।")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>@]', password):
        errors.append("কমপক্ষে একটি special character (!@#$% ইত্যাদি) দিতে হবে।")
    return errors


def _generate_otp():
    return str(random.randint(100000, 999999))


def _send_otp_email(email, otp, full_name):
    subject = "VaxSafe — আপনার OTP কোড"
    body = f"""
HELLO {full_name},

আপনার VaxSafe Registration OTP কোড:

    ━━━━━━━━━━━━━━
         {otp}
    ━━━━━━━━━━━━━━

এই কোডটি ১০ মিনিটের মধ্যে ব্যবহার করুন।
কেউ যদি এই কোড চায় তাকে দেবেন না।

— VaxSafe Team
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[VaxSafe] OTP email error: {e}")
        return False


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        full_name        = request.POST.get("full_name", "").strip()
        email            = request.POST.get("email", "").strip().lower()
        password         = request.POST.get("password", "")
        confirm_password = request.POST.get("reset_password", "")

        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "সব তথ্য পূরণ করতে হবে।")
            return render(request, "htmlpages/register.html")

        if password != confirm_password:
            messages.error(request, "দুটো Password মিলছে না।")
            return render(request, "htmlpages/register.html")

        pw_errors = validate_password(password)
        if pw_errors:
            for err in pw_errors:
                messages.error(request, err)
            return render(request, "htmlpages/register.html")

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            messages.error(request, "এই Email দিয়ে আগেই account তৈরি আছে।")
            return render(request, "htmlpages/register.html")

        OTPVerification.objects.filter(email=email, is_used=False).delete()

        otp = _generate_otp()

        from django.contrib.auth.hashers import make_password
        otpobj = OTPVerification.objects.create(
            email           = email,
            otp             = otp,
            full_name       = full_name,
            hashed_password = make_password(password),
        )

        sent = _send_otp_email(email, otp, full_name)
        if not sent:
            messages.error(request, "❌ Email পাঠাতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
            otpobj.delete()
            return render(request, "htmlpages/register.html")

        request.session['pending_otp_email'] = email

        messages.success(request, f"✅ {email} এ একটি OTP পাঠানো হয়েছে। ১০ মিনিটের মধ্যে verify করুন।")
        return redirect('verify_otp')

    return render(request, "htmlpages/register.html")


def verify_otp(request):
    email = request.session.get('pending_otp_email')
    if not email:
        messages.error(request, "Session expired। আবার register করুন।")
        return redirect('register')

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        try:
            otpobj = OTPVerification.objects.filter(
                email=email, is_used=False
            ).latest('created_at')
        except OTPVerification.DoesNotExist:
            messages.error(request, "❌ OTP পাওয়া যায়নি। আবার register করুন।")
            return redirect('register')

        if not otpobj.is_valid():
            messages.error(request, "❌ OTP মেয়াদ শেষ হয়ে গেছে। আবার register করুন।")
            otpobj.delete()
            return redirect('register')

        if otpobj.otp != entered_otp:
            otpobj.attempts += 1
            otpobj.save()
            remaining = 5 - otpobj.attempts
            if remaining <= 0:
                otpobj.delete()
                messages.error(request, "❌ অনেকবার ভুল OTP দিয়েছেন। আবার register করুন।")
                return redirect('register')
            messages.error(request, f"❌ OTP ভুল হয়েছে। আরও {remaining} বার সুযোগ আছে।")
            return render(request, "htmlpages/verify.html", {'email': email})

        try:
            user = User(
                username   = email,
                email      = email,
                first_name = otpobj.full_name,
            )
            user.password = otpobj.hashed_password
            user.save()

            Profile.objects.get_or_create(user=user)

            otpobj.is_used = True
            otpobj.save()

            if 'pending_otp_email' in request.session:
                del request.session['pending_otp_email']

            auth_login(request, user)
            messages.success(request, f"✅ স্বাগতম {otpobj.full_name}! Account সফলভাবে তৈরি হয়েছে।")
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, "Account তৈরিতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
            print(f"[VaxSafe] Account creation error: {e}")
            return render(request, "htmlpages/verify.html", {'email': email})

    return render(request, "htmlpages/verify.html", {'email': email})


def resend_otp(request):
    email = request.session.get('pending_otp_email')
    if not email:
        messages.error(request, "Session expired। আবার register করুন।")
        return redirect('register')

    try:
        otpobj = OTPVerification.objects.filter(
            email=email, is_used=False
        ).latest('created_at')
    except OTPVerification.DoesNotExist:
        messages.error(request, "OTP পাওয়া যায়নি। আবার register করুন।")
        return redirect('register')

    new_otp = _generate_otp()
    otpobj.otp        = new_otp
    otpobj.attempts   = 0
    otpobj.created_at = timezone.now()
    otpobj.save()

    sent = _send_otp_email(email, new_otp, otpobj.full_name)
    if sent:
        messages.success(request, f"✅ নতুন OTP {email} এ পাঠানো হয়েছে।")
    else:
        messages.error(request, "❌ Email পাঠাতে সমস্যা। একটু পর আবার চেষ্টা করুন।")

    return redirect('verify_otp')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if not username or not password:
            messages.error(request, "Username এবং Password দুটোই দিতে হবে।")
            return render(request, "htmlpages/login.html")
        user = authenticate(request, username=username, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"✅ স্বাগতম, {user.first_name or user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "❌ Username/Email অথবা Password ভুল হয়েছে।")
    return render(request, "htmlpages/login.html")


def logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("home")


# =====================================================
# PUBLIC PAGES
# =====================================================

def home(request):
    return render(request, "htmlpages/home.html")

def features(request):
    return render(request, "htmlpages/features.html")

def aboutUs(request):
    return render(request, "htmlpages/aboutUs.html")

def contact(request):
    return render(request, "htmlpages/contact.html")

def send_message(request):
    if request.method == 'POST':
        name    = request.POST.get('name', '')
        email   = request.POST.get('email', '')
        message = request.POST.get('message', '')
        if name and email and message:
            try:
                send_mail(
                    subject=f"New Message from {name}",
                    message=f"From: {name} ({email})\n\n{message}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, "Thank you for contacting us!")
            except Exception as e:
                messages.error(request, "Failed to send message.")
                print(f"Email error: {e}")
        else:
            messages.error(request, "Please fill in all fields.")
        return redirect('contact')
    return redirect('home')

def verify_email(request):
    return render(request, "htmlpages/verifyemail.html")


# =====================================================
# DASHBOARD
# =====================================================

@login_required(login_url='login')
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__lt=today
    ).update(status='Overdue')
    updates           = Update.objects.all().order_by("-created_at")[:5]
    total_vaccines    = Vaccine.objects.filter(user=request.user).count()
    upcoming_vaccines = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).order_by('date_administered')
    overdue_count     = Vaccine.objects.filter(user=request.user, status='Overdue').count()
    active_reminders_count = VaccineReminder.objects.filter(
        user=request.user, is_sent=False, reminder_date__gte=today,
    ).count()
    family_members_count = FamilyMember.objects.filter(user=request.user).count()
    current_family = profile.current_family
    current_member = None
    group_members  = []
    user_families  = request.user.family_memberships.filter(is_active=True).select_related('family')
    if current_family:
        current_member = FamilyGroupMember.objects.filter(family=current_family, user=request.user).first()
        group_members  = FamilyGroupMember.objects.filter(family=current_family, is_active=True)

    # ✅ নতুন (Task 3): Claimable Profile count
    claimable_count = 0
    if current_family:
        family_user_ids = list(FamilyGroupMember.objects.filter(
            family=current_family
        ).values_list('user_id', flat=True))
        claimable_count = FamilyMember.objects.filter(
            is_active=False,
            previous_caretaker__id__in=family_user_ids,
        ).exclude(user=request.user).count()

    # ✅ pending vaccine requests count (for user banner)
    pending_requests_count = VaccineRequest.objects.filter(
        user=request.user, status='Pending'
    ).count()

    # ✅ area admin check + pending count
    is_area_admin      = False
    area_pending_count = 0
    if request.user.is_staff or request.user.is_superuser:
        if request.user.is_superuser:
            is_area_admin      = True
            area_pending_count = VaccineRequest.objects.filter(status='Pending').count()
        else:
            try:
                AreaAdmin.objects.get(admin_user=request.user, is_active=True)
                is_area_admin      = True
                area_pending_count = VaccineRequest.objects.filter(
                    assigned_admin=request.user, status='Pending'
                ).count()
            except AreaAdmin.DoesNotExist:
                pass

    context = {
        'updates':                updates,
        'family_members_count':   family_members_count,
        'total_vaccines':         total_vaccines,
        'upcoming_vaccines':      upcoming_vaccines[:3],
        'upcoming_count':         upcoming_vaccines.count(),
        'overdue_count':          overdue_count,
        'reminders_active':       active_reminders_count > 0,
        'active_reminders_count': active_reminders_count,
        'current_family':         current_family,
        'current_user_role':      current_member.role if current_member else None,
        'family_members':         group_members,
        'user_families':          user_families,
        'claimable_count':        claimable_count,
        'pending_requests_count': pending_requests_count,
        'is_area_admin':          is_area_admin,
        'area_pending_count':     area_pending_count,
    }
    return render(request, "htmlpages/dashboard.html", context)


# =====================================================
# PROFILE
# =====================================================

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'delete_photo' in request.POST:
            if profile.photo:
                profile.photo.delete(save=True)
            messages.success(request, "✅ Profile photo deleted!")
            return redirect('profile')

        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()

            new_email = form.cleaned_data.get('email', '').strip()
            if new_email and new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    messages.error(request, "❌ এই Email অন্য কেউ ব্যবহার করছে।")
                    return render(request, 'htmlpages/profile.html', {
                        'form': form, 'profile': profile, 'title': 'My Profile'
                    })
                request.user.email = new_email
                request.user.save(update_fields=['email'])

            messages.success(request, "✅ Profile updated!")
            return redirect('profile')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, 'htmlpages/profile.html', {
        'form': form, 'profile': profile, 'title': 'My Profile'
    })


# =====================================================
# FAMILY MEMBERS
# =====================================================

@login_required
def familymembers(request):
    members = FamilyMember.objects.filter(user=request.user).annotate(vaccine_count=Count('vaccines')).order_by('name')
    return render(request, "htmlpages/familymembers.html", {
        'members': members, 'total_members': members.count(), 'title': 'Family Members'
    })


@login_required
def addfamilymember(request):
    if request.method == "POST":
        form = FamilyMemberForm(request.POST)
        if form.is_valid():
            fm = form.save(commit=False)
            fm.user = request.user
            fm.save()
            messages.success(request, f"✅ {fm.name} added!")
            return redirect("familymembers")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = FamilyMemberForm()
    return render(request, "htmlpages/addfamilymember.html", {'form': form, 'title': 'Add Family Member'})


@login_required
def edit_family_member(request, member_id):
    fm = get_object_or_404(FamilyMember, id=member_id, user=request.user)
    if request.method == 'POST':
        form = FamilyMemberForm(request.POST, instance=fm)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ {fm.name} updated!')
            return redirect('familymembers')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = FamilyMemberForm(instance=fm)
    return render(request, 'htmlpages/addfamilymember.html', {
        'form': form, 'family_member': fm, 'title': 'Edit Family Member', 'is_edit': True
    })


@login_required
def delete_family_member(request, member_id):
    fm = get_object_or_404(FamilyMember, id=member_id, user=request.user)
    if request.method == 'POST':
        name = fm.name
        fm.delete()
        messages.success(request, f'🗑️ {name} removed!')
        return redirect('familymembers')
    return render(request, 'htmlpages/delete_family_member_confirm.html', {
        'family_member': fm, 'vaccine_count': fm.vaccines.count()
    })


# =====================================================
# VACCINE MANAGEMENT  (Admin Only)
# =====================================================

@login_required
def add_vaccine(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ টিকার রেকর্ড যোগ/সম্পাদনা করার অনুমতি নেই। শুধুমাত্র Admin এই কাজ করতে পারবেন।")
        return redirect('vaccine_schedule')

    all_users                = User.objects.all().order_by('first_name', 'username')
    user_family_members_json = _build_user_family_json(all_users)

    target_user        = request.user
    get_target_user_id = request.GET.get('target_user', '').strip()

    if get_target_user_id and get_target_user_id != 'all':
        try:
            target_user = User.objects.get(id=int(get_target_user_id))
        except (User.DoesNotExist, ValueError):
            target_user = request.user
            get_target_user_id = ''

    if request.method == 'POST':
        target_user_id = request.POST.get('target_user', '').strip()

        if target_user_id == 'all':
            form = VaccineForm(request.POST, user=request.user)
            if form.is_valid():
                active_users = User.objects.filter(is_active=True)
                count = 0
                auto_chain_count = 0
                for tu in active_users:
                    v = Vaccine(
                        user                = tu,
                        family_member       = None,
                        name                = form.cleaned_data['name'],
                        dose_number         = form.cleaned_data['dose_number'],
                        date_administered   = form.cleaned_data['date_administered'],
                        next_dose_date      = form.cleaned_data.get('next_dose_date'),
                        location            = form.cleaned_data.get('location') or '',
                        healthcare_provider = form.cleaned_data.get('healthcare_provider') or '',
                        status              = form.cleaned_data.get('status', 'Scheduled'),
                        notes               = form.cleaned_data.get('notes') or '',
                        manufacturer        = form.cleaned_data.get('manufacturer') or '',
                        batch_number        = form.cleaned_data.get('batch_number') or '',
                        side_effects        = form.cleaned_data.get('side_effects') or '',
                    )
                    v.save()
                    _send_vaccine_scheduled_notification(v, tu)
                    count += 1

                    # ✅ নতুন (Task 2): প্রত্যেক user এর জন্য auto-schedule
                    next_v, _ = _auto_schedule_next_dose(v)
                    if next_v and next_v.pk != v.pk:
                        _send_next_dose_auto_notification(v, next_v, tu)
                        auto_chain_count += 1

                msg = (
                    f'✅ মোট {count} জন user এর জন্য "{form.cleaned_data["name"]}" '
                    f'({form.cleaned_data["dose_number"]}) সেট করা হয়েছে। '
                    f'সবাইকে App Notification ও Email পাঠানো হয়েছে।'
                )
                if auto_chain_count:
                    msg += f' 🔔 {auto_chain_count} জনের পরের ডোজ auto-schedule হয়েছে।'
                messages.success(request, msg)
                return redirect('vaccine_schedule')
            else:
                messages.error(request, '❌ Please correct the errors below.')
                return render(request, 'htmlpages/addvaccine.html', {
                    'form': form, 'title': 'টিকার রেকর্ড যোগ করুন (Admin)',
                    'is_admin': True, 'all_users': all_users,
                    'target_user': request.user,
                    'selected_target_user_id': 'all',
                    'user_family_members_json': user_family_members_json,
                })

        if target_user_id:
            try:
                target_user = User.objects.get(id=int(target_user_id))
            except (User.DoesNotExist, ValueError):
                target_user = request.user

        admin_family_member_id = request.POST.get('admin_family_member_id', '').strip()
        selected_family_member = None
        if admin_family_member_id:
            try:
                selected_family_member = FamilyMember.objects.get(
                    id=admin_family_member_id, user=target_user
                )
            except FamilyMember.DoesNotExist:
                selected_family_member = None

        form = VaccineForm(request.POST, user=target_user)
        if form.is_valid():
            v      = form.save(commit=False)
            v.user = target_user
            if selected_family_member:
                v.family_member = selected_family_member
            v.save()
            _send_vaccine_scheduled_notification(v, target_user)

            # ✅ নতুন (Task 2): Auto-schedule পরের ডোজ
            next_vaccine, auto_msg = _auto_schedule_next_dose(v)
            if next_vaccine and next_vaccine.pk != v.pk:
                _send_next_dose_auto_notification(v, next_vaccine, target_user)

            recipient_label = (
                selected_family_member.name
                if selected_family_member
                else (target_user.get_full_name() or target_user.username)
            )
            success_msg = (
                f'✅ "{recipient_label}" এর জন্য "{v.name}" ({v.dose_number}) সেট করা হয়েছে। '
                f'App Notification ও Email পাঠানো হয়েছে।'
            )
            if next_vaccine and next_vaccine.pk != v.pk:
                success_msg += (
                    f' 🔔 পরের ডোজ ({next_vaccine.dose_number}) '
                    f'{next_vaccine.date_administered.strftime("%d %B %Y")} '
                    f'এ auto-schedule হয়েছে।'
                )
            messages.success(request, success_msg)
            return redirect('vaccine_schedule')
        else:
            messages.error(request, '❌ Please correct the errors below.')

    else:
        form = VaccineForm(user=target_user)
        if get_target_user_id and get_target_user_id != 'all':
            form.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=target_user
            )

    return render(request, 'htmlpages/addvaccine.html', {
        'form':                     form,
        'title':                    'টিকার রেকর্ড যোগ করুন (Admin)',
        'is_admin':                 True,
        'all_users':                all_users,
        'target_user':              target_user,
        'selected_target_user_id':  get_target_user_id,
        'user_family_members_json': user_family_members_json,
    })


@login_required
def edit_vaccine(request, vaccine_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin টিকা সম্পাদনা করতে পারবেন।")
        return redirect('vaccine_schedule')
    vaccine    = get_object_or_404(Vaccine, id=vaccine_id)
    old_status = vaccine.status
    form       = VaccineForm(request.POST or None, instance=vaccine, user=vaccine.user)
    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        if old_status != 'Completed' and updated.status == 'Completed':
            _send_vaccine_completed_notification(updated)
            messages.success(request, f'✅ "{updated.name}" Completed করা হয়েছে। User কে Notification ও Email পাঠানো হয়েছে।')
        else:
            messages.success(request, f'✅ Vaccine "{updated.name}" updated!')
        return redirect('vaccine_schedule')
    elif request.method == 'POST':
        messages.error(request, '❌ Please correct the errors below.')
    return render(request, 'htmlpages/addvaccine.html', {
        'form': form, 'vaccine': vaccine, 'title': 'Edit Vaccine (Admin)', 'is_edit': True, 'is_admin': True,
    })


@login_required
def mark_vaccine_completed(request, vaccine_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ Permission denied.")
        return redirect('vaccine_schedule')
    vaccine = get_object_or_404(Vaccine, id=vaccine_id)
    if vaccine.status != 'Completed':
        vaccine.status = 'Completed'
        vaccine.save()
        _send_vaccine_completed_notification(vaccine)

        # ✅ নতুন (Task 2): Completed হলে পরের ডোজ auto-schedule
        next_v, auto_msg = _auto_schedule_next_dose(vaccine)
        extra = ""
        if next_v and next_v.pk != vaccine.pk:
            _send_next_dose_auto_notification(vaccine, next_v, vaccine.user)
            extra = (
                f" 🔔 পরের ডোজ ({next_v.dose_number}) "
                f"{next_v.date_administered.strftime('%d %B %Y')} এ auto-schedule হয়েছে।"
            )

        messages.success(
            request,
            f"✅ {vaccine.name} ({vaccine.dose_number}) Completed করা হয়েছে। "
            f"User কে App Notification ও Email পাঠানো হয়েছে।{extra}"
        )
    else:
        messages.info(request, "এটি ইতিমধ্যে Completed।")
    return redirect('vaccine_schedule')


@login_required
def delete_vaccine(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    if request.method == 'POST':
        name = vaccine.name
        vaccine.delete()
        messages.success(request, f'🗑️ "{name}" deleted!')
        return redirect('vaccine_schedule')
    return render(request, 'htmlpages/delete_vaccine_confirm.html', {'vaccine': vaccine, 'title': 'Delete Vaccine'})


@login_required
def vaccine_detail(request, vaccine_id):
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)
    return render(request, 'htmlpages/vaccine_detail.html', {
        'vaccine': vaccine, 'is_upcoming': vaccine.is_upcoming(), 'is_overdue': vaccine.is_overdue(),
        'days_until': vaccine.days_until() if vaccine.is_upcoming() else None, 'title': f'{vaccine.name} Details',
    })


@login_required
def upcoming_vaccinations(request):
    today    = timezone.now().date()
    upcoming = Vaccine.objects.filter(
        user=request.user, status='Scheduled', date_administered__gte=today
    ).select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/upcoming_vaccinations.html', {
        'vaccinations': upcoming, 'count': upcoming.count(), 'title': 'Upcoming Vaccinations'
    })


@login_required
def overdue_vaccinations(request):
    today = timezone.now().date()
    Vaccine.objects.filter(user=request.user, status='Scheduled', date_administered__lt=today).update(status='Overdue')
    overdue = Vaccine.objects.filter(user=request.user, status='Overdue').select_related('family_member').order_by('date_administered')
    return render(request, 'htmlpages/overdue_vaccinations.html', {
        'vaccinations': overdue, 'count': overdue.count(), 'title': 'Overdue Vaccinations'
    })


@login_required
def vaccine_list(request):
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')
    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')
    if member_filter:
        vaccines = vaccines.filter(family_member_id=member_filter)
    if status_filter:
        vaccines = vaccines.filter(status=status_filter)
    return render(request, 'htmlpages/vaccine_list.html', {
        'vaccines': vaccines, 'family_members': FamilyMember.objects.filter(user=request.user),
        'status_choices': Vaccine.STATUS_CHOICES, 'vaccine_types': Vaccine.VACCINE_TYPES,
        'selected_member': member_filter, 'selected_status': status_filter, 'title': 'Vaccine List',
    })


# =====================================================
# VACCINE HISTORY
# =====================================================

@login_required
def vaccine_history(request, member_id=None):
    if member_id:
        member          = get_object_or_404(FamilyMember, id=member_id, user=request.user)
        vaccines        = Vaccine.objects.filter(family_member=member).order_by('-date_administered')
        member_name     = member.name
        member_relation = member.relation
    else:
        vaccines        = Vaccine.objects.filter(user=request.user, family_member__isnull=True).order_by('-date_administered')
        member_name     = request.user.get_full_name() or request.user.username
        member_relation = "Self"
    total     = vaccines.count()
    completed = vaccines.filter(status='Completed').count()
    scheduled = vaccines.filter(status='Scheduled').count()
    overdue   = vaccines.filter(status='Overdue').count()
    return render(request, 'htmlpages/vaccine_history.html', {
        'vaccines': vaccines, 'member_name': member_name, 'member_relation': member_relation,
        'total': total, 'completed_count': completed, 'scheduled_count': scheduled,
        'overdue_count': overdue, 'title': f'{member_name} — Vaccine History',
    })


# =====================================================
# REMINDERS (পুরনো Reminder model)
# =====================================================

@login_required
def add_reminder(request):
    if request.method == 'POST':
        vaccine_name       = request.POST.get('vaccine_name', '').strip()
        scheduled_datetime = request.POST.get('scheduled', '').strip()
        family_member      = request.POST.get('family_member', '').strip()
        if not (vaccine_name and scheduled_datetime and family_member):
            messages.error(request, "❌ Please fill in all required fields.")
            return redirect('reminder_list')
        try:
            Reminder.objects.create(
                user=request.user, vaccine_name=vaccine_name,
                scheduled_datetime=parse_datetime(scheduled_datetime), family_member=family_member
            )
            messages.success(request, "✅ Reminder added!")
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
    return redirect('reminder_list')


@login_required
def edit_reminder(request):
    if request.method == 'POST':
        updated = 0
        for r in Reminder.objects.filter(user=request.user):
            vn   = request.POST.get(f'vaccine_name_{r.id}')
            sd   = request.POST.get(f'scheduled_{r.id}')
            fm   = request.POST.get(f'family_member_{r.id}')
            done = request.POST.get(f'completed_{r.id}') == 'on'
            if vn and sd and fm:
                try:
                    r.vaccine_name       = vn
                    r.scheduled_datetime = parse_datetime(sd)
                    r.family_member      = fm
                    r.completed          = done
                    r.save()
                    updated += 1
                except Exception as e:
                    print(f"Reminder update error {r.id}: {e}")
        if updated:
            messages.success(request, f"✅ {updated} reminder(s) updated!")
        else:
            messages.warning(request, "⚠️ No reminders updated.")
    return redirect('reminder_list')


# =====================================================
# VACCINATION CENTERS
# =====================================================

def centers(request):
    qs      = VaccinationCenter.objects.filter(is_active=True)
    q       = request.GET.get('q', '').strip()
    city    = request.GET.get('city', '').strip()
    vaccine = request.GET.get('vaccine', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(city__icontains=q))
    if city:
        qs = qs.filter(city__iexact=city)
    if vaccine:
        qs = qs.filter(available_vaccines__icontains=vaccine)
    return render(request, 'htmlpages/centers.html', {
        'centers': qs, 'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })


def center_detail(request, center_id):
    center = get_object_or_404(VaccinationCenter, id=center_id, is_active=True)
    return render(request, 'htmlpages/center_detail.html', {
        'center': center, 'google_maps_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })


# =====================================================
# ✅ নতুন (Task 1): AREA-BASED CENTER VIEW
# Area Admin & User উভয়েই নিজের এলাকার centers দেখবে
# =====================================================

@login_required
def area_centers(request):
    """
    User হলে → নিজের Profile.area এর centers।
    Area Admin (staff) হলে → AreaAdmin.area এর centers।
    Superuser হলে → সব area select করতে পারবে।
    """
    user_role         = 'user'
    user_area         = None
    can_add_center    = False
    can_pick_any_area = False

    if request.user.is_superuser:
        user_role         = 'superuser'
        can_add_center    = True
        can_pick_any_area = True
        # superuser GET ?area=... দিয়ে যেকোনো area দেখতে পারবে
        selected = request.GET.get('area', '').strip()
        user_area = selected if selected else 'Farmgate'

    elif request.user.is_staff:
        # Area Admin — শুধু নিজের এলাকা
        try:
            aa = AreaAdmin.objects.get(admin_user=request.user, is_active=True)
            user_area      = aa.area
            user_role      = 'area_admin'
            can_add_center = True
        except AreaAdmin.DoesNotExist:
            user_area = 'Central'
            user_role = 'staff_no_area'

    else:
        # Regular user — Profile.area থেকে
        try:
            profile = Profile.objects.get(user=request.user)
            user_area = profile.area or 'Central'
        except Profile.DoesNotExist:
            user_area = 'Central'

    centers_qs = VaccinationCenter.objects.filter(
        area=user_area, is_active=True
    ).order_by('-is_verified', '-rating', 'name')

    # Optional search filter
    q       = request.GET.get('q', '').strip()
    vaccine = request.GET.get('vaccine', '').strip()
    if q:
        centers_qs = centers_qs.filter(
            Q(name__icontains=q) | Q(address__icontains=q)
        )
    if vaccine:
        centers_qs = centers_qs.filter(available_vaccines__icontains=vaccine)

    # Area-level stats (admin দেখানোর জন্য)
    total_centers    = centers_qs.count()
    verified_centers = centers_qs.filter(is_verified=True).count()
    all_areas        = [a[0] for a in AreaAdmin._meta.get_field('area').choices]

    return render(request, 'htmlpages/area_centers.html', {
        'centers':           centers_qs,
        'user_area':         user_area,
        'user_role':         user_role,
        'can_add_center':    can_add_center,
        'can_pick_any_area': can_pick_any_area,
        'all_areas':         all_areas,
        'total_centers':     total_centers,
        'verified_centers':  verified_centers,
        'search_query':      q,
        'vaccine_filter':    vaccine,
        'title':             f'{user_area} এলাকার Vaccination Centers',
    })


@login_required
def add_area_center(request):
    """
    Area Admin বা Superuser নতুন vaccination center যোগ করবে।
    Area Admin → অটোমেটিক নিজের এলাকা সেট হবে।
    Superuser → যেকোনো এলাকা বেছে নিতে পারবে।
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin নতুন কেন্দ্র যোগ করতে পারবেন।")
        return redirect('area_centers')

    admin_area = None
    if not request.user.is_superuser:
        try:
            aa         = AreaAdmin.objects.get(admin_user=request.user, is_active=True)
            admin_area = aa.area
        except AreaAdmin.DoesNotExist:
            messages.error(request, "❌ আপনি কোনো এলাকার Admin নন।")
            return redirect('dashboard')

    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        city    = request.POST.get('city', 'Dhaka').strip()
        area    = request.POST.get('area', '').strip() if request.user.is_superuser else admin_area
        phone   = request.POST.get('phone', '').strip()
        email   = request.POST.get('email', '').strip()
        opening = request.POST.get('opening_time', '') or None
        closing = request.POST.get('closing_time', '') or None
        vaccines = request.POST.get('available_vaccines', '').strip() or 'COVID-19'
        description = request.POST.get('description', '').strip()

        if not name or not address or not area:
            messages.error(request, "❌ কেন্দ্রের নাম, ঠিকানা এবং এলাকা অবশ্যই দিতে হবে।")
        else:
            center = VaccinationCenter.objects.create(
                name=name, address=address, city=city, area=area,
                phone=phone or None, email=email or None,
                opening_time=opening, closing_time=closing,
                available_vaccines=vaccines, description=description,
                is_active=True, is_verified=request.user.is_superuser,
                created_by=request.user,
            )
            messages.success(
                request,
                f"✅ '{center.name}' কেন্দ্রটি {area} এলাকায় যোগ করা হয়েছে।"
            )
            return redirect('area_centers')

    return render(request, 'htmlpages/add_area_center.html', {
        'admin_area':   admin_area,
        'is_superuser': request.user.is_superuser,
        'all_areas':    [a[0] for a in AreaAdmin._meta.get_field('area').choices],
        'cities':       [c[0] for c in VaccinationCenter.CITY_CHOICES],
        'title':        'নতুন কেন্দ্র যোগ করুন',
    })


@login_required
def delete_area_center(request, center_id):
    """Area Admin/Superuser কেন্দ্র deactivate করবে।"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ Permission denied.")
        return redirect('area_centers')

    center = get_object_or_404(VaccinationCenter, id=center_id)

    # Area Admin শুধু নিজের এলাকার কেন্দ্র delete করতে পারবে
    if not request.user.is_superuser:
        try:
            aa = AreaAdmin.objects.get(admin_user=request.user, is_active=True)
            if center.area != aa.area:
                messages.error(request, "❌ এই কেন্দ্র আপনার এলাকার নয়।")
                return redirect('area_centers')
        except AreaAdmin.DoesNotExist:
            messages.error(request, "❌ আপনি কোনো এলাকার Admin নন।")
            return redirect('area_centers')

    if request.method == 'POST':
        center.is_active = False
        center.save()
        messages.success(request, f"✅ '{center.name}' কেন্দ্রটি deactivate করা হয়েছে।")
        return redirect('area_centers')

    return render(request, 'htmlpages/delete_center_confirm.html', {
        'center': center,
        'title': 'কেন্দ্র মুছুন',
    })


# =====================================================
# NEWS
# =====================================================

@login_required(login_url='login')
def news_list(request):
    category_filter = request.GET.get('category', '')
    search_query    = request.GET.get('search', '')
    news_items = News.objects.filter(is_published=True)
    if category_filter:
        news_items = news_items.filter(category=category_filter)
    if search_query:
        news_items = news_items.filter(
            Q(title__icontains=search_query) | Q(summary__icontains=search_query) | Q(content__icontains=search_query)
        )
    news_items = news_items.order_by('-published_date')
    return render(request, 'htmlpages/news.html', {
        'news_items':        news_items,
        'featured_news':     News.objects.filter(is_published=True, is_featured=True).order_by('-published_date')[:3],
        'categories':        News.CATEGORY_CHOICES,
        'selected_category': category_filter,
        'search_query':      search_query,
        'total_news':        news_items.count(),
        'title':             'Health News & Updates',
    })


@login_required(login_url='login')
def news_detail(request, slug):
    news_item = get_object_or_404(News, slug=slug, is_published=True)
    news_item.increment_views()
    related = News.objects.filter(category=news_item.category, is_published=True).exclude(id=news_item.id).order_by('-published_date')[:3]
    return render(request, 'htmlpages/news_detail.html', {
        'news': news_item, 'related_news': related,
        'reading_time': news_item.get_reading_time(), 'title': news_item.title,
    })


# =====================================================
# VACCINE UPDATES
# =====================================================

@login_required(login_url='login')
def vaccine_updates(request):
    category_filter = request.GET.get('category', '')
    search_query    = request.GET.get('search', '')
    updates = VaccineUpdate.objects.filter(is_published=True)
    if category_filter:
        updates = updates.filter(category=category_filter)
    if search_query:
        updates = updates.filter(Q(title__icontains=search_query) | Q(content__icontains=search_query))
    return render(request, 'htmlpages/vaccine_updates.html', {
        'updates': updates, 'categories': VaccineUpdate.CATEGORY_CHOICES,
        'selected_category': category_filter, 'search_query': search_query, 'title': 'Vaccine Updates',
    })


@login_required(login_url='login')
def vaccine_update_detail(request, pk):
    update = get_object_or_404(VaccineUpdate, pk=pk, is_published=True)
    return render(request, 'htmlpages/vaccine_updates_detail.html', {'update': update, 'title': update.title})


@login_required(login_url='login')
def create_vaccine_update(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('vaccine_updates')
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        content  = request.POST.get('content', '').strip()
        excerpt  = request.POST.get('excerpt', '').strip()
        category = request.POST.get('category', 'general')
        if title and content:
            u = VaccineUpdate.objects.create(title=title, content=content, excerpt=excerpt, category=category, author=request.user)
            messages.success(request, f'✅ "{u.title}" created!')
            return redirect('vaccine_update_detail', pk=u.pk)
        messages.error(request, '❌ Title and content required.')
    return render(request, 'htmlpages/vaccine_updates.html', {'categories': VaccineUpdate.CATEGORY_CHOICES, 'title': 'Create Vaccine Update'})


@login_required(login_url='login')
def edit_vaccine_update(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied.")
        return redirect('vaccine_updates')
    update = get_object_or_404(VaccineUpdate, pk=pk)
    if request.method == 'POST':
        update.title    = request.POST.get('title',    update.title).strip()
        update.content  = request.POST.get('content',  update.content).strip()
        update.excerpt  = request.POST.get('excerpt',  update.excerpt or '').strip()
        update.category = request.POST.get('category', update.category)
        update.save()
        messages.success(request, f'✅ "{update.title}" updated!')
        return redirect('vaccine_update_detail', pk=update.pk)
    return render(request, 'htmlpages/vaccine_updates_detail.html', {
        'update': update, 'categories': VaccineUpdate.CATEGORY_CHOICES, 'title': 'Edit Vaccine Update',
    })


# =====================================================
# FAMILY GROUP MANAGEMENT
# =====================================================

@login_required
def family_create_view(request):
    form = FamilyCreateForm(request.POST or None)
    if form.is_valid():
        family            = form.save(commit=False)
        family.created_by = request.user
        family.save()
        FamilyGroupMember.objects.create(family=family, user=request.user, role='Admin', can_view_others=True, can_edit_others=True)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.current_family = family
        profile.save()
        messages.success(request, "Family তৈরি হয়েছে!")
        return redirect('dashboard')
    return render(request, 'htmlpages/family_create.html', {'form': form})


@login_required
def family_invite_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        messages.error(request, "আপনি কোনো family তে নেই।")
        return redirect('family_create')
    get_object_or_404(FamilyGroupMember, family=family, user=request.user, role='Admin')
    form = FamilyInviteForm(request.POST or None)
    if form.is_valid():
        invitation = FamilyInvitation.objects.create(
            family=family, invited_by=request.user,
            email=form.cleaned_data['email'], role=form.cleaned_data['role'],
            relation=form.cleaned_data['relation'], expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject=f"{family.family_name} - Family Invitation",
            message=f"আপনাকে {family.family_name} তে invite করা হয়েছে।\nAccept: {accept_url}",
            from_email=settings.EMAIL_HOST_USER, recipient_list=[invitation.email]
        )
        messages.success(request, f"Invitation পাঠানো হয়েছে {invitation.email} এ!")
        return redirect('familymembers')
    return render(request, 'htmlpages/family_invite.html', {'form': form})


@login_required
def invitation_accept_view(request, token):
    invitation = get_object_or_404(FamilyInvitation, token=token)
    if not invitation.is_valid():
        messages.error(request, "Invitation expired বা আগেই use হয়েছে।")
        return redirect('dashboard')
    if request.method == 'POST':
        FamilyGroupMember.objects.get_or_create(
            family=invitation.family, user=request.user,
            defaults={'role': invitation.role, 'relation': invitation.relation}
        )
        invitation.is_accepted = True
        invitation.save()
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not profile.current_family:
            profile.current_family = invitation.family
            profile.save()
        messages.success(request, f"{invitation.family.family_name} এ যোগ দিয়েছেন!")
        return redirect('dashboard')
    return render(request, 'htmlpages/family_accept_invite.html', {'invitation': invitation})


@login_required
def admin_transfer_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    current_member = get_object_or_404(FamilyGroupMember, family=family, user=request.user, role='Admin')
    form = AdminTransferForm(family=family, current_user=request.user, data=request.POST or None)
    if form.is_valid():
        new_admin                      = form.cleaned_data['new_admin']
        current_member.role            = 'Member'
        current_member.can_edit_others = False
        current_member.save()
        new_admin.role            = 'Admin'
        new_admin.can_view_others = True
        new_admin.can_edit_others = True
        new_admin.save()
        messages.success(request, "Admin role transfer হয়েছে।")
        return redirect('familymembers')
    return render(request, 'htmlpages/admin_transfer.html', {'form': form})


@login_required
def dependent_upgrade_view(request, pk):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    dep_member = get_object_or_404(FamilyGroupMember, pk=pk, family=family, role='Dependent')
    if request.method == 'POST':
        invited_email = request.POST.get('email')
        invitation = FamilyInvitation.objects.create(
            family=family, invited_by=request.user, email=invited_email, role='Member',
            relation=dep_member.relation, expires_at=timezone.now() + timedelta(days=7)
        )
        accept_url = request.build_absolute_uri(f'/family/accept/{invitation.token}/')
        send_mail(
            subject="VaxSafe - আপনার নিজস্ব account তৈরি করুন",
            message=f"Account তৈরি করুন: {accept_url}",
            from_email=settings.EMAIL_HOST_USER, recipient_list=[invited_email]
        )
        messages.success(request, "Invitation পাঠানো হয়েছে!")
        return redirect('familymembers')
    return render(request, 'htmlpages/dependent_upgrade.html', {'member': dep_member})


@login_required
def leave_family_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        return redirect('family_create')
    member = get_object_or_404(FamilyGroupMember, family=family, user=request.user)
    if member.role == 'Admin' and family.members.filter(role='Admin', is_active=True).count() == 1:
        messages.error(request, "Family ছাড়ার আগে Admin transfer করুন।")
        return redirect('familymembers')

    # ✅ নতুন (Task 3): যেসব FamilyMember profile এই user manage করছে
    managed_members = FamilyMember.objects.filter(user=request.user, is_active=True)
    handoff_candidates = FamilyGroupMember.objects.filter(
        family=family, is_active=True
    ).exclude(user=request.user).exclude(user__isnull=True).select_related('user')

    if request.method == 'POST':
        action        = request.POST.get('action', 'leave')
        handoff_to_id = request.POST.get('handoff_to', '').strip()
        handoff_note  = request.POST.get('handoff_note', '').strip()

        # ✅ Action 1: managed profiles কে অন্য কারো হাতে handoff
        if action == 'handoff' and handoff_to_id:
            try:
                new_caretaker = User.objects.get(id=int(handoff_to_id))
                count = 0
                for fm in managed_members:
                    fm.previous_caretaker = request.user
                    fm.handoff_note       = handoff_note or f"{request.user.username} family ছেড়েছেন।"
                    fm.handoff_date       = timezone.now()
                    Vaccine.objects.filter(family_member=fm).update(user=new_caretaker)
                    fm.user = new_caretaker
                    fm.save()
                    count += 1

                    Notification.objects.create(
                        user=new_caretaker,
                        title=f"👤 আপনাকে নতুন Profile assign করা হয়েছে: {fm.name}",
                        message=(
                            f"{request.user.get_full_name() or request.user.username} family ছেড়ে যাওয়ার সময়\n"
                            f"'{fm.name}' ({fm.relation}) এর profile আপনার কাছে handover করেছেন।\n\n"
                            f"📝 নোট: {handoff_note or 'কোনো নোট নেই।'}\n\n"
                            f"এখন থেকে আপনি এই profile এর সব vaccine record manage করতে পারবেন।"
                        ),
                        notif_type='alert',
                    )
                if count:
                    messages.success(request, f"✅ {count} টি profile সফলভাবে handover হয়েছে।")
            except (User.DoesNotExist, ValueError):
                messages.error(request, "❌ Invalid caretaker selected.")
                return redirect('leave_family')

        # ✅ Action 2: managed profiles কে inactive mark — পরে claim করা যাবে
        elif action == 'mark_inactive':
            count = managed_members.update(
                is_active=False,
                previous_caretaker=request.user,
                handoff_note=handoff_note or f"{request.user.username} family ছেড়েছেন।",
                handoff_date=timezone.now(),
            )

            family_admins = FamilyGroupMember.objects.filter(
                family=family, role='Admin', is_active=True
            ).exclude(user=request.user)
            for fa in family_admins:
                if fa.user:
                    Notification.objects.create(
                        user=fa.user,
                        title=f"⚠️ Inactive Profiles — {count} টি claim প্রয়োজন",
                        message=(
                            f"{request.user.get_full_name() or request.user.username} family ছেড়ে গেছেন।\n"
                            f"তাঁর handle করা {count} টি profile এখন inactive অবস্থায় আছে।\n\n"
                            f"📋 'Claimable Profiles' page থেকে এই profile গুলো claim করুন।"
                        ),
                        notif_type='alert',
                    )
            if count:
                messages.warning(
                    request,
                    f"⚠️ {count} টি profile inactive মার্ক করা হয়েছে। অন্য family member রা claim করতে পারবেন।"
                )

        # আসল leave logic
        member.is_active = False
        member.save()
        new_family = FamilyGroup.objects.create(
            family_name=f"{request.user.first_name or request.user.username}'s Family",
            created_by=request.user
        )
        FamilyGroupMember.objects.create(
            family=new_family, user=request.user, role='Admin',
            can_view_others=True, can_edit_others=True
        )
        profile.current_family = new_family
        profile.save()
        messages.success(request, "🚪 Family থেকে বের হয়েছেন। নতুন family তৈরি হয়েছে।")
        return redirect('dashboard')

    return render(request, 'htmlpages/leave_family.html', {
        'family':              family,
        'managed_members':     managed_members,
        'handoff_candidates':  handoff_candidates,
        'title':               'Family ছাড়ুন',
    })


# =====================================================
# ✅ নতুন (Task 3): CLAIMABLE PROFILES — list page
# =====================================================

@login_required
def claimable_profiles_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family
    if not family:
        messages.info(request, "আপনি কোনো family তে নেই।")
        return redirect('family_create')

    family_user_ids = list(FamilyGroupMember.objects.filter(
        family=family
    ).values_list('user_id', flat=True))

    claimable = FamilyMember.objects.filter(
        is_active=False,
        previous_caretaker__id__in=family_user_ids,
    ).exclude(user=request.user).select_related('previous_caretaker').order_by('-handoff_date')

    return render(request, 'htmlpages/claimable_profiles.html', {
        'claimable': claimable,
        'family':    family,
        'title':     'Claimable Profiles',
    })


@login_required
def claim_profile_view(request, member_id):
    fm = get_object_or_404(FamilyMember, id=member_id, is_active=False)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    family = profile.current_family

    if family:
        family_user_ids = list(FamilyGroupMember.objects.filter(
            family=family
        ).values_list('user_id', flat=True))
        if fm.previous_caretaker_id and fm.previous_caretaker_id not in family_user_ids:
            messages.error(request, "❌ এই profile আপনার family-র নয়।")
            return redirect('claimable_profiles')

    if request.method == 'POST':
        old_caretaker = fm.previous_caretaker

        Vaccine.objects.filter(family_member=fm).update(user=request.user)
        VaccineReminder.objects.filter(family_member=fm).update(user=request.user)

        fm.user         = request.user
        fm.is_active    = True
        fm.handoff_date = timezone.now()
        fm.handoff_note = (
            f"{request.user.get_full_name() or request.user.username} এই profile claim করেছেন। "
            f"আগের note: {fm.handoff_note or '-'}"
        )
        fm.save()

        if old_caretaker and old_caretaker.is_active and old_caretaker != request.user:
            Notification.objects.create(
                user=old_caretaker,
                title=f"ℹ️ আপনার পূর্ববর্তী Profile claim হয়েছে: {fm.name}",
                message=(
                    f"{request.user.get_full_name() or request.user.username} "
                    f"'{fm.name}' এর profile claim করেছেন।"
                ),
                notif_type='alert',
            )

        Notification.objects.create(
            user=request.user,
            title=f"✅ Profile সফলভাবে Claim হয়েছে: {fm.name}",
            message=(
                f"আপনি এখন '{fm.name}' ({fm.relation}) এর profile manage করছেন।\n"
                f"সব vaccine history আপনার অ্যাকাউন্টে transfer হয়েছে।"
            ),
            notif_type='update',
        )

        messages.success(request, f"✅ '{fm.name}' এর profile সফলভাবে claim হয়েছে।")
        return redirect('familymembers')

    vaccine_count = Vaccine.objects.filter(family_member=fm).count()
    return render(request, 'htmlpages/claim_profile_confirm.html', {
        'member':        fm,
        'vaccine_count': vaccine_count,
        'title':         f'{fm.name} এর Profile Claim করুন',
    })


@login_required
def switch_family_view(request, pk):
    family = get_object_or_404(FamilyGroup, pk=pk)
    get_object_or_404(FamilyGroupMember, family=family, user=request.user, is_active=True)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.current_family = family
    profile.save()
    return redirect('dashboard')


# =====================================================
# NOTIFICATION VIEWS
# =====================================================

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count  = notifications.filter(is_read=False).count()
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'htmlpages/notifications.html', {
        'notifications': notifications, 'unread_count': unread_count,
    })


@login_required
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, "নোটিফিকেশন মুছে ফেলা হয়েছে।")
    return redirect('notification_list')


# =====================================================
# VACCINE REMINDER VIEWS
# =====================================================

@login_required
def reminder_list(request):
    if request.method == 'POST':
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "❌ শুধুমাত্র Admin Reminder সেট করতে পারবেন।")
            return redirect('reminder_list')
        return redirect('set_reminder')
    today             = timezone.now().date()
    vaccine_reminders = VaccineReminder.objects.filter(user=request.user).order_by('reminder_date')
    old_reminders     = Reminder.objects.filter(user=request.user).order_by('-scheduled_datetime')
    return render(request, 'htmlpages/reminder.html', {
        'vaccine_reminders': vaccine_reminders,
        'reminders':         old_reminders,
        'today':             today,
        'is_admin':          request.user.is_staff or request.user.is_superuser,
    })


@login_required
def set_reminder(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin Reminder সেট করতে পারবেন।")
        return redirect('reminder_list')

    all_users                = User.objects.all().order_by('first_name', 'username')
    user_family_members_json = _build_user_family_json(all_users)

    if request.method == 'POST':
        form = VaccineReminderForm(request.POST)

        target_user_id = request.POST.get('target_user')
        target_user    = request.user
        if target_user_id:
            try:
                target_user = User.objects.get(id=target_user_id)
            except User.DoesNotExist:
                pass

        family_member_id = request.POST.get('family_member_id')
        family_member    = None
        if family_member_id:
            try:
                family_member = FamilyMember.objects.get(id=family_member_id, user=target_user)
            except FamilyMember.DoesNotExist:
                pass

        if form.is_valid():
            vr               = form.save(commit=False)
            vr.user          = target_user
            vr.family_member = family_member
            vr.save()
            _send_reminder_notification(vr, target_user)
            recipient_label = family_member.name if family_member else (target_user.get_full_name() or target_user.username)
            messages.success(
                request,
                f"✅ '{recipient_label}' এর জন্য '{vr.vaccine_name}' রিমাইন্ডার সেট হয়েছে। "
                f"App Notification ও Email পাঠানো হয়েছে।"
            )
            return redirect('reminder_list')
        else:
            messages.error(request, "❌ তথ্য সঠিকভাবে পূরণ করুন।")
    else:
        form = VaccineReminderForm()

    return render(request, 'htmlpages/set_reminder.html', {
        'form':                     form,
        'all_users':                all_users,
        'user_family_members_json': user_family_members_json,
        'title':                    'Admin — Reminder সেট করুন',
    })


@login_required
def delete_reminder(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin Reminder মুছতে পারবেন।")
        return redirect('reminder_list')
    vr = get_object_or_404(VaccineReminder, pk=pk)
    vr.delete()
    messages.success(request, "রিমাইন্ডার মুছে ফেলা হয়েছে।")
    return redirect('reminder_list')


# =====================================================
# VACCINE SCHEDULE
# =====================================================

@login_required
def vaccine_schedule(request):
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')
    today         = timezone.now().date()
    Vaccine.objects.filter(user=request.user, status='Scheduled', date_administered__lt=today).update(status='Overdue')
    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')
    if member_filter == 'self':
        vaccines = vaccines.filter(family_member__isnull=True)
    elif member_filter:
        vaccines = vaccines.filter(family_member_id=member_filter)
    if status_filter:
        vaccines = vaccines.filter(status=status_filter)
    context = {
        'vaccines':          vaccines,
        'upcoming_vaccines': vaccines.filter(date_administered__gte=today).order_by('date_administered'),
        'past_vaccines':     vaccines.filter(date_administered__lt=today).order_by('-date_administered'),
        'family_members':    FamilyMember.objects.filter(user=request.user),
        'total_count':       vaccines.count(),
        'upcoming_count':    vaccines.filter(date_administered__gte=today).count(),
        'completed_count':   vaccines.filter(status='Completed').count(),
        'overdue_count':     vaccines.filter(status='Overdue').count(),
        'selected_member':   member_filter,
        'selected_status':   status_filter,
        'title':             'Vaccine Schedule',
        'is_admin':          request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'htmlpages/vaccine_schedule.html', context)


# =====================================================
# AREA ROUTING HELPER
# =====================================================

def _get_area_admin_for_user(user):
    """
    user এর এলাকা দেখে সেই এলাকার admin বের করো।
    যদি সেই এলাকার কোনো admin না থাকে → super admin কে return করো।
    """
    try:
        user_area      = user.profile.area or 'Central'
        area_admin_obj = AreaAdmin.objects.get(area=user_area, is_active=True)
        return area_admin_obj.admin_user
    except AreaAdmin.DoesNotExist:
        superuser = User.objects.filter(is_superuser=True, is_active=True).first()
        return superuser
    except Exception:
        return User.objects.filter(is_superuser=True, is_active=True).first()


# =====================================================
# USER: VACCINE REQUEST SUBMIT
# =====================================================

@login_required
def submit_vaccine_request(request):
    """User Admin কে টিকার জন্য request পাঠায়।"""
    if request.method == 'POST':
        form = VaccineRequestForm(request.POST, user=request.user)
        if form.is_valid():
            vr         = form.save(commit=False)
            vr.user    = request.user

            assigned      = _get_area_admin_for_user(request.user)
            vr.assigned_admin = assigned
            vr.save()

            if assigned:
                recipient_name = vr.get_recipient_name()
                user_area = getattr(request.user.profile, 'area', 'অজানা এলাকা') or 'অজানা এলাকা'
                Notification.objects.create(
                    user       = assigned,
                    title      = f"📋 নতুন টিকা Request: {vr.vaccine_name}",
                    message    = (
                        f"{request.user.get_full_name() or request.user.username} "
                        f"({user_area}) '{recipient_name}' এর জন্য "
                        f"'{vr.vaccine_name}' টিকার request করেছেন।\n"
                        f"📅 পছন্দের তারিখ: {vr.preferred_date.strftime('%d %B %Y')}"
                    ),
                    notif_type = 'alert',
                )
                if assigned.email:
                    try:
                        send_mail(
                            subject=f"VaxSafe — নতুন Vaccine Request: {vr.vaccine_name}",
                            message=(
                                f"User: {request.user.get_full_name() or request.user.username}\n"
                                f"Area: {user_area}\n"
                                f"Vaccine: {vr.vaccine_name}\n"
                                f"Preferred Date: {vr.preferred_date}\n"
                                f"Note: {vr.note or '-'}\n\n"
                                f"Dashboard থেকে Approve/Reject করুন।"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[assigned.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"[VaxSafe] Admin notification email error: {e}")

            messages.success(
                request,
                f"✅ '{vr.vaccine_name}' এর জন্য request পাঠানো হয়েছে! "
                f"Admin approve করলে আপনি notification পাবেন।"
            )
            return redirect('my_vaccine_requests')
        else:
            messages.error(request, "❌ তথ্য সঠিকভাবে পূরণ করুন।")
    else:
        form = VaccineRequestForm(user=request.user)

    # ✅ নতুন code (family_members যোগ করুন)
    from .models import FamilyMember  # উপরে import না থাকলে যোগ করুন

    return render(request, 'htmlpages/submit_vaccine_request.html', {
        'form': form,
        'title': 'টিকার জন্য Request করুন',
        'family_members': FamilyMember.objects.filter(user=request.user),
    })


@login_required
def my_vaccine_requests(request):
    """User নিজের সব request দেখতে পারবে।"""
    requests_qs = VaccineRequest.objects.filter(
        user=request.user
    ).select_related('family_member', 'assigned_admin').order_by('-created_at')

    return render(request, 'htmlpages/my_vaccine_requests.html', {
        'vaccine_requests': requests_qs,
        'pending_count':    requests_qs.filter(status='Pending').count(),
        'approved_count':   requests_qs.filter(status='Approved').count(),
        'rejected_count':   requests_qs.filter(status='Rejected').count(),
        'title':            'আমার টিকা Requests',
    })


# =====================================================
# ADMIN: MANAGE VACCINE REQUESTS (Area-filtered)
# =====================================================

@login_required
def admin_vaccine_requests(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ শুধুমাত্র Admin এই পেজ দেখতে পারবেন।")
        return redirect('dashboard')

    if request.user.is_superuser:
        requests_qs = VaccineRequest.objects.all().select_related(
            'user', 'family_member', 'assigned_admin'
        )
    else:
        requests_qs = VaccineRequest.objects.filter(
            assigned_admin=request.user
        ).select_related('user', 'family_member')

    status_filter = request.GET.get('status', '')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    requests_qs = requests_qs.order_by('-created_at')

    return render(request, 'htmlpages/admin_vaccine_requests.html', {
        'vaccine_requests': requests_qs,
        'pending_count':    requests_qs.filter(status='Pending').count(),
        'approved_count':   requests_qs.filter(status='Approved').count(),
        'rejected_count':   requests_qs.filter(status='Rejected').count(),
        'status_filter':    status_filter,
        'title':            'Vaccine Requests (Admin)',
        'is_superuser':     request.user.is_superuser,
    })


@login_required
def approve_vaccine_request(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ Permission denied.")
        return redirect('dashboard')

    vr = get_object_or_404(VaccineRequest, pk=pk)

    if not request.user.is_superuser and vr.assigned_admin != request.user:
        messages.error(request, "❌ এই request আপনার এলাকার নয়।")
        return redirect('admin_vaccine_requests')

    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()

        vr.status     = 'Approved'
        vr.admin_note = admin_note
        vr.save()

        vaccine = Vaccine.objects.create(
            user              = vr.user,
            family_member     = vr.family_member,
            name              = vr.vaccine_name,
            dose_number       = '1st',
            date_administered = vr.preferred_date,
            location          = vr.preferred_center or '',
            status            = 'Scheduled',
            notes             = f"User Request থেকে Approved। Admin Note: {admin_note}" if admin_note else "User Request থেকে Approved।",
        )

        recipient = vr.get_recipient_name()
        title = f"✅ টিকা Request Approved: {vr.vaccine_name}"
        msg_lines = [
            f"আপনার '{vr.vaccine_name}' টিকার request approve হয়েছে!",
            f"👤 Recipient: {recipient}",
            f"📅 তারিখ: {vr.preferred_date.strftime('%d %B %Y')}",
        ]
        if vr.preferred_center:
            msg_lines.append(f"📍 কেন্দ্র: {vr.preferred_center}")
        if admin_note:
            msg_lines.append(f"📝 Admin Note: {admin_note}")

        Notification.objects.create(
            user       = vr.user,
            title      = title,
            message    = "\n".join(msg_lines),
            notif_type = 'update',
        )
        if vr.user.email:
            try:
                send_mail(
                    subject=f"VaxSafe — {vr.vaccine_name} Request Approved!",
                    message=f"{title}\n\n" + "\n".join(msg_lines) + "\n\n---\nVaxSafe",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[vr.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"[VaxSafe] Approval email error: {e}")

        messages.success(
            request,
            f"✅ Request approve হয়েছে। Vaccine record তৈরি হয়েছে। "
            f"{vr.user.username} কে Notification পাঠানো হয়েছে।"
        )
        return redirect('admin_vaccine_requests')

    return render(request, 'htmlpages/approve_request_confirm.html', {
        'vr': vr, 'title': 'Request Approve করুন',
    })


@login_required
def reject_vaccine_request(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "❌ Permission denied.")
        return redirect('dashboard')

    vr = get_object_or_404(VaccineRequest, pk=pk)

    if not request.user.is_superuser and vr.assigned_admin != request.user:
        messages.error(request, "❌ এই request আপনার এলাকার নয়।")
        return redirect('admin_vaccine_requests')

    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()

        vr.status     = 'Rejected'
        vr.admin_note = admin_note
        vr.save()

        title = f"❌ টিকা Request Rejected: {vr.vaccine_name}"
        Notification.objects.create(
            user       = vr.user,
            title      = title,
            message    = (
                f"দুঃখিত, আপনার '{vr.vaccine_name}' request reject হয়েছে।\n"
                f"📝 কারণ: {admin_note or 'Admin কোনো কারণ দেননি।'}\n\n"
                f"পুনরায় request করতে পারেন।"
            ),
            notif_type = 'alert',
        )

        messages.warning(request, f"Request reject করা হয়েছে। {vr.user.username} কে Notification পাঠানো হয়েছে।")
        return redirect('admin_vaccine_requests')

    return render(request, 'htmlpages/reject_request_confirm.html', {
        'vr': vr, 'title': 'Request Reject করুন',
    })