from django.shortcuts import redirect
from django.http import HttpResponse, QueryDict, JsonResponse, Http404
from django.core.urlresolvers import reverse
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.db import connections, IntegrityError
from django import forms
from django.forms import fields
from django.contrib.auth.models import User
from django.utils import timezone

from BoMConfig.models import Header, Part, Configuration, ConfigLine,\
    PartBase, Baseline, Baseline_Revision, LinePricing, REF_CUSTOMER, HeaderLock, SecurityPermission,\
    REF_PRODUCT_AREA_2, REF_PROGRAM, REF_CONDITION, REF_MATERIAL_GROUP, REF_PRODUCT_PKG, REF_SPUD, REF_STATUS,\
    REF_REQUEST, PricingObject
from BoMConfig.forms import HeaderForm, ConfigForm, DateForm
from BoMConfig.views.landing import Lock, Default, LockException
from BoMConfig.views.approvals_actions import CloneHeader
from BoMConfig.utils import GrabValue, HeaderComparison, RevisionCompare

import copy
# import datetime
from itertools import chain
import json
import re


def UpdateConfigRevisionData(oHeader):
    oPrev = None
    try:
        if oHeader.model_replaced_link:
            oPrev = oHeader.model_replaced_link
        elif oHeader.baseline and oHeader.baseline.previous_revision:
            oPrev = oHeader.baseline.previous_revision.header_set.get(configuration_designation=oHeader.model_replaced or oHeader.configuration_designation,
                                                                      program=oHeader.program)
        else:
            if oHeader.baseline:
                aExistingRevs = sorted(
                    list(set([oBaseRev.version for oBaseRev in
                              oHeader.baseline.baseline.baseline_revision_set.order_by('version')])),
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

    if oPrev:
        sTemp = HeaderComparison(oHeader, oPrev)
        oHeader.change_notes = sTemp
        oHeader.save()
    # end if
# end def


def AddHeader(oRequest, sTemplate='BoMConfig/entrylanding.html'):
    # existing_instance is the existing header. Store the pk in the form to return for saving
    # Status message allows another view to redirect to here with an error message explaining the redirect

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    iFrameID = oRequest.GET.get('id', None)

    bCanReadHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    if bFrameReadOnly:
        bCanWriteHeader = False
    else:
        bCanWriteHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Write').filter(user__in=oRequest.user.groups.all()))
    bSuccess = False

    # Determine which pages to which the user is able to move forward
    bCanReadConfig = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(title='SAP_Inquiry_Creation_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(title='SAP_ST_Creation_Read').filter(user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadConfig or bCanReadTOC or bCanReadRevision or bCanReadInquiry or bCanReadSiteTemplate

    bDiscontinuationAlreadyCreated = False

    if sTemplate == 'BoMConfig/entrylanding.html':
        return redirect(reverse('bomconfig:configheader'))
    else:
        if bFrameReadOnly:
            oExisting = iFrameID
        else:
            oExisting = oRequest.session.get('existing', None)
        status_message = oRequest.session.get('status', None)

        if status_message:
            del oRequest.session['status']
        # end if

        try:
            if oExisting:
                if not bFrameReadOnly:
                    Lock(oRequest, oExisting)
                oExisting = Header.objects.get(pk=oExisting)
                bDiscontinuationAlreadyCreated = True if oExisting.model_replaced_link and \
                                                         oExisting.model_replaced_link.header_set.filter(
                                                             bom_request_type__name='Discontinue',
                                                             configuration_designation=oExisting.model_replaced_link.configuration_designation
                                                         ) else False
            # end if

            if oRequest.method == 'POST' and oRequest.POST:
                if not oExisting or 'configuration_status' not in oRequest.POST:
                    oModPost = QueryDict(None, mutable=True)
                    oModPost.update(oRequest.POST)
                    oModPost.update({'configuration_status': '1'})
                    headerForm = HeaderForm(oModPost, instance=oExisting, readonly=not bCanWriteHeader)
                else:
                    headerForm = HeaderForm(oRequest.POST, instance=oExisting, readonly=not bCanWriteHeader)
                # end if

                if oRequest.POST['baseline_impacted'] and oRequest.POST['baseline_impacted'] == 'New' and oRequest.POST.get('new_baseline', None):
                    Baseline.objects.get_or_create(title__iexact=oRequest.POST['new_baseline'],
                                                   defaults={'title':oRequest.POST['new_baseline'], 'customer': REF_CUSTOMER.objects.get(id=oRequest.POST['customer_unit'])})
                    headerForm.data._mutable = True
                    headerForm.data['baseline_impacted'] = oRequest.POST['new_baseline']
                    headerForm.data._mutable = False
                # end if

                if headerForm.is_valid():
                    if headerForm.cleaned_data['configuration_status'] == REF_STATUS.objects.get(name='In Process'):
                        try:
                            if bCanWriteHeader:
                                oHeader = headerForm.save(commit=False)
                                oHeader.shipping_condition = '71'
                                if oHeader.bom_request_type.name in ('Update','Discontinue') and not oHeader.model_replaced_link:
                                    if oHeader.baseline:
                                        aExistingRevs = sorted(
                                            list(set([oBaseRev.version for oBaseRev in
                                                      oHeader.baseline.baseline.baseline_revision_set.order_by(
                                                          'version')])),
                                            key=RevisionCompare)
                                    else:
                                        aExistingRevs = [oHeader.baseline_version]

                                    iPrev = aExistingRevs.index(oHeader.baseline_version) - 1
                                    if iPrev >= 0:
                                        try:
                                            oHeader.model_replaced_link = Header.objects.get(
                                                configuration_designation=oHeader.configuration_designation,
                                                program=oHeader.program,
                                                baseline_version=aExistingRevs[iPrev]
                                            )
                                        except Header.DoesNotExist:
                                            pass

                                if not bDiscontinuationAlreadyCreated and \
                                        oHeader.bom_request_type.name in ('New',) and \
                                        oHeader.model_replaced_link:

                                    oDiscontinued = CloneHeader(oHeader.model_replaced_link)
                                    oDiscontinued.bom_request_type = REF_REQUEST.objects.get(name='Discontinue')
                                    oDiscontinued.configuration_designation = oHeader.model_replaced_link.configuration_designation
                                    oDiscontinued.model_replaced = oHeader.model_replaced_link.configuration_designation
                                    oDiscontinued.model_replaced_link = oHeader.model_replaced_link
                                    try:
                                        oDiscontinued.save()
                                        bDiscontinuationAlreadyCreated = True
                                    except Exception as ex:
                                        print(ex)
                                oHeader.save()

                                if not hasattr(oHeader, 'configuration'):
                                    oConfig = Configuration.objects.create(**{'header': oHeader})

                                    (oPartBase,_) = PartBase.objects.get_or_create(**{'product_number':oHeader.configuration_designation})
                                    oPartBase.unit_of_measure = 'PC'
                                    oPartBase.save()
                                    (oPart,_) = Part.objects.get_or_create(**{'base': oPartBase,'product_description':oHeader.model_description})

                                    ConfigLine.objects.create(**{
                                        'config': oConfig,
                                        'part': oPart,
                                        'line_number': '10',
                                        'order_qty': 1,
                                        'vendor_article_number': oHeader.configuration_designation,
                                    })
                                else:
                                    if not oHeader.pick_list and oHeader.configuration.get_first_line().part.base.product_number != oHeader.configuration_designation:
                                        # Update line 10 Product number to match configuration designation
                                        (oPartBase,_) = PartBase.objects.get_or_create(**{'product_number':oHeader.configuration_designation})
                                        oPartBase.unit_of_measure = 'PC'
                                        oPartBase.save()
                                        (oPart,_) = Part.objects.get_or_create(**{'base': oPartBase,'product_description':oHeader.model_description})
                                        oFirstLine = oHeader.configuration.get_first_line()
                                        oFirstLine.part = oPart
                                        oFirstLine.vendor_article_number = oHeader.configuration_designation
                                        oFirstLine.save()
                                # end if

                                if not hasattr(oHeader, 'headerlock'):
                                    HeaderLock.objects.create(**{
                                        'header': oHeader,
                                        'session_key': Session.objects.get(session_key=oRequest.session.session_key)
                                    })
                                # end if

                                status_message = oRequest.session['status'] = 'Form data saved'
                            else:
                                oHeader = oExisting
                                status_message = None
                            #end if


                            bSuccess = True
                        except IntegrityError as ex:
                            status_message = 'Configuration already exists in Baseline'
                        # end try
                    else:
                        oHeader = oExisting
                        bSuccess = True
                    # end if

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

                            return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
                        # end if
                    # end if
                else:
                    status_message = 'Error(s) occurred'
                # end if
                headerForm.fields['product_area2'].queryset = REF_PRODUCT_AREA_2.objects.filter(parent=(headerForm.cleaned_data['product_area1'] if headerForm.cleaned_data.get('product_area1', None) else None))
                headerForm.fields['program'].queryset = REF_PROGRAM.objects.filter(parent=(headerForm.cleaned_data['customer_unit'] if headerForm.cleaned_data.get('customer_unit', None) else None))
            else:
                headerForm = HeaderForm(instance=oExisting, readonly=not bCanWriteHeader)
                headerForm.fields['product_area2'].queryset = REF_PRODUCT_AREA_2.objects.filter(parent=(oExisting.product_area1 if oExisting else None))
                headerForm.fields['program'].queryset = REF_PROGRAM.objects.filter(parent=(oExisting.customer_unit if oExisting else None))
            # end if
        except LockException:
            headerForm = HeaderForm(readonly=not bCanWriteHeader)
            status_message = 'File is locked for editing'
            if 'existing' in oRequest.session:
                del oRequest.session['existing']
            #end if
        # end try

        # Make 'Person Responsible' field a dropdown of PSM users
        if not oExisting:
            headerForm.fields['person_responsible'] = fields.ChoiceField(choices=[('', '---------')] + list(
                [(user.first_name + ' ' + user.last_name, user.first_name + ' ' + user.last_name) for user in User.objects.all() if\
                        user.groups.filter(name__in=['BOM_PSM_Baseline_Manager','BOM_PSM_Product_Supply_Manager'])]
            ))

        if not bFrameReadOnly and (not oExisting or (oExisting and type(oExisting) != str and oExisting.configuration_status.name == 'In Process')):
            headerForm.fields['baseline_impacted'].widget = forms.widgets.Select(choices=(('','---------'),('New','Create New baseline')) + tuple((obj.title,obj.title) for obj in Baseline_Revision.objects.filter(baseline__customer=oExisting.customer_unit if oExisting else None).filter(completed_date=None)))

            oCursor = connections['REACT'].cursor()
            oCursor.execute('SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE [CustomerUnit]=%s',[oExisting.customer_unit.name if oExisting else None])
            tResults = oCursor.fetchall()
            headerForm.fields['customer_name'].widget = forms.widgets.Select(choices=(('','---------'),) + tuple((obj,obj) for obj in chain.from_iterable(tResults)))

        dContext={
            'header': oExisting,
            'headerForm': headerForm,
            'break_list': ('Payment Terms', 'Shipping Condition', 'Initial Version', 'Configuration/Ordering Status', 'Name'),
            'status_message': status_message,
            'header_write_authorized': bCanWriteHeader,
            'header_read_authorized': bCanReadHeader,
            'can_continue': bCanMoveForward,
            'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else 'BoMConfig/template.html',
            'frame_readonly': bFrameReadOnly,
            'non_clonable': ['In Process', 'In Process/Pending'],
            'discontinuation_done': int(bDiscontinuationAlreadyCreated)
        }

        return Default(oRequest, sTemplate, dContext)
# end def


def AddConfig(oRequest):
    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    bCanReadConfigBOM = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfigSAP = bool(SecurityPermission.objects.filter(title='Config_Entry_SAPDoc_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfigAttr = bool(SecurityPermission.objects.filter(title='Config_Entry_Attributes_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfigPrice = bool(SecurityPermission.objects.filter(title='Config_Entry_PriceLinks_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfigCust = bool(SecurityPermission.objects.filter(title='Config_Entry_CustomerData_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfigBaseline = bool(SecurityPermission.objects.filter(title='Config_Entry_Baseline_Read').filter(user__in=oRequest.user.groups.all()))

    if bFrameReadOnly:
        bCanWriteConfigBOM = bCanWriteConfigSAP = bCanWriteConfigAttr = bCanWriteConfigPrice = bCanWriteConfigCust = bCanWriteConfigBaseline = False
    else:
        bCanWriteConfigBOM = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Write').filter(user__in=oRequest.user.groups.all()))
        bCanWriteConfigSAP = bool(SecurityPermission.objects.filter(title='Config_Entry_SAPDoc_Write').filter(user__in=oRequest.user.groups.all()))
        bCanWriteConfigAttr = bool(SecurityPermission.objects.filter(title='Config_Entry_Attributes_Write').filter(user__in=oRequest.user.groups.all()))
        bCanWriteConfigPrice = bool(SecurityPermission.objects.filter(title='Config_Entry_PriceLinks_Write').filter(user__in=oRequest.user.groups.all()))
        bCanWriteConfigCust = bool(SecurityPermission.objects.filter(title='Config_Entry_CustomerData_Write').filter(user__in=oRequest.user.groups.all()))
        bCanWriteConfigBaseline = bool(SecurityPermission.objects.filter(title='Config_Entry_Baseline_Write').filter(user__in=oRequest.user.groups.all()))

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(title='SAP_Inquiry_Creation_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(title='SAP_ST_Creation_Read').filter(user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadTOC or bCanReadRevision or bCanReadInquiry or bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader

    bCanReadConfig = bCanReadConfigBOM or bCanReadConfigSAP or bCanReadConfigAttr or bCanReadConfigPrice or bCanReadConfigCust or bCanReadConfigBaseline
    bCanWriteConfig = bCanWriteConfigBOM or bCanWriteConfigSAP or bCanWriteConfigAttr or bCanWriteConfigPrice or bCanWriteConfigCust or bCanWriteConfigBaseline

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

    if oRequest.method == 'POST' and oRequest.POST:
        configForm = ConfigForm(oRequest.POST, instance=oHeader.configuration if oHeader and hasattr(oHeader, 'configuration') else None)
        if configForm.is_valid():
            if bCanWriteConfig:
                oConfig = configForm.save(commit=False)
                if not hasattr(oHeader, 'configuration'):
                    oConfig.header = oHeader
                # end if
                oConfig.save()

                if oHeader.configuration_status.name == 'In Process':
                    oForm = json.loads(oRequest.POST['data_form'])
                    # Clean empty rows out and remove previous row statuses
                    for index in range(len(oForm) - 1, -1, -1):
                        # Convert to dict for uniformity
                        if type(oForm[index]) == list:
                            oForm[index] = {str(x):y for (x,y) in enumerate(oForm[index])}

                        if '0' in oForm[index]:
                            del oForm[index]['0']

                        if all(x in (None, '') for x in list(oForm[index].values())) or len(oForm[index]) < 1:
                            del oForm[index]
                            continue
                        else:
                            for x in range(31):
                                if str(x) not in oForm[index]:
                                    oForm[index][str(x)] = None
                            # end for
                        # end if
                    # end for

                    aExistingConfigLines = list(ConfigLine.objects.filter(config=oConfig))
                    oUpdateDate = timezone.now()

                    for dConfigLine in oForm:
                        dBaseData = {'product_number': dConfigLine['2'].strip('. '), 'unit_of_measure': dConfigLine['5']}

                        (oBase, _) = PartBase.objects.get_or_create(product_number=dConfigLine['2'].strip('. '))
                        PartBase.objects.filter(pk=oBase.pk).update(**dBaseData)

                        dPartData = {'product_description': dConfigLine['3'].strip().upper() if dConfigLine['3'] else dConfigLine['3'], 'base': oBase}

                        oNullQuery = Q(product_description__isnull=True)
                        oNoneQuery = Q(product_description='None')
                        oBlankQuery = Q(product_description='')
                        if Part.objects.filter(base=oBase).filter(oNoneQuery | oNullQuery | oBlankQuery) and not Part.objects.filter(**dPartData):
                            iPartPk = Part.objects.filter(base=oBase).filter(oNoneQuery | oNullQuery | oBlankQuery)[0].pk
                            Part.objects.filter(pk=iPartPk).update(**dPartData)
                            oPart = Part.objects.get(pk=iPartPk)
                        else:
                            (oPart, _) = Part.objects.get_or_create(**dPartData)

                        dLineData = {'line_number': dConfigLine['1'], 'order_qty': dConfigLine['4'] or None, 'spud': dConfigLine['12'],
                                     'plant': dConfigLine['6'], 'sloc': dConfigLine['7'], 'item_category': dConfigLine['8'],
                                     'internal_notes': dConfigLine['16'],# 'unit_price': dConfigLine['17'],
                                     'higher_level_item': dConfigLine['18'], 'material_group_5': dConfigLine['19'],
                                     'purchase_order_item_num': dConfigLine['20'], 'condition_type': dConfigLine['21'],
                                     'amount': dConfigLine['22'] or None, 'customer_asset': dConfigLine['24'],
                                     'customer_asset_tagging': dConfigLine['25'], 'customer_number': dConfigLine['26'],
                                     'sec_customer_number': dConfigLine['27'], 'vendor_article_number': dConfigLine['28'],
                                     'comments': dConfigLine['29'], 'additional_ref': dConfigLine['30'], 'config': oConfig,
                                     'part': oPart, 'is_child': bool(dConfigLine['2'].startswith('.') and not dConfigLine['2'].startswith('..')),
                                     'is_grandchild': bool(dConfigLine['2'].startswith('..')),
                                     'pcode': dConfigLine['9'], 'commodity_type': dConfigLine['10'], 'REcode': dConfigLine['13'],
                                     'package_type': dConfigLine['11'], 'mu_flag': dConfigLine['14'], 'x_plant': dConfigLine['15'],
                                     'traceability_req': dConfigLine['23'], 'last_updated': oUpdateDate}

                        if ConfigLine.objects.filter(config=oConfig).filter(line_number=dConfigLine['1']):
                            oConfigLine = ConfigLine.objects.get(**{'config': oConfig, 'line_number': dConfigLine['1']})
                            # oConfigLine = ConfigLine.objects.filter(config=oConfig).filter(line_number=dConfigLine['1'])[0].pk
                            # ConfigLine.objects.filter(pk=oConfigLine).update(**dLineData)
                            ConfigLine.objects.filter(pk=oConfigLine.pk).update(**dLineData)
                        else:
                            oConfigLine = ConfigLine(**dLineData)
                            oConfigLine.save()
                        # end if

                        # dPriceData = {'unit_price': dConfigLine['17'] or None, 'config_line': oConfigLine}
                        dPriceData = {'config_line': oConfigLine}
                        (oPrice, _) = LinePricing.objects.get_or_create(**dPriceData)
                        oPriceObj = None
                        try:
                            if oConfigLine.spud:
                                oPriceObj = PricingObject.objects.get(
                                    part=oConfigLine.part.base,
                                    customer=oConfigLine.config.header.customer_unit,
                                    sold_to=oConfigLine.config.header.sold_to_party,
                                    spud=REF_SPUD.objects.get(name=oConfigLine.spud),
                                    is_current_active=True
                                )
                            else:
                                oPriceObj = PricingObject.objects.get(
                                    part=oConfigLine.part.base,
                                    customer=oConfigLine.config.header.customer_unit,
                                    sold_to=oConfigLine.config.header.sold_to_party,
                                    spud=None,
                                    is_current_active=True
                                )
                        except PricingObject.DoesNotExist:
                            try:
                                oPriceObj = PricingObject.objects.get(
                                    part=oConfigLine.part.base,
                                    customer=oConfigLine.config.header.customer_unit,
                                    sold_to=None,
                                    spud=None,
                                    is_current_active=True
                                )
                            except PricingObject.DoesNotExist:
                                pass
                        oPrice.pricing_object = oPriceObj
                        oPrice.save()

                    # end for

                    for oOldLine in ConfigLine.objects.filter(config=oConfig):
                        if oOldLine.last_updated != oUpdateDate:
                            oOldLine.delete()
                    status_message = oRequest.session['status'] = 'Form data saved'
                # end if
            #end if
            if oRequest.POST['formaction'] == 'prev':
                if not bFrameReadOnly:
                    UpdateConfigRevisionData(oHeader)
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:config'
                if bCanReadHeader:
                    sDestination = 'bomconfig:configheader'
                # end if

                return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
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

                return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
            # end if
        else:
            status_message = configForm.errors['__all__'].as_text()
        # end if
    else:
        configForm = ConfigForm(instance=oHeader.configuration if oHeader and hasattr(oHeader, 'configuration') else None,)
    # end if

    data = BuildDataArray(oHeader, config=True)

    dContext = {
        'data_array': data,
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
        'material_group_list': [obj.name for obj in REF_MATERIAL_GROUP.objects.all()],
        'product_pkg_list': [obj.name for obj in REF_PRODUCT_PKG.objects.all()],
        'spud_list': [obj.name for obj in REF_SPUD.objects.all()],
        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }
    return Default(oRequest, sTemplate='BoMConfig/configuration.html', dContext=dContext)
# end def


def AddTOC(oRequest):
    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    bCanReadTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))

    if bFrameReadOnly:
        bCanWriteTOC = False
    else:
        bCanWriteTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Write').filter(user__in=oRequest.user.groups.all()))

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(title='SAP_Inquiry_Creation_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(title='SAP_ST_Creation_Read').filter(user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadRevision or bCanReadInquiry or bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader or bCanReadConfig

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
        configForm = ConfigForm(oRequest.POST, instance=oHeader.configuration if oHeader and hasattr(oHeader, 'configuration') else None)
        if configForm.is_valid():
            if bCanWriteTOC:
                oConfig = configForm.save(commit=False)
                if not hasattr(oHeader, 'configuration'):
                    oConfig.header = oHeader
                # end if
                oConfig.save()

                if oHeader.configuration_status.name == 'In Process':
                    oForm = json.loads(oRequest.POST['data_form'])
                    if type(oForm[0]) == list:
                        oForm[0] = {str(x):y for (x,y) in enumerate(oForm[0])}

                    if '1' in oForm[0] and oForm[0]['1'] not in ('', None):
                        oHeader.customer_designation = oForm[0]['1']
                    if '13' in oForm[0] and oForm[0]['13'] not in ('', None):
                        oHeader.internal_notes = oForm[0]['13']
                    if '14' in oForm[0] and oForm[0]['14'] not in ('', None):
                        oHeader.external_notes = oForm[0]['14']

                    oHeader.save()
                    status_message = oRequest.session['status'] = 'Form data saved'
                # end if
            # end if

            if oRequest.POST['formaction'] == 'prev':
                if not bFrameReadOnly:
                    oRequest.session['existing'] = oHeader.pk
                sDestination = 'bomconfig:configtoc'
                if bCanReadConfig:
                    sDestination = 'bomconfig:config'
                elif bCanReadHeader:
                    sDestination = 'bomconfig:configheader'
                # end if

                return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
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

                return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
            # end if
        # end if
    else:
        configForm = ConfigForm(instance=oHeader.configuration if oHeader and hasattr(oHeader, 'configuration') else None,
                                initial={'net_value': getattr(oHeader.configuration,'net_value') if hasattr(oHeader, 'configuration') else '0',
                                         'zpru_total': getattr(oHeader.configuration,'zpru_total') if hasattr(oHeader, 'configuration') else '0'})
    # end if

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
        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }
    return Default(oRequest, sTemplate='BoMConfig/configtoc.html', dContext=dContext)
# end def


def AddRevision(oRequest):
    error_matrix = []
    valid = True
    oForm = None

    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    bCanReadRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Read').filter(user__in=oRequest.user.groups.all()))
    if bFrameReadOnly:
        bCanWriteRevision = False
    else:
        bCanWriteRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Write').filter(user__in=oRequest.user.groups.all()))

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(title='SAP_Inquiry_Creation_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(title='SAP_ST_Creation_Read').filter(user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadInquiry or bCanReadSiteTemplate
    bCanMoveBack = bCanReadHeader or bCanReadConfig or bCanReadTOC

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
        oForm = json.loads(oRequest.POST['data_form'])
        if type(oForm[0]) == list:
            oForm[0] = {str(x):y for (x,y) in enumerate(oForm[0])}

        if '2' in oForm[0] and oForm[0]['2'] not in ('', None):
            form = DateForm({'date': oForm[0]['2']})
            if form.is_valid():
                oHeader.release_date = form.cleaned_data['date']
            else:
                error_matrix.append([None, None, 'X - Not a valid date.'])
                valid = False
            # end if
        if '5' in oForm[0] and oForm[0]['5'] not in ('', None):
            oHeader.change_comments = oForm[0]['5']

        if valid:
            try:
                if oHeader.configuration_status.name == 'In Process' and bCanWriteRevision:
                    oHeader.save()
                    status_message = oRequest.session['status'] = 'Form data saved'
                # end if

                if oRequest.POST['formaction'] == 'prev':
                    sDestination = 'bomconfig:configrevision'
                    if bCanReadTOC:
                        sDestination = 'bomconfig:configtoc'
                    elif bCanReadConfig:
                        sDestination = 'bomconfig:config'
                    elif bCanReadHeader:
                        sDestination = 'bomconfig:configheader'
                    # end if

                    return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
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

                    return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
                # end if
            except IntegrityError:
                status_message = 'Configuration already exists in Baseline'
        # end if
    # end if

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
        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }
    return Default(oRequest, sTemplate='BoMConfig/configrevision.html', dContext=dContext)
# end def


def AddInquiry(oRequest, inquiry):
    status_message = oRequest.session.get('status', None)

    bFrameReadOnly = oRequest.GET.get('readonly', None) == '1'
    if bFrameReadOnly:
        oHeader = oRequest.GET.get('id', None)
    else:
        oHeader = oRequest.session.get('existing', None)

    # Determine which pages to which the user is able to move forward
    bCanReadHeader = bool(SecurityPermission.objects.filter(title='Config_Header_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadConfig = bool(SecurityPermission.objects.filter(title='Config_Entry_BOM_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadTOC = bool(SecurityPermission.objects.filter(title='Config_ToC_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadRevision = bool(SecurityPermission.objects.filter(title='Config_Revision_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadInquiry = bool(SecurityPermission.objects.filter(title='SAP_Inquiry_Creation_Read').filter(user__in=oRequest.user.groups.all()))
    bCanReadSiteTemplate = bool(SecurityPermission.objects.filter(title='SAP_ST_Creation_Read').filter(user__in=oRequest.user.groups.all()))

    bCanMoveForward = bCanReadSiteTemplate and inquiry
    bCanMoveBack = bCanReadHeader or bCanReadConfig or bCanReadTOC or bCanReadRevision or (not inquiry and bCanReadInquiry)

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
        if oRequest.POST['formaction'] == 'prev':
            sDestination = 'bomconfig:configinquiry' if inquiry else 'bomconfig:configsite'
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

            return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
        elif oRequest.POST['formaction'] == 'next':
            sDestination = 'bomconfig:configinquiry' if inquiry else 'bomconfig:configsite'
            if bCanReadSiteTemplate and inquiry:
                sDestination = 'bomconfig:configsite'
            # end if

            return redirect(reverse(sDestination) + ('?id=' + str(oHeader.id) + '&readonly=1' if bFrameReadOnly else ''))
    # end if

    data = BuildDataArray(oHeader=oHeader, inquiry=inquiry, site=not inquiry)
    configForm = ConfigForm(instance=oHeader.configuration if oHeader and hasattr(oHeader, 'configuration') else None)
    configForm.fields['internal_external_linkage'].widget.attrs['disabled'] = True

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
        'base_template': 'BoMConfig/frame_template.html' if bFrameReadOnly else 'BoMConfig/template.html',
        'frame_readonly': bFrameReadOnly
    }

    return Default(oRequest, sTemplate='BoMConfig/inquiry.html', dContext=dContext)
# end def


def BuildDataArray(oHeader=None, config=False, toc=False, inquiry=False, site=False, revision=False):
    """Builds an array to pass to a HTML instance of Handsontable."""
    if not bool(config) ^ bool(toc) ^ bool(inquiry) ^ bool(site) ^ bool(revision):
        raise AssertionError('Only one argument should be true')
    # end if

    if config or inquiry or site:
        if (not oHeader) or (oHeader and not hasattr(oHeader, 'configuration')):
            if config:
                if not oHeader.pick_list:
                    return [{'1': '10', '2': oHeader.configuration_designation.upper(), '3': oHeader.model_description, '4': '1',
                         '5': 'PC'}, ]
                else:
                    return [{}]
            else:
                return [{'0': '10', '1': oHeader.configuration_designation.upper(), '2': oHeader.model_description, '3': '1'},]
            # end if
        # end if

        oConfig = oHeader.configuration
        aConfigLines = ConfigLine.objects.filter(config=oConfig).order_by('line_number')
        aConfigLines = sorted(aConfigLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
        aData = []
        for Line in aConfigLines:
            if config:
                dLine ={'1': Line.line_number,
                        '2': ('..' if Line.is_grandchild else '.' if Line.is_child else '') + Line.part.base.product_number,
                        '3': Line.part.product_description, '4': Line.order_qty, '5': Line.part.base.unit_of_measure,
                        '6': Line.plant, '7': ('0' * (4 - len(str(Line.sloc)))) + Line.sloc if Line.sloc else Line.sloc,
                        '8': Line.item_category, '9': Line.pcode, '10': Line.commodity_type,
                        '11': Line.package_type, '12': Line.spud, '13': Line.REcode,
                        '14': Line.mu_flag,
                        '15': ('0' * (2 - len(Line.x_plant))) + Line.x_plant if Line.x_plant else '',
                        '16': Line.internal_notes,
                        '17': (
                            "!" + str(Line.linepricing.override_price) if GrabValue(Line,'linepricing.override_price') else
                            GrabValue(Line, 'linepricing.pricing_object.unit_price') if GrabValue(Line,'linepricing.pricing_object') else ''
                        ) if (str(Line.line_number) == '10' and not Line.config.header.pick_list) or
                             Line.config.header.pick_list else '',
                        '18': Line.higher_level_item, '19': Line.material_group_5,
                        '20': Line.purchase_order_item_num, '21': Line.condition_type, '22': Line.amount,
                        '23': Line.traceability_req, '24': Line.customer_asset, '25': Line.customer_asset_tagging,
                        '26': Line.customer_number, '27': Line.sec_customer_number, '28': Line.vendor_article_number,
                        '29': Line.comments, '30': Line.additional_ref}
            else:
                LineNumber = None
                if '.' not in Line.line_number:
                    try:
                        LineNumber = int(Line.line_number)
                    except (ValueError, TypeError):
                        pass  # This ensures that we only continue when the stored line number is an integer
                    # end try
                # end if

                if LineNumber:
                    dLine = {'0': Line.line_number, '1': Line.part.base.product_number, '2': Line.part.product_description,
                             '3': Line.order_qty, '4': Line.plant, '5': Line.sloc,
                             '6': Line.item_category}
                    if inquiry:
                        dLine.update({'7': Line.linepricing.override_price if
                                        str(Line.line_number) == '10' and hasattr(Line,'linepricing') and
                                        GrabValue(Line,'linepricing.override_price') else GrabValue(Line,'linepricing.pricing_object.unit_price') if
                                        hasattr(Line,'linepricing') else '',
                                      '9': Line.material_group_5, '10': Line.purchase_order_item_num,
                                      '11': Line.condition_type, '12': Line.amount})
                        if LineNumber == 10 and not oHeader.pick_list:
                            dLine.update({'8': oHeader.configuration.net_value})
                    else:
                        dLine.update(({'7': Line.higher_level_item}))
                    # end if
                else:
                    continue
            # end if

            for key in copy.deepcopy(dLine):
                if not dLine[key]:
                    del dLine[key]
                # end if
            # end for
            aData.append(dLine)
        # end for
        return aData
    elif toc:
        if not oHeader:
            return [[]]
        else:
            return [{'0': oHeader.configuration_designation, '1': oHeader.customer_designation or '', '2': oHeader.technology.name if oHeader.technology else '',
                     '3': oHeader.product_area1.name if oHeader.product_area1 else '', '4': oHeader.product_area2.name if oHeader.product_area2 else '', '5': oHeader.model or '', '6': oHeader.model_description or '',
                     '7': oHeader.model_replaced or '', '9': oHeader.bom_request_type.name, '10': oHeader.configuration_status.name,
                     '11': oHeader.inquiry_site_template if str(oHeader.inquiry_site_template).startswith('1') else '',
                     '12': oHeader.inquiry_site_template if str(oHeader.inquiry_site_template).startswith('4') else '',
                     '13': (oHeader.internal_notes or ''), '14': (oHeader.external_notes or '')}]
    elif revision:
        if not oHeader or not hasattr(oHeader, 'configuration'):
            return [{}]
        else:
            data = []
            while oHeader and hasattr(oHeader, 'configuration'):
                data.append({
                    '0': oHeader.bom_version, '1': oHeader.baseline_version,
                    '2': oHeader.release_date.strftime('%b. %d, %Y') if oHeader.release_date else '',
                    '3': oHeader.model if not oHeader.pick_list else 'None',
                    '4': oHeader.configuration.configline_set.filter(line_number='10')[0].customer_number if
                    not oHeader.pick_list and oHeader.configuration.configline_set.filter(line_number='10')[
                        0].customer_number else '',
                    '5': oHeader.change_notes or '',
                    '6': oHeader.change_comments or '',
                    '7': oHeader.person_responsible,
                })

                if oHeader.baseline:
                    aExistingRevs = sorted(
                        list(set([oBaseRev.version for oBaseRev in
                                  oHeader.baseline.baseline.baseline_revision_set.order_by('version')])),
                        key=RevisionCompare)
                else:
                    aExistingRevs = [oHeader.baseline_version]

                iPrev = aExistingRevs.index(oHeader.baseline_version) - 1

                if oHeader.model_replaced_link:
                    oHeader = oHeader.model_replaced_link
                elif iPrev >= 0:
                    sPrevious = aExistingRevs[iPrev]

                    oQmodel = Q(configuration_designation=oHeader.model_replaced)
                    oQconfig = Q(configuration_designation=oHeader.configuration_designation)
                    oQprogram = Q(program=oHeader.program)
                    oQbaseline = Q(baseline=oHeader.baseline.previous_revision)
                    oQbaselineVer = Q(baseline_impacted=oHeader.baseline_impacted, baseline_version=sPrevious)
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


def Validator(oRequest):
    if oRequest.method == "POST" and oRequest.POST:
        form_data = json.loads(oRequest.POST['entered_data'])
        net_total = 0
        override_total = 0
        base_total = None
        first_line = None
        zpru_total = 0
        needs_zpru = False
        status = 'GOOD'

        Parent = 0
        Child = 0
        Grandchild = 0

        # Convert list of lists to list of dicts
        if type(form_data[1]) == list:
            for index in range(len(form_data)):
                form_data[index] = {str(key): (value if value != '' else None) for key, value in zip(range(len(form_data[index])), form_data[index])}
            #end for)

        # Clean empty rows out and remove previous row statuses
        for index in range(len(form_data) - 1, -1, -1):
            if '0' in form_data[index]:
                del form_data[index]['0']

            if all(x in (None, '', 'None') for x in list(form_data[index].values())) or len(form_data[index]) < 1:
                del form_data[index]
                continue
            else:
                for x in form_data[index]:
                    form_data[index][str(x)] = str(form_data[index][str(x)]) if form_data[index][str(x)] not in (None, 'None') else ''
            # end if
        # end for

        aLineNumbers = []
        error_matrix = [['']*31 for _ in range(len(form_data))]
        for index in range(len(form_data)):

            # Check entered data formats
            # Product Number
            if '2' not in form_data[index] or form_data[index]['2'].strip('.').strip() in ('None', ''):
                error_matrix[index][2] += 'X - No Product Number provided.\n'
                form_data[index]['2'] = ''
            else:
                form_data[index]['2'] = form_data[index]['2'].upper()#.replace(' ','')
                if len(form_data[index]['2'].strip('. ')) > 18:
                    error_matrix[index][2] += 'X - Product Number exceeds 18 characters.\n'
                # end if
            # end if

            if '28' not in form_data[index] or form_data[index]['28'] == 'None':
                form_data[index]['28'] = form_data[index]['2'].strip('./')
            if '1' in form_data[index] and form_data[index]['1'] not in ('None', ''):
                # if form_data[index]['2'].startswith(('.', '..')):
                #     pass # error_matrix[index][1] += 'X - Line number provided when product number indicates relationship.\n'
                if not re.match("^\d+(?:\.\d+){0,2}$|^$", form_data[index]['1'] or '') and form_data[index]['1'] not in ('None', None):
                    error_matrix[index][1] += 'X - Invalid character. Use 0-9 and "." only.\n'
                elif form_data[index]['1'] not in ('None', None):
                    this = form_data[index]['1']
                    if this.count('.') == 0 and this:
                        Parent = int(this)
                        Child = 0
                        Grandchild = 0
                    elif this.count('.') == 1:
                        Parent = int(this[:this.find('.')])
                        Child = int(this[this.rfind('.')+1:])
                        Grandchild = 0
                    elif form_data[index]['1'].count('.') == 2:
                        Parent = int(this[:this.find('.')])
                        Child = int(this[this.find('.')+1: this.rfind('.')])
                        Grandchild = int(this[this.rfind('.')+1:])
                    # end if
                else:
                    form_data[index]['1'] = ''
                # end if

                if '2' in form_data[index] and form_data[index]['2'] not in ('None', ''):
                    if form_data[index]['1'].count('.') == 2 and not form_data[index]['2'].startswith('..'):
                        form_data[index]['2'] = '..' + form_data[index]['2']
                    elif form_data[index]['1'].count('.') == 1 and not form_data[index]['2'].startswith('.'):
                        form_data[index]['2'] = '.' + form_data[index]['2']
                    # end if
                # end if
            else:
                if form_data[index]['2'].startswith('..'):
                    Grandchild += 1
                    form_data[index]['1'] = str(Parent) + "." + str(Child) + "." + str(Grandchild)
                elif form_data[index]['2'].startswith('.'):
                    Child += 1
                    form_data[index]['1'] = str(Parent) + "." + str(Child)
                else:
                    if Parent % 10 == 0:
                        Parent += 10
                    else:
                        Parent += 1
                    Child = 0
                    Grandchild = 0
                    form_data[index]['1'] = str(Parent)
                # end if
            # end if

            # Product Description
            if '3' not in form_data[index] or form_data[index]['3'].strip() in ('None', ''):
                form_data[index]['3'] = ''

            # Order Qty
            if '4' not in form_data[index] or not re.match("^\d+$", form_data[index]['4'] or ''):
                error_matrix[index][4] += 'X - Invalid Order Qty.\n'
                if '4' in form_data[index] and form_data[index]['4'] in ('None',''):
                    form_data[index]['4'] = ''
            # end if

            # Plant
            if '6' in form_data[index] and not re.match("^\d{4}$|^$", form_data[index]['6'] or ''):
                error_matrix[index][6] += 'X - Invalid Plant.\n'
            # end if

            # SLOC
            if '7' in form_data[index] and not re.match("^\d{4}$|^$", form_data[index]['7'] or ''):
                error_matrix[index][7] += 'X - Invalid SLOC.\n'
            # end if

            # Item Cat
            if '8' in form_data[index]:
                if not re.match("^Z[A-Z0-9]{3}$|^$", form_data[index]['8'] or '', re.IGNORECASE):
                    error_matrix[index][8] += 'X - Invalid Item Cat.\n'

                if form_data[index]['8']:
                    form_data[index]['8'] = form_data[index]['8'].upper()
            # end if

            # P-Code
            if '9' in form_data[index]:
                if not re.match("^\d{2,3}$|^\(\d{2,3}-\d{4}\).*$|^[A-Z]\d{2}$|^\([A-Z]\d{2}-\d{4}\).*$|^$", form_data[index]['9'] or '', re.IGNORECASE):
                    error_matrix[index][9] += 'X - Invalid P-Code.\n'

                if form_data[index]['9']:
                    form_data[index]['9'] = form_data[index]['9'].upper()
            # end if

            # HW/SW Ind
            if '10' in form_data[index]:
                if not re.match("^H(ARD)?W(ARE)?$|^S(OFT)?W(ARE)?$|^CS$|^$", form_data[index]['10'] or '', re.IGNORECASE):
                    error_matrix[index][10] += 'X - Invalid HW/SW Ind.\n'

                if form_data[index]['10']:
                    form_data[index]['10'] = form_data[index]['10'].upper()
            # end if

            # Unit Price
            if '17' in form_data[index]:
                if form_data[index]['17'] != 'None':
                    form_data[index]['17'] = form_data[index]['17'].replace('$', '').replace(',','')

                if not re.match("^(?:-)?\d+(?:\.\d+)?$|^$", form_data[index]['17'] or ''):
                    error_matrix[index][17] += 'X - Invalid Unit Price provided.\n'
            # end if

            # Condition Type & Amount Supplied Together
            NoCondition = '21' not in form_data[index] or form_data[index]['21'] in ('', 'None')
            NoAmount = '22' not in form_data[index] or form_data[index]['22'] in ('', 'None')
            if (NoCondition and not NoAmount) or (NoAmount and not NoCondition):
                if NoAmount and not NoCondition:
                    error_matrix[index][22] += 'X - Condition Type provided without Amount.\n'
                else:
                    error_matrix[index][21] += 'X - Amount provided without Condition Type.\n'
                # end if
            # end if

            # Amount
            if '22' in form_data[index]:
                if form_data[index]['22'] != 'None':
                    form_data[index]['22'] = form_data[index]['22'].replace('$', '').replace(',','')

                if not re.match("^(?:-)?\d+(?:\.\d+)?$|^$", form_data[index]['22'] or ''):
                    error_matrix[index][22] += 'X - Invalid Amount provided.\n'
            # end if

            # Traceability Req
            if '23' in form_data[index]:
                form_data[index]['23'] = form_data[index]['23'].strip() if form_data[index]['23'] else form_data[index]['23']
                if not re.match("^Y(?:es)?$|^N(?:o)?$|^$", form_data[index]['23'] or '', re.I):
                    error_matrix[index][23] += "X - Invalid Traceability Req.\n"

                if form_data[index]['23'] != 'None':
                    form_data[index]['23'] = form_data[index]['23'].upper()
            # end if

            # Customer Asset
            if '24' in form_data[index]:
                form_data[index]['24'] = form_data[index]['24'].strip() if form_data[index]['24'] else form_data[index]['24']
                if not re.match("^Y(?:es)?$|^N(?:o)?$|^$", form_data[index]['24'] or '', re.I):
                    error_matrix[index][24] += "X - Invalid Customer Asset.\n"

                if form_data[index]['24'] != 'None':
                    form_data[index]['24'] = form_data[index]['24'].upper()

                if '23' not in form_data[index] or form_data[index]['23'] in ('None', ''):
                    pass  # error_matrix[index][24] += "X - Customer assest set without Traceability Req.\n"
                if '23' in form_data[index] and form_data[index]['23'] in ('N', 'NO') and form_data[index]['24'] in ('Y', 'YES'):
                    pass  # error_matrix[index][24] += "X - Customer asset cannot be 'Y' when Traceability is 'N'.\n"
            # end if

            # Customer Asset tagging Req
            if '25' in form_data[index]:
                form_data[index]['25'] = form_data[index]['25'].strip() if form_data[index]['25'] else form_data[index]['25']
                if not re.match("^Y(?:es)?$|^N(?:o)?$|^$", form_data[index]['25'] or '', re.I):
                    error_matrix[index][25] += "X - Invalid Customer Asset tagging Req.\n"

                if form_data[index]['25']:
                    form_data[index]['25'] = form_data[index]['25'].upper()

                if '24' not in form_data[index] or form_data[index]['24'] in ('None', ''):
                    pass  # error_matrix[index][25] += 'X - Cannot provide Customer Asset Tagging without Customer Asset.\n'
                if '24' in form_data[index] and form_data[index]['24'] in ('N', 'NO') and form_data[index]['25'] in ('Y', 'YES'):
                    error_matrix[index][25] += 'X - Cannot mark Customer Asset Tagging when part is not Customer Asset.\n'
            # end if

            # Collect data from database(s)
            oCursor = connections['BCAMDB'].cursor()

            # Populate Read-only fields
            P_Code = form_data[index]['9'] if '9' in form_data[index] and re.match("^\d{2,3}$", form_data[index]['9'], re.IGNORECASE) else None
            tPCode = None
            oCursor.execute('SELECT DISTINCT [Material Description],[MU-Flag],[X-Plant Status],[Base Unit of Measure],'+
                            '[P Code] FROM dbo.BI_MM_ALL_DATA WHERE [Material]=%s',[form_data[index]['2'].strip('.') if form_data[index]['2'] else None])
            tPartData = oCursor.fetchall()
            if tPartData:
                if Header.objects.get(pk=oRequest.session['existing']).configuration_status.name == 'In Process':
                    if '3' not in form_data[index] or form_data[index]['3'] in ('None', None, ''):
                        form_data[index]['3'] = tPartData[0][0] if tPartData[0][0] not in (None, 'NONE', 'None') else ''
                    if '14' not in form_data[index] or form_data[index]['14'] in ('None', None, ''):
                        form_data[index]['14'] = tPartData[0][1] if tPartData[0][1] not in (None, 'NONE', 'None') else ''
                    if '15' not in form_data[index] or form_data[index]['15'] in ('None', None, ''):
                        form_data[index]['15'] = tPartData[0][2] if tPartData[0][2] not in (None, 'NONE', 'None') else ''
                    if '5' not in form_data[index] or form_data[index]['5'] in ('None', None, ''):
                        form_data[index]['5'] = tPartData[0][3] if tPartData[0][3] not in (None, 'NONE', 'None') else ''

                P_Code = form_data[index]['9'] if '9' in form_data[index] and re.match("^\d{2,3}$", form_data[index]['9'], re.IGNORECASE) else tPartData[0][4]
            else:
                error_matrix[index][2] += '! - Product Number not found.'
                # if Header.objects.get(pk=oRequest.session['existing']).pick_list or index != 0:
                #     # form_data[index]['5'] = ''
                #     # form_data[index]['9'] = ''
                #     # form_data[index]['10'] = ''
                #     # form_data[index]['14'] = ''
                #     # form_data[index]['15'] = ''
                #     error_matrix[index][2] += '! - Product Number not found.'
                # else:
                #     form_data[index]['5'] = 'PC'
                # # end if
            # end def

            if P_Code:
                oCursor.execute('SELECT [PCODE],[FireCODE],[Description],[Commodity] FROM dbo.REF_PCODE_FCODE WHERE [PCODE]=%s', [P_Code])
                tPCode = oCursor.fetchall()
            # end if

            if tPCode:
                # form_data[index]['9'] = '(' + tPCode[0][0] + " - " + tPCode[0][1] + "), " + tPCode[0][2]
                if '9' not in form_data[index] or form_data[index]['9'] in (None, 'None', '') or re.match("^\d{2,3}$", form_data[index]['9'], re.IGNORECASE):
                    form_data[index]['9'] = tPCode[0][2] if tPCode[0][2] else ''
                if '10' not in form_data[index] or form_data[index]['10'] == 'None':
                    form_data[index]['10'] = tPCode[0][3] if tPCode[0][3] else ''
                # end if
            # end if

            if '6' in form_data[index] and form_data[index]['6'] not in ('None', ''):
                oCursor.execute('SELECT [Plant] FROM dbo.REF_PLANTS')
                tPlants = [element[0] for element in oCursor.fetchall()]
                if form_data[index]['6'] not in tPlants:
                    error_matrix[index][6] += "! - Plant not found in database.\n"
            # end if

            if '7' in form_data[index] and form_data[index]['7'] not in ('None', ''):
                oCursor.execute('SELECT DISTINCT [SLOC] FROM dbo.REF_PLANT_SLOC')
                tSLOC = [element[0] for element in oCursor.fetchall()]
                if form_data[index]['7'] not in tSLOC:
                    error_matrix[index][7] += "! - SLOC not found in database.\n"
            # end if

            if '6' in form_data[index] and form_data[index]['6'] not in ('None', '')\
                    and '7' in form_data[index] and form_data[index]['7'] not in ('None', ''):
                oCursor.execute('SELECT [Plant],[SLOC] FROM dbo.REF_PLANT_SLOC WHERE [Plant]=%s AND [SLOC]=%s', [form_data[index]['6'], form_data[index]['7']])
                tResults = oCursor.fetchall()
                if (form_data[index]['6'], form_data[index]['7']) not in tResults:
                    error_matrix[index][6] += '! - Plant/SLOC combination not found.\n'
                    error_matrix[index][7] += '! - Plant/SLOC combination not found.\n'
                # end if
            # end if

            # Validate entries

            # Accumulate running total
            if '4' in form_data[index] and form_data[index]['4'] not in ('None', ''):
                if '21' in form_data[index] and form_data[index]['21'] == 'ZPR1':
                    needs_zpru = True
                    zpru_total += (float(form_data[index]['22'] if '22' in form_data[index] and form_data[index]['22'] else 0) * float(form_data[index]['4']))
                elif '21' in form_data[index] and form_data[index]['21'] == 'ZPRU':
                    needs_zpru = True
                elif '17' in form_data[index] and form_data[index]['17'] not in ('None', None, ''):
                    oHead = Header.objects.get(pk=oRequest.session['existing'])
                    if index == 0 and not oHead.pick_list:
                        # base_total = oHead.configuration.override_net_value or oHead.configuration.net_value
                        base_total = float(form_data[index]['17'].replace('!','')) if form_data[index]['17'] not in (None, '', 'None') else 0

                        if '21' in form_data[index] and form_data[index]['21'] == 'ZUST' and  '22' in form_data[index] and form_data[index]['22']:
                            base_total += float(form_data[index]['22'].replace('$','').replace(',',''))
                        # end if
                    # end if

                    if str(form_data[index]['17']).startswith('!'):
                        override_total += float(form_data[index]['17'][1:].replace('$','').replace(',','')) +\
                                          float(form_data[index]['22'].replace('$','').replace(',','')\
                                                    if '22' in form_data[index] and form_data[index]['22'] else 0)
                        error_matrix[index][17] = '! - CPM override in effect.\n'
                    else:
                        net_total += (float(form_data[index]['4']) * (float(form_data[index]['17'].replace('$','')
                                                                            .replace(',','')) if not (index == 0 and not oHead.pick_list) else 0)) +\
                                     float(form_data[index]['22'].replace('$','').replace(',','') if '22' in form_data[index] and form_data[index]['22'] else 0)
                    # end if
                    form_data[index]['17'] = form_data[index]['17'].replace('!','')
                # end if
            # end if

            aLineNumbers.append(form_data[index]['1'])

            # Update line status
            if any("X - " in error for error in error_matrix[index]):
                form_data[index]['0'] = '<span class="glyphicon glyphicon-remove-sign" style="color:#DD0000;"></span>'
                status = 'ERROR'
            elif any("! - " in error for error in error_matrix[index]):
                form_data[index]['0'] = '<span class="glyphicon glyphicon-exclamation-sign" style="color:#FF8800;"></span>'
                if status == 'GOOD':
                    status = 'WARNING'
                # end if
            else:
                form_data[index]['0'] = '<span class="glyphicon glyphicon-ok-sign" style="color:#00AA00;"></span>'
            # end if

        # end for

        # Check for duplicate line numbers
        dIndices = {}
        aDuplicates = []
        for index in range(len(form_data)):
            try:
                dIndices[form_data[index]['1']].append(index)
            except KeyError:
                dIndices[form_data[index]['1']] = [index]
            # end try
        # end for

        for aIndices in dIndices.values():
            if len(aIndices) > 1:
                aDuplicates.extend(aIndices[1:])
            # end if
        # end for

        for index in aDuplicates:
            form_data[index]['0'] = '<span class="glyphicon glyphicon-remove-sign" style="color:#DD0000;"></span>'
            error_matrix[index][1] = 'X - Duplicate line number.\n'
            status = 'ERROR'
        # end for

        if override_total and not base_total:
            form_data[0]['17'] = '!' + str(override_total)
        # end if

        dReturned = {'data': form_data, 'nettotal': round(base_total or override_total or net_total, 2), 'zprutotal': round(zpru_total, 2), 'errors': error_matrix,
                     'zpru': str(needs_zpru), 'status': status}
        return HttpResponse(json.dumps(dReturned))
    else:
        return redirect(reverse('bomconfig:index'))
    # end if
# end def


def ReactSearch(oRequest):
    if oRequest.method != 'POST' or not oRequest.POST:
        return Http404()
    # end if
    dReturnData = {}
    sPSMReq = oRequest.POST['psm_req']
    sQuery = "SELECT [req_id],[assigned_to],[customer_name],[sales_o],[sales_g],[sold_to_code],[ship_to_code],[bill_to_code],"+\
             "[pay_terms],[workgroup],[cu],[mus_cnt_num] FROM dbo.ps_requests WHERE [req_id] = %s AND [Modified_by] IS NULL"
    oCursor = connections['REACT'].cursor()
    oCursor.execute(sQuery, [sPSMReq])
    oResults = oCursor.fetchall()

    if oResults:
        oUser = User.objects.filter(email__iexact=oResults[0][1])
        if oUser: oUser = oUser[0]
        dReturnData.update({
            'req_id': oResults[0][0],
            'person_resp': oUser.first_name + " " + oUser.last_name if oUser else '',
            'cust_name': oResults[0][2],
            'sales_office': oResults[0][3],
            'sales_group': oResults[0][4],
            'sold_to': oResults[0][5],
            'ship_to': oResults[0][6],
            'bill_to': oResults[0][7],
            'terms': oResults[0][8].split()[0],
            'workgroup': oResults[0][9],
            'cust': oResults[0][10],
            'contract': oResults[0][11]
        })
    # end if

    return JsonResponse(data=dReturnData)
# end def


def ListFill(oRequest):
    if oRequest.method == 'POST' and oRequest.POST:
        iParentID = int(oRequest.POST['id'])
        cParentClass = Header._meta.get_field(oRequest.POST['parent']).rel.to
        oParent = cParentClass.objects.get(pk=iParentID)
        if oRequest.POST['child'] != 'baseline_impacted':
            cChildClass = Header._meta.get_field(oRequest.POST['child']).rel.to
            result = {obj.id:obj.name for obj in cChildClass.objects.filter(parent=oParent)}
        else:
            cChildClass = Baseline
            result = {obj.title:obj.title for obj in cChildClass.objects.filter(customer=oParent)}

        return JsonResponse(result)
    else:
        raise Http404
    # end if
#end def


def ListREACTFill(oRequest):
    from itertools import chain
    if oRequest.method == 'POST' and oRequest.POST:
        iParentID = int(oRequest.POST['id'])
        cParentClass = Header._meta.get_field(oRequest.POST['parent']).rel.to

        oParent = cParentClass.objects.get(pk=iParentID)

        oCursor = connections['REACT'].cursor()
        oCursor.execute('SELECT DISTINCT [Customer] FROM ps_fas_contracts WHERE [CustomerUnit]=%s',[oParent.name])
        tResults = oCursor.fetchall()
        result = {obj: obj for obj in chain.from_iterable(tResults)}
        return JsonResponse(result)
    else:
        raise Http404
    # end if
#end def


def Clone(oRequest):
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
                dResult['errors'].append('Duplicate Configuration already exists. (Ensure that previous clones have been renamed)')
        else:
            dResult['errors'].append('Undetermined database error')
    except Exception as ex:
        dResult['errors'].append(str(ex))

    return JsonResponse(dResult)
