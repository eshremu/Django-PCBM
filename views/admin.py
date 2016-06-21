from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from BoMConfig.models import DistroList
from BoMConfig.forms import DistroForm
from BoMConfig.views.landing import Default


def AdminLanding(oRequest):
    return Default(oRequest)
# end def


def MailingAdmin(oRequest):
    dContext = {
        'list': DistroList.objects.all()
    }
    sTemplate = 'BoMConfig/adminmail.html'
    return Default(oRequest, sTemplate, dContext)
# end def


def MailingChange(oRequest, id=''):
    oNew = None
    if oRequest.method == 'POST' and oRequest.POST:
        form = DistroForm(data=oRequest.POST, instance=DistroList.objects.get(id=id) if id else None)
        if form.is_valid():
            oNew = form.save()
    else:
        form = DistroForm(instance=DistroList.objects.get(id=id) if id else None)

    dContext = {
        'form': form
    }
    sTemplate = 'BoMConfig/adminmailchange.html'
    if not id and oNew:
        return redirect(reverse('bomconfig:mailchange', kwargs={'id': oNew.id}))
    else:
        return Default(oRequest, sTemplate, dContext)


def UserAdmin(oRequest):
    return Default(oRequest)
# end def
