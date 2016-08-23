from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

from BoMConfig.models import CustomerPartInfo, PartBase, REF_CUSTOMER
from BoMConfig.views.landing import Default
from BoMConfig.utils import StrToBool

import openpyxl
from openpyxl import utils

import json
import itertools


def CustomerAuditLand(oRequest):
    return redirect('bomconfig:customeraudit')


def CustomerAudit(oRequest):
    dContext = {
        'customer_list': REF_CUSTOMER.objects.all(),
        'data': json.dumps([[]]),
        'selectedCust': REF_CUSTOMER.objects.first()
    }

    if oRequest.POST:
        aData = json.loads(oRequest.POST.get('dataForm', '[]'))
        oCustomer = REF_CUSTOMER.objects.get(id=oRequest.POST.get('customerSelect'))

        if aData:
            aData = list(aLine for aLine in aData if any(aLine))

        for aLine in aData:
            try:
                (oPart,_) = PartBase.objects.get_or_create(product_number=aLine[0], defaults={'unit_of_measure': 'PC'})
            except PartBase.MultipleObjectsReturned:
                oPart = PartBase.objects.filter(product_number=aLine[0]).first()

            dNewCustInfo = {
                'customer': oCustomer,
                'customer_number': aLine[1],
                'part': oPart,
                'customer_asset_tagging': True if aLine[2] == 'Y' else False if aLine[2] == 'N' else None,
                'customer_asset': True if aLine[3] == 'Y' else False if aLine[3] == 'N' else None
            }

            # if bCreateNew:
            (oNewCustInfo, bCreated) = CustomerPartInfo.objects.get_or_create(**dNewCustInfo)

            oNewCustInfo.active = True
            oNewCustInfo.save()
        # end for

        dContext['data'] = json.dumps(aData)
        dContext['selectedCust'] = oCustomer

    return Default(oRequest, 'BoMConfig/customer_audit.html', dContext)
# end def


def CustomerAuditTableValidate(oRequest):
    received_data = json.loads(oRequest.POST['changed_data'])
    customer = oRequest.POST['customer']
    override = StrToBool(str(oRequest.POST.get('override', False)))

    response_data = {
        'table_data': {},
        'table_info': {},
    }

    for key in received_data.keys():
        response_data['table_data'][key] = [None] * 4
        response_data['table_info'][key] = [None] * 4

        part = None
        cust_info = None
        try:
            part = PartBase.objects.get(product_number=received_data[key][0])
            cust_info = part.customerpartinfo_set.get(customer__id=customer, active=True)
            response_data['table_data'][key][0] = part.product_number
            response_data['table_info'][key][0] = True
        except PartBase.DoesNotExist:
            if any(received_data[key]):
                response_data['table_data'][key][0] = received_data[key][0]
                response_data['table_info'][key][0] = None
            else:
                response_data['table_data'][key][0] = None
                response_data['table_info'][key][0] = None
        except (CustomerPartInfo.DoesNotExist, ValueError):
            response_data['table_data'][key][0] = part.product_number
            response_data['table_info'][key][0] = True
        # end try

        if not cust_info:
            try:
                cust_info = CustomerPartInfo.objects.get(customer_number=received_data[key][1], customer__id=customer, active=True)
                # if not response_data['table_data'][key][0]:
                response_data['table_data'][key][0] = cust_info.part.product_number

            except (CustomerPartInfo.DoesNotExist, ValueError):
                response_data['table_data'][key][1] = received_data[key][1]
                response_data['table_info'][key][1] = None
            # end try
        # end if

        if cust_info:
            if override:
                response_data['table_data'][key][0] = received_data[key][0] or cust_info.part.product_number
                response_data['table_info'][key][0] = True if cust_info.part.product_number == received_data[key][0] or not received_data[key][0] else None

                response_data['table_data'][key][1] = received_data[key][1] or cust_info.customer_number
                response_data['table_info'][key][1] = True if cust_info.customer_number == received_data[key][1] or not received_data[key][1] else None

                response_data['table_data'][key][2] = received_data[key][2] #or ('Y' if cust_info.customer_asset_tagging else 'N')
                response_data['table_data'][key][3] = received_data[key][3] #or ('Y' if cust_info.customer_asset else 'N')

                if cust_info.customer_asset_tagging is not None and received_data[key][2]:
                    response_data['table_info'][key][2] = True if bool(
                        cust_info.customer_asset_tagging == StrToBool(received_data[key][2], "")) else None
                elif cust_info.customer_asset_tagging is not None and not received_data[key][2]:
                    response_data['table_info'][key][2] = None
                elif cust_info.customer_asset_tagging is None:
                    response_data['table_info'][key][2] = None

                if cust_info.customer_asset is not None and received_data[key][3]:
                    response_data['table_info'][key][3] = True if bool(
                        cust_info.customer_asset == StrToBool(received_data[key][3], "")) else None
                elif cust_info.customer_asset is not None and not received_data[key][3]:
                    response_data['table_info'][key][3] = None
                elif cust_info.customer_asset is None:
                    response_data['table_info'][key][3] = None
            else:
                response_data['table_data'][key][0] = cust_info.part.product_number
                response_data['table_info'][key][0] = bool(cust_info.part.product_number == received_data[key][0])

                response_data['table_data'][key][1] = cust_info.customer_number
                response_data['table_info'][key][1] = bool(cust_info.customer_number == received_data[key][1])

                response_data['table_data'][key][2] = "Y" if cust_info.customer_asset_tagging else "N" if cust_info.customer_asset_tagging == False else ' '
                response_data['table_data'][key][3] = "Y" if cust_info.customer_asset else "N" if cust_info.customer_asset == False else ' '

                if cust_info.customer_asset_tagging is not None:
                    if received_data[key][2]:
                        response_data['table_info'][key][2] = bool(cust_info.customer_asset_tagging == StrToBool(received_data[key][2], ""))
                    elif not received_data[key][2]:
                        response_data['table_info'][key][2] = False
                else:
                    if not received_data[key][2]:
                        response_data['table_info'][key][2] = True
                    else:
                        response_data['table_info'][key][2] = False

                if cust_info.customer_asset is not None:
                    if received_data[key][3]:
                        response_data['table_info'][key][3] = bool(
                            cust_info.customer_asset == StrToBool(received_data[key][3], ""))
                    elif not received_data[key][3]:
                        response_data['table_info'][key][3] = False
                else:
                    if not received_data[key][3]:
                        response_data['table_info'][key][3] = True
                    else:
                        response_data['table_info'][key][3] = False
        else:
            response_data['table_data'][key][1] = received_data[key][1]
            response_data['table_data'][key][2] = received_data[key][2]
            response_data['table_data'][key][3] = received_data[key][3]
            if response_data['table_data'][key][1] and response_data['table_info'][key][1] is None:
                response_data['table_data'][key][2] = response_data['table_data'][key][2] #or 'N'
                response_data['table_info'][key][2] = None
                response_data['table_data'][key][3] = response_data['table_data'][key][3] #or 'N'
                response_data['table_info'][key][3] = None
        # end if

    return JsonResponse(response_data)
# end def


def CustomerAuditUpload(oRequest):
    if oRequest.POST:
        # try:
        status_message = ProcessUpload(oRequest.FILES['file'], int(oRequest.POST['file_type']), REF_CUSTOMER.objects.get(id=oRequest.POST['customer']), oRequest.user)
        # except TypeError:
        #     status_message = "Invalid file provided or file does not match selected type."
        # except ValueError:
        #     status_message = 'Invalid file type selected.'

    return Default(oRequest, sTemplate='BoMConfig/customer_audit_upload.html', dContext={'customer_list': REF_CUSTOMER.objects.all()})
# end def


def ProcessUpload(oStream, iFileType, oCustomer, oUser):
    if iFileType == 1:
        sSheetName = "Ericsson BOM Report"
        aColumns = [[2, 3, 4, 5, 6], [9, 10, 11, 12, 13]]
        aHeaders = ['Oracle Parent', 'Parent Barcode', 'Parent EADC', 'Parent MPN', 'Parent Description',
                    'Oracle Child', 'Child Barcode', 'Child EADC', 'Child MPN', 'Child Description']
    elif iFileType == 2:
        sSheetName = "Ericsson IM"
        aColumns = [[3, 6, 10, 12, 5]]
        aHeaders = ['Item Number', 'Barcode', 'External Download Code', 'Manufacturer Part Number', 'Item Description']
    else:
        raise ValueError

    try:
        oFile = openpyxl.load_workbook(oStream, read_only=True)
    except (IOError, utils.exceptions.InvalidFileException):
        raise TypeError

    for sName in oFile.get_sheet_names():
        if sSheetName in sName:
            sSheetName = sName
            break

    try:
        oDataSheet = oFile.get_sheet_by_name(sSheetName)
    except KeyError:
        raise TypeError

    aSheetData = oDataSheet.rows

    aFileHeaders = next(aSheetData, list())
    tDesiredHeaders = list(str(aFileHeaders[i-1].value).strip() for i in itertools.chain.from_iterable(aColumns))

    if tDesiredHeaders != aHeaders:
        raise TypeError

    aExtractedData = []

    for row in aSheetData:
        for aDataGroup in aColumns:
            aTemp = []
            for (idx, iCol) in enumerate(aDataGroup):
                oData = row[iCol - 1].value
                if idx == 0 and oData:
                    oData = oData.upper()
                elif idx == 1:
                    if oData and oData.strip() == 'Y':
                        oData = True
                    elif oData and oData.strip() == 'N':
                        oData = False
                    else:
                        oData = None
                elif idx == 2:
                    if oData and oData.strip() in ('E', 'C'):
                        oData = True
                    elif oData is not None:
                        oData = False
                    else:
                        oData = None
                elif idx == 3 and oData:
                    # Convert integer-like part numbers (Part number containing only digits must have '/' appended)
                    oData = oData.upper()
                    try:
                        int(oData)
                        oData += '/'
                    except ValueError:
                        pass

                aTemp.append(oData)
            # end for
            aTemp = tuple(aTemp)

            if any(aTemp):
                aExtractedData.append(aTemp)
        # end for
    # end for

    aExtractedData = list(set(aExtractedData))

    aDuplicateMPN = []
    aDuplicateCust = []
    aDuplicateTag = []
    aDuplicateInactive = []
    aInvalidEntries = []

    # Add/Remove each part
    for tPart in aExtractedData:
        if 'VARIOUS' in tPart[3].upper() or 'UNKNOWN' in tPart[3].upper() or str(tPart[3]).upper().strip() == 'NONE':
            aInvalidEntries.append(tPart)
            continue

        if str(tPart[0]).upper().strip() == 'NONE':
            aInvalidEntries.append(tPart)
            continue

        if 'DUPLICATE ITEM USE' in str(tPart[4]).upper():
            continue

        (oPart,_) = PartBase.objects.get_or_create(product_number=tPart[3], defaults={'unit_of_measure': 'PC'})
        # Determine if Part should be deactivated/added as inactive ('Discontinued use' in description)
        if 'DISCONTINUED' in str(tPart[4]).upper():
            (oMap, bCreated) = CustomerPartInfo.objects.get_or_create(part=oPart,
                                                                      customer=oCustomer,
                                                                      customer_number=tPart[0],
                                                                      customer_asset=tPart[2],
                                                                      customer_asset_tagging=tPart[1])
            if not bCreated:
                oMap.active = False
                oMap.save()
        else:
            # Check if any mapping exists with current info
            try:
                oExactMap = CustomerPartInfo.objects.get(part=oPart,
                                                         customer=oCustomer,
                                                         customer_number=tPart[0],
                                                         customer_asset=tPart[2],
                                                         customer_asset_tagging=tPart[1])
            except CustomerPartInfo.DoesNotExist:
                oExactMap = None\
            # end try

            try:
                oPartMap = CustomerPartInfo.objects.get(part=oPart, customer=oCustomer, active=True)
            except CustomerPartInfo.DoesNotExist:
                oPartMap = None
            # end try

            try:
                oCustMap = CustomerPartInfo.objects.get(customer_number=tPart[0], customer=oCustomer, active=True)
            except CustomerPartInfo.DoesNotExist:
                oCustMap = None
            # end try

            if oExactMap:
                if oExactMap.active:
                    continue
                else:
                    aDuplicateInactive.append(tPart)
                    continue
                # end if
            elif oPartMap and oCustMap and oPartMap == oCustMap:
                aDuplicateTag.append(tPart)
                CustomerPartInfo.objects.get_or_create(part=oPart,
                                                       customer=oCustomer,
                                                       customer_number=tPart[0],
                                                       customer_asset=tPart[2],
                                                       customer_asset_tagging=tPart[1])
                continue
            # end if

            if oPartMap or oCustMap:
                if oPartMap:
                    aDuplicateMPN.append(tPart)

                if oCustMap:
                    aDuplicateCust.append(tPart)

                CustomerPartInfo.objects.get_or_create(part=oPart,
                                                       customer=oCustomer,
                                                       customer_number=tPart[0],
                                                       customer_asset=tPart[2],
                                                       customer_asset_tagging=tPart[1])

                continue
            # end if

            (oMap, _) = CustomerPartInfo.objects.get_or_create(part=oPart,
                                                               customer=oCustomer,
                                                               customer_number=tPart[0],
                                                               customer_asset=tPart[2],
                                                               customer_asset_tagging=tPart[1])

            oMap.active = True
            oMap.save()
        # end if
    # end for

    if aDuplicateCust or aDuplicateMPN or aDuplicateTag or aDuplicateInactive or aInvalidEntries:
        aDuplicateInactive.sort(key=lambda x: x[3])
        aDuplicateCust.sort(key=lambda x: x[3])
        aDuplicateTag.sort(key=lambda x: x[3])
        aDuplicateMPN.sort(key=lambda x: x[3])
        aInvalidEntries.sort(key=lambda x: x[0])
        # Send discrepancy email
        subject = 'Customer Part Number upload discrepancies'
        from_email = 'pcbm.admin@ericsson.com'
        to_email = [user.email for user in get_user_model().objects.filter(groups__name='BOM_PSM_Baseline_Manager')]
        to_email = [oUser.email]
        text_message = GenerateEmailMessage(**{'cust': aDuplicateCust, 'mpn': aDuplicateMPN, 'tag': aDuplicateTag,
                                               'inactive': aDuplicateInactive, 'user': oUser, 'invalid': aInvalidEntries,
                                               'filename': oStream.name, 'type': iFileType})
        html_message = render_to_string('BoMConfig/customer_audit_email.html', {'cust': aDuplicateCust, 'mpn': aDuplicateMPN,
                                                                                'tag': aDuplicateTag, 'inactive': aDuplicateInactive,
                                                                                'user': oUser, 'invalid': aInvalidEntries,
                                                                                'filename': oStream.name, 'type': iFileType})
        oUser.email_user(subject=subject, message=text_message, from_email=from_email, html_message=html_message)
    # end if
# end def


def GenerateEmailMessage(cust=(), mpn=(), tag=(), inactive=(), invalid=(), user=None, filename='', type=0):
    temp = 'Hello {},\n\nThe following errors were found while uploading {} ({}):\n\n'.format(
        user.first_name, filename, 'BOM Report' if type == 1 else 'IM Report' if type == 2 else '')

    if inactive:
        maplist = inactive
        temp += 'Matches inactive Customer Number/MPN mapping\n'
        for map in maplist:
            temp += '\t' + map[0] + ' / ' + map[3] + '\n'
        temp += '\n'
    # end if

    if tag:
        maplist = tag
        temp += 'Matches Customer Number/MPN mapping with different customer asset information\n'
        for map in maplist:
            temp += '\t' + map[0] + ' / ' + map[3] + '\n'
        temp += '\n'
    # end if

    if mpn:
        maplist = mpn
        temp += 'MPN mapped to different Customer number\n'
        for map in maplist:
            temp += '\t' + map[3] + ' / ' + map[0] + '\n'
        temp += '\n'
    # end if

    if cust:
        maplist = cust
        temp += 'Customer Number mapped to different MPN\n'
        for map in maplist:
            temp += '\t' + map[0] + ' / ' + map[3] + '\n'
        temp += '\n'
    # end if

    if invalid:
        maplist = invalid
        temp += 'Customer Number and/or MPN is invalid\n'
        for map in maplist:
            temp += '\t' + map[0] + ' / ' + map[3] + '\n'
        temp += '\n'
    # end if

    return temp
# end def
