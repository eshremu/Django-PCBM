__author__ = 'epastag'

from BoMConfig.models import Header, Baseline
from BoMConfig.forms import SubmitForm
from BoMConfig.views.landing import Unlock, Default

from functools import cmp_to_key


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
                aHeads = Header.objects.filter(baseline__baseline=oBaseline).filter(baseline_version=sRev).order_by('configuration_status')
                if aHeads:
                    dTableData['revisions'].append({'revision': sRev, 'configs': aHeads})
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
            aRevisions = sorted(list(set([oBaseRev.version for oBaseRev in oBaseline.baseline_revision_set.order_by('version') if oBaseRev.version == oBaseRev.baseline.current_active_version])),
                                key=cmp_to_key(lambda x,y:(-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                 or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))
                                                                 or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1)),
                                reverse=True)

            dTableData = {'baseline': oBaseline.title, 'revisions':[]}

            for sRev in aRevisions[:1]:
                aHeads = Header.objects.filter(baseline__baseline=oBaseline).filter(baseline_version=sRev).order_by('configuration_status')
                if aHeads:
                    dTableData['revisions'].append({'revision': sRev, 'configs': aHeads})
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
                        'configs': Header.objects.filter(baseline__isnull=True).order_by('configuration_designation')
                    }
                ]
            }
        )
    # end if

    aTitles = ['','','Configuration','Status','Program','Customer Number','Model','Model Description','Customer Price',
               'Inquiry/Site Template Number','Model Replacing','Comments','ZUST','P-Code','Plant']

    return Default(oRequest, sTemplate='BoMConfig/baselinemgmt.html', dContext={'form': form, 'tables': aTable, 'downloadable': bDownloadable, 'column_titles': aTitles})
# end def