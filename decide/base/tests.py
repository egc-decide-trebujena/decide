from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from base import mods

import logging
from selenium.webdriver.remote.remote_connection import LOGGER
from urllib3.connectionpool import log as urllibLogger

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class BaseTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.token = None
        mods.mock_query(self.client)

        user_noadmin = User(username='noadmin')
        user_noadmin.set_password('qwerty')
        user_noadmin.save()

        user_admin = User(username='admin', is_staff=True)
        user_admin.set_password('qwerty')
        user_admin.save()

        LOGGER.setLevel(logging.WARNING)
        urllibLogger.setLevel(logging.WARNING)

    def tearDown(self):
        self.client = None
        self.token = None

    def login(self, user='admin', password='qwerty'):
        data = {'username': user, 'password': password}
        response = mods.post('authentication/login', json=data, response=True)
        self.assertEqual(response.status_code, 200)
        self.token = response.json().get('token')
        self.assertTrue(self.token)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)

    def logout(self):
        self.client.credentials()

class MainPageTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()

        super().setUp()       
        self.base.login()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()

    def test_access_mainpage_as_staff(self):
        self.driver.get(f'{self.live_server_url}/admin/')
        self.driver.find_element(By.ID,'id_username').send_keys("admin")
        self.driver.find_element(By.ID,'id_password').send_keys("qwerty",Keys.ENTER)

        self.driver.get(f'{self.live_server_url}/')
        self.assertTrue(len(self.driver.find_elements(By.ID,'id-admin-panel')) == 1)

    def test_access_mainpage_as_no_staff(self):
        self.driver.set_window_size(1920,1080)
        self.driver.get(f'{self.live_server_url}/authentication/signin')
        
        self.driver.find_element(By.NAME,'username').send_keys('noadmin')
        self.driver.find_element(By.NAME,'password').send_keys('qwerty')

        self.driver.find_element(By.ID,'id-signin-btn').click()

        self.driver.get(f'{self.live_server_url}/')
        self.assertTrue(len(self.driver.find_elements(By.ID,'id-admin-panel')) == 0)