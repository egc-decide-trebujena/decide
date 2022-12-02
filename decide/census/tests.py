import random
from django.contrib.auth.models import User
from django.test import TestCase
from census.forms import CensusReuseForm
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from .models import Census,CensusGroup
from base import mods
from base.tests import BaseTestCase

from pyexpat import model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from base.tests import BaseTestCase
from time import sleep
import sys, os
import csv
import pandas as pd
import json
import xlsxwriter

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
        response = self.client.get('/census/api/{}/?voter_id={}'.format(1, 2), format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), 'Invalid voter')

        response = self.client.get('/census/api/{}/?voter_id={}'.format(1, 1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 'Valid voter')

    def test_list_voting(self):
        response = self.client.get('/census/api?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.get('/census/api?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.get('/census/api?voting_id={}'.format(1), format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'voters': [1]})

    def test_add_new_voters_conflict(self):
        data = {'voting_id': 1, 'voters': [1]}
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 409)

    def test_add_new_voters(self):
        data = {'voting_id': 2, 'voters': [1,2,3,4]}
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get('voters')), Census.objects.count() - 1)

    def test_destroy_voter(self):
        data = {'voters': [1]}

        self.login()
        response = self.client.delete('/census/api/{}/'.format(1), data, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, Census.objects.count())
    
    def test_add_new_voters_with_group(self):
        data = {'voting_id': 1,'voters':[2],'group':{'name':'Test Group 1'}}
        self.login()
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get('voters')), Census.objects.count() - 1)


class SeleniumImportExcelTestCase(StaticLiveServerTestCase):
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        superuser_admin = User(username='superadmin', is_staff=True, is_superuser=True)
        superuser_admin.set_password('qwerty')
        superuser_admin.save()

        super().setUp()            
            
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census_group = None
        os.remove("census/test_import.xlsx")


    def create_excel_file(self,expenses):
        test = xlsxwriter.Workbook('census/test_import.xlsx')
        testfile = test.add_worksheet()
        
        for i in range(len(expenses)):
            for j in range(3):
                testfile.write(i, j, expenses[i][j])
        test.close()



    def test_import_excel_positive_no_group(self):
        expenses = (['voting_id', 'voter_id','group'],
                    [1,1,''])
        self.create_excel_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("./test_import.xlsx"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'census/test_import.xlsx')

        self.driver.get(f'{self.live_server_url}/census/import')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(1,Census.objects.count())
       

    def test_import_excel_positive_with_group(self):
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()

        expenses = (['voting_id', 'voter_id','group'],
                    [1,1,CensusGroup.objects.get(name='Test Group 1').pk])
        self.create_excel_file(expenses)

        ROOT_DIR = os.path.dirname(os.path.abspath("./test_import.xlsx"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'census/test_import.xlsx')

        self.driver.get(f'{self.live_server_url}/census/import')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(1,Census.objects.count())
        

    def test_import_excel_negative_with_group(self):
        expenses = (['voting_id', 'voter_id','group'],
                    [1,1,1])
        self.create_excel_file(expenses)

        ROOT_DIR = os.path.dirname(os.path.abspath("./test_import.xlsx"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'census/test_import.xlsx')

        self.driver.get(f'{self.live_server_url}/census/import')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        
    def test_import_excel_negative_null_data(self):

        expenses = (['voting_id', 'voter_id','group'],
                    [1,None,''])

        self.create_excel_file(expenses)

        ROOT_DIR = os.path.dirname(os.path.abspath("./test_import.xlsx"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'census/test_import.xlsx')

        self.driver.get(f'{self.live_server_url}/census/import')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        

    def test_import_excel_negative_integrity_error(self):
        expenses = (['voting_id', 'voter_id','group'],
                    [1,1,''],
                    [1,1,''])
        self.create_excel_file(expenses)

        ROOT_DIR = os.path.dirname(os.path.abspath("./test_import.xlsx"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'census/test_import.xlsx')

        self.driver.get(f'{self.live_server_url}/census/import')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())

class SeleniumImportJSONTestCase(StaticLiveServerTestCase):
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        superuser_admin = User(username='superadmin', is_staff=True, is_superuser=True)
        superuser_admin.set_password('qwerty')
        superuser_admin.save()
        
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save() 
        super().setUp()
          
            
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census_group = None
        os.remove("census/test_import_census_json.json")
    

    def create_json_file(self,expenses):
        
        datos = json.dumps(expenses)
        jsonFile = open("census/test_import_census_json.json", "w")
        jsonFile.write(datos)
        jsonFile.close()

            
            
    def test_import_json_positive(self):

        expenses = [{"voting_id":1, "voter_id":1, "group": ""}]

        self.create_json_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_json.json"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_json.json')

        self.driver.get(f'{self.live_server_url}/census/import_json')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(1,Census.objects.count())

    def test_import_json_positive_with_group(self):

        group_name = 'Test Group 1'
        group_id = CensusGroup.objects.get(name=group_name).pk

        expenses = [{"voting_id":1, "voter_id":1, "group": group_id}, {"voting_id":2, "voter_id":2, "group": group_id}]

        self.create_json_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_json.json"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_json.json')

        self.driver.get(f'{self.live_server_url}/census/import_json')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(2,Census.objects.count())

    def test_import_json_negative_nonexistent_group(self):

        expenses = [{"voting_id":1, "voter_id":1, "group": 18}, {"voting_id":2, "voter_id":2, "group": 28}]

        self.create_json_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_json.json"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_json.json')

        self.driver.get(f'{self.live_server_url}/census/import_json')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        
    def test_import_json_negative_null_data(self):

        expenses = [{"voting_id":1, "voter_id":1, "group": None}, {"voting_id":2, "voter_id":2, "group": None}]

        self.create_json_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_json.json"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_json.json')

        self.driver.get(f'{self.live_server_url}/census/import_json')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        

    def test_import_json_negative_integrity_error(self):
        
        expenses = [{"voting_id":1, "voter_id":1, "group": ""}, {"voting_id":1, "voter_id":1, "group": ""}]

        self.create_json_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_json.json"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_json.json')

        self.driver.get(f'{self.live_server_url}/census/import_json')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())

class SeleniumImportCSVTestCase(StaticLiveServerTestCase):
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        superuser_admin = User(username='superadmin', is_staff=True, is_superuser=True)
        superuser_admin.set_password('qwerty')
        superuser_admin.save()
        
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save() 
        super().setUp()
          
            
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census_group = None
        os.remove("census/test_import_census_csv.csv")
    

    def create_csv_file(self,expenses):

        header = ['voting_id', 'voter_id', 'group']

        with open('census/test_import_census_csv.csv', 'a', newline='') as f:
            
            writer = csv.writer(f)
            writer.writerow(header)

            if len(expenses) == 1:
                writer.writerow(expenses)
            elif len(expenses) > 1:
                writer.writerows(expenses)
            
            
    def test_import_csv_positive(self):

        expenses = [
            [1,1,''],
            [2,2,'']
        ]

        self.create_csv_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_csv.csv"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_csv.csv')

        self.driver.get(f'{self.live_server_url}/census/import_csv')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(2,Census.objects.count())

    def test_import_csv_positive_with_group(self):

        group_name = 'Test Group 1'
        group_id = CensusGroup.objects.get(name=group_name).pk

        expenses = [
            [1,1,group_id],
            [2,2,group_id]
        ]

        self.create_csv_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_csv.csv"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_csv.csv')

        self.driver.get(f'{self.live_server_url}/census/import_csv')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-success'))==1)
        self.assertEqual(2,Census.objects.count())

    def test_import_csv_negative_nonexistent_group(self):
        expenses = [
            [1,1,28],
            [2,2,39]
        ]

        self.create_csv_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_csv.csv"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_csv.csv')

        self.driver.get(f'{self.live_server_url}/census/import_csv')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        
    def test_import_csv_negative_null_data(self):

        expenses = [
            [None,1,28],
            [2,None,39]
        ]

        self.create_csv_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_csv.csv"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_csv.csv')

        self.driver.get(f'{self.live_server_url}/census/import_csv')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())
        

    def test_import_csv_negative_integrity_error(self):
        
        expenses = [
            [1,1,''],
            [1,1,'']
        ]

        self.create_csv_file(expenses)
        
        ROOT_DIR = os.path.dirname(os.path.abspath("census/test_import_census_csv.csv"))
        screenshotpath = os.path.join(os.path.sep, ROOT_DIR,'test_import_census_csv.csv')

        self.driver.get(f'{self.live_server_url}/census/import_csv')
        uploadElement=self.driver.find_element(by=By.ID, value="customFile")

        uploadElement.send_keys(screenshotpath)

        self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())


class CensusReuseTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
    
    def test_census_reuse(self):
        self.login()

        data = {'voting_id':'x','new_voting':'y'}
        response = self.client.post('/census/reuse',data=data)
        self.assertEqual(response.status_code, 400)

        data = {'voting_id':1,'new_voting':2}
        response = self.client.post('/census/reuse',data=data)
        self.assertEqual(response.status_code, 302)
        

class CensusExportTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()

    def tearDown(self):
        super().tearDown()
        self.census_group = None
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
