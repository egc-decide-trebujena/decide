from django.db import models

class CensusGroup(models.Model):
    name = models.CharField(max_length=256,unique=True)
    
    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

class CensusManager(models.Manager):
    def by_group(self,group):
        return super(CensusManager,self).get_queryset().filter(group=group)

class Census(models.Model):
    objects = models.Manager()
    groups = CensusManager()

    voting_id = models.PositiveIntegerField()
    voter_id = models.PositiveIntegerField()
    group = models.ForeignKey(CensusGroup,
                                blank=True, null=True,
                                related_name='census',
                                on_delete=models.SET_NULL)

    class Meta:
        unique_together = (('voting_id', 'voter_id'),)

    def __str__(self):
        selfstr = "({},{})".format(self.voting_id,self.voter_id)
        if self.group:
            selfstr = "({},{},{})".format(self.voting_id,self.voter_id,self.group)
        return selfstr
