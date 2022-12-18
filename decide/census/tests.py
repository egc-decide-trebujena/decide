from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Census,CensusGroup
from base.tests import BaseTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.keys import Keys
from django.test import TestCase, Client
from voting.models import Voting, Question, QuestionOption
from mixnet.models import Auth
from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By

from base.tests import BaseTestCase
import time
import os
import csv
import json
import xlsxwriter

class CensusNewPageTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()

        Voting.objects.all().delete()
        Census.objects.all().delete()
        q = Question(desc='test question')
        q.save()
        for i in range(5):
            opt = QuestionOption(question=q, option='option {}'.format(i+1))
            opt.save()
        v = Voting(name='test voting', question=q)
        v.save()

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        a, _ = Auth.objects.get_or_create(url=f'{self.live_server_url}',
                                          defaults={'me': True, 'name': 'test auth'})
        a.save()
        v.auths.add(a)
        v.save()
        password = 'qwerty'

        User.objects.create_superuser('Enriqu', 'myemail@test.com', password)

        options = webdriver.ChromeOptions()
        options.headless = False
        self.driver = webdriver.Chrome(options=options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_visualizer_detail(self):
        print(Voting.objects.get(id=1).id)
        self.driver.get(f'{self.live_server_url}/admin/')
        self.driver.find_element(By.ID, "id_username").send_keys('Enriqu')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)
        self.driver.get(f'{self.live_server_url}/census/new')
        time.sleep(15)
        self.driver.find_element(By.ID, "btn").click()
        self.assertTrue(len(self.driver.find_elements(By.ID,'success'))==1)

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
        self.user = None

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

class CensusGroupTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()

    def tearDown(self):
        super().tearDown()
        self.census = None
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

        self.driver.get(f'{self.live_server_url}/authentication/signin')
        self.driver.find_element(By.ID, "id_username").send_keys('superadmin')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty')
        self.driver.find_element(By.ID, "id-signin-btn").click()

        super().setUp()            
            
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census_group = None
        self.census = None
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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
        self.census = None
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        # self.driver.get(f'{self.live_server_url}/authentication/signin')
        # self.driver.find_element(By.ID, "id_username").send_keys('superadmin')
        # self.driver.find_element(By.ID, "id_password").send_keys('qwerty')
        # self.driver.find_element(By.CSS_SELECTOR, ".btn").click()
        
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save() 
        super().setUp()
          
            
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
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

        self.driver.find_element(By.ID, "id-submit-import").click()
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME,'alert-danger'))==1)
        self.assertEqual(0,Census.objects.count())

class CensusReuseTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.census = None
    
    def test_census_reuse_fail(self):
        self.login()

        staff = User.objects.get(username="admin").is_staff

        data = {'voting_id':'x','new_voting':'y','staff':staff}
        response = self.client.post('/census/reuse',data=data)
        self.assertEqual(len(response.context.get('errors')),1)
    
    def test_census_reuse(self):
        self.login()

        staff = User.objects.get(username="admin").is_staff

        data = {'voting_id':1,'new_voting':2,'staff':staff}
        response = self.client.post('/census/reuse',data=data)
        self.assertRedirects(response,'/census', status_code=302, target_status_code=301)

class CensusNewTestCase(StaticLiveServerTestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
    
    def tearDown(self):
        super().tearDown()
        self.driver.quit()
    
    def test_viewcreatecensus(self):
        self.driver.get(f'{self.live_server_url}/census/new')
        self.assertTrue(len(self.driver.find_elements(By.ID, "id_voting_id"))==1)
        self.assertTrue(len(self.driver.find_elements(By.ID, "id_voter_name"))==1)
        self.assertTrue(len(self.driver.find_elements(By.ID, "id_group_name"))==1)
        self.assertTrue(len(self.driver.find_elements(By.ID, "btn"))==1)

class CensusExportTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()


        self.user = User.objects.create_user(username='admins', password='admins')

        self.client = Client()

        self.client.login(username='admins', password='admins')
        

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
        census_values=Census.objects.all().values_list('voting_id','voter_id','group')
        values=rows[1].split(",")
        values[-1]=values[-1].replace("\r","")
        for i in range(len(census_values[0])):
            if values[i] != "":
                self.assertEqual(int(values[i]), census_values[0][i])
            else:
                self.assertEqual(None, census_values[0][i])
        
    def test_export_census_data_with_groups(self):

        self.census = Census(voting_id=2, voter_id=2,group=CensusGroup.objects.get(id=self.census_group.id))
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
        census_values=Census.objects.all().values_list('voting_id','voter_id','group')
        values=rows[1].split(",")
        values[-1]=values[-1].replace("\r","")
        for i in range(len(census_values[0])):
            if values[i] != "":
                self.assertEqual(int(values[i]), census_values[0][i])
            else:
                self.assertEqual(None, census_values[0][i])

class CensusPageTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp() 

        u = User(username='Jaime', is_staff=True)
        u.set_password('qwerty')
        u.save()

        id = User.objects.get(username="Jaime").pk

        census = Census(voting_id=1, voter_id=id)
        census.save()

        census2 = Census(voting_id=2, voter_id=id)
        census2.save()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_census_reuse(self):
        self.driver.get(f'{self.live_server_url}/admin')
        self.driver.find_element(By.ID, "id_username").send_keys('Jaime')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)

        self.driver.get(f'{self.live_server_url}/census/reuse')
        self.assertTrue(len(self.driver.find_elements(By.ID,'voting_id')) == 1)
        self.assertTrue(len(self.driver.find_elements(By.ID,'new_voting')) == 1)
        

    def test_census_mainpage(self):
        self.driver.get(f'{self.live_server_url}/admin')
        self.driver.find_element(By.ID, "id_username").send_keys('Jaime')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)

        time.sleep(5)
        self.driver.get(f'{self.live_server_url}/census')
        time.sleep(5)
        self.assertTrue(len(self.driver.find_elements(By.ID,'tabla-votacion'))==1)
        self.assertTrue(len(self.driver.find_elements(By.ID,'1-Jaime')) == 1)

