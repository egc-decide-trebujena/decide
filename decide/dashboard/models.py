from django.db import models

# Create your models here.
class DashBoard(models.Model):
    voting = models.PositiveIntegerField()
    voter = models.PositiveIntegerField()
    option = models.TextField()


    def __str__(self):
        return '{}: {},{}'.format(self.voting, self.voter,self.option)


class Percentages(models.Model):
    voting = models.PositiveIntegerField()
    percen=models.PositiveIntegerField()

    def __str__(self):
        return '{}: {},{}'.format(self.voting, self.percen)

