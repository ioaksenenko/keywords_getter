import json

from django import template


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
