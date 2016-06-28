__author__ = 'epastag'

from django.http import JsonResponse, Http404, QueryDict
from django.db import IntegrityError

from BoMConfig.models import Header, Baseline, SecurityPermission, Baseline_Revision
from BoMConfig.forms import SubmitForm
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue, RollbackBaseline

from functools import cmp_to_key
import json


aHeaderList = None


def BaselineLoad(oRequest):
    """This method is used as a landing page for Baseline Management while the useful view loads"""
    return Default(oRequest, sTemplate='BoMConfig/baselineload.html')


def BaselineMgmt(oRequest):
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

    bDownloadable = False
    dTableData = None
    aTable = []

    if oRequest.method == 'POST' and oRequest.POST:
        form = SubmitForm(oRequest.POST)
        if form.is_valid():
            oBaseline = Baseline.objects.get(title__iexact=form.cleaned_data['baseline_title'])

            # First get list of revisions going back to 'A'
            aRevisions = sorted(list(set([oBaseRev.version for oBaseRev in oBaseline.baseline_revision_set.order_by('version')])),
                                key=cmp_to_key(lambda x,y:(-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                 or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))
                                                                 or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1)),
                                reverse=True)

            dTableData = {'baseline': oBaseline.title, 'revisions':[]}

            for sRev in aRevisions:
                aHeads = Header.objects.filter(baseline__baseline=oBaseline).filter(baseline_version=sRev).order_by('configuration_status', 'pick_list', 'configuration_designation')
                if aHeads:
                    dTableData['revisions'].append({'revision': Baseline_Revision.objects.get(baseline=oBaseline, version=sRev), 'configs': aHeads})
                    if not bDownloadable:
                        bDownloadable = True
                # end if
            # end for
        # end if

        if dTableData:
            aTable = [dTableData]
        # end if
    else:
        form = SubmitForm()
        aBaselines = Baseline.objects.all()
        for oBaseline in aBaselines:
            aRevisions = sorted(list(set([oBaseRev.version for oBaseRev in oBaseline.baseline_revision_set.order_by('version') if oBaseRev.version in (oBaseRev.baseline.current_active_version, oBaseRev.baseline.current_inprocess_version)])),
                                key=cmp_to_key(lambda x,y:(-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                 or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))
                                                                 or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1)),
                                reverse=True)

            dTableData = {'baseline': oBaseline.title, 'revisions': []}

            for sRev in aRevisions:
                aHeads = Header.objects.filter(baseline__baseline=oBaseline).filter(baseline_version=sRev).order_by('configuration_status', 'pick_list', 'configuration_designation')
                if aHeads:
                    dTableData['revisions'].append({'revision': Baseline_Revision.objects.get(baseline=oBaseline, version=sRev), 'configs': aHeads})
                # end if
            # end for

            aTable.append(dTableData)
        # end for

        aTable.append(
            {
                'baseline':'No Associated Baseline',
                'revisions':[
                    {
                        'revision':'',
                        'configs': Header.objects.filter(baseline__isnull=True).order_by('configuration_status', 'pick_list', 'configuration_designation')
                    }
                ]
            }
        )
    # end if

    aTitles = ['', '', 'Configuration','Status','BoM Request Type','Program','Customer Number','Model','Model Description','Customer Price','Created Year',
               'Inquiry/Site Template Number','Model Replacing','Comments','Release Date','ZUST','P-Code','Plant']

    return Default(oRequest, sTemplate='BoMConfig/baselinemgmt.html', dContext={'form': form, 'tables': aTable, 'downloadable': bDownloadable, 'column_titles': aTitles})
# end def


def BaselineRollback(oRequest):
    data = QueryDict(oRequest.POST.get('form'))
    # data = json.loads(oRequest.POST.get('form'))

    oBaseline = Baseline.objects.get(title=data['baseline'])
    tOld = (oBaseline.current_active_version, oBaseline.current_inprocess_version)

    dResult = {
        'status': 0,
        'revision': '',
        'errors': []
    }

    try:
        RollbackBaseline(oBaseline)
        tNew = (oBaseline.current_active_version, oBaseline.current_inprocess_version)
        dResult['status'] = 1
        dResult['revision'] = 'from<br/><br/>{}<br/><br/>to<br/><br/>{}'.format(*('Active: {} / Inprocess: {}'.format(active, inproc) for (active, inproc) in (tOld, tNew)))
    except Exception as ex:
        dResult['errors'].append(str(ex))

    return JsonResponse(dResult)


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
    sConfig = oRequest.POST.get('config', None)

    global aHeaderList
    sTemplate='BoMConfig/overviewpricing.html'

    aHeaderList = Header.objects.filter(configuration_status__name='Active').order_by('baseline', 'pick_list')
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
        '7': GrabValue(oLine.linepricing, 'pricing_object.unit_price') if oLine.linepricing.pricing_object and
            (oLine.config.header.pick_list or str(oLine.line_number) != '10') else '0',
        '8': str(float(oLine.order_qty or 0) * float(GrabValue(oLine.linepricing, 'pricing_object.unit_price') or 0)),
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
