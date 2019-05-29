"""
Views for creating, editing, viewing, and validating configurations.
"""

from django.shortcuts import redirect
from django.http import QueryDict, JsonResponse, Http404
from django.core.urlresolvers import reverse
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.db import connections, IntegrityError
from django import forms
from django.forms import fields
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from BoMConfig.models import Header, Part, Configuration, ConfigLine, PartBase,\
    Baseline, Baseline_Revision, LinePricing, REF_CUSTOMER, HeaderLock, \
    SecurityPermission,REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, REF_TECHNOLOGY, REF_RADIO_FREQUENCY, REF_RADIO_BAND,REF_PROGRAM, REF_CONDITION, \
    REF_MATERIAL_GROUP, REF_PRODUCT_PKG, REF_SPUD, REF_REQUEST, PricingObject, \
    CustomerPartInfo, HeaderTimeTracker,User_Customer
from BoMConfig.forms import HeaderForm, ConfigForm, DateForm
from BoMConfig.views.landing import Lock, Default, LockException, Unlock
from BoMConfig.views.approvals_actions import CloneHeader
from BoMConfig.utils import GrabValue, HeaderComparison, RevisionCompare, \
    DetectBrowser, StrToBool

import copy
from collections import OrderedDict
from itertools import chain
import json
import re


def UpdateConfigRevisionData(oHeader):
    """
    Function to regenerate RevisionHistory data when a header is changed.  This
    ensures that the revision history is always up-to-date.
    :param oHeader: Header object changed
    :return: None
    """
    oPrev = None

    try:
        # If the Header has a linked model that is replaces, compare to that
        if oHeader.model_replaced_link:
            oPrev = oHeader.model_replaced_link
        # Try to find a header in the previous revision that has the same name
        # as this header's model replaced field or configuration designation.
        elif oHeader.baseline and oHeader.baseline.previous_revision:
            oPrev = oHeader.baseline.previous_revision.header_set.get(
                configuration_designation=oHeader.model_replaced or
                oHeader.configuration_designation,
                program=oHeader.program)
        else:
            if oHeader.baseline:
                aExistingRevs = sorted(
                    list(set([oBaseRev.version for oBaseRev in
                              oHeader.baseline.baseline
                             .baseline_revision_set.order_by('version')])),
                    key=RevisionCompare)
            else:
                aExistingRevs = [oHeader.baseline_version]

            iPrev = aExistingRevs.index(oHeader.baseline_version) - 1

            if iPrev >= 0:
                sPrevious = aExistingRevs[iPrev]

                oPrev = Header.objects.get(
                    configuration_designation=oHeader.configuration_designation,
                    program=oHeader.program,
                    baseline_version=sPrevious
                )
            # end if
        # end if
    except Header.DoesNotExist:
        pass
    # end try

    # if a previous version was found, compare the Header object and the
    # previous version.
    if oPrev:
        sTemp = HeaderComparison(oHeader, oPrev)
        oHeader.change_notes = sTemp
        oHeader.save(alert=False)
    # end if
# end def


@login_required
def AddHeader(oRequest, sTemplate='BoMConfig/entrylanding.html'):
    """
    View for creating a new Header object, or editing header information of an
    existing Header object.
    :param oRequest: Django HTTP request object
    :param sTemplate: Name of template to render for this view
    :return: HTTPResponse via Default function
    """
    # S-06756- added for restricting customer_unit,person responsible as per logged in user's cu in BOM entry view
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # This is the case when the user clicks the "BoM Entry" link
    if sTemplate == 'BoMConfig/entrylanding.html':
        if 'existing' in oRequest.session and oRequest.session['existing']:
            Unlock(oRequest, oRequest.session['existing'])
            del oRequest.session['existing']
        return redirect(reverse('bomconfig:configheader'))
    # This is the case when the user enters a configuration's header view via
    # search, actions, or baseline management.
    else:
        # Determine what permissions the user has on the view
        bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
        iFrameID = oRequest.GET.get('id', None)

        bCanReadHeader = bool(SecurityPermission.objects.filter(
            title='Config_Header_Read').filter(
            user__in=oRequest.user.groups.all())
        )
        bCanWriteHeader = False

        bSuccess = False

        # Determine which pages to which the user is able to move forward
        bCanReadConfig = bool(SecurityPermission.objects.filter(
            title='Config_Entry_BOM_Read').filter(
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

        bCanMoveForward = bCanReadConfig or bCanReadTOC or bCanReadRevision or \
            bCanReadInquiry or bCanReadSiteTemplate

        bDiscontinuationAlreadyCreated = False

        # "existing" is the existing header. Store the pk in the form to
        # return for saving. "status" message allows another view to redirect to
        # other views with an error message explaining the redirect.
        if bFrameReadOnly:
            oExisting = iFrameID
        else:
            oExisting = oRequest.session.get('existing', None)
        status_message = oRequest.session.get('status', None)

        if status_message:
            del oRequest.session['status']
        # end if

        try:
            # If this view is on an existing record, lock the record and
            # determine if a discontinuation is needed and already exisits.
            if oExisting:
                if not bFrameReadOnly:
                    Lock(oRequest, oExisting)
                oExisting = Header.objects.get(pk=oExisting)
                bDiscontinuationAlreadyCreated = True if \
                    oExisting.model_replaced_link and hasattr(
                        oExisting.model_replaced_link,
                        'replaced_by_model') and \
                    oExisting.model_replaced_link.replaced_by_model.filter(
                        bom_request_type__name='Discontinue',
                        configuration_designation=oExisting.model_replaced_link
                        .configuration_designation) else False
            # end if

            if bFrameReadOnly:
                bCanWriteHeader = False
            else:
                # Determine if the user can write the header information
                bCanWriteHeader = bool(
                    SecurityPermission.objects.filter(
                        title='Config_Header_Write').filter(
                        user__in=oRequest.user.groups.all())) and \
                                  (not oExisting or (oExisting and (
                                      oExisting.configuration_status.name ==
                                      'In Process')))

            # If this request is for POSTing data
            if oRequest.method == 'POST' and oRequest.POST:
# D-03994-Manual override pricing fix:
# When cloning a config, we should copy all manual override pricing from the previous config
# When status of that config (non-picklist) is changed to "New", then manual override pricing on line 10 should be removed
# When status of a picklist is changed to "New", no change should occur to the manual override pricing
# When status of a config (non-picklist) is changed to "Discontinue", no change should occur to the manual override pricing
# Added line 202 to 208 to update the override price to null in line 10 while saving a cloned config with status New
                if 'headerID' in oRequest.POST and not 'line_100':
                    configuration_id = Configuration.objects.filter(header=oRequest.POST.get('headerID'))
                    configline = ConfigLine.objects.filter(config=configuration_id).filter(line_number=10)
                    linepricing = LinePricing.objects.get(config_line=configline)
                    linepriceid = str(linepricing.id)
                    LinePricing.objects.filter(pk=linepriceid).update(
                    override_price = None)
#D-06102: Unit Price column incorrectly highlighted in Baseline download:
# When cloning a config, we should copy all manual override pricing from the previous config
# When status of that config (non-picklist) is changed to "New", then manual override pricing on line 100 should be removed
# When status of a picklist is changed to "New", no change should occur to the manual override pricing
# When status of a config (non-picklist) is changed to "Discontinue", no change should occur to the manual override pricing
                elif 'headerID' in oRequest.POST and 'line_100':
                    configuration_id = Configuration.objects.filter(header=oRequest.POST.get('headerID'))
                    configline = ConfigLine.objects.filter(config=configuration_id).filter(line_number=100)
                    linepricing = LinePricing.objects.get(config_line=configline)
                    linepriceid = str(linepricing.id)
                    LinePricing.objects.filter(pk=linepriceid).update(
                    override_price = None)
                # If this is a new header, build a form from the posted data
                # (for saving)
                if not oExisting or 'configuration_status' not in oRequest.POST:
                    oModPost = QueryDict(None, mutable=True)
                    oModPost.update(oRequest.POST)
                    oModPost.update({'configuration_status': 1})
                    headerForm = HeaderForm(
                        oModPost,
                        instance=oExisting,
                        readonly=not bCanWriteHeader,
                        browser=DetectBrowser(oRequest))
                else:
                    headerForm = HeaderForm(
                        oRequest.POST,
                        instance=oExisting,
                        readonly=not bCanWriteHeader,
                        browser=DetectBrowser(oRequest))
                # end if

                # If  the user requested to build a new baseline, create a new
                # baseline by the name specified.
                if oRequest.POST['baseline_impacted'] and \
                        oRequest.POST['baseline_impacted'] == 'New' and \
                        oRequest.POST.get('new_baseline', None):
                    Baseline.objects.get_or_create(
                        title__iexact=oRequest.POST['new_baseline'],
                        defaults={'title': oRequest.POST['new_baseline'],
                                  'customer': REF_CUSTOMER.objects.get(
                                      id=oRequest.POST['customer_unit'])
                                  }
                    )
                    headerForm.data._mutable = True
                    headerForm.data['baseline_impacted'] = oRequest.POST[
                        'new_baseline']
                    headerForm.data._mutable = False
                # end if

                # Ensure the data provided is valid
                if headerForm.is_valid():

                    # If the record is in-process or pending approval, changes
                    # can be made and saved
                    if headerForm.cleaned_data['configuration_status'].name in (
                            'In Process', 'In Process/Pending'):
                        try:
                            if bCanWriteHeader:
                                # Create the Header object from the form,
                                # without pushing the object to the database
                                oHeader = headerForm.save(commit=False)
                                oHeader.shipping_condition = '71'

                                # If the record is of type Update or
                                # Discontinue, attempt to link the record that
                                # is replaced.
                                if oHeader.bom_request_type.name in (
                                        'Update', 'Discontinue') and not \
                                        oHeader.model_replaced_link:

                                    # Determine previous revisions
                                    if hasattr(oHeader, 'baseline') and oHeader.baseline:
                                        aExistingRevs = sorted(
                                            list(set([oBaseRev.version for
                                                      oBaseRev in
                                                      oHeader.baseline.baseline
                                                     .baseline_revision_set
                                                     .order_by('version')])),
                                            key=RevisionCompare
                                        )
                                    else:
                                        aExistingRevs = [
                                            oHeader.baseline_version]

                                    iPrev = aExistingRevs.index(
                                        oHeader.baseline_version) - 1

                                    # If a previous revision exists, attempt to
                                    # find a matching record in the previous
                                    # revision
                                    if iPrev >= 0:
                                        try:
                                            oHeader.model_replaced_link = \
                                                Header.objects.get(
                                                    configuration_designation=oHeader.configuration_designation,
                                                    program=oHeader.program,
                                                    baseline_version=
                                                    aExistingRevs[iPrev]
                                                )
                                        except Header.DoesNotExist:
                                            pass

                                # If the discontinuation record has not been
                                # created and is needed, create it
                                if not bDiscontinuationAlreadyCreated and \
                                        oHeader.bom_request_type.name in \
                                        ('New',) and \
                                        oHeader.model_replaced_link:
                                    oDiscontinued = CloneHeader(
                                        oHeader.model_replaced_link)
                                    oDiscontinued.bom_request_type = \
                                        REF_REQUEST.objects.get(
                                            name='Discontinue')
                                    oDiscontinued.configuration_designation = \
                                        oHeader.model_replaced_link.configuration_designation
                                    oDiscontinued.model_replaced = \
                                        oHeader.model_replaced_link.configuration_designation
                                    oDiscontinued.model_replaced_link = \
                                        oHeader.model_replaced_link
                                    oDiscontinued.inquiry_site_template = \
                                        oHeader.inquiry_site_template if \
                                        oHeader.inquiry_site_template and \
                                        oHeader.inquiry_site_template > 0 \
                                        else None
                                    try:
                                        oDiscontinued.save()
                                        bDiscontinuationAlreadyCreated = True
                                    except Exception as ex:
                                        print(ex)

                                # Save the data to the database
                                oHeader.save(request=oRequest)

                                # Create the associated configuration if it does
                                # not already exist
                                if not hasattr(oHeader, 'configuration') or \
                                        oHeader.configuration.get_first_line() \
                                        is None:
                                    if not hasattr(oHeader, 'configuration'):
                                        oConfig = Configuration.objects.create(
                                            **{'header': oHeader})
                                    else:
                                        oConfig = oHeader.configuration

                                    # Non-pick list records need to have the
                                    # first line of the configuration created
                                    # with a part number matching the
                                    # configuration_designation
                                    if not oHeader.pick_list:
                                        (oPartBase, _) = \
                                            PartBase.objects.get_or_create(
                                                **{
                                                    'product_number':
                                                        oHeader.configuration_designation
                                                }
                                            )
                                        oPartBase.unit_of_measure = 'PC'
                                        oPartBase.save()
                                        (oPart, _) = Part.objects.get_or_create(
                                            **{
                                                'base': oPartBase,
                                                'product_description':
                                                    oHeader.model_description
                                            }
                                        )
                        # S-08410:Adjust Model and BoM Header Tab:- Added below if else block to create records in configline table
                        #  based on selected checkbox of line 100 or 10
                                        configid = Configuration.objects.get(header_id=oHeader.id)
                                        confignum = ConfigLine.objects.filter(config_id=configid.id)
                                        if not oHeader.line_100 and len(confignum) == 0:
                                            # ConfigLine.objects.filter(config_id=oHeader.id)

                                            ConfigLine.objects.create(**{
                                                'config': oConfig,
                                                'part': oPart,
                                                'line_number': '10',
                                                'order_qty': 1,
                                                'vendor_article_number':
                                                    oHeader.configuration_designation,
                                            })
                                        elif not oHeader.line_100 and len(confignum) != 0:
                                            ConfigLine.objects.filter(**{
                                                'config': oConfig,
                                                'part': oPart,
                                                'line_number': '100',
                                                'order_qty': 1,
                                                'vendor_article_number':
                                                    oHeader.configuration_designation,
                                            }).delete()
                                            ConfigLine.objects.create(**{
                                                    'config': oConfig,
                                                    'part': oPart,
                                                    'line_number': '10',
                                                    'order_qty': 1,
                                                    'vendor_article_number':
                                                        oHeader.configuration_designation,
                                                })
                                        elif oHeader.line_100 and len(confignum) == 0:
                                            ConfigLine.objects.create(**{
                                                'config': oConfig,
                                                'part': oPart,
                                                'line_number': '100',
                                                'order_qty': 1,
                                                'vendor_article_number':
                                                    oHeader.configuration_designation,
                                            })
                                        elif oHeader.line_100 and len(confignum) != 0:
                                            ConfigLine.objects.filter(**{
                                                'config': oConfig,
                                                'part': oPart,
                                                'line_number': '10',
                                                'order_qty': 1,
                                                'vendor_article_number':
                                                    oHeader.configuration_designation,
                                            }).delete()
                                            ConfigLine.objects.create(**{
                                                    'config': oConfig,
                                                    'part': oPart,
                                                    'line_number': '100',
                                                    'order_qty': 1,
                                                    'vendor_article_number':
                                                        oHeader.configuration_designation,
                                            })
                                else:
                                    # If the configuration already exists, make
                                    # sure the first line of non-pick lists is
                                    # updated to match the
                                    # configuration_designation
                                    if not oHeader.pick_list and \
                                                    oHeader.configuration\
                                                    .get_first_line().part.base\
                                                    .product_number != oHeader\
                                                    .configuration_designation:
                                        # Update line 10 Product number to match
                                        # configuration designation
                                        (oPartBase, _) = PartBase.objects\
                                            .get_or_create(
                                            **{
                                                'product_number':
                                                    oHeader.configuration_designation
                                            }
                                        )
                                        oPartBase.unit_of_measure = 'PC'
                                        oPartBase.save()
                                        (oPart, _) = Part.objects.get_or_create(
                                            **{
                                                'base': oPartBase,
                                                'product_description':
                                                    oHeader.model_description
                                            }
                                        )
                                        oFirstLine = \
                                            oHeader.configuration.get_first_line()
                                        oFirstLine.part = oPart
                                        oFirstLine.vendor_article_number = \
                                            oHeader.configuration_designation
                                        oFirstLine.save()
                                # end if

                                # Create a HeaderLock for new Header objects
                                if not hasattr(oHeader, 'headerlock'):
                                    HeaderLock.objects.create(**{
                                        'header': oHeader,
                                        'session_key': Session.objects.get(
                                            session_key=oRequest.session
                                            .session_key
                                        )
                                    })
                                # end if

                                status_message = oRequest.session['status'] = \
                                    'Form data saved'
                            else:
                                oHeader = oExisting
                                status_message = None
                            # end if

                            bSuccess = True
                        except IntegrityError:
                            oHeader = None
                            status_message = \
                                'Configuration already exists in Baseline'
                        # end try
                    else:
                        oHeader = oExisting
                        bSuccess = True
                    # end if

                    # if the record was saved successfully, redirect to next
                    # view as needed.
                    if bSuccess:
                        if oRequest.POST['formaction'] == 'save':
                            UpdateConfigRevisionData(oHeader)
                            oRequest.session['existing'] = oHeader.pk
                            oExisting = oHeader
                        elif oRequest.POST['formaction'] == 'saveexit':
                            UpdateConfigRevisionData(oHeader)
                            oRequest.session['existing'] = oHeader.pk
                            return redirect(reverse('bomconfig:index'))
                        elif oRequest.POST['formaction'] == 'next':
                            if not bFrameReadOnly:
                                UpdateConfigRevisionData(oHeader)
                                oRequest.session['existing'] = oHeader.pk
                            sDestination = 'bomconfig:configheader'
                            if bCanReadConfig:
                                sDestination = 'bomconfig:config'
                            elif bCanReadTOC:
                                sDestination = 'bomconfig:configtoc'
                            elif bCanReadRevision:
                                sDestination = 'bomconfig:configrevision'
                            elif bCanReadInquiry:
                                sDestination = 'bomconfig:configinquiry'
                            elif bCanReadSiteTemplate:
                                sDestination = 'bomconfig:configsite'
                            # end if

                            return redirect(reverse(sDestination) +
                                            ('?id=' + str(oHeader.id) +
                                             '&readonly=1' if bFrameReadOnly
                                             else ''))
                        # end if
                    # end if
                else:
                    status_message = 'Error(s) occurred'
                # end if
                headerForm.fields['product_area2'].queryset = \
                    REF_PRODUCT_AREA_2.objects.filter(
                        parent=(headerForm.cleaned_data['product_area1'] if
                                headerForm.cleaned_data.get('product_area1',
                                                            None) else None))
                headerForm.fields['program'].queryset = \
                    REF_PROGRAM.objects.filter(
                        parent=(headerForm.cleaned_data['customer_unit'] if
                                headerForm.cleaned_data.get('customer_unit',
                                                            None) else None))
            else:
                # If this is just to view the header, pre-populate the header
                # form
                headerForm = HeaderForm(
                    instance=oExisting,
                    readonly=not bCanWriteHeader,
                    browser=DetectBrowser(oRequest))
                headerForm.fields['product_area2'].queryset = \
                    REF_PRODUCT_AREA_2.objects.filter(
                        parent=(oExisting.product_area1 if oExisting else None))
                headerForm.fields['program'].queryset = \
                    REF_PROGRAM.objects.filter(
                        parent=(oExisting.customer_unit if oExisting else None))
            # end if
        except LockException:
            # If the Header is locked, show the user an error message
            headerForm = HeaderForm(readonly=not bCanWriteHeader,
                                    browser=DetectBrowser(oRequest))
            status_message = 'File is locked for editing'
            if 'existing' in oRequest.session:
                del oRequest.session['existing']
            # end if
        # end try

        # Make 'Person Responsible' field a dropdown of PSM users
        # S-06756- added for restricting person_responsible as per logged in user's cu
        headerForm.fields['person_responsible'].queryset = User_Customer.objects.filter(customer_name__in=aAvailableCU)
        ausers = []
        ausers = headerForm.fields['person_responsible'].queryset.values_list('user_id')

        if not oExisting:
            headerForm.fields['person_responsible'] = fields.ChoiceField(
                # choices=[('', '---------'), ('Suvasish', 'Suvasish')] + list( #This is for local Dev
                choices=[('', '---------')] + list(
                    [(user.first_name + ' ' + user.last_name,
                      user.first_name + ' ' + user.last_name) for user in
                     User.objects.all().filter(id__in=ausers).order_by('last_name') if # added filter(id__in=ausers) for S-06756
                     user.groups.filter(
                         name__in=['BOM_PSM_Baseline_Manager',
                                   'BOM_PSM_Product_Supply_Manager'])
                     ]
                )
            )

        # If the header is writable, make customer_name and baseline_impacted
        # fields into dropdowns
        if not bFrameReadOnly and (not oExisting or (
                        oExisting and type(oExisting) != str and
                        oExisting.configuration_status.name == 'In Process')):
            # This widget needs to use Baseline_Revision because we need to
            # filter using the completed_date, to ensure we only allow baselines
            # that have an in-process configuration to be selected.
            # S - 11552: Baseline tab changes: changed choices for new baseline to catalog
            headerForm.fields['baseline_impacted'].widget = \
                forms.widgets.Select(
                    choices=(('', '---------'),
                             ('New', 'Create New catalog')) + tuple(
                        (obj.title, obj.title) for obj in
                        Baseline_Revision.objects.filter(
                            baseline__customer=oExisting.customer_unit if
                            oExisting else None).filter(
                            completed_date=None).exclude(
                            baseline__title='No Associated Baseline').exclude(baseline__isdeleted=1).order_by(
                            'baseline__title'))
                )

            oCursor = connections['REACT'].cursor()
            oCursor.execute(
                ('SELECT DISTINCT [Customer] FROM ps_fas_contracts '
                 'WHERE [CustomerUnit]=%s'),
                [bytes(oExisting.customer_unit.name, 'ascii') if oExisting else
                 None]
            )
            tResults = oCursor.fetchall()
            headerForm.fields['customer_name'].widget = \
                forms.widgets.Select(
                    choices=(('', '---------'),) +
                    tuple((obj, obj) for obj in chain.from_iterable(tResults))
                )

#S-06166-Shift Header page to new reference table: Added to show the dropdown widget for sales group & populate data
            oCursor.execute(
                ('SELECT DISTINCT [sales_g] FROM ps_SalesOffice_SalesGroup '
                 'WHERE [sales_cu]=%s'),
                [bytes(oExisting.customer_unit.name, 'ascii') if oExisting else
                 None]
            )
            tResults1 = oCursor.fetchall()
            headerForm.fields['sales_group'].widget = \
                forms.widgets.Select(
                    choices=(('', '---------'),) +
                            tuple((obj, obj) for obj in chain.from_iterable(tResults1))
                )

            # oCursor.execute(
            #     ('SELECT DISTINCT [Sales_o] FROM ps_SalesOffice_SalesGroup '
            #      'WHERE [sales_cu]=%s'),
            #     [bytes(oExisting.customer_unit.name, 'ascii') if oExisting else
            #      None]
            # )
            # tResults2 = oCursor.fetchall()
            # headerForm.fields['sales_office'].widget = \
            #     forms.widgets.Select(
            #         choices=(('', '---------'),) +
            #                 tuple((obj, obj) for obj in chain.from_iterable(tResults2))
            #     )

            # S-06166-Shift Header page to new reference table: Added to show the dropdown widget for sold_to_party & populate data
            oCursor.execute(
                ('SELECT DISTINCT [SoldTo] FROM ps_fas_contracts '
                 'WHERE [Customer]=%s'),
                [bytes(oExisting.customer_name, 'ascii') if oExisting else
                 None]
            )
            tResults3 = oCursor.fetchall()
            headerForm.fields['sold_to_party'].widget = \
                forms.widgets.Select(
                    choices=(('', '---------'),) +
                            tuple((obj, obj) for obj in chain.from_iterable(tResults3))
                )

            # S-06166-Shift Header page to new reference table: Added to show the dropdown widget for ericsson contract # & populate data
            # S-07112 - Change dropdown selection view and value - Changed the query to fetch the contract no. and description concatenated to show in UI
            oCursor.execute(
              ("SELECT DISTINCT ([Contract] + '-' + [Description]) as [contract-desc] FROM ps_fas_contracts "
               "WHERE [SoldTo]=%s AND (select convert(varchar(10), getdate(),120))>= [ValidFrom] "
               "AND (SELECT convert(varchar(10), getdate(),120))<= [ValidTo]"),
               [oExisting.sold_to_party if oExisting else None])

            tResults4 = oCursor.fetchall()
            headerForm.fields['ericsson_contract'].widget = \
                forms.widgets.Select(
                    choices=(('', '---------'),) +
                            tuple((obj, obj) for obj in chain.from_iterable(tResults4))
                )

            # oCursor.execute(
            #     ('SELECT DISTINCT [BillTo] FROM ps_fas_contracts '
            #      'WHERE [Contract]=%s'),
            #     [bytes(oExisting.ericsson_contract, 'ascii') if oExisting else
            #      None]
            # )
            # tResults5 = oCursor.fetchall()
            # headerForm.fields['bill_to_party'].widget = \
            #     forms.widgets.Select(
            #         choices=(('', '---------'),) +
            #                 tuple((obj, obj) for obj in chain.from_iterable(tResults5))
            #     )

            # oCursor.execute(
            #     ('SELECT DISTINCT [PayTerms] FROM ps_fas_contracts '
            #      'WHERE [Contract]=%s'),
            #     [bytes(oExisting.ericsson_contract, 'ascii') if oExisting else
            #      None]
            # )
            # tResults6 = oCursor.fetchall()
            # headerForm.fields['payment_terms'].widget = \
            #     forms.widgets.Select(
            #         choices=(('', '---------'),) +
            #                 tuple((obj, obj) for obj in chain.from_iterable(tResults6))
            #     )

        sUserId = None

        # Determine user name
        if oRequest.user.is_authenticated() and oRequest.user.is_active:
            sUserId = oRequest.user.username

        # S-06166-Shift Header page to new reference table: Added to limit the CU dropdown field as per the loggedin user's CU
        headerForm.fields['customer_unit'].queryset = REF_CUSTOMER.objects.filter(name__in=aAvailableCU)
        # added for S-05906 Edit drop down option for BoM Entry Header -  Product Area 1(exclude deleted prodarea1)
        headerForm.fields['product_area1'].queryset = REF_PRODUCT_AREA_1.objects.filter(is_inactive=0)
        # S-05905 : Edit drop down option for BoM Entry Header - Technology: Added to filter dropdown data in BOM entry page
        headerForm.fields['technology'].queryset = REF_TECHNOLOGY.objects.filter(is_inactive=0)
        # S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band: Added to filter dropdown data in BOM entry page
        headerForm.fields['radio_frequency'].queryset = REF_RADIO_FREQUENCY.objects.filter(is_inactive=0)
        headerForm.fields['radio_band'].queryset = REF_RADIO_BAND.objects.filter(is_inactive=0)
        dContext = {
            'header': oExisting,
            'headerForm': headerForm,
            # S-06756- added for restricting customer_unit
            'customerlist': aAvailableCU,
            'break_list': ('Payment Terms', 'Shipping Condition',
                           'Initial Version', 'Configuration/Ordering Status',
                           'Name'),
            'status_message': status_message,
            'header_write_authorized': bCanWriteHeader,
            'header_read_authorized': bCanReadHeader,
            'can_continue': bCanMoveForward,
            'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly
            else 'BoMConfig/template.html',
            'frame_readonly': bFrameReadOnly,
            'non_clonable': ['In Process', 'In Process/Pending'],
            'discontinuation_done': int(bDiscontinuationAlreadyCreated)
        }

        return Default(oRequest, sTemplate, dContext)
# end def


@login_required
def AddConfig(oRequest):
    """
    View used to create and edit configuration data for header objects.
    :param oRequest: Django HTTP request object
    :return: HTTPResponse via Default function
    """
    status_message = oRequest.session.get('status', None)

    # Lock record for editing, if needed
    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    try:
        if oHeader:
            if not bFrameReadOnly:
                Lock(oRequest, oHeader)
            oHeader = Header.objects.get(pk=oHeader)
        else:
            oRequest.session['status'] = 'Define header first'
            return redirect(reverse('bomconfig:configheader'))
            # end if
    except LockException:
        oRequest.session['status'] = 'File locked for editing'
        return redirect(reverse('bomconfig:configheader'))
    # end try

    if status_message:
        del oRequest.session['status']
    # end if

    # Determine if record is in-process or pending approval
    bActive = oHeader.configuration_status.name not in ('In Process',
                                                        'In Process/Pending')
    bPending = oHeader.configuration_status.name in ('In Process/Pending',)

    userin=oRequest.user.groups.all()
    # Determine user read/write permission levels for configurations
    bCanReadConfigBOM = bool(
        SecurityPermission.objects.filter(
            title='Config_Entry_BOM_Read').filter(
            user__in=userin)
    )
    bCanReadConfigSAP = bool(SecurityPermission.objects.filter(
        title='Config_Entry_SAPDoc_Read').filter(
        user__in=userin))
    bCanReadConfigAttr = bool(SecurityPermission.objects.filter(
        title='Config_Entry_Attributes_Read').filter(
        user__in=userin))
    bCanReadConfigPrice = bool(SecurityPermission.objects.filter(
        title='Config_Entry_PriceLinks_Read').filter(
        user__in=userin))
    bCanReadConfigCust = bool(SecurityPermission.objects.filter(
        title='Config_Entry_CustomerData_Read').filter(
        user__in=userin))
    bCanReadConfigBaseline = bool(SecurityPermission.objects.filter(
        title='Config_Entry_Baseline_Read').filter(
        user__in=userin))

    sNeededLevel = oHeader.latesttracker.next_approval
    if sNeededLevel:
        bApprovalPermission = bool(oRequest.user.groups.filter(
            securitypermission__title__in=HeaderTimeTracker.permission_entry(
                sNeededLevel)))
    else:
        bApprovalPermission = False

    if bFrameReadOnly:
        bCanWriteConfigBOM = bCanWriteConfigSAP = bCanWriteConfigAttr = \
            bCanWriteConfigPrice = bCanWriteConfigCust = \
            bCanWriteConfigBaseline = False
    else:
        bCanWriteConfigBOM = bool(
            SecurityPermission.objects.filter(
                title='Config_Entry_BOM_Write').filter(
                user__in=userin)) and (
            not bPending or (bApprovalPermission and sNeededLevel is None))
        bCanWriteConfigSAP = bool(SecurityPermission.objects.filter(
            title='Config_Entry_SAPDoc_Write').filter(
            user__in=userin)) and (not bPending or (
                bApprovalPermission and sNeededLevel is None))
        bCanWriteConfigAttr = bool(SecurityPermission.objects.filter(
            title='Config_Entry_Attributes_Write').filter(
            user__in=userin)) and (
            not bPending or (bApprovalPermission and sNeededLevel == 'cpm'))
        bCanWriteConfigPrice = bool(SecurityPermission.objects.filter(
            title='Config_Entry_PriceLinks_Write').filter(
            user__in=userin)) and (
            not bPending or (bApprovalPermission and sNeededLevel in (
                'blm', 'cust1', 'cust2', 'cust_whse', 'evar', 'brd')))
        bCanWriteConfigCust = bool(SecurityPermission.objects.filter(
            title='Config_Entry_CustomerData_Write').filter(
            user__in=userin)) and (
            not bPending or (bApprovalPermission and sNeededLevel in (
                'cust1', 'cust2', 'cust_whse', 'evar', 'brd')))
        bCanWriteConfigBaseline = bool(SecurityPermission.objects.filter(
            title='Config_Entry_Baseline_Write').filter(
            user__in=userin)) and (
            not bPending or (bApprovalPermission and sNeededLevel in (
                'blm', 'csr')))

    # Determine which pages to which the user is able to move forward or
    # backward
    bCanReadHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Read').filter(user__in=userin))
    bCanReadTOC = bool(SecurityPermission.objects.filter(
        title='Config_ToC_Read').filter(user__in=userin))
    bCanReadRevision = bool(SecurityPermission.objects.filter(
        title='Config_Revision_Read').filter(
        user__in=userin))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(
        title='SAP_Inquiry_Creation_Read').filter(
        user__in=userin))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(
        title='SAP_ST_Creation_Read').filter(
        user__in=userin))

    bCanMoveForward = bCanReadTOC or bCanReadRevision or bCanReadInquiry or \
        bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader

    bCanReadConfig = bCanReadConfigBOM or bCanReadConfigSAP or \
        bCanReadConfigAttr or bCanReadConfigPrice or bCanReadConfigCust or \
        bCanReadConfigBaseline
    bCanWriteConfig = bCanWriteConfigBOM or bCanWriteConfigSAP or \
        bCanWriteConfigAttr or bCanWriteConfigPrice or bCanWriteConfigCust or \
        bCanWriteConfigBaseline

    # When POSTing a save
    if oRequest.method == 'POST' and oRequest.POST:

        # Create ConfigForm from POSTed data and existing Configuration instance
        configForm = ConfigForm(
            oRequest.POST,
            instance=oHeader.configuration if oHeader and hasattr(
                oHeader, 'configuration') else None)

        # If the form is valid
        if configForm.is_valid():

            # If the user has permission to write to the configuration
            if bCanWriteConfig:

                # Save the configuration (without committing to DB)
                oConfig = configForm.save(commit=False)

                # Attach the configuration to the Header saved in the session.
                # This is typically unneeded, but performed just to be safe.
                if not hasattr(oHeader, 'configuration'):
                    oConfig.header = oHeader
                    oConfig.save()
                # end if

                # ConfigLine data for the configuration can only be saved if the
                # record is in-process or pending approval
                if oHeader.configuration_status.name in ('In Process',
                                                         'In Process/Pending'):
                    oForm = json.loads(oRequest.POST['data_form'])

                    # Clean configuration line data POSTed into a format that is
                    # suitable for our purposes.  Ensure each line is
                    # represented as a dictionary, and that all column values
                    # are present.  Also remove any empty rows (this is why the
                    # list is iterated in reverse.  If it weren't, changing the
                    # size of the array mid-iteration would cause an error.)
                    for index in range(len(oForm) - 1, -1, -1):

                        # Convert to dict for uniformity
                        if type(oForm[index]) == list:
                            oForm[index] = {str(x): y for (x, y) in enumerate(
                                oForm[index])}

                        # Remove row status info (not needed in save)
                        if '0' in oForm[index]:
                            del oForm[index]['0']

                        # Remove empty rows and make sure non-empty rows have
                        # all columns present
                        if all(x in (None, '') for x in list(
                                oForm[index].values()
                        )) or len(oForm[index]) < 1:
                            del oForm[index]
                            continue
                        else:
                            for x in range(36):
                                if str(x) not in oForm[index]:
                                    oForm[index][str(x)] = None
                            # end for
                        # end if
                    # end for

                    oUpdateDate = timezone.now()

                    for dConfigLine in oForm:
                        # Create PartBase objects as needed
                        dBaseData = {
                            'product_number': dConfigLine['2'].lstrip('. '),
                            'unit_of_measure': dConfigLine['5']
                        }

                        (oBase, _) = PartBase.objects.get_or_create(
                            product_number=dConfigLine['2'].lstrip('. ')
                        )
                        PartBase.objects.filter(pk=oBase.pk).update(**dBaseData)

                        dPartData = {
                            'product_description': dConfigLine['3'].strip()
                            .upper() if dConfigLine['3'] else
                            dConfigLine['3'],
                            'base': oBase
                        }

                        # Create and/or Update Part objects as needed. Always
                        # try to update PartBase objects that have no product
                        # description first.
                        oNullQuery = Q(product_description__isnull=True)
                        oNoneQuery = Q(product_description='None')
                        oBlankQuery = Q(product_description='')
                        if Part.objects.filter(
                                base=oBase).filter(
                                            oNoneQuery | oNullQuery |
                                oBlankQuery) and not Part.objects.filter(
                                **dPartData):
                            iPartPk = Part.objects.filter(base=oBase).filter(
                                oNoneQuery | oNullQuery | oBlankQuery
                            ).first().pk
                            Part.objects.filter(pk=iPartPk).update(**dPartData)
                            oPart = Part.objects.get(pk=iPartPk)
                        else:
                            (oPart, _) = Part.objects.get_or_create(**dPartData)

                        # Create data dictionary for creating/updating
                        # ConfigLine object
                        dLineData = {'line_number': dConfigLine['1'],
                                     'order_qty': dConfigLine['4'] or None,
                                     'contextId': dConfigLine['6'],
                                     'plant': dConfigLine['7'],
                                     'sloc': dConfigLine['8'],
                                     'item_category': dConfigLine['9'],
                                     'pcode': dConfigLine['10'],
                                     'commodity_type': dConfigLine['11'],
                                     'package_type': dConfigLine['12'],
                                     'spud': REF_SPUD.objects.get(
                                         name=dConfigLine['13']
                                     ) if dConfigLine['13'] else None,
    # S-08473: Adjust configuration table to include new columns:-Added below portfolio code at no.14
                                     'current_portfolio_code': dConfigLine['14'],
                                     'REcode': dConfigLine['15'],
                                     'mu_flag': dConfigLine['16'],
                                     'x_plant': dConfigLine['17'],
    # S-08473: Adjust configuration table to include new columns:-Added below plant_specific_material_status & distribution_change_specific_material_status at no.18 & 19 respectively
                                     'plant_specific_material_status': dConfigLine['18'],
                                     'distribution_chain_specific_material_status': dConfigLine['19'],
                                     'internal_notes': dConfigLine['20'],
                                     'higher_level_item': dConfigLine['23'],
                                     'material_group_5': dConfigLine['24'],
                                     'purchase_order_item_num':
                                         dConfigLine['25'],
                                     'condition_type': dConfigLine['26'],
                                     'amount': dConfigLine['27'] or None,
                                     'traceability_req': dConfigLine['28'],
                                     'customer_asset': dConfigLine['29'],
                                     'customer_asset_tagging':
                                         dConfigLine['30'],
                                     'customer_number': dConfigLine['31'],
                                     'sec_customer_number': dConfigLine['32'],
                                     'vendor_article_number': dConfigLine['33'],
                                     'comments': dConfigLine['34'],
                                     'additional_ref': dConfigLine['35'],
                                     'config': oConfig,
                                     'part': oPart,
                                     'is_child': bool(
                                         dConfigLine['2'].startswith('.') and
                                         not dConfigLine['2'].startswith('..')),
                                     'is_grandchild': bool(
                                         dConfigLine['2'].startswith('..')),
                                     'last_updated': oUpdateDate}

                        # Update ConfigLine dict with CustomerAsset data as
                        # needed
                        try:
                            oMPNCustMap = CustomerPartInfo.objects.get(
                                part__product_number=oPart.base.product_number,
                                customer=oHeader.customer_unit,
                                active=True)

                            dLineData.update({
                                'customer_asset': "Y" if
                                oMPNCustMap.customer_asset else "N" if
                                oMPNCustMap.customer_asset is False else None,
                                'customer_asset_tagging': "Y" if
                                oMPNCustMap.customer_asset_tagging else "N" if
                                oMPNCustMap.customer_asset_tagging is False else
                                None,
                                'customer_number': oMPNCustMap.customer_number,
                                'sec_customer_number':
                                    oMPNCustMap.second_customer_number,
                            })
                        except CustomerPartInfo.DoesNotExist:
                            pass

                        # Update existing ConfigLine or create a new one if
                        # needed.  Updating reduces database churn of creating
                        # and deleting.
                        if ConfigLine.objects.filter(config=oConfig).filter(
                                line_number=dConfigLine['1']):
                            oConfigLine = ConfigLine.objects.get(
                                **{'config': oConfig,
                                   'line_number': dConfigLine['1']}
                            )
                            ConfigLine.objects.filter(pk=oConfigLine.pk).update(
                                **dLineData)
                        else:
                            oConfigLine = ConfigLine(**dLineData)
                            oConfigLine.save()
                        # end if

                        # Determine Pricing data for the line
                        oConfigLine = ConfigLine.objects.get(
                            **{'config': oConfig,
                               'line_number': dConfigLine['1']}
                        )
                        dPriceData = {'config_line': oConfigLine}
                        (oPrice, _) = LinePricing.objects.get_or_create(
                            **dPriceData)
                        oPriceObj = PricingObject.getClosestMatch(oConfigLine)
                        oPrice.pricing_object = oPriceObj
                        oPrice.save()
                    # end for

                    # Remove any ConfigLines that were not updated (which means
                    # they must have been removed)
                    for oOldLine in ConfigLine.objects.filter(config=oConfig):
                        if oOldLine.last_updated != oUpdateDate:
                            oOldLine.delete()
                    status_message = oRequest.session['status'] = \
                        'Form data saved'
                # end if
                oConfig.save(request=oRequest)
            # end if

            # Redirect the view as needed
            if oRequest.POST['formaction'] == 'prev':
                if not bFrameReadOnly:
                    UpdateConfigRevisionData(oHeader)
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:config'
                if bCanReadHeader:
                    sDestination = 'bomconfig:configheader'
                # end if

                return redirect(
                    reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                             '&readonly=1' if bFrameReadOnly
                                             else ''))
            elif oRequest.POST['formaction'] == 'saveexit':
                if not bFrameReadOnly:
                    UpdateConfigRevisionData(oHeader)
                    oRequest.session['existing'] = oHeader.pk
                return redirect(reverse('bomconfig:index'))
            elif oRequest.POST['formaction'] == 'save':
                if not bFrameReadOnly:
                    UpdateConfigRevisionData(oHeader)
                    oRequest.session['existing'] = oHeader.pk
                if 'status' in oRequest.session:
                    del oRequest.session['status']
                # end if
            elif oRequest.POST['formaction'] == 'next':
                if not bFrameReadOnly:
                    UpdateConfigRevisionData(oHeader)
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:config'
                if bCanReadTOC:
                    sDestination = 'bomconfig:configtoc'
                elif bCanReadRevision:
                    sDestination = 'bomconfig:configrevision'
                elif bCanReadInquiry:
                    sDestination = 'bomconfig:configinquiry'
                elif bCanReadSiteTemplate:
                    sDestination = 'bomconfig:configsite'
                # end if

                return redirect(
                    reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                             '&readonly=1' if bFrameReadOnly
                                             else ''))
            elif oRequest.POST['formaction']=='validate':
                status_message = oRequest.session['status'] = ''
                sDestination = 'bomconfig:config'
                return redirect(
                    reverse(sDestination) + ('?validation=true'))
            # end if
        else:
            status_message = configForm.errors['__all__'].as_text()
        # end if
    else:
        # Build ConfigForm from configuration data
        configForm = ConfigForm(
            instance=oHeader.configuration if
            oHeader and hasattr(oHeader, 'configuration') else None,)
    # end if

    # Build and validate data for display in configuration table
    data = BuildDataArray(oHeader, config=True)
    error_matrix ={}

    validation = oRequest.GET.get('validation')

    if validation == 'true':
        error_matrix = Validator(data, oHeader, bCanWriteConfig,
                                 bFrameReadOnly or bActive)
    else:
        error_matrix = {}

    dContext = {
        'data_array': json.dumps(data),
        'errors': error_matrix,
        'form': configForm,
        'header': oHeader,
        'status_message': status_message,
        'config_bom_read_authorized': bCanReadConfigBOM,
        'config_sap_read_authorized': bCanReadConfigSAP,
        'config_attr_read_authorized': bCanReadConfigAttr,
        'config_price_read_authorized': bCanReadConfigPrice,
        'config_cust_read_authorized': bCanReadConfigCust,
        'config_baseline_read_authorized': bCanReadConfigBaseline,
        'config_read_authorized': bCanReadConfig,
        'config_bom_write_authorized': bCanWriteConfigBOM,
        'config_sap_write_authorized': bCanWriteConfigSAP,
        'config_attr_write_authorized': bCanWriteConfigAttr,
        'config_price_write_authorized': bCanWriteConfigPrice,
        'config_cust_write_authorized': bCanWriteConfigCust,
        'config_baseline_write_authorized': bCanWriteConfigBaseline,
        'config_write_authorized': bCanWriteConfig,
        'can_continue': bCanMoveForward,
        'can_previous': bCanMoveBack,
        'condition_list': [obj.name for obj in REF_CONDITION.objects.all()],
        'material_group_list': [obj.name for obj in
                                REF_MATERIAL_GROUP.objects.all()],
        'product_pkg_list': [obj.name for obj in REF_PRODUCT_PKG.objects.all()],
        'spud_list': [obj.name for obj in REF_SPUD.objects.filter(is_inactive=0)], # S-05909 : Edit drop down option for BoM Entry Header - SPUD: Added to filter dropdown data in configuration page

        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else
        'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly,
        'active_lock': bActive
    }

    oCursor = connections['BCAMDB'].cursor()
    oCursor.execute("SELECT [ICG] FROM [BCAMDB].[dbo].[REF_ITEM_CAT_GROUP]")
    dContext.update({'item_cat_list': [obj for (obj,) in oCursor.fetchall()]})

    oCursor.close()
    return Default(oRequest,
                   sTemplate='BoMConfig/configuration.html',
                   dContext=dContext)
# end def


@login_required
def AddTOC(oRequest):
    """
    View for viewing and editing Table of Content data for Headers
    :param oRequest: Django HTTP request object
    :return: HTTPResponse via Default function
    """
    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    # Determine user's read/write permissions for Table of Content data
    bCanReadTOC = bool(SecurityPermission.objects.filter(
        title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))

    if bFrameReadOnly:
        bCanWriteTOC = False
    else:
        bCanWriteTOC = bool(SecurityPermission.objects.filter(
            title='Config_ToC_Write').filter(
            user__in=oRequest.user.groups.all()))

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(
        title='Config_Entry_BOM_Read').filter(
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

    bCanMoveForward = bCanReadRevision or bCanReadInquiry or \
        bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader or bCanReadConfig

    # Lock record for editing, if needed
    try:
        if oHeader:
            if not bFrameReadOnly:
                Lock(oRequest, oHeader)
            oHeader = Header.objects.get(pk=oHeader)
        else:
            oRequest.session['status'] = 'Define header first'
            return redirect(reverse('bomconfig:configheader'))
        # end if
    except LockException:
        oRequest.session['status'] = 'File locked for editing'
        return redirect(reverse('bomconfig:configheader'))
    # end try

    if status_message:
        del oRequest.session['status']

    # When POSTing a save
    if oRequest.method == 'POST' and oRequest.POST:
        configForm = ConfigForm(
            oRequest.POST,
            instance=oHeader.configuration if
            oHeader and hasattr(oHeader, 'configuration') else None)
        if configForm.is_valid():
            if bCanWriteTOC:
                oConfig = configForm.save(commit=False)
                if not hasattr(oHeader, 'configuration'):
                    oConfig.header = oHeader
                # end if
                oConfig.save()

                # Update ToC data for "In Process" records only
                if oHeader.configuration_status.name == 'In Process':
                    oForm = json.loads(oRequest.POST['data_form'])
                    if type(oForm[0]) == list:
                        oForm[0] = {str(x): y for (x, y) in enumerate(oForm[0])}

                    if '1' in oForm[0] and oForm[0]['1'] not in ('', None):
                        oHeader.customer_designation = oForm[0]['1']
                    if '13' in oForm[0] and oForm[0]['13'] not in ('', None):
                        oHeader.internal_notes = oForm[0]['13']
                    if '14' in oForm[0] and oForm[0]['14'] not in ('', None):
                        oHeader.external_notes = oForm[0]['14']

                    oHeader.save(request=oRequest)
                    status_message = oRequest.session['status'] = \
                        'Form data saved'
                # end if
            # end if

            # Redirect the view as needed
            if oRequest.POST['formaction'] == 'prev':
                if not bFrameReadOnly:
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:configtoc'
                if bCanReadConfig:
                    sDestination = 'bomconfig:config'
                elif bCanReadHeader:
                    sDestination = 'bomconfig:configheader'
                # end if

                return redirect(
                    reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                             '&readonly=1' if bFrameReadOnly
                                             else '')
                )
            elif oRequest.POST['formaction'] == 'saveexit':
                if not bFrameReadOnly:
                    oRequest.session['existing'] = oHeader.pk
                return redirect(reverse('bomconfig:index'))
            elif oRequest.POST['formaction'] == 'save':
                if not bFrameReadOnly:
                    oRequest.session['existing'] = oHeader.pk
                if 'status' in oRequest.session:
                    del oRequest.session['status']
                # end if
            elif oRequest.POST['formaction'] == 'next':
                if not bFrameReadOnly:
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:configtoc'
                if bCanReadRevision:
                    sDestination = 'bomconfig:configrevision'
                elif bCanReadInquiry:
                    sDestination = 'bomconfig:configinquiry'
                elif bCanReadSiteTemplate:
                    sDestination = 'bomconfig:configsite'
                # end if

                return redirect(
                    reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                             '&readonly=1' if bFrameReadOnly
                                             else '')
                )
            # end if
        # end if
    else:
        # Build ConfigForm from configuration data
        configForm = ConfigForm(
            instance=oHeader.configuration if
            oHeader and hasattr(oHeader, 'configuration') else None,
            initial={
                'net_value': getattr(oHeader.configuration, 'net_value') if
                hasattr(oHeader, 'configuration') else '0',
                'zpru_total': getattr(oHeader.configuration, 'zpru_total') if
                hasattr(oHeader, 'configuration') else '0'
            }
        )
    # end if

    # Build data for display in configuration table
    data = BuildDataArray(oHeader=oHeader, toc=True)

    dContext = {
        'data_array': data,
        'status_message': status_message,
        'form': configForm,
        'header': oHeader,
        'toc_read_authorized': bCanReadTOC,
        'toc_write_authorized': bCanWriteTOC,
        'can_continue': bCanMoveForward,
        'can_previous': bCanMoveBack,
        'base_template': 'BoMConfig/frame_template.html' if
        bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }
    return Default(oRequest,
                   sTemplate='BoMConfig/configtoc.html',
                   dContext=dContext)
# end def


@login_required
def AddRevision(oRequest):
    """
    View for creating and editing Revision data for a header/configuration
    :param oRequest: Django HTTP request
    :return: HTTPResponse via Default function
    """
    error_matrix = []
    valid = True
    oForm = None

    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    # Determine users read/write permissions
    bCanReadRevision = bool(SecurityPermission.objects.filter(
        title='Config_Revision_Read').filter(
        user__in=oRequest.user.groups.all()))
    if bFrameReadOnly:
        bCanWriteRevision = False
    else:
        bCanWriteRevision = bool(SecurityPermission.objects.filter(
            title='Config_Revision_Write').filter(
            user__in=oRequest.user.groups.all()))

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(
        title='Config_Entry_BOM_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(
        title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(
        title='SAP_Inquiry_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(
        title='SAP_ST_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadInquiry or bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader or bCanReadConfig or bCanReadTOC

    # Lock Header object if needed
    try:
        if oHeader:
            if not bFrameReadOnly:
                Lock(oRequest, oHeader)
            oHeader = Header.objects.get(pk=oHeader)
        else:
            oRequest.session['status'] = 'Define header first'
            return redirect(reverse('bomconfig:configheader'))
        # end if
    except LockException:
        oRequest.session['status'] = 'File locked for editing'
        return redirect(reverse('bomconfig:configheader'))
    # end try

    if status_message:
        del oRequest.session['status']

    # If POSTing data to save
    if oRequest.method == 'POST' and oRequest.POST:
        oForm = json.loads(oRequest.POST['data_form'])

        # Convert list of list to list of dictionary
        if type(oForm[0]) == list:
            oForm[0] = {str(x): y for (x, y) in enumerate(oForm[0])}

        # Validate entered information
        if '3' in oForm[0] and oForm[0]['3'] not in ('', None):
            form = DateForm({'date': oForm[0]['3']})
            if form.is_valid():
                oHeader.release_date = form.cleaned_data['date']
            else:
                error_matrix.append([None, None, 'X - Not a valid date.'])
                valid = False
            # end if

        if '7' in oForm[0] and oForm[0]['7'] not in ('', None):
            oHeader.change_comments = oForm[0]['7']

        if valid:
            try:
                # Save updated data
                if oHeader.configuration_status.name == 'In Process' and \
                        bCanWriteRevision:
                    oHeader.save(request=oRequest)
                    status_message = oRequest.session['status'] = \
                        'Form data saved'
                # end if

                # Redirect the view as needed
                if oRequest.POST['formaction'] == 'prev':
                    sDestination = 'bomconfig:configrevision'
                    if bCanReadTOC:
                        sDestination = 'bomconfig:configtoc'
                    elif bCanReadConfig:
                        sDestination = 'bomconfig:config'
                    elif bCanReadHeader:
                        sDestination = 'bomconfig:configheader'
                    # end if

                    return redirect(
                        reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                                 '&readonly=1' if bFrameReadOnly
                                                 else '')
                    )
                elif oRequest.POST['formaction'] == 'saveexit':
                    return redirect(reverse('bomconfig:index'))
                elif oRequest.POST['formaction'] == 'save':
                    if 'status' in oRequest.session:
                        del oRequest.session['status']
                    # end if
                elif oRequest.POST['formaction'] == 'next':
                    sDestination = 'bomconfig:configrevision'
                    if bCanReadInquiry:
                        sDestination = 'bomconfig:configinquiry'
                    elif bCanReadSiteTemplate:
                        sDestination = 'bomconfig:configsite'
                    # end if

                    return redirect(
                        reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                                 '&readonly=1' if bFrameReadOnly
                                                 else '')
                    )
                # end if
            except IntegrityError:
                status_message = 'Configuration already exists in Baseline'
        # end if
    # end if

    # Build data for revision view
    data = BuildDataArray(oHeader, revision=True)

    if not valid and oForm:
        data[0].update({'2': oForm[0]['2']})

    dContext = {
        'data_array': data,
        'status_message': status_message,
        'header': oHeader,
        'error_matrix': error_matrix,
        'revision_read_authorized': bCanReadRevision,
        'revision_write_authorized': bCanWriteRevision,
        'can_continue': bCanMoveForward,
        'can_previous': bCanMoveBack,
        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly
        else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }
    return Default(oRequest,
                   sTemplate='BoMConfig/configrevision.html',
                   dContext=dContext)
# end def


@login_required
def AddInquiry(oRequest, inquiry):
    """

    :param oRequest: Django HTTP request
    :param inquiry: Boolean to indicate if viewing an inquiry or site template
    :return: HTTPResponse via Default function
    """
    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(
        title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(
        title='Config_Entry_BOM_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(
        title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(
        title='Config_Revision_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(
        title='SAP_Inquiry_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(
        title='SAP_ST_Creation_Read').filter(
        user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadSiteTemplate and inquiry
    bCanMoveBack = bCanReadHeader or bCanReadConfig or bCanReadTOC or \
        bCanReadRevision or (not inquiry and bCanReadInquiry)

    # Lock Header object, if needed
    try:
        if oHeader:
            if not bFrameReadOnly:
                Lock(oRequest, oHeader)
            oHeader = Header.objects.get(pk=oHeader)
        else:
            oRequest.session['status'] = 'Define header first'
            return redirect(reverse('bomconfig:configheader'))
        # end if
    except LockException:
        oRequest.session['status'] = 'File locked for editing'
        return redirect(reverse('bomconfig:configheader'))
    # end try

    if status_message:
        del oRequest.session['status']

    if oRequest.method == 'POST' and oRequest.POST:
        # Redirect the view as needed
        if oRequest.POST['formaction'] == 'prev':
            sDestination = 'bomconfig:configinquiry' if inquiry \
                else 'bomconfig:configsite'
            if bCanReadInquiry and not inquiry:
                sDestination = 'bomconfig:configinquiry'
            elif bCanReadRevision:
                sDestination = 'bomconfig:configrevision'
            elif bCanReadTOC:
                sDestination = 'bomconfig:configtoc'
            elif bCanReadConfig:
                sDestination = 'bomconfig:config'
            elif bCanReadHeader:
                sDestination = 'bomconfig:configheader'
            # end if

            return redirect(
                reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                         '&readonly=1' if bFrameReadOnly
                                         else '')
            )
        elif oRequest.POST['formaction'] == 'next':
            sDestination = 'bomconfig:configinquiry' if inquiry \
                else 'bomconfig:configsite'
            if bCanReadSiteTemplate and inquiry:
                sDestination = 'bomconfig:configsite'
            # end if

            return redirect(
                reverse(sDestination) + ('?id=' + str(oHeader.id) +
                                         '&readonly=1' if bFrameReadOnly
                                         else '')
            )
    # end if

    # Build data for inquiry or site template view
    data = BuildDataArray(oHeader=oHeader, inquiry=inquiry, site=not inquiry)

    # Build ConfigForm using configuration instance
    configForm = ConfigForm(
        instance=oHeader.configuration if
        oHeader and hasattr(oHeader, 'configuration') else None)
    configForm.fields['internal_external_linkage'].widget.attrs[
        'disabled'] = True

    dContext = {
        'data_array': data,
        'status_message': status_message,
        'inquiry': inquiry,
        'form': configForm,
        'header': oHeader,
        'inquiry_read_authorized': bCanReadInquiry,
        'sitetemplate_read_authorized': bCanReadSiteTemplate,
        'can_continue': bCanMoveForward,
        'can_previous': bCanMoveBack,
        'base_template': 'BoMConfig/frame_template.html' if
        bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }

    return Default(
        oRequest,
        sTemplate='BoMConfig/inquiry.html',
        dContext=dContext
    )
# end def


def BuildDataArray(oHeader=None, config=False, toc=False, inquiry=False,
                   site=False, revision=False):
    """
    Builds an array to pass to a HTML instance of Handsontable.
    :param oHeader: Header object being used to generate data
    :param config: Boolean to indicate if generating data for configuration view
    :param toc: Boolean to indicate if generating data for table of content view
    :param inquiry: Boolean to indicate if generating data for inquiry view
    :param site: Boolean to indicate if generating data for site template view
    :param revision: Boolean to indicate if generating data for revision view
    :return: List of dictionaries
    """
    # Ensure only one boolean value is set to True
    if not bool(config) ^ bool(toc) ^ bool(inquiry) ^ bool(site) ^ \
            bool(revision):
        raise AssertionError('Only one argument should be true')
    # end if

    # If building a configuration, inquiry, or site template
    if config or inquiry or site:
        # If Header is not defined or has no Configuration attached (extremely
        # rare)
        if (not oHeader) or (oHeader and not hasattr(oHeader, 'configuration')):
            if config:
                if not oHeader.pick_list:
                    return [{
                        '1': '10',
                        '2': oHeader.configuration_designation.upper(),
                        '3': oHeader.model_description or '',
                        '4': '1',
                        '5': 'PC'
                    }]
                else:
                    return [{}]
            else:
                return [{
                    '0': '10',
                    '1': oHeader.configuration_designation.upper(),
                    '2': oHeader.model_description or '',
                    '3': '1'
                }]
            # end if
        # end if

        # Sort ConfigLines by line numbers
        oConfig = oHeader.configuration
        aConfigLines = ConfigLine.objects.filter(config=oConfig).order_by(
            'line_number')
        aConfigLines = sorted(
            aConfigLines,
            key=lambda x: [
                int(y) for y in getattr(x, 'line_number').split('.')
                ]
        )

        # Add ConfigLine data to data array
        aData = []
        for Line in aConfigLines:
            if config:
                dLine = {
                    '1': Line.line_number,
                    '2': ('..' if Line.is_grandchild else '.'
                          if Line.is_child else ''
                          ) + Line.part.base.product_number,
                    '3': Line.part.product_description,
                    '4': str(Line.order_qty or ''),
                    '5': Line.part.base.unit_of_measure,
                    '6': Line.contextId,
                    '7': Line.plant,
                    '8': Line.sloc,
                    '9': Line.item_category,
                    '10': Line.pcode,
                    '11': Line.commodity_type,
                    '12': Line.package_type,
                    '13': str(Line.spud) if Line.spud else None,
 # S-08473: Adjust configuration table to include new columns:-Added below portfolio code at no.14; this is responsible to show the saved value on page load
                    '14': Line.current_portfolio_code,
                    '15': Line.REcode,
                    '16': Line.mu_flag,
                    '17': str(Line.x_plant).zfill(2) if Line.x_plant else None,
 # S-08473: Adjust configuration table to include new columns:-Added below plant_specific_material_status & distribution_change_specific_material_status at no.18 & 19 respectively; this is responsible to show the saved value on page load
                   '18': Line.plant_specific_material_status,
                    '19': Line.distribution_chain_specific_material_status,
                    '20': Line.internal_notes,

                    '23': Line.higher_level_item,
                    '24': Line.material_group_5,
                    '25': Line.purchase_order_item_num,
                    '26': Line.condition_type,
                    '27': Line.amount,
                    '28': Line.traceability_req,
                    '29': Line.customer_asset,
                    '30': Line.customer_asset_tagging,
                    '31': Line.customer_number,
                    '32': Line.sec_customer_number,
                    '33': Line.vendor_article_number,
                    '34': Line.comments,
                    '35': Line.additional_ref
                }
# S-05770:-USCC(now MTW) Unit Price functionality - Below case is for new column 'Unit Price' at case no.18,Added to show unit price based on CU,
    # if MTW,NonPicklist-Line 10 is blank,parts wil have UP; pickList-All lines will have UP
    # for other CUs, picklist & nonPicklist:- UP will be blank in all lines
                if oHeader.customer_unit_id == 9:               # 9 is the ID for MTW customer.

    # S-08410:Adjust Model and BoM Header Tab:- Added below line to fetch the first _line of the config
                    oFirstLine = oHeader.configuration.get_first_line()

                    if not oHeader.pick_list:
    # S-08410:Adjust Model and BoM Header Tab:- Added below line to fetch if the config's first line starts with 10 or 100
                        if oFirstLine.line_number =='10':
                            if str(Line.line_number) == '10':

                                dLine.update({'21': None})
                                # if oConfig.override_net_value:
                                #     dLine.update(
                                #         {'21': str(oConfig.override_net_value)}
                                #     )
                                # else:
                                #     dLine.update({'21': str(oConfig.net_value) if oConfig.net_value is not None else None})
                                    # end if
                            else:
    # S-10577: Only Pull in pricing with Traceability = Y into config :-: Added below the condition to check if traceability value is Y,
    #  only then the price would be displayed - [MTW - Non-Picklist - Not line 10]
                                if Line.traceability_req == 'Y':
                                    if GrabValue(Line, 'linepricing.override_price'):
                                        dLine.update(
                                            {'21': str(Line.linepricing.override_price)}
                                        )
                                    elif GrabValue(Line,
                                                   'linepricing.pricing_object.unit_price'):
                                        dLine.update(
                                            {
                                                '21': str(
                                                    Line.linepricing.pricing_object.unit_price)
                                            }
                                        )
                                    else:
                                        dLine.update({'21': None})
                                        # end if
                                        # end if
                                        # end if
                                else:
                                    dLine.update({'21': None})
                        else:
                            if oFirstLine.line_number == '100':
                                if str(Line.line_number) == '100':
                                    dLine.update({'21': None})
                                else:
    # S-10577: Only Pull in pricing with Traceability = Y into config :-: Added below the condition to check if traceability value is Y,
    #  only then the price would be displayed [MTW - Non-Picklist - Not line 100]
                                    if Line.traceability_req == 'Y':
                                        if GrabValue(Line, 'linepricing.override_price'):
                                            dLine.update(
                                                {'21': str(Line.linepricing.override_price)}
                                            )
                                        elif GrabValue(Line,
                                                       'linepricing.pricing_object.unit_price'):
                                            dLine.update(
                                                {
                                                    '21': str(
                                                        Line.linepricing.pricing_object.unit_price)
                                                }
                                            )
                                        else:
                                            dLine.update({'21': None})
                                            # end if
                                            # end if
                                            # end if
                                    else:
                                        dLine.update({'21': None})
                    else:
    # S-10577: Only Pull in pricing with Traceability = Y into config :-: Added below the condition to check if traceability value is Y,
    #  only then the price would be displayed [MTW - Picklist ]
                        if Line.traceability_req == 'Y':
                            if GrabValue(Line, 'linepricing.override_price'):
                                dLine.update(
                                    {'21': str(Line.linepricing.override_price)}
                                )
                            elif GrabValue(Line,
                                           'linepricing.pricing_object.unit_price'):
                                dLine.update(
                                    {
                                        '21': str(
                                            Line.linepricing.pricing_object.unit_price)
                                    }
                                )
                            else:
                                dLine.update({'21': None})
                                # end if
                                # end if
                        else:
                            dLine.update({'21': None})
                else:
                    dLine.update({'21': None})

    # S-05770:-USCC Unit Price functionality - The below case is for Net Price functionality,case no. 18 is changed to 19
    # NonPicklist-Sum of UP of all the parts is shown as NP in line 10
    # Picklist- All lines will have the price displayed
        # S-08410:Adjust Model and BoM Header Tab:- Added below line to fetch the first _line of the config
                oFirstLine = oHeader.configuration.get_first_line()
                if not oHeader.pick_list:
                    if oFirstLine.line_number == '10':           # for Line 10 configs
                        if str(Line.line_number) == '10':
                            if oConfig.override_net_value:
                                dLine.update(
                                    {'22': str(oConfig.override_net_value)}
                                )
                            else:
                                dLine.update({'22': str(oConfig.net_value) if oConfig.net_value is not None else None})
                            # end if
                        else:
                            dLine.update({'22': ''})
                        # end if
                    else:                       # for Line 100 configs
                        if str(Line.line_number) == '100':
                            if oConfig.override_net_value:
                                dLine.update(
                                    {'22': str(oConfig.override_net_value)}
                                )
                            else:
                                dLine.update({'22': str(oConfig.net_value) if oConfig.net_value is not None else None})
                                # end if
                        else:
                            dLine.update({'22': ''})
                            # end if
                else:
                   if GrabValue(Line, 'linepricing.override_price'):
                        dLine.update(
                            {'22': str(Line.linepricing.override_price)}
                        )
                   elif GrabValue(Line,
                                   'linepricing.pricing_object.unit_price'):
                        dLine.update(
                            {
                                '22': str(
                                    Line.linepricing.pricing_object.unit_price)
                            }
                        )
                   else:
                        dLine.update({'22': None})
                    # end if
                # end if

            else:
                LineNumber = None
                if '.' not in Line.line_number:
                    try:
                        LineNumber = int(Line.line_number)
                    except (ValueError, TypeError):
                        # This ensures that we only continue when the stored
                        # line number is an integer
                        pass
                    # end try
                # end if

                if LineNumber:
                    dLine = {'0': Line.line_number,
                             '1': Line.part.base.product_number,
                             '2': Line.part.product_description,
                             '3': Line.order_qty,
                             '4': Line.plant,
                             '5': Line.sloc,
                             '6': Line.item_category}
                    if inquiry:
                        dLine.update(
                            {
                                '9': Line.material_group_5,
                                '10': Line.purchase_order_item_num,
                                '11': Line.condition_type,
                                '12': Line.amount
                            }
                        )
 # D-06152-UnboundLocalError at /acc/entry/inquiry:- Added below line to fetch the first line of config
                        oFirstLine = oHeader.configuration.get_first_line()
 # S-08410:Adjust Model and BoM Header Tab:- Added below line to fetch if the config's first line starts with 10 or 100
                        if not oHeader.pick_list:
                            if oFirstLine.line_number == '10':  # for Line 10 configs
                                if str(Line.line_number) == '10':
                                    if oConfig.override_net_value:
                                        dLine.update(
                                            {'7': oConfig.override_net_value}
                                        )
                                    else:
                                        dLine.update({'7': oConfig.net_value})
                                        # end if
                                else:
                                    dLine.update({'7': ''})
                                    # end if
                            else:
                                if str(Line.line_number) == '100':          # for Line 100 configs
                                    if oConfig.override_net_value:
                                        dLine.update(
                                            {'7': oConfig.override_net_value}
                                        )
                                    else:
                                        dLine.update({'7': oConfig.net_value})
                                        # end if
                                else:
                                    dLine.update({'7': ''})
                                    # end if
                        else:
                            if GrabValue(Line, 'linepricing.override_price'):
                                dLine.update(
                                    {'7': Line.linepricing.override_price}
                                )
                            elif GrabValue(
                                    Line,
                                    'linepricing.pricing_object.unit_price'):
                                dLine.update(
                                    {'7': Line.linepricing.pricing_object
                                        .unit_price}
                                )
                            else:
                                dLine.update({'7': ''})
                                # end if
                        # end if

                        if LineNumber == 10 and not oHeader.pick_list:
                            dLine.update(
                                {'8':
                                 oHeader.configuration.override_net_value or
                                 oHeader.configuration.net_value}
                            )
                    else:
                        dLine.update(({'7': Line.higher_level_item}))
                    # end if
                else:
                    continue
            # end if

            # Remove blank items from dictionary
            if not config:
                for key in copy.deepcopy(dLine):
                    if not dLine[key]:
                        del dLine[key]
                    # end if
                # end for
            aData.append(dLine)
        # end for
        return aData

    # If building table of contents
    elif toc:
        if not oHeader:
            return [[]]
        else:
            return [{'0': oHeader.configuration_designation,
                     '1': oHeader.customer_designation or '',
                     '2': oHeader.technology.name if oHeader.technology else '',
                     '3': oHeader.product_area1.name if oHeader.product_area1
                     else '',
                     '4': oHeader.product_area2.name if oHeader.product_area2
                     else '',
                     '5': oHeader.model or '',
                     '6': oHeader.model_description or '',
                     '7': oHeader.model_replaced or '',
                     '9': oHeader.bom_request_type.name,
                     '10': oHeader.configuration_status.name,
                     '11': oHeader.inquiry_site_template if
                     str(oHeader.inquiry_site_template).startswith('1') else
                     oHeader.inquiry_site_template * -1 if
                     oHeader.inquiry_site_template and
                     oHeader.inquiry_site_template < -1 and str(
                         oHeader.inquiry_site_template
                     ).startswith('-1') else '',
                     '12': oHeader.inquiry_site_template if
                     str(oHeader.inquiry_site_template).startswith('4') else
                     oHeader.inquiry_site_template * -1 if
                     oHeader.inquiry_site_template and
                     oHeader.inquiry_site_template < -1 and str(
                         oHeader.inquiry_site_template
                     ).startswith('-4') else '',
                     '13': (oHeader.internal_notes or ''),
                     '14': (oHeader.external_notes or '')}]

    # If building revision
    elif revision:
        if not oHeader or not hasattr(oHeader, 'configuration'):
            return [{}]
        else:
            data = []

            # Append revision data starting at current revision and working
            # backwards
            while oHeader and hasattr(oHeader, 'configuration'):
         # S-08411:Adjust Configuration UI & Backend to include Line Numbering scheme:- Added below if else block to set the line #
         # in a variable and use the same in the filter used in appending the data below; This is done to show in the revision tab of
         # a config
                if not oHeader.line_100:
                    linenum = '10'
                else:
                    linenum = '100'
                data.append({
                    '0': oHeader.bom_version,
                    '1': oHeader.baseline.title if oHeader.baseline else '',
                    '2': oHeader.baseline_version,
                    '3': oHeader.release_date.strftime('%b. %d, %Y') if
                    oHeader.release_date else '',
                    '4': oHeader.model if not oHeader.pick_list else 'None',
                    '5': oHeader.configuration.configline_set.filter(
                        line_number=linenum)[0].customer_number               # S-08411: Used the assigned variabie 'linenum' in this filter
                    if not oHeader.pick_list and
                    oHeader.configuration.configline_set.filter(
                        line_number=linenum)[0].customer_number else '',      # S-08411: Used the assigned variabie 'linenum' in this filter
                    '6': oHeader.change_notes or '',
                    '7': oHeader.change_comments or '',
                    '8': oHeader.person_responsible,
                })

                # Step to previous revision, if it exists
                if oHeader.baseline:
                    aExistingRevs = sorted(
                        list(set([oBaseRev.version for oBaseRev in
                                  oHeader.baseline.baseline
                                 .baseline_revision_set.order_by('version')])),
                        key=RevisionCompare)
                else:
                    aExistingRevs = [oHeader.baseline_version]

                iPrev = aExistingRevs.index(oHeader.baseline_version) - 1

                if oHeader.model_replaced_link:
                    oHeader = oHeader.model_replaced_link
                elif iPrev >= 0:
                    sPrevious = aExistingRevs[iPrev]

                    oQmodel = Q(
                        configuration_designation=oHeader.model_replaced
                    )
                    oQconfig = Q(
                        configuration_designation=oHeader.configuration_designation
                    )
                    oQprogram = Q(program=oHeader.program)
                    oQbaseline = Q(baseline=oHeader.baseline.previous_revision)
                    oQbaselineVer = Q(
                        baseline_impacted=oHeader.baseline_impacted,
                        baseline_version=sPrevious
                    )
                    try:
                        oHeader = Header.objects.get(oQmodel,
                                                     oQprogram,
                                                     oQbaseline | oQbaselineVer)
                    except Header.DoesNotExist:
                        try:
                            oHeader = Header.objects.get(
                                oQconfig,
                                oQprogram,
                                oQbaseline | oQbaselineVer)
                        except Header.DoesNotExist:
                            oHeader = None
                    # end try
                else:
                    oHeader = None
                # end if
            # end while

            return data
        # end if
    # end if

    return [{}]
# end def


def Validator(aData, oHead, bCanWriteConfig, bFormatCheckOnly):
    """
    Function to validate data for configuration view
    :param aData: List of dictionaries representing configuration line data
    :param oHead: Header object providing configuration data
    :param bCanWriteConfig: Boolean indicating if user can write to
    configuration
    :param bFormatCheckOnly: Boolean indicating if function should only clean up
    existing data in aData, without validating or determining errors
    :return: 2x2 array of dictionaries containing error information
    """
    Parent = 0
    Child = 0
    Grandchild = 0
    parents = set()
    children = set()

    aLineNumbers = []
    error_matrix = []

    # Populate error_matrix with blank information
    for _ in range(len(aData)):
        dummy = []
        for i in range(36):
            dummy.append({'value': ''})
        error_matrix.append(dummy)

# S-08474:Pull BCAMDB on Part addition/validation : Changed the query to fetch the values for 3 new columns on page load
# D-05973:Traceability not pulling for some parts : Added the traceability condition (gmdm.[PRIM Traceability]!='NULL')
# in line 2179 to pick the part which has traceability as not null

    if not bFormatCheckOnly:
        # Collect data from database(s)
        oCursor = connections['BCAMDB'].cursor()
        oCursor.execute(
            """
            SELECT bmps.[Material], bmps.[Material Description], bmps.[Base Unit of Measure],
                  bmps.Plant, zmard.SLoc,zmvke.[Item Category],pcode_fcode.[Description] AS [P-Code Description],
                  pcode_fcode.[Commodity],bmps.[MTyp],bmps.[PRIM RE Code],recode.[Title],
                  recode.[Description],bmps.[MU-Flag],bmps.[X-Plant Status],
                  xplantstatus.[Description] AS [X-Plant Description],gmdm.[PRIM Traceability],bmps.[Current Portfolio Code],zmarc.[MS],zmvke.[Material Status]
            FROM dbo.BI_MATERIAL_PLANT_SUMMARY AS bmps
            LEFT JOIN dbo.SAP_ZQR_GMDM AS gmdm
                ON bmps.Material=gmdm.[Material Number] AND bmps.Plant = gmdm.Plant
            LEFT JOIN (SELECT [Material],[Plant], MAX([Item Category]) AS [Item Category],[Material Status]
                 FROM [BCAMDB].[dbo].[SAP_ZMVKE]  WHERE [Item Category] <> 'NORM' GROUP BY  [Material],[Plant],[Material Status] ) zmvke
                 ON bmps.Material=zmvke.Material AND bmps.Plant=zmvke.Plant
            LEFT JOIN SAP_ZMARD AS zmard
                ON bmps.Material=zmard.Material AND bmps.Plant=zmard.Plant
            LEFT JOIN dbo.REF_PCODE_FCODE AS pcode_fcode
                ON bmps.[P Code]=pcode_fcode.[PCODE ]
            LEFT JOIN dbo.REF_PRODUCT_STATUS_CODES AS recode
                ON gmdm.[PRIM RE Code]=recode.[Status Code]
            LEFT JOIN dbo.REF_X_PLANT_STATUS_DESCRIPTIONS AS xplantstatus
                ON bmps.[X-Plant Status]=xplantstatus.[X-Plant Status Code]
            LEFT JOIN dbo.SAP_ZMARC zmarc
                ON  bmps.[Material] =zmarc.Material and bmps.Plant=zmarc.Plant
            WHERE bmps.[Plant] IN ('2685','2666','2392')
                  AND gmdm.[PRIM Traceability]!='NULL'
                  AND bmps.[Material] IN %s
                  ORDER BY  bmps.[Material]       
            """,
            (tuple(
                map(lambda val: bytes(val.lstrip('.'), 'ascii'),
                    [obj['2'] for obj in aData]
                    )
            ),)
        )

        tAllData = oCursor.fetchall()

        if any([obj['10'] for obj in aData if '10' in obj]):
            oCursor.execute(
                'SELECT [PCODE],[FireCODE],[Description],[Commodity] FROM '
                'dbo.REF_PCODE_FCODE WHERE [PCODE] IN %s',
                (tuple(
                    map(lambda val: bytes(val, 'ascii'),
                        [re.match(
                            r'^(?:\()?(?P<pcode>[A-Z]?\d{2,3})(?:-\d{4}\).*)?$',
                            obj['10']).group('pcode') for obj in aData if
                         re.match(r'^\d{2,3}$|^\(\d{2,3}-\d{4}\).*$|^[A-Z]\d{2}$'
                                  '|^\([A-Z]\d{2}-\d{4}\).*$', obj['10'] or '') is not None]
                        )
                ), )
            )
            tPCode = oCursor.fetchall()
        else:
            tPCode = ()

        if any([obj['7'] for obj in aData if '7' in obj]):
            oCursor.execute(
                'SELECT [Plant] FROM dbo.REF_PLANTS WHERE [Plant] IN %s',
                (tuple(
                    map(lambda val: bytes(val, 'ascii'),
                        [obj['7'] for obj in aData if obj['7'] not in ('', None)]
                        )
                ), )
            )
            tPlants = oCursor.fetchall()
        else:
            tPlants = ()

        if any([obj['8'] for obj in aData if '8' in obj]):
            oCursor.execute(
                'SELECT DISTINCT [SLOC] FROM dbo.REF_PLANT_SLOC WHERE [SLOC] IN %s',
                (tuple(
                    map(lambda val: bytes(val, 'ascii'),
                        [obj['8'] for obj in aData if obj['8'] not in ('', None)]
                        )
                ), )
            )
            tSLOC = oCursor.fetchall()
        else:
            tSLOC = ()

        oCursor.close()

        dPartData = {}

        # S-10574: Manually updated Traceability req.should carry over to the cloned config:-: Added below to fetch the configuration ID
        oConfig = oHead.configuration

        for row in tAllData:
            if row[0] in dPartData:
                 # Add row data to existing entry
                if row[1] not in dPartData[row[0]]['Description']:
                    dPartData[row[0]]['Description'].append(row[1])

                if row[2] not in dPartData[row[0]]['UOM']:
                    dPartData[row[0]]['UOM'].append(row[2])

                if (row[3], row[4]) not in dPartData[row[0]]['Plant/SLoc']:
                    dPartData[row[0]]['Plant/SLoc'].append((row[3], row[4]))

                if row[5] not in dPartData[row[0]]['ItemCat']:
                    dPartData[row[0]]['ItemCat'].append(row[5])

                if row[6] not in dPartData[row[0]]['P-Code']:
                    dPartData[row[0]]['P-Code'].append(row[6])

                if row[7] not in dPartData[row[0]]['Commodity']:
                    dPartData[row[0]]['Commodity'].append(row[7])

                if row[8] not in dPartData[row[0]]['M-Type']:
                    dPartData[row[0]]['M-Type'].append(row[8])

                if row[9] not in dPartData[row[0]]['RE-Code']:
                    dPartData[row[0]]['RE-Code'].append(row[9])

                if row[10] not in dPartData[row[0]]['RE-Code Title']:
                    dPartData[row[0]]['RE-Code Title'].append(row[10])

                if row[11] not in dPartData[row[0]]['RE-Code Desc']:
                    dPartData[row[0]]['RE-Code Desc'].append(row[11])

                if row[12] not in dPartData[row[0]]['MU-Flag']:
                    dPartData[row[0]]['MU-Flag'].append(row[12])

                if row[13] not in dPartData[row[0]]['X-Plant']:
                    dPartData[row[0]]['X-Plant'].append(row[13])

                if row[14] not in dPartData[row[0]]['X-Plant Desc']:
                    dPartData[row[0]]['X-Plant Desc'].append(row[14])

                if row[15] not in dPartData[row[0]]['Traceability']:
                    dPartData[row[0]]['Traceability'].append(row[15])

# S-08474:Pull BCAMDB on Part addition/validation : Added below 3 conditions to fetch the value from DB on page load after save
                if row[16] not in dPartData[row[0]]['Current Portfolio Code']:
                    dPartData[row[0]]['Current Portfolio Code'].append(row[16])

                if row[17] not in dPartData[row[0]]['Plant Specific Material Status']:
                    dPartData[row[0]]['Plant Specific Material Status'].append(row[17])

                if row[18] not in dPartData[row[0]]['Distribution Chain Specific Material Status']:
                    dPartData[row[0]]['Distribution Chain Specific Material Status'].append(row[18])
            else:
                # Create new entry
                dPartData[row[0]] = {
                    'Description': [row[1]],
                    'UOM': [row[2]],
                    'Plant/SLoc': [(row[3], row[4])],
                    'ItemCat': [row[5]],
                    'P-Code': [row[6]],
                    'Commodity': [row[7]],
                    'M-Type': [row[8]],
                    'RE-Code': [row[9]],
                    'RE-Code Title': [row[10]],
                    'RE-Code Desc': [row[11]],
                    'MU-Flag': [row[12]],
                    'X-Plant': [row[13]],
                    'X-Plant Desc': [row[14]],
                    'Traceability': [row[15]],
 # S-08474:Pull BCAMDB on Part addition/validation : Added below 3 lines to fetch the value from DB on page load after save
                    'Current Portfolio Code': [row[16]],
                    'Plant Specific Material Status': [row[17]],
                    'Distribution Chain Specific Material Status': [row[18]]
                }
            # end if
        # end for

        dPCodes = {}
        for row in tPCode:
            if row[0] in dPCodes:
                dPCodes[row[0]]['FireCode'].append(row[1])
                dPCodes[row[0]]['Description'].append(row[2])
                dPCodes[row[0]]['Commodity'].append(row[3])
            else:
                dPCodes[row[0]] = {
                    'FireCode': [row[1]],
                    'Description': [row[2]],
                    'Commodity': [row[3]]
                }
            # end if
        # end for

    # Step through each row
    for index in range(len(aData)):

        # Check entered data and formats
        # Product Number
        if aData[index]['2'].strip('.').strip() in ('', None):
            aData[index]['2'] = ''
            if not bFormatCheckOnly:
                error_matrix[index][2]['value'] += \
                    'X - No Product Number provided.\n'
        else:
            aData[index]['2'] = aData[index]['2'].upper()
            if len(aData[index]['2'].strip('. ')) > 18:
                if not bFormatCheckOnly:
                    error_matrix[index][2]['value'] += \
                        'X - Product Number exceeds 18 characters.\n'
            # end if
        # end if

        # Vendor Article Number
        if '33' in aData[index] and aData[index]['33'] in ('', None):
            aData[index]['33'] = aData[index]['2'].strip('./')

        # Line number
        # If line number is provided, ensure it is the correct format and track
        # the last Part, Child, Grandchild line number encountered.  This is
        # used to ensure any new part numbers fit correctly.
        if '1' in aData[index] and aData[index]['1'] not in ('', None):
            if not re.match("^\d+(?:\.\d+){0,2}$|^$", aData[index]['1'] or
                            '') and aData[index]['1'] not in (None,):
                if not bFormatCheckOnly:
                    error_matrix[index][1]['value'] += \
                        'X - Invalid character. Use 0-9 and "." only.\n'
            elif aData[index]['1'] not in ('', None):
                this = aData[index]['1']
                if this.count('.') == 0 and this:
                    Parent = int(this)
                    Child = 0
                    Grandchild = 0
                    parents.add(str(Parent))
                elif this.count('.') == 1:
                    Parent = int(this[:this.find('.')])
                    if str(Parent) not in parents:
                        if not bFormatCheckOnly:
                            error_matrix[index][1]['value'] += \
                                'X - This parent (' + str(Parent) + \
                                ') does not exist.\n'
                    else:
                        Child = int(this[this.rfind('.') + 1:])
                        children.add(str(Parent) + "." + str(Child))
                        Grandchild = 0
                elif this.count('.') == 2:
                    Parent = int(this[:this.find('.')])
                    if str(Parent) not in parents:
                        if not bFormatCheckOnly:
                            error_matrix[index][1]['value'] += \
                                'X - This parent (' + str(Parent) + \
                                ') does not exist.\n'
                    else:
                        Child = int(this[this.find('.') + 1: this.rfind('.')])
                        if str(Parent)+"."+str(Child) not in children:
                            if not bFormatCheckOnly:
                                error_matrix[index][1]['value'] += \
                                    'X - This child (' + str(Parent) + '.' + \
                                    str(Child) + ') does not exist.\n'
                        else:
                            Grandchild = int(this[this.rfind('.') + 1:])
                # end if
            else:
                aData[index]['1'] = ''
            # end if

            if aData[index]['2'] not in (None, ''):
                if aData[index]['1'].count('.') == 2 and not \
                        aData[index]['2'].startswith('..'):
                    aData[index]['2'] = '..' + aData[index]['2']
                elif aData[index]['1'].count('.') == 1 and not \
                        aData[index]['2'].startswith('.'):
                    aData[index]['2'] = '.' + aData[index]['2']
                # end if
            # end if
        else:
            if not bFormatCheckOnly:
                if aData[index]['2'].startswith('..'):
                    Grandchild += 1
                    aData[index]['1'] = str(Parent) + "." + str(Child) + "." + \
                        str(Grandchild)
                elif aData[index]['2'].startswith('.'):
                    Child += 1
                    aData[index]['1'] = str(Parent) + "." + str(Child)
                else:
                    if Parent % 10 == 0:
                        Parent += 10
                    else:
                        Parent += 1
                    Child = 0
                    Grandchild = 0
                    aData[index]['1'] = str(Parent)
            # end if
        # end if

        # Product Description
        # if '3' not in aData[index] or aData[index]['3'] is None or aData[index]['3'].strip() == '':
        #     aData[index]['3'] = ''
        # else:
        #     if len(aData[index]['3']) > 40:
        #         if not bFormatCheckOnly:
        #             error_matrix[index][3]['value'] += \
        #                 'X - Product Description exceeds 40 characters.\n'

        # Order Qty
        # if not re.match("^\d+(?:.\d+)?$", aData[index]['4'] or ''):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][4]['value'] += 'X - Invalid Order Qty.\n'
        #     if aData[index]['4'] in ('None', '', None):
        #         aData[index]['4'] = ''
        # end if

        # Plant
        # if not re.match("^\d{4}$|^$", aData[index]['7'] if '7' in aData[index] and aData[index]['7'] is not None else ''):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][7]['value'] += 'X - Invalid Plant.\n'
        # end if

        # SLOC
        # if not re.match("^\w{4}$|^$", aData[index]['8'] if '8' in aData[index] and aData[index]['8'] is not None else ''):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][8]['value'] += 'X - Invalid SLOC.\n'
        # end if

        # P-Code
        # if '10' in aData[index] and aData[index]['10']:
        #     aData[index]['10'] = aData[index]['10'].upper()
        #
        # if not re.match("^\d{2,3}$|^\(\d{2,3}-\d{4}\).*$|^[A-Z]\d{2}$"
        #                 "|^\([A-Z]\d{2}-\d{4}\).*$|^$",
        #                 aData[index]['10'] if '10' in aData[index] and aData[index]['10'] is not None else '',
        #                 re.IGNORECASE):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][10]['value'] += 'X - Invalid P-Code format.\n'
        # end if

        # HW/SW Ind
        # if '11' in aData[index] and aData[index]['11']:
        #     aData[index]['11'] = aData[index]['11'].upper()
        #
        # if not re.match("^HW$|^SW$|^CS$|^$",
        #                 aData[index]['11'] if '11' in aData[index] and aData[index]['11'] is not None else '',
        #                 re.IGNORECASE):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][11]['value'] += 'X - Invalid HW/SW Ind.\n'
        # end if

        # Condition Type & Amount Supplied Together
        NoCondition = '26' not in aData[index] or aData[index]['26'] in ('', None)
        NoAmount = '27' not in aData[index] or aData[index]['27'] in ('', None)
        if not bFormatCheckOnly:
            if (NoCondition and not NoAmount) or (NoAmount and not NoCondition):
                if NoAmount and not NoCondition:
                    error_matrix[index][27]['value'] += \
                        'X - Condition Type provided without Amount.\n'
                else:
                    error_matrix[index][26]['value'] += \
                        'X - Amount provided without Condition Type.\n'
                # end if
            # end if

        # Amount
        # if '23' in aData[index] and isinstance(aData[index]['23'], str):
        #     aData[index]['23'] = aData[index]['23'].replace('$',
        #                                                     '').replace(',',
        #                                                                 '')
        #
        # if not re.match("^(?:-)?\d+(?:\.\d+)?$|^$",
        #                 str(aData[index]['23']) if
        #                 '23' in aData[index] and aData[index]['23'] is not None else ''):
        #     if not bFormatCheckOnly:
        #         error_matrix[index][23]['value'] += \
        #             'X - Invalid Amount provided.\n'
        # end if

        # if '25' in aData[index] and aData[index]['25'] in ('N', 'NO') and '26' in aData[index] and aData[index]['26'] in \
        #         ('Y', 'YES'):
        #     error_matrix[index][26]['value'] += \
        #         ('X - Cannot mark Customer Asset Tagging when '
        #          'part is not Customer Asset.\n')

        if not bFormatCheckOnly:
            corePartNumber = aData[index]['2'].lstrip('.')
            # Populate Read-only fields

            if corePartNumber in dPartData.keys():
                if oHead.configuration_status.name == 'In Process':
                    # Product Description
                    if aData[index]['3'] in (None, ''):
                        aData[index]['3'] = dPartData[corePartNumber]['Description'][0] or ''

                    # MU-Flag
                    aData[index]['16'] = dPartData[corePartNumber]['MU-Flag'][0] or ''

                    # X-Plant
                    aData[index]['17'] = dPartData[corePartNumber]['X-Plant'][0] or ''

# S-08476: Adjust save process to preserve new columns:-Added below 3 lines to show the saved value of 3 new columns on page load
                    # Current Portfolio-Code
                    aData[index]['14'] = dPartData[corePartNumber]['Current Portfolio Code'][0] or ''

                    # Plant Specific Material Status
                    aData[index]['18'] = dPartData[corePartNumber]['Plant Specific Material Status'][0] or ''

                    # Distribution Chain Specific Material Status
                    aData[index]['19'] = dPartData[corePartNumber]['Distribution Chain Specific Material Status'][0] or ''

                    # UoM
                    aData[index]['5'] = dPartData[corePartNumber]['UOM'][0] or ''

                    # Item Category Group
                    if not re.match("^Z[A-Z0-9]{3}$|^$",
                                    aData[index]['9'] or '',
                                    re.IGNORECASE):
                        aData[index]['9'] = dPartData[corePartNumber]['ItemCat'][0] or ''

                    # Product Package Type
                    if dPartData[corePartNumber]['ItemCat'][0] == 'ZF26':
                        aData[index]['12'] = 'Fixed Product Package (FPP)'
                    elif dPartData[corePartNumber]['M-Type'][0] == 'ZASO':
                        aData[index]['12'] = 'Assembled Sales Object (ASO)'
                        if aData[index]['6'] in (None, ''):
                            error_matrix[index][6]['value'] += \
                                'X - ContextID must be populated for ASO parts.\n'
                    elif dPartData[corePartNumber]['M-Type'][0] == 'ZAVA':
                        aData[index]['12'] = 'Material Variant (MV)'
                    elif dPartData[corePartNumber]['M-Type'][0] == 'ZEDY':
                        aData[index]['12'] = 'Dynamic Product Package (DPP)'


 # S-08475: Adjust validation process to flag parts with non-green portfolio code : Added below condition to show the warning message on the cell if the color value is not green
                    # Portfolio Code
                    if dPartData[corePartNumber]['Current Portfolio Code'][0] != 'Green':
                        error_matrix[index][14]['value'] += '! - Portfolio code is Non-Green.' + '\n'
                    # end if

                    # X-Plant Description
                    if dPartData[corePartNumber]['X-Plant Desc'][0]\
                            and dPartData[corePartNumber]['X-Plant Desc'][0] not in error_matrix[index][17]['value']:
                        error_matrix[index][17]['value'] += dPartData[corePartNumber]['X-Plant Desc'][0] + '\n'
                    # end if
                # end if
            else:
                error_matrix[index][2]['value'] += \
                    '! - Product Number not found.\n'
                if oHead.configuration_status.name == 'In Process':
                    aData[index]['5'] = ''
                    aData[index]['14'] = ''
                    aData[index]['15'] = ''
                    aData[index]['16'] = ''
                    aData[index]['17'] = ''
                    aData[index]['18'] = ''
                    aData[index]['19'] = ''
            # end def

            # P-Code, Fire Code, Description & HW/SW Indicator
            if '10' in aData[index] and aData[index]['10'] in ('', None):  # P-Code is blank, so fill in with data from part (if available)
                if corePartNumber in dPartData.keys() and oHead.configuration_status.name == 'In Process':
                    aData[index]['10'] = dPartData[corePartNumber]['P-Code'][0]
                else:
                    aData[index]['10'] = ''

                # HW/SW Indication
                if aData[index]['11'] in ('None', '', None) and corePartNumber in dPartData.keys() and oHead.configuration_status.name == 'In Process':
                    aData[index]['11'] = dPartData[corePartNumber]['Commodity'][0]
                else:
                    aData[index]['11'] = aData[index]['11'] or ''

                # end if
            else:  # P-Code is populated (but may not be a valid value)
                # If P-Code is valid, extract the P-Code portion
                if re.match("^\d{2,3}$|^\(\d{2,3}-\d{4}\).*$|^[A-Z]\d{2}$"
                            "|^\([A-Z]\d{2}-\d{4}\).*$",
                            aData[index]['10'] if '10' in aData[index] else '',
                            re.IGNORECASE):
                    P_Code = re.match(
                        r'^(?:\()?(?P<pcode>[A-Z]?\d{2,3})(?:-\d{4}\).*)?$',
                        aData[index]['10'] if '10' in aData[index] else '').group('pcode')

                    # Use the extracted value to find the full P-Code description
                    if P_Code in dPCodes.keys():
                        P_Code = dPCodes[P_Code]
                        bVerified = True
                    else:  # No matching P-Code was found in database
                        bVerified = False

                    if bVerified:  # P-Code is valid and has a full description available
                        # # If the matching value does not match what is stored for the part, add a warning
                        # if corePartNumber in dPartData.keys() and dPartData[corePartNumber]['P-Code'][0] != P_Code['Description'][0]:
                        #     error_matrix[index][10]['value'] += '! - P-Code provided does not match P-Code stored for Material Number.\n'

                        # # If the matching value does not match what is stored in the DB for the p-code, add a warning
                        # if re.match("^\(\d{2,3}-\d{4}\).*$|^\([A-Z]\d{2}-\d{4}\).*$", aData[index]['10'], re.IGNORECASE) and aData[index]['10'].upper() != P_Code['Description'][0].upper():
                        #     if oHead.configuration_status.name == 'In Process':
                        #         aData[index]['10'] = P_Code['Description'][0].upper()
                        #     else:
                        #         error_matrix[index][10]['value'] += '! - P-Code description is not latest value.\n'

                        # If P-Code provided is valid, but is not in full description format, replace with full description
                        if re.match("^\(\d{2,3}-\d{4}\).*$|^\([A-Z]\d{2}-\d{4}\).*$", aData[index]['10'], re.IGNORECASE) is None and oHead.configuration_status.name == 'In Process':
                            aData[index]['10'] = P_Code['Description'][0].upper()

                        # HW/SW Indication
                        if aData[index]['11'] in ('None', '', None):
                            aData[index]['11'] = P_Code['Commodity'][0] or ''
                        # end if
                    else:
                        # Leave value as-is and add warning
                        error_matrix[index][10]['value'] += '! - P-Code not found.\n'

                        # HW/SW Indication
                        if aData[index]['11'] in ('None', '', None) and corePartNumber in dPartData.keys() and oHead.configuration_status.name == 'In Process':
                            aData[index]['11'] = dPartData[corePartNumber]['Commodity'][0]
                        else:
                            aData[index]['11'] = aData[index]['11'] or ''
                        # end if

                else:  # else leave it alone, the error will be displayed to the user
                    aData[index]['10'] = aData[index]['10'] if '10' in aData[index] else ''

                    # HW/SW Indication
                    if '11' in aData[index] and aData[index]['11'] in ('', None) and corePartNumber in dPartData.keys() and oHead.configuration_status.name == 'In Process':
                        aData[index]['11'] = dPartData[corePartNumber]['Commodity'][0]
                    else:
                        aData[index]['11'] = aData[index]['11'] if '11' in aData[index] else ''
                    # end if

            if oHead.configuration_status.name == 'In Process':

                if corePartNumber in dPartData.keys():
                    # # Current Portfolio-Code
                    # aData[index]['14'] = dPartData[corePartNumber]['Current Portfolio Code'][0] or ''

                    # RE-Code
                    aData[index]['15'] = dPartData[corePartNumber]['RE-Code'][0] or ''

                    # Traceability Req
 # S-10574: Manually updated Traceability req.should carry over to the cloned config:-: Added below block of code that fetches the traceability
 #  value from CSP DB and also from BCAMDB, then checks if it mismatches.If it mismatches then it shows the value fetched from CSP DB(Overridden traceability)

                    # fetches the config line for the part number
                    aConfigLines = ConfigLine.objects.filter(config=oConfig).filter(vendor_article_number=aData[index]['33'])
                    for oline in aConfigLines:
                        if oline.traceability_req == 'Y':       # Checks the traceability value for the part number
                            traceval = 'Z001'
                        else:
                            traceval = 'Z002'

                        if traceval != dPartData[corePartNumber]['Traceability'][0]:    # Checks if mismatches with the BCAMDB value
                            aData[index]['28'] = oline.traceability_req                  # writes the data in UI
                            # Previous code - line below
                         # aData[index]['28'] = 'Y' if dPartData[corePartNumber]['Traceability'][0] == 'Z001' else 'N' \
                         #    if dPartData[corePartNumber]['Traceability'][0] == 'Z002' else ''

                    # RE-Code title
                    if aData[index]['20']:
                        if dPartData[corePartNumber]['RE-Code Title'][0] and dPartData[corePartNumber]['RE-Code Title'][0] not in aData[index]['20']:
                            aData[index]['20'] = aData[index]['20'] + '; ' + \
                                                 dPartData[corePartNumber]['RE-Code Title'][0]
                    else:
                        aData[index]['20'] = dPartData[corePartNumber]['RE-Code Title'][0] or ''

                    # RE-Code description
                    if dPartData[corePartNumber]['RE-Code Desc'][0] and dPartData[corePartNumber]['RE-Code Desc'][0] not in error_matrix[index][15]['value']:
                        error_matrix[index][15]['value'] += dPartData[corePartNumber]['RE-Code Desc'][0] + '\n'
                else:
                    # RE-Code
                    aData[index]['15'] = ''
                    # Traceability Req
                    aData[index]['28'] = ''
                # end if
            # end if

            # Ensure Plant exists for part number
            if '7' in aData[index] and aData[index]['7'] not in ('', None):
                if (aData[index]['7'],) not in tPlants:
                    error_matrix[index][7]['value'] += \
                        "! - Plant not found in database.\n"

                if corePartNumber in dPartData.keys() and not any(aData[index]['7'] == plant for (plant, _) in dPartData[corePartNumber]['Plant/SLoc']):
                    error_matrix[index][7]['value'] += \
                        "! - Plant not found for material.\n"
            # end if

            # Ensure SLOC exists for part number
            if '8' in aData[index] and aData[index]['8'] not in ('', None):
                if (aData[index]['8'],) not in tSLOC:
                    error_matrix[index][8]['value'] += \
                        "! - SLOC not found in database.\n"

                if corePartNumber in dPartData.keys() and (aData[index]['7'], aData[index]['8']) not in dPartData[corePartNumber]['Plant/SLoc']:
                    error_matrix[index][8]['value'] += \
                        '! - Plant/SLOC combination not found for material.\n'
                # end if
            # end if
        # end if

        aLineNumbers.append(aData[index]['1'])

        if not bFormatCheckOnly:
            # Update line status
            if any("X - " in error['value'] for error in error_matrix[index]):
                aData[index]['0'] = 'X'
            elif any("! - " in error['value'] for error in error_matrix[index]):
                aData[index]['0'] = '!'
            else:
                aData[index]['0'] = 'OK'
            # end if

        # Change any NoneTypes to blank strings
        for i in aData[index]:
            if not aData[index][i]:
                aData[index][i] = ''
    # end for

    # Check for duplicate line numbers
    dIndices = {}
    aDuplicates = []
    for index in range(len(aData)):
        try:
            dIndices[aData[index]['1']].append(index)
        except KeyError:
            dIndices[aData[index]['1']] = [index]
        # end try
    # end for

    for aIndices in dIndices.values():
        if len(aIndices) > 1:
            aDuplicates.extend(aIndices[1:])
        # end if
    # end for

    if not bFormatCheckOnly:
        for index in aDuplicates:
            aData[index]['0'] = 'X'
            error_matrix[index][1]['value'] = 'X - Duplicate line number.\n'
        # end for

    return error_matrix
# end def


def ReactSearch(oRequest):
    """
    View used to search REACT tool database for REACT request number and provide
    all attached information
    :param oRequest: Django HTTP Request
    :return: JSONResponse containing REACT data
    """
    if oRequest.method != 'POST' or not oRequest.POST:
        return Http404()
    # end if
    dReturnData = {}
    sPSMReq = oRequest.POST['psm_req']
    sQuery = ("SELECT [req_id],[assigned_to],[customer_name],[sales_o],"
              "[sales_g],[sold_to_code],[ship_to_code],[bill_to_code],"
              "[pay_terms],[workgroup],[cu],[mus_cnt_num] FROM dbo.ps_requests "
              "WHERE [req_id] = %s AND [Modified_by] IS NULL"
              )
    oCursor = connections['REACT'].cursor()
    oCursor.execute(sQuery, [bytes(sPSMReq, 'ascii')])
    oResults = oCursor.fetchall()

    if oResults:
        oUser = User.objects.filter(email__iexact=oResults[0][1]).first()
 # D-03595-Problem saving new configuration when using REACT data:- Declared the below variable to send the ID of the customer unit so that can be
 #  used in the UI when an existing configuration is opened and saved
        oCustName = REF_CUSTOMER.objects.get(name=oResults[0][10])

        dReturnData.update({
            'req_id': oResults[0][0],
            'person_resp': oUser.first_name + " " + oUser.last_name if
            oUser else '',
            'cust_name': oResults[0][2],
            'sales_office': oResults[0][3],
            'sales_group': oResults[0][4],
            'sold_to': oResults[0][5],
            'ship_to': oResults[0][6],
            'bill_to': oResults[0][7],
            'terms': oResults[0][8].split()[0],
            'workgroup': oResults[0][9],
            'cust': oResults[0][10],
            'contract': oResults[0][11],
 # D-03595-Problem saving new configuration when using REACT data:- Added below attribute to send the ID of the customer unit so that can be
 # used in the UI when an existing configuration is opened and saved
            'cust_val': oCustName.id
        })
    # end if

    return JsonResponse(data=dReturnData)
# end def


def ListFill(oRequest):
    """
    View used to look up any subclassed object models (REF_PROGRAM,
    REF_PRODUCT_AREA_2, Baseline, etc.) to populate HeaderForm dropdowns
    :param oRequest: Django HTTP Request
    :return: JSONResponse
    """

    # Results are prepended with an "i" to allow client-side javascript to order
    # values as strings instead of as integers
    if oRequest.method == 'POST' and oRequest.POST:
        iParentID = int(oRequest.POST['id'])
        cParentClass = Header._meta.get_field(oRequest.POST['parent']).rel.to
        oParent = cParentClass.objects.get(pk=iParentID)
        # S-06756 : Restricting BOM entry based on logged in user's CU:-- Added below & else block to restrict Person_responsible dropdown based on selected CU
        userculist = []
        userculist = User_Customer.objects.filter(customer_name=oParent)
        ausers = []
        ausers = userculist.values_list('user_id')
        # added for S-05907 Edit drop down option for BoM Entry Header -  Product Area 2(exclude deleted prodarea2)
        if oRequest.POST['child'] == 'program' or oRequest.POST['child'] == 'product_area2' :
            cChildClass = Header._meta.get_field(oRequest.POST['child']).rel.to
            result = OrderedDict(
                [('i' + str(obj.id), obj.name) for obj in
                 cChildClass.objects.filter(parent=oParent).order_by('name').exclude(is_inactive=1)]
            )

        elif oRequest.POST['child'] == 'baseline_impacted':
            cChildClass = Baseline
            result = OrderedDict(
                [('i' + obj.title, obj.title) for obj in
                 cChildClass.objects.filter(customer=oParent).order_by('title').exclude(isdeleted=1)]
            )
        else:
            cChildClass = User
            result = OrderedDict(
                [('i' + str(obj.first_name + ' ' + obj.last_name), obj.first_name + ' ' + obj.last_name) for obj in
                 cChildClass.objects.filter(id__in=ausers)]

            )

        return JsonResponse(result)
    else:
        raise Http404
    # end if
# end def


def ListREACTFill(oRequest):
    """
    View used to determine list of customer names from REACT database based on
    Customer_Unit
    :param oRequest: Django HTTP Request
    :return: JSONResponse containing customer names
    """
    from itertools import chain
    if oRequest.method == 'POST' and oRequest.POST:
        #S-06166-Shift Header page to new reference table: Added below code for CU dependency change
        if(oRequest.POST['name'] == '' and oRequest.POST['sold_to'] == '' and oRequest.POST['contract_number'] == ''):
            iParentID = int(oRequest.POST['id'])
            cParentClass = Header._meta.get_field(oRequest.POST['parent']).rel.to
            oParent = cParentClass.objects.get(pk=iParentID)
        # S-06166-Shift Header page to new reference table: Added below code for CN dependency change
        if(oRequest.POST['id'] == '' and oRequest.POST['sold_to'] == '' and oRequest.POST['contract_number'] == ''):
            iParentName = oRequest.POST['name']

        # S-06166-Shift Header page to new reference table: Added below code for sold_to_party dependency change
        if (oRequest.POST['id'] == '' and oRequest.POST['name'] == '' and oRequest.POST['contract_number'] == ''):
            iParentSoldName = oRequest.POST['sold_to']

        # S-06166-Shift Header page to new reference table: Added below code for contract number dependency change
        if (oRequest.POST['id'] == '' and oRequest.POST['name'] == '' and oRequest.POST['sold_to'] == '' ):
            iParentContractName = oRequest.POST['contract_number']

        oCursor = connections['REACT'].cursor()

        # S-06166-Shift Header page to new reference table: Added below code to fetch data from DB based on CU for CN
        if oRequest.POST['child'] == 'customer_name':
            oCursor.execute(
                'SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE '
                '[CustomerUnit]=%s ORDER BY [Customer]',
                [bytes(oParent.name, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
        # S-06166-Shift Header page to new reference table: Added below code to fetch data from DB based on CN for sales group,sales_office,sold_to_party
        elif oRequest.POST['child'] == 'sales_group':
            oCursor.execute(
                'SELECT DISTINCT [sales_g] FROM ps_SalesOffice_SalesGroup WHERE '
                '[sales_cu]=%s ORDER BY [sales_g]',
                [bytes(oParent.name, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
        elif oRequest.POST['child'] == 'sales_office':
            oCursor.execute(
                'SELECT DISTINCT [Sales_o] FROM ps_SalesOffice_SalesGroup WHERE '
                '[sales_cu]=%s ORDER BY [Sales_o]',
                [bytes(oParent.name, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )

        elif oRequest.POST['child'] == 'sold_to_party':
            oCursor.execute(
                'SELECT DISTINCT [SoldTo] FROM ps_fas_contracts WHERE'
                '[Customer]=%s ORDER BY [SoldTo]',
                [bytes(iParentName, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
        # S-06166-Shift Header page to new reference table: Added below code to fetch data from DB based on sold_to for ericsson contract
        elif oRequest.POST['child'] == 'ericsson_contract':
           # S-07112 - Change dropdown selection view and value - Changed the query to fetch the contract no. and description concatenated to show in UI
            oCursor.execute("SELECT DISTINCT ([Contract] + '-' + [Description]) as [contract-desc] FROM [React].[dbo].[ps_fas_contracts] WHERE "
                "[SoldTo]=%s AND (select convert(varchar(10), getdate(),120))>= [ValidFrom] "
                "AND (SELECT convert(varchar(10), getdate(),120))<= [ValidTo]",
                [bytes(iParentSoldName, 'ascii')])
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
       # S-06166-Shift Header page to new reference table: Added below code to fetch data from DB based on ericsson contract for sold_to,payment_terms
        elif oRequest.POST['child'] == 'bill_to_party':
            oCursor.execute(
                'SELECT DISTINCT [BillTo] FROM ps_fas_contracts WHERE'
                '[Contract]=%s ORDER BY [BillTo]',
                [bytes(iParentContractName, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
        elif oRequest.POST['child'] == 'payment_terms':
            oCursor.execute(
                'SELECT DISTINCT [PayTerms] FROM ps_fas_contracts WHERE'
                '[Contract]=%s ORDER BY [PayTerms]',
                [bytes(iParentContractName, 'ascii')]
            )
            tResults = oCursor.fetchall()
            result = OrderedDict(
                [(obj, obj) for obj in chain.from_iterable(tResults)]
            )
        else:
            print('to be added.....')

        return JsonResponse(result)
    else:
        raise Http404
    # end if
# end def


def Clone(oRequest):
    """
    View used to clone Header from BoMEntry view
    :param oRequest: Django HTTP request
    :return: JSONResponse containing details of clone success
    """
    dResult = {
        'status': 0,
        'name': '',
        'errors': []
    }
    oOld = Header.objects.get(id=oRequest.POST.get('header'))
    try:
        oNew = CloneHeader(oOld)
        dResult['name'] = oNew.configuration_designation
        dResult['status'] = 1
    except IntegrityError as ex:
        match = re.search(r"'dbo\.BoMConfig_(.+?)'", str(ex))
        if match:
            if match.group(1).lower() == 'header':
                dResult['errors'].append(
                    'Duplicate Configuration already exists. '
                    '(Ensure that previous clones have been renamed)'
                )
        else:
            dResult['errors'].append('Undetermined database error')
    except Exception as ex:
        dResult['errors'].append(str(ex))

    return JsonResponse(dResult)

# end def


def AjaxValidator(oRequest):
    """
    View used in configuration view to validate each cell immediately after it
    is changed.
    :param oRequest: Django HTTP request object
    :return: JSONResponse containing any errors and/or field updates triggered
    by validation
    """
    if oRequest.method == "POST" and oRequest.POST:
        dData = oRequest.POST
        if 'existing' in oRequest.session:
            oHead = Header.objects.get(pk=oRequest.session['existing'])
        else:
            oHead = Header.objects.get(pk=oRequest.GET.get('id'))
        bCanWriteConfig = oRequest.POST.get('writeable', False)

        dResult = {
            'row': int(dData['row']),
            'col': int(dData['col']),
            'value': dData['value'],
            'status': 'OK',
            'error': {
                'value': None
            },
            'propagate': {
                'line': {

                }
            }
        }

        # Determine appropriate validation function based on column number
        if int(dData['col']) == 1:
            validate_func = ValidateLineNumber
            args = [dData, dResult]
        elif int(dData['col']) == 2:
            validate_func = ValidatePartNumber
            args = [dData, dResult, oHead, bCanWriteConfig]
        elif int(dData['col']) == 3:
            validate_func = ValidateDescription
            args = [dData, dResult]
        elif int(dData['col']) == 4:
            validate_func = ValidateQuantity
            args = [dData, dResult]
        elif int(dData['col']) == 5:
            validate_func = Placeholder
            args = [dData, dResult]
        elif int(dData['col']) == 6:
            validate_func = ValidateContextID
            args = [dData, dResult]
        elif int(dData['col']) == 7:
            validate_func = ValidatePlant
            args = [dData, dResult]
        elif int(dData['col']) == 8:
            validate_func = ValidateSLOC
            args = [dData, dResult]
        elif int(dData['col']) == 9:
            validate_func = ValidateItemCategory
            args = [dData, dResult]
        # elif int(dData['col']) == 10:
        #     validate_func = ValidatePCode
        #     args = [dData, dResult]
        elif int(dData['col']) == 11:
            validate_func = ValidateCommodityType
            args = [dData, dResult]
        elif int(dData['col']) == 12:
            validate_func = ValidatePackageType
            args = [dData, dResult]
        elif int(dData['col']) == 13:
            validate_func = ValidateSPUD
            args = [dData, dResult]
# S-08474:Pull BCAMDB on Part addition/validation : Added below to validate the portfolio code column
        elif int(dData['col']) == 14:
            validate_func = ValidateCurrentPortfolioCode
            args = [dData, dResult]
        # elif int(dData['col']) == 15:
        #     validate_func = ValidateRECode
        #     args = [dData, dResult]
        elif int(dData['col']) == 16:
            validate_func = ValidateMUFlag
            args = [dData, dResult]
        # elif int(dData['col']) == 17:
        #     validate_func = ValidateXPlant
        #     args = [dData, dResult]
  # S-08474:Pull BCAMDB on Part addition/validation : Added below to validate the Plant Specific Material Status column
        elif int(dData['col']) == 18:
            validate_func = ValidatePlantSpecificMaterialStatus
            args = [dData, dResult]
  # S-08474:Pull BCAMDB on Part addition/validation : Added below to validate the Distribution Chain Specific Material Status
        elif int(dData['col']) == 19:
            validate_func = ValidateDistributionChainSpecificMaterialStatus
            args = [dData, dResult]
        elif int(dData['col']) == 20:
            validate_func = Placeholder
            args = [dData, dResult]
    #S-05768: Rename Unit price to Net price and Add unit price
        elif int(dData['col']) == 21:
            validate_func = ValidateUnitPrice
            args = [dData, dResult, oHead]
        elif int(dData['col']) == 22:
            validate_func = ValidateUnitPrice
            args = [dData, dResult, oHead]
        elif int(dData['col']) == 23:
            validate_func = ValidateHigherLevel
            args = [dData, dResult]
        elif int(dData['col']) == 24:
            validate_func = ValidateMaterialGroup
            args = [dData, dResult]
        elif int(dData['col']) == 25:
            validate_func = ValidatePurchaseOrderItemNumber
            args = [dData, dResult]
        elif int(dData['col']) == 26:
            validate_func = ValidateCondition
            args = [dData, dResult, oHead]
        elif int(dData['col']) == 27:
            validate_func = ValidateAmount
            args = [dData, dResult]
        elif int(dData['col']) == 28:
            validate_func = ValidateTraceability
            args = [dData, dResult]
        elif int(dData['col']) == 29:
            validate_func = ValidateCustomerAsset
            args = [dData, dResult, oHead, bCanWriteConfig]
        elif int(dData['col']) == 30:
            validate_func = ValidateAssetTagging
            args = [dData, dResult, oHead, bCanWriteConfig]
        elif int(dData['col']) == 31:
            validate_func = ValidateCustomerNumber
            args = [dData, dResult, oHead, bCanWriteConfig]
        elif int(dData['col']) == 32:
            validate_func = ValidateSecCustomerNumber
            args = [dData, dResult, oHead, bCanWriteConfig]
        elif int(dData['col']) == 33:
            validate_func = ValidateVendorNumber
            args = [dData, dResult]
        elif int(dData['col']) == 34:
            validate_func = Placeholder
            args = [dData, dResult]
        elif int(dData['col']) == 35:
            validate_func = Placeholder
            args = [dData, dResult]
        else:
            validate_func = Placeholder
            args = [dData, dResult]
        # end if

        # Run validation function
        validate_func(*args)

        return JsonResponse(dResult)
    # end if
# end def


def Placeholder(dData, dResult):
    """
    Placeholder validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """
    return dResult
# end def


def ValidateLineNumber(dData, dResult):
    """
    Function to validate line number
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidatePartNumber(dData, dResult, oHead, bCanWriteConfig):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :param bCanWriteConfig: Boolean indicating whether user has write permission
    on the configuration being validated
    :return: dictionary
    """

    oCursor = connections['BCAMDB'].cursor()

# S-08474:Pull BCAMDB on Part addition/validation : Changed the query to fetch the values for 3 new columns on adding part number
    oCursor.execute(
        """
        SELECT TOP 1 T1.[Material Description],T1.[MU-Flag], T1.[X-Plant Status]+','+ REFSTATUS.[Description] xplantdesc,T1.[Base Unit of Measure],
        AP.[Description],T1.[MTyp],T1.[ZMVKE Item Category],T2.[PRIM RE Code]+','+RE.[Description] ErrorDescription,
        T2.[PRIM Traceability],AP.[Commodity],RE.[Title],BPS.[Current Portfolio Code],ZM.MS,ZV.[Material Status] FROM dbo.BI_MM_ALL_DATA T1
        LEFT JOIN dbo.SAP_ZQR_GMDM T2
        ON T2.[Material Number]=T1.Material 
        LEFT JOIN dbo.REF_PCODE_FCODE AP
        ON T1.[P Code]=AP.[PCODE ]
        LEFT JOIN dbo.REF_PRODUCT_STATUS_CODES RE 
        ON T2.[PRIM RE Code]=RE.[Status Code] 
        LEFT JOIN dbo.REF_X_PLANT_STATUS_DESCRIPTIONS REFSTATUS 
        ON T1.[X-Plant Status]=REFSTATUS.[X-Plant Status Code] 
        LEFT JOIN dbo.BI_MATERIAL_PLANT_SUMMARY BPS
        ON T1.[Material]=BPS.Material and T1.Plant=BPS.Plant 
        LEFT JOIN dbo.SAP_ZMARC ZM
        ON T1.[Material] =ZM.Material and T1.Plant=ZM.Plant 
        LEFT JOIN dbo.SAP_ZMVKE ZV
        ON T1.[Material] =ZV.Material and T1.Plant=ZV.Plant
        WHERE [ZMVKE Item Category]<>'NORM' and T1.Material = %s and T1.[Plant] IN ('2685','2666','2392')
        """
        ,
        [bytes(dResult['value'].strip('.'), 'ascii')])

    tAllDataInfo = oCursor.fetchall()

    if tAllDataInfo:
        if StrToBool(dData['allowChain']):
            dResult['propagate']['line'][3] = {
                'value': tAllDataInfo[0][0], 'chain': True}
            dResult['propagate']['line'][5] = {
                'value': tAllDataInfo[0][3], 'chain': False}
            dResult['propagate']['line'][9] = {
                'value': tAllDataInfo[0][6], 'chain': True}
            dResult['propagate']['line'][10] = {
                'value': tAllDataInfo[0][4], 'chain': True}
            dResult['propagate']['line'][14] = {
                'value': tAllDataInfo[0][1], 'chain': True}
            dResult['propagate']['line'][16] = {
                'value': tAllDataInfo[0][1], 'chain': True}
            dResult['propagate']['line'][17] = {
                'value': tAllDataInfo[0][2], 'chain': True}
            dResult['propagate']['line'][11] = {
                'value': tAllDataInfo[0][9], 'chain': True}
            dResult['propagate']['line'][20] = {
                'value': tAllDataInfo[0][10], 'chain': True}

            dResult['propagate']['line'][14] = {
                'value': tAllDataInfo[0][11], 'chain': True}
            dResult['propagate']['line'][18] = {
                'value': tAllDataInfo[0][12], 'chain': True}
            dResult['propagate']['line'][19] = {
                'value': tAllDataInfo[0][13], 'chain': True}

            dResult['propagate']['line'][15] = {
                'value': tAllDataInfo[0][7],  'chain': True}
            dResult['propagate']['line'][28] = {
                'value': 'Y' if tAllDataInfo[0][8] == 'Z001' else 'N' if
                tAllDataInfo[0][8] == 'Z002' else '',
                'chain': True
            }

            if tAllDataInfo[0][6] == 'ZF26':
                dResult['propagate']['line'][12] = {
                    'value': 'Fixed Product Package (FPP)',
                    'chain': False
                }
            elif tAllDataInfo[0][5] == 'ZASO':
                dResult['propagate']['line'][12] = {
                    'value': 'Assembled Sales Object (ASO)',
                    'chain': False
                }
            elif tAllDataInfo[0][5] == 'ZAVA':
                dResult['propagate']['line'][12] = {
                    'value': 'Material Variant (MV)',
                    'chain': False
                }
            elif tAllDataInfo[0][5] == 'ZEDY':
                dResult['propagate']['line'][12] = {
                    'value': 'Dynamic Product Package (DPP)',
                    'chain': False
                }

            if 'context_id' in dData.keys():
                dResult['propagate']['line'][6] = {
                    'value': dData['context_id'],
                    'chain': True
                }

    else:
        oCursor.close()
        dResult['error']['value'] = '! - Product Number not found.\n'
        dResult['status'] = '!'
        return

    if oHead.configuration_status.name == 'In Process':

        try:
            oMPNCustMap = CustomerPartInfo.objects.get(
                part__product_number=dResult['value'].strip('.'),
                customer=oHead.customer_unit,
                active=True)

            # if StrToBool(dData['allowChain']):
            dResult['propagate']['line'][29] = {
                'value': 'Y' if oMPNCustMap.customer_asset else 'N' if
                oMPNCustMap.customer_asset is False else '',
                'chain': True
            }
            dResult['propagate']['line'][30] = {
                'value': 'Y' if oMPNCustMap.customer_asset_tagging else 'N'
                if oMPNCustMap.customer_asset_tagging is False else '',
                'chain': True
            }
            dResult['propagate']['line'][31] = {
                'value': oMPNCustMap.customer_number,
                'chain': True
            }
            dResult['propagate']['line'][32] = {
                'value': oMPNCustMap.second_customer_number,
                'chain': True
            }
        except CustomerPartInfo.DoesNotExist:
            dResult['propagate']['line'][29] = {
                'value': None,
                'chain': True}
            dResult['propagate']['line'][30] = {
                'value': None,
                'chain': True}
            dResult['propagate']['line'][31] = {
                'value': None,
                'chain': True}
            dResult['propagate']['line'][32] = {
                'value': None,
                'chain': True}
# end def


def ValidateDescription(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateQuantity(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateContextID(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidatePlant(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    if dData['value'] != '':
        oCursor = connections['BCAMDB'].cursor()

        oCursor.execute(
            'SELECT DISTINCT [Plant] FROM dbo.REF_PLANTS WHERE [Plant]=%s',
            [bytes(dData['value'], 'ascii')]
        )
        tPlants = oCursor.fetchall()

        if not tPlants:
            oCursor.close()
            dResult['error']['value'] = "! - Plant not found in REF_PLANTS.\n"
            dResult['status'] = "!"
            return
    # 27/03: to remove the . from LHS of the part number so that part no. having . in the RHS would be considered a valid one.
        oCursor.execute(
            'SELECT [Plant] FROM dbo.SAP_ZQR_GMDM WHERE [Material Number]=%s',
            [bytes(dData['part_number'].lstrip('. '), 'ascii')])
        tResults = oCursor.fetchall()
        oCursor.close()
        if (dData['value'],) not in tResults:
            dResult['error']['value'] = '! - Plant not found for material in SAP_ZQR_GMDM.\n'
            dResult['status'] = '!'
            # end if
# end def


def ValidateSLOC(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    oCursor = connections['BCAMDB'].cursor()

    oCursor.execute(
        'SELECT DISTINCT [SLOC] FROM dbo.REF_PLANT_SLOC WHERE [SLOC]=%s',
        [bytes(dData['value'], 'ascii')]
    )
    tSLOCs = oCursor.fetchall()

    if not tSLOCs:
        oCursor.close()
        dResult['error']['value'] = "! - SLOC not found in REF_PLANT_SLOC.\n"
        dResult['status'] = "!"
        return

    if dData['plant'] not in ('', None):
    # 27/03: query changed , replaced SAP_MB52 with SAP_ZMARD and added SLOC column as a filter .
        oCursor.execute(
            'SELECT [SLoc] FROM dbo.SAP_ZMARD WHERE [Plant]=%s AND [Material]=%s and [SLoc]=%s',
            [bytes(dData['plant'], 'ascii'),
             bytes(dData['part_number'].lstrip('. '), 'ascii'),
             bytes(dData['value'], 'ascii')])
        tResults = oCursor.fetchall()
        oCursor.close()
        if not tResults:
    # 27/03: For SLOC validation we are refering to SAP_ZMARD instead of SAP_MB52
            dResult['error']['value'] = \
                '! - Plant/SLOC combination not found in SAP_ZMARD for material.\n'
            dResult['status'] = '!'
            # end if
    else:
        oCursor.close()
# end def


def ValidateItemCategory(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidatePCode(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    if re.match(r'^\(\d{2,3}-\d{4}\).*$|^\([A-Z]\d{2}-\d{4}\).*$',
                dResult['value'], re.I):
        sPCode = re.match(r'^\((?P<pcode>.{2,3})-\d{4}\).*$',
                          dResult['value'], re.I).group('pcode')
    elif re.match(r'^\d{2,3}$|^[A-Z]\d{2}$', dResult['value'], re.I):
        sPCode = dResult['value']
    else:
        dResult['error']['value'] = 'X - Invalid P-Code format.\n'
        dResult['status'] = 'X'
        return

    oCursor = connections['BCAMDB'].cursor()

    oCursor.execute(
        'SELECT [PCODE],[FireCODE],[Description],[Commodity] FROM '
        'dbo.REF_PCODE_FCODE WHERE [PCODE]=%s',
        [bytes(sPCode, 'ascii')])
    tPCode = oCursor.fetchall()
    oCursor.close()

    if tPCode:
        dResult['value'] = str(tPCode[0][2]).upper()
        if StrToBool(dData['allowChain']):
            dResult['propagate']['line'][11] = {'value': tPCode[0][3],
                                                'chain': True}
    else:
        dResult['error']['value'] = 'X - P-Code not found.\n'
        dResult['status'] = 'X'
        return
    # end if

# end def


def ValidateCommodityType(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidatePackageType(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateSPUD(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def

# S-08474:Pull BCAMDB on Part addition/validation : Added below function to validate the portfolio code column
def ValidateCurrentPortfolioCode(dData, dResult):
    """
    Function to validate line number
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def

def ValidateRECode(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    oCursor = connections['BCAMDB'].cursor()
    oCursor.execute(
            'SELECT DISTINCT [Title],[Description] FROM '
            'dbo.REF_PRODUCT_STATUS_CODES WHERE [Status Code]=%s',
            [bytes(dResult['value'], 'ascii')])
    tRECode = oCursor.fetchall()
    oCursor.close()
    if tRECode:
        if dData['int_notes'] and tRECode[0][0] not in dData['int_notes']:
                sNote = dData['int_notes'] + '; ' + tRECode[0][0]
        else:
            sNote = tRECode[0][0]

        if StrToBool(dData['allowChain']):
            dResult['propagate']['line'][20] = {'value': sNote,
                                                'chain': False}
        dResult['error']['value'] = tRECode[0][1] + '\n'
        dResult['status'] = 'OK'
    # end if
# end def


def ValidateMUFlag(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateXPlant(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    oCursor = connections['BCAMDB'].cursor()

    oCursor.execute(
        'SELECT [Description] FROM dbo.[REF_X_PLANT_STATUS_DESCRIPTIONS] '
        'WHERE [X-Plant Status Code]=%s',
        [bytes(dResult['value'], 'ascii')])
    tXPlant = oCursor.fetchall()
    oCursor.close()

    if tXPlant:
        dResult['error']['value'] = tXPlant[0][0] + '\n'
        dResult['status'] = 'OK'
    # end if
# end def

# S-08474:Pull BCAMDB on Part addition/validation : Added below to validate the Plant Specific Material Status column
def ValidatePlantSpecificMaterialStatus(dData, dResult):
    """
    Function to validate line number
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def

# S-08474:Pull BCAMDB on Part addition/validation : Added below to validate the Distribution Chain Specific Material Status column
def ValidateDistributionChainSpecificMaterialStatus(dData, dResult):
    """
    Function to validate line number
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def

def ValidateUnitPrice(dData, dResult, oHead):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :return: dictionary
    """

    if dResult['value'] not in ('', None):
        # S-08411:Adjust Configuration UI & Backend to include Line Numbering scheme:- Added below if else block to set the line #
        # in a variable and use the same in comparing the dData below; functionality not discovered yet!
        if not oHead.line_100:
            linenum = '10'
        else:
            linenum = '100'
        if dData['line_number'] == linenum and not oHead.pick_list:
            if str(oHead.configuration.override_net_value) == dResult['value']:
                dResult['error']['value'] = 'CPM override in effect.\n'
                dResult['status'] = 'OK'
        else:
            if oHead.configuration.configline_set.filter(
                    line_number=dData['line_number']):
                if str(GrabValue(oHead.configuration.configline_set.get(
                        line_number=dData['line_number']),
                        'linepricing.override_price')) == dResult['value']:
                    dResult['error']['value'] = 'CPM override in effect.\n'
                    dResult['status'] = 'OK'
    if StrToBool(dData['allowChain']):
        dResult['propagate']['total_value'] = str(
            oHead.configuration.total_value)
# end def


def ValidateHigherLevel(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateMaterialGroup(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidatePurchaseOrderItemNumber(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateCondition(dData, dResult, oHead):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :return: dictionary
    """

    return
# end def


def ValidateAmount(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return ''
# end def


def ValidateTraceability(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def


def ValidateCustomerAsset(dData, dResult, oHead, bCanWriteConfig):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :param bCanWriteConfig: Boolean indicating whether user has write permission
    on the configuration being validated
    :return: dictionary
    """

    return
# end def


def ValidateAssetTagging(dData, dResult, oHead, bCanWriteConfig):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :param bCanWriteConfig: Boolean indicating whether user has write permission
    on the configuration being validated
    :return: dictionary
    """

    return
# end def


def ValidateCustomerNumber(dData, dResult, oHead, bCanWriteConfig):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :param bCanWriteConfig: Boolean indicating whether user has write permission
    on the configuration being validated
    :return: dictionary
    """

    return
# end def


def ValidateSecCustomerNumber(dData, dResult, oHead, bCanWriteConfig):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :param oHead: Header object being validated
    :param bCanWriteConfig: Boolean indicating whether user has write permission
    on the configuration being validated
    :return: dictionary
    """

    return
# end def


def ValidateVendorNumber(dData, dResult):
    """
    Field validation function.
    :param dData: Dictionary of input data
    :param dResult: Dictionary of output data
    :return: dictionary
    """

    return
# end def
