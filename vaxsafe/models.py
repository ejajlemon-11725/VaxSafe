# models.py - Complete and Optimized with Centers and News
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone


class Update(models.Model):
    """
    Model for system updates and announcements
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Update'
        verbose_name_plural = 'Updates'

    def __str__(self):
        return self.title


class Profile(models.Model):
    """
    Extended user profile information
    """
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    photo = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        """Get user's full name"""
        return self.user.get_full_name() or self.user.username


class FamilyMember(models.Model):
    """
    Model to store family member information for vaccination tracking
    """
    RELATIONSHIP_CHOICES = [
        ('Self', 'Self'),
        ('Spouse', 'Spouse'),
        ('Child', 'Child'),
        ('Parent', 'Parent'),
        ('Sibling', 'Sibling'),
        ('Grandparent', 'Grandparent'),
        ('Grandchild', 'Grandchild'),
        ('Other', 'Other'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]

    NOTIFICATION_CHOICES = [
        ("Email", "Email"),
        ("SMS", "SMS"),
        ("App Notification", "App Notification")
    ]

    # Core Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="family_members")
    name = models.CharField(max_length=100, help_text="Full name of family member")
    age = models.PositiveIntegerField(blank=True, null=True, help_text="Age (optional if DOB provided)")
    date_of_birth = models.DateField(blank=True, null=True, help_text="Date of birth")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    relation = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES, help_text="Relationship to user")
    blood_group = models.CharField(max_length=5, blank=True, null=True, help_text="Blood group (e.g., A+, O-)")

    # Legacy fields (keeping for backward compatibility)
    vaccine_name = models.CharField(max_length=100, blank=True, null=True,
                                    help_text="Legacy field - use Vaccine model instead")
    date_time = models.DateTimeField(blank=True, null=True, help_text="Legacy field")
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_CHOICES, blank=True, null=True)

    # Metadata
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
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year
            if today.month < self.date_of_birth.month or \
                    (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
                age -= 1
            return age
        return self.age  # Return manual age if DOB not set

    @property
    def display_age(self):
        """Get age for display"""
        calculated = self.calculate_age()
        if calculated:
            return calculated
        return self.age or "N/A"


class Vaccine(models.Model):
    """
    Model to store vaccine records for users and their family members
    """

    # Vaccine Type Choices
    VACCINE_TYPES = [
        ('COVID-19', 'COVID-19'),
        ('Influenza', 'Influenza (Flu)'),
        ('Hepatitis B', 'Hepatitis B'),
        ('Hepatitis A', 'Hepatitis A'),
        ('MMR', 'MMR (Measles, Mumps, Rubella)'),
        ('Polio', 'Polio'),
        ('DTP', 'DTP (Diphtheria, Tetanus, Pertussis)'),
        ('Varicella', 'Varicella (Chickenpox)'),
        ('HPV', 'HPV (Human Papillomavirus)'),
        ('Pneumococcal', 'Pneumococcal'),
        ('Meningococcal', 'Meningococcal'),
        ('Rotavirus', 'Rotavirus'),
        ('Rabies', 'Rabies'),
        ('Typhoid', 'Typhoid'),
        ('Yellow Fever', 'Yellow Fever'),
        ('Japanese Encephalitis', 'Japanese Encephalitis'),
        ('BCG', 'BCG (Tuberculosis)'),
        ('Other', 'Other'),
    ]

    # Dose Number Choices
    DOSE_CHOICES = [
        ('1st', '1st Dose'),
        ('2nd', '2nd Dose'),
        ('3rd', '3rd Dose'),
        ('Booster', 'Booster'),
        ('Single', 'Single Dose'),
    ]

    # Status Choices
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Overdue', 'Overdue'),
        ('Cancelled', 'Cancelled'),
    ]

    # Foreign Keys
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vaccines',
        help_text='The user who owns this vaccine record'
    )

    family_member = models.ForeignKey(
        'FamilyMember',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vaccines',
        help_text='The family member this vaccine is for (optional)'
    )

    # Vaccine Information
    name = models.CharField(
        max_length=100,
        choices=VACCINE_TYPES,
        help_text='Name of the vaccine'
    )

    dose_number = models.CharField(
        max_length=20,
        choices=DOSE_CHOICES,
        default='1st',
        help_text='Dose number (1st, 2nd, Booster, etc.)'
    )

    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Vaccine manufacturer (e.g., Pfizer, Moderna)'
    )

    batch_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Vaccine batch/lot number'
    )

    # Date Information
    date_administered = models.DateField(
        help_text='Date the vaccine was/will be administered'
    )

    next_dose_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date for the next dose (if applicable)'
    )

    # Location Information
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Location where vaccine was administered'
    )

    healthcare_provider = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Name of healthcare provider who administered the vaccine'
    )

    # Status and Notes
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Scheduled',
        help_text='Current status of the vaccination'
    )

    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes or side effects'
    )

    # Side Effects
    side_effects = models.TextField(
        blank=True,
        null=True,
        help_text='Any side effects experienced'
    )

    # Metadata
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
        """String representation of the vaccine"""
        if self.family_member:
            return f"{self.name} - {self.dose_number} for {self.family_member.name}"
        return f"{self.name} - {self.dose_number} for {self.user.get_full_name() or self.user.username}"

    def is_upcoming(self):
        """Check if vaccine is scheduled for future"""
        return self.date_administered > timezone.now().date()

    def is_overdue(self):
        """Check if vaccine is overdue"""
        return (
                self.status == 'Scheduled' and
                self.date_administered < timezone.now().date()
        )

    def days_until(self):
        """Calculate days until vaccine date"""
        delta = self.date_administered - timezone.now().date()
        return delta.days

    def get_recipient_name(self):
        """Get the name of the person receiving the vaccine"""
        if self.family_member:
            return self.family_member.name
        return self.user.get_full_name() or self.user.username


class Reminder(models.Model):
    """
    Model for vaccine reminders
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    vaccine_name = models.CharField(max_length=255, help_text="Name of vaccine")
    scheduled_datetime = models.DateTimeField(help_text="When to send reminder")
    family_member = models.CharField(max_length=255, help_text="Family member name")
    completed = models.BooleanField(default=False, help_text="Has the reminder been acknowledged")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        """Return Active / Missed / Completed"""
        if self.completed:
            return "Completed"
        elif self.scheduled_datetime < timezone.now():
            return "Missed"
        else:
            return "Active"

    @property
    def is_active(self):
        """Check if reminder is still active"""
        return not self.completed and self.scheduled_datetime >= timezone.now()

    @property
    def is_missed(self):
        """Check if reminder was missed"""
        return not self.completed and self.scheduled_datetime < timezone.now()

    def time_until(self):
        """Get human-readable time until reminder"""
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
        else:
            return "Soon"


# =====================================================
# NEW MODELS: VACCINATION CENTERS AND NEWS
# =====================================================

class VaccinationCenter(models.Model):
    """
    Model for vaccination centers/hospitals
    """
    CITY_CHOICES = [
        ('Dhaka', 'Dhaka'),
        ('Chittagong', 'Chittagong'),
        ('Sylhet', 'Sylhet'),
        ('Rajshahi', 'Rajshahi'),
        ('Khulna', 'Khulna'),
        ('Barisal', 'Barisal'),
        ('Rangpur', 'Rangpur'),
        ('Mymensingh', 'Mymensingh'),
    ]

    name = models.CharField(max_length=255, help_text="Name of the vaccination center")
    address = models.TextField(help_text="Full address of the center")
    city = models.CharField(max_length=50, choices=CITY_CHOICES, help_text="City where center is located")
    phone = models.CharField(max_length=20, blank=True, null=True, help_text="Contact phone number")
    email = models.EmailField(blank=True, null=True, help_text="Contact email")

    # Operating Hours
    opening_time = models.TimeField(blank=True, null=True, help_text="Opening time")
    closing_time = models.TimeField(blank=True, null=True, help_text="Closing time")

    # Services
    available_vaccines = models.TextField(
        blank=True,
        null=True,
        help_text="List of available vaccines (comma-separated)"
    )

    # Status
    is_active = models.BooleanField(default=True, help_text="Is the center currently operational?")

    # Location coordinates (optional, for map integration)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Longitude coordinate"
    )

    # Additional Info
    website = models.URLField(blank=True, null=True, help_text="Center's website URL")
    description = models.TextField(blank=True, null=True, help_text="Additional information about the center")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_centers'
    )

    class Meta:
        ordering = ['city', 'name']
        verbose_name = 'Vaccination Center'
        verbose_name_plural = 'Vaccination Centers'
        indexes = [
            models.Index(fields=['city', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

    def get_operating_hours(self):
        """Get formatted operating hours"""
        if self.opening_time and self.closing_time:
            return f"{self.opening_time.strftime('%I:%M %p')} - {self.closing_time.strftime('%I:%M %p')}"
        return "Not specified"

    def get_vaccines_list(self):
        """Get list of available vaccines"""
        if self.available_vaccines:
            return [v.strip() for v in self.available_vaccines.split(',')]
        return []


class News(models.Model):
    """
    Model for health and vaccination news/articles
    """
    CATEGORY_CHOICES = [
        ('General', 'General Health'),
        ('COVID-19', 'COVID-19'),
        ('Vaccines', 'Vaccines'),
        ('Research', 'Research & Studies'),
        ('Policy', 'Health Policy'),
        ('Awareness', 'Public Awareness'),
        ('Alert', 'Health Alert'),
    ]

    title = models.CharField(max_length=300, help_text="News headline")
    slug = models.SlugField(max_length=300, unique=True, blank=True, help_text="URL-friendly version of title")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')

    # Content
    summary = models.TextField(help_text="Brief summary of the news (200-300 words)")
    content = models.TextField(help_text="Full news article content")

    # Media
    image = models.ImageField(
        upload_to='news_images/',
        blank=True,
        null=True,
        help_text="Featured image for the news article"
    )

    # Source & Attribution
    source = models.CharField(max_length=200, blank=True, null=True, help_text="News source")
    source_url = models.URLField(blank=True, null=True, help_text="Link to original article")

    # Status
    is_published = models.BooleanField(default=True, help_text="Is this news published?")
    is_featured = models.BooleanField(default=False, help_text="Feature this news on homepage?")

    # Metadata
    published_date = models.DateTimeField(default=timezone.now, help_text="Publication date")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='news_articles'
    )

    # Engagement
    views = models.PositiveIntegerField(default=0, help_text="Number of views")

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
        """Auto-generate slug if not provided"""
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while News.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def increment_views(self):
        """Increment view count"""
        self.views += 1
        self.save(update_fields=['views'])

    def get_reading_time(self):
        """Calculate estimated reading time in minutes"""
        words = len(self.content.split())
        minutes = max(1, words // 200)  # Assuming 200 words per minute
        return f"{minutes} min read"