from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Election(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    @property
    def status(self):
        now = timezone.now()
        if now < self.start_date:
            return "Upcoming"
        elif self.start_date <= now <= self.end_date:
            return "Active"
        else:
            return "Completed"

class Position(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} ({self.election})"


class Candidate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    bio = models.TextField()
    manifesto = models.TextField()
    image = models.ImageField(upload_to='candidates/', blank=True, null=True)
    party = models.CharField(max_length=100, blank=True)
    course_year = models.CharField(max_length=100)
    is_featured = models.BooleanField(default=False)
    votes_count = models.PositiveIntegerField(default=0)
    approval_rating = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"
    
    @property
    def initiatives_count(self):
        return self.manifesto.count('\n') + 1

    
    # Add related_name to Vote model if not already present
    class Meta:
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
    
    
    
    _votes_count = models.PositiveIntegerField(default=0, db_column='votes_count')

    @property
    def votes_count(self):
        return self._votes_count

    @votes_count.setter
    def votes_count(self, value):
        self._votes_count = value
        self.save()

class CandidateStat(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='stats')
    stat_type = models.CharField(max_length=50)  # 'votes', 'approval', 'initiatives'
    value = models.FloatField()
    label = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.candidate} - {self.stat_type}: {self.value}"

class CandidateFilter(models.Model):
    name = models.CharField(max_length=100)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.name


class Voter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)
    has_voted = models.BooleanField(default=False)
    
    def clean(self):
        # Check for duplicate student_id before saving
        if Voter.objects.filter(student_id=self.student_id).exclude(pk=self.pk).exists():
            raise ValidationError({'student_id': 'This student ID already exists.'})
    
    def __str__(self):
        return self.user.get_full_name()

class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_abstained = models.BooleanField(default=False)

    class Meta:
        unique_together = ('voter', 'position', 'election')

    def __str__(self):
        if self.is_abstained:
            return f"{self.voter} abstained for {self.position}"
        return f"{self.voter} voted for {self.candidate} as {self.position}"