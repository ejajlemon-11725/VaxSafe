# forms.py - Fixed & Clean
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Profile, FamilyMember, Vaccine, Reminder,
    FamilyGroup, FamilyGroupMember, FamilyInvitation,
    VaccineReminder, VaccineSchedule,
    VaccineRequest,   # ✅ FIXED: import যোগ করা হয়েছে
)


# ============================================================
# PROFILE FORM
# ============================================================

class ProfileForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address',
        }),
        label='Email Address'
    )

    class Meta:
        model  = Profile
        # ✅ FIXED: 'area' field যোগ করা হয়েছে
        fields = ['mobile', 'gender', 'date_of_birth', 'profession',
                  'address', 'blood_group', 'photo', 'area']
        widgets = {
            'mobile': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Enter mobile number',
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Enter profession'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Enter complete address'
            }),
            'blood_group': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., A+, O-, AB+',
            }),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            # ✅ FIXED: area widget যোগ করা হয়েছে
            'area': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'mobile':        'Mobile Number',
            'gender':        'Gender',
            'date_of_birth': 'Date of Birth',
            'profession':    'Profession',
            'address':       'Address',
            'blood_group':   'Blood Group',
            'photo':         'Profile Photo',
            'area':          'আপনার এলাকা',   # ✅ FIXED
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['email'].initial = user.email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            cleaned = ''.join(c for c in mobile if c.isdigit())
            if len(cleaned) < 10:
                raise ValidationError('Mobile number must be at least 10 digits')
        return mobile

    def clean_blood_group(self):
        blood_group = self.cleaned_data.get('blood_group')
        if blood_group:
            valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            if blood_group.upper() not in valid_groups:
                raise ValidationError('Please enter a valid blood group (A+, A-, B+, B-, AB+, AB-, O+, O-)')
            return blood_group.upper()
        return blood_group


# ============================================================
# FAMILY MEMBER FORM
# ============================================================

class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model  = FamilyMember
        fields = [
            'name', 'age', 'date_of_birth', 'gender',
            'relation', 'blood_group',
            'vaccine_name', 'date_time', 'notification_type',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Full Name', 'required': True
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Age', 'min': '0', 'max': '150'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'gender':   forms.Select(attrs={'class': 'form-control'}),
            'relation': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'blood_group': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., A+, O-',
            }),
            'vaccine_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Vaccine name (optional - legacy field)'
            }),
            'date_time': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
            'notification_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Full Name', 'age': 'Age', 'date_of_birth': 'Date of Birth',
            'gender': 'Gender', 'relation': 'Relationship', 'blood_group': 'Blood Group',
            'vaccine_name': 'Vaccine Name (Legacy)', 'date_time': 'Date & Time',
            'notification_type': 'Notification Type',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional = [
            'age', 'date_of_birth', 'gender', 'blood_group',
            'vaccine_name', 'date_time', 'notification_type',
        ]
        for field in optional:
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('age') and not cleaned_data.get('date_of_birth'):
            raise ValidationError('Please provide either age or date of birth')
        return cleaned_data

    def clean_blood_group(self):
        blood_group = self.cleaned_data.get('blood_group')
        if blood_group:
            valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            if blood_group.upper() not in valid_groups:
                raise ValidationError('Please enter a valid blood group')
            return blood_group.upper()
        return blood_group


# ============================================================
# VACCINE FORM
# ============================================================

class VaccineForm(forms.ModelForm):
    class Meta:
        model  = Vaccine
        fields = [
            'family_member', 'name', 'dose_number', 'manufacturer',
            'batch_number', 'date_administered', 'next_dose_date',
            'location', 'healthcare_provider', 'status', 'notes', 'side_effects',
        ]
        widgets = {
            'family_member':       forms.Select(attrs={'class': 'form-control'}),
            'name':                forms.Select(attrs={'class': 'form-control'}),
            'dose_number':         forms.Select(attrs={'class': 'form-control'}),
            'manufacturer':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Pfizer, Moderna'}),
            'batch_number':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., AB12345'}),
            'date_administered':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_dose_date':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., City Hospital, Dhaka'}),
            'healthcare_provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Dr. Smith'}),
            'status':              forms.Select(attrs={'class': 'form-control'}),
            'notes':               forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'side_effects':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'family_member': 'For Family Member', 'name': 'Vaccine Name',
            'dose_number': 'Dose Number', 'manufacturer': 'Manufacturer',
            'batch_number': 'Batch/Lot Number', 'date_administered': 'Date Administered',
            'next_dose_date': 'Next Dose Date', 'location': 'Location',
            'healthcare_provider': 'Healthcare Provider', 'status': 'Status',
            'notes': 'Additional Notes', 'side_effects': 'Side Effects',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        from .models import CustomVaccineType
        custom_choices = [
            (ct.name, ct.name)
            for ct in CustomVaccineType.objects.filter(is_active=True)
        ]
        all_choices = list(Vaccine.VACCINE_TYPES) + custom_choices
        self.fields['name'].widget = forms.Select(
            attrs={'class': 'form-control'},
            choices=all_choices
        )
        self.fields['name'].choices = all_choices

        if self.user:
            self.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=self.user
            ).order_by('name')
            self.fields['family_member'].empty_label = "Self (Me)"

        optional = [
            'family_member', 'manufacturer', 'batch_number',
            'next_dose_date', 'location', 'healthcare_provider',
            'notes', 'side_effects',
        ]
        for field in optional:
            self.fields[field].required = False

        if not self.instance.pk:
            self.fields['status'].initial = 'Scheduled'

    def clean_date_administered(self):
        date_administered = self.cleaned_data.get('date_administered')
        if date_administered:
            today = timezone.now().date()
            if (today - date_administered).days / 365 > 100:
                raise ValidationError('The date seems too far in the past.')
            if (date_administered - today).days / 365 > 5:
                raise ValidationError('The date seems too far in the future.')
        return date_administered

    def clean_next_dose_date(self):
        next_dose_date    = self.cleaned_data.get('next_dose_date')
        date_administered = self.cleaned_data.get('date_administered')
        if next_dose_date and date_administered and next_dose_date <= date_administered:
            raise ValidationError('Next dose date must be after the administered date.')
        return next_dose_date

    def clean(self):
        cleaned_data      = super().clean()
        date_administered = cleaned_data.get('date_administered')
        status            = cleaned_data.get('status')
        if date_administered and date_administered < timezone.now().date() and status == 'Scheduled':
            cleaned_data['status'] = 'Overdue'
        return cleaned_data


# ============================================================
# REMINDER FORM  (পুরনো Reminder model এর জন্য)
# ============================================================

class ReminderForm(forms.ModelForm):
    class Meta:
        model  = Reminder
        fields = ['vaccine_name', 'scheduled_datetime', 'family_member']
        widgets = {
            'vaccine_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Vaccine name', 'required': True
            }),
            'scheduled_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local', 'required': True
            }),
            'family_member': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Family member name', 'required': True
            }),
        }
        labels = {
            'vaccine_name':       'Vaccine Name',
            'scheduled_datetime': 'Reminder Date & Time',
            'family_member':      'Family Member',
        }

    def clean_scheduled_datetime(self):
        scheduled = self.cleaned_data.get('scheduled_datetime')
        if scheduled and scheduled < timezone.now():
            raise ValidationError('Reminder date must be in the future.')
        return scheduled


# ============================================================
# VACCINE APPLICATION FORM
# ============================================================

class VaccineApplicationForm(forms.ModelForm):
    vaccine_schedule = forms.ModelChoiceField(
        queryset=VaccineSchedule.objects.filter(is_active=True).order_by('vaccine_name', 'dose_number'),
        empty_label="— টিকা সিলেক্ট করুন —",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_vaccine_schedule'}),
        label='টিকার নাম ও ডোজ'
    )

    class Meta:
        model  = Vaccine
        fields = [
            'family_member', 'vaccine_schedule',
            'date_administered', 'location', 'healthcare_provider', 'notes',
        ]
        widgets = {
            'family_member':       forms.Select(attrs={'class': 'form-control'}),
            'date_administered':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'যেমন: ঢাকা মেডিকেল'}),
            'healthcare_provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ডাক্তারের নাম'}),
            'notes':               forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'family_member':       'কার জন্য? (নিজের জন্য ফাঁকা রাখুন)',
            'date_administered':   '১ম ডোজের তারিখ',
            'location':            'কোথায় নিয়েছেন',
            'healthcare_provider': 'ডাক্তার / স্বাস্থ্যকর্মী',
            'notes':               'অতিরিক্ত নোট',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=self.user
            ).order_by('name')
            self.fields['family_member'].empty_label = "নিজের জন্য (Self)"

        for f in ['family_member', 'location', 'healthcare_provider', 'notes']:
            self.fields[f].required = False


# ============================================================
# FAMILY GROUP FORMS
# ============================================================

class FamilyCreateForm(forms.ModelForm):
    class Meta:
        model  = FamilyGroup
        fields = ['family_name']
        widgets = {
            'family_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'যেমন: Rahman Family'
            })
        }


class FamilyInviteForm(forms.Form):
    ROLE_CHOICES = [('Member', 'Member'), ('Guardian', 'Guardian')]

    email    = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role     = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    relation = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Spouse / Son / Father...'})
    )


class AdminTransferForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def __init__(self, family, current_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        eligible = FamilyGroupMember.objects.filter(
            family=family, is_active=True
        ).exclude(user=current_user)
        self.fields['new_admin'] = forms.ModelChoiceField(
            queryset=eligible,
            widget=forms.Select(attrs={'class': 'form-select'})
        )


# ============================================================
# VACCINE REMINDER FORM
# ============================================================

class VaccineReminderForm(forms.ModelForm):
    class Meta:
        model  = VaccineReminder
        fields = ['vaccine_name', 'reminder_date', 'reminder_time', 'note']
        widgets = {
            'vaccine_name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'ভ্যাকসিনের নাম লিখুন'
            }),
            'reminder_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date'
            }),
            'reminder_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type':  'time'
            }),
            'note': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        3,
                'placeholder': 'অতিরিক্ত নোট (ঐচ্ছিক)'
            }),
        }
        labels = {
            'vaccine_name':  'ভ্যাকসিনের নাম',
            'reminder_date': 'তারিখ',
            'reminder_time': 'সময়',
            'note':          'নোট',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['note'].required = False

    def clean_reminder_date(self):
        date = self.cleaned_data.get('reminder_date')
        if date and date < timezone.now().date():
            raise ValidationError('রিমাইন্ডারের তারিখ অবশ্যই ভবিষ্যতে হতে হবে।')
        return date


# ============================================================
# ✅ FIXED: VACCINE REQUEST FORM  (top-level — VaccineReminderForm এর বাইরে)
# ============================================================

class VaccineRequestForm(forms.ModelForm):
    class Meta:
        model  = VaccineRequest
        fields = [
            'family_member', 'vaccine_name',
            'preferred_date', 'preferred_center', 'note',
        ]
        widgets = {
            'family_member': forms.Select(attrs={
                'class': 'form-control'
            }),
            'vaccine_name': forms.Select(attrs={
                'class': 'form-control'
            }),
            'preferred_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
            'preferred_center': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'যেমন: ঢাকা মেডিকেল, Farmgate Health Center (ঐচ্ছিক)',
            }),
            'note': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        3,
                'placeholder': 'অতিরিক্ত তথ্য বা অনুরোধ লিখুন (ঐচ্ছিক)',
            }),
        }
        labels = {
            'family_member':   'কার জন্য? (নিজের জন্য ফাঁকা রাখুন)',
            'vaccine_name':    'ভ্যাকসিনের নাম',
            'preferred_date':  'পছন্দের তারিখ',
            'preferred_center':'কেন্দ্রের নাম (ঐচ্ছিক)',
            'note':            'নোট / বিশেষ অনুরোধ',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['vaccine_name'].widget = forms.Select(
            attrs={'class': 'form-control'},
            choices=[('', '— ভ্যাকসিন সিলেক্ট করুন —')] + list(Vaccine.VACCINE_TYPES)
        )
        self.fields['vaccine_name'].choices = (
            [('', '— ভ্যাকসিন সিলেক্ট করুন —')] + list(Vaccine.VACCINE_TYPES)
        )

        if self.user:
            self.fields['family_member'].queryset = FamilyMember.objects.filter(
                user=self.user
            ).order_by('name')
            self.fields['family_member'].empty_label = "নিজের জন্য (Self)"

        for f in ['family_member', 'preferred_center', 'note']:
            self.fields[f].required = False

    def clean_preferred_date(self):
        date = self.cleaned_data.get('preferred_date')
        if date and date < timezone.now().date():
            raise ValidationError('পছন্দের তারিখ অবশ্যই ভবিষ্যতে হতে হবে।')
        return date