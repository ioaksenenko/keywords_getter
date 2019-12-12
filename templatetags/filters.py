import json

from django import template


register = template.Library()


@register.filter
def from_json(string):
    return json.loads(string)
