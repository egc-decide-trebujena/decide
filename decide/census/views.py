from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import (
        HTTP_201_CREATED as ST_201,
        HTTP_204_NO_CONTENT as ST_204,
        HTTP_400_BAD_REQUEST as ST_400,
        HTTP_401_UNAUTHORIZED as ST_401,
        HTTP_409_CONFLICT as ST_409
)

from base.perms import UserIsStaff
from .models import Census,CensusGroup
from .forms import CensusForm



class CensusCreate(generics.ListCreateAPIView):
    permission_classes = (UserIsStaff,)

    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voters = request.data.get('voters')
        try:
            for voter in voters:
                census = Census(voting_id=voting_id, voter_id=voter)
                census.save()
        except IntegrityError:
            return Response('Error try to create census', status=ST_409)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        voting_id = request.GET.get('voting_id')
        voters = Census.objects.filter(voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


class CensusDetail(generics.RetrieveDestroyAPIView):

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.data.get('voters')
        census = Census.objects.filter(voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voters deleted from census', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')


def census_creation(request):
    print(Census.objects.all().values_list('voting_id'))
    voter_id=Census.objects.all()
    voting_id=Census.objects.all()
    group_id = CensusGroup.objects.all().values_list('id')
    print(group_id)
    if request.method=='POST':
        form=CensusForm(request.POST)
        if form.is_valid():
            cd=form.cleaned_data
            voting_id=cd['voting_id']
            voter_id=cd['voter_id']
            group_id=cd['group_id']
            census=Census(voting_id=voting_id,voter_id=voter_id,group_id=group_id)
            census.save()
        else:
            return Response("Error",status=ST_400)
    else:
        form=CensusForm()
    print(Census.objects.all().values())
    return render(request,"new.html",{'form':form,'voter_id':voter_id,'voting_id':voting_id,'group_id':group_id})
