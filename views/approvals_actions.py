__author__ = 'epastag'

from django.utils import timezone
from django.http import HttpResponse, Http404, JsonResponse
from django.core.urlresolvers import reverse

from BoMConfig.models import Header, Baseline, Baseline_Revision, REF_CUSTOMER, REF_REQUEST, SecurityPermission, HeaderTimeTracker, REF_STATUS
from BoMConfig.utils import UpRev
from BoMConfig.views.landing import Unlock, Default
from django.contrib.auth.models import User

import copy
import json


def Approval(oRequest):
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    dContext = {
        'approval_wait': Header.objects.filter(configuration_status__name='In Process/Pending'),
        'customer_list': ['All'] + [obj.name for obj in REF_CUSTOMER.objects.all()],
        'approval_seq': HeaderTimeTracker.approvals(),
        'deaddate': timezone.datetime(1900,1,1),
        'namelist':['PSM Configuration Mgr.', 'SCM #1', 'SCM #2', 'CSR','Comm. Price Mgmt.','ACR','PSM Baseline Mgmt.',
                    'Customer #1','Customer #2','Customer Warehouse','Ericsson VAR','Baseline Release & Dist.'],
        'viewauthorized': SecurityPermission.objects.filter(title__iregex='^.*Approval.*$').filter(user__in=oRequest.user.groups.all()),
        'skip_authorized': SecurityPermission.objects.filter(title__iexact='BLM_Approval_Write').filter(user__in=oRequest.user.groups.all())
    }
    return Default(oRequest, sTemplate='BoMConfig/approvals.html', dContext=dContext)
# end def


def Action(oRequest):
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    dContext = {
        'in_process': Header.objects.filter(configuration_status__name='In Process'),
        'active': Header.objects.filter(configuration_status__name='Active'),
        'on_hold': Header.objects.filter(configuration_status__name='On Hold'),
        'customer_list': ['All'] + [obj.name for obj in REF_CUSTOMER.objects.all()],
        'viewauthorized': bool(oRequest.user.groups.filter(name__in=['BOM_BPMA_Architect','BOM_PSM_Product_Supply_Manager', 'BOM_PSM_Baseline_Manager']))
    }
    return Default(oRequest, sTemplate='BoMConfig/actions.html', dContext=dContext)
# end def


def ApprovalData(oRequest):
    if oRequest.method == 'POST' and oRequest.POST:
        oHeadTracker = HeaderTimeTracker.objects.get(id=oRequest.POST['id'])
        dResult = {
            'type': '',
            'person': '',
            'date': '',
            'comments': ''
        }

        oUser = User.objects.get(username=getattr(oHeadTracker,oRequest.POST['level']+"_approver"))
        dResult['person'] = oUser.first_name + " " + oUser.last_name

        if oRequest.POST['level'] != 'psm_config':
            dResult['comments'] = getattr(oHeadTracker,oRequest.POST['level']+"_comments", 'N/A')
            if getattr(oHeadTracker,oRequest.POST['level']+"_approved_on"):
                dResult['date'] = getattr(oHeadTracker,oRequest.POST['level']+"_approved_on").strftime('%m/%d/%Y')

                if getattr(oHeadTracker,oRequest.POST['level']+"_approved_on").date() == timezone.datetime(1900,1,1).date():
                    dResult['type'] = 'S'
                else:
                    dResult['type'] = 'A'
            elif getattr(oHeadTracker,oRequest.POST['level']+"_denied_approval"):
                dResult['date'] = getattr(oHeadTracker,oRequest.POST['level']+"_denied_approval").strftime('%m/%d/%Y')
                dResult['type'] = 'D'
        else:
            dResult['type'] = 'A'
            dResult['date'] = oHeadTracker.submitted_for_approval.strftime('%m/%d/%Y')
            dResult['comments'] = 'N/A'

        return JsonResponse(dResult)
    else:
        raise Http404()


def AjaxApprove(oRequest):
    if oRequest.method == 'POST' and oRequest.POST:
        if oRequest.POST.get('action', None) not in ('approve','disapprove','skip','clone','delete','send_to_approve', 'hold', 'unhold', 'cancel'):
            raise Http404
        sAction = oRequest.POST.get('action')
        aRecords = [int(record) for record in json.loads(oRequest.POST.get('data'))]
        if 'comments' in oRequest.POST:
            aComments = [record for record in json.loads(oRequest.POST.get('comments', None))]
        if 'destinations' in oRequest.POST:
            aDestinations = [record for record in json.loads(oRequest.POST.get('destinations', None))]

        if sAction == 'send_to_approve':
            for iRecord in aRecords:
                oHeader = Header.objects.get(pk=iRecord)
                oCreated = oHeader.headertimetracker_set.first().created_on
                if oHeader.headertimetracker_set.filter(submitted_for_approval=None):
                    oLatestTracker = oHeader.headertimetracker_set.filter(submitted_for_approval=None)[0]
                    oLatestTracker.submitted_for_approval = timezone.now()
                    oLatestTracker.psm_config_approver = oRequest.user.username
                    oLatestTracker.created_on = oCreated
                    oLatestTracker.save()
                else:
                    HeaderTimeTracker.objects.create(**{
                        'header': oHeader,
                        'submitted_for_approval': timezone.now(),
                        'psm_config_approver': oRequest.user.username,
                        'created_on': oCreated
                    })

                oHeader.configuration_status = REF_STATUS.objects.get(name='In Process/Pending')
                oHeader.save()
        elif sAction in ('approve', 'disapprove', 'skip'):
            aChain = HeaderTimeTracker.approvals()
            aBaselinesCompleted = []
            for index in range(len(aRecords)):
                oHeader = Header.objects.get(pk=aRecords[index])
                oLatestTracker = oHeader.headertimetracker_set.order_by('-submitted_for_approval')[0]

                sNeededLevel = None
                # Find earliest empty approval slot, and see if user has approval permission for that slot
                for level in aChain:
                    if getattr(oLatestTracker, level+'_denied_approval', None) is not None:
                        break
                    # end if

                    if getattr(oLatestTracker, level+'_approver','no attr') in (None, ''):
                        sNeededLevel = level
                        break
                    # end if
                # end for

                aNames = HeaderTimeTracker.permission_entry(sNeededLevel)
                bCanApprove = bool(SecurityPermission.objects.filter(title__in=aNames).filter(user__in=oRequest.user.groups.all()))
                # end if

                # If so, approve, disapprove, or skip as requested
                if bCanApprove:
                    if sAction == 'approve':
                        setattr(oLatestTracker, sNeededLevel+'_approver', oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_approved_on', timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments', aComments[index])
                    elif sAction == 'disapprove':
                        setattr(oLatestTracker, sNeededLevel+'_approver', oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_denied_approval', timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments', aComments[index])
                        oLatestTracker.disapproved_on = timezone.now()

                        # Create a new time tracker, if not disapproved back to PSM
                        if aDestinations[index] != 'psm_config':
                            oNewTracker = HeaderTimeTracker.objects.create(**{'header': oHeader,
                                                                              'created_on': oLatestTracker.created_on,
                                                                              'submitted_for_approval': timezone.now()
                                                                              })
                            # Copy over approval data for each level before destination level
                            for level in aChain:
                                if level == aDestinations[index]:
                                    break
                                # end if

                                setattr(oNewTracker, level+'_approver', getattr(oLatestTracker, level + '_approver', None))

                                if level == 'psm_config':
                                    continue
                                # end if

                                setattr(oNewTracker, level+'_denied_approval', getattr(oLatestTracker, level + '_denied_approval', None))
                                setattr(oNewTracker, level+'_approved_on', getattr(oLatestTracker, level + '_approved_on', None))
                                setattr(oNewTracker, level+'_comments', getattr(oLatestTracker, level + '_comments', None))
                            # end for

                            oNewTracker.save()
                        # Else, send header back to 'In Process' status
                        else:
                            oHeader.configuration_status = REF_STATUS.objects.get(name='In Process')
                            oHeader.save()
                        # end if
                    elif sAction == 'skip' and sNeededLevel != 'brd':
                        setattr(oLatestTracker, sNeededLevel+'_approver', oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_approved_on', timezone.datetime(1900,1,1))
                    oLatestTracker.save()

                    if sNeededLevel == 'brd' and sAction == 'approve':
                        oLatestTracker.completed_on = timezone.now()
                        oLatestTracker.save()

                        # Alter configuration status
                        if oHeader.bom_request_type.name in ('Discontinue','Legacy'):
                            oHeader.configuration_status = REF_STATUS.objects.get(name='Discontinued')
                        elif oHeader.bom_request_type.name in ('New','Update', 'Replacement'):
                            oHeader.configuration_status = REF_STATUS.objects.get(name='Active')
                        elif oHeader.bom_request_type.name == 'Preliminary':
                            oHeader.configuration_status = REF_STATUS.objects.get(name='In Process')
                            oHeader.bom_request_type = REF_REQUEST.objects.get(name='New')
                        oHeader.save()

                        if oHeader.configuration_status.name in ('Discontinued', 'Active') and oHeader.baseline_impacted:
                            aBaselinesCompleted.append(oHeader.baseline_impacted)
                        # end if
                    # end if
                # end if
            # end for

            aBaselinesCompleted = list(set(aBaselinesCompleted))
            aBaselinesToComplete = Baseline.objects.filter(title__in=aBaselinesCompleted)
            for oBaseline in aBaselinesToComplete:
                UpRev(oBaseline)
            # end for
        elif sAction == 'clone':
            oOldHeader = Header.objects.get(pk=aRecords[0])
            oNewHeader = copy.deepcopy(oOldHeader)
            oNewHeader.pk = None
            oNewHeader.configuration_designation = oOldHeader.configuration_designation + '_______CLONE_______'
            oNewHeader.configuration_status = REF_STATUS.objects.get(name='In Process')
            if oNewHeader.react_request is None:
                oNewHeader.react_request = ''
            # end if

            if oNewHeader.baseline_impacted:
                oNewHeader.baseline = Baseline_Revision.objects.get(baseline=Baseline.objects.get(title=oNewHeader.baseline_impacted),
                                                                    version=Baseline.objects.get(title=oNewHeader.baseline_impacted).current_inprocess_version)
                oNewHeader.baseline_version = oNewHeader.baseline.version
            # end if

            oNewHeader.save()

            oNewConfig = copy.deepcopy(oOldHeader.configuration)
            oNewConfig.pk = None
            oNewConfig.header = oNewHeader
            oNewConfig.save()

            for oConfigLine in oOldHeader.configuration.configline_set.all():
                oNewLine = copy.deepcopy(oConfigLine)
                oNewLine.pk = None
                oNewLine.config = oNewConfig
                oNewLine.save()

                if hasattr(oConfigLine,'linepricing'):
                    oNewPrice = copy.deepcopy(oConfigLine.linepricing)
                    oNewPrice.pk = None
                    oNewPrice.config_line = oNewLine
                    oNewPrice.save()
                # end if
            # end for

            oRequest.session['existing'] = oNewHeader.pk
            return HttpResponse(reverse('bomconfig:configheader'))
        elif sAction == 'delete':
            Header.objects.filter(pk__in=aRecords).delete()
        elif sAction == 'cancel':
            Header.objects.filter(pk__in=aRecords).update(configuration_status__name='Cancelled')
        elif sAction in ('hold', 'unhold'):
            for iRecord in aRecords:
                oHeader = Header.objects.get(pk=iRecord)
                oHeader.configuration.PSM_on_hold = not oHeader.configuration.PSM_on_hold
                oHeader.configuration.save()
            #end for
        # end if

        return HttpResponse()
    else:
        raise Http404()
# end def