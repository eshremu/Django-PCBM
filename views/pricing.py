from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from BoMConfig.models import Header, Configuration, ConfigLine, PartBase, LinePricing, REF_CUSTOMER,\
    SecurityPermission, REF_SPUD, PricingObject
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue

import json
import datetime


def PartPricing(oRequest):
    bCanReadPricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Read').filter(user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Write').filter(user__in=oRequest.user.groups.all()))

    dContext = {
        'partlines': []
    }

    status_message = ''

    if oRequest.method == 'POST' and oRequest.POST:
        sPartNumber = oRequest.POST.get('part', None)

        if sPartNumber:
            sPartNumber = sPartNumber.upper()
            dContext['part'] = sPartNumber
            try:
                oPart = PartBase.objects.get(product_number__iexact=sPartNumber)
                if Header.objects.filter(configuration_designation=oPart.product_number):
                    raise Header.DoesNotExist()

                if oRequest.POST.get('action') == 'save':
                    sPartNumber = oRequest.POST.get('initial', None)
                    oPart = PartBase.objects.get(product_number__iexact=sPartNumber)

                    aDataToSave = json.loads(oRequest.POST.get('data_form'))
                    for aRowToSave in aDataToSave:
                        # Skip empty rows
                        if not any(aRowToSave):
                            continue

                        try:
                            oCurrentPriceObj = PricingObject.objects.get(
                                part__product_number__iexact=aRowToSave[0] or oRequest.POST.get('initial', None),
                                customer__name=aRowToSave[1],
                                sold_to=aRowToSave[2] if aRowToSave[2] not in ('', '(None)') else None,
                                spud__name=aRowToSave[3] if aRowToSave[3] not in ('', '(None)') else None,
                                is_current_active=True
                            )
                        except PricingObject.DoesNotExist:
                            oCurrentPriceObj = None

                        # Updating entry with $0 as price or updating comments will modify current PriceObject in-place
                        if oCurrentPriceObj and ((oCurrentPriceObj.unit_price == 0 and float(aRowToSave[4]) != 0) or
                                                 (oCurrentPriceObj.comments != aRowToSave[10])):
                            if oCurrentPriceObj.unit_price == 0 and float(aRowToSave[4]) != 0:
                                oCurrentPriceObj.unit_price = aRowToSave[4]
                            if oCurrentPriceObj.comments != aRowToSave[10]:
                                oCurrentPriceObj.comments = aRowToSave[10]
                            oCurrentPriceObj.save()

                        # Creating a new PriceObject or changing price, erosion, erosion rate, or cut-over date
                        # generates new current PriceObject
                        elif not oCurrentPriceObj or \
                                oCurrentPriceObj.unit_price != float(aRowToSave[4]) or \
                                (aRowToSave[5] and datetime.datetime.strptime(aRowToSave[5],
                                                                              '%m/%d/%Y').date() != oCurrentPriceObj.valid_to_date) or \
                                (aRowToSave[6] and datetime.datetime.strptime(aRowToSave[6],
                                                                              '%m/%d/%Y').date() != oCurrentPriceObj.valid_from_date) or \
                                (aRowToSave[7] and datetime.date.today() <= datetime.datetime.strptime(
                                    aRowToSave[7], '%m/%d/%Y').date() != oCurrentPriceObj.cutover_date) or \
                                oCurrentPriceObj.price_erosion != eval(aRowToSave[8]) or \
                                (aRowToSave[9] and oCurrentPriceObj.erosion_rate != float(aRowToSave[9])):
                            if oCurrentPriceObj:
                                oCurrentPriceObj.is_current_active = False
                                oCurrentPriceObj.valid_to_date = datetime.date.today()
                                oCurrentPriceObj.save()

                            try:
                                PricingObject.objects.create(part=PartBase.objects.get(product_number__iexact=aRowToSave[0] or oRequest.POST.get('initial', None)),
                                                             customer=REF_CUSTOMER.objects.get(name=aRowToSave[1]),
                                                             sold_to=aRowToSave[2] if aRowToSave[2] not in ('(None)', None, '', 'null') else None,
                                                             spud=REF_SPUD.objects.get(name=aRowToSave[3]) if aRowToSave[3] not in ('(None)', '', None, 'null') else None,
                                                             is_current_active=True,
                                                             unit_price=aRowToSave[4],
                                                             valid_to_date=datetime.datetime.strptime(aRowToSave[5], '%m/%d/%Y').date() if aRowToSave[5] else None,
                                                             valid_from_date=datetime.datetime.strptime(aRowToSave[6], '%m/%d/%Y').date() if aRowToSave[6] else None,
                                                             cutover_date=datetime.datetime.strptime(aRowToSave[7], '%m/%d/%Y').date() if aRowToSave[7] else None,
                                                             price_erosion=eval(aRowToSave[8]) if aRowToSave[8] else False,
                                                             erosion_rate=float(aRowToSave[9]) if aRowToSave[9] else None,
                                                             comments=aRowToSave[10],
                                                             previous_pricing_object=oCurrentPriceObj)
                            except Exception as ex:
                                status_message = "ERROR: " + str(ex)

                aCustomers = REF_CUSTOMER.objects.all()
                aSPUDS = REF_SPUD.objects.all()

                aPriceObjs = PricingObject.objects.filter(part=oPart, is_current_active=True).order_by('customer',
                                                                                                       'sold_to', 'spud')
                for oPriceObj in aPriceObjs:
                    dContext['partlines'].append([
                        oPriceObj.part.product_number,
                        oPriceObj.customer.name,
                        oPriceObj.sold_to or '(None)',
                        getattr(oPriceObj.spud, 'name', '(None)'),
                        oPriceObj.unit_price or '',
                        oPriceObj.valid_to_date.strftime('%m/%d/%Y') if oPriceObj.valid_to_date else '',  # Valid-To
                        oPriceObj.valid_from_date.strftime('%m/%d/%Y') if oPriceObj.valid_from_date else '',  # Valid-from
                        oPriceObj.cutover_date.strftime('%m/%d/%Y') if oPriceObj.cutover_date else '',  # Cut-over
                        str(oPriceObj.price_erosion),  # Erosion
                        oPriceObj.erosion_rate or '',  # Erosion rate
                        oPriceObj.comments or '',  # Comments
                    ])

                dContext.update({
                    'customer_list': [oCust.name for oCust in aCustomers],
                    'spud_list': [oSpud.name for oSpud in aSPUDS],
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

    if not dContext['partlines']:
        if oRequest.POST.get('part') and not status_message:
            dContext['partlines'] = [[oRequest.POST.get('part', ''), '', '', '', '', '', '', '', '', '','']]
        elif oRequest.POST.get('initial') and not status_message:
            dContext['partlines'] = [[oRequest.POST.get('initial', ''), '', '', '', '', '', '', '', '', '','']]
        else:
            dContext['partlines'] = [[]]

    return Default(oRequest, sTemplate='BoMConfig/partpricing.html', dContext=dContext)


def ConfigPricing(oRequest):

    bCanReadPricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Read').filter(user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Write').filter(user__in=oRequest.user.groups.all()))

    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except:
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
    dContext = {'configlines':aConfigLines, 'readonly': False}
    if oRequest.method == 'POST' and oRequest.POST:
        sConfig = oRequest.POST['config'] if 'config' in oRequest.POST else None

        iProgram = oRequest.POST.get('program', None)
        iBaseline = oRequest.POST.get('baseline', None)
        if 'action' in oRequest.POST and oRequest.POST['action'] == 'search':
            iProgram = None
            iBaseline = None

        aConfigMatches = Header.objects.filter(configuration_designation__iexact=sConfig)#, configuration_status__name__startswith='In Process')
        if iProgram:
            aConfigMatches = aConfigMatches.filter(program__id=iProgram)
        if iBaseline:
            aConfigMatches = aConfigMatches.filter(baseline__id=iBaseline)

        if len(aConfigMatches) == 0:
            status_message = 'No matching configuration found'
            dContext.update({'config': sConfig})
        elif len(aConfigMatches) > 1:
            aProgramList = list([oHead.program.id, oHead.program.name] for oHead in aConfigMatches)
            aBaselineList = list([oHead.baseline.id, str(oHead.baseline)] if oHead.baseline else [None, ''] for oHead in aConfigMatches)
            dContext.update({'prog_list': aProgramList, 'config': sConfig, 'base_list': aBaselineList})
        else:
            iProgValue = aConfigMatches[0].program.id if aConfigMatches[0].program else None
            iBaseValue = aConfigMatches[0].baseline.id if aConfigMatches[0].baseline else None

            dLineFilters = {
                # 'config__header__configuration_status__name__startswith': 'In Process',
                'config__header__configuration_designation__iexact':sConfig,
            }
            dConfigFilters = {
                # 'header__configuration_status__name__startswith': 'In Process',
                'header__configuration_designation__iexact':sConfig,
            }

            if iProgValue is not None:
                dLineFilters.update({'config__header__program__id': iProgValue})
                dConfigFilters.update({'header__program__id': iProgValue})
            else:
                dLineFilters.pop('config__header__program__id', None)
                dConfigFilters.pop('header__program__id', None)

            if iBaseValue is not None:
                dLineFilters.update({'config__header__baseline__id': iBaseValue})
                dConfigFilters.update({'header__baseline__id': iBaseValue})
            else:
                dLineFilters.pop('config__header__baseline__id', None)
                dConfigFilters.pop('header__baseline__id', None)

            if 'action' in oRequest.POST and oRequest.POST['action'] == 'save':
                if oRequest.POST['config'] == oRequest.POST['initial']:
                    net_total = 0
                    for dLine in json.loads(oRequest.POST['data_form']):
                        # Change dLine to dict with str keys
                        if isinstance(dLine, list):
                            dLine = {str(key): val for (key, val) in enumerate(dLine)}
                        elif isinstance(dLine, dict):
                            dLine = {str(key): val for (key, val) in dLine.items()}

                        dLineFilters.update({'line_number': dLine['0']})

                        oLineToEdit = ConfigLine.objects.filter(**dLineFilters)[0]
                        oLinePrice = LinePricing.objects.get(config_line=oLineToEdit)
                        oLinePrice.override_price = dLine['7'] or None

                        if not oLineToEdit.config.header.pick_list and dLine['0'] == '10':
                            net_total = float(dLine['6'])
                        elif oLineToEdit.config.header.pick_list:
                            net_total += float(dLine['6'])

                        oLinePrice.save()
                    # end for
                    dLineFilters.pop('line_number', None)

                    oConfig = Configuration.objects.get(**dConfigFilters)
                    oConfig.override_net_value = float(oRequest.POST['net_value'])
                    oConfig.net_value = net_total
                    oConfig.save()

                    status_message = 'Data saved.'
                else:
                    status_message = 'Cannot change configuration during save.'
                    sConfig = oRequest.POST['initial']
                # end if
            # end if

            aLine = ConfigLine.objects.filter(**dLineFilters)
            aLine = sorted(aLine, key=lambda x: ([int(y) for y in x.line_number.split('.')]))

            aConfigLines = [{
                '0': oLine.line_number,
                '1': ('..' if oLine.is_grandchild else '.' if oLine.is_child else '') + oLine.part.base.product_number,
                '2': str(oLine.part.base.product_number) + str('_'+ oLine.spud.name if oLine.spud else ''),
                '3': oLine.part.product_description,
                '4': float(oLine.order_qty if oLine.order_qty else 0),
                '5': float(GrabValue(oLine,'linepricing.pricing_object.unit_price', 0)),
                '6': float(oLine.order_qty or 0) * float(GrabValue(oLine,'linepricing.pricing_object.unit_price', 0)),
                '7': GrabValue(oLine,'linepricing.override_price', ''),
                '8': oLine.higher_level_item or '',
                '9': oLine.material_group_5 or '',
                '10': oLine.commodity_type or '',
                '11': oLine.comments or '',
                '12': oLine.additional_ref or ''
                            } for oLine in aLine]

            if not aLine[0].config.header.pick_list:
                config_total = sum([float(line['6']) for line in aConfigLines])
                aConfigLines[0]['5'] = aConfigLines[0]['6'] = str(config_total)

            dContext['configlines'] = aConfigLines
            dContext.update({'config': sConfig,
                             'is_not_pick_list': not aLine[0].config.header.pick_list if aLine else False,
                             'program': iProgValue,
                             'baseline': iBaseValue,
                             'prog_list': [],
                             'base_list': [],
                             'readonly': 'In Process' not in aLine[0].config.header.configuration_status.name
                             })
        # end if
    # end if

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)


def OverviewPricing(oRequest):
    bCanReadPricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Read').filter(user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Write').filter(user__in=oRequest.user.groups.all()))

    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'status' in oRequest.session:
        del oRequest.session['status']
    # end if

    status_message = None

    sTemplate='BoMConfig/overviewpricing.html'

    aPricingObjectList = PricingObject.objects.filter(is_current_active=True).order_by('part', 'customer', 'sold_to', 'spud')

    aPricingLines = []
    aComments = []

    if aPricingObjectList:
        for oPriceObj in aPricingObjectList:
            aCommentRow = []
            dObj = [
                oPriceObj.part.product_number,
                oPriceObj.customer.name,
                oPriceObj.sold_to or '(None)',
                oPriceObj.spud.name if oPriceObj.spud else '(None)',
                oPriceObj.unit_price,
            ]

            aCommentRow.append("Valid: {}\nCut-over: {}".format((oPriceObj.valid_from_date.strftime('%m/%d/%Y') if oPriceObj.valid_from_date else "N/A") +
                                                                " - " + (oPriceObj.valid_to_date.strftime('%m/%d/%Y') if oPriceObj.valid_to_date else "Present"),
                                                                (oPriceObj.cutover_date.strftime('%m/%d/%Y') if oPriceObj.cutover_date else "N/A")) +
                               ("\nPrice Erosion (%): {}".format(oPriceObj.erosion_rate) if oPriceObj.price_erosion else ""))

            oChainPriceObj = oPriceObj
            while oChainPriceObj.previous_pricing_object:
                oChainPriceObj = oChainPriceObj.previous_pricing_object
                dObj.append(oChainPriceObj.unit_price)
                aCommentRow.append("Valid: {}\nCut-over: {}".format((oChainPriceObj.valid_from_date.strftime('%m/%d/%Y') if oChainPriceObj.valid_from_date else "N/A") +
                                                                    " - " + (oChainPriceObj.valid_to_date.strftime('%m/%d/%Y') if oChainPriceObj.valid_to_date else "Present"),
                                                                    (oChainPriceObj.cutover_date.strftime('%m/%d/%Y') if oChainPriceObj.cutover_date else "N/A")) +
                                   ("\nPrice Erosion (%): {}".format(oChainPriceObj.erosion_rate) if oChainPriceObj.price_erosion else ""))

            aPricingLines.append(dObj)
            aComments.append(aCommentRow)
    # end if

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

