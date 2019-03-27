"""
Views related to in-tool, user/customer level administration.
"""

from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connections, IntegrityError
from django.http import HttpResponse, Http404

# S-10578:-Admin to unlock a locked config: added below to import user details
from django.contrib.auth.models import User

import json
import itertools
from itertools import chain

# S-10578:-Admin to unlock a locked config: added below to import session details
from django.contrib.sessions.models import Session

from BoMConfig.models import DistroList, ApprovalList, User_Customer, Header,  REF_CUSTOMER, REF_PRODUCT_AREA_1, REF_SPUD, REF_PROGRAM,\
    REF_RADIO_BAND, REF_RADIO_FREQUENCY, REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, REF_TECHNOLOGY, HeaderLock
from BoMConfig.forms import DistroForm, UserForm, UserAddForm, CustomerApprovalLevelForm
from BoMConfig.views.landing import Default


@login_required
def AdminLanding(oRequest):
    return Default(oRequest, 'BoMConfig/adminlanding.html')
# end def

# Added below function for S-07533 New sub-tab drop-down admin base template creation
@login_required
def DropDownAdmin(oRequest):
    """
    Landing view for administration of dropdowns
    related items
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    return Default(oRequest, 'BoMConfig/admindropdown.html')
# end def

@login_required
def UnlockAdmin(oRequest):
    """
    Landing view for administration of dropdowns
    related items
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    dContext = {
        'locked_config':  HeaderLock.objects.filter(session_key__isnull=False),
        'errors_config': oRequest.session.pop('errors_config', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminunlock.html',dContext)
# end def

@login_required
def UnlockConfigAdmin(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    if oRequest.method == 'POST' and oRequest.POST:
        HeaderLock.objects.filter(header=oRequest.POST.get('lockedconfigid')).update(session_key = None)
        oRequest.session['errors_config'] = ['Configuration Unlocked successfully']
        oRequest.session['message_type_is_error'] = False

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end def

# S-05909 : Edit dropdown option for BoM Entry Header - SPUD :Added below for the landing page of Spud
@login_required
def SpudAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    dContext = {
            'spud': REF_SPUD.objects.filter(is_inactive=0),
            'errors': oRequest.session.pop('errors', None),
            'message_type_is_error': oRequest.session.pop('message_is_error',False)
    }

    return Default(oRequest, 'BoMConfig/adminspud.html', dContext)
# end def

# S-05909 : Edit dropdown option for BoM Entry Header - SPUD :Added below for the Adding a new Spud
@login_required
def SpudAdd(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    ospud = REF_SPUD()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_SPUD.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            ospud = REF_SPUD(name=oRequest.POST.get('data'))
            ospud.save()
            oRequest.session['errors'] = ['Spud Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Spud with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05909 : Edit dropdown option for BoM Entry Header - SPUD :Added below for the Editing Spud
@login_required
def SpudEdit(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    ospud = REF_SPUD()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_SPUD.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            REF_SPUD.objects.filter(pk=oRequest.POST.get('spudid')).update(
                    name=oRequest.POST.get('data'))
            oRequest.session['errors'] = ['Spud Changed successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Spud with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05909 : Edit dropdown option for BoM Entry Header - SPUD :Added below for the Deleting a Spud
@login_required
def SpudDelete(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    ospud = REF_SPUD()

    if oRequest.method == 'POST' and oRequest.POST:
        REF_SPUD.objects.filter(pk=oRequest.POST.get('spudid')).update(
                is_inactive=1)
        oRequest.session['errors'] = ['Spud Deleted successfully']
        oRequest.session['message_type_is_error'] = False
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05903 : Edit drop down option for BoM Entry Header - Program : Added below for landing page of Program
@login_required
def ProgramAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    # to find all the CUs
    aAvailableCU = REF_CUSTOMER.objects.all()

    dContext = {
        'program': REF_PROGRAM.objects.filter(is_inactive=0),
        'culist' : aAvailableCU,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminprogram.html', dContext)

# end def

# S-05903 : Edit drop down option for BoM Entry Header - Program: Added below for Adding a new Program
@login_required
def ProgramAdd(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    ospud = REF_PROGRAM()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_PROGRAM.objects.filter(name=oRequest.POST.get('data'),parent_id=oRequest.POST.get('cuval'),is_inactive=0):
            ospud = REF_PROGRAM(name=oRequest.POST.get('data'), parent_id=oRequest.POST.get('cuval'))
            ospud.save()
            oRequest.session['errors'] = ['Program Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Program with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05903 : Edit drop down option for BoM Entry Header - Program: Added below for Editing a new Program
@login_required
def ProgramEdit(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    ospud = REF_PROGRAM()

    if oRequest.method == 'POST' and oRequest.POST:
        # int(record) for record in json.loads(oRequest.POST.get('data'))
        if not REF_PROGRAM.objects.filter(name=oRequest.POST.get('data'), parent_id=oRequest.POST.get('cuid'),is_inactive=0):
            REF_PROGRAM.objects.filter(pk=oRequest.POST.get('progid')).update(
                name=oRequest.POST.get('data'), parent_id=oRequest.POST.get('cuid'))
            oRequest.session['errors'] = ['Program Changed successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Program with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05903 : Edit drop down option for BoM Entry Header - Program: Added below for Deleting a new Program
@login_required
def ProgramDelete(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    oprog = REF_SPUD()

    if oRequest.method == 'POST' and oRequest.POST:
        REF_PROGRAM.objects.filter(pk=oRequest.POST.get('progid')).update(
                is_inactive=1)
        oRequest.session['errors'] = ['Program Deleted successfully']
        oRequest.session['message_type_is_error'] = False

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05906 : Edit drop down option for BoM Entry Header - Product Area 1: Added below for Adding a new Product Area 1
@login_required
def ProductArea1Admin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'productarea1': REF_PRODUCT_AREA_1.objects.filter(is_inactive=0),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminproductarea1.html', dContext)
# end def

# S-05906 : Edit drop down option for BoM Entry Header - Product Area 1: Added below for Editing Product Area 1
@login_required
def ProductArea1Add(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    oproductarea1 = REF_PRODUCT_AREA_1()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_PRODUCT_AREA_1.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            oproductarea1 = REF_PRODUCT_AREA_1(name=oRequest.POST.get('data'))
            oproductarea1.save()
            oRequest.session['errors'] = ['Product Area 1 Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Product Area 1 with same name already exists.Please choose new name']
            oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
         raise Http404()
    # end if

# end if
# end def

# S-05906 : Edit drop down option for BoM Entry Header - Product Area 1: Added below for Editing a Product Area 1
@login_required
def ProductArea1Edit(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    oproductarea1 = REF_PRODUCT_AREA_1()

    if oRequest.method == 'POST' and oRequest.POST:
        # int(record) for record in json.loads(oRequest.POST.get('data'))
        if not REF_PRODUCT_AREA_1.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            REF_PRODUCT_AREA_1.objects.filter(pk=oRequest.POST.get('productarea1id')).update(
                    name=oRequest.POST.get('data'))
            oRequest.session['errors'] = ['Product Area 1 Changed successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Product Area 1 with same this name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05906 : Edit drop down option for BoM Entry Header - Product Area 1: Added below for Deleting a Product Area 1
@login_required
def ProductArea1Delete(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_PRODUCT_AREA_2.objects.filter(parent_id=oRequest.POST.get('productarea1id')):
                REF_PRODUCT_AREA_1.objects.filter(pk=oRequest.POST.get('productarea1id')).update(
                        is_inactive=1)
                oRequest.session['errors'] = ['Product Area 1 Deleted successfully']
                oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Selected Product Area 1 is associated with multiple Product Area2. So could not proceed with deletion']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05907 : Edit drop down option for BoM Entry Header - Product Area 2: Added below for the landing page of Product Area 2
@login_required
def ProductArea2Admin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    dContext = {
        'productarea2': REF_PRODUCT_AREA_2.objects.filter(is_inactive=0),
        'productarea1': REF_PRODUCT_AREA_1.objects.filter(is_inactive=0),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error',False)
    }
    return Default(oRequest, 'BoMConfig/adminproductarea2.html', dContext)
# end def

# S-05907 : Edit drop down option for BoM Entry Header - Product Area 2: Added below for Adding a new Product Area 2
@login_required
def ProductArea2Add(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    oproductarea2 = REF_PRODUCT_AREA_2()
    if oRequest.method == 'POST' and oRequest.POST:

        if not REF_PRODUCT_AREA_2.objects.filter(name=oRequest.POST.get('data'), parent_id=oRequest.POST.get('prodlist'), is_inactive=0):
            oproductarea2 = REF_PRODUCT_AREA_2(name=oRequest.POST.get('data'),parent_id=oRequest.POST.get('prodlist'))
            oproductarea2.save()
            oRequest.session['errors'] = ['Product Area 2 Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Product Area 2 with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
         raise Http404()
    # end if

# end if
# end def

# S-05907 : Edit drop down option for BoM Entry Header - Product Area 2: Added below for Editing a Product Area 2
@login_required
def ProductArea2Edit(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_PRODUCT_AREA_2.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            REF_PRODUCT_AREA_2.objects.filter(pk=oRequest.POST.get('productarea2id')).update(
                    name=oRequest.POST.get('data'))
            oRequest.session['errors'] = ['Product Area 2 Changed successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Product Area 2 with same name already exists. Please choose different name.']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05907 : Edit drop down option for BoM Entry Header - Product Area 2: Added below for Deleting a Product Area 2
@login_required
def ProductArea2Delete(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    if oRequest.method == 'POST' and oRequest.POST:
        REF_PRODUCT_AREA_2.objects.filter(pk=oRequest.POST.get('productarea2id')).update(
                is_inactive=1)
        oRequest.session['errors'] = ['Product Area 2 Deleted successfully']
        oRequest.session['message_type_is_error'] = False
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05905 : Edit drop down option for BoM Entry Header - Technology: Added below for the landing page of Technology
@login_required
def TechnologyAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'technology': REF_TECHNOLOGY.objects.filter(is_inactive=0),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/admintechnology.html', dContext)
# end def

# S-05905 : Edit drop down option for BoM Entry Header - Technology: Added below for the Adding a new Technology
@login_required
def TechnologyAdd(oRequest):
    """
    Landing view for administration to add technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    otechnology = REF_TECHNOLOGY()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_TECHNOLOGY.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            otechnology = REF_TECHNOLOGY(name=oRequest.POST.get('data'))
            otechnology.save()
            oRequest.session['errors'] = ['Technology Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Technology with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05905 : Edit drop down option for BoM Entry Header - Technology: Added below for the Editing of Technology
@login_required
def TechnologyEdit(oRequest):
    """
    Landing view for administration to edit technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    otechnology = REF_TECHNOLOGY()

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_TECHNOLOGY.objects.filter(name=oRequest.POST.get('data'),is_inactive=0):
            REF_TECHNOLOGY.objects.filter(pk=oRequest.POST.get('technologyid')).update(
                name=oRequest.POST.get('data'))
            oRequest.session['errors'] = ['Technology Changed successfully']
            oRequest.session['message_type_is_error'] = False

        else:
            oRequest.session['errors'] = ['Technology with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05905 : Edit drop down option for BoM Entry Header - Technology: Added below for Deleting of Technology
@login_required
def TechnologyDelete(oRequest):
    """
    Landing view for administration to delete technologies
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    otechnology = REF_TECHNOLOGY()

    if oRequest.method == 'POST' and oRequest.POST:
        REF_TECHNOLOGY.objects.filter(pk=oRequest.POST.get('technologyid')).update(
                is_inactive=1)
        oRequest.session['errors'] = ['Technology Deleted successfully']
        oRequest.session['message_type_is_error'] = False
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band: Added below for the landing page of Radio Frequency/Band
@login_required
def RFAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    # D-04685-Error with Band/Frequency:- Changed the logic below from sending data for 2 different tables to combining the 2 different datasets
    # into 1 and send the resultset as a whole
    rf = REF_RADIO_FREQUENCY.objects.filter(is_inactive=0)
    rb = REF_RADIO_BAND.objects.filter(is_inactive=0)

    resulttable =[]
    # D-04685-Error with Band/Frequency:- Forms a tuple with data from both radioband and radio frequency table and sends the same in dContext
    for i in range(0,len(rf)):
        resulttable.append((rf[i],rb[i]))

    dContext = {
        'radio_freq_band': resulttable,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminradiofrequency.html', dContext)
# end def

# S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band: Added below for Adding of RF/RB
@login_required
def RFAdd(oRequest):
    """
    Landing view for administration to add radio frequencies/band
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    if oRequest.method == 'POST' and oRequest.POST:
        if not REF_RADIO_BAND.objects.filter(name=oRequest.POST.get('radioband'), is_inactive=0) :
            ofreq = REF_RADIO_FREQUENCY(name=oRequest.POST.get('radiofreq'))
            oband = REF_RADIO_BAND(name=oRequest.POST.get('radioband'))
            ofreq.save()
            oband.save()
            oRequest.session['errors'] = ['Radio Frequency/Band Added successfully']
            oRequest.session['message_type_is_error'] = False
        else:
            oRequest.session['errors'] = ['Radio Band with same name already exists. Please choose different name']
            oRequest.session['message_type_is_error'] = True
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band: Added below for Editing of RF/RB
@login_required
def RFEdit(oRequest):
    """
    Landing view for administration to edit radio frequencies/band
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    if oRequest.method == 'POST' and oRequest.POST:
        # D-04685-Error with Band/Frequency:- picked out the below 3 lines from the if condition below that checks if the same radio band name exists or not.
        # As radio frequency can be same for different band names, so it need not be under the if condition
        REF_RADIO_FREQUENCY.objects.filter(pk=oRequest.POST.get('radiofreqbandid')).update(
            name=oRequest.POST.get('radiofreq'))
        oRequest.session['errors'] = ['Radio Frequency/Band Changed successfully']
        oRequest.session['message_type_is_error'] = False

        # How to get the name from the object -:Ex:- [<REF_RADIO_BAND: rb3/21>] = to = rb3/21
        for obj in REF_RADIO_BAND.objects.filter(pk=oRequest.POST.get('radiofreqbandid')):
          currentbandname = obj.name

        if currentbandname != oRequest.POST.get('radioband') :
            if not REF_RADIO_BAND.objects.filter(name=oRequest.POST.get('radioband'), is_inactive=0):

                REF_RADIO_BAND.objects.filter(pk=oRequest.POST.get('radiofreqbandid')).update(
                    name=oRequest.POST.get('radioband'))
                oRequest.session['errors'] = ['Radio Frequency/Band Changed successfully']
                oRequest.session['message_type_is_error'] = False
            else:
                oRequest.session['errors'] = ['Radio Band with same name already exists. Please choose different name']
                oRequest.session['message_type_is_error'] = True

        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

# S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band: Added below for Deleting of RF/RB
@login_required
def RFDelete(oRequest):
    """
    Landing view for administration to delete radio frequencies/band
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    if oRequest.method == 'POST' and oRequest.POST:
        # int(record) for record in json.loads(oRequest.POST.get('data'))
        REF_RADIO_FREQUENCY.objects.filter(pk=oRequest.POST.get('radiofreqbandid')).update(
                is_inactive=1)
        REF_RADIO_BAND.objects.filter(pk=oRequest.POST.get('radiofreqbandid')).update(
            is_inactive=1)
        oRequest.session['errors'] = ['Radio Frequency/Band Deleted successfully']
        oRequest.session['message_type_is_error'] =False
        return HttpResponse()
    else:
        raise Http404()
    # end if

# end if
# end def

@login_required
def MailingAdmin(oRequest):
    """
    Landing view for administration of distribution lists and other mailing
    related items
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'list': DistroList.objects.all()
    }
    sTemplate = 'BoMConfig/adminmail.html'
    return Default(oRequest, sTemplate, dContext)
# end def


@login_required
def MailingChange(oRequest, iRecordId=''):
    """
    View for creating new or editing/viewing existing DistroList objects
    :param oRequest: Django request object
    :param iRecordId: ID value of existing DistroForm object
    :return: HTML response via Default function
    """
    oNew = None

    # If the request is a POST request, we are saving a new record
    # or editing an existing record
    if oRequest.method == 'POST' and oRequest.POST:
        # Create an instance of a DistroForm using the data sent in post
        # If iRecordId was provided, link the form instance to the existing
        # DistroList object
        form = DistroForm(data=oRequest.POST, instance=DistroList.objects.get(id=iRecordId) if iRecordId else None)
        if form.is_valid():
            oNew = form.save()
    else:
        # Create an instance of DistroForm using data stored in an existing
        # DistroList object if iRecordId was provided, otherwise create a blank
        # DistroForm instance
        form = DistroForm(instance=DistroList.objects.get(id=iRecordId) if iRecordId else None)

    dContext = {
        'form': form,
        'grappelli_installed': 'grappelli' in settings.INSTALLED_APPS
    }
    sTemplate = 'BoMConfig/adminmailchange.html'

    # If this request was a creation of a new DistroList, redirect to this view
    # with the new DistroList's id provided
    if not iRecordId and oNew:
        return redirect(reverse('bomconfig:mailchange', kwargs={'iRecordId': oNew.id}))
    else:
        return Default(oRequest, sTemplate, dContext)
# end def


@login_required
def UserAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    dContext = {
        'users': set(
            get_user_model().objects.filter(groups__name__startswith='BOM_').exclude(groups__name__startswith='BOM_BPMA')
        ),
        'approval_wait': Header.objects.filter(
            configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0),
        'usercu': User_Customer.objects.all(),
        'usercuname': REF_CUSTOMER.objects.all(),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False),
        'customer_list': ['All'] + [obj.name for obj in
                                    REF_CUSTOMER.objects.all()],

    }
    # print(dContext)
    return Default(oRequest, 'BoMConfig/adminuser.html', dContext)
# end def

# S-07204 Refine User Admin page added delete button logic  in user admin page
@login_required
def UserDelete(oRequest):

    if oRequest.method == 'POST' and oRequest.POST:
        # When deleting a user, we don't actually remove the user from
        # the system, because they may have access to multiple tools.
        # Instead, we just remove the user from any groups that have
        # access permissions to this tool
        for record in json.loads(oRequest.POST.get('data')):
            oUser = get_user_model().objects.get(username=record)
            oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
            oRequest.session['errors'] = ['User deleted successfully']
            oRequest.session['message_is_error'] = False

        return HttpResponse()
    else:
        raise Http404()
    # end if

@login_required
def UserAdd(oRequest):
    """
    View for adding new users to the tool (and system if they do not exist)
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    # Create empty form instance
    oForm = UserAddForm()

    # If this is a form submission
    if oRequest.method == 'POST' and oRequest.POST:
        # Create a form instance using the submitted data
        oForm = UserAddForm(oRequest.POST)
        if oForm.is_valid():
            # Check if signum entered references a completely new user or just a user not in the tool
            if not get_user_model().objects.filter(username=oForm.cleaned_data['signum']):
                # Create New user by signum and default password
                newUser = get_user_model()(username=oForm.cleaned_data['signum'])
                newUser.set_password('123')
                newUser.save()
            else:
                # Retrieve existing user by signum
                newUser = get_user_model().objects.get(username=oForm.cleaned_data['signum'])

            # Redirect to UserChange view
            return redirect(reverse('bomconfig:userchange', kwargs={'iUserId': newUser.pk}))

    dContext={
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuseradd.html', dContext)
# end def


@login_required
def UserChange(oRequest, iUserId=''):
    """

    :param oRequest: Django request object
    :param iUserId: ID number of user object being changed
    :return: HTML response via Default function
    """

    # Find and retrieve the User object by iUserId
    if get_user_model().objects.filter(pk=iUserId):
        oUser = get_user_model().objects.get(pk=iUserId)

        # Create form defaults from User object information
        dInitial = {
            'signum': oUser.username,
            'first_name': oUser.first_name,
            'last_name': oUser.last_name,
            'email': oUser.email,
            'assigned_group': oUser.groups.filter(name__startswith='BOM_') if oUser.groups.filter(name__startswith='BOM_') else None
        }

    # Added for CU initial checked view
        aMatrixEntries = User_Customer.objects.filter(user_id=iUserId)
        dInitial['customer'] = list([str(oSecMat.customer_id) for oSecMat in aMatrixEntries.filter(user_id=iUserId)])

        # If this request is a form submission
        if oRequest.method == 'POST' and oRequest.POST:
            # Build a UserForm instance from the data submitted, using data in
            # dInitial to fill in blank fields.  It must be done this way
            # because UserForm is a standard Form object and not a ModelForm
            # object
            oForm = UserForm(oRequest.POST, initial=dInitial)

            # Save changes to user
            if oRequest.POST['action'] == 'save':
                if oForm.is_valid():
                    if oForm.has_changed():
                        # Process changes
                        for field in oForm.changed_data:
                            if field in ('signum', 'first_name', 'last_name', 'email'):
                                # Update user object personal info values
                                if field == 'signum':
                                    oUser.username = oForm.cleaned_data[field]

                                if field == 'first_name':
                                    oUser.first_name = oForm.cleaned_data[field]

                                if field == 'last_name':
                                    oUser.last_name = oForm.cleaned_data[field]

                                if field == 'email':
                                    oUser.email = oForm.cleaned_data[field]
                            elif field == 'assigned_group':
                                oUser.groups.add(*tuple(oForm.cleaned_data[field]))
                                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_').exclude(pk__in=oForm.cleaned_data[field])))
                            # end if
                    # S-06578: Added For CU options in Admin page
                            elif field == 'customer':
                                UserCustomerRelationEntries = User_Customer.objects.filter(user_id=iUserId)
                                aNewUserCustomerRelationEntries = []

                                for iCustomer in oForm.cleaned_data[field]:
                                    for obj in  REF_CUSTOMER.objects.filter(id=iCustomer):
                                        UserCustomerName = obj.name
                                    if UserCustomerRelationEntries.filter(customer_id=iCustomer,is_deleted=0,customer_name= UserCustomerName):
                                        aNewUserCustomerRelationEntries.append(
                                            UserCustomerRelationEntries.get(customer_id=iCustomer, is_deleted=0,customer_name= UserCustomerName))
                                    else:
                                        aNewUserCustomerRelationEntries.append(User_Customer(
                                            user_id=iUserId,
                                            customer_id=iCustomer,
                                            customer_name=UserCustomerName,
                                            is_deleted=0))
                                    # end if
                                # end for

                                for oSecMatrix in UserCustomerRelationEntries:
                                    if oSecMatrix not in aNewUserCustomerRelationEntries:
                                        oSecMatrix.delete()

                                for oSecMatrix in aNewUserCustomerRelationEntries:
                                    oSecMatrix.save()

                        # end for
                        oUser.save()
                        oRequest.session['errors'] = ['User changed successfully']
                        oRequest.session['message_is_error'] = False
                    else:
                        oRequest.session['errors'] = ['No changes detected']
                        oRequest.session['message_is_error'] = False
                    # end if
                # end if
            # Delete user
            elif oRequest.POST['action'] == 'delete':
                # When deleting a user, we don't actually remove the user from
                # the system, because they may have access to multiple tools.
                # Instead, we just remove the user from any groups that have
                # access permissions to this tool
                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
                oRequest.session['errors'] = ['User deleted successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:useradmin'))
            # end if
        else:
            # Build a UserForm instance from the data in dInitial
            oForm = UserForm(initial=dInitial)
    else:
        # If no such User is found, create an error and redirect to the UserAdd
        # view
        oRequest.session['errors'] = ['User not found']
        oRequest.session['message_is_error'] = True
        return redirect(reverse('bomconfig:useradd'))
    # end if

    dContext = {
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuserchange.html', dContext)
# end def

# S-10578:-Admin to unlock a locked config: Added below function to show user details when clicked on signum from unlock page
# This is a similar function of UserChange. Added this function separately as the parameter passed there was the userid but here we
# are passing the username(signum)
@login_required
def UserChangeFromUnlock(oRequest, iUserName=''):
    """

    :param oRequest: Django request object
    :param iUserId: ID number of user object being changed
    :return: HTML response via Default function
    """

    # Find and retrieve the User object by iUserId
    if get_user_model().objects.filter(username=iUserName):
        oUser = get_user_model().objects.get(username=iUserName)

        # Create form defaults from User object information
        dInitial = {
            'signum': oUser,
            'first_name': oUser.first_name,
            'last_name': oUser.last_name,
            'email': oUser.email,
            'assigned_group': oUser.groups.filter(name__startswith='BOM_') if oUser.groups.filter(name__startswith='BOM_') else None
        }

    # Added for CU initial checked view
        aMatrixEntries = User_Customer.objects.filter(user_id=oUser.id)
        dInitial['customer'] = list([str(oSecMat.customer_id) for oSecMat in aMatrixEntries.filter(user_id=oUser.id)])

        # If this request is a form submission
        if oRequest.method == 'POST' and oRequest.POST:
            # Build a UserForm instance from the data submitted, using data in
            # dInitial to fill in blank fields.  It must be done this way
            # because UserForm is a standard Form object and not a ModelForm
            # object
            oForm = UserForm(oRequest.POST, initial=dInitial)

            # Save changes to user
            if oRequest.POST['action'] == 'save':
                if oForm.is_valid():
                    if oForm.has_changed():
                        # Process changes
                        for field in oForm.changed_data:
                            if field in ('signum', 'first_name', 'last_name', 'email'):
                                # Update user object personal info values
                                if field == 'signum':
                                    oUser.username = oForm.cleaned_data[field]

                                if field == 'first_name':
                                    oUser.first_name = oForm.cleaned_data[field]

                                if field == 'last_name':
                                    oUser.last_name = oForm.cleaned_data[field]

                                if field == 'email':
                                    oUser.email = oForm.cleaned_data[field]
                            elif field == 'assigned_group':
                                oUser.groups.add(*tuple(oForm.cleaned_data[field]))
                                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_').exclude(pk__in=oForm.cleaned_data[field])))
                            # end if
                    # S-06578: Added For CU options in Admin page
                            elif field == 'customer':
                                UserCustomerRelationEntries = User_Customer.objects.filter(user_id=oUser.id)
                                aNewUserCustomerRelationEntries = []

                                for iCustomer in oForm.cleaned_data[field]:
                                    for obj in  REF_CUSTOMER.objects.filter(id=iCustomer):
                                        UserCustomerName = obj.name
                                    if UserCustomerRelationEntries.filter(customer_id=iCustomer,is_deleted=0,customer_name= UserCustomerName):
                                        aNewUserCustomerRelationEntries.append(
                                            UserCustomerRelationEntries.get(customer_id=iCustomer, is_deleted=0,customer_name= UserCustomerName))
                                    else:
                                        aNewUserCustomerRelationEntries.append(User_Customer(
                                            user_id=oUser.id,
                                            customer_id=iCustomer,
                                            customer_name=UserCustomerName,
                                            is_deleted=0))
                                    # end if
                                # end for

                                for oSecMatrix in UserCustomerRelationEntries:
                                    if oSecMatrix not in aNewUserCustomerRelationEntries:
                                        oSecMatrix.delete()

                                for oSecMatrix in aNewUserCustomerRelationEntries:
                                    oSecMatrix.save()

                        # end for
                        oUser.save()
                        oRequest.session['errors'] = ['User changed successfully']
                        oRequest.session['message_is_error'] = False
                    else:
                        oRequest.session['errors'] = ['No changes detected']
                        oRequest.session['message_is_error'] = False
                    # end if
                # end if
            # Delete user
            elif oRequest.POST['action'] == 'delete':
                # When deleting a user, we don't actually remove the user from
                # the system, because they may have access to multiple tools.
                # Instead, we just remove the user from any groups that have
                # access permissions to this tool
                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
                oRequest.session['errors'] = ['User deleted successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:useradmin'))
            # end if
        else:
            # Build a UserForm instance from the data in dInitial
            oForm = UserForm(initial=dInitial)
    else:
        # If no such User is found, create an error and redirect to the UserAdd
        # view
        oRequest.session['errors'] = ['User not found']
        oRequest.session['message_is_error'] = True
        return redirect(reverse('bomconfig:useradd'))
    # end if

    dContext = {
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuserchange.html', dContext)
# end def

@login_required
def ApprovalAdmin(oRequest):
    """
    Landning view for administration of ApprovalList objects, used to
    determine which levels of approval are required for records per each
    customer.
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'list': ApprovalList.objects.all(),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    sTemplate = 'BoMConfig/adminapproval.html'
    return Default(oRequest, sTemplate, dContext)


@login_required
def ApprovalChange(oRequest, iObjId=None):
    """
    View for adding or changing ApprovalList objects
    :param oRequest: Django request object
    :param iObjId:
    :return: HTML response via Default function
    """
    dInit = {}
    oApproveList = None

    # If changing an existing ApprovalList, retrieve the object and build the
    # forms initial data
    if iObjId:
        try:
            oApproveList = ApprovalList.objects.get(id=iObjId)
            dInit.update({
                'customer': oApproveList.customer,
                'required_choices': oApproveList.required.split(','),
                'optional_choices': oApproveList.optional.split(','),
                'disallowed_choices': oApproveList.disallowed.split(',')
            })
        except ApprovalList.DoesNotExist:
            return redirect(reverse('bomconfig:approvaladd'))

    # Create a CustomerApprovalLevelForm instance, and use data from the
    # existing ApprovalList object if we are changing it
    form = CustomerApprovalLevelForm(initial=dInit, readonly=bool(oApproveList))

    # if this request is a form submission
    if oRequest.POST:
        # Create a CustomerApprovalLevelForm instance, and use data from the
        # existing ApprovalList object if we are changing it
        form = CustomerApprovalLevelForm(oRequest.POST, readonly=bool(oApproveList))
        if form.is_valid():
            if oApproveList:
                # Update and save existing object
                oApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oApproveList.save()
                oRequest.session['errors'] = ['Changes saved successfully']
                oRequest.session['message_is_error'] = False
            else:
                # Populate and save new object, then redirect to ApprovalChange
                # view with id of new ApprovalList object
                oNewApproveList = ApprovalList()
                oNewApproveList.customer = form.cleaned_data['customer']
                oNewApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oNewApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oNewApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oNewApproveList.save()
                oRequest.session['errors'] = ['Approval created successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:approvalchange', kwargs={'iObjId': oNewApproveList.id}))

    dContext = {
        'form': form,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminapprovalchange.html', dContext)
# end def
