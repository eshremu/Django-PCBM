"""
Views related to searching database and returning search results
"""

from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.db.models import F
from django.contrib.auth.decorators import login_required

from BoMConfig.models import Header, ConfigLine, REF_REQUEST, REF_CUSTOMER, \
    REF_STATUS, REF_PROGRAM, REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, \
    REF_TECHNOLOGY, REF_RADIO_BAND, REF_RADIO_FREQUENCY, Baseline, User_Customer, Supply_Chain_Flow

from BoMConfig.templatetags.bomconfig_customtemplatetags import searchscramble
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue

import re
import functools
# S-11113: Multiple Selections and Choices on Dropdowns in Search / Advanced Search:- imported below package to evaluate in a simpler form
# eg.- ["green","red"] -> ['green','red']
import ast

@login_required
def Search(oRequest, advanced=False):
    """
    View for searching Headers
    :param oRequest: Django HTTP request object
    :param advanced: Boolean indicating if this request is for an advanced
    search
    :return: HTTPResponse containing search results
    """

    # S-06169: Search and Adv. Search restrict view to CU: added below 5lines
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

    if advanced:
        sTemplate = 'BoMConfig/searchadv.html'
    else:
        sTemplate = 'BoMConfig/search.html'
    # end if

    # Redirect as needed to single records
    readonly = oRequest.GET.get('readonly', False)
    link = oRequest.GET.get('link', None)
    config = oRequest.GET.get('config', None)
    if link or config:
        if link:
            if not readonly:
                oRequest.session['existing'] = link[5:-10]
                return redirect(reverse('bomconfig:configheader'))
            else:
                return redirect(reverse('bomconfig:configheader') +
                                ('?id=' + str(link[5:-10]) + '&readonly=1'))
        else:
            if not readonly:
                oRequest.session['existing'] = config[5:-10]
                return redirect(reverse('bomconfig:config'))
            else:
                return redirect(reverse('bomconfig:config') +
                                ('?id=' + str(config[5:-10]) + '&readonly=1'))
        # end if
    # end if

    # Start with all Header objects
    aHeaders = Header.objects.all()

    # If search parameters were POSTed
    if oRequest.method == 'POST' and oRequest.POST:
        # Create partial function for escaping special characters in strings
        oEscape = re.compile(r'([\^$+.\{\}\(\)\[\]\|\\])')
        escape = functools.partial(oEscape.sub, r'\\\1')

        # This is not an advanced search
        if not advanced:
            # Filter header list based on parameters POSTed
            if 'config_design' in oRequest.POST and \
                            oRequest.POST['config_design'] != '':
                aHeaders = aHeaders.filter(
                    configuration_designation__iregex="^" + escape(
                        oRequest.POST['config_design'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$")
            # end if

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aHeaders = aHeaders.filter(
                    person_responsible__iregex="^" + escape(
                        oRequest.POST['person'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$")
            # end if

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aHeaders = aHeaders.filter(
                    bom_request_type__name=oRequest.POST['request'])
            # end if

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                aHeaders = aHeaders.filter(
                    customer_unit=oRequest.POST['customer'])
            # end if

  # S - 11564: Search - Basic & Advanced adjustments - Added below block to filter based on CName in basic search
            if 'cuname' in oRequest.POST and oRequest.POST['cuname'] != '':
                aHeaders = aHeaders.filter(
                    customer_name=oRequest.POST['cuname'])
            # end if

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                aHeaders = aHeaders.filter(
                    configuration_status__name=oRequest.POST['status'].replace(
                        '_', ' ').title())
            else:
                aHeaders = aHeaders.filter(configuration_status__name='Active')
            # end if

            # Write search results to response
            results = HttpResponse()
            if aHeaders:
                results.write('<h5 style="color:red">Found ' +
                              str(len(aHeaders.filter(customer_unit_id__in=aAvailableCU))) + ' matching record(s)</h5>') # added .filter(customer_unit_id__in=aAvailableCU) for S-06169
                results.write(
                    '<table id="result_table"><thead><tr>'
                    '<th style="width: 20px;"><input class="selectall" '
                    'type="checkbox"/></th><th style="width:175px;">'
                    'Configuration</th><th style="25px;"></th>'
                    '<th style="width:175px;">Program</th>'
                    '<th style="width:175px;">Catalog</th>' #S-11548: Search - Advanced Search sub-tab changes: Changed Baseline to Catalog
                    '<th style="width:75px;">Version</th>'
                    '<th style="width:175px;">Person Responsible</th>'
                    '<th style="width:175px;">BoM Request Type</th>'
                    '<th style="width:175px;">Customer Unit</th>'
                    '<th style="width:175px;">Customer Name</th>'  # S-11564: Search - Basic & Advanced adjustments - Added to show the CName column in basic search resultset
                    '<th style="width:175px;">Status</th>'
                    # '<th>Readiness Complete</th>'   # S-12372- remove readiness complete in search/avd search page -commented out mentioned field to remove the field in Basic search reslut set
                    '</tr></thead><tbody>')
                for header in aHeaders:
                    if header.customer_unit in aAvailableCU:  # added for S-06169 Search and Adv. Search restrict view to CU
                       if header.baseline.isdeleted != 1:
        # S-11564: Search - Basic & Advanced adjustments - modified <td></td> to show cuname in list view
                            results.write(
                        ('<tr><td><input class="recordselect" type="checkbox" '
                         'value="{9}"/></td><td><a href="?link={0}">{1}</a>'
                         '</td><td><a href="?link={0}&readonly=1" '
                         'target="_blank"><span class="glyphicon '
                         'glyphicon-new-window" title="Open in new window">'
                         '</span></a></td><td>{2}</td><td>{10}</td><td>{3}</td>'
                         '<td>{4}</td><td>{5}</td><td>{6}</td><td>{7}</td>'
                         '<td>{8}</td>'
                         # '<td>{10}</td>'  # S-12372- remove readiness complete in search/avd search page -commented out mentioned <td>to remove the field in Basic search reslut set and set {11} to {10}in line 166
                         '</tr>'
                         ).format(
                            searchscramble(header.pk),
                            header.configuration_designation,
                            GrabValue(header, 'program.name') or '(None)',
                            header.baseline_version,
                            header.person_responsible,
                            header.bom_request_type.name,
                            header.customer_unit.name,
                            header.customer_name,  # S-11564: Search - Basic & Advanced adjustments - Added to show the CName column in basic search resultset
                            header.configuration_status.name,
                            header.pk,
                            # header.readiness_complete or 0, # S-12372- remove readiness complete in search/avd search page -commented out mentioned field to remove the field in Basic search reslut set
                            header.baseline.title if header.baseline else
                            '(Not Baselined)'
                        )
                    )
                # end for
                results.write(
                    '</tbody></table><div><button id="download" '
                    'class="btn btn-primary" style="margin-right: 5px;" '
                    'disabled>Download Records</button>'
                    '<button id="downloadcustom" class="btn btn-primary" '
                    'disabled>Download Results</button></div>'
                )
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        else:
            bRemoveDuplicates = True
            sTableHeader = (
                '<table id="result_table"><thead><tr><th style="width: 20px;">'
                '<input class="selectall" type="checkbox"></th>'
                '<th style="width:175px;">Configuration</th>'
                '<th style="width: 20px;"></th><th style="width:175px;">'
                'Catalog Impacted</th><th style="width:175px;">Version</th>' #S-11548: Search - Advanced Search sub-tab changes: Changed Baseline Impacted to Catalog Impacted
                '<th style="width:175px;">Inquiry / Site Template Number</th>'
                '<th style="width:175px;">Customer</th>'
            )

            """ This will be a list of strings.  Each string will be the
             dot-operator-separated string of attributes that would retrieve the
             desired value (i.e.: 'config.configline.part.description')
             This will be so that the search results list can be easily repeated
            """
            aLineFilter = ['config.header.inquiry_site_template',
                           'config.header.customer_unit.name']

            # Start with all ConfigLines.  We use ConfigLine because advanced
            # searches can search on part number, customer number, and other
            # values stored at the ConfigLine level, while still allowing access
            # to values stored at the Header level
            aConfigLines = ConfigLine.objects.filter(config__header__customer_unit_id__in=aAvailableCU).exclude(config__header__baseline__isdeleted=1)  # added filter(config__header__customer_unit_id__in=aAvailableCU) for S-06169 Search and Adv. Search restrict view to CU

            # Filter configline list based on parameters POSTed.  Also add each
            # search parameter field as a field in the results table
            if 'config_design' in oRequest.POST and \
                            oRequest.POST['config_design'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__configuration_designation__iregex="^" +
                    escape(
                        oRequest.POST['config_design'].strip()
                    ).replace(' ','\W').replace('?','.').replace('*', '.*') +
                    "$"
                )

            if 'inquiry_site' in oRequest.POST and \
                    oRequest.POST['inquiry_site'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__inquiry_site_template__iregex="^" + escape(
                        oRequest.POST['inquiry_site'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__react_request__iregex="^" + escape(
                        oRequest.POST['request'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += '<th style="width:175px;">REACT Request</th>'
                aLineFilter.append('config.header.react_request')

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                if oRequest.POST['customer'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__customer_unit=oRequest.POST[
                            'customer']
                    )

 # S - 11564: Search - Basic & Advanced adjustments - Added below block to filter based on CName in advanced search
            if 'cuname' in oRequest.POST and oRequest.POST['cuname'] != '':
                if oRequest.POST['cuname'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__customer_name=oRequest.POST[
                            'cuname']
                    )
            sTableHeader += '<th style="width:175px;">Customer Name</th>'
            aLineFilter.append('config.header.customer_name')

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__person_responsible__iregex="^" + escape(
                        oRequest.POST['person'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += \
                    '<th style="width:175px;">Person Responsible</th>'
                aLineFilter.append('config.header.person_responsible')

            if 'sold_to' in oRequest.POST and oRequest.POST['sold_to'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__sold_to_party__iregex="^" + escape(
                        oRequest.POST['sold_to'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += '<th style="width:175px;">Sold-to Party</th>'
                aLineFilter.append('config.header.sold_to_party')

            if 'program' in oRequest.POST and oRequest.POST['program'] != '':
                if oRequest.POST['program'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__program__name__iexact=oRequest.POST[
                            'program']
                    )
                sTableHeader += '<th style="width:175px;">Program</th>'
                aLineFilter.append('config.header.program')

            if 'technology' in oRequest.POST and \
                    oRequest.POST['technology'] != '':
                if oRequest.POST['technology'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__technology__name__iexact=oRequest.POST[
                            'technology']
                    )
                sTableHeader += '<th style="width:175px;">Technology</th>'
                aLineFilter.append('config.header.technology.name')

            if 'product1' in oRequest.POST and oRequest.POST['product1'] != '':
                if oRequest.POST['product1'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__product_area1__name__iexact=oRequest
                        .POST['product1']
                    )
                sTableHeader += '<th style="width:175px;">Product Area 1</th>'
                aLineFilter.append('config.header.product_area1.name')

            if 'product2' in oRequest.POST and oRequest.POST['product2'] != '':
                if oRequest.POST['product2'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__product_area2__name__iexact=oRequest
                        .POST['product2']
                    )
                sTableHeader += '<th style="width:175px;">Product Area 2</th>'
                aLineFilter.append('config.header.product_area2.name')

            if 'frequency' in oRequest.POST and \
                    oRequest.POST['frequency'] != '':
                if oRequest.POST['frequency'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__radio_frequency__name__iexact=oRequest
                        .POST['frequency']
                    )
                sTableHeader += '<th style="width:175px;">Radio Frequency</th>'
                aLineFilter.append('config.header.radio_frequency.name')

            if 'band' in oRequest.POST and oRequest.POST['band'] != '':
                if oRequest.POST['band'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__radio_band__name__iexact=oRequest.POST[
                            'band']
                    )
                sTableHeader += '<th style="width:175px;">Radio Band</th>'
                aLineFilter.append('config.header.radio_band.name')

            if 'readiness' in oRequest.POST and \
                    oRequest.POST['readiness'] != '':
                if oRequest.POST['readiness_param'] != 'ne':
                    aConfigLines = aConfigLines.filter(
                        **{'config__header__readiness_complete__' +
                           oRequest.POST['readiness_param']:
                               oRequest.POST['readiness']}
                    )
                else:
                    aConfigLines = aConfigLines.exclude(
                        **{'config__header__readiness_complete__exact':
                               oRequest.POST['readiness']})
                sTableHeader += \
                    '<th style="width:175px;">Readiness Complete</th>'
                aLineFilter.append('config.header.readiness_complete')

            if 'base_impact' in oRequest.POST and \
                    oRequest.POST['base_impact'] != '':
                if oRequest.POST['base_impact'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__baseline_impacted__iregex="^" + escape(
                            oRequest.POST['base_impact'].strip()
                        ).replace(' ', '\W').replace('?', '.').replace(
                            '*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Baseline Impacted</th>'
                aLineFilter.append('config.header.base_impact')

            if 'model' in oRequest.POST and oRequest.POST['model'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__model__iregex="^" + escape(
                        oRequest.POST['model'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += '<th style="width:175px;">Model</th>'
                aLineFilter.append('config.header.model')

            if 'model_desc' in oRequest.POST and \
                    oRequest.POST['model_desc'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__model_description__iregex="^" + escape(
                        oRequest.POST['model_desc'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += \
                    '<th style="width:175px;">Model Description</th>'
                aLineFilter.append('config.header.model_description')

            if 'init_rev' in oRequest.POST and oRequest.POST['init_rev'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__initial_revision__iregex="^" + escape(
                        oRequest.POST['init_rev'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTableHeader += '<th style="width:175px;">Initial Revision</th>'
                aLineFilter.append('config.header.initial_revision')

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                if oRequest.POST['status'] != 'n/a':
                    aConfigLines = aConfigLines.filter(
                        config__header__configuration_status__name__iexact=
                        oRequest.POST['status'].replace('_', ' ')
                    )
                sTableHeader += \
                    '<th style="width:175px;">Configuration Status</th>'
                aLineFilter.append('config.header.configuration_status.name')
            else:
                aConfigLines = aConfigLines.filter(
                    config__header__configuration_status__name='Active')

# S-11113: Multiple Selections and Choices on Dropdowns in Search / Advanced Search:- Added below block for multiple selection of ericsson contract
            if 'ericsson_contract' in oRequest.POST and len(oRequest.POST['ericsson_contract']) > 2:
                # if oRequest.POST['ericsson_contract'] != 'n/a':
                selectedcontvals = ast.literal_eval(oRequest.POST['ericsson_contract'])
                aConfigLines = aConfigLines.filter(config__header__ericsson_contract__in=selectedcontvals)

                sTableHeader += '<th style="width:175px;">Value Contract</th>'
                aLineFilter.append('config.header.ericsson_contract')

# S-11113: Multiple Selections and Choices on Dropdowns in Search / Advanced Search:- Added below block for multiple selection of supply flow chain
            if 'supply_chain_flow' in oRequest.POST and len(oRequest.POST['supply_chain_flow']) > 2:
                # if oRequest.POST['supply_chain_flow'] != 'n/a':
                selectedvals = ast.literal_eval(oRequest.POST['supply_chain_flow'])
                aConfigLines = aConfigLines.filter(config__header__supply_chain_flow__name__in=selectedvals)

                sTableHeader += '<th style="width:175px;">Supply Chain Flow</th>'
                aLineFilter.append('config.header.supply_chain_flow')

            sTempHeaderLine = ''
            aTempFilters = ['line_number']

            if 'product_num' in oRequest.POST and \
                    oRequest.POST['product_num'] != '':
                aConfigLines = aConfigLines.filter(
                    part__base__product_number__iregex="^" + escape(
                        oRequest.POST['product_num'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
 # S-13694-Additional Columns on Search/Advanced results display: Added 5 column below SPUD as per requirements
                sTempHeaderLine += ('<th style="width:195px;">Product Number</th>'
                                    '<th style="width:195px;">SPUD</th>'
                                    '<th style="width:195px;">Portfolio Code</th>'
                                    '<th style="width:195px;cellspacing:10px;">Customer Name<p></p></th>'
                                    '<th style="width:195px;">Program</th>'
                                    '<th style="width:195px;">Value Contract</th>'
                                    '<th style="width:195px;">Supply Chain Flow/Segment</th>')

                aTempFilters.append('part.base.product_number')
                aTempFilters.append('spud')
                # S-13694-Additional Columns on Search/Advanced results display: Fetched 5 columndata below SPUD as per requirements
                aTempFilters.append('current_portfolio_code')
                aTempFilters.append('config.header.customer_name')
                aTempFilters.append('config.header.program')
                aTempFilters.append('config.header.ericsson_contract')
                aTempFilters.append('config.header.supply_chain_flow')
                bRemoveDuplicates = False

            if 'context_id' in oRequest.POST and \
                    oRequest.POST['context_id'] != '':
                aConfigLines = aConfigLines.filter(
                    contextId__iregex="^" + escape(
                        oRequest.POST['context_id'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTempHeaderLine += '<th style="width:175px;">Context ID</th>'
                aTempFilters.append('contextId')
                bRemoveDuplicates = False

            if 'description' in oRequest.POST and \
                    oRequest.POST['description'] != '':
                aConfigLines = aConfigLines.filter(
                    part__product_description__iregex="^" + escape(
                        oRequest.POST['description'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTempHeaderLine += \
                    '<th style="width:175px;">Product Description</th>'
                aTempFilters.append('part.product_description')
                bRemoveDuplicates = False

            if 'customer_num' in oRequest.POST and \
                    oRequest.POST['customer_num'] != '':
                aConfigLines = aConfigLines.filter(
                    customer_number__iregex="^" + escape(
                        oRequest.POST['customer_num'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )
                sTempHeaderLine += \
                    '<th style="width:175px;">Customer Number</th>'
                aTempFilters.append('customer_number')
                bRemoveDuplicates = False

        # Added for S-05767:Addition of Second Cust No. in advance search filter
            if 'sec_customer_num' in oRequest.POST and \
                            oRequest.POST['sec_customer_num'] != '':
                aConfigLines = aConfigLines.filter(
                    sec_customer_number__iregex="^" + escape(
                        oRequest.POST['sec_customer_num'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                                                "$"
                )
                sTempHeaderLine += \
                    '<th style="width:175px;">Second Customer Number</th>'
                aTempFilters.append('sec_customer_number')
                bRemoveDuplicates = False

 # S-11113: Multiple Selections and Choices on Dropdowns in Search / Advanced Search:- Added below block for multiple selection of portfolio code
            if 'portfolio_code' in oRequest.POST and len(oRequest.POST['portfolio_code'])>2:
                if oRequest.POST['portfolio_code'] != 'n/a':
                    selectedportvals = ast.literal_eval(oRequest.POST['portfolio_code'])
                    aConfigLines = aConfigLines.filter(current_portfolio_code__in=selectedportvals)

                # sTableHeader += '<th style="width:175px;">Portfolio Code</th>'
                # aLineFilter.append('current_portfolio_code')

                sTempHeaderLine += \
                    '<th style="width:175px;">Portfolio Code</th>'
                aTempFilters.append('current_portfolio_code')
                bRemoveDuplicates = False

            if sTempHeaderLine:
                sTableHeader += '<th style="width:175px;">Line Number</th>' + \
                                sTempHeaderLine
                aLineFilter.extend(aTempFilters)

            if 'base_rev' in oRequest.POST and oRequest.POST['base_rev'] != '':
                aConfigLines = aConfigLines.filter(
                    config__header__baseline_version__iregex="^" + escape(
                        oRequest.POST['base_rev'].strip()
                    ).replace(' ', '\W').replace('?', '.').replace('*', '.*') +
                    "$"
                )

            if 'release' in oRequest.POST and oRequest.POST['release'] != '':
                if oRequest.POST['release_param'] != 'ne':
                    aConfigLines = aConfigLines.filter(
                        **{'config__header__release_date__' +
                           oRequest.POST['release_param']:
                               oRequest.POST['release']})
                else:
                    aConfigLines = aConfigLines.exclude(
                        **{'config__header__release_date__exact':
                            oRequest.POST['release']})
                sTableHeader += '<th style="width:175px;">Release Date</th>'
                aLineFilter.append('config.header.release_date')

            if 'latest_only' in oRequest.POST and \
                    oRequest.POST['latest_only'] != 'false':
                aConfigLines = aConfigLines.filter(
                    config__header__baseline__baseline__current_active_version=
                    F('config__header__baseline_version')
                )

            # If bRemoveDuplicates is True, only Header/Configuration level
            # values were searched, so remove duplicate headers fro the results
            if bRemoveDuplicates:
                aResults = [obj.config for obj in aConfigLines]
                aResults = set(aResults)
                aLineFilter = [sFilter[7:] if sFilter.startswith('config.')
                               else sFilter for sFilter in aLineFilter]
            else:
                aResults = aConfigLines

            # Write search results to HTTP response
            results = HttpResponse()
            if aResults:
                results.write('<h5 style="color:red">Found ' +
                              str(len(aResults)) + ' matching record(s)</h5>')
                results.write(sTableHeader + "</tr></thead><tbody>")
                for oResult in aResults:
                    results.write((
                        '<tr><td><input class="recordselect" type="checkbox" '
                        'value="{4}"></td><td><a href="?link={0}">{1}</a></td>'
                        '<td><a href="?link={0}&readonly=1" target="_blank">'
                        '<span class="glyphicon glyphicon-new-window" '
                        'title="Open in new window"></span></a></td>'
                        '<td>{2}</td><td>{3}</td>'
                    ).format(
                        searchscramble(str(GrabValue(
                            oResult, 'config.header.pk' if
                            isinstance(oResult, ConfigLine) else 'header.pk'))),
                        str(GrabValue(
                            oResult, 'config.header.configuration_designation'
                            if isinstance(oResult, ConfigLine)
                            else 'header.configuration_designation')),
                        str(GrabValue(oResult, 'config.header.baseline.title'
                        if isinstance(oResult, ConfigLine) else
                        'header.baseline.title', '(Not Baselined)')),
                        str(GrabValue(oResult, 'config.header.baseline_version'
                        if isinstance(oResult, ConfigLine) else
                        'header.baseline_version', '-----')),
                        oResult.config.header.pk if
                        isinstance(oResult, ConfigLine) else oResult.header.pk
                        )
                    )

                    for sFilter in aLineFilter:
                        if 'header.inquiry_site_template' in sFilter:
                            results.write('<td>')
                            iInqValue = GrabValue(oResult, sFilter, None)
                            if iInqValue is not None:
                                if iInqValue > 0:
                                    results.write(iInqValue)
                                elif iInqValue == -1:
                                    results.write('(Pending)')
                                elif iInqValue < -1:
                                    results.write(str(iInqValue * -1) +
                                                  ' (Pending Update)')
                            else:
                                results.write('-----')
                            results.write('</td>')
                        else:
                            results.write('<td>' + str(GrabValue(
                                oResult, sFilter, '-----')) + '</td>')
                    # end for

                    results.write('</tr>')
                # end for
                results.write(
                    '</tbody></table><div><button id="download" class="btn '
                    'btn-primary" style="margin-right: 5px" disabled>Download '
                    'Records</button><button id="downloadcustom" class="btn '
                    'btn-primary" disabled>Download Search Results</button>'
                    '</div>'
                )
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        # end if
    else:
        # Return the last 10 Headers in the database
        aHeaders = list(aHeaders)[-10:]
    # end if

# S-05903,S-05905, S-05906, S-05907, S-05908:-  Added Below-  .exclude(is_inactive=1)/filter(is_inactive=0) to filter the dropdowns of Program, Technology, PA1, PA2, RF/RB
    dContext = {
        'header_list': aHeaders.extend(oCu for oCu in aAvailableCU if oCu in aAvailableCU), # added  for S-06169 Search and Adv. Search restrict view to CU
        'request_list': REF_REQUEST.objects.all(),
        'cust_list': aAvailableCU, # added aAvailableCU for S-06169 Search and Adv. Search restrict view to CU
        'status_list': REF_STATUS.objects.all(),
        'prog_list': sorted(list(set(REF_PROGRAM.objects.filter(parent_id__in=aAvailableCU).filter(is_inactive=0).values_list(
            'name', flat=True)))), # added aAvailableCU for S-06169 Search and Adv. Search restrict view to CU
        'tech_list': REF_TECHNOLOGY.objects.all().exclude(is_inactive=1),
        'baseline_list': Baseline.objects.all().order_by('title').exclude(isdeleted=1).filter(customer_id__in=aAvailableCU), # added aAvailableCU for S-06169 Search and Adv. Search restrict view to CU
        # added for S-05906,S-05907 Edit drop down option for BoM Entry Header -  Product Area 1, Product Area2 (exclude deleted prodarea1,prodarea2)
        'prod1_list': sorted(list(set(
            REF_PRODUCT_AREA_1.objects.all().exclude(is_inactive=1).values_list('name', flat=True)))),
        'prod2_list': sorted(list(set(
            REF_PRODUCT_AREA_2.objects.all().exclude(is_inactive=1).values_list('name', flat=True))),
            key=lambda x: str(x).upper()),
        'band_list': REF_RADIO_BAND.objects.all().exclude(is_inactive=1).order_by('name'),
        'freq_list': sorted(list(set(
            REF_RADIO_FREQUENCY.objects.all().exclude(is_inactive=1).values_list('name', flat=True)))),
        'supply_chain_flow_list': Supply_Chain_Flow.objects.all().order_by('name')
    }
    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
# end def
