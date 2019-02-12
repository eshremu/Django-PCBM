"""
View related to viewing, editing, and downloading pricing information
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from BoMConfig.models import Header, Configuration, ConfigLine, PartBase, \
    LinePricing, REF_CUSTOMER, SecurityPermission, REF_SPUD, PricingObject, \
    REF_TECHNOLOGY, HeaderTimeTracker,User_Customer
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue, StrToBool

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
                    aDataToSave = json.loads(oRequest.POST.get('data_form'))
                    for aRowToSave in aDataToSave:
                        # Skip empty rows
                        if not any(aRowToSave):
                            continue

                        # Retrieve PricingObject that matches the data provided,
                        # if it exists
                        try:
                            oCurrentPriceObj = PricingObject.objects.get(
                                part__product_number__iexact=aRowToSave[0] or
                                oRequest.POST.get('initial', None),
                                customer__name=aRowToSave[1], # D-04625: New row populated when editing data in Unit Price Management removed if aRowToSave[1] in aAvailableCU else None
                                sold_to=aRowToSave[2] if aRowToSave[2] not in
                                ('', '(None)') else None,
                                spud__name=aRowToSave[3] if aRowToSave[3] not in
                                ('', '(None)') else None,
                                technology__name=aRowToSave[4] if aRowToSave[4]
                                not in ('', '(None)') else None,
                                is_current_active=True
                            )
                        except PricingObject.DoesNotExist:
                            oCurrentPriceObj = None

                        # Creating a new PriceObject or changing price, erosion,
                        # erosion rate, or cut-over date generates new current
                        # PriceObject
                        # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(line 110,107,swapped valid to and valid from field)
                        if not oCurrentPriceObj or \
                                oCurrentPriceObj.unit_price != float(
                                    aRowToSave[5]) or \
                                (aRowToSave[6] and
                                    datetime.datetime.strptime(aRowToSave[6],
                                                               '%m/%d/%Y'
                                                               ).date() !=
                                    oCurrentPriceObj.valid_from_date) or \
                                (aRowToSave[7] and datetime.datetime.strptime(
                                    aRowToSave[7], '%m/%d/%Y').date() !=
                                    oCurrentPriceObj.valid_to_date) or \
                                (aRowToSave[8] and datetime.date.today() <=
                                    datetime.datetime.strptime(aRowToSave[8],
                                                               '%m/%d/%Y'
                                                               ).date() !=
                                    oCurrentPriceObj.cutover_date) or \
                                oCurrentPriceObj.price_erosion != eval(
                                    aRowToSave[9]) or \
                                (aRowToSave[10] and
                                    oCurrentPriceObj.erosion_rate != float(
                                         aRowToSave[10])):

                            # Mark the previous match as 'inactive'
    # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(changed aRowToSave[7] to aRowToSave[6]
                            if oCurrentPriceObj:
                                oCurrentPriceObj.is_current_active = False
                                oCurrentPriceObj.valid_to_date = max(
                                    datetime.date.today(),
                                    datetime.datetime.strptime(
                                        aRowToSave[6],
                                        '%m/%d/%Y').date() if aRowToSave[6] else
                                    datetime.date.today()
                                )
                                oCurrentPriceObj.save()

                            # Create a new PricingObject
                            try:
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
                                    technology=REF_TECHNOLOGY.objects.get(
                                        name=aRowToSave[4]) if aRowToSave[4] not
                                    in ('(None)', '', None, 'null') else None,
                                    is_current_active=True,
                                    unit_price=aRowToSave[5],
# S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers(changed valid_to_date to aRowToSave[7] and valid_from_date to aRowToSave[6]
                                    valid_from_date=datetime.datetime.strptime(
                                        aRowToSave[6],
                                        '%m/%d/%Y'
                                    ).date() if aRowToSave[6] else None,
                                    valid_to_date=datetime.datetime.strptime(
                                        aRowToSave[7],
                                        '%m/%d/%Y'
                                    ).date() if aRowToSave[7] else None,
                                    cutover_date=datetime.datetime.strptime(
                                        aRowToSave[8],
                                        '%m/%d/%Y'
                                    ).date() if aRowToSave[8] else None,
                                    price_erosion=eval(
                                        aRowToSave[9]
                                    ) if aRowToSave[9] else False,
                                    erosion_rate=float(
                                        aRowToSave[10]
                                    ) if aRowToSave[10] else None,
                                    comments=aRowToSave[11],
                                    previous_pricing_object=oCurrentPriceObj
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
                        elif oCurrentPriceObj and (
                                    oCurrentPriceObj.comments != aRowToSave[11]
                        ):
                            if oCurrentPriceObj.comments != aRowToSave[11]:
                                oCurrentPriceObj.comments = aRowToSave[11]
                            oCurrentPriceObj.save()
                        # end if
                    # end for
                # end if

                # Retrieve all active PricingObjects that are associated to the
                # PartBase
                aPriceObjs = PricingObject.objects.filter(
                    part=oPart,
                    is_current_active=True).order_by('customer__name',
                                                     'sold_to', 'spud__name')

                # Create table data from list of objects
                for oPriceObj in aPriceObjs.filter(customer__in=aAvailableCU): # S-05923: Pricing - Restrict View to allowed CU's based on permissions added filter

                    dContext['partlines'].append([
                        oPriceObj.part.product_number,
                        oPriceObj.customer.name,
                        oPriceObj.sold_to or '(None)',
                        getattr(oPriceObj.spud, 'name', '(None)'),
                        getattr(oPriceObj.technology, 'name', '(None)'),
                        oPriceObj.unit_price or '',
                        # S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers
                        oPriceObj.valid_from_date.strftime('%m/%d/%Y') if
                        oPriceObj.valid_from_date else '',  # Valid-from
                        oPriceObj.valid_to_date.strftime('%m/%d/%Y') if
                        oPriceObj.valid_to_date else '',  # Valid-To
                        oPriceObj.cutover_date.strftime('%m/%d/%Y') if
                        oPriceObj.cutover_date else '',  # Cut-over
                        str(oPriceObj.price_erosion),  # Erosion
                        oPriceObj.erosion_rate or '',  # Erosion rate
                        oPriceObj.comments or '',  # Comments
                    ])

                dContext.update({
                    'customer_list': [
                        oCust.name for oCust in aAvailableCU], # S-05923: Pricing - Restrict View to allowed CU's based on permissions added aAvailableCU
                    'spud_list': [
                        oSpud.name for oSpud in REF_SPUD.objects.filter(is_inactive=0)], # S-05909 : Edit drop down option for BoM Entry Header - SPUD: Added to filter dropdown data in pricing page
                    'tech_list': [
                        oTech.name for oTech in REF_TECHNOLOGY.objects.filter(is_inactive=0)] # S-05905 : Edit drop down option for BoM Entry Header - Technology: Added to filter dropdown data in pricing page
                })
            except (PartBase.DoesNotExist,):
                status_message = 'ERROR: Part number not found'
            except Header.DoesNotExist:
                status_message = 'ERROR: Configuration Number provided'

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    # Create a blank default table if no PricingObjects currently exist for the
    # part number provided
    if not dContext['partlines']:
        if oRequest.POST.get('part') and not status_message:
            dContext['partlines'] = [[oRequest.POST.get('part', ''), '', '', '',
                                      '', '', '', '', '', '', '', '']]
        elif oRequest.POST.get('initial') and not status_message:
            dContext['partlines'] = [[oRequest.POST.get('initial', ''), '', '',
                                      '', '', '', '', '', '', '', '', '']]
        else:
            dContext['partlines'] = [[]]

    return Default(oRequest, sTemplate='BoMConfig/partpricing.html',
                   dContext=dContext)


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
            aBaselineList = list(
                [oHead.baseline.id, str(oHead.baseline)] if oHead.baseline else
                ['None', '(No Baseline)'] for oHead in aConfigMatches
            )
            dContext.update(
                {'prog_list': aProgramList, 'config': sConfig,
                 'base_list': aBaselineList})

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
                '3': oLine.part.product_description,
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