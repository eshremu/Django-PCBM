"""
Views used in tool maintenance mode
"""

from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.views.decorators.csrf import ensure_csrf_cookie

from BoMConfig import menulisting, footerFile, pagetitle, supportcontact

@ensure_csrf_cookie
def Maintenance(oRequest, sTemplate='BoMConfig/maintenance.html', dContext=None,
                show_footer=False, *args, **kwargs):
    """
    View for showing maintenance page when tool is in maintenance mode.
    :param oRequest: Django HTTP request object
    :param sTemplate: string specifying template to render
    :param dContext: dictionary of key/values to pass to the template
    :param show_footer: boolean to determine if footer should be shown in
                        template
    :param args: list of positional arguments
    :param kwargs: dictionary of keyword arguments
    :return: Django HTTPResponse object
    """
    sUserId = None

    if oRequest.user.is_authenticated() and oRequest.user.is_active:
        sUserId = oRequest.user.username
    # end if

    if not dContext:
        dContext = {}

    dNewContext = {}
    dNewContext.update([
        ('menulisting', menulisting,),
        ('header_template', 'BoMConfig/maintheader.html',),
        ('footer_template', footerFile,),
        ('pagetitle', pagetitle,),
        ('supportcontact', supportcontact,),
        ('userId', sUserId,),
        ('show_footer', show_footer,),
    ])
    dNewContext.update(dContext)

    response = render(oRequest, sTemplate, dNewContext)
    patch_cache_control(response, no_cache=True, no_store=True,
                        must_revalidate=True, pragma='no-cache', max_age=0)
    return response
# end def