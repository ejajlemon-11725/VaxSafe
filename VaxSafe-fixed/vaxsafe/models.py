# models.py - Fixed & Clean
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ============================================================
# AREA CHOICES  (top-level — সব জায়গায় ব্যবহার হবে)
# ============================================================

AREA_CHOICES = [
    ('Farmgate',  'Farmgate'),
    ('Mirpur-10', 'Mirpur-10'),
    ('Banani',    'Banani'),
    ('Uttara',    'Uttara'),
    ('Central',   'Central / Other'),
]


# ============================================================
# UPDATE MODEL
# ============================================================

class Update(models.Model):
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    posted_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Update'
        verbose_name_plural = 'Updates'

    def __str__(self):
        return self.title


# ============================================================
# PROFILE MODEL
# ============================================================

class Profile(models.Model):
    GENDER_CHOICES = [
        ('Male',   'Male'),
        ('Female', 'Female'),
        ('Other',  'Other'),
    ]

    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile        = models.CharField(max_length=20, blank=True, null=True)
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profession    = models.CharField(max_length=100, blank=True, null=True)
    address       = models.TextField(blank=True, null=True)
    blood_group   = models.CharField(max_length=5, blank=True, null=True)
    photo         = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # ✅ FIXED: area field যোগ করা হয়েছে
    area = models.CharField(
        max_length=50,
        choices=AREA_CHOICES,
        blank=True, null=True,
        help_text="আপনার এলাকা — Admin route করার জন্য ব্যবহৃত হবে"
    )

    current_family = models.ForeignKey(
        'FamilyGroup',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        return self.user.get_full_name() or self.user.username


# ============================================================
# FAMILY MEMBER MODEL  (vaccination tracking)
# ============================================================

class FamilyMember(models.Model):
    RELATIONSHIP_CHOICES = [
        ('Self',        'Self'),
        ('Spouse',      'Spouse'),
        ('Child',       'Child'),
        ('Parent',      'Parent'),
        ('Sibling',     'Sibling'),
        ('Grandparent', 'Grandparent'),
        ('Grandchild',  'Grandchild'),
        ('Other',       'Other'),
    ]

    GENDER_CHOICES = [
        ('Male',   'Male'),
        ('Female', 'Female'),
        ('Other',  'Other'),
    ]

    NOTIFICATION_CHOICES = [
        ('Email',            'Email'),
        ('SMS',              'SMS'),
        ('App Notification', 'App Notification'),
    ]

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_members')
    name          = models.CharField(max_length=100)
    age           = models.PositiveIntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    relation      = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    blood_group   = models.CharField(max_length=5, blank=True, null=True)

    vaccine_name      = models.CharField(max_length=100, blank=True, null=True)
    date_time         = models.DateTimeField(blank=True, null=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_CHOICES, blank=True, null=True)

    # ✅ নতুন: Profile claim/handoff tracking এর জন্য
    is_active           = models.BooleanField(
        default=True,
        help_text="False হলে এই profile আর কেউ handle করছে না — claim/transfer প্রয়োজন"
    )
    previous_caretaker  = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='handed_off_members',
        help_text="যে আগে এই profile handle করত (history track করার জন্য)"
    )
    handoff_note        = models.TextField(
        blank=True, null=True,
        help_text="কেন এই profile handover/inactive হয়েছে"
    )
    handoff_date        = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Family Member'
        verbose_name_plural = 'Family Members'
        indexes = [
            models.Index(fields=['user', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.relation})"

    def calculate_age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age -= 1
            return age
        return self.age

    @property
    def display_age(self):
        return self.calculate_age() or self.age or "N/A"


# ============================================================
# VACCINE MODEL
# ============================================================

class Vaccine(models.Model):
    VACCINE_TYPES = [
        ('COVID-19',             'COVID-19'),
        ('Influenza',            'Influenza (Flu)'),
        ('Hepatitis B',          'Hepatitis B'),
        ('Hepatitis A',          'Hepatitis A'),
        ('MMR',                  'MMR (Measles, Mumps, Rubella)'),
        ('Polio',                'Polio'),
        ('DTP',                  'DTP (Diphtheria, Tetanus, Pertussis)'),
        ('Varicella',            'Varicella (Chickenpox)'),
        ('HPV',                  'HPV (Human Papillomavirus)'),
        ('Pneumococcal',         'Pneumococcal'),
        ('Meningococcal',        'Meningococcal'),
        ('Rotavirus',            'Rotavirus'),
        ('Rabies',               'Rabies'),
        ('Typhoid',              'Typhoid'),
        ('Yellow Fever',         'Yellow Fever'),
        ('Japanese Encephalitis','Japanese Encephalitis'),
        ('BCG',                  'BCG (Tuberculosis)'),
        ('Other',                'Other'),
    ]

    DOSE_CHOICES = [
        ('1st',     '1st Dose'),
        ('2nd',     '2nd Dose'),
        ('3rd',     '3rd Dose'),
        ('Booster', 'Booster'),
        ('Single',  'Single Dose'),
    ]

    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Overdue',   'Overdue'),
        ('Cancelled', 'Cancelled'),
    ]

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vaccines')
    family_member = models.ForeignKey(
        FamilyMember, on_delete=models.CASCADE,
        null=True, blank=True, related_name='vaccines'
    )

    name                = models.CharField(max_length=100, choices=VACCINE_TYPES)
    dose_number         = models.CharField(max_length=20, choices=DOSE_CHOICES, default='1st')
    manufacturer        = models.CharField(max_length=100, blank=True, null=True)
    batch_number        = models.CharField(max_length=50, blank=True, null=True)
    date_administered   = models.DateField()
    next_dose_date      = models.DateField(null=True, blank=True)
    location            = models.CharField(max_length=200, blank=True, null=True)
    healthcare_provider = models.CharField(max_length=100, blank=True, null=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    notes               = models.TextField(blank=True, null=True)
    side_effects        = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_administered']
        verbose_name = 'Vaccine'
        verbose_name_plural = 'Vaccines'
        indexes = [
            models.Index(fields=['user', 'date_administered']),
            models.Index(fields=['status']),
            models.Index(fields=['family_member']),
        ]

    def __str__(self):
        if self.family_member:
            return f"{self.name} - {self.dose_number} for {self.family_member.name}"
        return f"{self.name} - {self.dose_number} for {self.user.get_full_name() or self.user.username}"

    def is_upcoming(self):
        return self.date_administered > timezone.now().date()

    def is_overdue(self):
        return self.status == 'Scheduled' and self.date_administered < timezone.now().date()

    def days_until(self):
        return (self.date_administered - timezone.now().date()).days

    def get_recipient_name(self):
        if self.family_member:
            return self.family_member.name
        return self.user.get_full_name() or self.user.username


# ============================================================
# REMINDER MODEL
# ============================================================

class Reminder(models.Model):
    user               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
    vaccine_name       = models.CharField(max_length=255)
    scheduled_datetime = models.DateTimeField()
    family_member      = models.CharField(max_length=255)
    completed          = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_datetime']
        verbose_name = 'Reminder'
        verbose_name_plural = 'Reminders'
        indexes = [
            models.Index(fields=['user', 'scheduled_datetime']),
            models.Index(fields=['completed']),
        ]

    def __str__(self):
        return f"{self.vaccine_name} for {self.family_member} on {self.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"

    @property
    def status(self):
        if self.completed:
            return "Completed"
        elif self.scheduled_datetime < timezone.now():
            return "Missed"
        return "Active"

    @property
    def is_active(self):
        return not self.completed and self.scheduled_datetime >= timezone.now()

    @property
    def is_missed(self):
        return not self.completed and self.scheduled_datetime < timezone.now()

    def time_until(self):
        if self.completed:
            return "Completed"
        delta = self.scheduled_datetime - timezone.now()
        if delta.days > 0:
            return f"{delta.days} day(s)"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hour(s)"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} minute(s)"
        elif delta.days < 0:
            return "Overdue"
        return "Soon"


# ============================================================
# VACCINATION CENTER MODEL
# ============================================================

class VaccinationCenter(models.Model):
    CITY_CHOICES = [
        ('Dhaka',      'Dhaka'),
        ('Chittagong', 'Chittagong'),
        ('Sylhet',     'Sylhet'),
        ('Rajshahi',   'Rajshahi'),
        ('Khulna',     'Khulna'),
        ('Barisal',    'Barisal'),
        ('Rangpur',    'Rangpur'),
        ('Mymensingh', 'Mymensingh'),
    ]

    name               = models.CharField(max_length=255)
    address            = models.TextField()
    city               = models.CharField(max_length=100, choices=CITY_CHOICES, default='Dhaka')
    # ✅ নতুন: Area-based filtering এর জন্য
    area               = models.CharField(
        max_length=50,
        choices=AREA_CHOICES,
        default='Central',
        help_text="এই কেন্দ্র কোন এলাকায় অবস্থিত — Area Admin এই কেন্দ্রগুলো manage করবেন"
    )
    phone              = models.CharField(max_length=20, blank=True, null=True)
    email              = models.EmailField(blank=True, null=True)
    opening_time       = models.TimeField(blank=True, null=True)
    closing_time       = models.TimeField(blank=True, null=True)
    available_vaccines = models.TextField(
        blank=True, null=True,
        help_text="Comma-separated list of available vaccines",
        default="COVID-19, Influenza, Hepatitis B"
    )
    latitude  = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    website   = models.URLField(blank=True, null=True)

    is_active   = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    rating      = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_centers'
    )

    class Meta:
        ordering = ['-rating', 'name']
        verbose_name = 'Vaccination Center'
        verbose_name_plural = 'Vaccination Centers'
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['area', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

    def get_operating_hours(self):
        if self.opening_time and self.closing_time:
            return f"{self.opening_time.strftime('%I:%M %p')} - {self.closing_time.strftime('%I:%M %p')}"
        return "Not specified"

    def get_vaccines_list(self):
        if self.available_vaccines:
            return [v.strip() for v in self.available_vaccines.split(',')]
        return []

    def get_google_maps_url(self):
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return "#"

    def get_distance_from(self, user_lat, user_lng):
        if not self.latitude or not self.longitude:
            return None
        from math import radians, sin, cos, sqrt, atan2
        R = 6371.0
        lat1, lon1 = map(lambda x: radians(float(x)), [user_lat, user_lng])
        lat2, lon2 = map(lambda x: radians(float(x)), [self.latitude, self.longitude])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 2)


# ============================================================
# NEWS MODEL
# ============================================================

class News(models.Model):
    CATEGORY_CHOICES = [
        ('General',   'General Health'),
        ('COVID-19',  'COVID-19'),
        ('Vaccines',  'Vaccines'),
        ('Research',  'Research & Studies'),
        ('Policy',    'Health Policy'),
        ('Awareness', 'Public Awareness'),
        ('Alert',     'Health Alert'),
    ]

    title        = models.CharField(max_length=300)
    slug         = models.SlugField(max_length=300, unique=True, blank=True)
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    summary      = models.TextField()
    content      = models.TextField()
    image        = models.ImageField(upload_to='news_images/', blank=True, null=True)
    source       = models.CharField(max_length=200, blank=True, null=True)
    source_url   = models.URLField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    is_featured  = models.BooleanField(default=False)
    published_date = models.DateTimeField(default=timezone.now)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    author       = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='news_articles'
    )
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-published_date']
        verbose_name = 'News Article'
        verbose_name_plural = 'News Articles'
        indexes = [
            models.Index(fields=['-published_date', 'is_published']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug, counter = base_slug, 1
            while News.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def get_reading_time(self):
        return f"{max(1, len(self.content.split()) // 200)} min read"


# ============================================================
# VACCINE UPDATE MODEL
# ============================================================

class VaccineUpdate(models.Model):
    CATEGORY_CHOICES = [
        ('general',     'General'),
        ('campaign',    'Campaign'),
        ('new_vaccine', 'New Vaccine'),
        ('policy',      'Policy Change'),
        ('alert',       'Health Alert'),
        ('schedule',    'Schedule Update'),
    ]

    title        = models.CharField(max_length=300)
    content      = models.TextField()
    excerpt      = models.TextField(blank=True, null=True)
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    author       = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vaccine_updates'
    )
    date         = models.DateTimeField(default=timezone.now)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Vaccine Update'
        verbose_name_plural = 'Vaccine Updates'

    def __str__(self):
        return self.title


# ============================================================
# FAMILY GROUP MODELS
# ============================================================

class FamilyGroup(models.Model):
    family_name = models.CharField(max_length=100)
    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='created_families'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.family_name

    def get_primary_admin(self):
        return self.members.filter(role='Admin', is_active=True).first()


class FamilyGroupMember(models.Model):
    ROLE_CHOICES = [
        ('Admin',     'Admin'),
        ('Guardian',  'Guardian'),
        ('Member',    'Member'),
        ('Dependent', 'Dependent'),
    ]

    family          = models.ForeignKey(FamilyGroup, on_delete=models.CASCADE, related_name='members')
    user            = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True, related_name='family_memberships'
    )
    dependent_name  = models.CharField(max_length=100, blank=True)
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Member')
    relation        = models.CharField(max_length=50, blank=True)
    can_view_others = models.BooleanField(default=False)
    can_edit_others = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)
    joined_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('family', 'user')
        verbose_name = 'Family Group Member'
        verbose_name_plural = 'Family Group Members'

    def __str__(self):
        name = self.user.get_full_name() if self.user else self.dependent_name
        return f"{name} ({self.role}) — {self.family.family_name}"


class FamilyInvitation(models.Model):
    family      = models.ForeignKey(FamilyGroup, on_delete=models.CASCADE)
    invited_by  = models.ForeignKey(User, on_delete=models.CASCADE)
    email       = models.EmailField()
    token       = models.UUIDField(default=uuid.uuid4, unique=True)
    role        = models.CharField(max_length=20, default='Member')
    relation    = models.CharField(max_length=50, blank=True)
    is_accepted = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    def is_valid(self):
        return not self.is_accepted and timezone.now() < self.expires_at

    def __str__(self):
        return f"Invite to {self.family} for {self.email}"


# ============================================================
# NOTIFICATION MODEL
# ============================================================

class Notification(models.Model):
    TYPE_CHOICES = [
        ('reminder', 'Vaccine Reminder'),
        ('update',   'Vaccine Update'),
        ('alert',    'General Alert'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='reminder')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# ============================================================
# VACCINE REMINDER MODEL
# ============================================================

class VaccineReminder(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vaccine_reminders')
    vaccine_name  = models.CharField(max_length=200)
    reminder_date = models.DateField()
    reminder_time = models.TimeField(default='09:00')
    note          = models.TextField(blank=True, null=True)
    is_sent       = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    family_member = models.ForeignKey(
        'FamilyMember',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vaccine_reminders'
    )

    class Meta:
        ordering = ['reminder_date']
        verbose_name = 'Vaccine Reminder'
        verbose_name_plural = 'Vaccine Reminders'

    def __str__(self):
        if self.family_member:
            return f"{self.user.username} → {self.family_member.name} — {self.vaccine_name} — {self.reminder_date}"
        return f"{self.user.username} (Self) — {self.vaccine_name} — {self.reminder_date}"

    def get_recipient_name(self):
        if self.family_member:
            return self.family_member.name
        return self.user.get_full_name() or self.user.username


# ============================================================
# VACCINE SCHEDULE MODEL (Admin-controlled)
# ============================================================

class VaccineSchedule(models.Model):
    VACCINE_TYPES = [
        ('COVID-19',              'COVID-19'),
        ('Influenza',             'Influenza (Flu)'),
        ('Hepatitis B',           'Hepatitis B'),
        ('Hepatitis A',           'Hepatitis A'),
        ('MMR',                   'MMR (Measles, Mumps, Rubella)'),
        ('Polio',                 'Polio'),
        ('DTP',                   'DTP (Diphtheria, Tetanus, Pertussis)'),
        ('Varicella',             'Varicella (Chickenpox)'),
        ('HPV',                   'HPV'),
        ('Pneumococcal',          'Pneumococcal'),
        ('BCG',                   'BCG (Tuberculosis)'),
        ('Rotavirus',             'Rotavirus'),
        ('Typhoid',               'Typhoid'),
        ('Yellow Fever',          'Yellow Fever'),
        ('Meningococcal',         'Meningococcal'),
        ('Japanese Encephalitis', 'Japanese Encephalitis'),
        ('Rabies',                'Rabies'),
        ('Other',                 'Other'),
    ]

    DOSE_CHOICES = [
        ('1st',     '1st Dose'),
        ('2nd',     '2nd Dose'),
        ('3rd',     '3rd Dose'),
        ('Booster', 'Booster'),
        ('Single',  'Single Dose'),
    ]

    vaccine_name   = models.CharField(max_length=100, choices=VACCINE_TYPES)
    dose_number    = models.CharField(max_length=20, choices=DOSE_CHOICES)
    interval_days  = models.PositiveIntegerField(
        default=0,
        help_text="পরের ডোজ কতদিন পর? (শেষ ডোজ হলে 0 দিন)"
    )
    description    = models.TextField(blank=True, null=True,
                                      help_text="এই ডোজ সম্পর্কে নোট")
    is_active      = models.BooleanField(default=True)
    created_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['vaccine_name', 'dose_number']
        verbose_name        = 'Vaccine Schedule'
        verbose_name_plural = 'Vaccine Schedules'
        unique_together     = ('vaccine_name', 'dose_number')

    def __str__(self):
        days = f" → পরের ডোজ {self.interval_days} দিন পর" if self.interval_days else " (শেষ ডোজ)"
        return f"{self.vaccine_name} — {self.dose_number}{days}"


# ============================================================
# CUSTOM VACCINE TYPE MODEL (Admin-controlled)
# ============================================================

class CustomVaccineType(models.Model):
    name             = models.CharField(max_length=200, unique=True)
    description      = models.TextField(blank=True, null=True)
    is_active        = models.BooleanField(default=True)
    notify_all_users = models.BooleanField(
        default=True,
        help_text="✅ Save করলে সব user কে App Notification পাঠাবে"
    )
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['name']
        verbose_name        = 'Custom Vaccine Type'
        verbose_name_plural = 'Custom Vaccine Types'

    def __str__(self):
        return self.name


# ============================================================
# OTP VERIFICATION MODEL
# ============================================================

class OTPVerification(models.Model):
    email           = models.EmailField()
    otp             = models.CharField(max_length=6)
    full_name       = models.CharField(max_length=150)
    hashed_password = models.CharField(max_length=255)
    created_at      = models.DateTimeField(auto_now_add=True)
    attempts        = models.PositiveIntegerField(default=0)
    is_used         = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'OTP Verification'

    def is_valid(self):
        """১০ মিনিটের মধ্যে valid।"""
        from datetime import timedelta
        return (
            not self.is_used
            and self.attempts < 5
            and timezone.now() < self.created_at + timedelta(minutes=10)
        )

    def __str__(self):
        return f"{self.email} — {self.otp}"


# ============================================================
# ✅ FIXED: AREA ADMIN MODEL  (top-level — OTPVerification এর বাইরে)
# ============================================================

class AreaAdmin(models.Model):
    admin_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='area_admin',
        null=True,          # ✅ এটা যোগ করো
        blank=True,         # ✅ এটা যোগ করো
        help_text="যে staff user কে এই এলাকার admin করা হবে"
    )
    area = models.CharField(
        max_length=50,
        choices=AREA_CHOICES,
        unique=True,
        default='',  # ✅ এটা যোগ করো
        help_text="এই admin কোন এলাকার দায়িত্বে আছেন"
    )

    phone      = models.CharField(max_length=20, blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


# ============================================================
# ✅ FIXED: VACCINE REQUEST MODEL  (top-level — OTPVerification এর বাইরে)
# ============================================================

class VaccineRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending',  'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='vaccine_requests'
    )
    family_member = models.ForeignKey(
        'FamilyMember', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vaccine_requests'
    )

    vaccine_name = models.CharField(max_length=200)
    preferred_date = models.DateField(null=True, blank=True, help_text="পছন্দের তারিখ")
    preferred_center = models.CharField(max_length=200, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    assigned_admin = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_vaccine_requests'
    )

    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.TextField(blank=True, null=True, help_text="Admin এর Response / Note")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Vaccine Request'
        verbose_name_plural = 'Vaccine Requests'

    def __str__(self):
        recipient = self.family_member.name if self.family_member else (
            self.user.get_full_name() or self.user.username
        )
        return f"{recipient} — {self.vaccine_name} [{self.status}]"

    def get_recipient_name(self):
        if self.family_member:
            return self.family_member.name
        return self.user.get_full_name() or self.user.username

    def get_user_area(self):
        """User এর এলাকা বের করো (Profile.area থেকে)।"""
        try:
            return self.user.profile.area or 'Central'
        except Exception:
            return 'Central'