from django.db import models
from django.contrib.postgres.fields import JSONField
from django.db.models.signals import post_save
from django.dispatch import receiver

from base import mods
from base.models import Auth, Key
from postproc.admin import *



QUESTION_TYPES = (
    ('normal','Votación normal'),
    ('borda', 'Votación con recuento borda'),
    ('dhondt', "Votación con sistema D'Hondt")
)

class Question(models.Model):
    desc = models.TextField()
    questionType = models.CharField(max_length=50, choices=QUESTION_TYPES, default='normal')

    def __str__(self):
        return self.desc


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    number = models.PositiveIntegerField(blank=True, null=True)
    option = models.TextField()

    def save(self):
        if not self.number:
            self.number = self.question.options.count() + 2
        return super().save()

    def __str__(self):
        return '{} ({})'.format(self.option, self.number)


class Voting(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True, null=True)
    question = models.ForeignKey(Question, related_name='voting', on_delete=models.CASCADE)

    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    pub_key = models.OneToOneField(Key, related_name='voting', blank=True, null=True, on_delete=models.SET_NULL)
    auths = models.ManyToManyField(Auth, related_name='votings')

    tally = JSONField(blank=True, null=True)
    postproc = JSONField(blank=True, null=True)

    #Estas nuevas tres variables nos servirán para calcular los porcentajes de genero que hay en una votación
    #Cada variable corresponde con el numero de votos de un genero
    num_votes_M = models.PositiveIntegerField(default=0)
    num_votes_W = models.PositiveIntegerField(default=0)
    num_votes_O = models.PositiveIntegerField(default=0)

    def create_pubkey(self):
        if self.pub_key or not self.auths.count():
            return

        auth = self.auths.first()
        data = {
            "voting": self.id,
            "auths": [ {"name": a.name, "url": a.url} for a in self.auths.all() ],
        }
        key = mods.post('mixnet', baseurl=auth.url, json=data)
        pk = Key(p=key["p"], g=key["g"], y=key["y"])
        pk.save()
        self.pub_key = pk
        self.save()

    def get_votes(self, token=''):
        # gettings votes from store
        votes = mods.get('store', params={'voting_id': self.id}, HTTP_AUTHORIZATION='Token ' + token)
        # anon votes
        return [[i['a'], i['b']] for i in votes]
    
    #La función get_userid saca una lista con todos los user_id de los miembros que han participado
    #en una votación determinada, la cual filtramos por voting_id
    def get_userid(self, token=''):
        votes = mods.get('store', params={'voting_id': self.id}, HTTP_AUTHORIZATION='Token ' + token)
        return [i['voter_id'] for i in votes]
        
    
    def get_paridad(self, userid):
        
        #Iniciamos el numero de votos a 0 antes de hacer el tally a la votación
        num_votes_M = 0
        num_votes_W = 0
        num_votes_O = 0

        #all_genders devuelve una lista con todos los Userprofiles donde aparecen [user_id, genre]
        all_genders = UserProfile.objects.all()

        for i in range(len(userid)):
            for b in all_genders:
                if (userid[i] == b.user_id):
                    if (b.genre == 'M'):
                        num_votes_M = num_votes_M + 1
                    elif (b.genre == 'W'):
                        num_votes_W = num_votes_W + 1
                    elif(b.genre == 'O'):
                        num_votes_O = num_votes_O + 1

        return [num_votes_M, num_votes_W, num_votes_O]
        
    

    def tally_votes(self, token=''):
        '''
        The tally is a shuffle and then a decrypt
        '''
        votes = self.get_votes(token)

        #userid llama a la función donde sacamos una lista con todos los user_id que han partidicpado en la votación
        userid = self.get_userid(token)
        #Calculamos el numero de votos por genero
        genre = self.get_paridad(userid)
        #Y lo devolvemos a la votación
        self.num_votes_M = genre[0]
        self.num_votes_W = genre[1]
        self.num_votes_O = genre[2]

        auth = self.auths.first()
        shuffle_url = "/shuffle/{}/".format(self.id)
        decrypt_url = "/decrypt/{}/".format(self.id)
        auths = [{"name": a.name, "url": a.url} for a in self.auths.all()]

        # first, we do the shuffle
        data = { "msgs": votes }
        response = mods.post('mixnet', entry_point=shuffle_url, baseurl=auth.url, json=data,
                response=True)
        if response.status_code != 200:
            # TODO: manage error
            pass

        # then, we can decrypt that
        data = {"msgs": response.json()}
        response = mods.post('mixnet', entry_point=decrypt_url, baseurl=auth.url, json=data,
                response=True)

        if response.status_code != 200:
            # TODO: manage error
            pass

        self.tally = response.json()
        self.save()

        self.do_postproc()

    def do_postproc(self):
        tally = self.tally
        options = self.question.options.all()

        #Debido a que el tally viene de forma ["123",["312"]], hay que separarlos ordenados, ahora quedan todos metidos en una lista
        if(self.question.questionType == "borda"):
            tallyAux = []
            for integer in tally:
                integer = str(integer)
                for i in integer:
                    tallyAux.append(int(i))
            tally = tallyAux
        #No es necesario cambiar el formato del tally para D'Hondt
        #elif(self.question.questionType == "dhondt"):

        opts = []
        for opt in options:
            if isinstance(tally, list):
                votes = tally.count(opt.number)
            else:
                votes = 0
            opts.append({
                'option': opt.option,
                'number': opt.number,
                'votes': votes,
                
            })
        
        if(self.question.questionType == "borda"):
            data = { 'type': 'IDENTITY', 'options': opts , "extra": tally, "questionType": "borda"}
        elif(self.question.questionType == "dhondt"):
            data = { 'type': 'IDENTITY', 'options': opts , "extra": tally, "questionType": "dhondt"}
        else:
            data = { 'type': 'IDENTITY', 'options': opts, "questionType": "normal"}
        postp = mods.post('postproc', json=data)

        self.postproc = postp
        self.save()

        

    def __str__(self):
        return self.name

