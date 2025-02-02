from django.contrib.auth.decorators import login_required
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.status import (
        HTTP_201_CREATED as ST_201,
        HTTP_204_NO_CONTENT as ST_204,
        HTTP_400_BAD_REQUEST as ST_400,
        HTTP_401_UNAUTHORIZED as ST_401,
        HTTP_409_CONFLICT as ST_409
)

from rest_framework.permissions import IsAdminUser
from .models import Census,CensusGroup
from .forms import CensusReuseForm, CensusGroupingForm, CensusForm
from .serializers import CensusGroupSerializer,CensusSerializer
from django.shortcuts import render

from django.conf import settings
import pandas as pd
from django.db import transaction
import math
from django.http import HttpResponse
import csv
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _


class CensusCreate(generics.ListCreateAPIView):
    serializer_class = CensusSerializer
    permission_classes = (IsAdminUser,)

    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voter_id = request.data.get('voter_id')
        group_name = request.data.get('group.name')

        try:
            group = None
            if group_name is not None:
                group = CensusGroup.objects.get(name=group_name)
            census = Census(voting_id=voting_id, voter_id=voter_id, group=group)
            census.save()
        except CensusGroup.DoesNotExist:
            return Response('The input Census Group does not exist', status=ST_400)
        except IntegrityError:
            return Response('Error trying to create census', status=ST_409)
        except:
            return Response('Census must have voting_id and voter_id', status=ST_400)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        census = Census.objects.all().values_list('voting_id','voter_id', 'group')
        return Response({'Current_Censuses': census})

@transaction.atomic
@login_required(login_url='/authentication/signin/?next=/census/import_json')
def import_json(request):
    try: 
        if request.method == 'POST':
            census_from_json=[]
        
            myfile = request.FILES['myfile'] 
            df=pd.read_json(myfile)

            for d in df.values:
                try:
                    group= None
                    if d[2]:
                        if d[2] == "":
                            group = None
                        else: 
                            group = CensusGroup.objects.get(id=d[2])

                    census = Census(voting_id=d[0], voter_id=d[1],group=group)
                    census_from_json.append(census)
                except CensusGroup.DoesNotExist:
                    message = _('The input Census Group does not exist')
                    messages.error(request, message)
                    return render(request,"json.html")
            for c in census_from_json:
                try:
                    c.save()
                except IntegrityError:
                    message = _('Error trying to import JSON. A census cannot be repeated.')
                    messages.error(request, message)
                    return render(request,"json.html")
            message = _('Census created')
            messages.success(request, message)
    except:
        message = _('Error in JSON data.')
        messages.error(request, message) 
        return render(request,"json.html")
    return render(request,"json.html")

@transaction.atomic
@login_required(login_url='/authentication/signin/?next=/census/import_csv')
def import_csv(request):
    cont=2
    try: 
        if request.method == 'POST':
            census_from_csv=[]
        
            myfile = request.FILES['myfile'] 
            df=pd.read_csv(myfile)

            for d in df.values:
                try:
                    group = None
                    if not math.isnan(d[2]):
                        group = CensusGroup.objects.get(id=d[2])

                    census = Census(voting_id=d[0], voter_id=d[1],group=group)
                    census_from_csv.append(census)
                    cont+=1
                except CensusGroup.DoesNotExist:
                    message = _("The input Census Group does not exist, in row {}").format(cont-1)
                    messages.error(request, message)
                    return render(request, "csv.html")
            cont=0
            for c in census_from_csv:
                try:
                    cont+=1
                    c.save()
                except IntegrityError:
                    message = _("Error trying to import CSV, in row {}. A census cannot be repeated.").format(cont)
                    messages.error(request, message)
                    return render(request,"csv.html")
            message=_("Census Created")
            messages.success(request, message)
            return render(request,"csv.html")
    except:
        message=_('Error in CSV data. There are wrong data in row {}').format(cont+1)
        messages.error(request, message) 
        return render(request,"csv.html")
    return render(request,"csv.html")

@transaction.atomic
@login_required(login_url='/authentication/signin/?next=/census/import')
def import_excel(request):
    cont=2
    try: 
        if request.method == 'POST':
            census_from_excel=[]
        
            myfile = request.FILES['myfile'] 
            df=pd.read_excel(myfile)

            for d in df.values:
                try:
                    group = None
                    if not math.isnan(d[2]):
                        group = CensusGroup.objects.get(id=d[2])

                    census = Census(voting_id=d[0], voter_id=d[1],group=group)
                    census_from_excel.append(census)
                    cont+=1
                except CensusGroup.DoesNotExist:
                    messages.error(request,_('The input Census Group does not exist, in row') + ' {}'.format(cont-1))
                    return render(request,"census/import.html")

            cont=0
            for c in census_from_excel:
                try:
                    cont+=1
                    c.save()
                except IntegrityError:
                    messages.error(request, _('Error trying to import excel, in row') + ' {}. '.format(cont) + _('A census cannot be repeated.'))
                    return render(request,"census/import.html")
                    
            messages.success(request, _('Census Created'))
            return render(request,"census/import.html")

    except:
        messages.error(request, _('Error in excel data. There are wrong data in row') + ' {}'.format(cont+1)) 
        return render(request,"census/import.html")

    return render(request,"census/import.html")

@login_required(login_url='/authentication/signin/?next=/census/export')
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
            message = _("Exportado correctamente")
            messages.success(request, message)
            return response
    except:
            message = _("Error in exporting data. There are null data in rows")
            messages.error(request, message)
            return render(request, "census/export.html")
    return render(request,"census/export.html")

class CensusDetail(generics.RetrieveDestroyAPIView):
    serializer_class = CensusSerializer

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.GET.get('voter_id')
        census = Census.objects.filter(voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voter deleted from voting', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')

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
            return Response('Error try to create census', status=ST_409)
        return Response('Census created', status=ST_201)

def censusReuse(request):
    if request.method == 'POST':
            form = CensusReuseForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                voting_id = cd['voting_id']
                new_voting = cd['new_voting']
                censos = Census.objects.all().values()
                for c in censos:
                    if(c['voting_id'] == voting_id):
                            try:
                                census = Census(voting_id=new_voting, voter_id=c['voter_id'], group_id=c['group_id'])
                                census.save()
                            except:
                                pass
                return redirect('/census')
            else:
                return render(request,'census/census_reuse_form.html',{'errors':[_('Entries must be integers')]})
    else:
        form = CensusReuseForm()
    return render(request,'census/census_reuse_form.html',{'form':form})

def censusCreation(request):
    msg=''
    tipo=''
    if request.method == 'POST':
        form=CensusForm(request.POST)
        
        if form.is_valid():
            cd = form.cleaned_data
            voting_id=cd['voting_id']
            voter_id=cd['voter_name']
            group=cd['group_name']
            if str(group).strip() == "" :
                try:
                    census=Census(voting_id=voting_id,voter_id=voter_id)
                    census.save()
                    msg=_("Censo creado con éxito")
                    tipo="success"
                except:
                    msg=_("No se ha podido crear el censo")
                    tipo="danger"
                    pass
                return render(request,'census/census_create.html',{'form':form, 'msg':msg, 'tipo':tipo})
            else:
                group_search=CensusGroup.objects.get_or_create(name=str(group))
                group_result=get_object_or_404(CensusGroup,name=str(group_search[0]))
                try:
                    census=Census(voting_id=voting_id,voter_id=voter_id,group_id=group_result.id)
                    census.save()
                    msg=_("Censo creado con éxito")
                    tipo="success"
                except:
                    msg=_("No se ha podido crear el censo")
                    tipo="danger"
                    pass
                return render(request,'census/census_create.html',{'form':form, 'msg':msg, 'tipo':tipo})
        else:
            msg=_("No se ha podido crear el censo")
            tipo="danger"
            return render(request,'census/census_create.html',{'form':form, 'msg':msg, 'tipo':tipo})
    else:
        form = CensusForm()
    return render(request,'census/census_create.html',{'form':form, 'msg':msg, 'tipo':tipo})

def censusList(request):
    censos = Census.objects.all().values()
    res = []
    options = []
    for c in censos:
        try:
            votante = User.objects.get(pk=c['voter_id'])
        except:
            votante = "El votante todavía no ha sido añadido"
        if(votante not in options):
            options.append(votante)
        censo = c['voting_id']
        try:
            grupo = CensusGroup.objects.get(id=c['group_id'])
            if(grupo not in options):
                options.append(grupo.name)
        except:
            grupo = "No tiene grupo asignado"
            if(grupo not in options):
                options.append(grupo)
        res.append({'voting_id':censo,'voter':votante,'group':grupo})
    return render(request,'census/census.html',{'censos':res, 'options':options})

class CensusGroupDetail(generics.RetrieveDestroyAPIView):
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

def census_grouping(request):
    msg=''
    tipo=''
    censos = Census.objects.all().values()
    censuses = sorted(census_list(censos), key=lambda i: i['voting_id'])

    if request.method == 'POST':
        form = CensusGroupingForm(request.POST)
       
        if form.is_valid():
            formData = form.cleaned_data
            group_name = formData['group']
            choices = formData['choices']
            
            censosForm = choices.values()

            for censo in censosForm:
                try:
                    if group_name.strip()=="":
                        census = Census(id=censo['id'], voting_id=censo['voting_id'], voter_id=censo['voter_id'])
                        census.save()
                    else:
                        group = CensusGroup.objects.get(name=group_name)
                        census = Census(id=censo['id'], voting_id=censo['voting_id'], voter_id=censo['voter_id'], group=group)
                        census.save()
                except:
                    msg="El grupo no existe o se ha escrito de forma incorrecta"
                    tipo="danger"
                    form = CensusGroupingForm()
                    return render(request,'census/census_grouping.html',{'form':form, 'censos': censuses, 'msg': msg, 'tipo': tipo})
            msg="Cambios efectuados correctamente"
            tipo="success"
            form = CensusGroupingForm()
            censuses = sorted(census_list(Census.objects.all().values()), key=lambda i: i['voting_id'])
            return render(request,'census/census_grouping.html',{'form':form, 'censos': censuses, 'msg': msg, 'tipo': tipo})
        else:
            msg="Se debe seleccionar un censo como mínimo"
            tipo="danger"
            form = CensusGroupingForm()
            return render(request,'census/census_grouping.html',{'form':form, 'censos': censuses, 'msg': msg, 'tipo': tipo})
    else:
        msg=''
        tipo=''
        form = CensusGroupingForm()
    return render(request,'census/census_grouping.html',{'form':form, 'censos': censuses, 'msg': msg, 'tipo': tipo})

def census_details(request):
    msg=''
    tipo=''
    censos = Census.objects.all().values()

    if request.method == 'POST':
        try:
            censo = Census.objects.filter(id = request.POST['delete'])
            censo.delete()
            msg="Censo eliminado correctamente"
            tipo="success"
        except:
            msg="No se pudo eliminar el censo"
            tipo="danger"
    census = sorted(census_list(censos), key=lambda i:i['id'])
    return render(request,'census/census_details.html',{'censos':census,'msg':msg,'tipo':tipo})

def census_list(censos):
    res = []
    for censo in censos:
        try:
            votante = User.objects.get(pk=censo['voter_id'])
        except:
            votante = _("El votante todavía no ha sido añadido")
        try:
            grupo = CensusGroup.objects.get(id=censo['group_id'])
        except:
            grupo = _("No tiene grupo asignado")
        res.append({'id': censo['id'],'voting_id':censo['voting_id'],'voter':votante,'group':grupo})
    return res
