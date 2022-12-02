from django.utils import timezone
from django.utils.dateparse import parse_datetime
import django_filters.rest_framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics
from voting.models import Voting
from census.models import Census
from dashboard.models import DashBoard, Percentages,Surveys
from django.contrib.auth import get_user_model
from .models import Vote
from .serializers import VoteSerializer
from base import mods
from base.perms import UserIsStaff



class StoreView(generics.ListAPIView):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filter_fields = ('voting_id', 'voter_id')

    def get(self, request):
        self.permission_classes = (UserIsStaff,)
        self.check_permissions(request)
        return super().get(request)

    def post(self, request):
        """
         * voting: id
         * voter: id
         * vote: { "a": int, "b": int }
        """

        vid = request.data.get('voting')

        dataux=request.data.get('opti')

        voting = mods.get('voting', params={'id': vid})

        if not voting or not isinstance(voting, list):
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)
        start_date = voting[0].get('start_date', None)
        end_date = voting[0].get('end_date', None)
        not_started = not start_date or timezone.now() < parse_datetime(start_date)
        is_closed = end_date and parse_datetime(end_date) < timezone.now()
        if not_started or is_closed:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        uid = request.data.get('voter')
        vote = request.data.get('vote')


        try:
            DashBoard.objects.get(voting=int(voting[0]['id']), voter=int(uid))
        except:
            DashBoard.objects.get_or_create(voting=int(voting[0]['id']), voter=int(uid))




        if not vid or not uid or not vote:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        # validating voter
        token = request.auth.key
        voter = mods.post('authentication', entry_point='/getuser/', json={'token': token})
        voter_id = voter.get('id', None)

        if not voter_id or voter_id != uid:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        # the user is in the census
        perms = mods.get('census/{}'.format(vid), params={'voter_id': uid}, response=True)
        if perms.status_code == 401:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        a = vote.get("a")
        b = vote.get("b")

        defs = { "a": a, "b": b }
        v, _ = Vote.objects.get_or_create(voting_id=vid, voter_id=uid,
                                          defaults=defs)
        v.a = a
        v.b = b


        v.save()

        #statistics


        voting = list(Voting.objects.values())
        total_votes = []
        new_votes = list(DashBoard.objects.all().values())

        for v in list(voting):
            sum = 0
            if v['postproc'] != None:
                for p in v['postproc']:
                    sum += int(p['votes'])

                tuple = (v['id'], sum)
                total_votes.append(tuple)



        add_votes = [n['voting'] for n in new_votes]

        set_add = set(add_votes)
        add_dict = {item: add_votes.count(item) for item in set_add}
        for key in add_dict.keys():
            tuple = (key, add_dict[key])
            total_votes.append(tuple)
        total_votes = sorted(total_votes, key=lambda x: x[0], reverse=False)
        census = list(Census.objects.values())
        dic_census = {}
        for c in census:
            if c['voting_id'] in dic_census.keys():
                dic_census[c['voting_id']] += 1
            else:
                dic_census[c['voting_id']] = 1
        list_census = list(dic_census.items())
        list_census = sorted(list_census, key=lambda x: x[0], reverse=False)
        votings_ids = [x[0] for x in total_votes]
        list_dict_census = []
        for it in list_census:
            dic_percen = {}
            if it[0] in votings_ids:
                dic_percen['votingid'] = it[0]
                dic_percen['porc'] = total_votes[votings_ids.index(it[0])][1] / it[1]
                list_dict_census.append(dic_percen)
            else:
                dic_percen['votingid'] = it[0]
                dic_percen['porc'] = 0
                list_dict_census.append(dic_percen)

        for ele in list_dict_census:
            try:
                p = Percentages.objects.get(voting=(ele['votingid']))
                p.delete()
                Percentages.objects.get_or_create(voting=int(ele['votingid']), percen=(float(ele['porc'])))
            except:
                Percentages.objects.get_or_create(voting=int(ele['votingid']), percen=(float(ele['porc'])))


        User = get_user_model()
        users = User.objects.values()
        us = list(users.all())
        usern_id = {}
        for u in us:
            usern_id[u['id']] = u['username']

        lista = []
        for i in us:
            lista.append(i['username'])


        # número de encuestas votadas por perfiles
        votes_user = {}
        for vote in new_votes:
            if vote['voter'] in votes_user.keys():

                votes_user[vote['voter']] = votes_user[vote['voter']] + 1
            else:
                votes_user[vote['voter']] = 1
        form_vu = []
        for it in votes_user.keys():
            dict = {}
            dict['voter'] = usern_id[it]
            dict['number'] = votes_user[it]
            form_vu.append(dict)
        list_form = list(form_vu)

        for f in list_form:
            try:
                p = Surveys.objects.get(voter=(f['voter']))
                p.delete()
                Surveys.objects.get_or_create(voter=(f['voter']), number=(int(f['number'])))
            except:
                Surveys.objects.get_or_create(voter=(f['voter']), number=(int(f['number'])))

        return  Response({})
