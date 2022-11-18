from base.tests import BaseTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from django.utils import timezone
from voting.models import Voting, Question, QuestionOption

# Create your tests here.
class DashBoard_test_case(StaticLiveServerTestCase):

    def setUp(self):
        # Load base test functionality for decide
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

    def test_simpleVisualizer(self):
        q = Question(desc='test question')
        q.save()
        v = Voting(name='test voting', question=q)
        v.save()
        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()


        response = self.driver.get(f'{self.live_server_url}/visualizer/{v.pk}/')
        vState = self.driver.find_element(By.TAG_NAME, "h2").text
        self.assertTrue(vState, "Votación en curso")


    def test_vote_dashboard_user_positive(self):
        q = Question(desc='test questcccion')
        q.save()
        v = Voting(name='test voting', question=q)
        v.save()
        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()
        response = self.driver.get(f'{self.live_server_url}/dashboard')
        percentages_selector = WebDriverWait(self.driver, timeout=10).until(
            lambda d: d.find_element(by=By.ID, value="noadmin"))
        self.assertEqual(percentages_selector.text,"noadmin")

    def test_vote_dashboard_user_negative(self):
        q = Question(desc='test questcccion')
        q.save()
        v = Voting(name='test voting', question=q)
        v.save()
        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()
        response = self.driver.get(f'{self.live_server_url}/dashboard')
        percentages_selector = WebDriverWait(self.driver, timeout=10).until(
            lambda d: d.find_element(by=By.ID, value="noadmin"))
        self.assertNotEqual(percentages_selector.text,"www")



