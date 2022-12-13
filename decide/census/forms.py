from django import forms
from .models import Census,CensusGroup
from django.contrib.auth.models import User
from voting.models import Voting

class CensusReuseForm(forms.Form):
    voting_id = forms.IntegerField(label="voting_id")
    new_voting = forms.IntegerField(label="new_voting")

class CensusGroupingForm(forms.Form):
    group = forms.CharField(label="group", required = False)
    choices = forms.ModelMultipleChoiceField(
    queryset= Census.objects.all(),
    widget  = forms.CheckboxSelectMultiple,
    )


votings= list((x.id, x.id) for x in Voting.objects.all())
voters= list((x.id, x.username) for x in User.objects.all())

class CensusForm(forms.Form):
    voting_id=forms.ChoiceField(widget=forms.Select(attrs={'class': "form-control"}), choices=votings, label="Elige votación")
    voter_id=forms.ChoiceField(widget=forms.Select(attrs={'class': "form-control"}), choices=voters, label="Elige votante")
    group_id=forms.CharField(widget=forms.TextInput(attrs={'class': "form-control"}),label='group_id', required=False, )
