import json

from django import template
from keywords_getter import models


register = template.Library()


@register.filter
def from_json(string):
    return json.loads(string)


@register.filter
def is_all_exclude(keywords):
    for keyword in keywords:
        if not keyword.exclude:
            return False
    return True


@register.filter
def div(lhs, rhs):
    return lhs / rhs


@register.filter
def is_excluded(word):
    records = models.Keyword.objects.filter(word=word)
    for record in records:
        return record.exclude
