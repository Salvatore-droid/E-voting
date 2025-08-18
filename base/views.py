from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Election, Position, Candidate, Voter, Vote, UserProfile
from django.db.models import Count
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.generic import DetailView
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
import pandas as pd
from io import BytesIO
from django.db.models import Prefetch
from django.contrib.auth.models import User

@login_required(login_url='login_view')
def dashboard(request):
    now = timezone.now()
    election = Election.objects.filter(
        start_date__gte=now
    ).order_by('start_date').first()
    
    if not election:
        election = Election.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        ).first()
    
    total_voters = Voter.objects.count()
    verified_voters = Voter.objects.filter(is_verified=True).count()
    total_candidates = Candidate.objects.count()
    total_positions = Position.objects.count()
    
    context = {
        'election': election,
        'total_voters': total_voters,
        'verified_voters': verified_voters,
        'total_candidates': total_candidates,
        'total_positions': total_positions,
    }
    return render(request, 'base/dashboard.html', context)

@login_required
def vote(request):
    now = timezone.now()
    election = Election.objects.filter(
        start_date__lte=now,
        end_date__gte=now,
        is_active=True
    ).first()

    if not election:
        messages.warning(request, "There are no active elections at this time.")
        return redirect('/')

    try:
        voter = request.user.voter
        if not voter.is_verified:
            messages.error(request, "Your account is not yet verified to vote.")
            return redirect('settings')
            
        # Check if user has already voted in this election
        if voter.votes.filter(election=election).exists():
            messages.info(request, "You have already voted in this election.")
            return redirect('results')
            
    except Voter.DoesNotExist:
        messages.error(request, "You are not registered as a voter.")
        return redirect('settings')

    positions = Position.objects.filter(election=election).order_by('order')
    
    if request.method == 'POST':
        votes = {}
        abstentions = []
        has_errors = False
        
        # Validate all required positions have selections
        for position in positions:
            candidate_id = request.POST.get(f'position_{position.id}')
            
            if position.is_required and not candidate_id:
                messages.error(request, f"You must select a candidate or abstain for {position.title}")
                has_errors = True
                continue
                
            if candidate_id == 'abstain':
                abstentions.append(position)
            elif candidate_id:
                try:
                    candidate = Candidate.objects.get(id=candidate_id, position=position)
                    votes[position] = candidate
                except Candidate.DoesNotExist:
                    messages.error(request, f"Invalid candidate selected for {position.title}")
                    has_errors = True
        
        if has_errors:
            return redirect('vote')
        
        # Create votes if validation passed
        for position, candidate in votes.items():
            # Check if already voted for this position
            if not voter.votes.filter(position=position, election=election).exists():
                Vote.objects.create(
                    voter=voter,
                    candidate=candidate,
                    position=position,
                    election=election
                )
        
        for position in abstentions:
            # Check if already abstained for this position
            if not voter.votes.filter(position=position, election=election).exists():
                Vote.objects.create(
                    voter=voter,
                    position=position,
                    election=election,
                    is_abstained=True
                )

        messages.success(request, "Your vote has been successfully recorded!")
        return redirect('voting_receipt')

    context = {
        'election': election,
        'positions': positions,
        'voter': voter,
    }
    return render(request, 'base/voting.html', context)

@login_required
def candidate(request):
    active_election = Election.objects.filter(is_active=True).first()
    filters = Candidate.objects.filter()
    selected_filter = request.GET.get('filter')
    position_filter = request.GET.get('position')
    search_query = request.GET.get('search', '')
    
    candidates = Candidate.objects.filter(position__election=active_election)
    
    if selected_filter:
        candidates = candidates.filter(
            Q(position__title__icontains=selected_filter) |
            Q(party__icontains=selected_filter)
        )
    
    if position_filter:
        candidates = candidates.filter(position__id=position_filter)
    
    if search_query:
        candidates = candidates.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(course_year__icontains=search_query) |
            Q(bio__icontains=search_query) |
            Q(manifesto__icontains=search_query)
        )
    
    positions = Position.objects.filter(election=active_election).order_by('order')
    positions = positions.annotate(candidate_count=Count('candidates'))
    
    context = {
        'active_election': active_election,
        'candidates': candidates,  # Removed the featured_candidate exclusion
        'filters': filters,
        'positions': positions,
        'selected_filter': selected_filter,
        'position_filter': position_filter,
        'search_query': search_query,
    }
    return render(request, 'base/candidate.html', context)

@login_required
def candidate_detail(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    stats = candidate.stats.all()
    
    context = {
        'candidate': candidate,
        'stats': stats,
    }
    return render(request, 'base/detail.html', context)

@login_required
def vote_for_candidate(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    try:
        voter = request.user.voter
        if not voter.is_verified:
            messages.error(request, "Your account is not verified to vote.")
            return redirect('candidate')
            
        # Check if already voted for this position in this election
        if voter.votes.filter(position=candidate.position, election=candidate.position.election).exists():
            messages.warning(request, f"You have already voted for {candidate.position.title} position.")
            return redirect('candidate')
            
    except Voter.DoesNotExist:
        messages.error(request, "You are not registered as a voter.")
        return redirect('candidate')

    now = timezone.now()
    if not (candidate.position.election.start_date <= now <= candidate.position.election.end_date):
        messages.error(request, "Voting is not currently active for this election.")
        return redirect('candidate')
    
    if request.method == 'POST':
        Vote.objects.create(
            voter=voter,
            candidate=candidate,
            position=candidate.position,
            election=candidate.position.election
        )
        
        messages.success(request, f"You have successfully voted for {candidate.user.get_full_name()} as {candidate.position.title}!")
        return redirect('voting_receipt_with_candidate', candidate_id=candidate.id)
    
    context = {
        'candidate': candidate,
    }
    return render(request, 'base/confirm_vote.html', context)

@login_required
def voting_receipt(request):
    """Handle receipt without specific candidate"""
    try:
        voter = request.user.voter
        election = Election.objects.filter(is_active=True).first()
        votes = Vote.objects.filter(voter=voter, election=election).select_related('candidate', 'position')
        
        if not votes.exists():
            messages.warning(request, "You haven't voted in the current election.")
            return redirect('vote')
            
    except Voter.DoesNotExist:
        messages.error(request, "Voter information not found.")
        return redirect('dashboard')
    
    context = {
        'voter': voter,
        'election': election,
        'votes': votes,
    }
    return render(request, 'base/receipt.html', context)

@login_required
def voting_receipt_with_candidate(request, candidate_id):
    """Handle receipt for specific candidate"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    try:
        voter = request.user.voter
        vote = Vote.objects.get(candidate=candidate, voter=voter)
    except Voter.DoesNotExist:
        messages.error(request, "Voter information not found.")
        return redirect('dashboard')
    except Vote.DoesNotExist:
        messages.error(request, "No voting record found.")
        return redirect('candidate')
    
    context = {
        'candidate': candidate,
        'vote': vote,
    }
    return render(request, 'base/receipt.html', context)

def results(request):
    election = Election.objects.filter(
        end_date__lt=timezone.now()
    ).order_by('-end_date').first()
    
    if request.method == 'POST' and 'election_id' in request.POST:
        election = get_object_or_404(Election, id=request.POST['election_id'])
    
    if not election:
        return render(request, 'base/results.html', {
            'no_elections': True
        })
    
    elections = Election.objects.filter(
        end_date__lt=timezone.now()
    ).order_by('-end_date')
    
    positions = Position.objects.filter(election=election).annotate(
        total_votes=Count('votes')
    ).prefetch_related(
        Prefetch('candidates', queryset=Candidate.objects.annotate(
            vote_count=Count('votes')
        ).order_by('-vote_count')),
        'candidates__user'
    ).order_by('order')
    
    for position in positions:
        position.candidates_list = []
        for idx, candidate in enumerate(position.candidates.all(), start=1):
            candidate.rank = idx
            candidate.percentage = (candidate.vote_count / position.total_votes * 100) if position.total_votes > 0 else 0
            candidate.is_winner = idx == 1 and position.total_votes > 0
            position.candidates_list.append(candidate)
    
    total_voters = User.objects.filter(is_active=True, is_staff=False).count()
    votes_cast = Vote.objects.filter(election=election).values('voter').distinct().count()
    voter_turnout = (votes_cast / total_voters * 100) if total_voters > 0 else 0
    total_candidates = Candidate.objects.filter(position__election=election).count()
    
    context = {
        'election': election,
        'elections': elections,
        'positions': positions,
        'total_voters': total_voters,
        'votes_cast': votes_cast,
        'voter_turnout': round(voter_turnout, 1),
        'total_candidates': total_candidates,
    }
    return render(request, 'base/results.html', context)

def settings(request):
    return render(request, 'base/settings.html')

def help(request):
    return render(request, 'base/help.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Login successful')
            return redirect('/')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'base/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login_view')

def download_results(request, election_id, file_type):
    election = get_object_or_404(Election, id=election_id)
    
    positions = Position.objects.filter(election=election).annotate(
        total_votes=Count('votes')
    ).prefetch_related(
        Prefetch('candidates', queryset=Candidate.objects.annotate(
            vote_count=Count('votes')
        ).order_by('-vote_count')),
        'candidates__user'
    ).order_by('order')
    
    for position in positions:
        position.candidates_list = []
        for idx, candidate in enumerate(position.candidates.all(), start=1):
            candidate.rank = idx
            candidate.percentage = (candidate.vote_count / position.total_votes * 100) if position.total_votes > 0 else 0
            candidate.is_winner = idx == 1 and position.total_votes > 0
            position.candidates_list.append(candidate)
    
    if file_type == 'pdf':
        html_string = render_to_string('base/results_pdf.html', {
            'election': election,
            'positions': positions,
        })
        html = HTML(string=html_string)
        result = html.write_pdf()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{election.title}_results.pdf"'
        response.write(result)
        return response
    
    elif file_type == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for position in positions:
                data = {
                    'Candidate': [c.user.get_full_name() for c in position.candidates_list],
                    'Votes': [c.vote_count for c in position.candidates_list],
                    'Percentage': [f"{c.percentage:.1f}%" for c in position.candidates_list],
                    'Rank': [c.rank for c in position.candidates_list],
                }
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=position.title[:31], index=False)
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{election.title}_results.xlsx"'
        return response
    
    elif file_type == 'summary':
        summary_lines = [f"Election Results Summary - {election.title}\n\n"]
        for position in positions:
            summary_lines.append(f"{position.title}:\n")
            winner = next((c for c in position.candidates_list if c.is_winner), None)
            if winner:
                summary_lines.append(f"  Winner: {winner.user.get_full_name()} ({winner.vote_count} votes, {winner.percentage:.1f}%)\n")
            summary_lines.append(f"  Total Votes: {position.total_votes}\n\n")
        response = HttpResponse("\n".join(summary_lines), content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{election.title}_summary.txt"'
        return response
    
    return HttpResponse("Invalid file type", status=400)

@login_required(login_url='login_view')
def voting_history(request):
    try:
        # Try to get the voter record for the current user
        voter = Voter.objects.get(user=request.user)
    except Voter.DoesNotExist:
        messages.error(request, "You are not registered as a voter.")
        return redirect('dashboard')
    
    # Get the voter's voting history
    votes = Vote.objects.filter(voter=voter).select_related(
        'election', 'position', 'candidate', 'candidate__user'
    ).order_by('-timestamp')
    
    # Filtering logic
    search_query = request.GET.get('search', '')
    if search_query:
        votes = votes.filter(
            Q(election__title__icontains=search_query) |
            Q(position__title__icontains=search_query) |
            Q(candidate__user__first_name__icontains=search_query) |
            Q(candidate__user__last_name__icontains=search_query)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        votes = votes.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(votes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'votes': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': dict(Vote.VOTE_STATUS_CHOICES),
    }
    return render(request, 'base/history.html', context)

class VoteDetailView(DetailView):
    model = Vote
    template_name = 'base/vote_detail.html'
    context_object_name = 'vote'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'election', 'position', 'candidate', 'candidate__user', 'voter', 'voter__user'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context

# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .forms import ProfileForm, PasswordChangeForm, NotificationSettingsForm
from django.contrib.auth import update_session_auth_hash

@login_required
def settings(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
    
    # Initialize forms
    profile_form = ProfileForm(instance=profile, prefix='profile')
    password_form = PasswordChangeForm(user=request.user, prefix='password')
    notification_form = NotificationSettingsForm(instance=profile, prefix='notifications')
    
    # Handle form submissions
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, request.FILES, instance=profile, prefix='profile')
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('settings')
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST, prefix='password')
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important to keep user logged in
                profile.last_password_change = timezone.now()
                profile.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('settings')
        
        elif 'update_notifications' in request.POST:
            notification_form = NotificationSettingsForm(request.POST, instance=profile, prefix='notifications')
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Notification settings updated!')
                return redirect('settings')
        
        elif 'enable_2fa' in request.POST:
            profile.two_factor_auth = True
            profile.save()
            messages.success(request, 'Two-factor authentication enabled!')
            return redirect('settings')
        
        elif 'disable_2fa' in request.POST:
            profile.two_factor_auth = False
            profile.save()
            messages.success(request, 'Two-factor authentication disabled!')
            return redirect('settings')
    
    context = {
        'profile': profile,
        'profile_form': profile_form,
        'password_form': password_form,
        'notification_form': notification_form,
    }
    return render(request, 'base/settings.html', context)



    # views.py
from django.contrib.auth import logout
from django.contrib import messages

@login_required
def delete_account(request):
    if request.method == 'POST':
        # Optional: Add any confirmation logic here
        user = request.user
        logout(request)  # Log out the user before deleting
        user.delete()  # This will delete the user and their profile due to CASCADE
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('login_view')
    
    return render(request, 'base/confirm_delete.html')

# views.py
from django.contrib.auth import logout

@login_required
def revoke_session(request, session_key):
    if request.method == 'POST':
        try:
            session = Session.objects.get(session_key=session_key)
            # Verify the session belongs to the current user
            session_data = session.get_decoded()
            if str(request.user.id) == str(session_data.get('_auth_user_id')):
                session.delete()
                messages.success(request, 'Session revoked successfully.')
            else:
                messages.error(request, 'You cannot revoke this session.')
        except Session.DoesNotExist:
            messages.error(request, 'Session not found.')
    
    return redirect('active_sessions')

# views.py
from django.contrib.sessions.models import Session
from django.utils import timezone

@login_required
def active_sessions(request):
    # Get all active sessions for the current user
    sessions = Session.objects.filter(
        expire_date__gte=timezone.now()
    )
    
    user_sessions = []
    for session in sessions:
        session_data = session.get_decoded()
        if str(request.user.id) == str(session_data.get('_auth_user_id')):
            user_sessions.append({
                'session_key': session.session_key,
                'ip': session_data.get('ip', 'Unknown'),
                'user_agent': session_data.get('user_agent', 'Unknown'),
                'last_activity': session.expire_date
            })
    
    context = {
        'active_sessions': user_sessions,
        'current_session_key': request.session.session_key
    }
    return render(request, 'base/active_sessions.html', context)