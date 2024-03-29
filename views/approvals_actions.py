"""
Views related to actions and function in the "Actions" and "Approvals" sections
of the tool.
"""

from django.utils import timezone, encoding
from django.http import HttpResponse, Http404, JsonResponse
from django.core.urlresolvers import reverse
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.db import transaction, connections
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.conf import settings

from collections import OrderedDict
from itertools import chain

from BoMConfig.models import Header, Baseline, Baseline_Revision, REF_CUSTOMER,\
    REF_REQUEST, SecurityPermission, HeaderTimeTracker, REF_STATUS, \
    ApprovalList, PartBase, ConfigLine, Part, CustomerPartInfo, PricingObject, \
    LinePricing, DocumentRequest,User_Customer,RevisionHistory
from BoMConfig.utils import UpRev, GrabValue, StrToBool,GenerateRevisionSummary,RevisionCompare,HeaderComparison, TitleShorten
from BoMConfig.views.landing import Unlock, Default
from django.contrib.auth.models import User

import base64
import copy
from cryptography.fernet import Fernet
import hashlib
import json
import re

UNICODE_ENCODING = 'utf-8'


def ToBytes(sData):
    """Ensure that a character sequence is represented as a bytes object. If
    it's already a bytes object, no change is made. If it's a string object,
    it's encoded as a UTF-8 string. Otherwise, it is treated as a sequence of
    character ordinal values."""

    if isinstance(sData, str):
        return sData.encode(UNICODE_ENCODING)
    else:
        return bytes(sData)


def FromBytes(sBytes):
    """Ensure that a character sequence is represented as a string object. If
    it's already a string object, no change is made. If it's a bytes object,
    it's decoded as a UTF-8 string. Otherwise, it is treated as a sequence of
    character ordinal values and decoded as a UTF-8 string."""

    if isinstance(sBytes, str):
        return sBytes
    else:
        return bytes(sBytes).decode(UNICODE_ENCODING)


def GetEncryptionKey(sPassword):
    """Convert a password to a 32-bit encryption key, represented in base64
    URL-safe encoding."""
    return base64.b64encode(hashlib.sha256(ToBytes(sPassword)).digest())


def Encrypt(sUnencryptedData, sPassword=None):
    """Accept a string of unencrypted data and return it as an encrypted byte
    sequence (a bytes instance). Note that this function returns a bytes instance, not a
    unicode string."""

    sKey = GetEncryptionKey(sPassword)
    del sPassword
    oSymmetricEncoding = Fernet(sKey)
    del sKey
    return oSymmetricEncoding.encrypt(ToBytes(sUnencryptedData))


def Decrypt(sEncryptedData, sPassword=None):
    """Accept an encrypted byte sequence (a bytes instance) and return it as an
    unencrypted byte sequence. Note that the return value is a bytes instance,
    not a string; if you passed in a unicode string and want that back, you will
    have to decode it using FromBytes(). This is because this function makes no
    assumption that what you originally passed in was a UTF-8 string as opposed
    to a raw byte sequence."""

    sKey = GetEncryptionKey(sPassword)
    del sPassword
    oSymmetricEncoding = Fernet(sKey)
    del sKey

    # An error here typically indicates that a different password was used to
    # encrypt the data:
    return oSymmetricEncoding.decrypt(ToBytes(sEncryptedData))


@login_required
def Approval(oRequest):
    """
    View for viewing and interacting with records pending approval
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    # S-067173 :Approvals -Restrict view to logged in users CU:- Added to get the logged in user's CU list
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # customer = REF_CUSTOMER.objects.filter(id=iCustId)
    cParentClass = Header._meta.get_field('customer_unit').rel.to
    oParent = cParentClass.objects.get(pk=oCan.customer_id)

    oCursor = connections['REACT'].cursor()
    oCursor.execute(
        'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
        '[CustomerUnit]=%s AND (SELECT convert(varchar(10), getdate(), 120)) >= [ValidFrom] AND'
        '(SELECT convert(varchar(10), getdate(), 120)) <= [ValidTo] ORDER BY [Customer]',
        [bytes(oParent.name, 'ascii')]
    )
    tResults = oCursor.fetchall()
    result = OrderedDict(
        [(obj, obj) for obj in chain.from_iterable(tResults)]
    )
    # print(result)

    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if
    # S-067173 :Approvals -Restrict view to logged in users CU:- Added '.filter(customer_unit__in=aAvailableCU)' in the approval_wait,baselines attributes of dContext
    # Added 'aAvailableCU' in customer_list attribute
    dContext = {
        'approval_wait': Header.objects.filter(
            configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(customer_unit__in=aAvailableCU),
        'requests': ['All'] + [obj.name for obj in REF_REQUEST.objects.all()],
        'baselines': ['All'] + sorted(list(
            set(
                [str(obj.baseline.title) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(customer_unit__in=aAvailableCU)]))),
        'customer_list': ['All'] + aAvailableCU,
        'customername_list': '',
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900, 1, 1),
 # S-11555: Approvals tab changes: Changed Baseline to Catalog in role header for PSM Baseline Mgmt.(PSM changed to PPM) and  Baseline Release & Dist.
        'namelist': ['PSM Configuration Mgr.', 'SCM #1', 'SCM #2', 'CSR',
                     'Comm. Price Mgmt.', 'ACR', 'PPM Catalog Mgmt.',
                     'Customer #1', 'Customer #2', 'Customer Warehouse',
                     'Ericsson VAR', 'Catalog Release & Dist.'],
        'viewauthorized': SecurityPermission.objects.filter(
            title__iregex='^.*Approval.*$').filter(
            user__in=oRequest.user.groups.all()),
        'skip_authorized': SecurityPermission.objects.filter(
            title__iexact='BLM_Approval_Write').filter(
            user__in=oRequest.user.groups.all()),
        'notify_users': {
            key: User.objects.filter(
                groups__securitypermission__title__in=value).exclude(
                groups__name__startswith='BOM_BPMA').distinct().order_by(
                'last_name') for key, value in
            HeaderTimeTracker.permission_map().items()
            },
        'available_levels': ",.".join(
            [''] + [sLevel for sLevel in HeaderTimeTracker.approvals() if
                    bool(SecurityPermission.objects.filter(
                        title__in=HeaderTimeTracker.permission_entry(sLevel)
                    ).filter(user__in=oRequest.user.groups.all()))])[1:],
    }
    return Default(oRequest, sTemplate='BoMConfig/approvals.html',
                   dContext=dContext)
# end def

# S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
#  added below function
@login_required
def ApprovalHold(oRequest):
    """
    View for viewing and interacting with records pending approval and which is on hold
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    cParentClass = Header._meta.get_field('customer_unit').rel.to
    oParent = cParentClass.objects.get(pk=oCan.customer_id)

    oCursor = connections['REACT'].cursor()
    oCursor.execute(
        'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
        '[CustomerUnit]=%s AND (SELECT convert(varchar(10), getdate(), 120)) >= [ValidFrom] AND'
        '(SELECT convert(varchar(10), getdate(), 120)) <= [ValidTo] ORDER BY [Customer]',
        [bytes(oParent.name, 'ascii')]
    )
    tResults = oCursor.fetchall()
    result = OrderedDict(
        [(obj, obj) for obj in chain.from_iterable(tResults)]
    )

    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if
    # D-06381: Approvals->On Hold->Issue with UI, and cannot remove On-Hold :- added 2 excludes to filter-out hold records which are not in In process/pending in approval page
    dContext = {
        'on_hold': Header.objects.filter(
            configuration_status__name='On Hold').filter(baseline__isdeleted=0).filter(customer_unit__in=aAvailableCU).exclude(old_configuration_status__name='In Process').exclude(old_configuration_status__name='Active'),
        'requests': ['All'] + [obj.name for obj in REF_REQUEST.objects.all()],
        'baselines': ['All'] + sorted(list(
            set(
                [str(obj.baseline.title) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='On Hold').filter(baseline__isdeleted=0).filter(customer_unit__in=aAvailableCU)]))),
        'customer_list': ['All'] + aAvailableCU,
        'customername_list': result,
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900, 1, 1),
        # S-11555: Approvals tab changes: Changed Baseline to Catalog in role header for PSM Baseline Mgmt.(PSM changed to PPM) and  Baseline Release & Dist.
        'namelist': ['PSM Configuration Mgr.', 'SCM #1', 'SCM #2', 'CSR',
                     'Comm. Price Mgmt.', 'ACR', 'PPM Catalog Mgmt.',
                     'Customer #1', 'Customer #2', 'Customer Warehouse',
                     'Ericsson VAR', 'Catalog Release & Dist.'],
        'viewauthorized': SecurityPermission.objects.filter(
            title__iregex='^.*Approval.*$').filter(
            user__in=oRequest.user.groups.all()),
        'removehold_authorized': HeaderTimeTracker.next_approval,
        'available_levels': ",.".join(
            [''] + [sLevel for sLevel in HeaderTimeTracker.approvals() if
                    bool(SecurityPermission.objects.filter(
                        title__in=HeaderTimeTracker.permission_entry(sLevel)
                    ).filter(user__in=oRequest.user.groups.all()))])[1:],
    }
    return Default(oRequest, sTemplate='BoMConfig/approvals_hold.html',
                   dContext=dContext)
# end def

@login_required
def ApprovalCustomerCustomerName(oRequest):
    """
       View for actions on records in various states (In process, active, on-hold,
       etc.)
       :param oRequest: Django request object
       :param kwargs: Dictionary of keyword arguments passed to the function
       :return: HTML response via Default function
       """
    customer = oRequest.POST['data']

    # # S-067172 :Actions -Restrict view to logged in users CU:- Added to get the logged in user's CU list
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    cParentClass = Header._meta.get_field('customer_unit').rel.to
    oParent = cParentClass.objects.get(pk=customer)

    oCursor = connections['REACT'].cursor()
    oCursor.execute(
        'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
        '[CustomerUnit]=%s AND (SELECT convert(varchar(10), getdate(), 120)) >= [ValidFrom] AND'
        '(SELECT convert(varchar(10), getdate(), 120)) <= [ValidTo] ORDER BY [Customer]',
        [bytes(oParent.name, 'ascii')]
    )
    tResults = oCursor.fetchall()
    result = OrderedDict(
        [(obj, obj) for obj in chain.from_iterable(tResults)]
    )

    # Unlock any record previously held
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if oRequest.method == 'POST' and oRequest.POST:
        return JsonResponse(result)
    else:
        raise Http404
# end def

# D-04023-Customer filter on Actions issue for Admin users :- Added ActionCustomer to populate baseline dropdown based on selected CU
@login_required
def ActionCustomer(oRequest, iCustId=''):
    """
       View for actions on records in various states (In process, active, on-hold,
       etc.)
       :param oRequest: Django request object
       :param kwargs: Dictionary of keyword arguments passed to the function
       :return: HTML response via Default function
       """
    # S-067172 :Actions -Restrict view to logged in users CU:- Added to get the logged in user's CU list
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    customer = REF_CUSTOMER.objects.filter(id=iCustId)

    cParentClass = Header._meta.get_field('customer_unit').rel.to
    oParent = cParentClass.objects.get(pk=iCustId)

    # S-12405: Actions & Approvals adjustments - Added below block for fetching the customer name list
    oCursor = connections['REACT'].cursor()
    oCursor.execute(
        'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
        '[CustomerUnit]=%s AND (SELECT convert(varchar(10), getdate(), 120)) >= [ValidFrom] AND'
        '(SELECT convert(varchar(10), getdate(), 120)) <= [ValidTo] ORDER BY [Customer]',
        [bytes(oParent.name, 'ascii')]
    )
    tResults = oCursor.fetchall()
    result = OrderedDict(
        [(obj, obj) for obj in chain.from_iterable(tResults)]
    )

    # Unlock any record previously held
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    # S-12405: Actions & Approvals adjustments - Added below if else condition since the catalog filter will get populated based on CU
    # if selected CU is Tier-1(AT&T,Veriozon,Sprint,T-Mobile) else will be blank initially & get populated on selection of CNAME in Actions- In Process Page
    if iCustId == '1' or iCustId == '2' or iCustId == '3' or iCustId == '4':
        baseline = ['All'] + sorted(list(
            set(
                [str(obj.baseline) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='In Process').filter(baseline__isdeleted=0).filter(
                    customer_unit=customer)])))
    else:
        baseline = ''

    # S-12405: Actions & Approvals adjustments - Added customername_list below in the dContext
    dContext = {
        'in_process': Header.objects.filter(
            configuration_status__name='In Process').filter(baseline__isdeleted=0).filter(
            customer_unit=customer),
        'requests': ['All'] + [obj.name for obj in REF_REQUEST.objects.all()],
        'baselines': baseline,
        'customername_list': result,
        'custid' : iCustId,
        'active': [obj for obj in Header.objects.filter(
            configuration_status__name='In Process/Pending', ) if
                   HeaderTimeTracker.approvals().index(
                       obj.latesttracker.next_approval) >
                   HeaderTimeTracker.approvals().index('acr')],
        'on_hold': Header.objects.filter(configuration_status__name='On Hold').filter(customer_unit=customer),
        'selectedcustomer': customer,
        'customer_list': ['All'] + aAvailableCU,
        'viewauthorized': bool(oRequest.user.groups.filter(
            name__in=['BOM_BPMA_Architect', 'BOM_PSM_Product_Supply_Manager',
                      'BOM_PSM_Baseline_Manager'])),
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900, 1, 1),
        # S-11553: Actions tab changes : Changed Baseline to Catalog in role header for PSM Baseline Mgmt.(PSM changed to PPM) and  Baseline Release & Dist.
        'namelist': ['SCM #1', 'SCM #2', 'CSR', 'Comm. Price Mgmt.', 'ACR',
                     'PPM Catalog Mgmt.', 'Customer #1', 'Customer #2',
                     'Customer Warehouse', 'Ericsson VAR',
                     'Catalog Release & Dist.'],
    }

    return Default(oRequest, 'BoMConfig/actions_inprocess_customer.html', dContext)

# end def

# S-12405: Actions & Approvals adjustments - Added below function for populating baselines based on CNAME selection
@login_required
def ActionCustomerNameBaseline(oRequest):
    """
       View for actions on records in various states (In process, active, on-hold,
       etc.)
       :param oRequest: Django request object
       :param kwargs: Dictionary of keyword arguments passed to the function
       :return: HTML response via Default function
       """

    customername = oRequest.POST['custname']
    pagename = oRequest.POST['page']

    # S-067172 :Actions -Restrict view to logged in users CU:- Added to get the logged in user's CU list

    # Unlock any record previously held
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if oRequest.method == 'POST' and oRequest.POST:
        if pagename == 'actions':                   # in actions_in process page
            baseline = OrderedDict(
                [(str(obj.baseline), str(obj.baseline)) if
                         obj.baseline.title != 'No Associated Baseline' else
                         "(Not baselined)" for obj in Header.objects.filter(
                            configuration_status__name='In Process').filter(
                            customer_name=customername).filter(baseline__isdeleted=0)]
            )
        elif pagename == 'actions_active':              # in actions hold page
            baseline = OrderedDict(
                [(str(obj.baseline), str(obj.baseline)) if
                     obj.baseline.title != 'No Associated Baseline' else
                     "(Not baselined)" for obj in Header.objects.filter(
                        configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(
                        customer_name=customername) if
                     HeaderTimeTracker.approvals().index(
                         obj.latesttracker.next_approval) >
                     HeaderTimeTracker.approvals().index('acr')
                     ])
        #     baseline = OrderedDict(
        #         [(str(obj.baseline.title), str(obj.baseline.title)) if
        #              obj.baseline.title != 'No Associated Baseline' else
        #              "(Not baselined)" for obj in Header.objects.filter(
        #                 configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(
        #                 customer_name=customername)])

        return JsonResponse(baseline)
    else:
        raise Http404
# end def

# S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added below defination to filter baseline on selected CU
@login_required
def ActiveCustomer(oRequest, iCustId=''):
    """
       View for document on records for In process/Pending  states
       :param oRequest: Django request object
       :param iCustId: Selected Customer-id
       :return: HTML response via Default function
       """
    # # S-067172 :Actions -Resctrict view to logged in users CU:- Added to get the logged in user's CU list
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    customer = REF_CUSTOMER.objects.filter(id=iCustId)

    cParentClass = Header._meta.get_field('customer_unit').rel.to
    oParent = cParentClass.objects.get(pk=iCustId)

    oCursor = connections['REACT'].cursor()
    oCursor.execute(
        'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
        '[CustomerUnit]=%s AND (SELECT convert(varchar(10), getdate(), 120)) >= [ValidFrom] AND'
        '(SELECT convert(varchar(10), getdate(), 120)) <= [ValidTo] ORDER BY [Customer]',
        [bytes(oParent.name, 'ascii')]
    )
    tResults = oCursor.fetchall()
    result = OrderedDict(
        [(obj, obj) for obj in chain.from_iterable(tResults)]
    )

    # Unlock any record previously held
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    # S-12405: Actions & Approvals adjustments - Added below if else condition since the catalog filter will get populated based on CU
    # if selected CU is Tier-1(AT&T,Veriozon,Sprint,T-Mobile) else will be blank initially & get populated on selection of CNAME in Actions-Documents Page
    if iCustId == '1' or iCustId == '2' or iCustId == '3' or iCustId == '4':
        baseline = ['All'] + sorted(list(
            set(
                [str(obj.baseline) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(
                    customer_unit=customer) if
                 HeaderTimeTracker.approvals().index(
                     obj.latesttracker.next_approval) >
                 HeaderTimeTracker.approvals().index('acr')
                 ])))
    else:
        baseline = ''

    dContext = {
        'in_process': Header.objects.filter(
            configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0).filter(
            customer_unit=customer),
        'requests': ['All'] + [obj.name for obj in REF_REQUEST.objects.all()],
        'customername_list' : result,
        'baselines': baseline,
        'active': [obj for obj in Header.objects.filter(
            configuration_status__name='In Process/Pending', ).filter(baseline__isdeleted=0).filter(
            customer_unit=customer)
                   if
                   HeaderTimeTracker.approvals().index(
                       obj.latesttracker.next_approval) >
                   HeaderTimeTracker.approvals().index('acr')
                   ]
        ,
        'on_hold': Header.objects.filter(configuration_status__name='On Hold').filter(customer_unit=customer),
        'selectedcustomer': customer,
        'customer_list': ['All'] + aAvailableCU,
        'viewauthorized': bool(oRequest.user.groups.filter(
            name__in=['BOM_BPMA_Architect', 'BOM_PSM_Product_Supply_Manager',
                      'BOM_PSM_Baseline_Manager'])),
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900, 1, 1),
        # S-11553: Actions tab changes : Changed Baseline to Catalog in role header for PSM Baseline Mgmt.(PSM changed to PPM) and  Baseline Release & Dist.
        'namelist': ['SCM #1', 'SCM #2', 'CSR', 'Comm. Price Mgmt.', 'ACR',
                     'PPM Catalog Mgmt.', 'Customer #1', 'Customer #2',
                     'Customer Warehouse', 'Ericsson VAR',
                     'Catalog Release & Dist.'],
    }

    return Default(oRequest, 'BoMConfig/actions_active_customer.html', dContext)

# end def

@login_required
def Action(oRequest, **kwargs):
    """
    View for actions on records in various states (In process, active, on-hold,
    etc.)
    :param oRequest: Django request object
    :param kwargs: Dictionary of keyword arguments passed to the function
    :return: HTML response via Default function
    """

    # S-067172 :Actions -Resctrict view to logged in users CU:- Added to get the logged in user's CU list
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # Unlock any record previously held
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'type' in kwargs:
        sTemplate = 'BoMConfig/actions_{}.html'.format(kwargs['type'])
    else:
        return redirect('bomconfig:action_inprocess')

    # S-067172 :Actions -Restrict view to logged in users CU:- Added '.filter(customer_unit__in=aAvailableCU)' in the in_process,baselines,on-hold attributes of dContext
    # Added 'aAvailableCU' in customer_list attribute

    dContext = {
        'in_process': Header.objects.filter(
            configuration_status__name='In Process').filter(baseline__isdeleted=0).filter(
            customer_unit__in=aAvailableCU),
        'requests': ['All'] + [obj.name for obj in REF_REQUEST.objects.all()],
        'baselines': ['All'] + sorted(list(
            set(
                [str(obj.baseline) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='In Process').filter(baseline__isdeleted=0).filter(
                    customer_unit__in=aAvailableCU)]))),
# S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added 'baseline_active' to filter baselines
# which are in pending status and approval level is beyond 'acr'
        'baseline_active': ['All'] + sorted(list(
            set(
                [str(obj.baseline) if
                 obj.baseline.title != 'No Associated Baseline' else
                 "(Not baselined)" for obj in Header.objects.filter(
                    configuration_status__name='In Process/Pending').filter().filter(baseline__isdeleted=0).filter(
                    customer_unit__in=aAvailableCU) if
                 HeaderTimeTracker.approvals().index(
                     obj.latesttracker.next_approval) >
                 HeaderTimeTracker.approvals().index('acr')
                 ]))),
        'active': [obj for obj in Header.objects.filter(
            configuration_status__name='In Process/Pending', ).filter(baseline__isdeleted=0).filter(
            customer_unit__in=aAvailableCU)
                   if
                   HeaderTimeTracker.approvals().index(
                       obj.latesttracker.next_approval) >
                   HeaderTimeTracker.approvals().index('acr')
                   ],
    # D-06381: Approvals->On Hold->Issue with UI, and cannot remove On-Hold :- added filter for hold records which are in-process status earlier in Actions page.
        'on_hold': Header.objects.filter(configuration_status__name='On Hold').filter(baseline__isdeleted=0).filter(customer_unit__in=aAvailableCU).filter(old_configuration_status__name='In Process'),
        'customer_list': ['All'] + aAvailableCU,
        'viewauthorized': bool(oRequest.user.groups.filter(
            name__in=['BOM_BPMA_Architect', 'BOM_PSM_Product_Supply_Manager',
                      'BOM_PSM_Baseline_Manager'])),
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900, 1, 1),
    # S-11553: Actions tab changes : Changed Baseline to Catalog in role header for PSM Baseline Mgmt.(PSM changed to PPM) and  Baseline Release & Dist.
        'namelist': ['SCM #1', 'SCM #2', 'CSR', 'Comm. Price Mgmt.', 'ACR',
                     'PPM Catalog Mgmt.', 'Customer #1', 'Customer #2',
                     'Customer Warehouse', 'Ericsson VAR',
                     'Catalog Release & Dist.'],
    }

    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
# end def


def ApprovalData(oRequest):
    """
    View to provide approval details.  When provided with a HeaderTimeTracker
    object id and an approval level, whether the level has been approved or
    disapproved, when the action occurred, and the person who performed the
    action.
    :param oRequest: Django request object
    :return: JSONResponse containing details
    """
    if oRequest.method == 'POST' and oRequest.POST:
        oHeadTracker = HeaderTimeTracker.objects.get(id=oRequest.POST['id'])
        dResult = {
            'type': '',
            'person': '',
            'date': '',
            'comments': ''
        }

        # Collect the full name of the user associated with the username stored
        # (if any)
        if getattr(oHeadTracker, oRequest.POST['level'] + "_approver"
                   ) != 'system':
            try:
                oUser = User.objects.get(
                    username=getattr(oHeadTracker,
                                     oRequest.POST['level'] + "_approver"))
                dResult['person'] = oUser.get_full_name()
            except User.DoesNotExist:
                dResult['person'] = '(User not found)'
        else:
            dResult['person'] = 'System'

        # Collect comments at the level, and the date in the "<level>
        # approved_on" field, or the "<level>_denied_approval" field. Also set
        # the type of action (A - Approval, S - Skip, D- Disapproval)
        if oRequest.POST['level'] != 'psm_config':
            dResult['comments'] = getattr(
                oHeadTracker, oRequest.POST['level'] + "_comments", 'N/A'
            )
            if getattr(oHeadTracker, oRequest.POST['level']+"_approved_on"):
                dResult['date'] = getattr(
                    oHeadTracker, oRequest.POST['level'] + "_approved_on"
                ).strftime('%m/%d/%Y')

                if getattr(
                    oHeadTracker,
                    oRequest.POST['level'] + "_approved_on"
                ).date() == timezone.datetime(1900, 1, 1).date():
                    dResult['type'] = 'S'
                else:
                    dResult['type'] = 'A'
            elif getattr(oHeadTracker,
                         oRequest.POST['level'] + "_denied_approval"):
                dResult['date'] = getattr(
                    oHeadTracker,
                    oRequest.POST['level'] + "_denied_approval"
                ).strftime('%m/%d/%Y')
                dResult['type'] = 'D'
            # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
            #  added below elif block
            elif getattr(oHeadTracker,
                         oRequest.POST['level'] + "_hold_approval"):
                dResult['date'] = getattr(
                    oHeadTracker,
                    oRequest.POST['level'] + "_hold_approval"
                ).strftime('%m/%d/%Y')
                dResult['type'] = 'H'
        else:
            dResult['type'] = 'A'
            dResult['date'] = oHeadTracker.submitted_for_approval.strftime(
                '%m/%d/%Y')
            dResult['comments'] = 'N/A'

        return JsonResponse(dResult)
    else:
        raise Http404()

# S-07984: Add the list of changes(revision information) under each config and BOM Request Type: Added below function to write the revision comments
def WriteRevisionToFile(record,oRequest):

        oHeader = Header.objects.get(id=record)
# S-07984: Add the list of changes(revision information) under each config and BOM Request Type: Added 'confid' to append the
#          configuration ID to each revision comments so that the comments can be recognised in the HTML email content
        confid = str(oHeader.id)
        sAvailBase = Baseline.objects.filter(title=oHeader.baseline.title)

        for version in sAvailBase:
            sPrevious = version.current_active_version
            sCurrent = version.current_inprocess_version

            for config in sCurrent:

                oDiscontinued = Q(configuration_status__name='Discontinued')
                oToDiscontinue = Q(bom_request_type__name='Discontinue')


                # aDiscontinuedHeaders = [oHead for oHead in Header.objects.get]
                aDiscontinuedHeaders = [oHead for oHead in Header.objects.filter(id=oHeader.id).filter(
                    bom_request_type__name='Discontinue')]


                aAddedHeaders = [oHead for oHead in Header.objects.filter(id=oHeader.id).filter(
                    bom_request_type__name__in=('New', 'Legacy', 'Preliminary'))]

                aUpdatedHeaders = [oHead for oHead in Header.objects.filter(id=oHeader.id).filter(
                    bom_request_type__name='Update')]




                aCurrButNotPrev = []
                for oHead in aUpdatedHeaders:
                    try:
                        Baseline_Revision.objects.get(baseline=sAvailBase,
                                                      version=sPrevious).header_set.get(
                            configuration_designation=oHead.configuration_designation,
                            program=oHead.program)

                    except (Header.DoesNotExist, Baseline_Revision.DoesNotExist):
                        aCurrButNotPrev.append(oHead)
                        # end try

                sNewSummary = confid+'Added'
                sRemovedSummary = confid + 'Discontinued'

                # Append the formatted string for each Header in aAddedHeaders
                for oHead in aAddedHeaders:
            # D-04019: Internal Server Error (500) on multiple actions
                    sNewSummary += '\n'.format(oHead.configuration_designation)

                # Add a line for each Header that is an "Update" but has not previous record
                # in the previous revision
                for oHead in aCurrButNotPrev:
                    sNewSummary += '\n'.format(oHead.configuration_designation)
                # end for

                # Add a line for each discontinued Header. Skip headers that have been
                # replaced and that replacement is in aAddedHeaders, since we have already
                # added a description of that transaction earlier
                for oHead in aDiscontinuedHeaders:
            # D-04019: Internal Server Error (500) on multiple actions
                    sRemovedSummary += '\n'.format(oHead.configuration_designation)
                # end for

                # Calculate and add changes for updated headers
                sUpdateSummary = confid + 'Updated:\n'
                for oHead in aUpdatedHeaders:
                    try:
                        oPrev = oHead.model_replaced_link or Header.objects.get(
                            configuration_designation=oHead.configuration_designation,
                            program=oHead.program,
                            baseline_version=sPrevious
                        )

                        sTemp = HeaderComparison(oHead, oPrev)
                    except Header.DoesNotExist:
                        sTemp = ''
                    # end try

                    if sTemp:
                        oHead.change_notes = sTemp
                        oHead.save()
                        sUpdateSummary += '\n'.format(
                            oHead.configuration_designation + (
                                ' ({})'.format(oHead.program) if oHead.program else ''
                            ) + (
                                '  {}'.format(
                                    oHead.configuration.get_first_line().customer_number
                                ) if not oHead.pick_list and
                                     oHead.configuration.get_first_line().customer_number
                                else ''
                            )
                        )

                        for sLine in sTemp.split('\n'):
                            sUpdateSummary += confid + (' ' * 8) + sLine + '\n'
                            # end if
                # end for

                sHistory = ''

                if sNewSummary != confid+'Added':
                    sHistory += sNewSummary
                if sRemovedSummary != confid+'Discontinued':
                    sHistory += sRemovedSummary
                if sUpdateSummary != confid + 'Updated:\n':
                    sHistory += sUpdateSummary

                # Save revision history
            # D-04019: Internal Server Error (500) on multiple actions - commented the below lines
                # (oNew, _) = RevisionHistory.objects.get_or_create(baseline=sAvailBase,
                #                                                   revision=sCurrent)
                # oNew.history = sHistory
                # oNew.save()

        return sHistory

@transaction.atomic
def AjaxApprove(oRequest):
    """
    View to perform the following actions on records:
    Approve - Approve first available level in latest HeaderTimeTracker for
        record
    Disapprove - Disapprove first available level in latest HeaderTimeTracker for
        record
    Skip - Skip first available level in latest HeaderTimeTracker for
        record (this is an admin level action only)
    Clone - Create a near-exact copy of a record
    Delete - Delete a record from the database
    Submit for Approval - Move a record from "In Process" to "In Process/Pending
        Approval"
    Place on Hold - Place a record "On Hold"
    Remove from Hold - Return a record from "On Hold" to its previous status
    Cancel - Mark a record as "Cancelled"

    This function is atomic, meaning that any changes to the database (via
    saving objects or otherwise) will be rolled back if any error occurs in the
    function.

    :param oRequest: Django request object
    :return: HTTPResponse
    """
    if oRequest.method == 'POST' and oRequest.POST:
        # Disallow requests with unsupported actions or no action
        if oRequest.POST.get('action', None) not in (
                'approve', 'disapprove', 'skip', 'clone', 'delete',
                'send_to_approve', 'hold', 'unhold', 'cancel'):
            raise Http404

        # Collect the list of record ids, comments, and destinations supplied
        # with the request, if any.
        sAction = oRequest.POST.get('action')
        aRecords = [
            int(record) for record in json.loads(oRequest.POST.get('data'))]

        if 'comments' in oRequest.POST:
            aComments = [
                record for record in json.loads(oRequest.POST.get('comments',
                                                                  None))]
        if 'destinations' in oRequest.POST:
            aDestinations = [
                record for record in json.loads(
                    oRequest.POST.get('destinations', None)
                )]
        # added for S-07353 Allow emails to be manually added to notify list. adding custom field in approval dropdown list
        if 'customemailid' in oRequest.POST:
            aCustomEmail = [
                record for record in json.loads(
                    oRequest.POST.get('customemailid', None)
                )]

        dEmailRecipients = {}

        # Submit record(s) for approval
        if sAction == 'send_to_approve':
            dApprovalData = json.loads(oRequest.POST.get('approval'))

            for iRecord in aRecords:
                # For each record, retrieve the actual header record. If the
                # header has a HeaderTimeTracker object that has no data in the
                # submitted_for_approval field, operate on that object,
                # otherwise, create a new HeaderTimeTracker object for the
                # header.
                oHeader = Header.objects.get(pk=iRecord)
                oCreated = oHeader.headertimetracker_set.first().created_on
                if oHeader.headertimetracker_set.filter(
                        submitted_for_approval=None):
                    oLatestTracker = oHeader.headertimetracker_set.filter(
                        submitted_for_approval=None).first()
                    oLatestTracker.submitted_for_approval = timezone.now()
                    oLatestTracker.psm_config_approver = oRequest.user.username
                    oLatestTracker.created_on = oCreated
                    oLatestTracker.save()
                else:
                    oLatestTracker = HeaderTimeTracker.objects.create(**{
                        'header': oHeader,
                        'submitted_for_approval': timezone.now(),
                        'psm_config_approver': oRequest.user.username,
                        'created_on': oCreated
                    })

                # dApprovalData (and by extension dRecordApprovals) will contain
                # data about optional approval levels included and any
                # additional notifications desired.
                dRecordApprovals = dApprovalData[str(iRecord)]
                try:
                    oApprovalList = ApprovalList.objects.get(
                        customer=oHeader.customer_unit)
                except ApprovalList.DoesNotExist:
                    oApprovalList = None

                for index, level in enumerate(HeaderTimeTracker.approvals()):
                    if level in ('psm_config', 'brd'):
                        continue

                    # If level is disallowed or not included in the desired
                    # levels, mark the field as skipped  by the system
                    if (oApprovalList and str(index) in
                        oApprovalList.disallowed.split(',')) or (
                            not StrToBool(dRecordApprovals[level][0])):
                        setattr(oLatestTracker, level + '_approver', 'system')
                        setattr(oLatestTracker, level + '_approved_on',
                                timezone.datetime(1900, 1, 1))
                        setattr(oLatestTracker, level + '_comments',
                                'Not required for this customer')
                    # Otherwise, set notification party (if included)
                    elif dRecordApprovals[level][1]:
                        if int(dRecordApprovals[level][1]) != 0:
                            oNotifyUser = User.objects.get(
                                id=dRecordApprovals[level][1])
                            setattr(oLatestTracker, level + "_notify",
                                    oNotifyUser.email)
                        else:
                            setattr(oLatestTracker, level + "_notify",
                                    dRecordApprovals[level][2])

                oLatestTracker.save()

                # Update list of users that should be notified about this record
                # being submitted for approval.
                #
                # The email recipient dictionary is set-up as
                # {
                #   <email_address>: {
                #       <action>: {
                #           <next_approval_level>: [<HeaderTimeTracker>, ...]
                if hasattr(oLatestTracker,
                           oLatestTracker.next_approval + '_notify'):
                    sNextLevel = oLatestTracker.next_approval
                    for sRecip in list(
                            set(
                                (getattr(oLatestTracker,
                                         sNextLevel + '_notify', '') or ''
                                 ).split(';')
                            )):
                        if sRecip not in dEmailRecipients:
                            dEmailRecipients[sRecip] = {'submit': {}}

                        if sNextLevel:
                            if sNextLevel not in dEmailRecipients[
                                    sRecip]['submit'].keys():
                                dEmailRecipients[
                                    sRecip]['submit'][sNextLevel] = {}

                            if oLatestTracker.header.baseline_impacted not in \
                                    dEmailRecipients[sRecip][
                                        'submit'][sNextLevel].keys():
                                dEmailRecipients[sRecip]['submit'][sNextLevel][
                                    oLatestTracker.header.baseline_impacted
                                ] = []

                            dEmailRecipients[sRecip]['submit'][sNextLevel][
                                oLatestTracker.header.baseline_impacted].append(
                                oLatestTracker)

                # Update Header status
                oHeader.configuration_status = REF_STATUS.objects.get(
                    name='In Process/Pending')
                oHeader.save()
            # end for
        # Approval actions (approve, disapprove, skip)
        elif sAction in ('approve', 'disapprove', 'skip'):
            from BoMConfig.views.download import EmailDownload

            aChain = HeaderTimeTracker.approvals()
            aBaselinesCompleted = []
            aRecipients = []
            ctr = 0
            for index in range(len(aRecords)):
                # For each item in aRecords, get the corresponding Header, and
                # that Header's most recently created HeaderTimeTracker object
                oHeader = Header.objects.get(pk=aRecords[index])
                oLatestTracker = oHeader.headertimetracker_set.order_by(
                    '-submitted_for_approval').first()

                # Determine the next approval level needed on the record
                sNeededLevel = oLatestTracker.next_approval

                # Determine if the user making the request has permission to
                # perform the requested action on this record
                aNames = HeaderTimeTracker.permission_entry(sNeededLevel)
                try:
                    bCanApprove = bool(SecurityPermission.objects.filter(
                        title__in=aNames).filter(
                        user__in=oRequest.user.groups.all()))
                except ValueError:
                    bCanApprove = False
                # end if

                # If so, approve, disapprove, or skip as requested
                if bCanApprove:

                    if sAction == 'approve':
                        # Set HeaderTimeTracker's name, date, and comments
                        # fields for the needed approval level
                        setattr(oLatestTracker, sNeededLevel+'_approver',
                                oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_approved_on',
                                timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments',
                                aComments[index])

                        # Determine the list of recipients that should be
                        # notified of this records approval

                        if aDestinations[index]:
# D-04088- Approvals incorrectly require notify field to be selected: Added below if & else to separate the aRecipients in case of custom & normal notify fields.
                            if int(aDestinations[index]) == 0:      # for custom
   # added for S-07353 Allow emails to be manually added to notify list. adding custom field in approval dropdown list
                                 if aCustomEmail[ctr] != '':
                                    aRecipients.append(aCustomEmail[ctr])
                                    ctr = ctr + 1
                            else:                                   # normal notify fields
                                aRecipients.append(User.objects.get(
                                    id=aDestinations[index]).email)
                        sNotifyLevel = oLatestTracker.next_approval
                        if sNotifyLevel != 'brd':
                            if hasattr(oLatestTracker,
                                       str(sNotifyLevel) + '_notify') and \
                                    getattr(oLatestTracker,
                                            str(sNotifyLevel) + '_notify',
                                            None):
                                aRecipients.extend(
                                    getattr(oLatestTracker,
                                            sNotifyLevel + '_notify',
                                            '').split(";"))
                        else:
                            aRecipients.extend(
                                [user.email for user in User.objects.filter(
                                    groups__name="BOM_PSM_Baseline_Manager")])

                        # Add the determined recipients to the dEmailRecipients
                        # dictionary
                        if aRecipients:
                            for sRecip in list(set(aRecipients)):
                                if sRecip not in dEmailRecipients:
                                    dEmailRecipients[sRecip] = {'approve': {}}

                                if sNotifyLevel:
                                    if sNotifyLevel not in dEmailRecipients[
                                            sRecip]['approve'].keys():
                                        dEmailRecipients[sRecip]['approve'][
                                            sNotifyLevel] = {}

                                    if oLatestTracker.header.baseline_impacted \
                                            not in dEmailRecipients[sRecip][
                                                'approve'][sNotifyLevel].keys():
                                        dEmailRecipients[
                                            sRecip]['approve'][sNotifyLevel][
                                            oLatestTracker.header.baseline_impacted
                                        ] = []

                                    dEmailRecipients[sRecip][
                                        'approve'][
                                        sNotifyLevel][
                                        oLatestTracker.header.baseline_impacted
                                    ].append(oLatestTracker)

                    elif sAction == 'disapprove':
                        # Set HeaderTimeTracker's name, date, and comments
                        # fields for the needed approval level
                        setattr(oLatestTracker, sNeededLevel+'_approver',
                                oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_denied_approval',
                                timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments',
                                aComments[index])
                        oLatestTracker.disapproved_on = timezone.now()

                        # if not disapproved back to PSM_Config, create a new
                        # HeaderTimeTracker object for this Header
                        sReturnedLevel = 'psm_config'
                        if aDestinations[index] != 'psm_config':
                            oNewTracker = HeaderTimeTracker.objects.create(
                                **{'header': oHeader,
                                   'created_on': oLatestTracker.created_on,
                                   'submitted_for_approval': timezone.now()
                                   }
                            )

                            # Copy over approval data for each level before
                            # destination level
                            for level in aChain:
                                if level == aDestinations[index]:
                                    sReturnedLevel = level
                                # end if

                                if (aChain.index(level) < aChain.index(
                                        aDestinations[index])) or (
                                            getattr(oLatestTracker,
                                                    level + '_approver') ==
                                            'system'):
                                    setattr(oNewTracker, level+'_approver',
                                            getattr(oLatestTracker,
                                                    level + '_approver', None))

                                if level == 'psm_config':
                                    continue
                                # end if

                                if (aChain.index(level) < aChain.index(
                                        aDestinations[index])) or (
                                            getattr(oLatestTracker,
                                                    level + '_approver') ==
                                            'system'):
                                    setattr(oNewTracker,
                                            level+'_denied_approval',
                                            getattr(oLatestTracker,
                                                    level + '_denied_approval',
                                                    None))
                                    setattr(oNewTracker, level+'_approved_on',
                                            getattr(oLatestTracker,
                                                    level + '_approved_on',
                                                    None))
                                    setattr(oNewTracker, level+'_comments',
                                            getattr(oLatestTracker,
                                                    level + '_comments', None))

                                if hasattr(oNewTracker, level + "_notify"):
                                    setattr(oNewTracker, level + '_notify',
                                            getattr(oLatestTracker,
                                                    level + '_notify', None))
                            # end for

                            oNewTracker.save()

                            # Determine the list of recipients to be notified of
                            # this records disapproval
                            sLastApprover = getattr(
                                oLatestTracker, sReturnedLevel + '_approver',
                                None)
                            if hasattr(oLatestTracker,
                                       sReturnedLevel + '_notify'):
                                sLastNotify = getattr(
                                    oLatestTracker, sReturnedLevel + '_notify',
                                    None)
                            else:
                                sLastNotify = None

                            # Add the determined recipients to the
                            # dEmailRecipients dictionary
                            if sLastApprover or sLastNotify:
                                aRecipients = []
                                if sLastApprover:
                                    aRecipients.append(
                                        User.objects.get(
                                            username=sLastApprover
                                        ).email
                                    )

                                if sLastNotify:
                                    aRecipients.extend(sLastNotify.split(";"))

                                for sRecip in list(set(aRecipients)):
                                    if sRecip not in dEmailRecipients:
                                        dEmailRecipients[sRecip] = {
                                            'disapprove': {}
                                        }

                                    if sReturnedLevel:
                                        if sReturnedLevel not in \
                                                dEmailRecipients[sRecip][
                                                    'disapprove'].keys():
                                            dEmailRecipients[
                                                sRecip]['disapprove'][
                                                sReturnedLevel] = {}

                                        if oLatestTracker.header.\
                                                baseline_impacted not in \
                                                dEmailRecipients[sRecip][
                                                    'disapprove'][
                                                    sReturnedLevel].keys():
                                            dEmailRecipients[sRecip][
                                                'disapprove'][sReturnedLevel][
                                                oLatestTracker.header.
                                                    baseline_impacted] = []

                                        dEmailRecipients[sRecip]['disapprove'][
                                            sReturnedLevel][
                                            oLatestTracker.header.
                                                baseline_impacted].append(
                                            oLatestTracker)

                        # Else, send header back to 'In Process' status
                        else:
                            oHeader.configuration_status = REF_STATUS.objects.\
                                get(name='In Process')
                            oHeader.save()

                            # Update dEmailRecipients dictionary to include the
                            # user that submitted the record for approval
                            if User.objects.get(
                                    username=oLatestTracker.psm_config_approver
                            ).email not in dEmailRecipients:
                                dEmailRecipients[User.objects.get(
                                    username=oLatestTracker.psm_config_approver
                                ).email] = {'disapprove': {}}

                            if 'psm_config' not in dEmailRecipients[
                                User.objects.get(
                                    username=oLatestTracker.psm_config_approver
                                    ).email]['disapprove'].keys():
                                dEmailRecipients[
                                    User.objects.get(
                                        username=oLatestTracker.psm_config_approver
                                    ).email]['disapprove']['psm_config'] = {}

                            if oLatestTracker.header.baseline_impacted not in \
                                    dEmailRecipients[User.objects.get(
                                        username=oLatestTracker.psm_config_approver
                                    ).email]['disapprove']['psm_config'].keys():
                                dEmailRecipients[User.objects.get(
                                    username=oLatestTracker.psm_config_approver
                                ).email]['disapprove']['psm_config'][
                                    oLatestTracker.header.baseline_impacted] = []

                            dEmailRecipients[User.objects.get(
                                username=oLatestTracker.psm_config_approver
                            ).email]['disapprove']['psm_config'][
                                oLatestTracker.header.baseline_impacted].append(
                                oLatestTracker)
                        # end if
                    elif sAction == 'skip' and sNeededLevel != 'brd':
                        setattr(oLatestTracker, sNeededLevel+'_approver',
                                oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_approved_on',
                                timezone.datetime(1900, 1, 1))
                    oLatestTracker.save()

                    # If this approval is the last one needed for release
                    if sNeededLevel == 'brd' and sAction == 'approve':
                        # Set the tracker's completed_on field
                        oLatestTracker.completed_on = timezone.now()
                        oLatestTracker.save()

                        # Alter configuration status
                        if oHeader.bom_request_type.name in ('Discontinue',):
                            oHeader.configuration_status = REF_STATUS.objects.\
                                get(name='Discontinued')
                            oHeader.release_date = oLatestTracker.completed_on
                        elif oHeader.bom_request_type.name in ('New', 'Update',
                                                               'Replacement',
                                                               'Legacy'):
                            oHeader.configuration_status = REF_STATUS.objects.\
                                get(name='Active')
                            oHeader.release_date = oLatestTracker.completed_on
                        elif oHeader.bom_request_type.name == 'Preliminary':
                            oHeader.configuration_status = REF_STATUS.objects.\
                                get(name='In Process')
                            oHeader.bom_request_type = REF_REQUEST.objects.get(
                                name='New')
                        oHeader.save()

                        # Add any completed baselines to the list
                        if oHeader.configuration_status.name in ('Discontinued',
                                                                 'Active') and \
                                oHeader.baseline:
                            aBaselinesCompleted.append(oHeader.baseline)
                        # end if
                    # end if
                # end if
            # end for

            # Remove duplicates from the list of completed baselines
            aBaselinesCompleted = list(set(aBaselinesCompleted))

            # For each completed baseline, uprev the baseline, and send an email
            # of the baseline to the correct recipients
            for oBaseline in aBaselinesCompleted:
                UpRev(oBaseline.baseline)
                EmailDownload( oRequest,oBaseline.baseline) # D-03452: Some emails are not being tagged as test system, added oRequest
            # end for

        # Clone the record, then go to the BoM Entry view for the newly cloned
        # record
        elif sAction == 'clone':
            oOldHeader = Header.objects.get(pk=aRecords[0])
            oNewHeader = CloneHeader(oOldHeader)

            oRequest.session['existing'] = oNewHeader.pk
            return HttpResponse(reverse('bomconfig:configheader'))
        elif sAction == 'delete':
            Header.objects.filter(pk__in=aRecords).delete()
        elif sAction == 'cancel':
            Header.objects.filter(pk__in=aRecords).update(
                configuration_status__name='Cancelled')             # __(double underscore means join)
        elif sAction in ('hold', 'unhold'):
            # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
            #  changed below elif block and commented earlier code
            #
            #     for iRecord in aRecords:
            #         oHeader = Header.objects.get(pk=iRecord)
            #         # Toggle the Header's configuration's on-hold status.
            #         oHeader.configuration.PSM_on_hold = not oHeader.configuration.\
            #             PSM_on_hold
            #         oHeader.configuration.save()

            # end for
            aChain = HeaderTimeTracker.approvals()


            for index in range(len(aRecords)):
                # For each item in aRecords, get the corresponding Header, and
                # that Header's most recently created HeaderTimeTracker object
                oHeader = Header.objects.get(pk=aRecords[index])
                oLatestTracker = oHeader.headertimetracker_set.order_by(
                    '-submitted_for_approval').first()
                # Determine the next approval level needed on the record
                sNeededLevel = oLatestTracker.next_approval

                # Determine if the user making the request has permission to
                # perform the requested action on this record
                aNames = HeaderTimeTracker.permission_entry(sNeededLevel)
                try:
                    bCanHold = bool(SecurityPermission.objects.filter(
                        title__in=aNames).filter(
                        user__in=oRequest.user.groups.all()))
                except ValueError:
                    bCanHold = False
                # end if

                # If so, hold or unhold as requested
                if bCanHold and sAction == 'hold' and sNeededLevel != 'psm_config':
                    # if sAction == 'hold' and sNeededLevel != 'psm_config':
                        # Set HeaderTimeTracker's name, date, and comments
                        # # fields for the needed approval level
                    setattr(oLatestTracker, sNeededLevel + '_approver',
                            oRequest.user.username) if oLatestTracker else ''
                    setattr(oLatestTracker, sNeededLevel + '_hold_approval',
                            timezone.now()) if oLatestTracker else ''
                    setattr(oLatestTracker, sNeededLevel + '_comments',
                            aComments[index])if oLatestTracker else ''
                    oLatestTracker.hold_on = timezone.now()
                    oLatestTracker.save()
            # D-06454: Chevrons not showing correct coloring when view only on On Hold records: Added below two lines to check PSM_on_hold in configuration
                    oHeader.configuration.PSM_on_hold = 1
                    oHeader.configuration.save()
                    oHeader.configuration_status = REF_STATUS.objects.get(name='On Hold')
                    oHeader.save()
            # D-06381: Approvals->On Hold->Issue with UI, and cannot remove On-Hold :- commented out below elif block because it is not needed.
                    # elif sAction == 'unhold':
                    #     for iRecord in aRecords:
                    #         oHeader = Header.objects.get(pk=iRecord)
                    #         # Toggle the Header's configuration's on-hold status.
                    #         oHeader.configuration.PSM_on_hold = not oHeader.configuration. \
                    #             PSM_on_hold
                    #         oHeader.configuration.save()
                    #         # end for
                else:
                    for iRecord in aRecords:
                        oHeader = Header.objects.get(pk=iRecord)
                        # Toggle the Header's configuration's on-hold status.
                        oHeader.configuration.PSM_on_hold = not oHeader.configuration. \
                            PSM_on_hold
                        oHeader.configuration.save()

        # end if
        # S-05766:Identify Emails from Test System:-- Added to frame the Email content/subject as per the environment
        if oRequest.POST.get('windowurl') == 'local':
            envName = 'Local System:'
        elif oRequest.POST.get('windowurl') == 'test':
            envName = 'Test System:'
        else:
            envName = ''

        # Send the appropriate message to each user in the dEmailRecipients
        # dictionary.  Message is determined by level and action.
        for key in dEmailRecipients.keys():
            for approval in dEmailRecipients[key]:
               for level in dEmailRecipients[key][approval]:
                   for baseline in dEmailRecipients[key][approval][level]:
 #S-07984: Add the list of changes(revision information) under each config and BOM Request Type: Added below 6 lines to get the comments of each config under selected baselines
                        svar = ''
                        for iRecord in aRecords:
                            oHeader = Header.objects.get(pk=iRecord)
                            svar =  svar +  WriteRevisionToFile(iRecord, oRequest)

                        aLines = svar.split('\n')[:-1]
                        oMessage = EmailMultiAlternatives(
                            # S-05766:Identify Emails from Test System:-- Concatenated envName to frame the Email subject as per the environment
                            subject= envName+ ((baseline or '(No baseline)') +
                                     ' Review & Approval'),
                            body=loader.render_to_string(
                                'BoMConfig/approval_approve_email_plain.txt',
                                {'submitter': oRequest.user.get_full_name(),
                                 'records': dEmailRecipients[key][approval][
                                     level][baseline],
                                 'recipient': User.objects.filter(
                                     email=key).first().first_name if
                                 User.objects.filter(email=key) else key,
                                 'level': level,
                                 'action': approval,
# S-07984: Add the list of changes(revision information) under each config and BOM Request Type: Added below send the comments in 'ALines' to HTML
                                 'revision': aLines,
                                 }
                            ),
# S-10576: Change the header of the tool to ACC :- Changed the tool name from pcbm to acc
                            from_email='acc.admin@ericsson.com',
                            to=[key],
                            cc=[oRequest.user.email],
                            bcc=list(
                                set(
                                    [
                                        User.objects.get(
                                            username=getattr(oRecord,
                                                             sublevel +
                                                             '_approver')
                                        ).email
                                        for oRecord in dEmailRecipients[key][
                                            approval][level][baseline]
                                        for sublevel in aChain[
                                                        aChain.index(level):
                                                        aChain.index(
                                                            oRecord.disapproved_level
                                                        )
                                                        ]
                                        if getattr(oRecord,
                                                   sublevel + '_approver'
                                                   ) != 'system'
                                        ]
                                )
                            ) if approval == 'disapprove' else [],
                            headers={'Reply-To': oRequest.user.email}
                        )
                        oMessage.attach_alternative(loader.render_to_string(
                            'BoMConfig/approval_approve_email.html',
                            {'submitter': oRequest.user.get_full_name(),
                             'records': dEmailRecipients[key][approval][level][
                                 baseline],
                             'recipient': User.objects.filter(
                                 email=key).first().first_name if
                             User.objects.filter(email=key) else key,
                             'level': level,
                             'action': approval,
                             # S-05766:Identify Emails from Test System:-- Added this parameter to send the appropriate environment name to the email HTML content
                             'windowURL': oRequest.POST.get('windowurl'),
# S-07984: Add the list of changes(revision information) under each config and BOM Request Type: Added below send the comments in 'ALines' to HTML
                             'revision': aLines
                             }
                        ), 'text/html')
                        # uncommented below line for D-03232 to send mail for baseline Review and approval
                        oMessage.send(fail_silently=False)
                    # end for
                # end for
            # end for
        # end for

        return HttpResponse()
    else:
        raise Http404()
# end def

# S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
 #  added below def

def HoldApprove(oRequest):
    if oRequest.method == 'POST' and oRequest.POST:
        # Disallow requests with unsupported actions or no action
        if oRequest.POST.get('action', None) not in ('unhold'):
            raise Http404
#  D-06242: Removal from 'On-Hold' causing invalid approval: Added destination to fetch destination from oRequest.
        if 'destinations' in oRequest.POST:
            aDestinations = [
                record for record in json.loads(
                    oRequest.POST.get('destinations', None)
                )]

        # Collect the list of record ids supplied
        # with the request, if any.
        sAction = oRequest.POST.get('action')
        aRecords = [
            int(record) for record in json.loads(oRequest.POST.get('data'))]

        if sAction =='unhold':
            for index in range(len(aRecords)):
        # For each item in aRecords, get the corresponding Header, and
        # that Header's most recently created HeaderTimeTracker object
                oHeader = Header.objects.get(pk=aRecords[index])
                oLatestTracker = oHeader.headertimetracker_set.order_by(
                    '-submitted_for_approval').first()
#  D-06242: Removal from 'On-Hold' causing invalid approval: Added below lines to create new HeaderTimeTracker entry and to copy all previous data in the prev row.
                # Determine if the user making the request has permission to
                # perform the requested action on this record
                aChain = HeaderTimeTracker.approvals()
                # end if
                sReturnedLevel = 'scm1'
                if aDestinations[index] != 'psm_config' :
                    oNewTracker = HeaderTimeTracker.objects.create(
                        **{'header': oHeader,
                           'created_on': oLatestTracker.created_on,
                           'submitted_for_approval': timezone.now()
                           }
                    )

                    # Copy over approval data for each level before
                    # destination level
                    for level in aChain:
                        if level == aDestinations[index]:
                            sReturnedLevel = level
                        # end if

                        if (aChain.index(level) < aChain.index(
                                aDestinations[index])) or (
                                            getattr(oLatestTracker,
                                                    level + '_approver') ==
                                            'system'):
                            setattr(oNewTracker, level + '_approver',
                                    getattr(oLatestTracker,
                                            level + '_approver', None))
                            setattr(oNewTracker,
                                    level + '_hold_approval',
                                    getattr(oLatestTracker,
                                            level + '_hold_approval', None
                                            ))
                            setattr(oNewTracker, level + '_approved_on',
                                    getattr(oLatestTracker,
                                            level + '_approved_on', None
                                            ))
                            setattr(oNewTracker, level + '_comments',
                                    getattr(oLatestTracker,
                                            level + '_comments', None))
                        # end if
                    # end for

                    oNewTracker.save()
            # D-06454: Chevrons not showing correct coloring when view only on On Hold records: Added below two lines to uncheck PSM_on_hold in configuration
                    oHeader.configuration.PSM_on_hold = 0
                    oHeader.configuration.save()
                    oHeader.configuration_status = REF_STATUS.objects.get(name='In Process/Pending')
                    oHeader.save()

    return HttpResponse()


def CloneHeader(oHeader):
    """
    Function to create a near-exact clone of a Header object
    :param oHeader: Header object to clone
    :return: Header object (clone)
    """
    # Make a deep copy of the Header object.  Remove the pk, so that when saved,
    # the database will treat it as a new entry.
    oOldHeader = oHeader
    oNewHeader = copy.deepcopy(oOldHeader)
    oNewHeader.pk = None
    oNewHeader.configuration_designation = oOldHeader.configuration_designation\
        + '_______CLONE_______'
    oNewHeader.configuration_status = REF_STATUS.objects.get(name='In Process')

    # Remove fields that should only be linked to the original Header
    oNewHeader.inquiry_site_template = None
    if oNewHeader.react_request is None:
        oNewHeader.react_request = ''
    # end if

    oNewHeader.change_notes = None
    oNewHeader.change_comments = None
    oNewHeader.release_date = None
    oNewHeader.model_replaced_link = None

    # Add the new clone to the correct in-process baseline revision
    if oNewHeader.baseline_impacted:
        oNewHeader.baseline = Baseline_Revision.objects.get(
            baseline=Baseline.objects.get(title=oNewHeader.baseline_impacted),
            version=Baseline.objects.get(
                title=oNewHeader.baseline_impacted).current_inprocess_version)
        oNewHeader.baseline_version = oNewHeader.baseline.version
    else:
        oNewHeader.baseline = Baseline_Revision.objects.get(
            baseline=Baseline.objects.get(title='No Associated Baseline'),
            version=Baseline.objects.get(
                title='No Associated Baseline').current_inprocess_version
        )
        oNewHeader.baseline_version = oNewHeader.baseline.version
    # end if

    # Since a single record may be cloned multiple times, and record names must
    # be unique within a baseline, we check to see if a clone already exists,
    # and if so, update the name as needed.
    iTry = 1
    while len(Header.objects.filter(
            configuration_designation=oNewHeader.configuration_designation,
            program=oNewHeader.program, baseline=oNewHeader.baseline,
            baseline_version=oNewHeader.baseline_version)) > 0:
        oNewHeader.configuration_designation = \
            oOldHeader.configuration_designation + '_______CLONE' + str(iTry) +\
            '_______'
        iTry += 1

    oNewHeader.save()

    # Make a clone of the configuration, configlines, and linepricing objects
    oNewConfig = copy.deepcopy(oOldHeader.configuration)
    oNewConfig.pk = None
    oNewConfig.header = oNewHeader
    oNewConfig.save()

    for oConfigLine in oOldHeader.configuration.configline_set.all():
        oNewLine = copy.deepcopy(oConfigLine)
        oNewLine.pk = None
        oNewLine.config = oNewConfig
        # added for if cloned configuration has New Configuration name, then it's customer no. will be none else will have customer no of previous configuration
        if oNewConfig.header.configuration_designation != oOldHeader.configuration_designation:
            oNewLine.customer_number = None
        else:
            oNewLine.customer_number = copy.deepcopy(oConfigLine.customer_number)
        oNewLine.sec_customer_number = None
        oNewLine.customer_asset = copy.deepcopy(oConfigLine.customer_asset)
        oNewLine.customer_asset_tagging = copy.deepcopy(oConfigLine.customer_asset_tagging)
        if oConfigLine.linepricing.pricing_object:
            oNewLine.unit_price = oConfigLine.linepricing.pricing_object.unit_price
        else:
            oNewLine.unit_price=None
        # oNewLine.comments = None
        oNewLine.save()

        if hasattr(oConfigLine, 'linepricing'):
            oNewPrice = copy.deepcopy(oConfigLine.linepricing)
            oNewPrice.pk = None
            # D-03994-Manual override pricing fix: When cloning a config, we should copy all manual override pricing from the previous config
            oNewPrice.override_price = copy.deepcopy(oConfigLine.linepricing.override_price)
            oNewPrice.config_line = oNewLine
            oNewPrice.pricing_object = PricingObject.getClosestMatch(oNewLine)
            oNewPrice.save()
        # end if
    # end for
    return oNewHeader
# end def


def AjaxApprovalForm(oRequest):
    """
    View used to generate the form used when submitting records for approval.
    The form contains all approval levels, and checkboxes for users to select
    which optional levels are included.  Also provides a dropdown and textbox
    to enter recipients of notification at each approval level.
    :param oRequest: Django request object
    :return: JSONResponse object
    """
    if oRequest.POST:
        # Collect list of records being submitted for approval
        aRecords = json.loads(oRequest.POST['data'])

        # Collect approval levels accept psm_config and brd, which are always
        # required for every record
        aApprovalLevels = HeaderTimeTracker.approvals()[1:-1]
        dPermissionLevels = HeaderTimeTracker.permission_map()

        dForm = {}

        for record in aRecords:
            oHeader = Header.objects.get(id=record)
            # Generate a dictionary containing the required, disallowed, and
            # optional approval levels, per ApprovalList objects for the
            # associated Customer unit.
            dContext = {'approval_levels': aApprovalLevels,
                        'required': (GrabValue(ApprovalList.objects.filter(
                            customer=oHeader.customer_unit).first(),
                                               'required') or '').split(','),
                        'optional': (GrabValue(ApprovalList.objects.filter(
                            customer=oHeader.customer_unit).first(),
                                               'optional') or '').split(','),
                        'disallowed': (GrabValue(ApprovalList.objects.filter(
                            customer=oHeader.customer_unit).first(),
                                                 'disallowed') or '').split(','),
                        'email': {}
                        }

            # Add eligible users to the list of notification recipients for each
            # approval level
            for key, value in dPermissionLevels.items():
                if key in aApprovalLevels:
                    dContext['email'].update(
                        {key: list(
                            User.objects.filter(
                                groups__securitypermission__in=SecurityPermission.
                                objects.filter(title__in=value)).exclude(
                                groups__name__contains='BPMA').order_by(
                                'last_name').distinct())})

            # Using the previously built context, render the form template to a
            # string of HTML
            dForm[record] = [oHeader.configuration_designation + "  " +
                             oHeader.baseline_version,
                             loader.render_to_string(
                                 'BoMConfig/approvalform.html', dContext)]

        return JsonResponse(dForm)
    else:
        return Http404()
# end def


def ChangePart(oRequest):
    """
    View used for changing single part number across multiple records at once.
    :param oRequest:
    :return:
    """
    if oRequest.POST:
        dResponse = {}

        # Performing search
        if oRequest.POST['action'] == 'search':
            dResponse['type'] = 'search'
            sPart = oRequest.POST.get('part', '')
            sPart = sPart.upper().strip()

            # If a part number was provided
            if sPart:
                try:
                    # Get the part corresponding to the part number provided
                    oPart = PartBase.objects.get(product_number=sPart)

                    # Collect all ConfigLine objects that use the part specified
                    # and are attached to an "In process" header
                    aLines = ConfigLine.objects.filter(
                        part__base=oPart,
                        config__header__configuration_status__name='In Process')

                    # Create list of tuple representing configuration name,
                    # program, baseline, header object, is_changeable)
                    aHeaders = [
                        (oLine.config.header.configuration_designation,
                         oLine.config.header.program,
                         oLine.config.header.baseline_impacted,
                         oLine.config.header, True) for oLine in aLines]

                    # In-Process/Pending records are not changeable, since they
                    # are pending approval
                    aLines = ConfigLine.objects.filter(
                        part__base=oPart,
                        config__header__configuration_status__name='In Process/Pending'
                    )

                    aHeaders.extend(
                        [(oLine.config.header.configuration_designation,
                          oLine.config.header.program,
                          oLine.config.header.baseline_impacted,
                          oLine.config.header, False) for oLine in aLines
                         ]
                    )

                    # Active records are only changeable if no in-process copy
                    # exists (and therefore can be cloned)
                    aLines = ConfigLine.objects.filter(
                        part__base=oPart,
                        config__header__configuration_status__name='Active')

                    oInProc = Q(
                        configuration_status__name__in=['In Process',
                                                        'In Process/Pending'])
                    oHoldInProc = Q(
                        old_configuration_status__name__in=[
                            'In Process', 'In Process/Pending'])
                    for oLine in aLines:
                        # If in-process copy exists
                        if Header.objects.filter(
                                oInProc | oHoldInProc,
                                configuration_designation=oLine.config.header.
                                configuration_designation,
                                program=oLine.config.header.program,
                                baseline_impacted=oLine.config.header.
                                baseline_impacted
                        ):
                            oObj = Header.objects.filter(
                                oInProc | oHoldInProc,
                                configuration_designation=oLine.config.header.
                                configuration_designation,
                                program=oLine.config.header.program,
                                baseline_impacted=oLine.config.header.
                                baseline_impacted
                            ).first()

                            # If in-process copy is already in list of records,
                            # skip the record
                            if (oLine.config.header.configuration_designation,
                                oLine.config.header.program,
                                oLine.config.header.baseline_impacted, oObj,
                                False) in aHeaders or (
                                    oLine.config.header.configuration_designation,
                                    oLine.config.header.program,
                                    oLine.config.header.baseline_impacted, oObj,
                                    True) in aHeaders:
                                pass
                            else:
                                aHeaders.append(
                                    (oLine.config.header.
                                     configuration_designation,
                                     oLine.config.header.program,
                                     oLine.config.header.baseline_impacted,
                                     oLine.config.header, False))
                        else:
                            aHeaders.append(
                                (oLine.config.header.configuration_designation,
                                 oLine.config.header.program,
                                 oLine.config.header.baseline_impacted,
                                 oLine.config.header, True))

                    # if no headers use the part, provide an error
                    if not aHeaders:
                        dResponse['error'] = True
                        dResponse['status'] = 'No records containing part'

                    # otherwise, return a response containing information from
                    # the list of headers generated.
                    else:
                        aHeaders = list(set(aHeaders))
                        aHeaders.sort(
                            key=lambda x: (x[0], x[1].name if x[1] else '',
                                           x[2])
                        )
                        dResponse['error'] = False
                        dResponse['records'] = [
                            {'id': tHeader[3].id,
                             'configuration_designation': tHeader[0],
                             'program': tHeader[1].name if tHeader[1] else
                                '(None)',
                             'baseline': tHeader[2] or '(None)',
                             'status': tHeader[3].configuration_status.name,
                             'selectable': tHeader[4],
                             'revision': tHeader[3].baseline_version or '(None)'
                             } for tHeader in aHeaders]
                        dResponse['part'] = sPart
                except PartBase.DoesNotExist:
                    dResponse['error'] = True
                    dResponse['status'] = 'No matching part'

            # Otherwise, provide an error
            else:
                dResponse['error'] = True
                dResponse['status'] = 'No part number provided'

        # Performing replacement
        elif oRequest.POST['action'] == 'replace':
            dResponse['type'] = 'replace'

            sPart = oRequest.POST.get('part')
            sPart = sPart.upper().strip()

            sReplacePart = oRequest.POST.get('replacement')
            sReplacePart = sReplacePart.upper().strip()

            try:
                int(sReplacePart)
                sReplacePart += '/'
            except ValueError:
                pass

            aRecords = json.loads(oRequest.POST.get('records'))

            # If a replacement part was provided, does not match the initial
            # part number, and records were selected for replacement, perform
            # the replacement.  Otherwise, provide an appropriate error.
            if sReplacePart:
                if sReplacePart != sPart:
                    if aRecords:
                        for iId in aRecords:
                            oHeader = Header.objects.get(id=iId)

                            # if Header is not "In process", it must be "Active"
                            # and cloneable, so clone the active version, and
                            # the changes will be made to the newly created
                            # in-process clone.
                            if oHeader.configuration_status.name != 'In Process':
                                oNewHeader = CloneHeader(oHeader)
                                oNewHeader.configuration_designation = \
                                    oHeader.configuration_designation
                                oNewHeader.bom_request_type = \
                                    REF_REQUEST.objects.get(name='Update')
                                oNewHeader.model_replaced = ''
                                oNewHeader.model_replaced_link = oHeader
                                oNewHeader.save()
                                oHeader = oNewHeader

                            # Get or create the part associated with the
                            # replacement part number.  The data associated with
                            # this new part will be populated/updated when the
                            # configuration is actually validated.
                            (oReplacementBase, _) = PartBase.objects.\
                                get_or_create(
                                product_number=sReplacePart,
                                defaults={'unit_of_measure': 'PC'})
                            try:
                                (oReplacement, _) = Part.objects.get_or_create(
                                    base=oReplacementBase)
                            except Part.MultipleObjectsReturned:
                                oReplacement = Part.objects.filter(
                                    base=oReplacementBase).first()

                            # Update each ConfigLine's Part, LinePricing, and
                            # CustomerPartInfo information if it exists.
                            for oLine in oHeader.configuration.configline_set.\
                                    filter(part__base__product_number=sPart):
                                oLine.part = oReplacement
                                oLine.vendor_article_number = \
                                    sReplacePart.strip('./')
                                oLinePrice = PricingObject.getClosestMatch(
                                    oLine)

                                if not hasattr(oLine, 'linepricing'):
                                    LinePricing.objects.create(
                                        **{'config_line': oLine}
                                    )

                                oLine.linepricing.pricing_object = oLinePrice
                                oLine.linepricing.save()

                                try:
                                    oCustInfo = CustomerPartInfo.objects.get(
                                        active=True, part=oReplacementBase,
                                        customer=oHeader.customer_unit)
                                    oLine.customer_number = oCustInfo.\
                                        customer_number
                                    oLine.sec_customer_number = oCustInfo.\
                                        second_customer_number
                                    oLine.customer_asset_tagging = 'Y' if \
                                        oCustInfo.customer_asset_tagging else \
                                        'N' if oCustInfo.customer_asset_tagging\
                                        is False else ''
                                    oLine.customer_asset = 'Y' if \
                                        oCustInfo.customer_asset else 'N' if \
                                        oCustInfo.customer_asset is False else \
                                        ''
                                except CustomerPartInfo.DoesNotExist:
                                    oLine.customer_number = None
                                    oLine.sec_customer_number = None
                                    oLine.customer_asset_tagging = None
                                    oLine.customer_asset = None

                                oLine.save()
                            # end for
                        # end for

                        dResponse['error'] = False
                        dResponse['status'] = \
                            'Part number successfully replaced'

                    else:
                        dResponse['error'] = True
                        dResponse['status'] = \
                            'No records selected for replacement'
                    # end if
                else:
                    dResponse['error'] = True
                    dResponse['status'] = \
                        'Replacement part is the same as the searched part'
                # end if

            else:
                dResponse['error'] = True
                dResponse['status'] = 'No replacement part'
            # end if

        # end if

        return JsonResponse(dResponse)
    else:
        return Http404
# end def


def CreateDocument(oRequest):
    """
    View for creating document requests for generating SAP documents.
    :param oRequest: Django HTTP request
    :return: HTTPRequest
    """
    oHeader = Header.objects.get(id=oRequest.POST.get('id'))

    # Update valid-to and valid-from dates
    # If the record is a discontinuation, update the valid-to date to the
    # present date. Otherwise update the valid-from date to the present date.
    if oHeader.bom_request_type.name != 'Discontinue':
        if not oHeader.valid_from_date or oHeader.valid_from_date < \
                timezone.datetime.now().date():
            oHeader.valid_from_date = timezone.datetime.now().date()
    else:
        if not oHeader.valid_to_date or oHeader.valid_to_date < \
                timezone.datetime.now().date():
            oHeader.valid_to_date = (timezone.datetime.now().date() +
                                     timezone.timedelta(1))

    # For non-discontinuation records, ensure that the valid-to date is after
    # the valid-from date.  If it is not, make the new valid-to date one year
    # after the valid-from date.
    if oHeader.valid_from_date and oHeader.valid_to_date and \
            oHeader.valid_from_date > oHeader.valid_to_date and \
            oHeader.bom_request_type.name != 'Discontinue':
        while oHeader.valid_from_date > oHeader.valid_to_date:
            oHeader.valid_to_date = (oHeader.valid_to_date +
                                     timezone.timedelta(365))

    bCreateSiteTemplate = StrToBool(oRequest.POST.get('type'))

    # Retrieve the Item Category Group to Item Category mapping data from the
    # database
    oCursor = connections['BCAMDB'].cursor()
    oCursor.execute(
        "SELECT [ICG],[{}] FROM [BCAMDB].[dbo].[REF_ITEM_CAT_GROUP]".format(
            ("ZTPL" if bCreateSiteTemplate else "ZDOT"))
    )
    dItemCatMap = dict(oCursor.fetchall())

    oPattern = re.compile(r'^.+\((?P<key>[A-Z0-9]{3})\)$|^$', re.I)

    # Set the parameters for creating a document
    if not bCreateSiteTemplate:

    # S-10961: Adjust Actions and Documents tabs UI and backend :- Added the below line to fetch the first line number
        oFirstLine = oHeader.configuration.get_first_line()

        # Create Inquiry
        data = {
            "inquiry_type": "ZDOT",
            "order_type": "ZTP",
            'zy_delivery_partner': '',
            'site_id': "PCBM Controlled",
            "sales_org": "1259" if oHeader.customer_unit.name in
                                   ['EMC', 'Canada',
                                    'New Canadian'] else "1263",
            "distribution_channel": "XX",
            "division": "XX",
            "sales_office": oHeader.sales_office,
            "sales_group": oHeader.sales_group,
            "sold_to_party": str(oHeader.sold_to_party or ''),
            "ship_to_party": str(oHeader.ship_to_party or ''),
            "bill_to_party": str(oHeader.bill_to_party or ''),
            "configuration_designation": oHeader.configuration_designation,
            "valid_from_date": oHeader.valid_from_date.strftime('%Y-%m-%d') if
            oHeader.valid_from_date else '',
            'po_date': oHeader.valid_from_date.strftime('%Y-%m-%d') if
            oHeader.valid_from_date else '',
            "valid_to_date": oHeader.valid_to_date.strftime('%Y-%m-%d') if
            oHeader.valid_to_date else '',
            "payment_terms": oHeader.payment_terms.split()[0] if
            oHeader.payment_terms else '',
            "ericsson_contract": str(oHeader.ericsson_contract or ''),
            'no_zip_routing': oHeader.no_zip_routing,
            'internal_external_linkage': "X" if
            oHeader.configuration.internal_external_linkage else '',
            'shipping_condition': oHeader.shipping_condition,
            'complete_delivery': oHeader.complete_delivery,
            'form_header': '',
            "line_items": [
                {
                    'line_number': oLine.line_number,
                    'product_number': oLine.part.base.product_number,
                    'product_description': oLine.part.product_description or '',
                    'order_qty': str(oLine.order_qty),
                    'plant': oLine.plant or '',
                    'sloc': oLine.sloc or '',
                    'item_category': dItemCatMap[oLine.item_category] if
                    oLine.item_category in dItemCatMap else
                    oLine.item_category or '',
                    'pcode': (oLine.pcode[1:4]).strip('-') if oLine.pcode else '',  #  D-03252 : Incorrect p-code passed to Inquiry creation table addition of .strip('-')
                    'unit_price': str(
                        oHeader.configuration.override_net_value or
                        oHeader.configuration.net_value or '')
# S-10961: Adjust Actions and Documents tabs UI and backend :- Changed the below line to its next line and added line 100 condition
# D-06863: error in SAP inquiry creation :- Commented below 2nd line and uncommented below line and added the (or condition)
                    if not oHeader.pick_list and oLine.line_number == '10' or (oFirstLine.line_number == '100' and oLine.line_number == '100')
                    # if not oHeader.pick_list and (oFirstLine.line_number == '10' or oFirstLine.line_number == '100')
                    else '' if not oHeader.pick_list else str(GrabValue(
                        oLine.linepricing, 'override_price', '') or GrabValue(
                        oLine.linepricing, 'pricing_object.unit_price', '')
                                                              ) or '',
                    'condition_type': oLine.condition_type or '',
                    'amount': str(oLine.amount) if oLine.amount is not None
                    else '',
                    'contextId': oLine.contextId or '',
                    'higher_level_item': oLine.higher_level_item or '',
                    'material_group_5': oPattern.match(oLine.material_group_5 or
                                                       '').group('key') or '',
                    'purchase_order_item_num': (oLine.purchase_order_item_num or
                                                ''),
                    "valid_from_date": oHeader.valid_from_date.strftime(
                        '%Y-%m-%d') if oHeader.valid_from_date else '',
                }
                for oLine in sorted(
                    oHeader.configuration.configline_set.exclude(
                        line_number__contains='.'),
                    key=lambda x: [int(y) for y in getattr(x, 'line_number'
                                                           ).split('.')])
                ]
        }
    else:
        # Create Site Template
        data = {
            "contract_type": "ZTPL",
            'order_type': '',
            'zy_delivery_partner': '',
            "sales_org": "1259" if oHeader.customer_unit.name in
                                   ['EMC', 'Canada',
                                    'New Canadian'] else "1263",
            "distribution_channel": "XX",
            "division": "XX",
            "sales_office": '',
            "sales_group": '',
            "sold_to_party": str(oHeader.sold_to_party or ''),
            "ship_to_party": str(oHeader.ship_to_party or ''),
            "bill_to_party": str(oHeader.bill_to_party or ''),
            "configuration_designation": oHeader.configuration_designation,
            "model_description": oHeader.model_description or '',
            "valid_from_date": oHeader.valid_from_date.strftime('%Y-%m-%d') if
            oHeader.valid_from_date else '',
            "valid_to_date": oHeader.valid_to_date.strftime('%Y-%m-%d') if
            oHeader.valid_to_date else '',
            "ericsson_contract": str(oHeader.ericsson_contract or ''),
            'no_zip_routing': oHeader.no_zip_routing,
            'internal_external_linkage': "X" if
            oHeader.configuration.internal_external_linkage else '',
            'shipping_condition': oHeader.shipping_condition,
            'complete_delivery': oHeader.complete_delivery,
            "payment_terms": oHeader.payment_terms.split()[0] if
            oHeader.payment_terms else '',
            "line_items": [
                {
                    'line_number': oLine.line_number,
                    'product_number': oLine.part.base.product_number,
                    'product_description': oLine.part.product_description or '',
                    'order_qty': str(oLine.order_qty),
                    'plant': oLine.plant or '',
                    'sloc': oLine.sloc or '',
                    'item_category': dItemCatMap[oLine.item_category] if
                    oLine.item_category in dItemCatMap else
                    oLine.item_category or '',
                    'pcode': oLine.pcode[1:4] if oLine.pcode else '',
                    'higher_level_item': oLine.higher_level_item or '',
                    'contextId': oLine.contextId or '',
                    'material_group_5': oPattern.match(oLine.material_group_5 or
                                                       '').group('key') or '',
                    'customer_number': oLine.customer_number or '',
                }
                for oLine in sorted(
                    oHeader.configuration.configline_set.exclude(
                        line_number__contains='.'),
                    key=lambda x: [int(y) for y in getattr(x, 'line_number'
                                                           ).split('.')]
                )
                ]
        }
    # end if

    # For discontinuations, make sure that if the record being discontinued has
    # a replacement, the replacement has a valid document number.
    if oHeader.bom_request_type.name == 'Discontinue':
        if oHeader.model_replaced_link and \
                oHeader.model_replaced_link.replaced_by_model.exclude(
                    id=oHeader.id):
            if oHeader.model_replaced_link.replaced_by_model.exclude(
                    id=oHeader.id).first().inquiry_site_template is not None \
                    and oHeader.model_replaced_link.replaced_by_model.exclude(
                        id=oHeader.id).first().inquiry_site_template > 0:
                data['configuration_designation'] = (
                    'Replaced by {}'.format(
                        oHeader.model_replaced_link.replaced_by_model.exclude(
                            id=oHeader.id).first().inquiry_site_template)
                )
            else:
                return HttpResponse(status=409, reason="Invalid replacement")
        else:
            data['configuration_designation'] = 'Obsolete'

    export_dict = {
        "data": data,
        "pdf": StrToBool(oRequest.POST.get('pdf'), False),
        "update": StrToBool(oRequest.POST.get('update'), False),

        # type = False for Inquiry, True for Site Template
        "type": StrToBool(oRequest.POST.get('type'), False),
        "record_id": oHeader.id,
        'credentials': {
            'username': oRequest.POST.get('user'),
            'password': FromBytes(
                Encrypt(
                    oRequest.POST.get('pass'),
                    encoding.force_text(settings.SECRET_KEY)
                )
            )
        },
        'user': {
            'signum': oRequest.user.username,
            'email': oRequest.user.email,
            'full_name': oRequest.user.get_full_name()
        },
        'react_req': oHeader.react_request
    }

    if StrToBool(oRequest.POST.get('update'), False):
        export_dict.update({'existing_doc': oHeader.inquiry_site_template})

    # If updating existing document
    if StrToBool(oRequest.POST.get('update'), False):
        oHeader.inquiry_site_template *= -1
    else:
        oHeader.inquiry_site_template = -1
    oHeader.save()

    DocumentRequest.objects.create(req_data=json.dumps(export_dict),
                                   record_processed=oHeader)

    return HttpResponse(status=200)
# end def
