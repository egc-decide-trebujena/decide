from django import forms

class CensusReuseForm(forms.Form):
    voting_id = forms.IntegerField(label="voting_id")
    new_voting = forms.IntegerField(label="new_voting")