from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from rest_framework import generics
from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.status import (
        HTTP_201_CREATED as ST_201,
        HTTP_204_NO_CONTENT as ST_204,
        HTTP_400_BAD_REQUEST as ST_400,
        HTTP_401_UNAUTHORIZED as ST_401,
        HTTP_409_CONFLICT as ST_409
)
from rest_framework.permissions import IsAdminUser
from base.perms import UserIsStaff
from .models import Census,CensusGroup
from voting.models import Voting
from .forms import CensusForm

from .serializers import CensusGroupSerializer,CensusSerializer

from django.conf import settings
import pandas as pd
from rest_framework.decorators import api_view
from django.db import transaction
import math
from django.http import HttpResponse
import csv
from django.contrib import messages


class CensusCreate(generics.ListCreateAPIView):
    serializer_class = CensusSerializer
    permission_classes = (IsAdminUser,)

    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voters = request.data.get('voters')
        group_name = request.data.get('group')
        if group_name:
            group_name = group_name.get('name')
        try:
            group = None
            if group_name and len(group_name) > 0:
                group = CensusGroup.objects.get(name=group_name)
            for voter in voters:
                census = Census(voting_id=voting_id, voter_id=voter, group=group)
                census.save()
        except CensusGroup.DoesNotExist:
            return Response('The input Census Group does not exist', status=ST_400)
        except IntegrityError:
            return Response('Error trying to create census', status=ST_409)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        voting_id = request.GET.get('voting_id')
        voters = Census.objects.filter(voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


 




def export_excel(request):
    try:           
        if request.method == 'POST':
            census=Census.objects.all()
            response=HttpResponse()
            response['Content-Disposition']= 'attachment; filename=census.xlsx'
            writer=csv.writer(response)
            writer.writerow(['voting_id','voter_id','group'])
            census_fields=census.values_list('voting_id','voter_id','group')
            for c in census_fields:
                writer.writerow(c)
            messages.success(request,"Exportado correctamente")
            return response
    except:
            messages.error(request,'Error in exporting data. There are null data in rows')
            return render(request, "export.html")
    return render(request,"export.html")



class CensusDetail(generics.RetrieveDestroyAPIView):
    serializer_class = CensusSerializer

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
    voter_id= [x[0] for x in User.objects.all().values_list('username')]
    voting_id=  [x[0] for x in Voting.objects.all().values_list('id')]
    group_id = [x[0] for x in CensusGroup.objects.all().values_list('name')]
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
    return render(request,"new.html",{'form':form,'voter_id':voter_id,'voting_id':voting_id,'group_id':group_id})
class CensusGroupCreate(generics.ListCreateAPIView):
    serializer_class = CensusGroupSerializer
    permission_classes = (IsAdminUser,)
    queryset = CensusGroup.objects.all()

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        try:
            census_group = CensusGroup(name=name)
            census_group.save()
        except IntegrityError:
            return Response('Error trying to create census', status=ST_409)
        return Response('Census group created', status=ST_201)
  
class CensusGroupDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CensusGroupSerializer
    queryset = CensusGroup.objects.all()

    def destroy(self, request, pk, *args, **kwargs):
        census_group = CensusGroup.objects.filter(id=pk)
        census_group.delete()
        return Response('Census Group deleted from census', status=ST_204)

    def retrieve(self, request, pk, *args, **kwargs):
        try:
            CensusGroup.objects.get(id=pk)
        except ObjectDoesNotExist:
            return Response('Non-existent group', status=ST_401)
        return Response('Valid group')
