__author__ = 'epastag'

from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.db.models import F, Q
from django.contrib.auth.decorators import login_required

from BoMConfig.models import Header, ConfigLine, REF_REQUEST, REF_CUSTOMER, REF_STATUS, REF_PROGRAM, REF_PRODUCT_AREA_1,\
    REF_PRODUCT_AREA_2, REF_TECHNOLOGY, REF_RADIO_BAND, REF_RADIO_FREQUENCY, Baseline

from BoMConfig.templatetags.bomconfig_customtemplatetags import searchscramble
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue

import re
import functools


@login_required
def Search(oRequest, advanced=False):
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

    readonly = oRequest.GET.get('readonly', False)
    link = oRequest.GET.get('link', None)
    config = oRequest.GET.get('config', None)
    if link or config:
        if link:
            if not readonly:
                oRequest.session['existing'] = link[5:-10]
                return redirect(reverse('bomconfig:configheader'))
            else:
                return redirect(reverse('bomconfig:configheader') + ('?id=' + str(link[5:-10]) + '&readonly=1'))
        else:
            if not readonly:
                oRequest.session['existing'] = config[5:-10]
                return redirect(reverse('bomconfig:config'))
            else:
                return redirect(reverse('bomconfig:config') + ('?id=' + str(config[5:-10]) + '&readonly=1'))
        # end if
    # end if

    aHeaders = Header.objects.all()

    if oRequest.method == 'POST' and oRequest.POST:
        oEscape = re.compile(r'([\^$+.\{\}\(\)\[\]\|\\])')
        escape = functools.partial(oEscape.sub, r'\\\1')
        if not advanced:

            if 'config_design' in oRequest.POST and oRequest.POST['config_design'] != '':
                aHeaders = aHeaders.filter(configuration_designation__iregex="^" + escape(oRequest.POST['config_design'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
            # end if

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aHeaders = aHeaders.filter(person_responsible__iregex="^" + escape(oRequest.POST['person'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
            # end if

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aHeaders = aHeaders.filter(bom_request_type__name=oRequest.POST['request'])
            # end if

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                aHeaders = aHeaders.filter(customer_unit__name=oRequest.POST['customer'])
            # end if

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                aHeaders = aHeaders.filter(configuration_status__name=oRequest.POST['status'].replace('_', ' ').title())
            else:
                aHeaders = aHeaders.filter(configuration_status__name='Active')
            # end if

            results = HttpResponse()
            if aHeaders:
                results.write('<h5 style="color:red">Found ' + str(len(aHeaders)) + ' matching record(s)</h5>')
                results.write('<table id="result_table"><thead><tr><th style="width: 20px;"><input class="selectall" '
                              'type="checkbox"/></th><th style="width:175px;">Configuration</th><th style="25px;"></th><th style="width:175px;">Program</th>'
                              '<th style="width:175px;">Baseline</th><th style="width:75px;">Version</th><th style="width:175px;">Person Responsible</th>'
                              '<th style="width:175px;">BoM Request Type</th><th style="width:175px;">Customer Unit</th>'
                              '<th style="width:175px;">Status</th><th>Readiness Complete</th></tr></thead><tbody>')
                for header in aHeaders:
                    results.write(('<tr><td><input class="recordselect" type="checkbox" value="{8}"/></td><td><a href="?'
                                    'link={0}">{1}</a></td><td><a href="?link={0}&readonly=1" target="_blank"><span class="glyphicon '
                                    'glyphicon-new-window" title="Open in new window"></span></a></td><td>{2}</td><td>{10}</td><td>{3}</td><td>{4}'
                                    '</td><td>{5}</td><td>{6}</td><td>{7}</td><td>{9}</td></tr>')
                                  .format(searchscramble(header.pk), header.configuration_designation,
                                          GrabValue(header, 'program.name') or '(None)', header.baseline_version,
                                          header.person_responsible, header.bom_request_type.name, header.customer_unit.name,
                                          header.configuration_status.name, header.pk, header.readiness_complete or 0,
                                          header.baseline.title if header.baseline else '(Not Baselined)'))
                # end for
                results.write('</tbody></table><div><button id="download" class="btn btn-primary" style="margin-right: 5px;" disabled>Download Records</button>'
                              '<button id="downloadcustom" class="btn btn-primary" disabled>Download Results</button></div>')
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        else:
            bRemoveDuplicates = True
            sTableHeader = ('<table id="result_table"><thead><tr><th style="width: 20px;"><input class="selectall"'
                            ' type="checkbox"></th><th style="width:175px;">Configuration</th><th style="width: 20px;">'
                            '</th><th style="width:175px;">Baseline Impacted</th><th style="width:175px;">Version</th>'
                            '<th style="width:175px;">Inquiry / Site Template Number</th><th style="width:175px;">Customer</th>')

            """ This will be a list of strings.  Each string will be the dot-operator-separated string of attributes
             that would retrieve the desired value (i.e.: 'config.configline.part.description')
             This will be so that the search results list can be easily repeated"""
            aLineFilter = ['config.header.inquiry_site_template', 'config.header.customer_unit.name']

            aConfigLines = ConfigLine.objects.all()

            if 'config_design' in oRequest.POST and oRequest.POST['config_design'] != '':
                aConfigLines = aConfigLines.filter(config__header__configuration_designation__iregex="^" + escape(oRequest.POST['config_design'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")

            if 'inquiry_site' in oRequest.POST and oRequest.POST['inquiry_site'] != '':
                aConfigLines = aConfigLines.filter(config__header__inquiry_site_template__iregex="^" + escape(oRequest.POST['inquiry_site'].strip())
                    .replace(' ', '\W').replace('?', '.').replace('*', '.*') + "$")
                # sTableHeader += '<th style="width:175px;">Inquiry / Site Template Number</th>'
                # aLineFilter.append('config.header.inquiry_site_number')

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aConfigLines = aConfigLines.filter(config__header__react_request__iregex="^" + escape(oRequest.POST['request'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">REACT Request</th>'
                aLineFilter.append('config.header.react_request')

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                if oRequest.POST['customer'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__customer_unit__name=oRequest.POST['customer'])
                # sTableHeader += '<th style="width:175px;">Customer</th>'
                # aLineFilter.append('config.header.customer_unit.name')

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aConfigLines = aConfigLines.filter(config__header__person_responsible__iregex="^" + escape(oRequest.POST['person'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Person Responsible</th>'
                aLineFilter.append('config.header.person_responsible')

            if 'sold_to' in oRequest.POST and oRequest.POST['sold_to'] != '':
                aConfigLines = aConfigLines.filter(config__header__sold_to_party__iregex="^" + escape(oRequest.POST['sold_to'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Sold-to Party</th>'
                aLineFilter.append('config.header.sold_to_party')

            if 'program' in oRequest.POST and oRequest.POST['program'] != '':
                if oRequest.POST['program'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__program__name__iexact=oRequest.POST['program'])
                sTableHeader += '<th style="width:175px;">Program</th>'
                aLineFilter.append('config.header.program')

            if 'technology' in oRequest.POST and oRequest.POST['technology'] != '':
                if oRequest.POST['technology'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__technology__name__iexact=oRequest.POST['technology'])
                sTableHeader += '<th style="width:175px;">Technology</th>'
                aLineFilter.append('config.header.technology.name')

            if 'product1' in oRequest.POST and oRequest.POST['product1'] != '':
                if oRequest.POST['product1'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__product_area1__name__iexact=oRequest.POST['product1'])
                sTableHeader += '<th style="width:175px;">Product Area 1</th>'
                aLineFilter.append('config.header.product_area1.name')

            if 'product2' in oRequest.POST and oRequest.POST['product2'] != '':
                if oRequest.POST['product2'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__procuct_area2__name__iexact=oRequest.POST['product2'])
                sTableHeader += '<th style="width:175px;">Product Area 2</th>'
                aLineFilter.append('config.header.product_area2.name')

            if 'frequency' in oRequest.POST and oRequest.POST['frequency'] != '':
                if oRequest.POST['frequency'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__radio_frequency__name__iexact=oRequest.POST['frequency'])
                sTableHeader += '<th style="width:175px;">Radio Frequency</th>'
                aLineFilter.append('config.header.radio_frequency.name')

            if 'band' in oRequest.POST and oRequest.POST['band'] != '':
                if oRequest.POST['band'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__radio_band__name__iexact=oRequest.POST['band'])
                sTableHeader += '<th style="width:175px;">Radio Band</th>'
                aLineFilter.append('config.header.radio_band.name')

            if 'readiness' in oRequest.POST and oRequest.POST['readiness'] != '':
                if oRequest.POST['readiness_param'] != 'ne':
                    aConfigLines = aConfigLines.filter(**{'config__header__readiness_complete__' + oRequest.POST['readiness_param']: oRequest.POST['readiness']})
                else:
                    aConfigLines = aConfigLines.exclude(
                        **{'config__header__readiness_complete__exact': oRequest.POST['readiness']})
                sTableHeader += '<th style="width:175px;">Readiness Complete</th>'
                aLineFilter.append('config.header.readiness_complete')

            if 'base_impact' in oRequest.POST and oRequest.POST['base_impact'] != '':
                if oRequest.POST['base_impact'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__baseline_impacted__iregex="^" + escape(oRequest.POST['base_impact'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                # sTableHeader += '<th style="width:175px;">Baseline Impacted</th>'
                # aLineFilter.append('config.header.baseline_impacted')

            if 'model' in oRequest.POST and oRequest.POST['model'] != '':
                aConfigLines = aConfigLines.filter(config__header__model__iregex="^" + escape(oRequest.POST['model'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model</th>'
                aLineFilter.append('config.header.model')

            if 'model_desc' in oRequest.POST and oRequest.POST['model_desc'] != '':
                aConfigLines = aConfigLines.filter(config__header__model_description__iregex="^" + escape(oRequest.POST['model_desc'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model Description</th>'
                aLineFilter.append('config.header.model_description')

            if 'init_rev' in oRequest.POST and oRequest.POST['init_rev'] != '':
                aConfigLines = aConfigLines.filter(config__header__initial_revision__iregex="^" + escape(oRequest.POST['init_rev'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Initial Revision</th>'
                aLineFilter.append('config.header.initial_revision')

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                if oRequest.POST['status'] != 'n/a':
                    aConfigLines = aConfigLines.filter(config__header__configuration_status__name__iexact=oRequest.POST['status'].replace('_', ' '))
                sTableHeader += '<th style="width:175px;">Configuration Status</th>'
                aLineFilter.append('config.header.configuration_status.name')
            else:
                aConfigLines = aConfigLines.filter(config__header__configuration_status__name='Active')

            sTempHeaderLine = ''
            aTempFilters = ['line_number']

            if 'product_num' in oRequest.POST and oRequest.POST['product_num'] != '':
                aConfigLines = aConfigLines.filter(part__base__product_number__iregex="^" + escape(oRequest.POST['product_num'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Number</th><th style="width:175px;">SPUD</th>'
                aTempFilters.append('part.base.product_number')
                aTempFilters.append('spud')
                bRemoveDuplicates = False

            if 'context_id' in oRequest.POST and oRequest.POST['context_id'] != '':
                aConfigLines = aConfigLines.filter(
                    contextId__iregex="^" + escape(oRequest.POST['context_id'].strip())
                    .replace(' ', '\W').replace('?', '.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Context ID</th>'
                aTempFilters.append('contextId')
                bRemoveDuplicates = False

            if 'description' in oRequest.POST and oRequest.POST['description'] != '':
                aConfigLines = aConfigLines.filter(part__product_description__iregex="^" + escape(oRequest.POST['description'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Description</th>'
                aTempFilters.append('part.product_description')
                bRemoveDuplicates = False

            if 'customer_num' in oRequest.POST and oRequest.POST['customer_num'] != '':
                aConfigLines = aConfigLines.filter(customer_number__iregex="^" + escape(oRequest.POST['customer_num'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Customer Number</th>'
                aTempFilters.append('customer_number')
                bRemoveDuplicates = False

            if sTempHeaderLine:
                sTableHeader += '<th style="width:175px;">Line Number</th>' + sTempHeaderLine
                aLineFilter.extend(aTempFilters)

            if 'base_rev' in oRequest.POST and oRequest.POST['base_rev'] != '':
                aConfigLines = aConfigLines.filter(config__header__baseline_version__iregex="^" + escape(oRequest.POST['base_rev'].strip())
                                           .replace(' ','\W').replace('?','.').replace('*', '.*') + "$")

            if 'release' in oRequest.POST and oRequest.POST['release'] != '':
                if oRequest.POST['release_param'] != 'ne':
                    aConfigLines = aConfigLines.filter(**{'config__header__release_date__' + oRequest.POST['release_param']: oRequest.POST['release']})
                else:
                    aConfigLines = aConfigLines.exclude(**{'config__header__release_date__exact': oRequest.POST['release']})
                sTableHeader += '<th style="width:175px;">Release Date</th>'
                aLineFilter.append('config.header.release_date')

            if 'latest_only' in oRequest.POST and oRequest.POST['latest_only'] != 'false':
                aConfigLines = aConfigLines.filter(config__header__baseline__baseline__current_active_version=F('config__header__baseline_version'))

            if bRemoveDuplicates:
                aResults = [obj.config for obj in aConfigLines]
                aResults = set(aResults)
                aLineFilter = [sFilter[7:] if sFilter.startswith('config.') else sFilter for sFilter in aLineFilter]
            else:
                aResults = aConfigLines

            results = HttpResponse()
            if aResults:
                results.write('<h5 style="color:red">Found ' + str(len(aResults)) + ' matching record(s)</h5>')
                results.write(sTableHeader + "</tr></thead><tbody>")
                for oResult in aResults:
                    results.write(('<tr><td><input class="recordselect" type="checkbox" value="{4}"></td>'
                                   '<td><a href="?link={0}">{1}</a></td><td><a href="?link={0}&readonly=1" target="_blank">'
                                   '<span class="glyphicon glyphicon-new-window" title="Open in new window"></span></a></td>'
                                   '<td>{2}</td><td>{3}</td>').format(
                        searchscramble(str(GrabValue(oResult,'config.header.pk' if isinstance(oResult, ConfigLine) else 'header.pk'))),
                        str(GrabValue(oResult,'config.header.configuration_designation' if isinstance(oResult, ConfigLine)
                            else 'header.configuration_designation')),
                        str(GrabValue(oResult, 'config.header.baseline.title' if isinstance(oResult, ConfigLine) else 'header.baseline.title', '(Not Baselined)')),
                        str(GrabValue(oResult,'config.header.baseline_version' if isinstance(oResult, ConfigLine) else 'header.baseline_version', '-----')),
                        oResult.config.header.pk if isinstance(oResult, ConfigLine) else oResult.header.pk
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
                                    results.write(str(iInqValue * -1) + ' (Pending Update)')
                            else:
                                results.write('-----')
                            results.write('</td>')
                        else:
                            results.write('<td>' + str(GrabValue(oResult, sFilter, '-----')) + '</td>')
                    # end for

                    results.write('</tr>')
                # end for
                results.write('</tbody></table><div><button id="download" class="btn btn-primary" style="margin-right: 5px" disabled>Download Records</button>'
                              '<button id="downloadcustom" class="btn btn-primary" disabled>Download Search Results</button></div>')
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        # end if
    else:
        aHeaders = list(aHeaders)[-10:]
    # end if

    dContext = {
        'header_list': aHeaders,
        'request_list': REF_REQUEST.objects.all(),
        'cust_list': REF_CUSTOMER.objects.all(),
        'status_list': REF_STATUS.objects.all(),
        'prog_list': list(set(REF_PROGRAM.objects.all().values_list('name', flat=True))),
        'tech_list': REF_TECHNOLOGY.objects.all(),
        'baseline_list': Baseline.objects.all(),
        'prod1_list': list(set(REF_PRODUCT_AREA_1.objects.all().values_list('name', flat=True))),
        'prod2_list': list(set(REF_PRODUCT_AREA_2.objects.all().values_list('name', flat=True))),
        'band_list': REF_RADIO_BAND.objects.all(),
        'freq_list': list(set(REF_RADIO_FREQUENCY.objects.all().values_list('name', flat=True)))
    }
    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
# end def
