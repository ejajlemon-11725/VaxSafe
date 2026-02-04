# views.py - Complete and Optimized with Centers and News
import random
import time
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Count, Q

from .models import Profile, FamilyMember, Reminder, Update, Vaccine, VaccinationCenter, News
from .forms import ProfileForm, FamilyMemberForm, VaccineForm


# =====================================================
# PUBLIC PAGES
# =====================================================

def home(request):
    """Homepage view"""
    return render(request, "htmlpages/home.html")


def features(request):
    """Features page view"""
    return render(request, "htmlpages/features.html")


def aboutUs(request):
    """About Us page view"""
    return render(request, "htmlpages/aboutUs.html")


def contact(request):
    """Contact page view"""
    return render(request, "htmlpages/contact.html")


def send_message(request):
    """Handle contact form submission"""
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
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
                messages.success(request, "Thank you for contacting us! We'll get back to you soon.")
            except Exception as e:
                messages.error(request, "Failed to send message. Please try again later.")
                print(f"Email error: {e}")
        else:
            messages.error(request, "Please fill in all fields.")

        return redirect('contact')

    return redirect('home')


# =====================================================
# OTP HELPER FUNCTIONS
# =====================================================

def send_otp(request, email):
    """Generate and send OTP to email"""
    otp = str(random.randint(100000, 999999))
    request.session['otp'] = otp
    request.session['email'] = email
    request.session['otp_time'] = time.time()

    try:
        send_mail(
            subject="Your VaxSafe Verification Code",
            message=f"Your verification code is: {otp}\n\nThis code will expire in 5 minutes.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        messages.error(request, "Could not send OTP. Please try again later.")
        return False


# =====================================================
# AUTHENTICATION
# =====================================================

def register(request):
    """User registration view"""
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("reset_password", "")

        # Validation
        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, "htmlpages/register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "htmlpages/register.html")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "htmlpages/register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, "htmlpages/register.html")

        if User.objects.filter(username=email).exists():
            messages.error(request, "This email is already in use.")
            return render(request, "htmlpages/register.html")

        # Save temp user data
        request.session['temp_user'] = {
            "full_name": full_name,
            "email": email,
            "password": password,
        }

        if send_otp(request, email):
            messages.info(request, "OTP sent to your email.")
            return redirect("verify")

    return render(request, "htmlpages/register.html")


def verify(request):
    """OTP verification view"""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "submit":
            entered_otp = request.POST.get("otp", "").strip()
            saved_otp = request.session.get("otp")
            otp_time = request.session.get("otp_time")

            # Expiry check (5 minutes)
            if otp_time and time.time() - otp_time > 300:
                messages.error(request, "OTP expired. Please resend.")
                return render(request, "htmlpages/verify.html")

            if entered_otp == saved_otp:
                data = request.session.get("temp_user")

                if data:
                    try:
                        # Create user
                        user = User.objects.create_user(
                            username=data["email"],
                            email=data["email"],
                            password=data["password"],
                            first_name=data["full_name"]
                        )

                        # Create profile
                        Profile.objects.create(user=user)

                        # Auto login
                        auth_login(request, user)

                        # Clear session
                        for key in ["otp", "otp_time", "temp_user", "email"]:
                            request.session.pop(key, None)

                        messages.success(request, "✅ Account created successfully! Welcome to VaxSafe!")
                        return redirect("dashboard")
                    except Exception as e:
                        messages.error(request, "Error creating account. Please try again.")
                        print(f"User creation error: {e}")
            else:
                messages.error(request, "❌ Invalid OTP. Please try again.")
                return render(request, "htmlpages/verify.html")

        elif action == "resend":
            email = request.session.get("email")
            if email:
                if send_otp(request, email):
                    messages.success(request, "✅ New OTP sent to your email!")
                return render(request, "htmlpages/verify.html")
            else:
                return redirect("register")

    return render(request, "htmlpages/verify.html")


def login_view(request):
    """User login view"""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Please provide both username and password.")
            return render(request, "htmlpages/login.html")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"✅ Welcome back, {user.first_name or user.username}!")
            return redirect("dashboard")
        else:
            messages.error(request, "❌ Invalid username or password.")

    return render(request, "htmlpages/login.html")


def logout(request):
    """User logout view"""
    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("home")


# =====================================================
# DASHBOARD & PROFILE
# =====================================================

@login_required(login_url='login')
def dashboard(request):
    """Main dashboard view with statistics"""
    # Get latest updates
    updates = Update.objects.all().order_by("-created_at")[:5]

    # Get family members count
    family_members_count = FamilyMember.objects.filter(user=request.user).count()

    # Get vaccine statistics
    today = timezone.now().date()

    total_vaccines = Vaccine.objects.filter(user=request.user).count()

    upcoming_vaccines = Vaccine.objects.filter(
        user=request.user,
        status='Scheduled',
        date_administered__gte=today
    ).order_by('date_administered')

    upcoming_count = upcoming_vaccines.count()

    # Update overdue vaccines
    Vaccine.objects.filter(
        user=request.user,
        status='Scheduled',
        date_administered__lt=today
    ).update(status='Overdue')

    overdue_count = Vaccine.objects.filter(
        user=request.user,
        status='Overdue'
    ).count()

    # Get active reminders count
    active_reminders_count = Reminder.objects.filter(
        user=request.user,
        completed=False,
        scheduled_datetime__gte=timezone.now()
    ).count()

    context = {
        'updates': updates,
        'family_members_count': family_members_count,
        'total_vaccines': total_vaccines,
        'upcoming_vaccines': upcoming_vaccines[:3],  # Show top 3
        'upcoming_count': upcoming_count,
        'overdue_count': overdue_count,
        'reminders_active': active_reminders_count > 0,
        'active_reminders_count': active_reminders_count,
    }

    return render(request, "htmlpages/dashboard.html", context)


@login_required
def profile_view(request):
    """User profile management view"""
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Handle photo deletion
        if 'delete_photo' in request.POST:
            if profile.photo:
                profile.photo.delete(save=True)
            messages.success(request, "✅ Profile photo deleted successfully!")
            return redirect('profile')

        # Handle profile update
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = ProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
        'title': 'My Profile'
    }
    return render(request, 'htmlpages/profile.html', context)


# Alias for backward compatibility
profile = profile_view


# =====================================================
# FAMILY MEMBERS MANAGEMENT
# =====================================================

@login_required
def familymembers(request):
    """View all family members"""
    members = FamilyMember.objects.filter(user=request.user).annotate(
        vaccine_count=Count('vaccines')
    ).order_by('name')

    context = {
        'members': members,
        'total_members': members.count(),
        'title': 'Family Members'
    }
    return render(request, "htmlpages/familymembers.html", context)


@login_required
def addfamilymember(request):
    """Add a new family member"""
    if request.method == "POST":
        form = FamilyMemberForm(request.POST)
        if form.is_valid():
            family_member = form.save(commit=False)
            family_member.user = request.user
            family_member.save()
            messages.success(request, f"✅ {family_member.name} added successfully!")
            return redirect("familymembers")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = FamilyMemberForm()

    context = {
        'form': form,
        'title': 'Add Family Member'
    }
    return render(request, "htmlpages/addfamilymember.html", context)


@login_required
def edit_family_member(request, member_id):
    """Edit a family member"""
    family_member = get_object_or_404(FamilyMember, id=member_id, user=request.user)

    if request.method == 'POST':
        form = FamilyMemberForm(request.POST, instance=family_member)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ {family_member.name} updated successfully!')
            return redirect('familymembers')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = FamilyMemberForm(instance=family_member)

    context = {
        'form': form,
        'family_member': family_member,
        'title': 'Edit Family Member',
        'is_edit': True
    }
    return render(request, 'htmlpages/addfamilymember.html', context)


@login_required
def delete_family_member(request, member_id):
    """Delete a family member"""
    family_member = get_object_or_404(FamilyMember, id=member_id, user=request.user)

    if request.method == 'POST':
        name = family_member.name

        # Check if family member has vaccines
        vaccine_count = family_member.vaccines.count()
        if vaccine_count > 0:
            messages.warning(
                request,
                f'⚠️ {name} has {vaccine_count} vaccine record(s). These will also be deleted.'
            )

        family_member.delete()
        messages.success(request, f'🗑️ {name} removed from family members!')
        return redirect('familymembers')

    context = {
        'family_member': family_member,
        'vaccine_count': family_member.vaccines.count()
    }
    return render(request, 'htmlpages/delete_family_member_confirm.html', context)


# =====================================================
# VACCINE MANAGEMENT
# =====================================================

@login_required
def add_vaccine(request):
    """Add a new vaccine record"""
    if request.method == 'POST':
        form = VaccineForm(request.POST, user=request.user)

        if form.is_valid():
            vaccine = form.save(commit=False)
            vaccine.user = request.user
            vaccine.save()

            messages.success(request, f'✅ Vaccine "{vaccine.name}" added successfully!')
            return redirect('vaccine_schedule')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = VaccineForm(user=request.user)

    context = {
        'form': form,
        'title': 'Add Vaccine'
    }
    return render(request, 'htmlpages/addvaccine.html', context)


@login_required
def vaccine_schedule(request):
    """Display vaccine schedule with filtering"""
    # Get filter parameters
    member_filter = request.GET.get('member', '')
    status_filter = request.GET.get('status', '')

    # Base queryset
    vaccines = Vaccine.objects.filter(user=request.user).select_related('family_member')

    # Apply filters
    if member_filter:
        if member_filter == 'self':
            vaccines = vaccines.filter(family_member__isnull=True)
        else:
            vaccines = vaccines.filter(family_member_id=member_filter)

    if status_filter:
        vaccines = vaccines.filter(status=status_filter)

    # Update overdue vaccines
    today = timezone.now().date()
    Vaccine.objects.filter(
        user=request.user,
        status='Scheduled',
        date_administered__lt=today
    ).update(status='Overdue')

    # Separate upcoming and past
    upcoming_vaccines = vaccines.filter(date_administered__gte=today).order_by('date_administered')
    past_vaccines = vaccines.filter(date_administered__lt=today).order_by('-date_administered')

    # Get family members for filter
    family_members = FamilyMember.objects.filter(user=request.user)

    # Calculate statistics
    total_count = vaccines.count()
    upcoming_count = upcoming_vaccines.count()
    completed_count = vaccines.filter(status='Completed').count()
    overdue_count = vaccines.filter(status='Overdue').count()

    context = {
        'vaccines': vaccines,
        'upcoming_vaccines': upcoming_vaccines,
        'past_vaccines': past_vaccines,
        'family_members': family_members,
        'total_count': total_count,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'selected_member': member_filter,
        'selected_status': status_filter,
        'title': 'Vaccine Schedule'
    }
    return render(request, 'htmlpages/vaccine_schedule.html', context)


@login_required
def edit_vaccine(request, vaccine_id):
    """Edit an existing vaccine record"""
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)

    if request.method == 'POST':
        form = VaccineForm(request.POST, instance=vaccine, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Vaccine "{vaccine.name}" updated successfully!')
            return redirect('vaccine_schedule')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = VaccineForm(instance=vaccine, user=request.user)

    context = {
        'form': form,
        'vaccine': vaccine,
        'title': 'Edit Vaccine',
        'is_edit': True
    }
    return render(request, 'htmlpages/addvaccine.html', context)


@login_required
def delete_vaccine(request, vaccine_id):
    """Delete a vaccine record"""
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)

    if request.method == 'POST':
        vaccine_name = vaccine.name
        vaccine.delete()
        messages.success(request, f'🗑️ Vaccine "{vaccine_name}" deleted successfully!')
        return redirect('vaccine_schedule')

    context = {
        'vaccine': vaccine,
        'title': 'Delete Vaccine'
    }
    return render(request, 'htmlpages/delete_vaccine_confirm.html', context)


@login_required
def vaccine_detail(request, vaccine_id):
    """View detailed information about a vaccine"""
    vaccine = get_object_or_404(Vaccine, id=vaccine_id, user=request.user)

    context = {
        'vaccine': vaccine,
        'is_upcoming': vaccine.is_upcoming(),
        'is_overdue': vaccine.is_overdue(),
        'days_until': vaccine.days_until() if vaccine.is_upcoming() else None,
        'title': f'{vaccine.name} Details'
    }
    return render(request, 'htmlpages/vaccine_detail.html', context)


@login_required
def upcoming_vaccinations(request):
    """View upcoming vaccinations"""
    today = timezone.now().date()

    upcoming = Vaccine.objects.filter(
        user=request.user,
        status='Scheduled',
        date_administered__gte=today
    ).select_related('family_member').order_by('date_administered')

    context = {
        'vaccinations': upcoming,
        'count': upcoming.count(),
        'title': 'Upcoming Vaccinations'
    }
    return render(request, 'htmlpages/upcoming_vaccinations.html', context)


@login_required
def overdue_vaccinations(request):
    """View overdue vaccinations"""
    today = timezone.now().date()

    # Update status for overdue vaccines
    Vaccine.objects.filter(
        user=request.user,
        status='Scheduled',
        date_administered__lt=today
    ).update(status='Overdue')

    overdue = Vaccine.objects.filter(
        user=request.user,
        status='Overdue'
    ).select_related('family_member').order_by('date_administered')

    context = {
        'vaccinations': overdue,
        'count': overdue.count(),
        'title': 'Overdue Vaccinations'
    }
    return render(request, 'htmlpages/overdue_vaccinations.html', context)


# =====================================================
# REMINDERS MANAGEMENT
# =====================================================

@login_required
def reminder(request):
    """List all reminders"""
    reminders = Reminder.objects.filter(user=request.user).order_by('-scheduled_datetime')

    # Separate active and past reminders
    active_reminders = [r for r in reminders if r.is_active]
    past_reminders = [r for r in reminders if not r.is_active]

    context = {
        'reminders': reminders,
        'active_reminders': active_reminders,
        'past_reminders': past_reminders,
        'active_count': len(active_reminders),
        'title': 'Reminders'
    }
    return render(request, 'htmlpages/reminder.html', context)


@login_required
def add_reminder(request):
    """Add a new reminder"""
    if request.method == 'POST':
        vaccine_name = request.POST.get('vaccine_name', '').strip()
        scheduled_datetime = request.POST.get('scheduled', '').strip()
        family_member = request.POST.get('family_member', '').strip()

        if not (vaccine_name and scheduled_datetime and family_member):
            messages.error(request, "❌ Please fill in all required fields.")
            return redirect('reminder')

        try:
            Reminder.objects.create(
                user=request.user,
                vaccine_name=vaccine_name,
                scheduled_datetime=parse_datetime(scheduled_datetime),
                family_member=family_member
            )
            messages.success(request, "✅ Reminder added successfully!")
        except Exception as e:
            messages.error(request, f"❌ Error adding reminder: {str(e)}")

        return redirect('reminder')

    return redirect('reminder')


@login_required
def edit_reminder(request):
    """Edit all reminders (bulk update)"""
    if request.method == 'POST':
        reminders = Reminder.objects.filter(user=request.user)
        updated_count = 0

        for r in reminders:
            vaccine_name = request.POST.get(f'vaccine_name_{r.id}')
            scheduled_datetime = request.POST.get(f'scheduled_{r.id}')
            family_member = request.POST.get(f'family_member_{r.id}')
            completed = request.POST.get(f'completed_{r.id}') == 'on'

            if vaccine_name and scheduled_datetime and family_member:
                try:
                    r.vaccine_name = vaccine_name
                    r.scheduled_datetime = parse_datetime(scheduled_datetime)
                    r.family_member = family_member
                    r.completed = completed
                    r.save()
                    updated_count += 1
                except Exception as e:
                    print(f"Error updating reminder {r.id}: {e}")

        if updated_count > 0:
            messages.success(request, f"✅ {updated_count} reminder(s) updated successfully!")
        else:
            messages.warning(request, "⚠️ No reminders were updated.")

        return redirect('reminder')

    return redirect('reminder')


# =====================================================
# VACCINATION CENTERS
# =====================================================

@login_required(login_url='login')
def centers(request):
    """View vaccination centers with search and filtering"""
    # Get filter parameters
    city_filter = request.GET.get('city', '')
    search_query = request.GET.get('search', '')

    # Base queryset - only active centers
    centers_list = VaccinationCenter.objects.filter(is_active=True)

    # Apply city filter
    if city_filter:
        centers_list = centers_list.filter(city=city_filter)

    # Apply search
    if search_query:
        centers_list = centers_list.filter(
            Q(name__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(available_vaccines__icontains=search_query)
        )

    # Order by city and name
    centers_list = centers_list.order_by('city', 'name')

    # Get all cities for filter dropdown
    cities = VaccinationCenter.CITY_CHOICES

    context = {
        'centers': centers_list,
        'cities': cities,
        'selected_city': city_filter,
        'search_query': search_query,
        'total_centers': centers_list.count(),
        'title': 'Vaccination Centers'
    }
    return render(request, "htmlpages/centers.html", context)


@login_required(login_url='login')
def center_detail(request, center_id):
    """View detailed information about a vaccination center"""
    center = get_object_or_404(VaccinationCenter, id=center_id, is_active=True)

    context = {
        'center': center,
        'vaccines_list': center.get_vaccines_list(),
        'operating_hours': center.get_operating_hours(),
        'title': center.name
    }
    return render(request, 'htmlpages/center_detail.html', context)


# =====================================================
# NEWS & UPDATES
# =====================================================

@login_required(login_url='login')
def news_list(request):
    """View all published news with filtering"""
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')

    # Base queryset - only published news
    news_items = News.objects.filter(is_published=True)

    # Apply category filter
    if category_filter:
        news_items = news_items.filter(category=category_filter)

    # Apply search
    if search_query:
        news_items = news_items.filter(
            Q(title__icontains=search_query) |
            Q(summary__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # Order by publication date
    news_items = news_items.order_by('-published_date')

    # Get featured news
    featured_news = News.objects.filter(is_published=True, is_featured=True).order_by('-published_date')[:3]

    # Get categories for filter
    categories = News.CATEGORY_CHOICES

    context = {
        'news_items': news_items,
        'featured_news': featured_news,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
        'total_news': news_items.count(),
        'title': 'Health News & Updates'
    }
    return render(request, 'htmlpages/news.html', context)


@login_required(login_url='login')
def news_detail(request, slug):
    """View detailed news article"""
    news_item = get_object_or_404(News, slug=slug, is_published=True)

    # Increment view count
    news_item.increment_views()

    # Get related news (same category, excluding current)
    related_news = News.objects.filter(
        category=news_item.category,
        is_published=True
    ).exclude(id=news_item.id).order_by('-published_date')[:3]

    context = {
        'news': news_item,
        'related_news': related_news,
        'reading_time': news_item.get_reading_time(),
        'title': news_item.title
    }
    return render(request, 'htmlpages/news_detail.html', context)


# =====================================================
# UTILITY VIEWS
# =====================================================

def verify_email(request):
    """Email verification page"""
    return render(request, "htmlpages/verifyemail.html")