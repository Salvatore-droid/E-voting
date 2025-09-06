from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.conf import settings
import re

class School(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    registration_format = models.CharField(max_length=200, help_text="Regex pattern for validating student IDs")
    color = models.CharField(max_length=7, default="#003366")  # Hex color for UI
    
    def __str__(self):
        return self.name
    
    def validate_student_id(self, student_id):
        """Validate if a student ID matches this school's format"""
        try:
            return re.match(self.registration_format, student_id) is not None
        except re.error:
            return False


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+254700000000'."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True
    )
    department = models.CharField(max_length=100, blank=True)
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    election_reminders = models.BooleanField(default=True)
    results_announcements = models.BooleanField(default=True)
    
    # Security Settings
    two_factor_auth = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"
    
    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return '/static/images/default.jpg'

class Election(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField(null=True, blank=True)  # Allow null temporarily for form
    end_date = models.DateTimeField(null=True, blank=True)    # Allow null temporarily for form
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.title
    
    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")
    
    @property
    def status(self):
        now = timezone.now()
        if not self.start_date or not self.end_date:
            return "Not Set"  # Handle case when dates are not set
        if now < self.start_date:
            return "Upcoming"
        elif self.start_date <= now <= self.end_date:
            return "Active"
        return "Completed"

class Position(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    is_required = models.BooleanField(default=True)
    max_votes = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['election', 'order']),
        ]

    def __str__(self):
        return f"{self.title} ({self.election})"

class Candidate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidacies')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    bio = models.TextField()
    manifesto = models.TextField()
    image = models.ImageField(upload_to='candidates/', blank=True, null=True)
    party = models.CharField(max_length=100, blank=True)
    course_year = models.CharField(max_length=100, blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='candidates', null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'position')
        indexes = [
            models.Index(fields=['position', 'is_approved']),
            models.Index(fields=['school']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"
    
    @property
    def votes_count(self):
        return self.votes.count()

    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url
    
    @property
    def approval_rating(self):
        total_votes = self.position.votes.count()
        return (self.votes_count / total_votes * 100) if total_votes > 0 else 0
    
    @property
    def initiatives_count(self):
        return self.manifesto.count('\n') + 1

class CandidateStat(models.Model):
    STAT_TYPES = (
        ('votes', 'Votes'),
        ('approval', 'Approval Rating'),
        ('views', 'Profile Views'),
    )
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='stats')
    stat_type = models.CharField(max_length=50, choices=STAT_TYPES)
    value = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['candidate', 'stat_type']),
        ]

    def __str__(self):
        return f"{self.candidate} - {self.stat_type}: {self.value}"

class Voter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='voter')
    student_id = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['student_id', 'is_verified']),
        ]

    def clean(self):
        if Voter.objects.filter(student_id=self.student_id).exclude(pk=self.pk).exists():
            raise ValidationError({'student_id': 'This student ID already exists.'})
    
    def __str__(self):
        return self.user.get_full_name()
    
    @classmethod
    def get_total_voters(cls):
        return cls.objects.filter(is_verified=True).count()

class Vote(models.Model):
    VOTE_STATUS_CHOICES = [
        ('verified', 'Verified'),
        ('pending', 'Pending Review'),
        ('disputed', 'Disputed'),
    ]
    
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='votes')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_abstained = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=VOTE_STATUS_CHOICES, default='verified')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=200, blank=True)
    vote_hash = models.CharField(max_length=64, unique=True, blank=True, null=True)
    transaction_id = models.CharField(max_length=66, blank=True, null=True)
    block_number = models.PositiveIntegerField(blank=True, null=True)
    is_verified_on_chain = models.BooleanField(default=False)
    
    
    class Meta:
        unique_together = ('voter', 'position', 'election')
        indexes = [
            models.Index(fields=['voter', 'election']),
            models.Index(fields=['candidate', 'election']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def clean(self):
        # Prevent voting for candidates outside voter's school
        if not self.is_abstained and self.candidate and self.voter:
            try:
                voter_school = self.voter.user.profile.school
                candidate_school = self.candidate.school
                
                if voter_school != candidate_school:
                    raise ValidationError("You can only vote for candidates from your own school.")
            except (UserProfile.DoesNotExist, AttributeError):
                raise ValidationError("Voter profile information is incomplete.")
    
    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)
    

    def __str__(self):
        if self.is_abstained:
            return f"{self.voter} abstained for {self.position}"
        return f"{self.voter} voted for {self.candidate} as {self.position}"

class ElectionAnalytics(models.Model):
    election = models.OneToOneField(Election, on_delete=models.CASCADE, related_name='analytics')
    total_voters = models.PositiveIntegerField(default=0)
    votes_cast = models.PositiveIntegerField(default=0)
    voter_turnout = models.FloatField(default=0)
    faculty_data = models.JSONField(default=dict)
    timeline_data = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['election']),
        ]

    def __str__(self):
        return f"Analytics for {self.election.title}"

class ResultDownload(models.Model):
    DOWNLOAD_TYPES = [
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Data'),
        ('summary', 'Executive Summary'),
    ]
    
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='downloads')
    download_type = models.CharField(max_length=10, choices=DOWNLOAD_TYPES)
    file = models.FileField(upload_to='results/downloads/')
    generated_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('election', 'download_type')
        indexes = [
            models.Index(fields=['election', 'download_type']),
        ]

    def __str__(self):
        return f"{self.get_download_type_display()} for {self.election.title}"

class ElectionTimelineEvent(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='timeline_events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateTimeField()
    icon = models.CharField(max_length=50, default='fas fa-calendar-alt')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['election', 'event_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.election.title}"