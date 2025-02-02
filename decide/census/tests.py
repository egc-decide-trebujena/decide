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
from selenium.webdriver.support.wait import WebDriverWait

from base.tests import BaseTestCase
import time
import os
import csv
import json
import xlsxwriter

class CensusNewPositiveTestCase(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.base = BaseTestCase()
        self.base.setUp()

        self.q = Question(desc='test question')
        self.q.save()
        for i in range(5):
            self.opt = QuestionOption(question=self.q, option='option {}'.format(i+1))
            self.opt.save()
        self.v = Voting(name='test voting', question=self.q)
        self.v.save()

        self.v.create_pubkey()
        self.v.start_date = timezone.now()
        self.v.save()

        self.a, self._ = Auth.objects.get_or_create(url=f'{self.live_server_url}',
                                          defaults={'me': True, 'name': 'test auth'})
        self.a.save()
        self.v.auths.add(self.a)
        self.v.save()

        self.password = 'qwerty'

        self.u=User.objects.create_superuser('Enriqu', 'myemail@test.com', self.password)

        self.options = webdriver.ChromeOptions()
        self.options.headless = True
        self.driver = webdriver.Chrome(options=self.options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_positive_census(self):
        self.driver.get(f'{self.live_server_url}/admin/')
        self.driver.find_element(By.ID, "id_username").send_keys('Enriqu')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)
        self.driver.get(f'{self.live_server_url}/census/new')
        self.driver.find_element(By.ID, "btn").click()
        self.assertTrue(len(self.driver.find_elements(By.ID,'success'))==1)

class CensusNewBDTestCase(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        self.base = BaseTestCase()
        self.base.setUp()

        self.q = Question(desc='test question')
        self.q.save()
        for i in range(5):
            self.opt = QuestionOption(question=self.q, option='option {}'.format(i+1))
            self.opt.save()
        self.v = Voting(name='test voting', question=self.q)
        self.v.save()

        self.v.create_pubkey()
        self.v.start_date = timezone.now()
        self.v.save()

        self.a, self._ = Auth.objects.get_or_create(url=f'{self.live_server_url}',
                                          defaults={'me': True, 'name': 'test auth'})
        self.a.save()
        self.v.auths.add(self.a)
        self.v.save()

        self.password = 'qwerty'

        self.u=User.objects.create_superuser('Enriqu', 'myemail@test.com', self.password)

        self.options = webdriver.ChromeOptions()
        self.options.headless = True
        self.driver = webdriver.Chrome(options=self.options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_bd_census(self):
        self.c=Census.objects.all().count()
        self.driver.get(f'{self.live_server_url}/admin/')
        self.driver.find_element(By.ID, "id_username").send_keys('Enriqu')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)
        self.driver.get(f'{self.live_server_url}/census/new')
        self.driver.find_element(By.ID, "btn").click()
        self.af=Census.objects.all().count()
        self.assertTrue(self.c+1==self.af)

class CensusNewNegativeTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()
        self.password = 'qwerty'

        self.u=User.objects.create_superuser('Enriqu', 'myemail@test.com', self.password)

        self.options = webdriver.ChromeOptions()
        self.options.headless = True
        self.driver = webdriver.Chrome(options=self.options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_error_census_creation(self):
        self.driver.get(f'{self.live_server_url}/admin/')
        self.driver.find_element(By.ID, "id_username").send_keys('Enriqu')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty',Keys.ENTER)
        self.driver.get(f'{self.live_server_url}/census/new')
        self.driver.find_element(By.ID, "btn").click()
        self.assertTrue(len(self.driver.find_elements(By.ID,'danger'))>0)

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
        self.assertEqual(response.json(), {'Current_Censuses': [[1, 1, None]]})

    def test_add_new_voters_conflict(self):
        data = {'voting_id': 1, 'voter_id': 1, 'group':{'name':''}}
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 401)

        self.login(user='noadmin')
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 409)

    def test_add_new_voters(self):
        old_census = Census.objects.count()
        voters = [2,3,4,5]
        for v in voters:
            data = {'voting_id': 1, 'voter_id': v, 'group':{'name':''}}
            response = self.client.post('/census/api', data, format='json')
            self.assertEqual(response.status_code, 401)

            self.login(user='noadmin')
            response = self.client.post('/census/api', data, format='json')
            self.assertEqual(response.status_code, 403)

            self.login()
            response = self.client.post('/census/api', data, format='json')
            self.assertEqual(response.status_code, 201)
            self.logout()
        self.assertEqual(Census.objects.count(), old_census + len(voters))

    def test_destroy_voter(self):
        self.login()
        response = self.client.delete('/census/api/{}/?voter_id={}'.format(1,1), format='json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, Census.objects.count())
    
    def test_add_new_voters_with_group(self):
        old_census = Census.objects.count()
        data = {'voting_id': 1,'voter_id':2,'group':{'name':'Test Group 1'}}
        self.login()
        response = self.client.post('/census/api', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Census.objects.count(), old_census + 1)

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
        
        self.census_group = CensusGroup(name='Test Group 1')
        self.census_group.save() 

        self.driver.get(f'{self.live_server_url}/authentication/signin')
        self.driver.find_element(By.ID, "id_username").send_keys('superadmin')
        self.driver.find_element(By.ID, "id_password").send_keys('qwerty')
        self.driver.find_element(By.ID, "id-signin-btn").click()
        
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

        v_id = User.objects.get(username="Jaime").pk

        census = Census(voting_id=1, voter_id=v_id)
        census.save()

        census2 = Census(voting_id=2, voter_id=v_id)
        census2.save()
        
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

class CensusGroupModelTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.census_group = CensusGroup(name='Trebujena')
        self.census_group.save()

    def tearDown(self):
        super().tearDown()
        self.census_group = None
    
    def test_get_group(self):
        self.assertEquals(CensusGroup.objects.get(pk=self.census_group.pk).name, 'Trebujena')

    def test_create_group(self):
        numGroup = CensusGroup.objects.count()
        group = CensusGroup(name='Sevilla')
        group.save()
        self.assertEquals(CensusGroup.objects.count(),numGroup+1)
    
    def test_delete_group(self):
        numGroup = CensusGroup.objects.count()
        self.census_group.delete()
        self.assertEquals(CensusGroup.objects.count(),numGroup-1)
    
    def test_update_group(self):
        self.census_group.name = 'Sevilla'
        self.census_group.save()
        self.assertEquals(CensusGroup.objects.get(pk=self.census_group.pk).name, 'Sevilla')

class CensusGroupingModelTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()
        self.census_group = CensusGroup(name='Trebujena')
        self.census_group.save()
        self.census2 = Census(voting_id=1, voter_id=2, group = self.census_group)
        self.census2.save()

    def tearDown(self):
        super().tearDown()
        self.census = None
        self.census_group = None
        self.census2 = None
    
    def test_census_add_group(self):
        self.census.group = self.census_group
        self.census.save()
        self.assertEquals(Census.objects.get(pk=self.census.pk).group.name, 'Trebujena')
    
    def test_census_group_after_group_deletion(self):
        self.assertEquals(Census.objects.get(pk=self.census2.pk).group.name, 'Trebujena')
        self.census_group.delete()
        self.assertEquals(Census.objects.get(pk=self.census2.pk).group, None)
    
    def test_census_delete_group(self):
        self.census2.group.delete()
        self.assertNotEquals(Census.objects.get(pk=self.census2.pk).group, self.census_group)
    
    def test_census_group_after_group_update(self):
        self.census_group.name = 'Marchena'
        self.census_group.save()
        self.assertEquals(Census.objects.get(pk=self.census2.pk).group.name, 'Marchena')


class CensusDetailsTranslationCase(StaticLiveServerTestCase):

    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()
        
        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_details/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()

        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="reuse_census"))
        self.assertEqual(header_text.text, "Réutiliser les recensements")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_details/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()

        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="reuse_census"))
        self.assertEqual(header_text.text, "Volkszählungen wiederverwenden")

    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_details/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()

        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="reuse_census"))
        self.assertEqual(header_text.text, "Reutilizar Censos")
        
        
    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_details/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="reuse_census"))
        self.assertEqual(header_text.text, "Reuse census")

class CensusReuseTranslationCase(StaticLiveServerTestCase):

    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
    
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/reuse'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="origin_voting"))
        self.assertEqual(header_text.text.strip(), "Vote d'origine:")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/reuse'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="origin_voting"))
        self.assertEqual(header_text.text.strip(), "Herkunftsabstimmung:")
        
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/reuse'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="origin_voting"))
        self.assertEqual(header_text.text.strip(), "Votación origen:")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/reuse'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="origin_voting"))
        self.assertEqual(header_text.text.strip(), "Origin voting:")
class ImportExcelPageTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importer un fichier excel")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Excel-datei importieren")
    
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importación Fichero Excel")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Import excel file")

class CensusGroupingTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_grouping/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text.strip(), "Recensement de groupe")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_grouping/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text.strip(), "Gruppenzählung")
        
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_grouping/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text.strip(), "Agrupar Censo")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/census_grouping/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text.strip(), "Group Census")
        
    
class CensusPageTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    
    def test_french_translation(self):
        
        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="voter"))
        self.assertEqual(header_text.text.strip(), "Électeur")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="voter"))
        self.assertEqual(header_text.text.strip(), "Wähler")
        
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="voter"))
        self.assertEqual(header_text.text.strip(), "Votante")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="voter"))
        self.assertEqual(header_text.text.strip(), "Voter")

class ExportExcelPageTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/export/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Exporter un fichier excel")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/export/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Excel-datei exportieren")
    
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/export/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Exportación de Fichero Excel")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/export/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Export excel file")

class ImportJSONExcelPageTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_json/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importer un fichier JSON")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_json/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "JSON-datei importieren")
    
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_json/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importación Fichero JSON")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_json/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Import JSON file")

class ImportCSVExcelPageTranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()
        
        self.test_user = User.objects.create_user(username='test_user', password='test_user_password')
        
        self.driver.get('{}/authentication/signin'.format(self.live_server_url))
        username_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_username"))
        username_field.send_keys('test_user')
        password_field = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id_password"))
        password_field.send_keys('test_user_password')
        
        submit_login_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="id-signin-btn"))
        submit_login_button.click()
        
    def tearDown(self):           
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()
        
    def test_french_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_csv/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importer un fichier CSV")
        
    def test_german_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_csv/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "CSV-datei importieren")
    
    def test_spanish_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_csv/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Importación Fichero Excel")

    def test_english_translation(self):

        self.driver.set_window_size(1920,1080)
        self.driver.get('{}/census/import_csv/'.format(self.live_server_url))
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.NAME, value="language"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        header_text = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="page_title"))
        self.assertEqual(header_text.text, "Import CSV file")
