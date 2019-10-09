"""
Views related to Baseline viewing and management.
"""

from django.http import JsonResponse, QueryDict
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404

from BoMConfig.models import Header, Baseline, Baseline_Revision, REF_CUSTOMER, User_Customer
from BoMConfig.forms import SubmitForm
from BoMConfig.views.landing import Unlock, Default
from BoMConfig.utils import RollbackBaseline, TestRollbackBaseline, \
    RollbackError, RevisionCompare

import json


@login_required
def BaselineLoad(oRequest):
    """
    This method is used as a landing page for Baseline Management while the
    useful view loads
    :param oRequest: Django Request object
    :return: HTTPResponse via Default function
    """

    return Default(oRequest, sTemplate='BoMConfig/baselineload.html')


@login_required
def BaselineMgmt(oRequest):
    """
    View to display baselines.  Either displays current active and in-process
    revisions for all baselines, or all revisions for one baseline, when
    provided.
    :param oRequest: Django request object
    :return: HTTPResponse via Default function
    """

    # Unlock any Headers that may have been locked for editing and remove any
    # old status messages
    # S-06171- added for restricting customer_unit as per logged in user's cu in baseline view
    aFilteredUser = User_Customer.objects.filter(user_id=oRequest.user.id)
    aAvailableCU = []
    for oCan in aFilteredUser:

        for aFilteredCU in REF_CUSTOMER.objects.filter(id=oCan.customer_id):
            aAvailableCU.append(aFilteredCU)

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
    bDetailed = False
    dTableData = None
    aTable = []
    # A POST was submitted, the user is searching for a baseline, so show single
    # baseline details
    if oRequest.method == 'POST' and oRequest.POST['baseline_title']:
        # If part is called when the baseline is selected from the baseline dropdown & the page gets reloaded
        form = SubmitForm(oRequest.POST)
        if form.is_valid():
            oBaseline = form.cleaned_data['baseline_title']
            # S-06171: Baseline Restricts CU- This is the queryset that populates based on CU list of logged in user
            form.fields['baseline_title'].queryset = Baseline.objects.filter(customer__in=aAvailableCU).exclude(isdeleted=1)
            # First get list of baseline revisions for this baseline a sort them
            # in reverse order
            aRevisions = sorted(
                list(
                    set(
                        [
                            oBaseRev.version for oBaseRev in
                            oBaseline.baseline_revision_set.order_by('version')
                            ]
                    )
                ),
                key=RevisionCompare,
                reverse=True
            )

            dTableData = {'baseline': oBaseline, 'revisions': []}

            # Collect Headers for each Baseline_Revision
            for sRev in aRevisions:
                aHeads = Header.objects.filter(
                    baseline__baseline=oBaseline).filter(
                    baseline_version=sRev).order_by('configuration_status',
                                                    'pick_list',
                                                    'configuration_designation')
                if aHeads:
                    dTableData['revisions'].append({
                        'revision': Baseline_Revision.objects.get(
                            baseline=oBaseline, version=sRev),
                        'configs': aHeads,
                        'customer': ' '.join(
                            set(
                                [oHead.customer_unit.name
                                    .replace(" ", "-_").replace("&", "_") for
                                 oHead in aHeads]
                            )
                        )
                    })

                    if not bDownloadable:
                        bDownloadable = True
                # end if
            # end for

            bDetailed = True
        # end if

        if dTableData:
            aTable = [dTableData]
        # end if

    # Otherwise, show current in-process and active revision details for all
    # baselines
    else:
        #Else part is called when the baseline page loads
        form = SubmitForm()
        form.fields['baseline_title'].queryset = Baseline.objects.filter(customer__in=aAvailableCU).exclude(isdeleted=1)
        aBaselines = Baseline.objects.filter(customer__in=aAvailableCU).exclude(isdeleted=1)

        # For each baseline, get header data for active and in-process
        # Baseline_Revision
        for oBaseline in aBaselines:
            aRevisions = [oBaseline.current_inprocess_version or None,
                          oBaseline.current_active_version or None]
            dTableData = {'baseline': oBaseline, 'revisions': []}

            for sRev in aRevisions:
                if not sRev:
                    continue
                aHeads = Header.objects.filter(
                    baseline__baseline=oBaseline).filter(
                    baseline_version=sRev).order_by('configuration_status',
                                                    'pick_list',
                                                    'configuration_designation')
        # S-11565:Baseline tab - main page adjustments - Added Customer_name in the dTableData below, set here the CNAME for the baselines to be able
        # to filter based on CName
                if aHeads:
                    dTableData['revisions'].append({
                        'revision': Baseline_Revision.objects.get(
                            baseline=oBaseline, version=sRev),
                        'configs': aHeads,
                        'customer': oBaseline.customer.name
                        .replace(" ", "-_").replace("&", "_"),
                        'customer_name': oBaseline.customer_name
                    })
                # end if
            # end for

            aTable.append(dTableData)
        # end for

        # Add information for "No Associated Baseline" baseline
        # S-06171: Baseline Restricts CU-.filter(customer_unit__in=aAvailableCU) appended to 'configs'
        if Baseline.objects.filter(title='No Associated Baseline'):
            oBaseline = Baseline.objects.get(title='No Associated Baseline')
            aRevisions = [oBaseline.current_inprocess_version or None,
                          oBaseline.current_active_version or None]
          # S-11565:Baseline tab - main page adjustments - Added Customer_name in the aTable, set here as blank like done for revision
            aTable.append(
                {
                    'baseline': oBaseline,
                    'revisions': [
                        {
                            'revision': '',
                            'configs': Header.objects.filter(
                                baseline__baseline=oBaseline).filter(customer_unit__in=aAvailableCU).filter(
                                baseline_version__in=aRevisions).order_by(
                                'configuration_status', 'pick_list',
                                'configuration_designation'),
                            'customer': " ".join(
                                [cust.name.replace(" ", "-_").replace("&", "_")
                                 for cust in REF_CUSTOMER.objects.all()]),
                            'customer_name': ''
                        }
                    ],
                }
            )
    # end if

    aTitles = ['', 'Configuration', 'Product Area 2', 'Status', 'BoM Request Type', 'Program',
               'Customer Number', 'Second Customer Number', 'Model', 'Model Description',
               'Customer Price', 'Created Year', 'Inquiry/Site Template Number',
               'Model Replacing', 'Comments', 'Release Date', 'ZUST', 'P-Code',
               'Plant']  # S-05745: Add Second Customer number in Baseline View added Second Customer Number

    # S-06171: Baseline Restricts CU- added a cust_list attribute in dContext for CU fiter dropdown
    dContext = {
        'form': form,
        'tables': aTable,
        'downloadable': bDownloadable,
        'detailed': bDetailed,
        'column_titles': aTitles,
        'cust_list': aAvailableCU,
    }

    return Default(oRequest, sTemplate='BoMConfig/baselinemgmt.html',
                   dContext=dContext)
# end def

def BaselineRollbackTest(oRequest):
    """
    View to initiate a test BaselineRollback to ensure that a baseline is
    capable of being rolled back (to the previous revision)
    :param oRequest: Django request object
    :return: JSONResponse
    """
    data = QueryDict(oRequest.POST.get('form'))
    oBaseline = Baseline.objects.get(title=data['baseline'])

    dResult = {
        'status': 0,
        'errors': []
    }

    # Attempt to run TestRollbackBaseline.  If it errors or fails, append the
    # errors to the response.
    try:
        aDuplicates = TestRollbackBaseline(oBaseline)
        if not aDuplicates:
            dResult['status'] = 1
        else:
            sTemp = ('<p>The following configurations must be removed from '
                     'the in-process revision</p>')
            sTemp += '<ul>'
            for oHead in aDuplicates:
                sTemp += '<li>{}{}</li>'.format(
                    oHead.configuration_designation,
                    " (" + oHead.program.name + ")" if oHead.program else ''
                )
            sTemp += '</ul>'
            dResult['errors'].append(sTemp)
    except RollbackError as ex:
        # S-10576: Change the header of the tool to ACC :- Changed the tool name from pcbm to acc
        if 'release date' in str(ex):
            dResult['errors'].append("<p>Active revision was not released via "
                                     "the ACC tool.</p>")
        elif 'previous revision' in str(ex):
            dResult['errors'].append("<p>No previous revision exists in the "
                                     "ACC tool.</p>")

    return JsonResponse(dResult)
# end def

def DeleteBaseline(oRequest):

    if oRequest.method == 'POST' and oRequest.POST:
        aRecords = [
            int(record) for record in json.loads(oRequest.POST.get('data'))]


        Baseline.objects.filter(pk__in=aRecords).update(
            isdeleted=1)

        Baseline_Revision.objects.filter(baseline__in=aRecords).update(
            isdeleted=1)

        return HttpResponse()
    else:
        raise Http404()

# end def

def BaselineRollback(oRequest):
    """
    View to active the baseline rollback feature.
    :param oRequest: Django request object
    :return: JSONResponse
    """
    data = QueryDict(oRequest.POST.get('form'))

    oBaseline = Baseline.objects.get(title=data['baseline'])
    tOld = (oBaseline.current_active_version,
            oBaseline.current_inprocess_version)

    dResult = {
        'status': 0,
        'revision': '',
        'errors': []
    }

    # Attempt to run RollbackBaseline.  If it errors, append errors to response.
    try:
        RollbackBaseline(oBaseline)
        tNew = (oBaseline.current_active_version,
                oBaseline.current_inprocess_version)
        dResult['status'] = 1
        dResult['revision'] = 'from<br/><br/>{}<br/><br/>to<br/><br/>{}'.format(
            *('Active: {} / Inprocess: {}'.format(active, inproc) for
              (active, inproc) in (tOld, tNew)))
    except Exception as ex:
        dResult['errors'].append(str(ex))

    return JsonResponse(dResult)

