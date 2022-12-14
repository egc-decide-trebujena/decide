from urllib import response
from base import mods
from base.tests import BaseTestCase
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys



class AuthTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        mods.mock_query(self.client)
        u = User(username='voter1')
        u.set_password('123')
        u.save()

        u2 = User(username='admin')
        u2.set_password('admin')
        u2.is_superuser = True
        u2.save()

    def tearDown(self):
        self.client = None

    def test_login(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)

        token = response.json()
        self.assertTrue(token.get('token'))

    def test_login_fail(self):
        data = {'username': 'voter1', 'password': '321'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_getuser(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        response = self.client.post('/authentication/getuser/', token, format='json')
        self.assertEqual(response.status_code, 200)

        user = response.json()
        self.assertEqual(user['id'], 1)
        self.assertEqual(user['username'], 'voter1')

    def test_getuser_invented_token(self):
        token = {'token': 'invented'}
        response = self.client.post('/authentication/getuser/', token, format='json')
        self.assertEqual(response.status_code, 404)

    def test_getuser_invalid_token(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.filter(user__username='voter1').count(), 1)

        token = response.json()
        self.assertTrue(token.get('token'))

        response = self.client.post('/authentication/logout/', token, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/authentication/getuser/', token, format='json')
        self.assertEqual(response.status_code, 404)

    def test_logout(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.filter(user__username='voter1').count(), 1)

        token = response.json()
        self.assertTrue(token.get('token'))

        response = self.client.post('/authentication/logout/', token, format='json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Token.objects.filter(user__username='voter1').count(), 0)

    def test_register_bad_permissions(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        token.update({'username': 'user1'})
        response = self.client.post('/authentication/register/', token, format='json')
        self.assertEqual(response.status_code, 401)

    def test_register_bad_request(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        token.update({'username': 'user1'})
        response = self.client.post('/authentication/register/', token, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_user_already_exist(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        token.update(data)
        response = self.client.post('/authentication/register/', token, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        token.update({'username': 'user1', 'password': 'pwd1'})
        response = self.client.post('/authentication/register/', token, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            sorted(list(response.json().keys())),
            ['token', 'user_pk']
        )




        
        
        
    # #New tests for the new urls

    # def test_login_user_by_mail(self):
    #     self.client = APIClient()
    #     mods.mock_query(self.client)
    #     u = User(username='josgarmar31', email='josgarmar31@alum.us.es')
    #     u.set_password('contraseña1')
    #     u.save()
    #     data = {'username': 'josgarmar31@alum.us.es', 'password': 'contraseña1'}
    #     response = self.client.post('/authentication/signin/', data, format='json')
    #     print(response)
    #     self.assertEqual(response.status_code, 200)

    #     token = response.json()
    #     self.assertTrue(token.get('token'))


class AuthTestSelenium(StaticLiveServerTestCase):

    def setUp(self):
        # Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()
        self.client = APIClient()
        mods.mock_query(self.client)
        u = User(username='leslie', email='leslie@us.es')
        u.set_password('contraseña1')
        u.save()
        super().setUp()

    def tearDown(self):
    
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
    
    
    def test_login_by_username(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("leslie")
        self.driver.find_element_by_id("id_password").send_keys("contraseña1")
        self.driver.find_element_by_id("submit").click()
        self.assertEqual(self.driver.current_url, f"{self.live_server_url}/authentication/hello/")

    def test_login_by_email(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("leslie@us.es")
        self.driver.find_element_by_id("id_password").send_keys("contraseña1")
        self.driver.find_element_by_id("submit").click()
        self.assertEqual(self.driver.current_url, f"{self.live_server_url}/authentication/hello/")

    def test_fail_password_login_by_username(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("leslie")
        self.driver.find_element_by_id("id_password").send_keys("no es mi contraseña")
        self.driver.find_element_by_id("submit").click()
        error = self.driver.find_element_by_id("error")
        self.assertEqual(error.text, "Username or password is incorrect")

    def test_fail_password_login_by_email(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("leslie@us.es")
        self.driver.find_element_by_id("id_password").send_keys("no es mi contraseña")
        self.driver.find_element_by_id("submit").click()
        error = self.driver.find_element_by_id("error")
        self.assertEqual(error.text, "Username or password is incorrect")

    def test_fail_username_login_by_username(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("niidea")
        self.driver.find_element_by_id("id_password").send_keys("contraseña1")
        self.driver.find_element_by_id("submit").click()
        error = self.driver.find_element_by_id("error")
        self.assertEqual(error.text, "Username or password is incorrect")

    def test_fail_email_login_by_email(self):
        self.driver.get(f"{self.live_server_url}/authentication/signin/")
        self.driver.find_element_by_id("id_username").send_keys("nosequieneres@us.es")
        self.driver.find_element_by_id("id_password").send_keys("contraseña1")
        self.driver.find_element_by_id("submit").click()
        error = self.driver.find_element_by_id("error")
        self.assertEqual(error.text, "Username or password is incorrect")



class TranslationCase(StaticLiveServerTestCase):
    
    def setUp(self):
        #Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()


        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)


        super().setUp() 
        
    def tearDown(self):           

        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        
    
    def test_french_translation(self):

        self.driver.get("http://127.0.0.1:8000/authentication/signin/")
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select > option:nth-child(4)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        username_label = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > div > form > p:nth-child(2) > label"))
        self.assertEqual(username_label.text, "Nom d'utilisateur :")
        
    def test_german_translation(self):

        self.driver.get("http://127.0.0.1:8000/authentication/signin/")
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select > option:nth-child(3)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        username_label = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > div > form > p:nth-child(2) > label"))
        self.assertEqual(username_label.text, "Benutzername:")
        
    def test_spanish_translation(self):

        self.driver.get("http://127.0.0.1:8000/authentication/signin/")
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select > option:nth-child(2)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        username_label = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > div > form > p:nth-child(2) > label"))
        self.assertEqual(username_label.text, "Nombre de usuario:")

    def test_english_translation(self):

        self.driver.get("http://127.0.0.1:8000/authentication/signin/")
        
        language_selector = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select"))
        language_selector.click()
        selected_language = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > footer > form > select > option:nth-child(1)"))
        selected_language.click()
        change_language_button = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.ID, value="change-language-button"))
        change_language_button.click()
        username_label = WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(by=By.CSS_SELECTOR, value="body > div > form > p:nth-child(2) > label"))
        self.assertEqual(username_label.text, "Username:")

