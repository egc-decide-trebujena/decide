from django import forms
from .models import Census


class CensusForm(forms.Form):
    voting_id=forms.IntegerField(label='voting_id')
    voter_id=forms.IntegerField(label='voter_id')
    group_id=forms.IntegerField(label='group_id')