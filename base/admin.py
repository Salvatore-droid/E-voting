from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Election, Position, Candidate, Voter, Vote
from django.utils import timezone
from django.utils.html import format_html

from django.utils.safestring import mark_safe

# Unregister the default User admin
admin.site.unregister(User)

# Custom User Admin with Voter inline
class VoterInline(admin.StackedInline):
    model = Voter
    can_delete = False
    verbose_name_plural = 'Voter Profile'
    extra = 1  # Only show one empty form
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Only show the inline when editing an existing user
        if obj is None:
            formset.max_num = 0
        return formset

class CustomUserAdmin(UserAdmin):
    inlines = (VoterInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_voter')
    
    def is_voter(self, instance):
        return hasattr(instance, 'voter')
    is_voter.boolean = True
    is_voter.short_description = 'Is Voter'

# Unregister the default User admin and register our custom one

admin.site.register(User, CustomUserAdmin)

# Candidate Inline for Position
class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 1
    fields = ('user', 'bio', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return obj.image.url if obj.image else "No image"
        return "No image"
    image_preview.short_description = 'Image Preview'

# Position Admin
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'election', 'candidates_count')
    list_filter = ('election',)
    search_fields = ('title', 'description')
    inlines = (CandidateInline,)
    
    def candidates_count(self, obj):
        return obj.candidate_set.count()
    candidates_count.short_description = 'Candidates'

# Election Admin
class PositionInline(admin.TabularInline):
    model = Position
    extra = 1
    fields = ('title', 'description')

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'status', 'positions_count', 'voters_count')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'
    inlines = (PositionInline,)
    actions = ['activate_elections', 'deactivate_elections']
    
    def positions_count(self, obj):
        return obj.position_set.count()
    positions_count.short_description = 'Positions'
    
    def voters_count(self, obj):
        return Vote.objects.filter(election=obj).values('voter').distinct().count()
    voters_count.short_description = 'Voters'
    
    def status(self, obj):
        now = timezone.now()
        if now < obj.start_date:
            return "Upcoming"
        elif obj.start_date <= now <= obj.end_date:
            return "Active" if obj.is_active else "Inactive"
        else:
            return "Completed"
    status.short_description = 'Status'
    
    @admin.action(description='Activate selected elections')
    def activate_elections(self, request, queryset):
        queryset.update(is_active=True)
    
    @admin.action(description='Deactivate selected elections')
    def deactivate_elections(self, request, queryset):
        queryset.update(is_active=False)

# Candidate Admin
# admin.py
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'position', 'election', 'votes_count_display', 'image_preview')
    list_filter = ('position__election', 'position')
    search_fields = ('user__first_name', 'user__last_name', 'position__title')
    readonly_fields = ('image_preview', 'votes_count_display')
    fields = ('user', 'position', 'bio', 'manifesto', 'image', 'image_preview', 'votes_count_display')
    
    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Candidate'
    user_full_name.admin_order_field = 'user__first_name'
    
    def election(self, obj):
        return obj.position.election
    election.short_description = 'Election'
    election.admin_order_field = 'position__election'
    
    def votes_count_display(self, obj):
        return obj.votes_count
    votes_count_display.short_description = 'Votes'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Preview'


# Vote Admin
@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter_info', 'candidate_info', 'position', 'election', 'timestamp')
    list_filter = ('election', 'position')
    search_fields = ('voter__user__first_name', 'voter__user__last_name', 
                    'candidate__user__first_name', 'candidate__user__last_name')
    date_hierarchy = 'timestamp'
    
    def voter_info(self, obj):
        return f"{obj.voter.user.get_full_name()} ({obj.voter.student_id})"
    voter_info.short_description = 'Voter'
    
    def candidate_info(self, obj):
        return obj.candidate.user.get_full_name()
    candidate_info.short_description = 'Candidate'

# Voter Admin
@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'student_id', 'is_verified', 'has_voted', 'votes_count')
    list_filter = ('is_verified', 'has_voted')
    search_fields = ('user__first_name', 'user__last_name', 'student_id')
    actions = ['verify_voters', 'unverify_voters']
    
    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Voter'
    
    def votes_count(self, obj):
        return obj.vote_set.count()
    votes_count.short_description = 'Votes Cast'
    
    @admin.action(description='Verify selected voters')
    def verify_voters(self, request, queryset):
        queryset.update(is_verified=True)
    
    @admin.action(description='Unverify selected voters')
    def unverify_voters(self, request, queryset):
        queryset.update(is_verified=False)