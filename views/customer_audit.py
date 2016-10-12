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
import zipfile


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
            oNewCustInfo.priority = True
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

    dContext = {'customer_list': REF_CUSTOMER.objects.all()}

    if oRequest.POST:
        try:
            bErrors = ProcessUpload(oRequest.FILES['file'], int(oRequest.POST['file_type']), REF_CUSTOMER.objects.get(id=oRequest.POST['customer']), oRequest.user)
            status_message = 'Upload completed.' + (' An email has been sent detailing discrepancies.' if bErrors else '')
            status_error = False
        except TypeError:
            status_message = "Invalid file provided or file does not match selected type."
            status_error = True
        except ValueError:
            status_message = 'Invalid file type selected.'
            status_error = True

        dContext['status_message'] = status_message
        dContext['status_error'] = status_error

    return Default(oRequest, sTemplate='BoMConfig/customer_audit_upload.html', dContext=dContext)
# end def


def ProcessUpload(oStream, iFileType, oCustomer, oUser):
    if iFileType == 1:
        sSheetName = "Ericsson BOM Report"
        aColumns = [[2, 3, 4, 5, 6, 8], [9, 10, 11, 12, 13, 16]]
        aHeaders = ['Oracle Parent', 'Parent Barcode', 'Parent EADC', 'Parent MPN', 'Parent Description', 'Parent Status',
                    'Oracle Child', 'Child Barcode', 'Child EADC', 'Child MPN', 'Child Description', 'Child Item Status']
    elif iFileType == 2:
        sSheetName = "Ericsson IM"
        aColumns = [[3, 6, 10, 12, 5, 8]]
        aHeaders = ['Item Number', 'Barcode', 'External Download Code', 'Manufacturer Part Number', 'Item Description', 'Status Code']
    else:
        raise ValueError('Invalid file type')

    try:
        oFile = openpyxl.load_workbook(oStream, read_only=True)
    except (IOError, utils.exceptions.InvalidFileException, zipfile.BadZipFile):
        raise TypeError('Invalid file')

    for sName in oFile.get_sheet_names():
        if sSheetName in sName:
            sSheetName = sName
            break

    try:
        oDataSheet = oFile.get_sheet_by_name(sSheetName)
    except KeyError:
        raise TypeError('Invalid sheet name')

    aSheetData = oDataSheet.rows

    aFileHeaders = next(aSheetData, list())
    tDesiredHeaders = list(str(aFileHeaders[i-1].value).strip() for i in itertools.chain.from_iterable(aColumns))

    if tDesiredHeaders != aHeaders:
        raise TypeError('Header line mismatch')

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

    # aExtractedData will be sorted by Status: Inactive/Obsolete, Active, Phased
    # This helps when uploading records.  Since active records will be processed first, we can assume that any conflicts
    # experienced by phased records are not critical errors
    aExtractedData.sort(key=lambda x: 1 if x[5] in ['Inactive', 'Obsolete'] else 3 if 'Phase' in x[5] else 2 if 'Active' in x[5] else 0)

    aDuplicateMPN = []
    aDuplicateCust = []
    aDuplicateTag = []
    aDuplicateInactive = []
    aInvalidEntries = []

    bErrorsLogged = False

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
        # Determine if Part should be deactivated/added as inactive (Status is "Inactive" or "Obsolete" or 'Discontinued use' in description)
        if tPart[5] in ['Inactive', 'Obsolete'] or 'DISCONTINUED' in str(tPart[4]).upper():
            (oMap, bCreated) = CustomerPartInfo.objects.get_or_create(part=oPart,
                                                                      customer=oCustomer,
                                                                      customer_number=tPart[0],
                                                                      customer_asset=tPart[2],
                                                                      customer_asset_tagging=tPart[1])
            if not bCreated and not oMap.priority:
                oMap.active = False
                oMap.save()
            elif not bCreated and oMap.priority:
                aDuplicateInactive.append(tPart)
        else:
            # Check if any mappings exists with current info
            try:
                oExactMap = CustomerPartInfo.objects.get(part=oPart,
                                                         customer=oCustomer,
                                                         customer_number=tPart[0],
                                                         customer_asset=tPart[2],
                                                         customer_asset_tagging=tPart[1])
            except CustomerPartInfo.DoesNotExist:
                oExactMap = None
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

            # If there is an exact match, and its status already matches the line data status, nothing further is required
            if oExactMap and ((oExactMap.active and "Active" in tPart[5]) or (not oExactMap.active and "Phase" in tPart[5])):
                continue

            # If there is an exact match, and its status does not match the line data status, the remaining checks also
            # need to occur, to ensure we do not overwrite protected data.
            # We should log in error if this line data is attempting to overwrite protected  (priority) information
            elif oExactMap and ((oExactMap.active and oExactMap.priority and "Phase" in tPart[5]) or
                                  (not oExactMap.active and oExactMap.priority and "Active" in tPart[5])):
                aDuplicateInactive.append(tPart)

                continue

            # If the Part match and Customer number match are the same, then there is really only one match,
            # the only difference between the match and line record is the customer asset information
            elif oPartMap and oCustMap and oPartMap == oCustMap:
                # If the line record is "Phase NTW" or "Phase RCL", don't log the error.
                # oMap will either be a new inactive record, or an existing record (possibly active).
                # Leave the record as-is, because it might be newer information.
                # Log the error if the record is protected and the line data is attempting to change that
                if oPartMap.priority and 'Active' in tPart[5]:
                    aDuplicateTag.append(tPart)

                CustomerPartInfo.objects.get_or_create(part=oPart,
                                                       customer=oCustomer,
                                                       customer_number=tPart[0],
                                                       customer_asset=tPart[2],
                                                       customer_asset_tagging=tPart[1])

                if 'Phase' in tPart[5] or oPartMap.priority:
                    continue
            # end if

            # If the MPN and Customer Number each have their own separate active matches, log the errors
            elif oPartMap or oCustMap:
                # If the line record is "Phase NTW" or "Phase RCL", don't log the error.
                # oMap will either be a new inactive record, or an existing record (possibly active)
                # If it is inactive, that is fine since the part is phased. If it is active, just leave it active
                # since it might be newer information than what is provided by upload
                # Log the error if the line data is attempting to overwrite protected information
                if oPartMap and oPartMap.priority and 'Active' in tPart[5]:
                    aDuplicateMPN.append(tPart)

                if oCustMap and oCustMap.priority and 'Active' in tPart[5]:
                    aDuplicateCust.append(tPart)

                CustomerPartInfo.objects.get_or_create(part=oPart,
                                                       customer=oCustomer,
                                                       customer_number=tPart[0],
                                                       customer_asset=tPart[2],
                                                       customer_asset_tagging=tPart[1])

                if 'Phase' in tPart[5] or (oPartMap and oPartMap.priority) or (oCustMap and oCustMap.priority):
                    continue
            # end if

            # Only line records that do not conflict with existing protected data
            # will have made it this far, so it is fine to make the record active in the database.
            (oMap, _) = CustomerPartInfo.objects.get_or_create(part=oPart,
                                                               customer=oCustomer,
                                                               customer_number=tPart[0],
                                                               customer_asset=tPart[2],
                                                               customer_asset_tagging=tPart[1])

            if "Active" in tPart[5]:
                oMap.active = True
                oMap.save()
        # end if
    # end for

    if aDuplicateCust or aDuplicateMPN or aDuplicateTag or aDuplicateInactive or aInvalidEntries:
        bErrorsLogged = True
        aDuplicateInactive.sort(key=lambda x: x[3])
        aDuplicateCust.sort(key=lambda x: x[3])
        aDuplicateTag.sort(key=lambda x: x[3])
        aDuplicateMPN.sort(key=lambda x: x[3])
        aInvalidEntries.sort(key=lambda x: x[0])
        # Send discrepancy email
        subject = 'Customer Part Number upload discrepancies'
        from_email = 'pcbm.admin@ericsson.com'
        text_message = GenerateEmailMessage(**{'cust': aDuplicateCust, 'mpn': aDuplicateMPN, 'tag': aDuplicateTag,
                                               'inactive': aDuplicateInactive, 'user': oUser, 'invalid': aInvalidEntries,
                                               'filename': oStream.name, 'type': iFileType})
        html_message = render_to_string('BoMConfig/customer_audit_email.html', {'cust': aDuplicateCust, 'mpn': aDuplicateMPN,
                                                                                'tag': aDuplicateTag, 'inactive': aDuplicateInactive,
                                                                                'user': oUser, 'invalid': aInvalidEntries,
                                                                                'filename': oStream.name, 'type': iFileType})
        oUser.email_user(subject=subject, message=text_message, from_email=from_email, html_message=html_message)
    # end if

    return bErrorsLogged
# end def


def GenerateEmailMessage(cust=(), mpn=(), tag=(), inactive=(), invalid=(), user=None, filename='', type=0):
    temp = 'Hello {},\n\nThe following errors were found while uploading {} ({}):\n\n'.format(
        user.first_name, filename, 'BOM Report' if type == 1 else 'IM Report' if type == 2 else '')

    aErrorLists = [inactive, tag, mpn, cust, invalid]
    aTableTitles = ['Attempted to change priority Customer Number/MPN mapping',
                    'Matches priority Customer Number/MPN mapping with different customer asset information',
                    'MPN priority mapped to different Customer number',
                    'Customer Number priority mapped to different MPN',
                    'Customer Number and/or MPN is invalid']

    for (idx, maplist) in enumerate(aErrorLists):
        if maplist:
            temp += aTableTitles[idx] + '\n'
            for map in maplist:
                temp += '\t' + map[0] + ' / ' + map[3] + ' / ' + ('Y' if map[1] else "N" if map[1] is False else "(None)") + \
                        ' / ' + ('Y' if map[2] else "N" if map[2] is False else "(None)") + '\n'
            temp += '\n'
        # end if
    # end for

    return temp
# end def
