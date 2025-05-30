from django.urls import path
from . import views



urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('vote/', views.vote, name='vote'),
    path('vote/<int:candidate_id>/', views.vote_for_candidate, name='vote'),
    path('history/', views.history, name='history'),
    path('candidate/', views.candidate, name='candidate'),
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('results/', views.results, name='results'),
    path('settings/', views.settings, name='settings'),
    path('help/', views.help, name='help'),
    path('login/', views.login_view, name='login_view'),
    

]
