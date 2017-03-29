"""
Views used in the default viewing of all pages or interacting with records in
the tool
"""

from django.shortcuts import render
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout as auth_logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse, resolve
from django.contrib.sessions.models import Session

from BoMConfig.models import NewsItem, Alert, Header, HeaderLock, \
    SecurityPermission
from BoMConfig import menulisting, headerFile, footerFile, pagetitle, \
    supportcontact

import traceback


class LockException(BaseException):
    """
    Custom exception class used when locking Header objects for editing
    """
    pass
# end def


def SetSession(oRequest):
    """
    Clears expired sessions and sets request session to not expire
    :param oRequest: Django HTTP request object
    :return: None
    """
    oRequest.session.clear_expired()
    if oRequest.session.get_expiry_age():
        oRequest.session.set_expiry(0)
    # end if
# end def


def Lock(oRequest, iHeaderPK):
    """
    Associates a session to a HeaderLock object to prevent multiple users from
    entering and editing a Header
    :param oRequest: Django HTTP request object
    :param iHeaderPK: Integer containing the pk/id of the Header object to lock
    :return: None
    """
    if Header.objects.filter(pk=iHeaderPK):
        if Header.objects.get(pk=iHeaderPK).configuration_status.name != \
                'In Process':
            return
        # end if

        # If Header does not have an associated HeaderLock, create one
        if not HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)):
            HeaderLock.objects.create(
                **{'header': Header.objects.get(pk=iHeaderPK)})
        # end if

        # If the record is unlocked, lock it to the user session
        if HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)).filter(
                session_key=None):
            HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)).filter(
                session_key=None).update(
                **{'session_key': Session.objects.get(
                    session_key=oRequest.session.session_key)}
            )
        # If the record is locked by the user session, allow the lock to
        # continue
        elif HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)).filter(
                session_key=Session.objects.get(
                    session_key=oRequest.session.session_key)):
            pass
        else:
            raise LockException('File is locked for editing')
    else:
        raise Header.DoesNotExist('No such Header found')
    # end if
# end def


def Unlock(oRequest, iHeaderPK):
    """
    Removes the association of a session to a HeaderLock object to allow users
    to enter and edit a Header
    :param oRequest: Django HTTP request object
    :param iHeaderPK: Integer containing the pk/id of the Header object to
    unlock
    :return: None
    """
    if Header.objects.filter(pk=iHeaderPK):
        # If the current user session is locking the Header, remove the session
        # from the HeaderLock.
        if HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)).filter(
                session_key=Session.objects.get(
                    session_key=oRequest.session.session_key)):
            HeaderLock.objects.filter(
                header=Header.objects.get(pk=iHeaderPK)).filter(
                session_key=Session.objects.get(
                    session_key=oRequest.session.session_key)
            ).update(**{'session_key': None})
        else:
            pass
    else:
        raise Header.DoesNotExist('No existing header')
# end def


def Logout(oRequest):
    """
    View/Function to logout of the tool, unlocking any record the user still has
    locked and immediately expiring session
    :param oRequest: Django HTTP request object
    :return: Logout via authentication module logout function
    """
    try:
        Unlock(oRequest, iHeaderPK=oRequest.session.get('existing', None))
    except Header.DoesNotExist:
        pass
    # end try
    oRequest.session.set_expiry(1)
    return auth_logout(oRequest, next_page='/pcbm/')
# end def


def FinalUnlock(oRequest):
    """
    View/Function to unlock any record the user still has
    locked when a user does not logout but instead closes the browser window
    :param oRequest: Django HTTP request object
    :return: HTTPResponse
    """
    if oRequest.method == 'POST':
        try:
            Unlock(oRequest, iHeaderPK=oRequest.session.get('existing', None))
        except (LockException, Header.DoesNotExist):
            pass
        except Exception:
            print(traceback.format_exc())
        # end try

        if oRequest.POST.get('close', None) == 'true':
            oRequest.session.set_expiry(0)

        response = HttpResponse()
        response['Content-Length'] = 0
        return response
    else:
        raise Http404()
# end def


def InitialLock(oRequest):
    """
    View/Function to create session, if it does not exist, and lock a record at
    the same time
    :param oRequest: Django HTTP request object
    :return: HTTPResponse
    """
    if oRequest.method == 'POST':
        try:
            SetSession(oRequest)
            Lock(oRequest, iHeaderPK=oRequest.session.get('existing', None))
        except (LockException, Header.DoesNotExist):
            pass
        except Exception:
            print(traceback.format_exc())
        # end try

        response = HttpResponse()
        response['Content-Length'] = 0
        return response
    else:
        raise Http404()
# end def


def Index(oRequest):
    """
    View to display tool landing page, displaying news and alerts
    :param oRequest: Django HTTP request object
    :return: HTTPResponse via Default function
    """
    SetSession(oRequest)
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    aLatestAlerts = Alert.objects.filter(
        PublishDate__lte=timezone.now()).order_by('-PublishDate')
    aLatestNews = NewsItem.objects.filter(
        PublishDate__lte=timezone.now()).order_by('-PublishDate')

    dContext = {
        'latest_alerts': aLatestAlerts,
        'latest_news': aLatestNews,
    }
    return Default(oRequest, 'BoMConfig/index.html', dContext)
# end def


@login_required
def Login(oRequest):
    """
    View to ensure tool login
    :param oRequest: Django HTTP request object
    :return: Redirect to Index view
    """
    return HttpResponseRedirect(
        reverse(
            'bomconfig:index',
            current_app=resolve(oRequest.path).app_name
        )
    )
# end def


@ensure_csrf_cookie
def Default(oRequest, sTemplate='BoMConfig/template.html', dContext=None,
            show_footer=False):
    """
    View wrapper used to display all tool pages. Sets values and parameters that
    are used in all or most views, insetad of repeatedly setting them in each
    view
    :param oRequest: Django HTTP request object
    :param sTemplate: String storing HTML template to render and display
    :param dContext: Dictionary containing data to pass to template for
    rendering
    :param show_footer: Boolean indicating if the view should show footer
    section
    :return: HttpResponse
    """
    sUserId = None

    # Determine user name
    if oRequest.user.is_authenticated() and oRequest.user.is_active:
        sUserId = oRequest.user.username
    # end if

    # Determine user permission levels for various actions in-tool
    bCanReadHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWriteHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Write').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigBOM = bool(SecurityPermission.objects.filter(
        title='Config_Entry_BOM_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigSAP = bool(SecurityPermission.objects.filter(
        title='Config_Entry_SAPDoc_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigAttr = bool(SecurityPermission.objects.filter(
        title='Config_Entry_Attributes_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigPrice = bool(SecurityPermission.objects.filter(
        title='Config_Entry_PriceLinks_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigCust = bool(SecurityPermission.objects.filter(
        title='Config_Entry_CustomerData_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfigBaseline = bool(SecurityPermission.objects.filter(
        title='Config_Entry_Baseline_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(
        title='Config_ToC_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(
        title='Config_Revision_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(
        title='SAP_Inquiry_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(
        title='SAP_ST_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))

    if not dContext:
        dContext = {}

    dNewContext = {}
    dNewContext.update([
        ('menulisting', menulisting,),
        ('header_template', headerFile,),
        ('footer_template', footerFile,),
        ('pagetitle', pagetitle,),
        ('supportcontact', supportcontact,),
        ('userId', sUserId,),
        ('show_footer', show_footer,),
        ('header_write_authorized', bCanWriteHeader),
        ('header_read_authorized', bCanReadHeader),
        ('config_read_authorized', bCanReadConfigBOM),
        ('config_sap_read_authorized', bCanReadConfigSAP),
        ('config_attr_read_authorized', bCanReadConfigAttr),
        ('config_price_read_authorized', bCanReadConfigPrice),
        ('config_cust_read_authorized', bCanReadConfigCust),
        ('config_baseline_read_authorized', bCanReadConfigBaseline),
        ('toc_read_authorized', bCanReadTOC),
        ('revision_read_authorized', bCanReadRevision),
        ('inquiry_read_authorized', bCanReadInquiry),
        ('sitetemplate_read_authorized', bCanReadSiteTemplate),
    ])
    dNewContext.update(dContext)

    # Render and return response
    response = render(oRequest, sTemplate, dNewContext)
    patch_cache_control(response, no_cache=True, no_store=True,
                        must_revalidate=True, pragma='no-cache', max_age=0)
    return response
# end def
