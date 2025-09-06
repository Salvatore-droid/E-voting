from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import VoteDetailView



urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('vote/', views.vote, name='vote'),
    path('vote/<int:candidate_id>/', views.vote_for_candidate, name='vote'),
    path('vote/<int:pk>/', VoteDetailView.as_view(), name='vote_detail'),
    path('receipt/', views.voting_receipt, name='voting_receipt'),
    path('receipt/<int:candidate_id>/', views.voting_receipt_with_candidate, name='voting_receipt_with_candidate'),
    path('history/', views.voting_history, name='voting_history'),
    path('candidate/', views.candidate, name='candidate'),
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('results/', views.results, name='results'),
    path('results/download/<int:election_id>/<str:file_type>/', views.download_results, name='download_results'),
    path('help/', views.help, name='help'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),

    path('settings/', views.settings, name='settings'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
    path('settings/active-sessions/', views.active_sessions, name='active_sessions'),
    path('settings/revoke-session/<str:session_key>/', views.revoke_session, name='revoke_session'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
    template_name='base/password_reset.html',
    email_template_name='base/password_reset_email.html',
    subject_template_name='password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='base/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='base/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='base/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('select-school/', views.select_school, name='select_school'),
    
]
