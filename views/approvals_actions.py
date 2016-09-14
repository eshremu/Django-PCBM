__author__ = 'epastag'

from django.utils import timezone
from django.http import HttpResponse, Http404, JsonResponse
from django.core.urlresolvers import reverse
from django.template import Template, Context, loader
from django.core.mail import send_mail, EmailMultiAlternatives
from django.shortcuts import redirect
from django.db import transaction
from django.db.models import Q

from BoMConfig.models import Header, Baseline, Baseline_Revision, REF_CUSTOMER, REF_REQUEST, SecurityPermission,\
    HeaderTimeTracker, REF_STATUS, ApprovalList, PartBase, ConfigLine, Part, CustomerPartInfo, PricingObject
from BoMConfig.utils import UpRev, GrabValue, StrToBool
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
        'deaddate': timezone.datetime(1900, 1, 1),
        'namelist':['PSM Configuration Mgr.', 'SCM #1', 'SCM #2', 'CSR','Comm. Price Mgmt.','ACR','PSM Baseline Mgmt.',
                    'Customer #1','Customer #2','Customer Warehouse','Ericsson VAR','Baseline Release & Dist.'],
        'viewauthorized': SecurityPermission.objects.filter(title__iregex='^.*Approval.*$').filter(user__in=oRequest.user.groups.all()),
        'skip_authorized': SecurityPermission.objects.filter(title__iexact='BLM_Approval_Write').filter(user__in=oRequest.user.groups.all()),
        'notify_users': {key: set(User.objects.filter(groups__securitypermission__title__in=value).exclude(groups__name__startswith='BOM_BPMA')) for key,value in HeaderTimeTracker.permission_map().items()}
    }
    return Default(oRequest, sTemplate='BoMConfig/approvals.html', dContext=dContext)
# end def


def Action(oRequest, **kwargs):
    if 'existing' in oRequest.session:
        try:
            Unlock(oRequest, oRequest.session['existing'])
        except Header.DoesNotExist:
            pass
        # end try

        del oRequest.session['existing']
    # end if

    if 'type' in kwargs:
        sTemplate = 'BoMConfig/actions_{}.html'.format(kwargs['type'])
    else:
        return redirect('bomconfig:action_inprocess')

    dContext = {
        'in_process': Header.objects.filter(configuration_status__name='In Process'),
        'active': Header.objects.filter(configuration_status__name='Active', inquiry_site_template=None, pick_list=False),
        'on_hold': Header.objects.filter(configuration_status__name='On Hold'),
        'customer_list': ['All'] + [obj.name for obj in REF_CUSTOMER.objects.all()],
        'viewauthorized': bool(oRequest.user.groups.filter(name__in=['BOM_BPMA_Architect','BOM_PSM_Product_Supply_Manager', 'BOM_PSM_Baseline_Manager'])),
        'approval_seq': HeaderTimeTracker.approvals(),
    }
    return Default(oRequest, sTemplate=sTemplate, dContext=dContext)
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

        if getattr(oHeadTracker, oRequest.POST['level']+"_approver") != 'system':
            try:
                oUser = User.objects.get(username=getattr(oHeadTracker, oRequest.POST['level']+"_approver"))
                dResult['person'] = oUser.first_name + " " + oUser.last_name
            except User.DoesNotExist:
                dResult['person'] = '(User not found)'
        else:
            dResult['person'] = 'System'

        if oRequest.POST['level'] != 'psm_config':
            dResult['comments'] = getattr(oHeadTracker, oRequest.POST['level']+"_comments", 'N/A')
            if getattr(oHeadTracker, oRequest.POST['level']+"_approved_on"):
                dResult['date'] = getattr(oHeadTracker, oRequest.POST['level']+"_approved_on").strftime('%m/%d/%Y')

                if getattr(oHeadTracker, oRequest.POST['level']+"_approved_on").date() == timezone.datetime(1900, 1, 1).date():
                    dResult['type'] = 'S'
                else:
                    dResult['type'] = 'A'
            elif getattr(oHeadTracker, oRequest.POST['level']+"_denied_approval"):
                dResult['date'] = getattr(oHeadTracker, oRequest.POST['level']+"_denied_approval").strftime('%m/%d/%Y')
                dResult['type'] = 'D'
        else:
            dResult['type'] = 'A'
            dResult['date'] = oHeadTracker.submitted_for_approval.strftime('%m/%d/%Y')
            dResult['comments'] = 'N/A'

        return JsonResponse(dResult)
    else:
        raise Http404()


@transaction.atomic
def AjaxApprove(oRequest):
    if oRequest.method == 'POST' and oRequest.POST:
        if oRequest.POST.get('action', None) not in ('approve', 'disapprove', 'skip', 'clone', 'delete', 'send_to_approve', 'hold', 'unhold', 'cancel'):
            raise Http404
        sAction = oRequest.POST.get('action')
        aRecords = [int(record) for record in json.loads(oRequest.POST.get('data'))]
        if 'comments' in oRequest.POST:
            aComments = [record for record in json.loads(oRequest.POST.get('comments', None))]
        if 'destinations' in oRequest.POST:
            aDestinations = [record for record in json.loads(oRequest.POST.get('destinations', None))]

        dEmailRecipients = {}
        if sAction == 'send_to_approve':
            dApprovalData = json.loads(oRequest.POST.get('approval'))

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
                    oLatestTracker = HeaderTimeTracker.objects.create(**{
                        'header': oHeader,
                        'submitted_for_approval': timezone.now(),
                        'psm_config_approver': oRequest.user.username,
                        'created_on': oCreated
                    })

                dRecordApprovals = dApprovalData[str(iRecord)]
                try:
                    oApprovalList = ApprovalList.objects.get(customer=oHeader.customer_unit)
                except ApprovalList.DoesNotExist:
                    oApprovalList = None

                for index, level in enumerate(HeaderTimeTracker.approvals()):
                    if level in ('psm_config', 'brd'):
                        continue
                    if (oApprovalList and str(index) in oApprovalList.disallowed.split(',')) or (not StrToBool(dRecordApprovals[level][0])):
                        setattr(oLatestTracker, level + '_approver', 'system')
                        setattr(oLatestTracker, level + '_approved_on', timezone.datetime(1900, 1, 1))
                        setattr(oLatestTracker, level + '_comments', 'Not required for this customer')
                    elif dRecordApprovals[level][1]:
                        if int(dRecordApprovals[level][1]) != 0:
                            oNotifyUser = User.objects.get(id=dRecordApprovals[level][1])
                            setattr(oLatestTracker, level + "_notify", oNotifyUser.email)
                        else:
                            setattr(oLatestTracker, level + "_notify", dRecordApprovals[level][2])

                oLatestTracker.save()

                if hasattr(oLatestTracker, oLatestTracker.next_approval + '_notify'):
                    sNextLevel = oLatestTracker.next_approval
                    for sRecip in list(set(getattr(oLatestTracker, sNextLevel + '_notify').split(';'))):
                        if sRecip not in dEmailRecipients:
                            dEmailRecipients[sRecip] = {'submit': {}}

                        if sNextLevel:
                            if sNextLevel not in dEmailRecipients[sRecip]['submit'].keys():
                                dEmailRecipients[sRecip]['submit'][sNextLevel] = {}

                            if oLatestTracker.header.baseline_impacted not in dEmailRecipients[sRecip]['submit'][sNextLevel].keys():
                                dEmailRecipients[sRecip]['submit'][sNextLevel][oLatestTracker.header.baseline_impacted] = []

                            dEmailRecipients[sRecip]['submit'][sNextLevel][oLatestTracker.header.baseline_impacted].append(oLatestTracker)

                oHeader.configuration_status = REF_STATUS.objects.get(name='In Process/Pending')
                oHeader.save()
            # end for

        elif sAction in ('approve', 'disapprove', 'skip'):
            from BoMConfig.views.download import EmailDownload
            aChain = HeaderTimeTracker.approvals()
            aBaselinesCompleted = []
            for index in range(len(aRecords)):
                oHeader = Header.objects.get(pk=aRecords[index])
                oLatestTracker = oHeader.headertimetracker_set.order_by('-submitted_for_approval')[0]

                sNeededLevel = oLatestTracker.next_approval

                aNames = HeaderTimeTracker.permission_entry(sNeededLevel)
                try:
                    bCanApprove = bool(SecurityPermission.objects.filter(title__in=aNames).filter(user__in=oRequest.user.groups.all()))
                except ValueError:
                    bCanApprove = False
                # end if

                # If so, approve, disapprove, or skip as requested
                if bCanApprove:
                    if sAction == 'approve':
                        setattr(oLatestTracker, sNeededLevel+'_approver', oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_approved_on', timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments', aComments[index])

                        aRecipients = []
                        if aDestinations[index]:
                            aRecipients.append(User.objects.get(id=aDestinations[index]).email)

                        sNotifyLevel = oLatestTracker.next_approval
                        if sNotifyLevel != 'brd':
                            if hasattr(oLatestTracker, str(sNotifyLevel) + '_notify') and getattr(oLatestTracker, str(sNotifyLevel) + '_notify', None):
                                aRecipients.extend(getattr(oLatestTracker, sNotifyLevel + '_notify').split(";"))
                        else:
                            aRecipients.extend([user.email for user in User.objects.filter(groups__name="BOM_PSM_Baseline_Manager")])

                        if aRecipients:
                            for sRecip in list(set(aRecipients)):
                                if sRecip not in dEmailRecipients:
                                    dEmailRecipients[sRecip] = {'approve':{}}

                                if sNotifyLevel:
                                    if sNotifyLevel not in dEmailRecipients[sRecip]['approve'].keys():
                                        dEmailRecipients[sRecip]['approve'][sNotifyLevel] = {}

                                    if oLatestTracker.header.baseline_impacted not in dEmailRecipients[sRecip]['approve'][sNotifyLevel].keys():
                                        dEmailRecipients[sRecip]['approve'][sNotifyLevel][oLatestTracker.header.baseline_impacted] = []

                                    dEmailRecipients[sRecip]['approve'][sNotifyLevel][oLatestTracker.header.baseline_impacted].append(oLatestTracker)


                    elif sAction == 'disapprove':
                        setattr(oLatestTracker, sNeededLevel+'_approver', oRequest.user.username)
                        setattr(oLatestTracker, sNeededLevel+'_denied_approval', timezone.now())
                        setattr(oLatestTracker, sNeededLevel+'_comments', aComments[index])
                        oLatestTracker.disapproved_on = timezone.now()

                        # Create a new time tracker, if not disapproved back to PSM
                        sReturnedLevel = 'psm_config'
                        if aDestinations[index] != 'psm_config':
                            oNewTracker = HeaderTimeTracker.objects.create(**{'header': oHeader,
                                                                              'created_on': oLatestTracker.created_on,
                                                                              'submitted_for_approval': timezone.now()
                                                                              })
                            # Copy over approval data for each level before destination level
                            for level in aChain:
                                if level == aDestinations[index]:
                                    sReturnedLevel = level
                                # end if

                                if (aChain.index(level) < aChain.index(aDestinations[index])) or (getattr(oLatestTracker, level + '_approver')=='system'):
                                    setattr(oNewTracker, level+'_approver', getattr(oLatestTracker, level + '_approver', None))

                                if level == 'psm_config':
                                    continue
                                # end if

                                if (aChain.index(level) < aChain.index(aDestinations[index])) or (getattr(oLatestTracker, level + '_approver')=='system'):
                                    setattr(oNewTracker, level+'_denied_approval', getattr(oLatestTracker, level + '_denied_approval', None))
                                    setattr(oNewTracker, level+'_approved_on', getattr(oLatestTracker, level + '_approved_on', None))
                                    setattr(oNewTracker, level+'_comments', getattr(oLatestTracker, level + '_comments', None))

                                if hasattr(oNewTracker, level + "_notify"):
                                    setattr(oNewTracker, level + '_notify', getattr(oLatestTracker, level + '_notify', None))
                            # end for

                            oNewTracker.save()

                            sLastApprover = getattr(oLatestTracker, sReturnedLevel + '_approver', None)
                            if hasattr(oLatestTracker, sReturnedLevel + '_notify'):
                                sLastNotify = getattr(oLatestTracker, sReturnedLevel + '_notify', None)
                            else:
                                sLastNotify = None
                            if sLastApprover or sLastNotify:
                                aRecipients = []
                                if sLastApprover:
                                    aRecipients.append(User.objects.get(username=sLastApprover).email)

                                if sLastNotify:
                                    aRecipients.extend(sLastNotify.split(";"))

                                for sRecip in list(set(aRecipients)):
                                    if sRecip not in dEmailRecipients:
                                        dEmailRecipients[sRecip] = {'disapprove': {}}

                                    if sReturnedLevel:
                                        if sReturnedLevel not in dEmailRecipients[sRecip]['disapprove'].keys():
                                            dEmailRecipients[sRecip]['disapprove'][sReturnedLevel] = {}

                                        if oLatestTracker.header.baseline_impacted not in dEmailRecipients[sRecip]['disapprove'][sReturnedLevel].keys():
                                            dEmailRecipients[sRecip]['disapprove'][sReturnedLevel][oLatestTracker.header.baseline_impacted] = []

                                        dEmailRecipients[sRecip]['disapprove'][sReturnedLevel][oLatestTracker.header.baseline_impacted].append(oLatestTracker)

                        # Else, send header back to 'In Process' status
                        else:
                            oHeader.configuration_status = REF_STATUS.objects.get(name='In Process')
                            oHeader.save()

                            if User.objects.get(username=oLatestTracker.psm_config_approver).email not in dEmailRecipients:
                                dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]={'disapprove':{}}

                            if 'psm_config' not in dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]['disapprove'].keys():
                                dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]['disapprove']['psm_config'] = {}

                            if oLatestTracker.header.baseline_impacted not in dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]['disapprove']['psm_config'].keys():
                                dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]['disapprove']['psm_config'][oLatestTracker.header.baseline_impacted] = []

                            dEmailRecipients[User.objects.get(username=oLatestTracker.psm_config_approver).email]['disapprove']['psm_config'][oLatestTracker.header.baseline_impacted].append(oLatestTracker)
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
                EmailDownload(oBaseline)
            # end for
        elif sAction == 'clone':
            oOldHeader = Header.objects.get(pk=aRecords[0])
            oNewHeader = CloneHeader(oOldHeader)

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

        for key in dEmailRecipients.keys():
            for approval in dEmailRecipients[key]:
                for level in dEmailRecipients[key][approval]:
                    for baseline in dEmailRecipients[key][approval][level]:
                        oMessage = EmailMultiAlternatives(
                            subject=(baseline or '(No baseline)') + ' Review & Approval',
                            body=loader.render_to_string(
                                'BoMConfig/approval_approve_email_plain.txt',
                                {'submitter': oRequest.user.get_full_name(),
                                 'records': dEmailRecipients[key][approval][level][baseline],
                                 'recipient': User.objects.filter(email=key).first().first_name if User.objects.filter(
                                     email=key) else key,
                                 'level': level,
                                 'action': approval
                                 }
                            ),
                            from_email='pcbm.admin@ericsson.com',
                            to=[key],
                            cc=[oRequest.user.email],
                            bcc=list(set([User.objects.get(username=getattr(oRecord, sublevel + '_approver')).email
                                 for oRecord in dEmailRecipients[key][approval][level][baseline]
                                 for sublevel in aChain[aChain.index(level):aChain.index(oRecord.disapproved_level)]
                                 ])) if approval == 'disapprove' else [],
                            headers={'Reply-To': oRequest.user.email}
                        )
                        oMessage.attach_alternative(loader.render_to_string(
                            'BoMConfig/approval_approve_email.html',
                            {'submitter': oRequest.user.get_full_name(),
                             'records': dEmailRecipients[key][approval][level][baseline],
                             'recipient': User.objects.filter(email=key).first().first_name if User.objects.filter(
                                 email=key) else key,
                             'level': level,
                             'action': approval
                             }
                        ), 'text/html')
                        oMessage.send(fail_silently=False)
                    # end for
                # end for
            # end for
        # end for

        return HttpResponse()
    else:
        raise Http404()
# end def


def CloneHeader(oHeader):
    oOldHeader = oHeader
    oNewHeader = copy.deepcopy(oOldHeader)
    oNewHeader.pk = None
    oNewHeader.configuration_designation = oOldHeader.configuration_designation + '_______CLONE_______'
    oNewHeader.configuration_status = REF_STATUS.objects.get(name='In Process')
    if oNewHeader.react_request is None:
        oNewHeader.react_request = ''
    # end if

    if oNewHeader.baseline_impacted:
        oNewHeader.baseline = Baseline_Revision.objects.get(
            baseline=Baseline.objects.get(title=oNewHeader.baseline_impacted),
            version=Baseline.objects.get(title=oNewHeader.baseline_impacted).current_inprocess_version)
        oNewHeader.baseline_version = oNewHeader.baseline.version
    # end if

    iTry = 1
    while len(Header.objects.filter(configuration_designation=oNewHeader.configuration_designation, program=oNewHeader.program, baseline=oNewHeader.baseline, baseline_version=oNewHeader.baseline_version)) > 0:
        oNewHeader.configuration_designation = oOldHeader.configuration_designation + '_______CLONE' + str(iTry) + '_______'
        iTry += 1

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

        if hasattr(oConfigLine, 'linepricing'):
            oNewPrice = copy.deepcopy(oConfigLine.linepricing)
            oNewPrice.pk = None
            oNewPrice.config_line = oNewLine
            oNewPrice.save()
        # end if
    # end for
    return oNewHeader
# end def


def AjaxApprovalForm(oRequest):
    if oRequest.POST:
        aRecords = json.loads(oRequest.POST['data'])

        aApprovalLevels = HeaderTimeTracker.approvals()[1:-1]
        dPermissionLevels = HeaderTimeTracker.permission_map()

        dForm = {}

        for record in aRecords:
            oHeader = Header.objects.get(id=record)
            dContext = {'approval_levels': aApprovalLevels,
                        'required': (GrabValue(ApprovalList.objects.filter(customer=oHeader.customer_unit).first(), 'required') or '').split(','),
                        'optional': (GrabValue(ApprovalList.objects.filter(customer=oHeader.customer_unit).first(), 'optional') or '').split(','),
                        'disallowed': (GrabValue(ApprovalList.objects.filter(customer=oHeader.customer_unit).first(), 'disallowed') or '').split(','),
                        'email': {}
                        }

            for key, value in dPermissionLevels.items():
                if key in aApprovalLevels:
                    dContext['email'].update({key: list(set(User.objects.filter(groups__securitypermission__in=SecurityPermission.objects.filter(title__in=value)).exclude(groups__name__contains='BPMA')))})

            dForm[record] = [oHeader.configuration_designation + "  " + oHeader.baseline_version, loader.render_to_string('BoMConfig/approvalform.html', dContext)]

        return JsonResponse(dForm)
    else:
        return Http404()
# end def


def ChangePart(oRequest):
    if oRequest.POST:
        dResponse = {}

        if oRequest.POST['action'] == 'search':
            dResponse['type'] = 'search'
            sPart = oRequest.POST.get('part','')
            sPart = sPart.upper().strip()
            if sPart:
                try:
                    oPart = PartBase.objects.get(product_number=sPart)
                    aLines = ConfigLine.objects.filter(part__base=oPart,
                                                       config__header__configuration_status__name='In Process')

                    # Create list of tuple representing configuration name, program, baseline, object, is_changeable)
                    aHeaders = [(oLine.config.header.configuration_designation, oLine.config.header.program,
                                 oLine.config.header.baseline_impacted, oLine.config.header, True) for oLine in aLines]

                    # In-Process/Pending records are not changeable, since they are pending approval
                    aLines = ConfigLine.objects.filter(part__base=oPart,
                                                       config__header__configuration_status__name='In Process/Pending')

                    aHeaders.extend([(oLine.config.header.configuration_designation, oLine.config.header.program,
                                 oLine.config.header.baseline_impacted, oLine.config.header, False) for oLine in aLines])

                    # Active records are only changeable if no in-process copy exists (and therefore can be cloned)
                    aLines = ConfigLine.objects.filter(part__base=oPart,
                                                       config__header__configuration_status__name='Active')

                    oInProc = Q(configuration_status__name__in=['In Process', 'In Process/Pending'])
                    oHoldInProc = Q(old_configuration_status__name__in=['In Process', 'In Process/Pending'])
                    for oLine in aLines:
                        # If in-process copy exists
                        if Header.objects.filter(oInProc|oHoldInProc,
                                                 configuration_designation=oLine.config.header.configuration_designation,
                                                 program=oLine.config.header.program,
                                                 baseline_impacted=oLine.config.header.baseline_impacted):
                            oObj = Header.objects.filter(
                                oInProc | oHoldInProc,
                                configuration_designation=oLine.config.header.configuration_designation,
                                program=oLine.config.header.program,
                                baseline_impacted=oLine.config.header.baseline_impacted).first()

                            # If in-process copy is already in list of records, skip the record
                            if (oLine.config.header.configuration_designation, oLine.config.header.program, oLine.config.header.baseline_impacted, oObj, False) in aHeaders or\
                                (oLine.config.header.configuration_designation, oLine.config.header.program,
                                 oLine.config.header.baseline_impacted, oObj, True) in aHeaders:
                                pass
                            else:
                                aHeaders.append((oLine.config.header.configuration_designation, oLine.config.header.program, oLine.config.header.baseline_impacted, oLine.config.header, False))
                        else:
                            aHeaders.append((oLine.config.header.configuration_designation,
                                             oLine.config.header.program, oLine.config.header.baseline_impacted,
                                             oLine.config.header, True))

                    if not aHeaders:
                        dResponse['error'] = True
                        dResponse['status'] = 'No records containing part'
                    else:
                        aHeaders = list(set(aHeaders))
                        aHeaders.sort(key=lambda x:(x[0], x[1].name if x[1] else '', x[2]))
                        dResponse['error'] = False
                        dResponse['records'] = [{'id': tHeader[3].id,
                                                 'configuration_designation': tHeader[0],
                                                 'program': tHeader[1].name if tHeader[1] else '(None)',
                                                 'baseline': tHeader[2] or '(None)',
                                                 'status': tHeader[3].configuration_status.name,
                                                 'selectable': tHeader[4]} for tHeader in aHeaders]
                        dResponse['part'] = sPart
                except PartBase.DoesNotExist:
                    dResponse['error'] = True
                    dResponse['status'] = 'No matching part'
            else:
                dResponse['error'] = True
                dResponse['status'] = 'No part number provided'
        elif oRequest.POST['action'] == 'replace':
            dResponse['type'] = 'replace'

            sPart = oRequest.POST.get('part')
            sPart = sPart.upper().strip()

            sReplacePart = oRequest.POST.get('replacement')
            sReplacePart = sReplacePart.upper().strip()

            try:
                int(sReplacePart)
                sReplacePart += '/'
            except ValueError:
                pass

            aRecords = json.loads(oRequest.POST.get('records'))

            if sReplacePart:
                if sReplacePart != sPart:
                    if aRecords:
                        for id in aRecords:
                            oHeader = Header.objects.get(id=id)
                            # print(oHeader)
                            if oHeader.configuration_status.name != 'In Process':
                                # print('Clone header')
                                oNewHeader = CloneHeader(oHeader)
                                oNewHeader.configuration_designation = oHeader.configuration_designation
                                oNewHeader.bom_request_type = REF_REQUEST.objects.get(name='Update')
                                oNewHeader.model_replaced = ''
                                oNewHeader.model_replaced_link = oHeader
                                oNewHeader.save()
                                oHeader = oNewHeader

                            # print('Get or create replacement part')
                            (oReplacementBase, _) = PartBase.objects.get_or_create(product_number=sReplacePart, defaults={'unit_of_measure':'PC'})
                            try:
                                (oReplacement, _) = Part.objects.get_or_create(base=oReplacementBase)
                            except Part.MultipleObjectsReturned:
                                oReplacement = Part.objects.filter(base=oReplacementBase).first()

                            for oLine in oHeader.configuration.configline_set.filter(part__base__product_number=sPart):
                                # print(oLine)
                                # print('Change', sPart, 'to', sReplacePart)
                                oLine.part = oReplacement
                                oLine.vendor_article_number = sReplacePart.strip('./')
                                # print('Update LinePricing object for new part')
                                oLinePrice = None
                                try:
                                    oLinePrice = PricingObject.objects.get(customer=oHeader.customer_unit,
                                                                           part=oReplacementBase,
                                                                           is_current_active=True,
                                                                           sold_to=oHeader.sold_to_party,
                                                                           spud=oLine.spud)
                                except PricingObject.DoesNotExist:
                                    try:
                                        oLinePrice = PricingObject.objects.get(customer=oHeader.customer_unit,
                                                                               part=oReplacementBase,
                                                                               is_current_active=True,
                                                                               sold_to=oHeader.sold_to_party,
                                                                               spud=None)
                                    except PricingObject.DoesNotExist:
                                        try:
                                            oLinePrice = PricingObject.objects.get(customer=oHeader.customer_unit,
                                                                                   part=oReplacementBase,
                                                                                   is_current_active=True,
                                                                                   sold_to=None,
                                                                                   spud=oLine.spud)
                                        except PricingObject.DoesNotExist:
                                            try:
                                                oLinePrice = PricingObject.objects.get(customer=oHeader.customer_unit,
                                                                                       part=oReplacementBase,
                                                                                       is_current_active=True,
                                                                                       sold_to=None,
                                                                                       spud=None)
                                            except PricingObject.DoesNotExist:
                                                pass

                                oLine.linepricing.pricing_object = oLinePrice
                                # print('Update customer part number for new part')
                                try:
                                    oCustInfo = CustomerPartInfo.objects.get(active=True, part=oReplacementBase, customer=oHeader.customer_unit)
                                    oLine.customer_number = oCustInfo.customer_number
                                    oLine.sec_customer_number = oCustInfo.second_customer_number
                                    oLine.customer_asset_tagging = 'Y' if oCustInfo.customer_asset_tagging else 'N' if oCustInfo.customer_asset_tagging is False else ''
                                    oLine.customer_asset = 'Y' if oCustInfo.customer_asset else 'N' if oCustInfo.customer_asset is False else ''
                                except CustomerPartInfo.DoesNotExist:
                                    oLine.customer_number = None
                                    oLine.sec_customer_number = None
                                    oLine.customer_asset_tagging = None
                                    oLine.customer_asset = None

                                oLine.save()
                            # end for
                        # end for

                        dResponse['error'] = False
                        dResponse['status'] = 'Part number successfully replaced'

                    else:
                        dResponse['error'] = True
                        dResponse['status'] = 'No records selected for replacement'
                    # end if
                else:
                    dResponse['error'] = True
                    dResponse['status'] = 'Replacement part is the same as the searched part'
                # end if

            else:
                dResponse['error'] = True
                dResponse['status'] = 'No replacement part'
            # end if

        # end if

        return JsonResponse(dResponse)
    else:
        return Http404
