################################################################

from django import template

from .. import utils

################################################################

register = template.Library()

################################################################


@register.filter
def unslugify(value):
    return utils.unslugify(value)


################################################################
