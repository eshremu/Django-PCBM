"""
Views associated with creating, editing, loading, and performing audit of
customer number / Ericsson number mappings.
"""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from BoMConfig.models import CustomerPartInfo, PartBase, REF_CUSTOMER, \
    ConfigLine, User_Customer
from BoMConfig.views.landing import Default
from BoMConfig.utils import StrToBool

import openpyxl
from openpyxl import utils

import json
import itertools
import zipfile


def CustomerAuditLand(oRequest):
    """
    Landing view for customer audit functions
    :param oRequest: Django HTTP request
    :return: redirect to CustomerAudit function
    """
    return redirect('bomconfig:customeraudit')


@login_required
def CustomerAudit(oRequest):
    """
    View for creating, editing, and validating customer part number mappings.
    :param oRequest: Django HTTP request
    :return: HTTPResponse via Default function
    """
    # S-06174- Customer Audit restrict view
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    dContext = {
        'customer_list': aAvailableCU, # S-06174- Customer Audit restrict view changed to aAvailableCU
        'data': json.dumps([[]]),
        'selectedCust': REF_CUSTOMER.objects.first()
    }

    # If POSTing save data
    if oRequest.POST:
        # Retrieve form and customer data POSTed
        aData = json.loads(oRequest.POST.get('dataForm', '[]'))
        oCustomer = REF_CUSTOMER.objects.get(
            id=oRequest.POST.get('customerSelect'))

        # Remove empty data rows from data set
        if aData:
            aData = list(aLine for aLine in aData if any(aLine))

        for aLine in aData:
            # Retrieve PartBase object that is being linked
            try:
                (oPart, _) = PartBase.objects.get_or_create(
                    product_number=aLine[0], defaults={'unit_of_measure': 'PC'})
            except PartBase.MultipleObjectsReturned:
                oPart = PartBase.objects.filter(product_number=aLine[0]).first()

            # Create expected entry from data submitted
            dNewCustInfo = {
                'customer': oCustomer,
                'customer_number': aLine[1],
                'second_customer_number': aLine[2] or None,
                'part': oPart,
                'customer_asset_tagging': True if aLine[3] == 'Y' else False
                if aLine[3] == 'N' else None,
                'customer_asset': True if aLine[4] == 'Y' else False if
                aLine[4] == 'N' else None
            }

            # Create new entry of gete matching entry if it already exists
            (oNewCustInfo, bCreated) = CustomerPartInfo.objects.get_or_create(
                **dNewCustInfo)

            # Set newest entry as active (deactivating all other entries for the
            # same part) and priority (this means file uploads cannot overwrite
            # this entry)
            oNewCustInfo.active = True
            oNewCustInfo.priority = True
            oNewCustInfo.save()

            # Update any ConfigLine objects that are affected by this update
            for oConfigLine in ConfigLine.objects.filter(
                    config__header__configuration_status__name__startswith='In Process',
                    config__header__customer_unit=oCustomer,
                    part__base=oPart):
                oConfigLine.customer_asset = "Y" if \
                    oNewCustInfo.customer_asset else "N" if \
                    oNewCustInfo.customer_asset is False else None
                oConfigLine.customer_asset_tagging = "Y" if \
                    oNewCustInfo.customer_asset_tagging else "N" if \
                    oNewCustInfo.customer_asset_tagging is False else None
                oConfigLine.customer_number = oNewCustInfo.customer_number
                oConfigLine.sec_customer_number = \
                    oNewCustInfo.second_customer_number
                oConfigLine.save()
        # end for

        dContext['data'] = json.dumps(aData)
        dContext['selectedCust'] = oCustomer

    return Default(oRequest, 'BoMConfig/customer_audit.html', dContext)
# end def


def CustomerAuditTableValidate(oRequest):
    """
    View to validate rows in the view above.  When the table is not in overwrite
    mode, the function will highlight which users entries do not match the data
    stores in the database.  When the table is in overwrite mode, this function
    will highlight which fields in the database will be changed.
    :param oRequest: Django HTTP request object
    :return: JSONResponse containing data and validation information for output
    """
    received_data = json.loads(oRequest.POST['changed_data'])
    customer = oRequest.POST['customer']
    overwrite = StrToBool(str(oRequest.POST.get('override', False)))

    response_data = {
        'table_data': {},
        'table_info': {},
    }

    for key in received_data.keys():
        # Create a dictionary to store what data will be displayed in the output
        # table, and a dictionary to store the validation data per field
        #
        # In 'table_info', True means the value provided matches the data
        # stored, False means it does not, and None means the tool is not
        # concerned about a match or the data is not stored in the database
        response_data['table_data'][key] = [None] * 5
        response_data['table_info'][key] = [None] * 5

        part = None
        cust_info = None

        # Try to find an entry which matches the Part number AND customer number
        # entered (if any)
        try:
            part = PartBase.objects.get(product_number=received_data[key][0])
            cust_info = part.customerpartinfo_set.get(customer__id=customer,
                                                      active=True)
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

        # If no CustomerPartInfo entry exists for this part, try to find an
        # entry that uses the customer number entered (if any).
        if not cust_info:
            try:
                cust_info = CustomerPartInfo.objects.get(
                    customer_number=received_data[key][1],
                    customer__id=customer,
                    active=True
                )
                response_data['table_data'][key][0] = \
                    cust_info.part.product_number

            except (CustomerPartInfo.DoesNotExist, ValueError):
                response_data['table_data'][key][1] = received_data[key][1]
                response_data['table_info'][key][1] = None
                response_data['table_data'][key][2] = received_data[key][2]
                response_data['table_info'][key][2] = None
            # end try
        # end if

        # If a CustomerPartInfo entry has been found
        if cust_info:
            # If we are overwriting the entry, check which fields already match
            # and which are going to change. Each field will be populated by the
            # data provided, or by the data stored in the database if no data
            # was provided.
            if overwrite:
                response_data['table_data'][key][0] = \
                    received_data[key][0] or cust_info.part.product_number
                response_data['table_info'][key][0] = \
                    True if cust_info.part.product_number == \
                    received_data[key][0] or not received_data[key][0] \
                    else None

                response_data['table_data'][key][1] = \
                    received_data[key][1] or cust_info.customer_number
                response_data['table_info'][key][1] = \
                    True if cust_info.customer_number == received_data[key][1] \
                    or not received_data[key][1] else None

                response_data['table_data'][key][2] = received_data[key][2]
                response_data['table_info'][key][2] = \
                    True if cust_info.second_customer_number == \
                    (received_data[key][2] or None) else None

                response_data['table_data'][key][3] = received_data[key][3]
                response_data['table_data'][key][4] = received_data[key][4]

                if cust_info.customer_asset_tagging is not None and \
                        received_data[key][3]:
                    response_data['table_info'][key][3] = True if bool(
                        cust_info.customer_asset_tagging == StrToBool(
                            received_data[key][3], "")) else None
                elif cust_info.customer_asset_tagging is not None and not \
                        received_data[key][3]:
                    response_data['table_info'][key][3] = None
                elif cust_info.customer_asset_tagging is None:
                    response_data['table_info'][key][3] = None

                if cust_info.customer_asset is not None and \
                        received_data[key][4]:
                    response_data['table_info'][key][4] = True if bool(
                        cust_info.customer_asset == StrToBool(
                            received_data[key][4], "")) else None
                elif cust_info.customer_asset is not None and not \
                        received_data[key][4]:
                    response_data['table_info'][key][4] = None
                elif cust_info.customer_asset is None:
                    response_data['table_info'][key][4] = None

            # If we aren't overwriting the entry, check which fields already
            # match and which do not. Each field will be populated by the
            # data provided, or by the data stored in the database if no data
            # was provided.
            else:
                response_data['table_data'][key][0] = \
                    cust_info.part.product_number
                response_data['table_info'][key][0] = bool(
                    cust_info.part.product_number == received_data[key][0])

                response_data['table_data'][key][1] = cust_info.customer_number
                response_data['table_info'][key][1] = bool(
                    cust_info.customer_number == received_data[key][1])

                response_data['table_data'][key][2] = \
                    cust_info.second_customer_number
                response_data['table_info'][key][2] = bool(
                    cust_info.second_customer_number == (
                        received_data[key][2] or None))

                response_data['table_data'][key][3] = "Y" if \
                    cust_info.customer_asset_tagging else "N" if \
                    cust_info.customer_asset_tagging is False else ' '
                response_data['table_data'][key][4] = "Y" if \
                    cust_info.customer_asset else "N" if \
                    cust_info.customer_asset is False else ' '

                if cust_info.customer_asset_tagging is not None:
                    if received_data[key][3]:
                        response_data['table_info'][key][3] = bool(
                            cust_info.customer_asset_tagging == StrToBool(
                                received_data[key][3], ""))
                    elif not received_data[key][3]:
                        response_data['table_info'][key][3] = False
                else:
                    if not received_data[key][3]:
                        response_data['table_info'][key][3] = True
                    else:
                        response_data['table_info'][key][3] = False

                if cust_info.customer_asset is not None:
                    if received_data[key][4]:
                        response_data['table_info'][key][4] = bool(
                            cust_info.customer_asset == StrToBool(
                                received_data[key][4], ""))
                    elif not received_data[key][4]:
                        response_data['table_info'][key][4] = False
                else:
                    if not received_data[key][4]:
                        response_data['table_info'][key][4] = True
                    else:
                        response_data['table_info'][key][4] = False

        # If no CustomerPartInfo entry is found, then there is nothing to
        # validate against, so provide no validation feedback
        else:
            response_data['table_data'][key][1] = received_data[key][1]
            response_data['table_data'][key][2] = received_data[key][2]
            response_data['table_data'][key][3] = received_data[key][3]
            response_data['table_data'][key][4] = received_data[key][4]
            if response_data['table_data'][key][1] and \
                    response_data['table_info'][key][1] is None:
                response_data['table_data'][key][3] = response_data[
                    'table_data'][key][3]
                response_data['table_info'][key][3] = None
                response_data['table_data'][key][4] = response_data[
                    'table_data'][key][4]
                response_data['table_info'][key][4] = None
        # end if

    return JsonResponse(response_data)
# end def


@login_required
def CustomerAuditUpload(oRequest):
    """
    View to provide users with a means to upload customer Part Number documents
    for creating new CustomerPartInfo mapping objects.
    :param oRequest:
    :return:
    """
    # S-06174- Customer Audit restrict view
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    dContext = {'customer_list': aAvailableCU}

    # If POSTing an upload file and file type
    if oRequest.POST:
        try:
            # Attempt to process the uploaded file
            bErrors = ProcessUpload(
                oRequest.FILES['file'],
                int(oRequest.POST['file_type']),
                REF_CUSTOMER.objects.get(id=oRequest.POST['customer']),
                oRequest.user
            )
            status_message = 'Upload completed.' + \
                             (' An email has been sent detailing discrepancies.'
                              if bErrors else '')
            status_error = False
        except TypeError:
            status_message = \
                "Invalid file provided or file does not match selected type."
            status_error = True
        except ValueError:
            status_message = 'Invalid file type selected.'
            status_error = True

        dContext['status_message'] = status_message
        dContext['status_error'] = status_error

    return Default(oRequest, sTemplate='BoMConfig/customer_audit_upload.html',
                   dContext=dContext)
# end def

def ProcessUpload(oStream, iFileType, oCustomer, oUser):
    """
    Function to parse information from a data stream provided in oStream into
    CustomerPartInfo objects.  There are currently two supported file types.
    :param oStream: Data stream (filestream, etc.) containing uploaded
    information
    :param iFileType: Integer indicating type of file uploaded
    :param oCustomer: REF_CUSTOMER object used to create CustomerPartInfo object
    :param oUser: User object creating entries
    :return: Boolean indicating if any erroneous data was encountered
    """
    # S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:-
    # Based on customer and file type, determine what sheet name and column titles are
    # expected in the file
    if str(oCustomer) == 'MTW':
        if iFileType == 2:
            sSheetName = "FAA Y Report"
            aColumns = [[1, 6, 5, 2, 4, 3]]
            aHeaders = ['FFA Article', 'ZENG Article', 'Serialization', 'MPN',
                        'Article Description',  'Vendor Article Number']
        else:
            raise ValueError('Invalid file type')
    else:

        if iFileType == 1:
            sSheetName = "Ericsson BOM Report"
            aColumns = [[2, 3, 4, 5, 6, 8], [9, 10, 11, 12, 13, 16]]
            aHeaders = ['Oracle Parent', 'Parent Barcode', 'Parent EADC',
                        'Parent MPN', 'Parent Description', 'Parent Status',
                        'Oracle Child', 'Child Barcode', 'Child EADC', 'Child MPN',
                        'Child Description', 'Child Item Status']
        elif iFileType == 2:
            sSheetName = "Ericsson IM"
            aColumns = [[3, 6, 10, 12, 5, 8]]
            aHeaders = ['Item Number', 'Barcode', 'External Download Code',
                        'Manufacturer Part Number', 'Item Description',
                        'Status Code']
        else:
            raise ValueError('Invalid file type')

    # Attempt to open the .xls(x) file
    try:
        oFile = openpyxl.load_workbook(oStream, read_only=True)
    except (IOError, utils.exceptions.InvalidFileException, zipfile.BadZipFile):
        raise TypeError('Invalid file')

    # Attempt to find exact match for expected sheet name (this was needed due
    # to extra spaces being present in file, which we cannot control)
    for sName in oFile.get_sheet_names():
        if sSheetName in sName:
            sSheetName = sName
            break
    # Attempt to retrieve the sheet object of the file
    try:
        oDataSheet = oFile.get_sheet_by_name(sSheetName)
    except KeyError:
        raise TypeError('Invalid sheet name')

    aSheetData = oDataSheet.rows

    # Determine if expected headers match what is in the file, to ensure we use
    # the correct data
    aFileHeaders = next(aSheetData, list())
    tDesiredHeaders = list(str(aFileHeaders[i-1].value).strip() for i in
                           itertools.chain.from_iterable(aColumns))
    if tDesiredHeaders != aHeaders:
        raise TypeError('Header line mismatch')

    aExtractedData = []

    # S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:-
    # Added the if condition for MTW customer
    # Parse out relevant data from file
    if str(oCustomer) == 'MTW':
        for row in aSheetData:
            for aDataGroup in aColumns:
                aTemp = []
                for (idx, iCol) in enumerate(aDataGroup):
                    oData = row[iCol - 1].value
                    if idx == 0 and oData:  # Customer Part number
                        oData = oData
                    elif idx == 1:  # Second Customer Part Number
                        oData = oData
                    elif idx == 2:  # Customer asset
                        if oData and oData.strip() =='EAM1':
                            oData = True
                        elif oData is not None:
                            oData = False
                        else:
                            oData = None
                    elif idx == 3 and oData:  # Ericsson part number/MPN
                        # Convert integer-like part numbers (Part number containing
                        # only digits must have '/' appended)
                        oData = oData
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
    else:                           # For AT&T
        for row in aSheetData:
            for aDataGroup in aColumns:
                aTemp = []
                for (idx, iCol) in enumerate(aDataGroup):
                    oData = row[iCol - 1].value
                    if idx == 0 and oData:  # Customer Part number
                        oData = oData.upper()
                    elif idx == 1:  # Customer asset tagging
                        if oData and oData.strip() == 'Y':
                            oData = True
                        elif oData and oData.strip() == 'N':
                            oData = False
                        else:
                            oData = None
                    elif idx == 2:  # Customer asset
                        if oData and oData.strip() in ('E', 'C'):
                            oData = True
                        elif oData is not None:
                            oData = False
                        else:
                            oData = None
                    elif idx == 3 and oData:  # Ericsson part number
                        # Convert integer-like part numbers (Part number containing
                        # only digits must have '/' appended)
                        oData = oData
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

    # Remove duplicate entries
    aExtractedData = list(set(aExtractedData))

    # aExtractedData will be sorted by Status: Inactive/Obsolete, Active, Phased
    # This helps when uploading records.  Since active records will be processed
    # first, we can assume that any conflicts experienced by phased records are
    # not critical errors
    aExtractedData.sort(key=lambda x: 1 if x[5] in ['Inactive', 'Obsolete'] else
                        3 if 'Phase' in x[5] else 2 if 'Active' in x[5] else 0)

    aDuplicateMPN = []
    aDuplicateCust = []
    aDuplicateTag = []
    aDuplicateInactive = []
    aInvalidEntries = []
    aDuplicateSecCust = []

    bErrorsLogged = False

# S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:- Added if and else block for each customer (AT&T & MTW)
# for creating the discrepency arrays

    if str(oCustomer) == 'AT&T':
        # Add/Remove each part
        for tPart in aExtractedData:
            if 'VARIOUS' in tPart[3].upper() or 'UNKNOWN' in tPart[3].upper() or \
                            str(tPart[3]).upper().strip() == 'NONE':
                aInvalidEntries.append(tPart)
                continue

            if str(tPart[0]).upper().strip() == 'NONE':
                aInvalidEntries.append(tPart)
                continue

            if 'DUPLICATE ITEM USE' in str(tPart[4]).upper():
                continue

            (oPart, _) = PartBase.objects.get_or_create(
                product_number=tPart[3], defaults={'unit_of_measure': 'PC'})

            # Determine if Part should be deactivated/added as inactive (Status is
            # "Inactive" or "Obsolete" or 'Discontinued use' in description)
            if tPart[5] in ['Inactive', 'Obsolete'] or 'DISCONTINUED' in \
                    str(tPart[4]).upper():

                (oMap, bCreated) = CustomerPartInfo.objects.get_or_create(
                    part=oPart,
                    customer=oCustomer,
                    customer_number=tPart[0],
                    customer_asset=tPart[2],
                    customer_asset_tagging=tPart[1]
                )
                if not bCreated and not oMap.priority:
                    oMap.active = False
                    oMap.save()
                elif not bCreated and oMap.priority:
                    aDuplicateInactive.append(tPart)
            else:

                # Check if any mappings exists with current info
                # Attempt to find an entry that matches exactly
                try:
            # D-03939:Customer Upload functionality returns error: changed 'get' to 'filter' to get the multiple records of the same combination
                    oExactMap = CustomerPartInfo.objects.filter(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        customer_asset_tagging=tPart[1]
                    )
            # D-03939:Customer Upload functionality returns error: Added if else block to check the whether length is more than 1 or not
                    if len(oExactMap) > 1:
                  # D-03939:Customer Upload functionality returns error: Added below if block to check if active record is present in the sheet or not
                        if "Active" in tPart[5] :
                            oExactMap = CustomerPartInfo.objects.get(
                                part=oPart,
                                customer=oCustomer,
                                customer_number=tPart[0],
                                customer_asset=tPart[2],
                                customer_asset_tagging=tPart[1],
                                active=True
                            )
                    else:
                        oExactMap = CustomerPartInfo.objects.get(
                            part=oPart,
                            customer=oCustomer,
                            customer_number=tPart[0],
                            customer_asset=tPart[2],
                            customer_asset_tagging=tPart[1]
                        )
                except CustomerPartInfo.DoesNotExist:
                    oExactMap = None
                # end try

                # Attempt to find an entry that only matches part number
                try:
                    oPartMap = CustomerPartInfo.objects.get(
                        part=oPart, customer=oCustomer, active=True)
                except CustomerPartInfo.DoesNotExist:
                    oPartMap = None
                # end try

                # Attempt to find an entry that only matches customer part number
                try:
                    oCustMap = CustomerPartInfo.objects.get(
                        customer_number=tPart[0], customer=oCustomer, active=True)
                except CustomerPartInfo.DoesNotExist:
                    oCustMap = None
                # end try

                # If there is an exact match, and its status already matches the
                # line data status, nothing further is required
                if oExactMap and (
                            (oExactMap.active and "Active" in tPart[5]) or
                            (not oExactMap.active and "Phase" in tPart[5])):
                    continue

                # If there is an exact match, and its status does not match the line
                # data status, the remaining checks also need to occur, to ensure we
                # do not overwrite protected data. We should log an error if this
                # line data is attempting to overwrite protected (priority)
                # information
                elif oExactMap and (
                            (oExactMap.active and oExactMap.priority and "Phase" in
                                tPart[5]) or
                            (not oExactMap.active and oExactMap.priority and
                                     "Active" in tPart[5])):
                    aDuplicateInactive.append(tPart)

                    continue

                # If the Part match and Customer number match are the same, then
                # there is really only one match, the only difference between the
                # match and line record is the customer asset information
                elif oPartMap and oCustMap and oPartMap == oCustMap:
                    # If the line record is "Phase NTW" or "Phase RCL", don't log
                    # the error. oMap will either be a new inactive record, or an
                    # existing record (possibly active). Leave the record as-is,
                    # because it might be newer information. Log the error if the
                    # record is protected and the line data is attempting to change
                    # that
                    if oPartMap.priority and 'Active' in tPart[5]:
                        aDuplicateTag.append(tPart)

                    CustomerPartInfo.objects.get_or_create(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        customer_asset_tagging=tPart[1]
                    )

                    if 'Phase' in tPart[5] or oPartMap.priority:
                        continue
                # end if

                # If the MPN and Customer Number each have their own separate active
                # matches, log the errors
                elif oPartMap or oCustMap:
                    # If the line record is "Phase NTW" or "Phase RCL", don't log
                    # the error. oMap will either be a new inactive record, or an
                    # existing record (possibly active).
                    # If it is inactive, that is fine since the part is phased. If
                    # it is active, just leave it active since it might be newer
                    # information than what is provided by upload
                    # Log the error if the line data is attempting to overwrite
                    # protected information
                    if oPartMap and oPartMap.priority and 'Active' in tPart[5]:
                        aDuplicateMPN.append(tPart)

                    if oCustMap and oCustMap.priority and 'Active' in tPart[5]:
                        aDuplicateCust.append(tPart)

                    CustomerPartInfo.objects.get_or_create(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        customer_asset_tagging=tPart[1]
                    )

                    if 'Phase' in tPart[5] or (oPartMap and oPartMap.priority) or \
                            (oCustMap and oCustMap.priority):
                        continue
                # end if

                # Only line records that do not conflict with existing protected
                # data will have made it this far, so it is fine to make the record
                # active in the database.
                (oMap, _) = CustomerPartInfo.objects.get_or_create(
                    part=oPart,
                    customer=oCustomer,
                    customer_number=tPart[0],
                    customer_asset=tPart[2],
                    customer_asset_tagging=tPart[1]
                )

                if "Active" in tPart[5]:
                    oMap.active = True
                    oMap.save()
        # end if
        # end for
    else:
        # Add/Remove each part
        for tPart in aExtractedData:
            if 'VARIOUS' in tPart[3].upper() or 'UNKNOWN' in tPart[3].upper() or \
                            str(tPart[3]).upper().strip() == 'NONE' or tPart[3] == '':
                aInvalidEntries.append(tPart)
                continue
            if str(tPart[0]).upper().strip() == 'NONE':
                aInvalidEntries.append(tPart)
                continue
            if 'DUPLICATE ITEM USE' in str(tPart[4]).upper():
                continue

            (oPart, _) = PartBase.objects.get_or_create(
                product_number=tPart[3], defaults={'unit_of_measure': 'PC'})

            # Determine if Part should be deactivated/added as inactive (Status is
            # "Inactive" or "Obsolete" or 'Discontinued use' in description)
            if tPart[5] in ['Inactive', 'Obsolete'] or 'DISCONTINUED' in \
                    str(tPart[4]).upper():
                (oMap, bCreated) = CustomerPartInfo.objects.get_or_create(
                    part=oPart,
                    customer=oCustomer,
                    customer_number=tPart[0],
                    customer_asset=tPart[2],
                    second_customer_number=tPart[1]
                )
                if not bCreated and not oMap.priority:
                    oMap.active = False
                    oMap.save()
                elif not bCreated and oMap.priority:
                    aDuplicateInactive.append(tPart)
            else:
                # Check if any mappings exists with current info
                # Attempt to find an entry that matches exactly
                try:
# S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:-changed 'get' to 'filter' to get the multiple records of the same combination
                    oExactMap = CustomerPartInfo.objects.filter(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        second_customer_number=tPart[1]
                    )
# S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:-Added if else block to check the whether length is more than 1 or not
                    if len(oExactMap) > 1:
                        oExactMap = CustomerPartInfo.objects.get(
                            part=oPart,
                            customer=oCustomer,
                            customer_number=tPart[0],
                            customer_asset=tPart[2],
                            second_customer_number=tPart[1],
                            active=True
                        )
                    else:
                        oExactMap = CustomerPartInfo.objects.get(
                            part=oPart,
                            customer=oCustomer,
                            customer_number=tPart[0],
                            customer_asset=tPart[2],
                            second_customer_number=tPart[1]
                        )
                except CustomerPartInfo.DoesNotExist:
                    oExactMap = None
                # end try

                # Attempt to find an entry that only matches part number
                try:
                    oPartMap = CustomerPartInfo.objects.get(
                        part=oPart, customer=oCustomer, active=True)
                except CustomerPartInfo.DoesNotExist:
                    oPartMap = None
                # end try
                # Attempt to find an entry that only matches customer part number
                try:
                    oCustMap = CustomerPartInfo.objects.get(
                        customer_number=tPart[0], customer=oCustomer, active=True)
                except CustomerPartInfo.DoesNotExist:
                    oCustMap = None
                # end try

                # Attempt to find an entry that only matches second customer part number
                try:
                    if tPart[1]:
                        oSecCustMap = CustomerPartInfo.objects.get(
                            customer_number=tPart[0], second_customer_number=tPart[1], customer=oCustomer, active=True)
                except CustomerPartInfo.DoesNotExist:
                    oSecCustMap = None
                    # end try

                # If there is an exact match, and its status already matches the
                # line data status, nothing further is required
                if oExactMap and ((oExactMap.active) or (not oExactMap.active)):
                    continue

                # If there is an exact match, and its status does not match the line
                # data status, the remaining checks also need to occur, to ensure we
                # do not overwrite protected data. We should log an error if this
                # line data is attempting to overwrite protected (priority)
                # information
                elif oExactMap and (
                    (oExactMap.active and oExactMap.priority) or
                    (not oExactMap.active and oExactMap.priority)):
                    aDuplicateInactive.append(tPart)
                    continue

                # If the Part match and Customer number match are the same, then
                # there is really only one match, the only difference between the
                # match and line record is the customer asset information
                elif oPartMap and oCustMap and oPartMap == oCustMap:
                    # If the line record is "Phase NTW" or "Phase RCL", don't log
                    # the error. oMap will either be a new inactive record, or an
                    # existing record (possibly active). Leave the record as-is,
                    # because it might be newer information. Log the error if the
                    # record is protected and the line data is attempting to change
                    # that
                    # if oPartMap.priority and 'Active' in tPart[5]:
                    if oPartMap.priority:
                        aDuplicateTag.append(tPart)

                    CustomerPartInfo.objects.get_or_create(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        second_customer_number=tPart[1]
                    )

                    # if 'Phase' in tPart[5] or oPartMap.priority:
                    if oPartMap.priority:
                         continue
                # end if

                # If the MPN and Customer Number each have their own separate active
                # matches, log the errors
                elif oPartMap or oCustMap:
                    # If the line record is "Phase NTW" or "Phase RCL", don't log
                    # the error. oMap will either be a new inactive record, or an
                    # existing record (possibly active).
                    # If it is inactive, that is fine since the part is phased. If
                    # it is active, just leave it active since it might be newer
                    # information than what is provided by upload
                    # Log the error if the line data is attempting to overwrite
                    # protected information
                    if oPartMap and oPartMap.priority:
                        aDuplicateMPN.append(tPart)

                    if oCustMap and oCustMap.priority:
                        aDuplicateCust.append(tPart)

                    CustomerPartInfo.objects.get_or_create(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        second_customer_number=tPart[1]
                    )

                    if (oPartMap and oPartMap.priority) or \
                            (oCustMap and oCustMap.priority):
                        continue
                # original end if

                # If the MPN and Second Customer Number each have their own separate active
                # matches, log the errors
                elif oPartMap or oSecCustMap:
                    # If the line record is "Phase NTW" or "Phase RCL", don't log
                    # the error. oMap will either be a new inactive record, or an
                    # existing record (possibly active).
                    # If it is inactive, that is fine since the part is phased. If
                    # it is active, just leave it active since it might be newer
                    # information than what is provided by upload
                    # Log the error if the line data is attempting to overwrite
                    # protected information
                    if oPartMap and oPartMap.priority:
                        aDuplicateMPN.append(tPart)

                    if oSecCustMap and oSecCustMap.priority:
                        aDuplicateSecCust.append(tPart)

                    CustomerPartInfo.objects.get_or_create(
                        part=oPart,
                        customer=oCustomer,
                        customer_number=tPart[0],
                        customer_asset=tPart[2],
                        second_customer_number=tPart[1]
                    )

                    if (oPartMap and oPartMap.priority) or \
                            (oSecCustMap and oSecCustMap.priority):
                        continue
                # end if

                # Only line records that do not conflict with existing protected
                # data will have made it this far, so it is fine to make the record
                # active in the database.
                (oMap, _) = CustomerPartInfo.objects.get_or_create(
                    part=oPart,
                    customer=oCustomer,
                    customer_number=tPart[0],
                    customer_asset=tPart[2],
                    second_customer_number=tPart[1]
                )

                oMap.active = True
                oMap.save()
            # end if
            # end for

    # if any errors were found, send an email detailing the errors
    if aDuplicateCust or aDuplicateMPN or aDuplicateTag or aDuplicateInactive \
            or aInvalidEntries:
        bErrorsLogged = True
        if str(oCustomer) == 'AT&T':
            aDuplicateInactive.sort(key=lambda x: x[3])
            aDuplicateCust.sort(key=lambda x: x[3])
            aDuplicateTag.sort(key=lambda x: x[3])
            aDuplicateMPN.sort(key=lambda x: x[3])
            aInvalidEntries.sort(key=lambda x: x[0])

 # S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:- Added seccust and customer attribute in the data block to be sent
 # to GenerateEmailMessage and also the email body
       # Send discrepancy email
# S-10576: Change the header of the tool to ACC :- Changed the tool name from pcbm to acc
        subject = 'Customer Part Number upload discrepancies'
        from_email = 'acc.admin@ericsson.com'
        text_message = GenerateEmailMessage(
            **{
                'cust': aDuplicateCust,
                'seccust': aDuplicateSecCust,
                'mpn': aDuplicateMPN,
                'tag': aDuplicateTag,
                'inactive': aDuplicateInactive,
                'user': oUser,
                'invalid': aInvalidEntries,
                'filename': oStream.name,
                'doc_type': iFileType,
                'customer': str(oCustomer)
            }
        )
        html_message = render_to_string(
            'BoMConfig/customer_audit_email.html',
            {
                'cust': aDuplicateCust,
                'seccust' : aDuplicateSecCust,
                'mpn': aDuplicateMPN,
                'tag': aDuplicateTag,
                'inactive': aDuplicateInactive,
                'user': oUser,
                'invalid': aInvalidEntries,
                'filename': oStream.name,
                'type': iFileType,
                'customer': str(oCustomer)
            }
        )
        oUser.email_user(subject=subject, message=text_message,
                         from_email=from_email, html_message=html_message)
    # end if

    return bErrorsLogged
# end def


def GenerateEmailMessage(cust=(), seccust=(), mpn=(), tag=(), inactive=(), invalid=(),
                         user=None, filename='', doc_type=0, customer=''):
    """
    Function to generate a plain-text error message detailing any errors
    encountered during file upload
    :param cust: List of entries found that duplicate an existing customer part
    number
    :param mpn: List of entries found that duplicate an existing E/// part
    number
    :param tag: List of entries found that did not match existing asset statuses
    :param inactive: List of entries that did not match status of existing
    entries
    :param invalid: List of entries that did not contain valid part information
    :param user: User object of user uploading file
    :param filename: String containing name of file uploaded
    :param doc_type: Integer indicating file type uploaded
    :return: String containing formatted plain-text error message
    """
    temp = ('Hello {},\n\nThe following errors were found '
            'while uploading {} ({}):\n\n').format(
        user.first_name, filename,
        'BOM Report' if doc_type == 1 else 'IM Report' if doc_type == 2 else ''
    )

    # S-08946: Add USCC SAP (MTW as of now) download format to upload for validation:- Added below if else block to build the
    # respective titles and content for discrepancy email

    # aErrorLists = [inactive, tag, mpn, cust, invalid]
    if customer == 'AT&T':
        aErrorLists = [inactive, tag, mpn, cust, invalid]
        aTableTitles = ['Attempted to change priority Customer Number/MPN mapping',
                        ('Matches priority Customer Number/MPN mapping with '
                         'different customer asset information'),
                        'MPN priority mapped to different Customer number',
                        'Customer Number priority mapped to different MPN',
                        'Customer Number and/or MPN is invalid']

        for (idx, maplist) in enumerate(aErrorLists):
            if maplist:
                temp += aTableTitles[idx] + '\n'

                for mapping in maplist:
                    temp += '\t' + mapping[0] + ' / ' + mapping[3] + ' / ' + \
                            ('Y' if mapping[1] else "N" if mapping[1] is False else
                                "(None)") + ' / ' + \
                            ('Y' if mapping[2] else "N" if mapping[2] is False
                                else "(None)") + '\n'
                temp += '\n'
            # end if
        # end for
    else:
        aErrorLists = [inactive, tag, mpn, cust, seccust, invalid]
        aTableTitles = ['Attempted to change priority Customer Number/MPN mapping',
                        'Matches priority Customer Number/MPN mapping with different customer asset information – ',
                        ('MPN priority mapped to different Customer number'),
                        'Customer Number priority mapped to different MPN',
                        'MPN priority mapped to different Second Customer number',
                        'Customer Number and/or MPN is invalid'
                        ]

        for (idx, maplist) in enumerate(aErrorLists):
            if maplist:
                temp += aTableTitles[idx] + '\n'
                for mapping in maplist:
                    temp += '\t' + 'mapping[0]' + ' / ' + 'mapping[3]' + ' / ' + \
                            'mapping[1]' + ' / ' + 'mapping[2]' + '\n'
                temp += '\n'
            # end if
        # end for

    return temp
# end def
