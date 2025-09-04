from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def replace(value, args):
    """Usage: {{ value|replace:"old,new" }}"""
    old, new = args.split(',')
    return value.replace(old, new)