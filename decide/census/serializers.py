from rest_framework import serializers
from .models import Census,CensusGroup

class CensusGroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CensusGroup
        fields = ('name',)

class CensusSerializer(serializers.HyperlinkedModelSerializer):
    group = CensusGroupSerializer()
    class Meta:
        model = Census
        fields = ('id','voting_id','voter_id','group')

