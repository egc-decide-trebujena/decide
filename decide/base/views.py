from django.shortcuts import render
from voting import models as voting_models
from census import models as census_models

def main_page(request):
    is_anonymous = request.user.is_anonymous
    is_staff = request.user.is_staff
    allowed_votings = census_models.Census.objects.filter(voter_id=request.user.pk).values('voting_id')

    voting_votings = voting_models.Voting.objects.filter(end_date__isnull=True,start_date__isnull=False,pk__in=allowed_votings)
    visualize_votings = voting_models.Voting.objects.filter(end_date__isnull=False,tally__isnull=False,pk__in=allowed_votings)

    if is_anonymous:
        return render(request,'register.html')
    else:
        return render(request,'mainpage.html',{
                                                'voting_votings':voting_votings,
                                                'visualize_votings':visualize_votings,
                                                'is_anonymous':is_anonymous,
                                                'is_staff':is_staff
                                                })