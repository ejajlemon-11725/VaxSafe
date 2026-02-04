# forms.py - Complete and Optimized (No changes required for Centers and News)
# The existing forms.py remains the same as provided
from django import forms
from .models import Profile, FamilyMember, Vaccine, Reminder
from django.utils import timezone
from django.core.exceptions import ValidationError


class ProfileForm(forms.ModelForm):
    """
    Form for user profile management
    """

    class Meta:
        model = Profile
        fields = ['mobile', 'gender', 'date_of_birth', 'profession', 'address', 'blood_group', 'photo']

        widgets = {
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter mobile number',
                'pattern': '[0-9+\\-\\s()]*'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter profession'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter complete address'
            }),
            'blood_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., A+, O-, AB+',
                'pattern': '(A|B|AB|O)[+-]'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

        labels = {
            'mobile': 'Mobile Number',
            'gender': 'Gender',
            'date_of_birth': 'Date of Birth',
            'profession': 'Profession',
            'address': 'Address',
            'blood_group': 'Blood Group',
            'photo': 'Profile Photo'
        }

        help_texts = {
            'mobile': 'Enter your contact number',
            'date_of_birth': 'Your date of birth',
            'blood_group': 'Format: A+, O-, AB+, etc.',
            'photo': 'Upload a profile picture (optional)'
        }

    def clean_mobile(self):
        """Validate mobile number"""
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            # Remove spaces and special characters for validation
            cleaned = mobile.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
            if not cleaned.isdigit():
                raise ValidationError('Mobile number should contain only digits and optional +, -, (, ) characters')
            if len(cleaned) < 10:
                raise ValidationError('Mobile number must be at least 10 digits')
        return mobile

    def clean_blood_group(self):
        """Validate blood group format"""
        blood_group = self.cleaned_data.get('blood_group')
        if blood_group:
            valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            if blood_group.upper() not in valid_groups:
                raise ValidationError('Please enter a valid blood group (A+, A-, B+, B-, AB+, AB-, O+, O-)')
            return blood_group.upper()
        return blood_group


class FamilyMemberForm(forms.ModelForm):
    """
    Form for adding/editing family members
    """

    class Meta:
        model = FamilyMember
        fields = [
            "name",
            "age",
            "date_of_birth",
            "gender",
            "relation",
            "blood_group",
            "vaccine_name",
            "date_time",
            "notification_type"
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'required': True
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Age',
                'min': '0',
                'max': '150'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'relation': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'blood_group': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., A+, O-',
                'pattern': '(A|B|AB|O)[+-]'
            }),
            'vaccine_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vaccine name (optional - legacy field)'
            }),
            'date_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'notification_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

        labels = {
            'name': 'Full Name',
            'age': 'Age',
            'date_of_birth': 'Date of Birth',
            'gender': 'Gender',
            'relation': 'Relationship',
            'blood_group': 'Blood Group',
            'vaccine_name': 'Vaccine Name (Legacy)',
            'date_time': 'Date & Time',
            'notification_type': 'Notification Type'
        }

        help_texts = {
            'name': 'Enter full name of family member',
            'age': 'Enter age (will be calculated from DOB if provided)',
            'date_of_birth': 'Select date of birth',
            'blood_group': 'Format: A+, O-, AB+, etc.',
            'vaccine_name': 'Legacy field - use Vaccine model for tracking vaccines',
        }

    def __init__(self, *args, **kwargs):
        super(FamilyMemberForm, self).__init__(*args, **kwargs)
        # Make fields optional
        optional_fields = [
            'age', 'date_of_birth', 'gender', 'blood_group',
            'vaccine_name', 'date_time', 'notification_type'
        ]
        for field in optional_fields:
            self.fields[field].required = False

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        age = cleaned_data.get('age')
        date_of_birth = cleaned_data.get('date_of_birth')

        # Validate that either age or DOB is provided
        if not age and not date_of_birth:
            raise ValidationError('Please provide either age or date of birth')

        return cleaned_data

    def clean_blood_group(self):
        """Validate blood group"""
        blood_group = self.cleaned_data.get('blood_group')
        if blood_group:
            valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            if blood_group.upper() not in valid_groups:
                raise ValidationError('Please enter a valid blood group')
            return blood_group.upper()
        return blood_group


class VaccineForm(forms.ModelForm):
    """
    Form for adding and editing vaccine records
    """

    class Meta:
        model = Vaccine
        fields = [
            'family_member',
            'name',
            'dose_number',
            'manufacturer',
            'batch_number',
            'date_administered',
            'next_dose_date',
            'location',
            'healthcare_provider',
            'status',
            'notes',
            'side_effects',
        ]

        widgets = {
            'family_member': forms.Select(attrs={
                'class': 'form-control',
            }),
            'name': forms.Select(attrs={
                'class': 'form-control',
            }),
            'dose_number': forms.Select(attrs={
                'class': 'form-control',
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Pfizer, Moderna, AstraZeneca',
            }),
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., AB12345',
            }),
            'date_administered': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'next_dose_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., City Hospital, Dhaka',
            }),
            'healthcare_provider': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Dr. Smith',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any additional notes...',
            }),
            'side_effects': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any side effects experienced...',
            }),
        }

        labels = {
            'family_member': 'For Family Member',
            'name': 'Vaccine Name',
            'dose_number': 'Dose Number',
            'manufacturer': 'Manufacturer',
            'batch_number': 'Batch/Lot Number',
            'date_administered': 'Date Administered',
            'next_dose_date': 'Next Dose Date',
            'location': 'Location',
            'healthcare_provider': 'Healthcare Provider',
            'status': 'Status',
            'notes': 'Additional Notes',
            'side_effects': 'Side Effects',
        }

        help_texts = {
            'family_member': 'Leave blank if this vaccine is for you',
            'name': 'Select the type of vaccine',
            'date_administered': 'Date when the vaccine was or will be given',
            'next_dose_date': 'Date for next dose (if applicable)',
            'batch_number': 'Optional: Batch or lot number from vaccine card',
            'side_effects': 'Optional: Any reactions or side effects',
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with user-specific family members"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter family members by current user
        if self.user:
            self.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=self.user
            ).order_by('name')
            self.fields['family_member'].empty_label = "Self (Me)"

        # Make certain fields optional
        optional_fields = [
            'family_member', 'manufacturer', 'batch_number',
            'next_dose_date', 'location', 'healthcare_provider',
            'notes', 'side_effects'
        ]
        for field in optional_fields:
            self.fields[field].required = False

        # Set default status for new records
        if not self.instance.pk:
            self.fields['status'].initial = 'Scheduled'

    def clean_date_administered(self):
        """Validate date_administered field"""
        date_administered = self.cleaned_data.get('date_administered')

        if date_administered:
            today = timezone.now().date()
            years_ago = (today - date_administered).days / 365

            # Check if date is too far in the past
            if years_ago > 100:
                raise ValidationError(
                    'The date seems too far in the past. Please check the date.'
                )

            # Check if date is too far in the future (more than 5 years)
            years_future = (date_administered - today).days / 365
            if years_future > 5:
                raise ValidationError(
                    'The date seems too far in the future. Please check the date.'
                )

        return date_administered

    def clean_next_dose_date(self):
        """Validate next_dose_date field"""
        next_dose_date = self.cleaned_data.get('next_dose_date')
        date_administered = self.cleaned_data.get('date_administered')

        # Next dose date should be after administered date
        if next_dose_date and date_administered:
            if next_dose_date <= date_administered:
                raise ValidationError(
                    'Next dose date must be after the administered date.'
                )

        return next_dose_date

    def clean(self):
        """Additional form-level validation"""
        cleaned_data = super().clean()
        date_administered = cleaned_data.get('date_administered')
        status = cleaned_data.get('status')

        # Auto-update status based on date
        if date_administered:
            today = timezone.now().date()

            # If date is in the past and status is scheduled, suggest overdue
            if date_administered < today and status == 'Scheduled':
                cleaned_data['status'] = 'Overdue'

        return cleaned_data


class ReminderForm(forms.ModelForm):
    """
    Form for creating reminders
    """

    class Meta:
        model = Reminder
        fields = ['vaccine_name', 'scheduled_datetime', 'family_member']

        widgets = {
            'vaccine_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vaccine name',
                'required': True
            }),
            'scheduled_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'family_member': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Family member name',
                'required': True
            }),
        }

        labels = {
            'vaccine_name': 'Vaccine Name',
            'scheduled_datetime': 'Reminder Date & Time',
            'family_member': 'Family Member'
        }

        help_texts = {
            'vaccine_name': 'Name of the vaccine',
            'scheduled_datetime': 'When should we remind you?',
            'family_member': 'Who is this reminder for?'
        }

    def clean_scheduled_datetime(self):
        """Validate that reminder is not in the past"""
        scheduled = self.cleaned_data.get('scheduled_datetime')

        if scheduled:
            if scheduled < timezone.now():
                raise ValidationError(
                    'Reminder date must be in the future.'
                )

        return scheduled