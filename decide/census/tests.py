import random
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Census,CensusGroup
from base import mods
from base.tests import BaseTestCase


class CensusTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()

    def tearDown(self):
        super().tearDown()
        self.census = None

    def test_check_vote_permissions(self):
        response = self.client.get('/census/{}/?voter_id={}'.format(1, 2), format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), 'Invalid voter')

        response = self.client.get('/census/{}/?voter_id={}'.format(1, 1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Valid voter')

    def test_list_voting(self):
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.get('/census/?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'voters': [1]})

    def test_add_new_voters_conflict(self):
        data = {'voting_id': 1, 'voters': [1]}
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 409)

    def test_add_new_voters(self):
        data = {'voting_id': 2, 'voters': [1,2,3,4]}
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get('voters')), Census.objects.count() - 1)

    def test_destroy_voter(self):
        data = {'voters': [1]}
        response = self.client.delete('/census/{}/'.format(1), data, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, Census.objects.count())
    
    def test_add_new_voters_with_group(self):
        data = {'voting_id': 1,'voters':[2],'group':{'name':'Test Group 1'}}
        self.login()
        response = self.client.post('/census/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get('voters')), Census.objects.count() - 1)

class CensusGroupTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()

    def tearDown(self):
        super().tearDown()
        self.census_group = None

    def test_group_creation(self):
        data = {'name':'Test Group 2'}
        response = self.client.post('/census/censusgroups/',data,format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/censusgroups/',data,format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/censusgroups/',data,format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(2,CensusGroup.objects.count())

    def test_group_destroy(self):
        group_name = 'Test Group 1'
        group_id = CensusGroup.objects.get(name=group_name).pk
        before = CensusGroup.objects.count()

        self.login()
        response = self.client.delete('/census/censusgroups/{}/'.format(group_id),format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(before-1,CensusGroup.objects.count())

class CensusExportTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()

    def tearDown(self):
        super().tearDown()
        self.census = None
        
    
    def test_export_census_data_without_groups(self):
        #Comprobamos que la petición es correcta
        response = self.client.get('/census/export/', format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/census/export/', format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=census.xlsx')
        #Leemos el fichero creado y comprobamos los resultados
        myfile=response.content.decode("utf-8") 
       
        rows=myfile.split("\n")
        fields=[f.name for f in Census._meta.fields + Census._meta.many_to_many ]
        fields=fields[1:]
        headers=[f for f in rows[0].split(",")]
        headers[-1]=headers[-1].replace("\r","")

        self.assertEqual(headers, fields)
        print(rows[1])
        census_values=Census.objects.all().values_list('voting_id','voter_id','group')
        print(census_values)
        values=rows[1].split(",")
        values[-1]=values[-1].replace("\r","")
        print(values)
        for i in range(len(census_values[0])):
            if values[i] != "":
                self.assertEqual(int(values[i]), census_values[0][i])
            else:
                self.assertEqual(None, census_values[0][i])
        
    def test_export_census_data_with_groups(self):

        self.census = Census(voting_id=2, voter_id=2,group=CensusGroup.objects.get(id=1))
        self.census.save()
        

        #Comprobamos que la petición es correcta
        response = self.client.get('/census/export/', format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/census/export/', format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=census.xlsx')
        #Leemos el fichero creado y comprobamos los resultados
        myfile=response.content.decode("utf-8") 
       
        rows=myfile.split("\n")
        fields=[f.name for f in Census._meta.fields + Census._meta.many_to_many ]
        fields=fields[1:]
        headers=[f for f in rows[0].split(",")]
        headers[-1]=headers[-1].replace("\r","")

        self.assertEqual(headers, fields)
        print(rows[1])
        census_values=Census.objects.all().values_list('voting_id','voter_id','group')
        print(census_values)
        values=rows[1].split(",")
        values[-1]=values[-1].replace("\r","")
        print(values)
        for i in range(len(census_values[0])):
            if values[i] != "":
                self.assertEqual(int(values[i]), census_values[0][i])
            else:
                self.assertEqual(None, census_values[0][i])



    