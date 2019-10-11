"""
View related to viewing, editing, and downloading pricing information
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.loader import render_to_string
from BoMConfig.models import Header, Configuration, ConfigLine, PartBase, \
    LinePricing, REF_CUSTOMER, SecurityPermission, REF_SPUD, PricingObject, \
    REF_TECHNOLOGY, HeaderTimeTracker,User_Customer
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue, StrToBool
# D-07324: Unit Price upload adjustment:
from datetime import datetime,date
import openpyxl
from openpyxl import utils
import zipfile
import json
import datetime
import itertools


@login_required
def PartPricing(oRequest):
    """
    View for viewing and editing pricing information for individual parts
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    # Determine if user has permission to interact with pricing information
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))
    # S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab)
    errorfound=False
    
    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    dContext = {
        'partlines': []
    }

    status_message = ''

    # If POSTing data
    if oRequest.method == 'POST' and oRequest.POST:
        # Get the part number
        sPartNumber = oRequest.POST.get('part', None)

        if sPartNumber:
            sPartNumber = sPartNumber.upper()
            dContext['part'] = sPartNumber
            try:
                # Retrieve PartBase associated to part number provided
                oPart = PartBase.objects.get(product_number__iexact=sPartNumber)

                # Test if the part number is actually a title for a Header
                if Header.objects.filter(
                        configuration_designation=oPart.product_number):
                    raise Header.DoesNotExist()

                # If the request action is 'save' (instead of 'search')
                if oRequest.POST.get('action') == 'save':
                    # Use 'initial', which is set after searching. Do not use
                    # 'part' because the user could have changed the value
                    sPartNumber = oRequest.POST.get('initial', None)
                    oPart = PartBase.objects.get(
                        product_number__iexact=sPartNumber)

                    # Retrieve data to save
                    if oRequest.POST.get('data_form') is not None:
                        aDataToSave = json.loads(oRequest.POST.get('data_form'))
                    else:
                        aDataToSave = None
                        pass

                    if aDataToSave is not None:
                        for aRowToSave in aDataToSave:
                        # Skip empty rows
                            if not any(aRowToSave):
                                continue

                            # Retrieve PricingObject that matches the data provided,
                            # if it exists
                            try:
        # S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab): added valid_from_date to check
        #  in filtering to get exact match
                                oCurrentPriceObj = PricingObject.objects.get(
                                    part__product_number__iexact=aRowToSave[0] or
                                                                 oRequest.POST.get('initial', None),
                                    customer__name=aRowToSave[1],# D-04625: New row populated when editing data in Unit Price Management removed if aRowToSave[1] in aAvailableCU else None
                                    # sold_to=aRowToSave[2] if aRowToSave[2] not in
                                    #                          ('', '(None)') else None, # D-07148: Demo on S-12676: Account for valid to and valid from dates in Unit Price Mgmt (in Pricing tab):
                                    # commented out.Sold-to should have no effect on rules in adding a different price.

                                    spud__name=aRowToSave[3] if aRowToSave[3] not in
                                                                ('', '(None)') else None,
                                    valid_from_date=datetime.datetime.strptime(
                                        aRowToSave[5],
                                     '%m/%d/%Y'
                                    ).date() if aRowToSave[5] else None,
                                    is_current_active=True
                                )
                            except PricingObject.DoesNotExist:
                                oCurrentPriceObj = None
                    # D-07148: Demo on S-12676: Account for valid to and valid from dates in Unit Price Mgmt (in Pricing tab):
                    # For edit/new row entry:To check if valid-to entered is same as of previous record then error,
                    # if not update existing valid-to to entered date. Or raise the error if not satisfied.
                            if oCurrentPriceObj and aRowToSave[6] not in ('', '(None)'):
                                if datetime.datetime.strptime(aRowToSave[6],'%m/%d/%Y').date() == oCurrentPriceObj.valid_to_date:
                                    oCurrentPriceObj.is_current_active = True
                                    errorfound = True
                                    oCurrentPriceObj.save()
                                    break
                                elif (datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date() == oCurrentPriceObj.valid_from_date and \
                                datetime.datetime.strptime(aRowToSave[6],'%m/%d/%Y').date() != oCurrentPriceObj.valid_to_date and \
                                oCurrentPriceObj.unit_price != float(aRowToSave[4])):
                                    oCurrentPriceObj.is_current_active = True
                                    errorfound = True
                                    oCurrentPriceObj.save()
                                    break
                                elif (datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date() == oCurrentPriceObj.valid_from_date and \
                                datetime.datetime.strptime(aRowToSave[6],'%m/%d/%Y').date() != oCurrentPriceObj.valid_to_date and \
                                oCurrentPriceObj.unit_price == float(aRowToSave[4])):
                                    oCurrentPriceObj.valid_to_date = datetime.datetime.strptime(
                                        aRowToSave[6], '%m/%d/%Y').date()
                                    oCurrentPriceObj.is_current_active = True
                                    oCurrentPriceObj.save()
                                    break
                                else:
                                    oCurrentPriceObj.valid_to_date = datetime.datetime.strptime(aRowToSave[6],
                                                                                                '%m/%d/%Y').date()
                                    oCurrentPriceObj.is_current_active = True
                                    oCurrentPriceObj.save()
                                    break

                            if not oCurrentPriceObj or \
                                    oCurrentPriceObj.unit_price != float(
                                        aRowToSave[4]) or \
                                    (aRowToSave[5] and
                                        datetime.datetime.strptime(aRowToSave[5],
                                                                   '%m/%d/%Y'
                                                                   ).date() !=
                                        oCurrentPriceObj.valid_from_date ) or \
                                    (aRowToSave[6] and datetime.datetime.strptime(
                                        aRowToSave[6], '%m/%d/%Y').date() !=
                                        oCurrentPriceObj.valid_to_date):
                                # Mark the previous match as 'inactive'
        # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(changed aRowToSave[7] to aRowToSave[6]
        # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.changed aRowToSave[6] to aRowToSave[5]
        # S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab):  added below conditions to check various combinations

                                if oCurrentPriceObj and oCurrentPriceObj.unit_price != float(aRowToSave[4]) and \
                                    (oCurrentPriceObj.valid_from_date == datetime.datetime.strptime( aRowToSave[5],'%m/%d/%Y').date()):
                                    oCurrentPriceObj.is_current_active = True
                                    errorfound = True
                                    oCurrentPriceObj.save()
                                    break

                                elif oCurrentPriceObj and (oCurrentPriceObj.valid_to_date != datetime.datetime.strptime(
                                    aRowToSave[6],'%m/%d/%Y').date() and oCurrentPriceObj.unit_price == float(aRowToSave[4])):
                                    oCurrentPriceObj.valid_to_date = datetime.datetime.strptime(
                                        aRowToSave[6], '%m/%d/%Y').date()
                                    oCurrentPriceObj.is_current_active = True
                                    oCurrentPriceObj.save()
                                elif oCurrentPriceObj and (oCurrentPriceObj.unit_price != float(aRowToSave[4]) and \
                                 oCurrentPriceObj.valid_to_date == datetime.datetime.strptime(aRowToSave[6],'%m/%d/%Y').date() and \
                                 oCurrentPriceObj.valid_from_date == datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date()):
                                    oCurrentPriceObj.is_current_active = True
                                    errorfound = True
                                    oCurrentPriceObj.save()

                                elif oCurrentPriceObj and (oCurrentPriceObj.unit_price != float(
                                    aRowToSave[4]) and oCurrentPriceObj.valid_to_date != datetime.datetime.strptime(aRowToSave[6],'%m/%d/%Y').date() and \
                                    oCurrentPriceObj.valid_from_date == datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date()):
                                    oCurrentPriceObj.is_current_active = True
                                    errorfound = True
                                    oCurrentPriceObj.save()
                                elif oCurrentPriceObj and (oCurrentPriceObj.unit_price == float(
                                    aRowToSave[4])and oCurrentPriceObj.valid_from_date == datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date()):
                                    oCurrentPriceObj.is_current_active = True
                                    oCurrentPriceObj.valid_to_date = datetime.datetime.strptime(
                                            aRowToSave[6],
                                            '%m/%d/%Y'
                                        ).date() if aRowToSave[6] else None,
                                    oCurrentPriceObj.save()
                                    break

                                # else:
                                #     oCurrentPriceObj.is_current_active = False
                                #     oCurrentPriceObj.valid_to_date = max(
                                #         datetime.date.today(),
                                #         datetime.datetime.strptime(
                                #             aRowToSave[5],
                                #             '%m/%d/%Y').date() if aRowToSave[5] else
                                #         datetime.date.today()
                                #     )
                                #     oCurrentPriceObj.save()
                                # Create a new PricingObject
           # S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab): added below conditions to check condition before adding in db.
                # D-07148: Demo on S-12676: Account for valid to and valid from dates in Unit Price Mgmt (in Pricing tab):
                # First it will check for list of combination present for CU+SPUD, if its not present it will create an entry else it will check for
                # valid-to-date, if entered data is greater than existing values then only it will enter data else flag error.
                                try:
                                    aPricingList = PricingObject.objects.filter(
                                        customer=REF_CUSTOMER.objects.get(
                                            name=aRowToSave[1]),
                                        part=PartBase.objects.get(
                                        product_number__iexact=aRowToSave[0] or oRequest.POST.get('initial', None)),
                                        is_current_active=True,
                                        spud=REF_SPUD.objects.get(name=aRowToSave[3]) if aRowToSave[3] not in ('(None)', '', None, 'null') else None)
                                    if len(aPricingList)==0:
                                        oNewPriceObj = PricingObject.objects.create(
                                            part=PartBase.objects.get(
                                                product_number__iexact=aRowToSave[0] or
                                                                       oRequest.POST.get('initial', None)),
                                            customer=REF_CUSTOMER.objects.get(
                                                name=aRowToSave[1]),
                                            sold_to=aRowToSave[2] if aRowToSave[2] not
                                                                     in ('(None)', None, '', 'null') else None,
                                            spud=REF_SPUD.objects.get(
                                                name=aRowToSave[3]) if aRowToSave[3] not
                                                                       in ('(None)', '', None, 'null') else None,
                                            # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
                                            # commented-out aRowToSave[4] and changed aRowToSave[5] to aRowToSave[7] -> aRowToSave[4] to aRowToSave[6]
                                            # technology=REF_TECHNOLOGY.objects.get(
                                            #     name=aRowToSave[4]) if aRowToSave[4] not
                                            # in ('(None)', '', None, 'null') else None,
                                            is_current_active=True,
                                            unit_price=aRowToSave[4],
                                            # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(changed valid_to_date to aRowToSave[7] and valid_from_date to aRowToSave[6]
                                            valid_from_date=datetime.datetime.strptime(
                                                aRowToSave[5],
                                                '%m/%d/%Y'
                                            ).date() if aRowToSave[5] else None,
                                            valid_to_date=datetime.datetime.strptime(
                                                aRowToSave[6],
                                                '%m/%d/%Y'
                                            ).date() if aRowToSave[6] else None,
                                            # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
                                            # commented-out aRowToSave[8] to aRowToSave[10] and changed aRowToSave[11] to aRowToSave[7] for comments
                                            # cutover_date=datetime.datetime.strptime(
                                            #     aRowToSave[8],
                                            #     '%m/%d/%Y'
                                            # ).date() if aRowToSave[8] else None,
                                            # price_erosion=eval(
                                            #     aRowToSave[9]
                                            # ) if aRowToSave[9] else False,
                                            # erosion_rate=float(
                                            #     aRowToSave[10]
                                            # ) if aRowToSave[10] else None,
                                            comments=aRowToSave[7],
                                            previous_pricing_object=oCurrentPriceObj
                                        )
                                    else:

                                        avalid_to_date= [
                                                oRow.valid_to_date
                                            for oRow in aPricingList
                                        ]
                                        max_date=max(d for d in avalid_to_date if isinstance(d, datetime.date))

                                        if datetime.datetime.strptime(aRowToSave[5],'%m/%d/%Y').date()< max_date:
                                            errorfound = True
                                            break
                                        else:
                                            oNewPriceObj = PricingObject.objects.create(
                                                part=PartBase.objects.get(
                                                    product_number__iexact=aRowToSave[0] or
                                                                           oRequest.POST.get('initial', None)),
                                                customer=REF_CUSTOMER.objects.get(
                                                    name=aRowToSave[1]),
                                                sold_to=aRowToSave[2] if aRowToSave[2] not
                                                                         in ('(None)', None, '', 'null') else None,
                                                spud=REF_SPUD.objects.get(
                                                    name=aRowToSave[3]) if aRowToSave[3] not
                                                                           in (
                                                                               '(None)', '', None, 'null') else None,
                                                # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
                                                # commented-out aRowToSave[4] and changed aRowToSave[5] to aRowToSave[7] -> aRowToSave[4] to aRowToSave[6]
                                                # technology=REF_TECHNOLOGY.objects.get(
                                                #     name=aRowToSave[4]) if aRowToSave[4] not
                                                # in ('(None)', '', None, 'null') else None,
                                                is_current_active=True,
                                                unit_price=aRowToSave[4],
                                                # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(changed valid_to_date to aRowToSave[7] and valid_from_date to aRowToSave[6]
                                                valid_from_date=datetime.datetime.strptime(
                                                    aRowToSave[5],
                                                    '%m/%d/%Y'
                                                ).date() if aRowToSave[5] else None,
                                                valid_to_date=datetime.datetime.strptime(
                                                    aRowToSave[6],
                                                    '%m/%d/%Y'
                                                ).date() if aRowToSave[6] else None,
                                                # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
                                                # commented-out aRowToSave[8] to aRowToSave[10] and changed aRowToSave[11] to aRowToSave[7] for comments
                                                # cutover_date=datetime.datetime.strptime(
                                                #     aRowToSave[8],
                                                #     '%m/%d/%Y'
                                                # ).date() if aRowToSave[8] else None,
                                                # price_erosion=eval(
                                                #     aRowToSave[9]
                                                # ) if aRowToSave[9] else False,
                                                # erosion_rate=float(
                                                #     aRowToSave[10]
                                                # ) if aRowToSave[10] else None,
                                                comments=aRowToSave[7]
                                                # previous_pricing_object=oCurrentPriceObj
                                            )

                                    # Update any configurations that are in-process
                                    # or pending approval by CPM to use the new
                                    # pricing information
                                    dFilterArgs = {
                                        'config__header__configuration_status__name__in':
                                            ('In Process', 'In Process/Pending'),
                                        'part__base':
                                            PartBase.objects.get(
                                                product_number__iexact=aRowToSave[0]
                                                or oRequest.POST.get(
                                                    'initial', None)),
                                        'config__header__customer_unit':
                                            REF_CUSTOMER.objects.get(
                                                name=aRowToSave[1])
                                    }

                                    for oConfigLine in ConfigLine.objects.filter(
                                            **dFilterArgs):
                                        if oConfigLine.config.header\
                                                .configuration_status.name != \
                                                'In Process' and HeaderTimeTracker\
                                                .approvals().index(
                                                oConfigLine.config.header
                                                        .latesttracker.next_approval
                                                ) > HeaderTimeTracker.approvals()\
                                                .index('cpm'):
                                            continue

                                        if not hasattr(oConfigLine, 'linepricing'):
                                            LinePricing.objects.create(
                                                {'config_line': oConfigLine})

                                        oLinePrice = oConfigLine.linepricing
                                        if PricingObject.getClosestMatch(
                                                oConfigLine) == oNewPriceObj:
                                            oLinePrice.pricing_object = oNewPriceObj
                                            oLinePrice.save()
                                            oConfigLine.config.save()
                                except Exception as ex:
                                    status_message = "ERROR: " + str(ex)

                            # Updating comments only will modify current PriceObject
                            # in-place
                # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. changed aRowToSave[11] to aRowToSave[7] for comments
                            elif oCurrentPriceObj and (
                                        oCurrentPriceObj.comments != aRowToSave[7]
                            ):
                                if oCurrentPriceObj.comments != aRowToSave[7]:
                                    oCurrentPriceObj.comments = aRowToSave[7]
                                oCurrentPriceObj.save()
                            # end if
                    # end for
                # end if

                # Retrieve all active PricingObjects that are associated to the
                # PartBase
                aPriceObjs = PricingObject.objects.filter(
                    part=oPart,
                    is_current_active=True).order_by('customer__name',
                                                      'spud__name', 'valid_from_date')

                # Create table data from list of objects
                for oPriceObj in aPriceObjs.filter(customer__in=aAvailableCU): # S-05923: Pricing - Restrict View to allowed CU's based on permissions added filter
            # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
                    dContext['partlines'].append([
                        oPriceObj.part.product_number,
                        oPriceObj.customer.name,
                        oPriceObj.sold_to or '(None)',
                        getattr(oPriceObj.spud, 'name', '(None)'),
    # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. commented technology
                        # getattr(oPriceObj.technology, 'name', '(None)'),
                        oPriceObj.unit_price or '',
                        # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers
                        oPriceObj.valid_from_date.strftime('%m/%d/%Y') if
                        oPriceObj.valid_from_date else '',  # Valid-from
                        oPriceObj.valid_to_date.strftime('%m/%d/%Y') if
                        oPriceObj.valid_to_date else '',  # Valid-To
    # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. commented below 3 fields
                        # oPriceObj.cutover_date.strftime('%m/%d/%Y') if
                        # oPriceObj.cutover_date else '',  # Cut-over
                        # str(oPriceObj.price_erosion),  # Erosion
                        # oPriceObj.erosion_rate or '',  # Erosion rate
                        oPriceObj.comments or '',  # Comments
                    ])

                dContext.update({
                    'customer_list': [
                        oCust.name for oCust in aAvailableCU], # S-05923: Pricing - Restrict View to allowed CU's based on permissions added aAvailableCU
                    'spud_list': [
                        oSpud.name for oSpud in REF_SPUD.objects.filter(is_inactive=0)]  # S-05909 : Edit drop down option for BoM Entry Header - SPUD: Added to filter dropdown data in pricing page
    # S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. commented-out tech-list
                    # 'tech_list': [
                    #     oTech.name for oTech in REF_TECHNOLOGY.objects.filter(is_inactive=0)] # S-05905 : Edit drop down option for BoM Entry Header - Technology: Added to filter dropdown data in pricing page
                })
            except (PartBase.DoesNotExist,):
                status_message = 'ERROR: Part number not found'
            except Header.DoesNotExist:
                status_message = 'ERROR: Configuration Number provided'

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
        'errorfound':errorfound
    })

    # Create a blank default table if no PricingObjects currently exist for the
    # part number provided
    if not dContext['partlines']:
        if oRequest.POST.get('part') and not status_message:
# S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. removed 4 ''
            dContext['partlines'] = [[oRequest.POST.get('part', ''), '', '', '',
                                      '', '', '', '']]
        elif oRequest.POST.get('initial') and not status_message:
            dContext['partlines'] = [[oRequest.POST.get('initial', ''), '', '',
                                      '', '', '', '', '']]
        else:
            dContext['partlines'] = [[]]
    # dContext['errorfound'] = errorfound
    return Default(oRequest, sTemplate='BoMConfig/partpricing.html',
                   dContext=dContext)
# S-11541: Upload - pricing for list of parts in pricing tab: Added below PriceUpload function to upload pricing data
@login_required
def PriceUpload(oRequest):
    """
    View to provide users with a means to upload Part Number price
    for creating new pricingobject mapping objects.
    :param oRequest:
    :return:
    """
    # Determine if user has permission to interact with pricing information
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))
    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    dContext = {'customer_list': aAvailableCU,
                'pricing_read_authorized': bCanReadPricing,
                'pricing_write_authorized': bCanWritePricing
                }

    # If POSTing an upload file
    if oRequest.POST:
        try:
            # Attempt to process the uploaded file
            bErrors = ProcessPriceUpload(
                oRequest.FILES['file'],
                REF_CUSTOMER.objects.get(id=oRequest.POST['customer']),
                oRequest.user
            )
            status_message = 'Upload completed.' + \
                (' An email has been sent detailing errors.'
                              if bErrors else '')
            status_error = False
        except ValueError:
            status_message = 'Invalid file provided'
            status_error = True

        dContext['status_message'] = status_message
        dContext['status_error'] = status_error

    return Default(oRequest, sTemplate='BoMConfig/priceupload.html',
                   dContext=dContext)
# end def
# S-12189: Validate pricing for list of parts in pricing tab: Added below function to validate pricing data before saving in th DB
# Condition to Upload: if the uploaded values match an existing entry exactly in the combined fields for Part #, Customer, Sold-to, SPUD,
# Valid From, and Valid To, then it should be flagged in an email and not added to the database. Same for Comment also. Any data if there is
# a difference in one of those fields from (a), then a new entry should be made except for customer will be uploaded.
def ProcessPriceUpload(oStream, oCustomer, oUser):
    """
    Function to parse information from a data stream provided in oStream into
    CustomerPartInfo objects.  There are currently two supported file types.
    :param oStream: Data stream (filestream, etc.) containing uploaded
    information
    :param oCustomer: REF_CUSTOMER object used to create PriceObject object
    :param oUser: User object creating entries
    :return: Boolean indicating if any erroneous data was encountered
    """
    sSheetName = "Price Upload"
    aColumns = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]]
    aHeaders = ['Part Number', 'Customer', 'Sold-To', 'SPUD', 'Technology', 'Latest Unit Price ($)', 'Valid From',
                 'Valid To', 'Cut-over Date', 'Price Erosion', 'Erosion Rate (%)', 'Comments']

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
    for row in aSheetData:
        for aDataGroup in aColumns:
            aTemp = []
            for (idx, iCol) in enumerate(aDataGroup):
                oData = row[iCol - 1].value
                aTemp.append(oData)
            # end for
            aTemp = tuple(aTemp)
            if any(aTemp):
                aExtractedData.append(aTemp)
                # end for
                # end for

    # Remove duplicate entries
    # D-07529: Not all lines processed in Price upload: After analysis we found that due to below line data is processed randomly.
    # Commented-out the same to process all lines in price upload
    # aExtractedData = list(set(aExtractedData))
    aDuplicateEntry = []
    aDuplicateComments = []
    aDuplicateCustomer = []
    aInvalidEntries = []
    # D-07324: Unit Price upload adjustment: Added below two variable to append Date fields record
    aDateUpdates = []
    aDupDates = []

    bErrorsLogged = False

    for tPart in aExtractedData:
        # Check if any mappings exists with current info
        # Attempt to find an entry that matches exactly
		# D-07324: Unit Price upload adjustment: Due to excel formatting of date fields changed vt_temp, vf_temp.
        # vt_temp = datetime.date.strftime(tPart[7], '%m/%d/%Y') if tPart[7] else ''
        # vf_temp = datetime.date.strftime(tPart[6], '%m/%d/%Y') if tPart[6] else ''
        vf_temp = tPart[6]
        vt_temp = tPart[7]

        oPart = PartBase.objects.filter( product_number=tPart[0])
        if not oPart:
            aInvalidEntries.append(tPart)
            continue
        try:
            # D-07324: Unit Price upload adjustment: Removed Sold-to from filtering condition as it is not dependent on sold-to now,
            # and added unit price to filter based on price. Removed Valid-to and Valid-from dates from filter
            oCurrentPriceObj = PricingObject.objects.get(
                part__product_number__iexact=tPart[0],
                customer__name=tPart[1],
                # sold_to=tPart[2] if tPart[2] not in ('', '(None)') else None,
                spud__name=tPart[3] if tPart[3] not in ('', '(None)') else None,
                unit_price=tPart[5],
                is_current_active=True
            )


        except PricingObject.DoesNotExist:
            oCurrentPriceObj = None
        # D-07324: Unit Price upload adjustment: Added belwo check to figure-out if it is a new entry for Current Price object with
        # new date range or date update of existing object.
        if (oCurrentPriceObj and (vt_temp is not None) and (vf_temp is not None)):
            if ( oCurrentPriceObj.valid_from_date is not None and oCurrentPriceObj.valid_to_date is None):
                if (oCurrentPriceObj.unit_price == float(tPart[5])):
                    oCurrentPriceObj.valid_to_date = datetime.datetime.strftime(vt_temp,'%Y-%m-%d')
                    oCurrentPriceObj.is_current_active = True
                    oCurrentPriceObj.save()
                    aDateUpdates.append(tPart)
                    continue
            #D-07500: Price Upload not modifying Valid To date and adding new price line: Added below block to modify valid-to based on the uploaded file.
            elif ( oCurrentPriceObj.valid_from_date is not None and oCurrentPriceObj.valid_to_date is not None):
                if (oCurrentPriceObj.unit_price == float(tPart[5]) and oCurrentPriceObj.valid_from_date<vt_temp.date() and oCurrentPriceObj.valid_to_date!=vt_temp.date()):
                    oCurrentPriceObj.valid_to_date = datetime.datetime.strftime(vt_temp,'%Y-%m-%d')
                    oCurrentPriceObj.is_current_active = True
                    oCurrentPriceObj.save()
                    aDateUpdates.append(tPart)
                    continue
                continue

            elif ( oCurrentPriceObj.valid_from_date is None and oCurrentPriceObj.valid_to_date is None):
                if (oCurrentPriceObj.unit_price == float(tPart[5])):
                    oCurrentPriceObj.valid_to_date =datetime.datetime.strftime(vt_temp,'%Y-%m-%d')
                    oCurrentPriceObj.valid_from_date = datetime.datetime.strftime(vf_temp,'%Y-%m-%d')
                    oCurrentPriceObj.is_current_active = True
                    oCurrentPriceObj.save()
                    aDateUpdates.append(tPart)
                    continue
            else :
                aPricingList = PricingObject.objects.filter(
                    part__product_number__iexact=tPart[0],
                    customer__name=tPart[1],
                    spud__name=tPart[3] if tPart[3] not in ('', '(None)') else None,
                    is_current_active=True)
                avalid_to_date = [
                    oRow.valid_to_date
                    for oRow in aPricingList
                ]
                if avalid_to_date is not [None]:
                    max_date = max(d for d in avalid_to_date if isinstance(d, datetime.date))
                    if max_date <= datetime.datetime.date(vf_temp):
                        oNewPriceObj = PricingObject.objects.create(
                            part=PartBase.objects.get(
                                product_number__iexact=tPart[0]),
                            spud=REF_SPUD.objects.get(name__iexact=tPart[3]) if tPart[3] not
                                                                                in (
                                                                                    '(None)', '', None, 'null') else None,
                            customer=REF_CUSTOMER.objects.get(
                                                    name=tPart[1]),
                            sold_to=tPart[2] if tPart[2] not
                                                in ('(None)', '', None, 'null') else None,
                            unit_price=tPart[5],
                            # valid_from_date=datetime.datetime.strftime(vf_temp,
                            #                                            '%Y-%m-%d'
                            #                                            ) if vf_temp is not None else None,
                            # valid_to_date=datetime.datetime.strptime(vt_temp,
                            #                         '%Y-%m-%d'
                            #                     ).date() if vt_temp is not None else None,
                            valid_from_date=vf_temp if vf_temp is not None else None,
                            valid_to_date=vt_temp if vt_temp is not None else None,
                            technology=REF_TECHNOLOGY.objects.get(
                                name=tPart[4]) if tPart[4] not
                                                  in ('(None)', '', None, 'null') else None,
                            comments=tPart[11] if tPart[11] not
                                                  in ('(None)', '', None, 'null') else None,
                            is_current_active=True,

                        )
                else:
                    print('')
        if oCurrentPriceObj and vf_temp and vt_temp is not None:
            if (oCurrentPriceObj.valid_to_date is None and oCurrentPriceObj.valid_from_date.strftime('%m/%d/%Y') == vf_temp):
                if (oCurrentPriceObj.unit_price == float(tPart[5])):
                    oCurrentPriceObj.valid_to_date = datetime.datetime.strftime(vt_temp,'%Y-%m-%d')
                    oCurrentPriceObj.is_current_active = True
                    oCurrentPriceObj.save()
                    aDateUpdates.append(tPart)
                    continue

        if not oCurrentPriceObj and str(oCustomer).upper() != str(tPart[1]).upper():
            aDuplicateCustomer.append(tPart)
            continue
        if oCurrentPriceObj and str(oCustomer).upper() != str(tPart[1]).upper():
            aDuplicateCustomer.append(tPart)
            continue
        if oCurrentPriceObj and str(oCustomer).upper() == str(tPart[1]).upper() and not tPart[11]:
            aDuplicateEntry.append(tPart)
            continue
        if oCurrentPriceObj and str(oCustomer).upper() == str(tPart[1]).upper() and tPart[11]:
            aDuplicateComments.append(tPart)
            continue


        if not oCurrentPriceObj:
            # Create a new PricingObject
            # D-07324: Unit Price upload adjustment: Declared a list to filter Pricing list,if the combination is not present in DB then it will
            # create an entry or check for existing date fileds. If it lies in-between the date range it will flag error in mail else create an entry.
            try:
                aPricingList = PricingObject.objects.filter(
                    part__product_number__iexact=tPart[0],
                    customer__name=tPart[1],
                    spud__name=tPart[3] if tPart[3] not in ('', '(None)') else None,
                    is_current_active=True)

                if len(aPricingList) == 0:
                    oNewPriceObj = PricingObject.objects.create(
                        part=PartBase.objects.get(
                            product_number__iexact=tPart[0]),
                        spud=REF_SPUD.objects.get(name__iexact=tPart[3])if tPart[3] not
                                        in ('(None)', '', None, 'null') else None,
                        customer=REF_CUSTOMER.objects.get(
                                                    name__iexact=tPart[1]),
                        sold_to=tPart[2] if tPart[2] not
                                        in ('(None)', '', None, 'null') else None,
                        unit_price=tPart[5],
                        valid_from_date=vf_temp if vf_temp is not None else None,
                        valid_to_date=vt_temp if vt_temp is not None else None,
                        technology=REF_TECHNOLOGY.objects.get(
                                            name=tPart[4]) if tPart[4] not
                                        in ('(None)', '', None, 'null') else None,
                        comments=tPart[11] if tPart[11] not
                                        in ('(None)', '', None, 'null') else None,
                        is_current_active=True
                    )
                else:

                    avalid_to_date = [
                        oRow.valid_to_date
                        for oRow in aPricingList
                    ]

                    max_date = max(d for d in avalid_to_date if isinstance(d, datetime.date))

                    if max_date <= datetime.datetime.date(vf_temp):
                        oNewPriceObj = PricingObject.objects.create(
                            part=PartBase.objects.get(
                                product_number__iexact=tPart[0]),
                            spud=REF_SPUD.objects.get(name__iexact=tPart[3]) if tPart[3] not
                                                                                in (
                                                                                '(None)', '', None, 'null') else None,
                            customer=REF_CUSTOMER.objects.get(
                                                    name=tPart[1]),
                            sold_to=tPart[2] if tPart[2] not
                                                in ('(None)', '', None, 'null') else None,
                            unit_price=tPart[5],
                            valid_from_date=vf_temp if vf_temp is not None else None,
                            valid_to_date=vt_temp if vt_temp is not None else None,
                            # valid_from_date=datetime.datetime.strftime(vf_temp,
                            #                         '%Y-%m-%d'
                            #                     ) if vf_temp not in ('', '(None)') else None,
                            # valid_to_date=datetime.datetime.strftime(vt_temp,
                            #                                          '%Y-%m-%d'
                            #                                          ) if vt_temp is not None else None,
                            technology=REF_TECHNOLOGY.objects.get(
                                name=tPart[4]) if tPart[4] not
                                                  in ('(None)', '', None, 'null') else None,
                            comments=tPart[11] if tPart[11] not
                                                  in ('(None)', '', None, 'null') else None,
                            is_current_active=True,

                        )
                    else:
                        aDupDates.append(tPart)
            except PricingObject.DoesNotExist:
                oNewPriceObj = None
        # end if
    # end for
    # D-07324: Unit Price upload adjustment: added aDateUpdates or aDupDates. Also upadted text_message for the new entries.
    if aDuplicateComments or aDuplicateCustomer or aDuplicateEntry  or aInvalidEntries or aDateUpdates or aDupDates:
        bErrorsLogged = True
        # Commented-out as it is not required
        # aDuplicateEntry.sort(key=lambda x: x[3])
        # aDuplicateComments.sort(key=lambda x: x[3])
        # aDuplicateCustomer.sort(key=lambda x: x[3])
        # aInvalidEntries.sort(key=lambda x: x[3])


        subject = 'Price upload errors'
        from_email = 'acc.admin@ericsson.com'
        text_message = GenerateEmailMessage(
            **{
                'dupentry': aDuplicateEntry,
                'comments': aDuplicateComments,
                'cu': aDuplicateCustomer,
                'invalidentry': aInvalidEntries,
                'updatedate': aDateUpdates,
                'dupdates': aDupDates,
                'user': oUser,
                'filename': oStream.name
            }
        )
        html_message = render_to_string(
            'BoMConfig/priceupload_email.html',
            {
                'dupentry': aDuplicateEntry,
                'comments': aDuplicateComments,
                'cu': aDuplicateCustomer,
                'invalidentry': aInvalidEntries,
                'updatedate': aDateUpdates,
                'dupdates': aDupDates,
                'user': oUser,
                'filename': oStream.name
            }
        )
        oUser.email_user(subject=subject, message=text_message,
                         from_email=from_email, html_message=html_message)
    # end if


    return bErrorsLogged

# S-12189: Validate pricing for list of parts in pricing tab: Added below function to generate detailed error message
# D-07324: Unit Price upload adjustment: added updatedate,dupdates to send mail for date updates
def GenerateEmailMessage( dupentry=(), comments=(), cu=(), invalidentry=(), updatedate=(), dupdates=(),
                         user=None, filename=''):
    """
    Function to generate a plain-text error message detailing any errors
    encountered during file upload
    :param cu: List of entries found that duplicate an existing customer associated
    :param comments: List of entries found that duplicate an comments
    :param dupentry: List of entries found that found to be duplicate
    :param user: User object of user uploading file
    :param filename: String containing name of file uploaded
    :return: String containing formatted plain-text error message
    """
    temp = ('Hello {},\n\nThe following errors were found '
            'while uploading {}:\n\n').format(
        user.first_name, filename
    )
# D-07324: Unit Price upload adjustment: added updatedate,added aTableTitles->Last two titles to send mail for date updates
    aErrorLists = [dupentry, comments, cu, invalidentry, updatedate, dupdates]
    aTableTitles = ['Same Part Number + Customer + Sold-to + SPUD + Valid From + Valid To already exists in the database with different pricing',
                    'Same Part Number + Customer + Sold-to + SPUD + Valid From + Valid To has different value in Comments',
                    ('Different Customer provided in the file for the selected Customer'),
                    'Part does not exist in system',
                    'Dates Updated',
                    'Date Range entered already exists for a CU and SPUD combination.Please select a different date range'
                    ]

    for (idx, maplist) in enumerate(aErrorLists):
        if maplist:
            temp += aTableTitles[idx] + '\n'
            for mapping in maplist:
                temp += '\t' + mapping[0] + '\n'
            temp += '\n'
        # end if
    # end for

    return temp
# end def

@login_required
def ConfigPricing(oRequest):
    """
    View for viewing and editing manual pricing overrides for individual Headers
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    # Determine user permissions
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))
    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # Unlock any locked Header
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'status' in oRequest.session:
        del oRequest.session['status']
    # end if

    status_message = None

    sTemplate = 'BoMConfig/configpricing.html'
    aConfigLines = []
    dContext = {'configlines': aConfigLines, 'readonly': False}


    # If POSTing data
    if oRequest.method == 'POST' and oRequest.POST:
        sConfig = oRequest.POST['config'] if 'config' in oRequest.POST else None

        iProgram = oRequest.POST.get('program', None)
        iBaseline = oRequest.POST.get('baseline', None)
        if 'action' in oRequest.POST and oRequest.POST['action'] == 'search':
            iProgram = None
            iBaseline = None

        # Since the user searches by Header name only, it is possible to have
        # multiple Headers with the same name, with different programs and/or
        # baselines.  So if multiple matches exist, we will create a list to
        # allow the user to select the desired Header.

        # Start with all Headers that match the name
        aConfigMatches = Header.objects.filter(
            configuration_designation__iexact=sConfig).filter(customer_unit_id__in=aAvailableCU) # S-05923: Pricing - Restrict View to allowed CU's based on permissions added .filter

        # If iProgram has a value, filter Headers by program
        if iProgram and iProgram not in ('None', 'NONE'):
            aConfigMatches = aConfigMatches.filter(program__id=iProgram)
        elif iProgram:
            aConfigMatches = aConfigMatches.filter(program=None)

        # If iBaseline has a value, filter Headers by baseline id
        if iBaseline and iBaseline not in ('None', 'NONE'):
            aConfigMatches = aConfigMatches.filter(baseline__id=iBaseline)
        elif iBaseline:
            aConfigMatches = aConfigMatches.filter(baseline=None)

        if len(aConfigMatches) == 0:
            status_message = 'No matching configuration found'
            dContext.update({'config': sConfig})

        # More than one match was found, so create a list with an entry for each
        # match
        elif len(aConfigMatches) > 1:
            aProgramList = list(
                [oHead.program.id, oHead.program.name] if oHead.program else
                ['None', '(No Program)'] for oHead in aConfigMatches
            )
        # S-11538: Open multiple revisions for each configuration - UI Elements :- Added below to pick the baseline, it's revision
            aBaselineList = list(
                [oHead.baseline.id, str(oHead.baseline_impacted), str(oHead.baseline_version)] if oHead.baseline else
                ['None', '(No Baseline)'] for oHead in aConfigMatches
            )

# S - 12898: Need status information on multiple revision selection in Pricing - Added aConfigStatusList below to fetch the status info

            aConfigStatusList = list(
                [oHead.configuration_status.id, oHead.configuration_status.name] if oHead.configuration_status else
                ['None', '(No Status)'] for oHead in aConfigMatches
            )

 # S - 12898: Need status information on multiple revision selection in Pricing - Added configstatus in dcontext to store the status info
            dContext.update(
                {'prog_list': aProgramList, 'config': sConfig,
                 'base_list': aBaselineList, 'configstatus' : aConfigStatusList})

        # Only a single match was found, so load the data for the match
        else:
            iProgValue = aConfigMatches[0].program.id if \
                aConfigMatches[0].program else None
            iBaseValue = aConfigMatches[0].baseline.id if \
                aConfigMatches[0].baseline else None

            dLineFilters = {
                'config__header__configuration_designation__iexact': sConfig,
            }
            dConfigFilters = {
                'header__configuration_designation__iexact': sConfig,
            }

            dLineFilters.update({'config__header__program__id': iProgValue})
            dConfigFilters.update({'header__program__id': iProgValue})

            dLineFilters.update({'config__header__baseline__id': iBaseValue})
            dConfigFilters.update({'header__baseline__id': iBaseValue})

            # Save data
            if 'action' in oRequest.POST and oRequest.POST['action'] == 'save':
                # Ensure user has not changed the configuration value prior to
                # saving
                if oRequest.POST['config'] == oRequest.POST['initial']:
                    # net_total = 0
                    for dLine in json.loads(oRequest.POST['data_form']):
                        # Change dLine to dict with str keys
                        if isinstance(dLine, list):
                            dLine = {
                                str(key): val for (key, val) in enumerate(dLine)
                                }
                        elif isinstance(dLine, dict):
                            dLine = {
                                str(key): val for (key, val) in dLine.items()}

                        dLineFilters.update({'line_number': dLine['0']})

                        # Retrieve ConfigLine matching line number and update
                        # override_price
                        oLineToEdit = ConfigLine.objects.filter(
                            **dLineFilters)[0]
                        (oLinePrice, _) = LinePricing.objects.get_or_create(
                            config_line=oLineToEdit)
                        oLinePrice.override_price = float(dLine['7']) if \
                            dLine['7'] not in (None, '') else None

                        oLinePrice.save()
                    # end for
                    dLineFilters.pop('line_number', None)

                    # Save the configuration
                    oConfig = Configuration.objects.get(**dConfigFilters)
                    oConfig.save()

                    status_message = 'Data saved.'
                else:
                    status_message = 'Cannot change configuration during save.'
                    sConfig = oRequest.POST['initial']
                # end if
            # end if

            # Retrieve ConfigLines that matches the filters and sort by line
            # number
            aLine = ConfigLine.objects.filter(**dLineFilters)
            aLine = sorted(aLine, key=lambda x: (
                [int(y) for y in x.line_number.split('.')]))

            # Build table layout from matching data
            aConfigLines = [{
                '0': oLine.line_number,
                '1': ('..' if oLine.is_grandchild else '.' if
                      oLine.is_child else '') + oLine.part.base.product_number,
                '2': str(oLine.part.base.product_number) +
                str('_' + oLine.spud.name if oLine.spud else ''),
# D-07617: Configuration Price Mgmt does not show table in view :- Added the if else condition below since it was showing the value as None
# when a part number was not found and as a result, for the presence of 'None' value in the configlines data, could not draw table in JS
                '3': oLine.part.product_description if oLine.part.product_description else '',
                '4': float(oLine.order_qty if oLine.order_qty else 0),
                '5': float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '6': float(oLine.order_qty or 0) * float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '7': GrabValue(oLine, 'linepricing.override_price', ''),
                '8': oLine.traceability_req or '', # S-05769: Addition of Product Traceability field in Pricing->Config Price Management tab
                '9': oLine.higher_level_item or '',
                '10': oLine.material_group_5 or '',
                '11': oLine.commodity_type or '',
                '12': oLine.comments or '',
                '13': oLine.additional_ref or ''
                            } for oLine in aLine]

            # Update expected price roll-up (determined by unit price per line)
            if not aLine[0].config.header.pick_list:
                config_total = sum([float(line['6']) for line in aConfigLines])
                aConfigLines[0]['5'] = aConfigLines[0]['6'] = str(config_total)

            dContext['configlines'] = aConfigLines
            dContext.update(
                {'config': sConfig,
                 'is_not_pick_list': not aLine[0].config.header.pick_list if
                 aLine else False,
                 'program': iProgValue,
                 'baseline': iBaseValue,
                 'prog_list': [],
                 'base_list': [],
                 'readonly': 'In Process' not in
                             aLine[0].config.header.configuration_status.name
                 }
            )
        # end if
    # end if

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)

# S-11537: Multi Config sub tab - UI for Multiple Config tab :- Added below MultConfigPricing to show multiple configs
@login_required
def MultiConfigPricing(oRequest):
    """
    View for viewing and editing manual pricing overrides for individual Headers
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    # Determine user permissions
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))
    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # Unlock any locked Header
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'status' in oRequest.session:
        del oRequest.session['status']
    # end if

    status_message = None

    sTemplate = 'BoMConfig/multi_configpricing.html'
    aConfigLines = []
    aConfigLines1 = []
    aBaselines1 = []
    aBaseRev1 = []
    aConfigs1 = []
    aConfigStatus1 = []
    dContext = {'configlines': aConfigLines1, 'readonly': False}

    # If POSTing data
    if oRequest.method == 'POST' and oRequest.POST:

        scon= oRequest.POST['config'] if 'config' in oRequest.POST else None
        scon2= scon.split(';')

        for config_index in range(len(scon2)):
            sConfig = scon2[config_index]

            if 'action' in oRequest.POST and oRequest.POST['action'] == 'search':
                iProgram = None
                iBaseline = None

            # Since the user searches by Header name only, it is possible to have
            # multiple Headers with the same name, with different programs and/or
            # baselines.  So if multiple matches exist, we will create a list to
            # allow the user to select the desired Header.

            # Start with all Headers that match the name
            if sConfig:
 # D-07123: Latest active configuration is not the item shown in mulit-config pricing feature - Commented the below statememt as it was fetching the latest version &
 # added the statement below it to fetch the Active version of the config
                # aConfigMatches = Header.objects.filter(
                #     configuration_designation__iexact=sConfig).filter(customer_unit_id__in=aAvailableCU).latest('baseline') # S-05923: Pricing - Restrict View to allowed CU's based on permissions added .filter
                aConfigMatches = Header.objects.filter(
                    configuration_designation__iexact=sConfig).filter(customer_unit_id__in=aAvailableCU).filter(
                    configuration_status=3)  # S-05923: Pricing - Restrict View to allowed CU's based on permissions added .filter

            # if aConfigMatches == 0:    #D-07123: commented this line and added below since the non-active configs also used to go to else part
            if not aConfigMatches:                          # If NO Active Version found
                status_message = 'No Active configuration found'

                aConfigLines = []
                aConfigLines1.append(aConfigLines)
                dContext['configlines'] = aConfigLines1

                aBaselines = []
                aBaselines1.append(aBaselines)
                dContext['baselines'] = aBaselines1
                aBaseRev = []
                aBaseRev1.append(aBaseRev)
                dContext['baserevs'] = aBaseRev1
                aConfigs1.append(sConfig)
                dContext['configs'] = aConfigs1
                dContext['configstatus'] = aConfigStatus1

                dContext.update({'config': scon })

            # Only a single match was found, so load the data for the match
            else:                                           # If Active Version found
 # D-07123: Latest active configuration is not the item shown in mulit-config pricing feature - Iterating aConfigMatches to extract data as it is in object form
                for obj in aConfigMatches:
                    iProgValue = obj.program.id if \
                        obj.program else None
                    iBaseValue = obj.baseline.id if \
                        obj.baseline else None
                    iBaselineValue = obj.baseline.title if \
                        obj.baseline else None
                    iBaseRevValue = obj.baseline.version if \
                        obj.baseline else None
        # Added below to add config status for each config for the readonly & editable feature in multi-config pricing page
                    iConfigStatusValue = obj.configuration_status.name if \
                        obj.configuration_status else None

                if sConfig:
                    dLineFilters = {
                        'config__header__configuration_designation__iexact': sConfig,
                    }

                    dConfigFilters = {
                        'header__configuration_designation__iexact': sConfig,
                    }
                dLineFilters.update({'config__header__program__id': iProgValue})
                dConfigFilters.update({'header__program__id': iProgValue})

                dLineFilters.update({'config__header__baseline__id': iBaseValue})
                dConfigFilters.update({'header__baseline__id': iBaseValue})

                # Retrieve ConfigLines that matches the filters and sort by line
                # number
                aLine = ConfigLine.objects.filter(**dLineFilters)
                aLine = sorted(aLine, key=lambda x: (
                    [int(y) for y in x.line_number.split('.')]))

                # Build table layout from matching data
                aConfigLines = [{
                    '0': oLine.line_number,
                    '1': ('..' if oLine.is_grandchild else '.' if
                          oLine.is_child else '') + oLine.part.base.product_number,
                    '2': str(oLine.part.base.product_number) +
                    str('_' + oLine.spud.name if oLine.spud else ''),
# D-07617: Configuration Price Mgmt does not show table in view :- Added the if else condition below since it was showing the value as None
# when a part number was not found and as a result, for the presence of 'None' value in the configlines data, could not draw table in JS
                    '3': oLine.part.product_description if oLine.part.product_description else '',
                    '4': float(oLine.order_qty if oLine.order_qty else 0),
                    '5': float(GrabValue(
                        oLine, 'linepricing.pricing_object.unit_price', 0)),
                    '6': float(oLine.order_qty or 0) * float(GrabValue(
                        oLine, 'linepricing.pricing_object.unit_price', 0)),
                    '7': GrabValue(oLine, 'linepricing.override_price', ''),
                    '8': oLine.traceability_req or '', # S-05769: Addition of Product Traceability field in Pricing->Config Price Management tab
                    '9': oLine.higher_level_item or '',
                    '10': oLine.material_group_5 or '',
                    '11': oLine.commodity_type or '',
                    '12': oLine.comments or '',
                    '13': oLine.additional_ref or ''
                                } for oLine in aLine]

                # Update expected price roll-up (determined by unit price per line)
                if not aLine[0].config.header.pick_list:
                    config_total = sum([float(line['6']) for line in aConfigLines])
                    aConfigLines[0]['5'] = aConfigLines[0]['6'] = str(config_total)

                aConfigLines1.append(aConfigLines)
                aBaselines1.append(iBaselineValue)
                aBaseRev1.append(iBaseRevValue)
                aConfigs1.append(sConfig)
                aConfigStatus1.append(iConfigStatusValue)

                dContext['configlines'] = aConfigLines1
                dContext['baselines'] = aBaselines1
                dContext['baserevs'] = aBaseRev1
                dContext['configs'] = aConfigs1
    # Added below to add config status for each config for the readonly & editable feature in multi-config pricing page
                dContext['configstatus'] = aConfigStatus1

                dContext.update(
                    {'config': scon,
                     'is_not_pick_list': not aLine[0].config.header.pick_list if
                     aLine else False,
                     'program': iProgValue,
                     'baseline': iBaseValue,
                     'prog_list': [],
                     'base_list': [],
                     'readonly': 'In Process' not in
                                 aLine[0].config.header.configuration_status.name
                     }
                )
        # end if
    # end if

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)

# S-11538: Open multiple revisions for each configuration - UI Elements :- Added below function to show multiple revisions for each config
@login_required
def MultiRevConfigPricing(oRequest):
    """
    View for viewing and editing manual pricing overrides for individual Headers
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    # Determine user permissions
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))
    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:
        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # Unlock any locked Header
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'status' in oRequest.session:
        del oRequest.session['status']
    # end if

    status_message = None

    sTemplate = 'BoMConfig/multirevconfigpricing.html'
    aConfigLines = []
    dContext = {'configlines': aConfigLines, 'readonly': False}


    # If POSTing data
    if oRequest.method == 'POST' and oRequest.POST:
        sConfig = oRequest.POST['config'] if 'config' in oRequest.POST else None
        # Uncommented below line because the Multi Rev saving wasnt working without the program info
        iProgram = oRequest.POST.get('iProgId', None)
        iBaseline = oRequest.POST.get('iBaseId', None)

        if 'action' in oRequest.POST and oRequest.POST['action'] == 'search':
            iProgram = None
            iBaseline = None

        # Since the user searches by Header name only, it is possible to have
        # multiple Headers with the same name, with different programs and/or
        # baselines.  So if multiple matches exist, we will create a list to
        # allow the user to select the desired Header.

        # Start with all Headers that match the name
        aConfigMatches = Header.objects.filter(
            configuration_designation__iexact=sConfig).filter(

            customer_unit_id__in=aAvailableCU)  # S-05923: Pricing - Restrict View to allowed CU's based on permissions added .filter

    # Added below blocks the Multi Rev saving wasnt working without the program info
        iProgram = oRequest.POST.get('iProgId', None)
        # If iProgram has a value, filter Headers by program
        if iProgram and iProgram not in ('None', 'NONE'):
            aConfigMatches = aConfigMatches.filter(program__id=iProgram)
        elif iProgram:
            aConfigMatches = aConfigMatches.filter(program=None)

        if iBaseline and iBaseline not in ('None', 'NONE'):
            aConfigMatches = aConfigMatches.filter(baseline__id=iBaseline)
        elif iBaseline:
            aConfigMatches = aConfigMatches.filter(baseline=None)
        if len(aConfigMatches) == 0:
            status_message = 'No matching configuration found'
            dContext.update({'config': sConfig})

        # Only a single match was found, so load the data for the match
        else:
            # Changed the iProgvalue and iBasevalue based on the GET info because Multi Rev saving wasnt working without the program info
            iProgValue = oRequest.GET.get('iProgId', None)
            iBaseValue = oRequest.GET.get('iBaseId', None)

            dLineFilters = {
                'config__header__configuration_designation__iexact': sConfig,
            }
            dConfigFilters = {
                'header__configuration_designation__iexact': sConfig,
            }
            # Added below block because Multi Rev saving wasnt working without the program info
            if iProgValue != 'None':
                dLineFilters.update({'config__header__program__id': iProgValue})
                dConfigFilters.update({'header__program__id': iProgValue})

            dLineFilters.update({'config__header__baseline__id': iBaseValue})
            dConfigFilters.update({'header__baseline__id': iBaseValue})

            # Save data
            if 'action' in oRequest.POST and oRequest.POST['action'] == 'save':
                # Ensure user has not changed the configuration value prior to
                # saving
                if oRequest.POST['config'] == oRequest.POST['initial']:
                    # net_total = 0
                    for dLine in json.loads(oRequest.POST['data_form']):
                        # Change dLine to dict with str keys
                        if isinstance(dLine, list):
                            dLine = {
                                str(key): val for (key, val) in enumerate(dLine)
                                }
                        elif isinstance(dLine, dict):
                            dLine = {
                                str(key): val for (key, val) in dLine.items()}

                        dLineFilters.update({'line_number': dLine['0']})

                        # Retrieve ConfigLine matching line number and update
                        # override_price
                        oLineToEdit = ConfigLine.objects.filter(
                            **dLineFilters)[0]
                        (oLinePrice, _) = LinePricing.objects.get_or_create(
                            config_line=oLineToEdit)
                        oLinePrice.override_price = float(dLine['7']) if \
                            dLine['7'] not in (None, '') else None

                        oLinePrice.save()
                    # end for
                    dLineFilters.pop('line_number', None)

                    # Save the configuration
                    oConfig = Configuration.objects.get(**dConfigFilters)
                    oConfig.save()

                    status_message = 'Data saved.'
                else:
                    status_message = 'Cannot change configuration during save.'
                    sConfig = oRequest.POST['initial']
                # end if
            # end if

            # Retrieve ConfigLines that matches the filters and sort by line
            # number
            aLine = ConfigLine.objects.filter(**dLineFilters)
            aLine = sorted(aLine, key=lambda x: (
                [int(y) for y in x.line_number.split('.')]))

            # Build table layout from matching data
            aConfigLines = [{
                '0': oLine.line_number,
                '1': ('..' if oLine.is_grandchild else '.' if
                      oLine.is_child else '') + oLine.part.base.product_number,
                '2': str(oLine.part.base.product_number) +
                str('_' + oLine.spud.name if oLine.spud else ''),
# D-07617: Configuration Price Mgmt does not show table in view :- Added the if else condition below since it was showing the value as None
# when a part number was not found and as a result, for the presence of 'None' value in the configlines data, could not draw table in JS
                '3': oLine.part.product_description if oLine.part.product_description else '',
                '4': float(oLine.order_qty if oLine.order_qty else 0),
                '5': float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '6': float(oLine.order_qty or 0) * float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '7': GrabValue(oLine, 'linepricing.override_price', ''),
                '8': oLine.traceability_req or '', # S-05769: Addition of Product Traceability field in Pricing->Config Price Management tab
                '9': oLine.higher_level_item or '',
                '10': oLine.material_group_5 or '',
                '11': oLine.commodity_type or '',
                '12': oLine.comments or '',
                '13': oLine.additional_ref or ''
                            } for oLine in aLine]

            # Update expected price roll-up (determined by unit price per line)
            if not aLine[0].config.header.pick_list:
                config_total = sum([float(line['6']) for line in aConfigLines])
                aConfigLines[0]['5'] = aConfigLines[0]['6'] = str(config_total)

            dContext['configlines'] = aConfigLines
            dContext.update(
                {'config': sConfig,
                 'is_not_pick_list': not aLine[0].config.header.pick_list if
                 aLine else False,
                 # 'program': iProgValue,
                 'baseline': iBaseValue,
                 'prog_list': [],
                 'base_list': [],
                 'readonly': 'In Process' not in
                             aLine[0].config.header.configuration_status.name
                 }
            )
        # end if
    # end if
    if oRequest.method == 'GET' and oRequest.GET:

        sConfig = oRequest.GET['iConf'] if 'iConf' in oRequest.GET else None

        iBaseline = oRequest.GET.get('iBaseId', None)

        if 'action' in oRequest.POST and oRequest.POST['action'] == 'search':
            iProgram = None
            iBaseline = None

        # Since the user searches by Header name only, it is possible to have
        # multiple Headers with the same name, with different programs and/or
        # baselines.  So if multiple matches exist, we will create a list to
        # allow the user to select the desired Header.

        # Start with all Headers that match the name
        aConfigMatches = Header.objects.filter(
            configuration_designation__iexact=sConfig).filter(
            customer_unit_id__in=aAvailableCU)  # S-05923: Pricing - Restrict View to allowed CU's based on permissions added .filter
        # If iBaseline has a value, filter Headers by baseline id
        if iBaseline and iBaseline not in ('None', 'NONE'):
            aConfigMatches = aConfigMatches.filter(baseline__id=iBaseline)
        elif iBaseline:
            aConfigMatches = aConfigMatches.filter(baseline=None)

        if len(aConfigMatches) == 0:
            status_message = 'No matching configuration found'
            dContext.update({'config': sConfig})

        # Only a single match was found, so load the data for the match
        else:
            iBaseValue = aConfigMatches[0].baseline.id if \
                aConfigMatches[0].baseline else None

            dLineFilters = {
                'config__header__configuration_designation__iexact': sConfig,
            }
            dConfigFilters = {
                'header__configuration_designation__iexact': sConfig,
            }

            dLineFilters.update({'config__header__baseline__id': iBaseValue})
            dConfigFilters.update({'header__baseline__id': iBaseValue})

            # Save data
            if 'action' in oRequest.POST and oRequest.POST['action'] == 'save':
                # Ensure user has not changed the configuration value prior to
                # saving
                if oRequest.GET['config'] == oRequest.GET['initial']:
                    # net_total = 0
                    for dLine in json.loads(oRequest.GET['data_form']):
                        # Change dLine to dict with str keys
                        if isinstance(dLine, list):
                            dLine = {
                                str(key): val for (key, val) in enumerate(dLine)
                                }
                        elif isinstance(dLine, dict):
                            dLine = {
                                str(key): val for (key, val) in dLine.items()}

                        dLineFilters.update({'line_number': dLine['0']})

                        # Retrieve ConfigLine matching line number and update
                        # override_price
                        oLineToEdit = ConfigLine.objects.filter(
                            **dLineFilters)[0]
                        (oLinePrice, _) = LinePricing.objects.get_or_create(
                            config_line=oLineToEdit)
                        oLinePrice.override_price = float(dLine['7']) if \
                            dLine['7'] not in (None, '') else None

                        oLinePrice.save()
                    # end for
                    dLineFilters.pop('line_number', None)

                    # Save the configuration
                    oConfig = Configuration.objects.get(**dConfigFilters)
                    oConfig.save()

                    status_message = 'Data saved.'
                else:
                    status_message = 'Cannot change configuration during save.'
                    sConfig = oRequest.GET['initial']
                # end if
            # end if

            # Retrieve ConfigLines that matches the filters and sort by line
            # number
            aLine = ConfigLine.objects.filter(**dLineFilters)
            aLine = sorted(aLine, key=lambda x: (
                [int(y) for y in x.line_number.split('.')]))

            # Build table layout from matching data
            aConfigLines = [{
                '0': oLine.line_number,
                '1': ('..' if oLine.is_grandchild else '.' if
                      oLine.is_child else '') + oLine.part.base.product_number,
                '2': str(oLine.part.base.product_number) +
                str('_' + oLine.spud.name if oLine.spud else ''),
# D-07617: Configuration Price Mgmt does not show table in view :- Added the if else condition below since it was showing the value as None
# when a part number was not found and as a result, for the presence of 'None' value in the configlines data, could not draw table in JS
                '3': oLine.part.product_description if oLine.part.product_description else '',
                '4': float(oLine.order_qty if oLine.order_qty else 0),
                '5': float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '6': float(oLine.order_qty or 0) * float(GrabValue(
                    oLine, 'linepricing.pricing_object.unit_price', 0)),
                '7': GrabValue(oLine, 'linepricing.override_price', ''),
                '8': oLine.traceability_req or '', # S-05769: Addition of Product Traceability field in Pricing->Config Price Management tab
                '9': oLine.higher_level_item or '',
                '10': oLine.material_group_5 or '',
                '11': oLine.commodity_type or '',
                '12': oLine.comments or '',
                '13': oLine.additional_ref or ''
                            } for oLine in aLine]

            # Update expected price roll-up (determined by unit price per line)
            if not aLine[0].config.header.pick_list:
                config_total = sum([float(line['6']) for line in aConfigLines])
                aConfigLines[0]['5'] = aConfigLines[0]['6'] = str(config_total)

            dContext['configlines'] = aConfigLines
            dContext.update(
                {'config': sConfig,
                 'is_not_pick_list': not aLine[0].config.header.pick_list if
                 aLine else False,
                 # 'program': iProgValue,
                 'baseline': iBaseValue,
                 'prog_list': [],
                 'base_list': [],
                 'readonly': 'In Process' not in
                             aLine[0].config.header.configuration_status.name
                 }
            )
        # end if
    # end if

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)


@login_required
def OverviewPricing(oRequest):
    """
    View for viewing all existing pricing information for parts
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    # Determine user permissions
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))

    # Unlock any locked Header
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'status' in oRequest.session:
        del oRequest.session['status']
    # end if

    status_message = None

    sTemplate = 'BoMConfig/overviewpricing.html'

    # Collect line data
    aPricingLines, aComments = PricingOverviewLists(oRequest) # S-05923: Pricing - Restrict View to allowed CU's based on permissions: added oRequest

    dContext = {
        'pricelines': aPricingLines,
        'comments': aComments
    }

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)
# end def

# S-05923: Pricing - Restrict View to allowed CU's based on permissions: added oRequest
def PricingOverviewLists(oRequest):
    """
    Function to write all pricing data into two lists.  The first list is a list
    of lists containing data to be displayed in each row/column of a table.  The
    second is a list of lists containing additional data to be used as a comment
    on a each row/column.  Comments are displayed on mouseover.
    :return: 2x list of lists
    """

    # S-05923: Pricing - Restrict View to allowed CU's based on permissions
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)
    # Retrieve all active PricingObjects
    aPricingObjectList = PricingObject.objects.filter(
        is_current_active=True).filter(customer_id__in=aAvailableCU).order_by(
        'part__product_number', 'customer__name', 'sold_to', 'spud__name') # For S-05923: Pricing added .filter(customer_id__in=aAvailableCU)

    aPricingLines = []
    aComments = []
    if aPricingObjectList:
        for oPriceObj in aPricingObjectList:
            aCommentRow = []
            # Create row data from PricingObject
            aObj = [
                oPriceObj.part.product_number,
                oPriceObj.customer.name,
                oPriceObj.sold_to or '(None)',
                oPriceObj.spud.name if oPriceObj.spud else '(None)',
                oPriceObj.technology.name if oPriceObj.technology else '(None)',
                oPriceObj.unit_price,
                # fix for S-05772 Add Valid From and Valid to columns on Pricing->Pricing Overview tab
                oPriceObj.valid_from_date.strftime('%m/%d/%Y') if
                oPriceObj.valid_from_date else '',  # Valid-from
                oPriceObj.valid_to_date.strftime('%m/%d/%Y') if
                oPriceObj.valid_to_date else '',  # Valid-To
            ]
            # Create comment data from PricingObject
            aCommentRow.append("Valid: {}\nCut-over: {}".format(
                (oPriceObj.valid_from_date.strftime('%m/%d/%Y') if
                 oPriceObj.valid_from_date else "N/A") +
                " - " + (oPriceObj.valid_to_date.strftime('%m/%d/%Y') if
                         oPriceObj.valid_to_date else "Present"),
                (oPriceObj.cutover_date.strftime('%m/%d/%Y') if
                 oPriceObj.cutover_date else "N/A")) +
                               ("\nPrice Erosion (%): {}".format(
                                   oPriceObj.erosion_rate) if
                                oPriceObj.price_erosion else ""))

            # Attempt to find PricingObjects that match for previous years,
            # going back 4 years
            for i in range(1, 5):
                # Retrieve PricingObject
                oChainPriceObj = PricingObject.objects.filter(
                    part__product_number=oPriceObj.part.product_number,
                    customer__name=aAvailableCU,  # For S-05923: Pricing, changed to aAvailableCU
                    sold_to=oPriceObj.sold_to,
                    spud=oPriceObj.spud,
                    technology=oPriceObj.technology,
                    valid_to_date__year=datetime.datetime.now().year - i
                ).order_by('valid_to_date', 'valid_from_date').first()

                # If such a match exists, add it to the lists
                if oChainPriceObj:
                    aObj.append(oChainPriceObj.unit_price)
                    aCommentRow.append(
                        "Valid: {}\nCut-over: {}".format(
                            (oChainPriceObj.valid_from_date.strftime(
                                '%m/%d/%Y') if oChainPriceObj.valid_from_date
                             else "N/A") + " - " + (
                                oChainPriceObj.valid_to_date.strftime(
                                    '%m/%d/%Y') if
                                oChainPriceObj.valid_to_date else "Present"),
                            (oChainPriceObj.cutover_date.strftime('%m/%d/%Y') if
                             oChainPriceObj.cutover_date else "N/A")) + (
                            "\nPrice Erosion (%): {}".format(
                                oChainPriceObj.erosion_rate) if
                            oChainPriceObj.price_erosion else "")
                    )
                else:
                    aObj.append('')
                    aCommentRow.append('')
                # end if
            # end for

            aPricingLines.append(aObj)
            aComments.append(aCommentRow)
        # end for
    # end if

    return aPricingLines, aComments


@login_required
def PriceErosion(oRequest):
    """
    View for viewing and editing pricing information eligible for erosion
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    sTemplate = 'BoMConfig/erosionpricing.html'
    sStatusMessage = None
    # For S-05923: Pricing added belwo lines
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

    # Determine user permissions
    bCanReadPricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Read').filter(
        user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(
        title='Detailed_Price_Write').filter(
        user__in=oRequest.user.groups.all()))

    # If POSTing save data
    if oRequest.POST:
        # If list of records was posted (records were actually selected)
        aRecords = json.loads(oRequest.POST['formData'])
        if any(itertools.chain.from_iterable(aRecords)):
            try:
                for aRecord in aRecords:
                    # Record has been selected for erosion
                    if StrToBool(aRecord[0]):
                        # Retrieve currently existing PricingObject
                        oCurrentPriceObj = PricingObject.objects.get(
                            price_erosion=True,
                            is_current_active=True,
                            part__product_number=aRecord[1],
                            customer__name=aAvailableCU, # For S-05923: Pricing changed to aAvailableCU
                            sold_to=aRecord[3] if aRecord[3] not in
                            ('', '(None)', None) else None,
                            spud__name=aRecord[4] if aRecord[4] not in
                            ('', '(None)', None) else None,
                            technology__name=aRecord[5] if aRecord[5] not in
                            ('', '(None)', None) else None)

                        # Create new PricingObject from existing object and
                        # posted data
                        oNewPriceObj = PricingObject.objects.create(
                            part=PartBase.objects.get(
                                product_number__iexact=aRecord[1]),
                            customer=REF_CUSTOMER.objects.get(name=aRecord[2]),
                            sold_to=aRecord[3] if aRecord[3] not in
                            ('(None)', None, '', 'null') else None,
                            spud=REF_SPUD.objects.get(
                                name=aRecord[4]) if aRecord[4] not in
                            ('(None)', '', None, 'null') else None,
                            technology=REF_TECHNOLOGY.objects.get(
                                name=aRecord[5]) if aRecord[5] not in
                            ('(None)', '', None, 'null') else None,
                            is_current_active=True,
                            unit_price=aRecord[8],
                            valid_to_date=datetime.datetime.strptime(
                                aRecord[10],
                                '%m/%d/%Y').date() if aRecord[10] else None,
                            valid_from_date=datetime.datetime.strptime(
                                aRecord[9],
                                '%m/%d/%Y').date() if aRecord[9] else
                            datetime.datetime.now().date(),
                            cutover_date=datetime.datetime.strptime(
                                aRecord[9],
                                '%m/%d/%Y').date() if aRecord[9] else
                            datetime.datetime.now().date(),
                            price_erosion=True,
                            erosion_rate=aRecord[7],
                            previous_pricing_object=oCurrentPriceObj)

                        # mark old object as inactive
                        oCurrentPriceObj.is_current_active = False
                        oCurrentPriceObj.save()

                        dFilterArgs = {
                            'config__header__configuration_status__name__in':
                                ('In Process', 'In Process/Pending'),
                            'part__base': PartBase.objects.get(
                                product_number__iexact=aRecord[1]),
                            'config__header__customer_unit':
                                aAvailableCU} # For S-05923: Pricing changed to aAvailableCU

                        # Update pricing information for any configuration which
                        # used the previous PricingObject
                        for oConfigLine in ConfigLine.objects.filter(
                                **dFilterArgs):
                            if oConfigLine.config.header\
                                    .configuration_status.name != 'In Process' \
                                    and oConfigLine.config.header.latesttracker\
                                    .next_approval != 'cpm':
                                continue

                            if not hasattr(oConfigLine, 'linepricing'):
                                LinePricing.objects.create(
                                    {'config_line': oConfigLine})

                            oLinePrice = oConfigLine.linepricing
                            if PricingObject.getClosestMatch(oConfigLine) == \
                                    oNewPriceObj:
                                oLinePrice.pricing_object = oNewPriceObj
                                oLinePrice.save()
                            # end if
                        # end for
                    # end if
                # end for
                sStatusMessage = 'Saved successfully'
            except PricingObject.DoesNotExist:
                sStatusMessage = 'Invalid selection'
            # end try
        else:
            sStatusMessage = 'No record(s) selected'
        # end if
    # end if

    aRecords = PricingObject.objects.filter(
        price_erosion=True,
        is_current_active=True).filter(customer_id__in=aAvailableCU).order_by(
        'part__product_number', 'customer__name', 'sold_to', 'spud__name') # For S-05923: Pricing added .filter

    dContext = {
        'data': [['False',
                  oPO.part.product_number,
                  oPO.customer.name,
                  oPO.sold_to or "(None)",
                  oPO.spud.name if oPO.spud else '(None)',
                  oPO.technology.name if oPO.technology else "(None)",
                  oPO.unit_price,
                  oPO.erosion_rate,
                  '', '', ''] for oPO in aRecords],
        'cu_list': sorted(list(set(str(val) for val in aRecords.values_list(
            'customer__name', flat=True)))),
        'soldto_list': sorted(list(set(str(val) for val in aRecords.values_list(
            'sold_to', flat=True)))),
        'spud_list': sorted(list(set(str(val) for val in aRecords.values_list(
            'spud__name', flat=True)))),
        'tech_list': sorted(list(set(str(val) for val in aRecords.values_list(
            'technology__name', flat=True)))),
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
        'status_message': sStatusMessage
    }
    return Default(oRequest, sTemplate, dContext)


def ErosionAjax(oRequest):
    """
    View/Function to provide list of PricingObjects that are eligible for
    erosion and match search criteria provided
    :param oRequest: Django HTTP request object
    :return: JSON Response containing new table data
    """
    # Create filter arguments from POSTed data (if any)
    dArgs = {'price_erosion': True,
             'is_current_active': True}

    if oRequest.POST['customer'] != 'all':
        dArgs['customer__name'] = oRequest.POST['customer']

    if oRequest.POST['sold_to'] != 'all':
        if oRequest.POST['sold_to'] != 'None':
            dArgs['sold_to'] = oRequest.POST['sold_to']
        else:
            dArgs['sold_to'] = None

    if oRequest.POST['spud'] != 'all':
        if oRequest.POST['spud'] != 'None':
            dArgs['spud__name'] = oRequest.POST['spud']
        else:
            dArgs['spud'] = None

    if oRequest.POST['technology'] != 'all':
        if oRequest.POST['technology'] != 'None':
            dArgs['technology__name'] = oRequest.POST['technology']
        else:
            dArgs['technology'] = None

    # Retrieve PricingObjects that match filter parameters
    aRecords = PricingObject.objects.filter(**dArgs).order_by(
        'part__product_number', 'customer', 'sold_to', 'spud')

    # Return JSON of table data
    return JsonResponse([['False',
                          oPO.part.product_number,
                          oPO.customer.name,
                          oPO.sold_to or "(None)",
                          oPO.spud.name if oPO.spud else '(None)',
                          oPO.technology.name if oPO.technology else "(None)",
                          oPO.unit_price,
                          oPO.erosion_rate,
                          '',
                          '',
                          ''] for oPO in aRecords] if aRecords else [[]],
                        safe=False)
# end def