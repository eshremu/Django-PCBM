__author__ = 'epastag'

from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse

from BoMConfig.models import Header, ConfigLine, REF_REQUEST, REF_CUSTOMER, REF_STATUS
from BoMConfig.templatetags.customtemplatetags import searchscramble
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import GrabValue


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

        if not advanced:

            if 'config_design' in oRequest.POST and oRequest.POST['config_design'] != '':
                aHeaders = aHeaders.filter(configuration_designation__iregex="^" + oRequest.POST['config_design'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
            # end if

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aHeaders = aHeaders.filter(person_responsible__iregex="^" + oRequest.POST['person'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
            # end if

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aHeaders = aHeaders.filter(bom_request_type__name=oRequest.POST['request'])
            # end if

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                aHeaders = aHeaders.filter(customer_unit__name=oRequest.POST['customer'])
            # end if

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                aHeaders = aHeaders.filter(configuration_status__name=oRequest.POST['status'].replace('_', ' ').title())
            # end if

            results = HttpResponse()
            if aHeaders:
                results.write('<h5 style="color:red">Found ' + str(len(aHeaders)) + ' matching record(s)</h5>')
                results.write('<table><thead><tr><th style="width: 20px;"><input class="selectall" type="checkbox"/></th><th style="width:175px;">Configuration</th><th style="width:175px;">Program</th>' +
                              '<th style="width:175px;">Version</th><th style="width:175px;">Person Responsible</th>' +
                              '<th style="width:175px;">BoM Request Type</th><th style="width:175px;">Customer Unit</th>' +
                              '<th style="width:175px;">Status</th></tr></thead><tbody>')
                for header in aHeaders:
                    results.write('<tr><td><input class="recordselect" type="checkbox" value="{8}"/></td><td><a href="?link={0}">{1}</a></td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td><td>{7}</td></tr>'\
                        .format(searchscramble(header.pk), header.configuration_designation, GrabValue(header, 'program.name') or '', header.baseline_version,
                                header.person_responsible, header.bom_request_type.name, header.customer_unit.name, header.configuration_status.name, header.pk))
                # end for
                results.write('</tbody></table><button id="download" disabled>Download</button>')
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        else:
            bRemoveDuplicates = True
            sTableHeader = '<table><thead><tr><th style="width: 20px;"><input class="selectall" type="checkbox"></th><th style="width:175px;">Configuration</th><th style="width:175px;">Version</th>'
            """ This will be a list of strings.  Each string will be the dot-operator-separated string of attributes
             that would retrieve the desired value (i.e.: 'config.configline.part.description')
             This will be so that the search results list can be easily repeated"""
            aLineFilter = []

            aConfigLines = ConfigLine.objects.all()

            if 'config_design' in oRequest.POST and oRequest.POST['config_design'] != '':
                aConfigLines = aConfigLines.filter(config__header__configuration_designation__iregex="^" + oRequest.POST['config_design'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                aConfigLines = aConfigLines.filter(config__header__react_request__iregex="^" + oRequest.POST['request'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">REACT Request</th>'
                aLineFilter.append('config.header.react_request')

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                aConfigLines = aConfigLines.filter(config__header__customer_unit__name=oRequest.POST['customer'])
                sTableHeader += '<th style="width:175px;">Customer</th>'
                aLineFilter.append('config.header.customer_unit.name')

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                aConfigLines = aConfigLines.filter(config__header__person_responsible__iregex="^" + oRequest.POST['person'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Person Responsible</th>'
                aLineFilter.append('config.header.person_responsible')

            if 'sold_to' in oRequest.POST and oRequest.POST['sold_to'] != '':
                aConfigLines = aConfigLines.filter(config__header__sold_to_party__iregex="^" + oRequest.POST['sold_to'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Sold-to Party</th>'
                aLineFilter.append('config.header.sold_to_party')

            if 'program' in oRequest.POST and oRequest.POST['program'] != '':
                aConfigLines = aConfigLines.filter(config__header__program__iregex="^" + oRequest.POST['program'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Program</th>'
                aLineFilter.append('config.header.program')

            if 'technology' in oRequest.POST and oRequest.POST['technology'] != '':
                aConfigLines = aConfigLines.filter(config__header__technology__name__iregex="^" + oRequest.POST['technology'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Technology</th>'
                aLineFilter.append('config.header.technology.name')

            if 'base_impact' in oRequest.POST and oRequest.POST['base_impact'] != '':
                aConfigLines = aConfigLines.filter(config__header__baseline_impacted__iregex="^" + oRequest.POST['base_impact'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Baseline Impacted</th>'
                aLineFilter.append('config.header.baseline_impacted')

            if 'model' in oRequest.POST and oRequest.POST['model'] != '':
                aConfigLines = aConfigLines.filter(config__header__model__iregex="^" + oRequest.POST['model'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model</th>'
                aLineFilter.append('config.header.model')

            if 'model_desc' in oRequest.POST and oRequest.POST['model_desc'] != '':
                aConfigLines = aConfigLines.filter(config__header__model_description__iregex="^" + oRequest.POST['model_desc'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model Description</th>'
                aLineFilter.append('config.header.model_description')

            if 'init_rev' in oRequest.POST and oRequest.POST['init_rev'] != '':
                aConfigLines = aConfigLines.filter(config__header__initial_revision__iregex="^" + oRequest.POST['init_rev'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Initial Revision</th>'
                aLineFilter.append('config.header.initial_revision')

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                aConfigLines = aConfigLines.filter(config__header__configuration_status__name__iexact=oRequest.POST['status'].replace('_', ' '))
                sTableHeader += '<th style="width:175px;">Configuration Status</th>'
                aLineFilter.append('config.header.configuration_status.name')

            if 'inquiry_site' in oRequest.POST and oRequest.POST['inquiry_site'] != '':
                aConfigLines = aConfigLines.filter(config__header__inquiry_site_template__iregex="^" + oRequest.POST['inquiry_site'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Inquiry / Site Template Number</th>'
                aLineFilter.append('config.header.inquiry_site_number')

            sTempHeaderLine = ''
            aTempFilters = ['line_number']

            if 'product_num' in oRequest.POST and oRequest.POST['product_num'] != '':
                aConfigLines = aConfigLines.filter(part__base__product_number__iregex="^" + oRequest.POST['product_num'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Number</th><th style="width:175px;">SPUD</th>'
                aTempFilters.append('part.base.product_number')
                aTempFilters.append('spud')
                bRemoveDuplicates = False

            if 'description' in oRequest.POST and oRequest.POST['description'] != '':
                aConfigLines = aConfigLines.filter(part__product_description__iregex="^" + oRequest.POST['description'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Description</th>'
                aTempFilters.append('part.product_description')
                bRemoveDuplicates = False

            if 'customer_num' in oRequest.POST and oRequest.POST['customer_num'] != '':
                aConfigLines = aConfigLines.filter(customer_number__iregex="^" + oRequest.POST['customer_num'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Customer Number</th>'
                aTempFilters.append('customer_number')
                bRemoveDuplicates = False

            if 'mu_flag' in oRequest.POST and oRequest.POST['mu_flag'] != '':
                aConfigLines = aConfigLines.filter(mu_flag__iregex="^" + oRequest.POST['mu_flag'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">MU-Flag</th>'
                aTempFilters.append('mu_flag')
                bRemoveDuplicates = False

            if 'xplant' in oRequest.POST and oRequest.POST['xplant'] != '':
                aConfigLines = aConfigLines.filter(x_plant__iregex="^" + oRequest.POST['xplant'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">X-Plant Material Status</th>'
                aTempFilters.append('x_plant')
                bRemoveDuplicates = False

            if sTempHeaderLine:
                sTableHeader += '<th style="width:175px;">Line Number</th>' + sTempHeaderLine
                aLineFilter.extend(aTempFilters)

            if 'base_rev' in oRequest.POST and oRequest.POST['base_rev'] != '':
                aConfigLines = aConfigLines.filter(config__header__baseline_version__iregex="^" + oRequest.POST['base_rev'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")

            if 'release' in oRequest.POST and oRequest.POST['release'] != '':
                aConfigLines = aConfigLines.filter(**{'config__header__release_date__' + oRequest.POST['release_param']: oRequest.POST['release']})
                sTableHeader += '<th style="width:175px;">Release Date</th>'
                aLineFilter.append('config.header.release_date')

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
                    results.write('<tr><td><input class="recordselect" type="checkbox" value="{3}"></td><td><a href="?link={0}">{1}</a></td><td>{2}</td>'.format(
                        searchscramble(str(GrabValue(oResult,'config.header.pk' if isinstance(oResult, ConfigLine) else 'header.pk'))),
                        str(GrabValue(oResult,'config.header.configuration_designation' if isinstance(oResult, ConfigLine)
                            else 'header.configuration_designation')),
                        str(GrabValue(oResult,'config.header.baseline_version' if isinstance(oResult, ConfigLine) else 'header.baseline_version')),
                        oResult.config.header.pk if isinstance(oResult, ConfigLine) else oResult.header.pk
                        )
                    )

                    for sFilter in aLineFilter:
                        results.write('<td>' + str(GrabValue(oResult, sFilter)) + '</td>')
                    # end for

                    results.write('</tr>')
                # end for
                results.write('</tbody></table><button id="download" disabled>Download</button>')
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
        'status_list': REF_STATUS.objects.all()
    }
    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
# end def
