from django import template

register = template.Library()

DENOM_LABELS = {
    1000: '₱1,000',
    500:  '₱500',
    200:  '₱200',
    100:  '₱100',
    50:   '₱50',
    20:   '₱20',
    10:   '₱10',
    5:    '₱5',
    1:    '₱1',
}

@register.filter
def get_denom(form, denom):
    """Return the current value of a denomination field from the form."""
    field_name = f'denom_{denom}'
    field = form[field_name] if field_name in form.fields else None
    if field is None:
        return 0
    return form.initial.get(field_name, 0) or form.data.get(field_name, 0) or 0
