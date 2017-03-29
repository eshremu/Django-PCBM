from django import template
from django.template.defaultfilters import stringfilter, floatformat
from datetime import datetime, date
import random
import string

register = template.Library()


@register.filter(name='getattr')
def getattribute(obj, attr):
    """
    Returns the attribute specified by 'attr' from the object specified by
    'obj'.
    :param obj: Object to act upon
    :param attr: String containing name of attribute
    :return: Any value stored by attr in obj
    """
    return getattr(obj, attr, None)
# end def


@register.filter(name='getindex')
def getindex(obj, attr):
    """
    Returns the value at index specified by 'attr' from the list specified by
    'obj'.
    :param obj: Object to act upon (iterable)
    :param attr: String containing index number to retrieve
    :return: Any value stored by attr in obj
    """
    if attr < len(obj):
        return obj[attr]
    return None
# end def


@register.filter(name='getindexof')
def getindexof(obj, attr):
    """
    Returns the index of value specified by 'attr' from the list specified by
    'obj'.
    :param obj: Iterable object to act upon
    :param attr: String containing value to find in obj
    :return: Any value stored by attr in obj
    """
    if isinstance(obj, (list, tuple)):
        try:
            return obj.index(attr)
        except ValueError:
            return None
    return None
# end def


@register.filter(name='getkeyvalue')
def getkeyvalue(dict, key=''):
    """
    Returns the value specified by 'key' from the dictionary specified by
    'dict'.
    :param dict: Dictionary
    :param key: String containing key
    :return: Any value stored by key in dict
    """
    try:
        return dict[key]
    except KeyError:
        return None
# end def


@register.filter(name='replacewithspace')
@stringfilter
def replacewithspace(source, old):
    """
    Returns the string 'source' with all instances of 'old' replaced with a
    single blank space.
    :param source: String
    :param old: String containing value to replace
    :return: String
    """
    return source.replace(old, ' ')
# end def


@register.filter(name='replace')
@stringfilter
def replace(source, args):
    """
    Returns the string 'source' with all instances of 'old' replaced with an
    instance of 'new'.
    :param source: String
    :param args: String containing value to replace and replacement value
    separated by space
    :return: String
    """
    (old, new) = args.split()
    if old[0] == '\\' and old[1] == 'n':
        old = '\n'
    return source.replace(old, new)
# end def


@register.filter(name='replacewhitespace')
@stringfilter
def replacewhitespace(source, new):
    """
    Returns the string 'source' with all instances of whitespace replaced with
    an instance of 'new'.
    :param source: String
    :param new: String containing new character
    :return: String
    """
    return source.replace(' ', new)
# end def


@register.filter(name='iffloatformat')
def iffloatformat(value, arg=-1):
    """
    If 'value' is a float, returns a version of 'value' formatted by the
    floatformat filter in Django. Otherwise, returns 'value' un-modified.
    :param value: value to test
    :param arg: String containing desired precision of returned value
    :return: String
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
    """
    If 'value' is a datetime, returns a version of 'value' formatted according
    to the format string 'arg'. Otherwise, returns 'value' un-modified.
    :param value: value to test
    :param arg: String containing desired date format
    :return: String
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
    """
    Function to wrap a value in a string of random characters. Used for
    obfuscation.
    :param value: Value to wrap
    :return: String
    """
    early = ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits
    ) for _ in range(5))
    last = ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits
    ) for _ in range(10))
    return early + str(value) + last
# end def


@register.simple_tag
def random_string(length):
    """
    Generates string of random characters 'length' long
    :param length: String specifying desired length of random string
    :return: String
    """
    count = int(length)
    return ''.join(random.choice(string.digits + string.ascii_letters) for _ in
                   range(count))
# end def


@register.filter(name='has_group')
def has_group(user, group):
    """
    Tests if user is a member of group
    :param user: User object
    :param group: String containing name of group
    :return: Boolean
    """
    return bool(user.groups.filter(name__istartswith=group))
# end def


@register.filter(name='multiply')
def multiply(multiplicand, multiplier):
    """
    Multiplies two number
    :param multiplicand: Integer of float
    :param multiplier: Integer of float
    :return: Integer or float
    """
    if isinstance(multiplicand, (int, float)) and isinstance(multiplier,
                                                             (int, float)):
        return multiplicand * multiplier
    else:
        return None
# end def


@register.filter(name='startswith')
def startswith(string, substring):
    """
    Tests if 'string' begins with 'substring'
    :param string: String to search
    :param substring: String to find as substring
    :return: Boolean
    """
    return str(string).startswith(substring)
# end def
