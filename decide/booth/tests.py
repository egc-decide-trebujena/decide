from django.contrib.auth.models import User
from base.tests import BaseTestCase
from django.utils import timezone
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.keys import Keys
from voting.models import Voting, Question, QuestionOption
from census.models import Census
from mixnet.models import Auth

from selenium import webdriver
from selenium.webdriver.common.by import By

class BoothPageTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()

        Voting.objects.all().delete()

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
        password = 'password'

        u=User.objects.create_superuser('Enriqu', 'myemail@test.com', password)

        c=Census(voting_id=v.id,voter_id=u.id)
        c.save()

        options = webdriver.ChromeOptions()
        options.headless = False
        self.driver = webdriver.Chrome(options=options)

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        self.census = None
        self.user = None

    def test_dashboard_booth(self):
        print(Voting.objects.get(id=1).id)
        self.driver.get(f'{self.live_server_url}/admin/voting/voting')
        self.driver.find_element(By.ID, "id_username").send_keys('Enriqu')
        self.driver.find_element(By.ID, "id_password").send_keys('password',Keys.ENTER)
        self.driver.get(f'{self.live_server_url}/')
        self.assertTrue(len(self.driver.find_elements(By.ID,'voting-1'))==1)
