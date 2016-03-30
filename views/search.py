__author__ = 'epastag'

from django.shortcuts import redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse

from BoMConfig.models import Header, ConfigLine
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
            oRequest.session['existing'] = link[5:-10]
            return redirect(reverse('bomconfig:configheader') + ('?readonly=1' if readonly else ''))
        else:
            oRequest.session['existing'] = config[5:-10]
            return redirect(reverse('bomconfig:config') + ('?readonly=1' if readonly else ''))
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
                results.write('<table><thead><tr><th style="width:175px;">Configuration</th>' +
                              '<th style="width:175px;">Version</th><th style="width:175px;">Person Responsible</th>' +
                              '<th style="width:175px;">BoM Request Type</th><th style="width:175px;">Customer Unit</th>' +
                              '<th style="width:175px;">Status</th></tr></thead><tbody>')
                for header in aHeaders:
                    results.write('<tr><td><a href="?link={0}">{1}</a></td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td><td>{6}</td></tr>'\
                        .format(searchscramble(header.pk), header.configuration_designation, header.baseline_version,
                                header.person_responsible, header.bom_request_type.name, header.customer_unit.name, header.configuration_status.name))
                # end for
                results.write('</tbody></table>')
            else:
                results.write('NO CONFIGURATIONS MATCHING SEARCH')
            # end if

            return results
        else:
            bRemoveDuplicates = True
            sTableHeader = '<table><thead><tr><th style="width:175px;">Configuration</th><th style="width:175px;">Version</th>'
            """ This will be a list of strings.  Each string will be the dot-operator-separated string of attributes
             that would retrieve the desired value (i.e.: 'config.configline.part.description')
             This will be so that the search results list can be easily repeated"""
            aLineFilter = []

            aConfigLines = ConfigLine.objects.all()

            if 'config_design' in oRequest.POST and oRequest.POST['config_design'] != '':
                # aHeaders = aHeaders.filter(configuration_designation__iregex="^" + oRequest.POST['config_design']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__configuration_designation__iregex="^" + oRequest.POST['config_design'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")

            if 'request' in oRequest.POST and oRequest.POST['request'] != '':
                # aHeaders = aHeaders.filter(react_request__iregex="^" + oRequest.POST['request']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__react_request__iregex="^" + oRequest.POST['request'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">REACT Request</th>'
                aLineFilter.append('config.header.react_request')

            if 'customer' in oRequest.POST and oRequest.POST['customer'] != '':
                # aHeaders = aHeaders.filter(customer_unit=oRequest.POST['customer'])
                aConfigLines = aConfigLines.filter(config__header__customer_unit__name=oRequest.POST['customer'])
                sTableHeader += '<th style="width:175px;">Customer</th>'
                aLineFilter.append('config.header.customer_unit.name')

            if 'person' in oRequest.POST and oRequest.POST['person'] != '':
                # aHeaders = aHeaders.filter(person_responsible__iregex="^" + oRequest.POST['person']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__person_responsible__iregex="^" + oRequest.POST['person'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Person Responsible</th>'
                aLineFilter.append('config.header.person_responsible')

            if 'sold_to' in oRequest.POST and oRequest.POST['sold_to'] != '':
                # aHeaders = aHeaders.filter(sold_to_party__iregex="^" + oRequest.POST['sold_to']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__sold_to_party__iregex="^" + oRequest.POST['sold_to'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Sold-to Party</th>'
                aLineFilter.append('config.header.sold_to_party')

            if 'program' in oRequest.POST and oRequest.POST['program'] != '':
                # aHeaders = aHeaders.filter(program__iregex="^" + oRequest.POST['program']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__program__iregex="^" + oRequest.POST['program'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Program</th>'
                aLineFilter.append('config.header.program')

            if 'technology' in oRequest.POST and oRequest.POST['technology'] != '':
                # aHeaders = aHeaders.filter(technology__iregex="^" + oRequest.POST['technology']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__technology__name__iregex="^" + oRequest.POST['technology'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Technology</th>'
                aLineFilter.append('config.header.technology.name')

            if 'base_impact' in oRequest.POST and oRequest.POST['base_impact'] != '':
                # aHeaders = aHeaders.filter(baseline_impacted__iregex="^" + oRequest.POST['base_impact']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__baseline_impacted__iregex="^" + oRequest.POST['base_impact'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Baseline Impacted</th>'
                aLineFilter.append('config.header.baseline_impacted')

            if 'model' in oRequest.POST and oRequest.POST['model'] != '':
                # aHeaders = aHeaders.filter(model__iregex="^" + oRequest.POST['model']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__model__iregex="^" + oRequest.POST['model'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model</th>'
                aLineFilter.append('config.header.model')

            if 'model_desc' in oRequest.POST and oRequest.POST['model_desc'] != '':
                # aHeaders = aHeaders.filter(model_description__iregex="^" + oRequest.POST['model_desc']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__model_description__iregex="^" + oRequest.POST['model_desc'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Model Description</th>'
                aLineFilter.append('config.header.model_description')

            if 'init_rev' in oRequest.POST and oRequest.POST['init_rev'] != '':
                # aHeaders = aHeaders.filter(initial_revision__iregex="^" + oRequest.POST['init_rev']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__initial_revision__iregex="^" + oRequest.POST['init_rev'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Initial Revision</th>'
                aLineFilter.append('config.header.initial_revision')

            if 'status' in oRequest.POST and oRequest.POST['status'] != '':
                # aHeaders = aHeaders.filter(configuration_status=oRequest.POST['status'])
                aConfigLines = aConfigLines.filter(config__header__configuration_status__name__iexact=oRequest.POST['status'].replace('_', ' '))
                sTableHeader += '<th style="width:175px;">Configuration Status</th>'
                aLineFilter.append('config.header.configuration_status.name')

            if 'inquiry_site' in oRequest.POST and oRequest.POST['inquiry_site'] != '':
                # aHeaders = aHeaders.filter(inquiry_site_template__iregex="^" + oRequest.POST['inquiry_site']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__inquiry_site_template__iregex="^" + oRequest.POST['inquiry_site'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTableHeader += '<th style="width:175px;">Inquiry / Site Template Number</th>'
                aLineFilter.append('config.header.inquiry_site_number')

            sTempHeaderLine = ''
            aTempFilters = ['line_number']

            if 'product_num' in oRequest.POST and oRequest.POST['product_num'] != '':
                # aConfigs = Configuration.objects.filter(configline__part__base__product_number__iregex="^" + oRequest.POST['product_num']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$").distinct()
                # aHeaders = aHeaders.filter(configuration__in=aConfigs)
                aConfigLines = aConfigLines.filter(part__base__product_number__iregex="^" + oRequest.POST['product_num'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Number</th><th style="width:175px;">SPUD</th>'
                aTempFilters.append('part.base.product_number')
                aTempFilters.append('spud')
                bRemoveDuplicates = False

            if 'description' in oRequest.POST and oRequest.POST['description'] != '':
                # aConfigs = Configuration.objects.filter(configline__part__product_description__iregex="^" + oRequest.POST['description']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$").distinct()
                # aHeaders = aHeaders.filter(configuration__in=aConfigs)
                aConfigLines = aConfigLines.filter(part__product_description__iregex="^" + oRequest.POST['description'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Product Description</th>'
                aTempFilters.append('part.product_description')
                bRemoveDuplicates = False

            if 'customer_num' in oRequest.POST and oRequest.POST['customer_num'] != '':
                # aConfigs = Configuration.objects.filter(configline__customer_number__iregex="^" + oRequest.POST['customer_num']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$").distinct()
                # aHeaders = aHeaders.filter(configuration__in=aConfigs)
                aConfigLines = aConfigLines.filter(customer_number__iregex="^" + oRequest.POST['customer_num'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">Customer Number</th>'
                aTempFilters.append('customer_number')
                bRemoveDuplicates = False

            if 'mu_flag' in oRequest.POST and oRequest.POST['mu_flag'] != '':
                # aConfigs = Configuration.objects.filter(configline__part__base__mu_flag__iregex="^" + oRequest.POST['mu_flag']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$").distinct()
                # aHeaders = aHeaders.filter(configuration__in=aConfigs)
                aConfigLines = aConfigLines.filter(mu_flag__iregex="^" + oRequest.POST['mu_flag'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">MU-Flag</th>'
                aTempFilters.append('mu_flag')
                bRemoveDuplicates = False

            if 'xplant' in oRequest.POST and oRequest.POST['xplant'] != '':
                # aConfigs = Configuration.objects.filter(configline__part__base__x_plant__iregex="^" + oRequest.POST['xplant']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$").distinct()
                # aHeaders = aHeaders.filter(configuration__in=aConfigs)
                aConfigLines = aConfigLines.filter(x_plant__iregex="^" + oRequest.POST['xplant'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                sTempHeaderLine += '<th style="width:175px;">X-Plant Material Status</th>'
                aTempFilters.append('x_plant')
                bRemoveDuplicates = False

            if sTempHeaderLine:
                sTableHeader += '<th style="width:175px;">Line Number</th>' + sTempHeaderLine
                aLineFilter.extend(aTempFilters)

            if 'base_rev' in oRequest.POST and oRequest.POST['base_rev'] != '':
                # aHeaders = aHeaders.filter(baseline_version__iregex="^" + oRequest.POST['base_rev']
                #                            .replace('.', '\.').replace('?','.').replace('*', '.*') + "$")
                aConfigLines = aConfigLines.filter(config__header__baseline_version__iregex="^" + oRequest.POST['base_rev'].strip()
                                           .replace(' ','\W').replace('.', '\.').replace('?','.').replace('*', '.*') + "$")

            if 'release' in oRequest.POST and oRequest.POST['release'] != '':
                # aHeaders = aHeaders.filter(release_date__lte=oRequest.POST['release'])
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
                    results.write('<tr><td><a href="?link={0}">{1}</a></td><td>{2}</td>'.format(
                        searchscramble(str(GrabValue(oResult,'config.header.pk' if isinstance(oResult, ConfigLine) else 'header.pk'))),
                        str(GrabValue(oResult,'config.header.configuration_designation' if isinstance(oResult, ConfigLine)
                            else 'header.configuration_designation')),
                        str(GrabValue(oResult,'config.header.baseline_version' if isinstance(oResult, ConfigLine) else 'header.baseline_version'))
                        )
                    )

                    for sFilter in aLineFilter:
                        results.write('<td>' + str(GrabValue(oResult, sFilter)) + '</td>')
                    # end for

                    results.write('</tr>')
                # end for
                results.write('</tbody></table>')
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
    }
    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
# end def
