from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Usage: {{ my_dict|get_item:key_var }}
    Safely gets a value from a dict in a Django template.
    Returns 0 if the key is missing.
    """
    if not isinstance(dictionary, dict):
        return 0
    return dictionary.get(key, 0)
