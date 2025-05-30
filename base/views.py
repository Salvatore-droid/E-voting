from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Election, Position, Candidate, Voter, Vote
from django.db.models import Count
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q
from .models import Election, Position, Candidate, CandidateFilter





# Create your views here.
@login_required(login_url='login_view')
def dashboard(request):
    # Get the upcoming or active election
    now = timezone.now()
    election = Election.objects.filter(
        start_date__gte=now
    ).order_by('start_date').first()
    
    if not election:
        election = Election.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        ).first()
    
    # Statistics
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
    # Get current active election
    now = timezone.now()
    election = Election.objects.filter(
        start_date__lte=now,
        end_date__gte=now,
        is_active=True
    ).first()

    if not election:
        messages.warning(request, "There are no active elections at this time.")
        return redirect('home')

    # Check if user is a verified voter
    try:
        voter = request.user.voter
        if not voter.is_verified:
            messages.error(request, "Your account is not yet verified to vote.")
            return redirect('profile')
        if voter.has_voted:
            messages.info(request, "You have already voted in this election.")
            return redirect('results')
    except Voter.DoesNotExist:
        messages.error(request, "You are not registered as a voter.")
        return redirect('profile')

    # Get all positions and candidates
    positions = Position.objects.filter(election=election).order_by('order')
    candidates = Candidate.objects.filter(position__election=election).select_related('position', 'user')

    if request.method == 'POST':
        # Process voting form
        votes = {}
        abstentions = []
        
        for position in positions:
            candidate_id = request.POST.get(f'position_{position.id}')
            if candidate_id:
                if candidate_id == 'abstain':
                    abstentions.append(position)
                else:
                    try:
                        candidate = Candidate.objects.get(id=candidate_id)
                        votes[position] = candidate
                    except Candidate.DoesNotExist:
                        pass

        # Save votes
        for position, candidate in votes.items():
            Vote.objects.create(
                voter=voter,
                candidate=candidate,
                position=position,
                election=election
            )

        # Save abstentions
        for position in abstentions:
            Vote.objects.create(
                voter=voter,
                position=position,
                election=election,
                is_abstained=True
            )

        # Mark voter as voted
        voter.has_voted = True
        voter.save()

        messages.success(request, "Your vote has been successfully recorded!")
        return redirect('voting_receipt')

    context = {
        'election': election,
        'positions': positions,
        'candidates': candidates,
        'voter': voter,
    }
    return render(request, 'base/voting.html', context)

@login_required
def voting_receipt(request):
    try:
        voter = request.user.voter
        election = Election.objects.filter(is_active=True).first()
        votes = Vote.objects.filter(voter=voter, election=election).select_related('candidate', 'position')
        
        if not votes.exists():
            messages.warning(request, "You haven't voted in the current election.")
            return redirect('voting_page')
            
    except (Voter.DoesNotExist, AttributeError):
        messages.error(request, "Voter information not found.")
        return redirect('home')
    
    context = {
        'voter': voter,
        'election': election,
        'votes': votes,
    }
    return render(request, 'base/receipt.html', context)

def history(request):
    return render(request, 'base/history.html')


@login_required
def candidate(request):
    # Get active election
    active_election = Election.objects.filter(is_active=True).first()
    
    # Get all filters
    filters = CandidateFilter.objects.filter(is_active=True)
    
    # Get selected filter from request
    selected_filter = request.GET.get('filter')
    position_filter = request.GET.get('position')
    search_query = request.GET.get('search', '')
    
    # Get all candidates for active election
    candidates = Candidate.objects.filter(position__election=active_election)
    
    # Apply filters
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
    
    # Get featured candidate
    featured_candidate = candidates.filter(is_featured=True).first()
    
    # Get all positions for filter tabs
    positions = Position.objects.filter(election=active_election).order_by('order')
    
    # Annotate with candidate count
    positions = positions.annotate(candidate_count=Count('candidates'))
    
    context = {
        'active_election': active_election,
        'featured_candidate': featured_candidate,
        'candidates': candidates.exclude(id=featured_candidate.id if featured_candidate else None),
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

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import Election, Position, Candidate, Vote, Voter
from django.db import IntegrityError
# ... your existing candidate and candidate_detail views ...

@login_required
def vote_for_candidate(request, candidate_id):
    # Get the candidate
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    # Check if user is a verified voter
    try:
        voter = request.user.voter
        if not voter.is_verified:
            messages.error(request, "Your account is not verified to vote.")
            return redirect('candidate')
            
        if voter.has_voted:
            messages.warning(request, "You have already voted in this election.")
            return redirect('candidate')
            
    except Voter.DoesNotExist:
        messages.error(request, "You are not registered as a voter.")
        return redirect('candidate')
    try:
        # Check if vote already exists
        existing_vote = Vote.objects.filter(
            voter=voter,
            position=candidate.position,
            election=candidate.position.election
        ).exists()
        
        if existing_vote:
            messages.error(request, "You have already voted for this position.")
            return redirect('candidate')
            
        # Create new vote if none exists
        Vote.objects.create(
            voter=voter,
            candidate=candidate,
            position=candidate.position,
            election=candidate.position.election
        )
        messages.success(request, "Vote recorded successfully!")
        return redirect('some_success_url')
        
    except IntegrityError:
        messages.error(request, "You have already voted for this position.")
        return redirect('some_redirect_url')
    # Check if election is active
    now = timezone.now()
    if not (candidate.position.election.start_date <= now <= candidate.position.election.end_date):
        messages.error(request, "Voting is not currently active for this election.")
        return redirect('candidate')
    
    if request.method == 'POST':
        # Create the vote
        Vote.objects.create(
            voter=voter,
            candidate=candidate,
            position=candidate.position,
            election=candidate.position.election
        )
        
        # Update candidate vote count
        Candidate.objects.filter(id=candidate.id).update(votes_count=models.F('votes_count') + 1)
        
        # Mark voter as voted
        voter.has_voted = True
        voter.save()
        
        messages.success(request, f"You have successfully voted for {candidate.user.get_full_name()} as {candidate.position.title}!")
        return redirect('voting_receipt', candidate_id=candidate.id)
    
    context = {
        'candidate': candidate,
    }
    return render(request, 'base/confirm_vote.html', context)

@login_required
def voting_receipt(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    try:
        vote = Vote.objects.get(candidate=candidate, voter=request.user.voter)
    except Vote.DoesNotExist:
        messages.error(request, "No voting record found.")
        return redirect('candidate')
    
    context = {
        'candidate': candidate,
        'vote': vote,
    }
    return render(request, 'base/receipt.html', context)


def results(request):
    now = timezone.now()
    election = Election.objects.filter(
        end_date__lte=now
    ).order_by('-end_date').first()
    
    if not election:
        return render(request, 'voting/no_results.html')
    
    # Get vote counts per candidate for each position
    positions = Position.objects.filter(election=election).annotate(
        total_votes=Count('candidates__votes')
    ).prefetch_related(
        'candidates',
        'candidates__votes'
    )
    
    context = {
        'election': election,
        'positions': positions,
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