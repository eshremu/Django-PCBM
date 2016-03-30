__author__ = 'epastag'

from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout as auth_logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseRedirect, HttpResponse, QueryDict, JsonResponse, Http404
from django.core.urlresolvers import reverse, resolve
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.db import connections, IntegrityError
from django import forms
from django.contrib.auth.models import Group

from BoMConfig.models import NewsItem, Alert, Header, Part, Configuration, ConfigLine,\
    PartBase, Baseline, Baseline_Revision, LinePricing, REF_CUSTOMER, REF_REQUEST, HeaderLock, SecurityPermission, ParseException,\
    REF_TECHNOLOGY, REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, REF_CUSTOMER_NAME, REF_PROGRAM, REF_CONDITION, REF_MATERIAL_GROUP,\
    REF_PRODUCT_PKG, REF_SPUD, HeaderTimeTracker, REF_RADIO_BAND, REF_RADIO_FREQUENCY, PricingObject
from BoMConfig import menulisting, headerFile, footerFile, pagetitle, supportcontact
from BoMConfig.forms import HeaderForm, ConfigForm, DateForm, FileUploadForm, SubmitForm
from BoMConfig.templatetags.customtemplatetags import searchscramble
from BoMConfig.BillOfMaterials import BillOfMaterials
from BoMConfig.utils import UpRev, MassUploaderUpdate, GenerateRevisionSummary
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue

import copy
from itertools import chain
import json
import openpyxl
from openpyxl import utils
import os
import re
from functools import cmp_to_key
import traceback


aHeaderList = None
# aParts = None


def PartPricing(oRequest):
    bCanReadPricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Read').filter(user__in=oRequest.user.groups.all()))
    bCanWritePricing = bool(SecurityPermission.objects.filter(title='Detailed_Price_Write').filter(user__in=oRequest.user.groups.all()))

    # global aParts

    aHeaderParts = [head.configuration_designation for head in Header.objects.filter(pick_list=False)]
    # aParts = PartBase.objects.exclude(product_number__in=aHeaderParts).order_by('product_number')
    # aConFigLines = ConfigLine.objects.filter(config__header__configuration_status__name='Active').filter(part__base__product_number__in=aParts)
    # aCurrentPrices = PricingObject.objects.filter(is_current_active=True,)
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
                        oCurrentPriceObj = PricingObject.objects.get(part__product_number__iexact=aRowToSave[0],
                                                                     customer__name=aRowToSave[1],
                                                                     sold_to=aRowToSave[2],
                                                                     spud__name=aRowToSave[3], is_current_active=True)
                        if oCurrentPriceObj.unit_price == 0 and float(aRowToSave[4]) != 0:
                            oCurrentPriceObj.unit_price = aRowToSave[4]
                            oCurrentPriceObj.save()
                        elif oCurrentPriceObj.unit_price != float(aRowToSave[4]):
                            oCurrentPriceObj.is_current_active = False
                            oCurrentPriceObj.save()
                            PricingObject.objects.create(part=PartBase.objects.get(product_number__iexact=aRowToSave[0]),
                                                         customer=REF_CUSTOMER.objects.get(name=aRowToSave[1]),
                                                         sold_to=aRowToSave[2],
                                                         spud=REF_SPUD.objects.get(name=aRowToSave[3]),
                                                         is_current_active=True,
                                                         unit_price=aRowToSave[4],
                                                         previous_pricing_object=oCurrentPriceObj)

                for oCustomer in REF_CUSTOMER.objects.all():
                    oCursor = connections['REACT'].cursor()
                    oCursor.execute('SELECT DISTINCT [SoldTo] FROM ps_fas_contracts WHERE [CustomerUnit]=%s',[oCustomer.name])
                    tResults = oCursor.fetchall()

                    for (iSoldTo,) in tResults:
                        for oSpud in REF_SPUD.objects.all():
                            (oPriceObj,_) = PricingObject.objects.get_or_create(part=oPart, customer=oCustomer, sold_to=iSoldTo, spud=oSpud, is_current_active=True)
                            dContext['partlines'].append([oPart.product_number, oCustomer.name, iSoldTo, oSpud.name, oPriceObj.unit_price])
            except (PartBase.DoesNotExist, Header.DoesNotExist):
                status_message = 'Part number not found'

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate='BoMConfig/partpricing.html', dContext=dContext)


# def GetPartLine(oRequest):
#     if oRequest.method == 'GET':
#         raise Http404('Access Denied')
#     else:
#         global aParts
#         iIndex = int(oRequest.POST['count'])
#
#         aPartLines = []
#         if iIndex < len(aParts):
#             oPart = aParts[iIndex]
#
#             for oCustomer in REF_CUSTOMER.objects.all():
#                 oCursor = connections['REACT'].cursor()
#                 oCursor.execute('SELECT DISTINCT [SoldTo] FROM ps_fas_contracts WHERE [CustomerUnit]=%s',[oCustomer.name])
#                 tResults = oCursor.fetchall()
#
#                 for (iSoldTo,) in tResults:
#                     for oSpud in REF_SPUD.objects.all():
#                         # PricingObject.objects.get_or_create(part=oPart, customer=oCustomer, sold_to=iSoldTo, spud=oSpud)
#                         aPartLines.append([oPart.product_number, oCustomer.name, iSoldTo, oSpud.name, ''])
#
#         return JsonResponse(aPartLines, safe=False)


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
    dContext = {'configlines':aConfigLines}
    if oRequest.method == 'POST' and oRequest.POST:
        sConfig = oRequest.POST['config'] if 'config' in oRequest.POST else None
        if oRequest.POST['action'] == 'save':
            if oRequest.POST['config'] == oRequest.POST['initial']:
                for dLine in json.loads(oRequest.POST['data_form']):
                    oLineToEdit = ConfigLine.objects.filter(config__header__configuration_status__name='Active')\
                        .filter(config__header__configuration_designation__iexact=sConfig)\
                        .filter(line_number=dLine['0'])[0]
                    oLinePrice = LinePricing.objects.get(config_line=oLineToEdit)
                    oLinePrice.unit_price = dLine['5'] or None
                    oLinePrice.override_price = dLine['7'] or None
                    oLinePrice.save()
                # end for

                oConfig = Configuration.objects.get(header__configuration_designation__iexact=sConfig)
                oConfig.override_net_value = float(oRequest.POST['net_value'])
                oConfig.save()

                status_message = 'Data saved.'
            else:
                status_message = 'Cannot change configuration during save.'
                sConfig = oRequest.POST['initial']
            # end if
        # end if

        aLine = ConfigLine.objects.filter(config__header__configuration_designation__iexact=sConfig)
        aLine = sorted(aLine, key=lambda x: ([int(y) for y in x.line_number.split('.')]))

        aConfigLines = [{
            '0': oLine.line_number,
            '1': ('..' if oLine.is_grandchild else '.' if oLine.is_child else '') + oLine.part.base.product_number,
            '2': str(oLine.part.base.product_number) + str('_'+ oLine.spud if oLine.spud else ''),
            '3': oLine.part.product_description,
            '4': oLine.order_qty if oLine.order_qty else 0,
            '5': GrabValue(oLine.linepricing, 'pricing_object.unit_price') or 0,
            '6': str(float(oLine.order_qty or 0) * float(GrabValue(oLine.linepricing, 'pricing_object.unit_pricing') or 0)),
            '7': oLine.linepricing.override_price or '',
            '8': oLine.higher_level_item or '',
            '9': oLine.material_group_5 or '',
            '10': oLine.commodity_type or '',
            '11': oLine.comments or '',
            '12': oLine.additional_ref or ''
                        } for oLine in aLine]
        dContext['configlines'] = aConfigLines
        dContext.update({'config': sConfig, 'is_not_pick_list': not aLine[0].config.header.pick_list if aLine else False})

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
    sConfig = oRequest.POST['config'] if 'config' in oRequest.POST else None

    global aHeaderList
    sTemplate='BoMConfig/overviewpricing.html'

    aHeaderList = Header.objects.filter(configuration_status__name='Active').order_by('baseline','pick_list')
    # aLine = ConfigLine.objects.filter(config__header__configuration_status='Active')
    if aHeaderList:
        aLine = aHeaderList[0].configuration.configline_set.all()
        aLine = sorted(aLine, key=lambda x: ([int(y) for y in x.line_number.split('.')]))
        aLine = sorted(aLine, key=lambda x: (x.config.header.baseline.title if x.config.header.baseline else '',
                                             x.config.header.configuration_designation))
    else:
        aLine = []
    # end if

    aConfigLines = [{
        '0': oLine.config.header.baseline.title if oLine.config.header.baseline else oLine.config.header.configuration_designation,
        '1': oLine.line_number,
        '2': oLine.config.header.configuration_designation,
        '3': ('..' if oLine.is_grandchild else '.' if oLine.is_child else '') + oLine.part.base.product_number,
        '4': oLine.part.base.product_number,
        '5': oLine.order_qty if oLine.order_qty else 0,
        '6': oLine.part.product_description,
        '7': oLine.linepricing.pricing_object.unit_price if oLine.linepricing.pricing_object and
                                                            (oLine.config.header.pick_list or
                                                                 str(oLine.line_number) != '10') else '',
        '8': str(float(oLine.order_qty or 0) * float(oLine.linepricing.pricing_object.unit_price if oLine.linepricing.pricing_object else 0)),
        '9': oLine.linepricing.override_price or ''
                    } for oLine in aLine]

    dContext = {
        'configlines': aConfigLines
    }

    dContext.update({
        'status_message': status_message,
        'pricing_read_authorized': bCanReadPricing,
        'pricing_write_authorized': bCanWritePricing,
    })

    return Default(oRequest, sTemplate, dContext)
# end def


def GetConfigLines(oRequest):
    if oRequest.method == 'GET':
        raise Http404('Access Denied')
    else:
        global aHeaderList
        iMultiplier = int(oRequest.POST['multiplier'])

        if iMultiplier < len(aHeaderList):
            aLine = aHeaderList[iMultiplier].configuration.configline_set.all()
        else:
            aLine = []

        aLine = sorted(aLine, key=lambda x: [int(y) for y in x.line_number.split('.')])
        aLine = sorted(aLine, key=lambda x: (x.config.header.baseline.title if x.config.header.baseline else '',
                                             x.config.header.configuration_designation))

        aConfigLines = [{
            '0': oLine.config.header.baseline.title if oLine.config.header.baseline else oLine.config.header.configuration_designation,
            '1': oLine.line_number,
            '2': oLine.config.header.configuration_designation,
            '3': ('..' if oLine.is_grandchild else '.' if oLine.is_child else '') + oLine.part.base.product_number,
            '4': oLine.part.base.product_number,
            '5': oLine.order_qty if oLine.order_qty else 0,
            '6': oLine.part.product_description,
            '7': oLine.linepricing.pricing_object.unit_price if hasattr(oLine,'linepricing') and
                                                                oLine.linepricing.pricing_object
                                                                and (oLine.config.header.pick_list or
                                                                     str(oLine.line_number) != '10') else '',
            '8': str(float(oLine.order_qty or 0) * float(oLine.linepricing.pricing_object.unit_price if
                                                         hasattr(oLine,'linepricing') and
                                                         oLine.linepricing.pricing_object else 0)),
            '9': oLine.linepricing.override_price if hasattr(oLine,'linepricing') else ''
                        } for oLine in aLine]

        return JsonResponse(aConfigLines, safe=False)
    # end if
#end def