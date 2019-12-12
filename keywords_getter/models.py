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
