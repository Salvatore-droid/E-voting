# In admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import *


# Define an inline admin for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'school', 'phone_number')
    search_fields = ('user__username', 'student_id', 'school__name')
    list_filter = ('school', 'department')
    autocomplete_fields = ('user', 'school')

# Extend the default UserAdmin to include UserProfile
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_full_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_format')
    search_fields = ['name']
    list_filter = ('name',)


# Election Admin
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'get_status', 'is_active', 'created_at')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    readonly_fields = ('created_at',)  # Remove 'status' from readonly_fields
    
    def get_status(self, obj):
        return obj.status
    get_status.short_description = 'Status'

# Position Admin
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'election', 'is_required', 'order')
    list_filter = ('election', 'is_required')
    search_fields = ('title', 'description')
    ordering = ('election', 'order')

# Candidate Admin
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'school', 'is_approved')
    search_fields = ('user__username', 'position__title', 'school__name')
    list_filter = ('school', 'position', 'is_approved')
    autocomplete_fields = ('user', 'position', 'school')
    
    def get_queryset(self, request):
        # For non-superusers, only show candidates from their school
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            if hasattr(request.user, 'profile') and request.user.profile.school:
                return qs.filter(school=request.user.profile.school)
        except UserProfile.DoesNotExist:
            pass
        return qs.none()

# Voter Admin
class VoterAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'is_verified')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id')
    raw_id_fields = ()  # Updated as per previous fix
    actions = ['mark_as_verified', 'mark_as_unverified']
    
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_as_verified.short_description = "Mark selected voters as verified"
    
    def mark_as_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    mark_as_unverified.short_description = "Mark selected voters as unverified"

# Vote Admin
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'candidate', 'position', 'election', 'status', 'timestamp', 'is_abstained')
    list_filter = ('status', 'is_abstained', 'position__election', 'position')
    search_fields = ('voter__user__username', 'voter__user__first_name', 'voter__user__last_name', 
                    'candidate__user__username', 'candidate__user__first_name', 'candidate__user__last_name')
    raw_id_fields = ('voter', 'candidate', 'position', 'election')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

# Election Analytics Admin
class ElectionAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('election', 'last_updated')
    readonly_fields = ('last_updated',)
    raw_id_fields = ('election',)

# Result Download Admin
class ResultDownloadAdmin(admin.ModelAdmin):
    list_display = ('election', 'download_type', 'generated_at', 'download_count')
    list_filter = ('download_type',)
    readonly_fields = ('generated_at', 'download_count')
    raw_id_fields = ('election',)

# Election Timeline Event Admin
class ElectionTimelineEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'election', 'event_date', 'order')
    list_filter = ('election',)
    search_fields = ('title', 'description')
    raw_id_fields = ('election',)
    ordering = ('election', 'order')

# Register models
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Election, ElectionAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(CandidateStat)
admin.site.register(Voter, VoterAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(ElectionAnalytics, ElectionAnalyticsAdmin)
admin.site.register(ResultDownload, ResultDownloadAdmin)
admin.site.register(ElectionTimelineEvent, ElectionTimelineEventAdmin)