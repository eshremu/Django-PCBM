from django import template
from django.template.defaultfilters import stringfilter, floatformat
from datetime import datetime, date
import random
import string

register = template.Library()


@register.filter(name='getattr')
def getattribute(obj, attr):
    """ Returns the attribute specified by 'attr' from the object specified by 'obj'. """
    return getattr(obj, attr, None)
# end def


@register.filter(name='getindex')
def getindex(obj, attr):
    """ Returns the value at index specified by 'attr' from the list specified by 'obj'. """
    if attr < len(obj):
        return obj[attr]
    return None
# end def


@register.filter(name='getindexof')
def getindexof(obj, attr):
    """ Returns the index of value specified by 'attr' from the list specified by 'obj'. """
    if isinstance(obj, (list, tuple)):
        try:
            return obj.index(attr)
        except ValueError:
            return None
    return None
# end def


@register.filter(name='getkeyvalue')
def getkeyvalue(dict, key=''):
    """ Returns the attribute specified by 'attr' from the object specified by 'obj'. """
    try:
        return dict[key]
    except KeyError:
        return None
# end def


@register.filter(name='replacewithspace')
@stringfilter
def replacewithspace(source, old):
    """ Returns the string 'source' with all instances of 'old' replaced with a single blank space. """
    return source.replace(old, ' ')
# end def


@register.filter(name='replace')
@stringfilter
def replace(source, args):
    """ Returns the string 'source' with all instances of 'old' replaced with an instance of 'new'. """
    (old, new) = args.split()
    if old[0] == '\\' and old[1] == 'n':
        old = '\n'
    return source.replace(old, new)
# end def


@register.filter(name='replacewhitespace')
@stringfilter
def replacewhitespace(source, new):
    """ Returns the string 'source' with all instances of whitespace replaced with an instance of 'new'. """
    return source.replace(' ', new)
# end def


@register.filter(name='iffloatformat')
def iffloatformat(value, arg=-1):
    """ If 'value' is a float, returns a version of 'value'
        formatted by the floatformat filter in Django.
        Otherwise, returns 'value' un-modified.
    """
    try:
        assert type(value) == float
        int(arg)
    except (TypeError, AssertionError):
        return value
    else:
        return floatformat(value, arg)
# end def


@register.filter(name='ifdateformat')
def ifdateformat(value, arg="%b. %d, %Y"):
    """ If 'value' is a datetime, returns a version of 'value'
        formatted according to the format string 'arg'.
        Otherwise, returns 'value' un-modified.
    """
    try:
        assert type(value) in (datetime, date)
    except (TypeError, AssertionError):
        return value
    else:
        return value.strftime(arg)
# end def


@register.filter(name='searchscramble')
def searchscramble(value):
    early = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(5))
    last = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))
    return early + str(value) + last
# end def


@register.simple_tag
def random_string(length):
    count = int(length)
    return ''.join(random.choice(string.digits + string.ascii_letters) for i in range(count))
# end def


@register.filter(name='has_group')
def has_group(user, group):
    return bool(user.groups.filter(name__istartswith=group))
# end def
