import json

from django.db import models


class Course(models.Model):
    cid = models.IntegerField(default=0)
    name = models.CharField(max_length=255, default='')
    sdo = models.CharField(max_length=255, default='')
    keywords = models.CharField(max_length=255, default='')

    def __str__(self):
        return json.dumps({
            'cid': self.cid,
            'name': self.name,
            'sdo': self.sdo,
            'keywords': self.keywords,
        })


class Keyword(models.Model):
    word = models.CharField(max_length=255, default='')
    exclude = models.BooleanField(default=False)

    def __str__(self):
        return json.dumps({
            'word': self.word,
            'exclude': self.exclude
        })
