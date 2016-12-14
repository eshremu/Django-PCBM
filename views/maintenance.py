from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.views.decorators.csrf import ensure_csrf_cookie

from BoMConfig import menulisting, footerFile, pagetitle, supportcontact

@ensure_csrf_cookie
def Maintenance(oRequest, sTemplate='BoMConfig/maintenance.html', dContext=None, show_footer=False, *args, **kwargs):
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
    patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, pragma='no-cache', max_age=0)
    return response
# end def