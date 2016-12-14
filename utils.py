__author__ = 'epastag'
from django.utils import timezone
from django.db.models import Q
from BoMConfig.models import Header, Baseline, RevisionHistory, Baseline_Revision, REF_STATUS, LinePricing, \
    REF_CUSTOMER, REF_REQUEST
from copy import deepcopy
import datetime
from functools import cmp_to_key
import re


RevisionCompare = cmp_to_key(lambda x, y: (-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                  list(y.strip('1234567890')))
                                                                or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1))


def UpRev(oRecord, sExceptionHeader=None, sExceptionRev=None, sCopyToRevision=None):
    if not isinstance(oRecord,(Baseline, Header)):
        raise TypeError('UpRev can only be passed a Baseline or Header type object')
    # end if

    if isinstance(oRecord,Header) and not sCopyToRevision:
        raise ValueError('Must provide sCopyToRevision when passing a Header to this function')
    # end if
    oNewInprocRev = None
    sNewInprocessRev = ''
    if isinstance(oRecord, Baseline):
        sCurrentActiveRev = oRecord.current_active_version
        try:
            oCurrActiveRev = Baseline_Revision.objects.get(**{'baseline':oRecord, 'version': sCurrentActiveRev})
            aHeaders = oCurrActiveRev.header_set.exclude(configuration_status__name='Discontinued')\
                .exclude(configuration_status__name='Cancelled').exclude(configuration_status__name='Inactive')
        except Baseline_Revision.DoesNotExist:
            aHeaders = []

        sCurrentInProcRev = oRecord.current_inprocess_version
        oCurrInprocRev = Baseline_Revision.objects.get(**{'baseline':oRecord, 'version': sCurrentInProcRev})

        # Need to create a new in-process revision : new in-p = increm(curr in-p) or revision being uploaded
        if sExceptionRev and RevisionCompare(sCurrentInProcRev) < RevisionCompare(sExceptionRev) < RevisionCompare(IncrementRevision(sCurrentInProcRev)):
            sNewInprocessRev = sExceptionRev
        else:
            sNewInprocessRev = IncrementRevision(sCurrentInProcRev)
        (oNewInprocRev, _) = Baseline_Revision.objects.get_or_create(**{'baseline':oRecord, 'version': sNewInprocessRev})

        # Move in-process & in-process/pending records from current in-process rev to new in-process rev
        aHeadersToMoveToInProc = oCurrInprocRev.header_set.filter(configuration_status__name__in=['In Process', 'In Process/Pending', 'On Hold'])

        for oHeader in aHeadersToMoveToInProc:
            oHeader.baseline = oNewInprocRev
            oHeader.baseline_version = sNewInprocessRev
            oHeader.save()
        # end for
    else:
        aHeaders = [oRecord]
        sCurrentInProcRev = sCopyToRevision
        oCurrInprocRev = Baseline_Revision.objects.get(**{'baseline':oRecord.baseline.baseline, 'version': sCurrentInProcRev})
    # end if

    # Copy active records from current active rev to current in-proc rev
    for oHeader in aHeaders:
        oNextHeader = Header.objects.filter(configuration_designation=oHeader.configuration_designation, program=oHeader.program, baseline_version=sCurrentInProcRev)
        if not((oHeader.configuration_designation == sExceptionHeader and IncrementRevision(oHeader.baseline_version) == sExceptionRev) or oNextHeader):

            oNewHeader = deepcopy(oHeader)
            oNewHeader.pk = None
            oNewHeader.baseline_version = sCurrentInProcRev
            if oNewHeader.react_request is None:
                oNewHeader.react_request = ''
            # end if
            oNewHeader.baseline = oCurrInprocRev
            oNewHeader.model_replaced_link = oHeader
            if oNewHeader.bom_request_type.name == 'New':
                oNewHeader.bom_request_type = REF_REQUEST.objects.get(name='Update')
                oNewHeader.model_replaced = ''
            oNewHeader.save()

            oNewConfig = deepcopy(oHeader.configuration)
            oNewConfig.pk = None
            oNewConfig.header = oNewHeader
            oNewConfig.save()

            for oConfigLine in oHeader.configuration.configline_set.all():
                oNewLine = deepcopy(oConfigLine)
                oNewLine.pk = None
                oNewLine.config = oNewConfig
                oNewLine.save()

                oNewPrice = deepcopy(oConfigLine.linepricing) if hasattr(oConfigLine, 'linepricing') else LinePricing()
                oNewPrice.pk = None
                oNewPrice.config_line = oNewLine
                oNewPrice.save()
            # end for
        # end if

        # 'Inactive' current active version of records
        oHeader.configuration_status = REF_STATUS.objects.get(name='Inactive')
        if oHeader.change_comments:
            oHeader.change_comments += '\n'
        else:
            oHeader.change_comments = ''
        # end if

        oHeader.change_comments += 'Baseline revision increment'
        oHeader.save()
    # end for

    if isinstance(oRecord, Baseline):
        # Make current in-proc rev into curr active rev
        oCurrInprocRev.completed_date = timezone.now()
        oCurrInprocRev.save()

        if (oNewInprocRev):
            oNewInprocRev.previous_revision = oCurrInprocRev
            oNewInprocRev.save()

        oRecord.current_active_version = sCurrentInProcRev
        oRecord.current_inprocess_version = sNewInprocessRev
        oRecord.save()

        # GenerateRevisionSummary(oRecord, sCurrentActiveRev, sCurrentInProcRev)
        MassUploaderUpdate(oRecord)
    # end if
# end def


def IncrementRevision(sRevision):
    if not isinstance(sRevision, str):
        raise TypeError("Function must be passed type 'str'. Unrecognized type: " + str(type(sRevision)))

    if not sRevision.isalpha():
        sRevision = sRevision.rstrip('1234567890')
    # end if

    sRevision = sRevision.upper()

    return GetLetterCode(char_to_num(sRevision) + 1)


def char_to_num(sString):
    """Converts Base 26 sString (Using A-Z) to Base 10 decimal."""
    # if not sString:
    #     return 0
    #
    # return char_to_num(sString[:-1])*26 + (ord(sString[-1]) - 64)
    i = 0
    for iIndex, sLetter in enumerate(sString):
        i += (ord(sLetter) - 64) * (26 ** (len(sString) - iIndex - 1))
    return i


def GetLetterCode(iColumn):
    """Converts iColumn to its corresponding letter(s) value."""
    if not 1 <= iColumn:
        raise ValueError("Invalid column number: " + str(iColumn))
    # end if

    if iColumn > 26:
        # The return value of iColumn // 26 is one greater than what it
        # should be on each multiple of 26. For example, GetLetterCode(52)
        # should return AZ, but because 52 // 26 is 2, it instead returns
        # B@. So, a minor correction is required for cases in which iColumn
        # is a multiple of 26.
        if iColumn % 26 == 0:
            iModifier = (iColumn // 26) - 1
            iConvertToChar = 26
        else:
            iModifier = (iColumn // 26)
            iConvertToChar = iColumn % 26
        # end if

        return GetLetterCode(iModifier) + chr(iConvertToChar + 64)
    else:
        return chr(iColumn + 64)
    # end if
# end def


def DecrementRevision(sRevision):
    if not isinstance(sRevision, str):
        raise TypeError("Function must be passed type 'str'. Unrecognized type: " + str(type(sRevision)))

    if not sRevision.strip():
        raise Exception('Revision cannot be decremented any further')

    if not sRevision.isalpha():
        raise ValueError('String must not contain non-alphabet characters')
    # end if

    sRevision = sRevision.upper()

    return GetLetterCode(char_to_num(sRevision) - 1)


def MassUploaderUpdate(oBaseline=None):
    """
    After a mass upload, this function will go through the database and make changes to the data to ensure conformity:
        - For each baseline:
            -- Each header will be checked to make sure it is in the most recent revision if still active
            -- Historical entries will be made in order to show progress from previous revisions
                I.E.: If a configuration is Active on revision AD, and another configuration is active on AF, and the
                baseline is on revision AF, then the AD config needs to be on AF, but we also need to create a copy on
                revision AE, so that we can maintain a historical track of what configs were on which revisions, etc.
            -- Historical entries will be corrected to show status as 'Inactive' so that only the most recent revision
                is active, but historical data still exists
            -- Revision History items will be generated/updated for each baseline revision from earliest to current
        - If 'oBaseline' is provided, the above will only be done for the Baseline provided
    """
    if oBaseline:
        aBaselines = [oBaseline]
    else:
        aBaselines = Baseline.objects.all()
    # end if

    for oBase in aBaselines:
        # Get list of revisions that exist
        aExistingRevs = sorted(list(set([oBaseRev.version for oBaseRev in oBase.baseline_revision_set.order_by('version')])),
                               key=RevisionCompare)

        aPrevRevs = deepcopy(aExistingRevs)
        try:
            aPrevRevs.remove(oBase.current_active_version)
        except ValueError:
            pass
        # end try

        aPrevRevs.remove(oBase.current_inprocess_version)
        aExistingRevs.remove(oBase.current_inprocess_version)

        dHeadersToMoveForward = {}
        for rev in aPrevRevs:
            oPrevBaseRev = Baseline_Revision.objects.get(baseline=oBase, version=rev)
            for oHeader in oPrevBaseRev.header_set.all():
                key = (oHeader.configuration_designation, oHeader.program)
                if oHeader.configuration_status.name == 'Active':
                    if key in dHeadersToMoveForward:
                        dHeadersToMoveForward[key][-1][1] = rev
                        dHeadersToMoveForward[key][-1][2] = oHeader.configuration_status.name
                        dHeadersToMoveForward[key].append([rev,'',''])
                    else:
                        dHeadersToMoveForward[key] = [[rev, '','']]
                    # end if
                elif oHeader.configuration_status.name in ('Discontinued', 'Cancelled', 'Inactive'):
                    if key in dHeadersToMoveForward:
                        if dHeadersToMoveForward[key][-1][1] == '':
                            dHeadersToMoveForward[key][-1][1] = rev
                            dHeadersToMoveForward[key][-1][2] = oHeader.configuration_status.name
                        # end if
                    else:
                        pass
                    # end if
                # end if
            # end for
        # end for

        for (config_name, prog), rev_list in dHeadersToMoveForward.items():
            for aMoveParams in rev_list:
                iFrom = aExistingRevs.index(aMoveParams[0])
                if aMoveParams[1]:
                    iTo = aExistingRevs.index(aMoveParams[1])
                else:
                    iTo = len(aExistingRevs)
                # end if
                sFinalStatus = aMoveParams[2]

                while iFrom < (iTo - 1):
                    oHeader = Header.objects.get(configuration_designation=config_name, baseline_version=aExistingRevs[iFrom], program=prog)

                    try:
                        UpRev(oHeader, sCopyToRevision=aExistingRevs[iFrom + 1])
                    except:
                        pass
                    iFrom += 1
                # end while

                if iFrom != len(aExistingRevs) - 1:
                    oHeader = Header.objects.get(configuration_designation=config_name, baseline_version=aExistingRevs[iFrom], program=prog)
                    oHeader.configuration_status = REF_STATUS.objects.get(name='Inactive')
                    if oHeader.change_comments:
                        oHeader.change_comments += '\nBaseline revision increment'
                    else:
                        oHeader.change_comments = 'Baseline revision increment'
                    # end if
                    oHeader.save()
                # end if
            # end for
        # end for

        aExistingRevs = [None] + aExistingRevs
        aExistingRevs.append(oBase.current_inprocess_version)
        for index in range(len(aExistingRevs) - 1):
            GenerateRevisionSummary(oBase, aExistingRevs[index], aExistingRevs[index + 1])
        # end for
    # end for
# end def


def GenerateRevisionSummary_old(oBaseline, sPrevious, sCurrent):
    """
    Compares two revisions of a baseline and generates a summary of configurations dropped and added.  Also generates
    a summary of changes made on configurations found in both revisions.
    """

    if sPrevious:
        oPrevBaseline = Baseline_Revision.objects.get(**{'baseline': oBaseline, 'version': sPrevious})
        aPrevHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oPrevBaseline.header_set.all()]
        aPrevDiscontinuedHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oPrevBaseline.header_set\
            .filter(configuration_status__name='Discontinued')]
    else:
        aPrevHeaders = []
        aPrevDiscontinuedHeaders = []
    # end if

    oCurrBaseline = Baseline_Revision.objects.get(**{'baseline': oBaseline, 'version': sCurrent})
    aCurrHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oCurrBaseline.header_set.all()]
    aDiscontinuedHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oCurrBaseline.header_set\
        .filter(configuration_status__name='Discontinued')]

    aNew = set(aCurrHeaders).difference(set(aPrevHeaders))
    aRemoved = set(set(set(aPrevHeaders).difference(set(aCurrHeaders))).difference(set(aDiscontinuedHeaders))).difference(set(aPrevDiscontinuedHeaders))
    sNewSummary = 'Added:\n'
    for (sNew,_) in aNew:
        sNewSummary += '    - {}\n'.format(sNew)
    # end for

    sDiscontinuedSummary = 'Discontinued:\n'
    for (sDiscontinue,_) in aDiscontinuedHeaders:
        sDiscontinuedSummary += '    - {}\n'.format(sDiscontinue)
    # end for

    sRemoveSummary = 'Removed:\n'
    for (sRemove,_) in aRemoved:
        sRemoveSummary += '    - {}\n'.format(sRemove)
    # end for

    dUpdates = {}
    for (sHeader, oProg) in set(set(aCurrHeaders).difference(set(aDiscontinuedHeaders))).intersection(set(aPrevHeaders)):
        dUpdates[sHeader] = []
        oCurrHead = oCurrBaseline.header_set.filter(configuration_designation=sHeader).filter(baseline_version=sCurrent).filter(program=oProg)[0]

        if sPrevious:
            oPrevHead = oPrevBaseline.header_set.filter(configuration_designation=sHeader).filter(baseline_version=sPrevious).filter(program=oProg)[0]

            aPrevLines = oPrevHead.configuration.configline_set.all()
            aPrevLines = sorted(aPrevLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
            aPrevLines = [oLine for oLine in aPrevLines if '.' not in oLine.line_number]
            aPrevLineNumbers = [oLine.line_number for oLine in aPrevLines]
        else:
            aPrevLineNumbers = []

        aCurrLines = oCurrHead.configuration.configline_set.all()
        aCurrLines = sorted(aCurrLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
        aCurrLines = [oLine for oLine in aCurrLines if '.' not in oLine.line_number]
        aCurrLineNumbers = [oLine.line_number for oLine in aCurrLines]

        aRemovedLines = [sLine for sLine in aPrevLineNumbers if sLine not in aCurrLineNumbers]
        aAddedLines = [sLine for sLine in aCurrLineNumbers if sLine not in aPrevLineNumbers]
        aCarriedLines = [sLine for sLine in aPrevLineNumbers if sLine in aCurrLineNumbers]

        for line in aRemovedLines:
            [oPrevLine] = [oPrev for oPrev in aPrevLines if oPrev.line_number == line]
            dUpdates[sHeader].append('Removed: Line {0}; Product {1}'.format(oPrevLine.line_number,
                                                                             oPrevLine.part.base.product_number))
        # end for

        for line in aAddedLines:
            [oNewLine] = [oNew for oNew in aCurrLines if oNew.line_number == line]
            dUpdates[sHeader].append('Added: Line {0}; Product {1}'.format(oNewLine.line_number,
                                                                             oNewLine.part.base.product_number))
        # end for


        for line in aCarriedLines:
            [oPrevLine] = [oPrev for oPrev in aPrevLines if oPrev.line_number == line]
            [oCurrLine] = [oCurr for oCurr in aCurrLines if oCurr.line_number == line]

            if oCurrLine.part.base.product_number != oPrevLine.part.base.product_number:
                dUpdates[sHeader].append('{0} - Replaced {1} with {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.part.base.product_number,
                                                                              oCurrLine.part.base.product_number))
            # end if

            if oCurrLine.order_qty != oPrevLine.order_qty:
                dUpdates[sHeader].append('{0} - Changed order qty from {1} to {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.order_qty, oCurrLine.order_qty))
            # end if

            # if oCurrLine.plant != oPrevLine.plant:
            #     dUpdates[sHeader].append('{0} - Changed plant from {1} to {2}'.format(oCurrLine.line_number,
            #                                                                   oPrevLine.plant,
            #                                                                   oCurrLine.plant))
            # # end if
            #
            # if oCurrLine.sloc != oPrevLine.sloc:
            #     dUpdates[sHeader].append('{0} - Changed SLOC from {1} to {2}'.format(oCurrLine.line_number,
            #                                                                   oPrevLine.sloc,
            #                                                                   oCurrLine.sloc))
            # # end if
            #
            # if oCurrLine.item_category != oPrevLine.item_category:
            #     dUpdates[sHeader].append('{0} - Changed Item Cat. from {1} to {2}'.format(oCurrLine.line_number,
            #                                                                   oPrevLine.item_category,
            #                                                                   oCurrLine.item_category))
            # # end if
            #
            # if oCurrLine.pcode != oPrevLine.pcode:
            #     dUpdates[sHeader].append('{0} - Changed P-Code from {1} to {2}'.format(oCurrLine.line_number,
            #                                                                   oPrevLine.pcode,
            #                                                                   oCurrLine.pcode))
            # # end if

            if GrabValue(oCurrLine,'linepricing.pricing_object') and GrabValue(oPrevLine,'linepricing.pricing_object')\
                    and oCurrLine.linepricing.pricing_object.unit_price != oPrevLine.linepricing.pricing_object.unit_price:
                dUpdates[sHeader].append('{0} - Changed Unit Price from ${1} to ${2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.linepricing.pricing_object.unit_price,
                                                                              oCurrLine.linepricing.pricing_object.unit_price))
            # end if
        # end for

        if not dUpdates[sHeader]:
            del dUpdates[sHeader]
        # end if
    # end for

    sHistory = ''
    if len(sNewSummary) > 7:
        sHistory += sNewSummary
    if len(sDiscontinuedSummary) > 14:
        sHistory += sDiscontinuedSummary
    if len(sRemoveSummary) > 9:
        sHistory += sRemoveSummary

    if dUpdates:
        sHistory += 'Updated:\n'
        for sConfig in dUpdates.keys():
            sHistory += '    - {}\n'.format(sConfig)
            for sUpdate in dUpdates[sConfig]:
                sHistory += '        -- {}\n'.format(sUpdate)
            # end for
        # end for
    # end if

    (oNew, _) = RevisionHistory.objects.get_or_create(baseline=oBaseline, revision=sCurrent)
    oNew.history = sHistory
    oNew.save()
# end def


def GrabValue(oStartObj, sAttrChain, default=None):
    import functools
    try:
        value = functools.reduce(lambda x, y: getattr(x, y), sAttrChain.split('.'), oStartObj)
        if value is None:
            return default
        else:
            return functools.reduce(lambda x, y: getattr(x, y), sAttrChain.split('.'), oStartObj)
    except AttributeError:
        return default
# end def


class RollbackError(Exception):
    pass


def TestRollbackBaseline(oBaseline):
    oCurrentActive = oBaseline.latest_revision

    if oCurrentActive is None:
        raise RollbackError('No previous revision exists')

    try:
        oReleaseDate = max([oTrack.completed_on for oHead in oBaseline.latest_revision.header_set.all() for oTrack in
                            oHead.headertimetracker_set.all() if oTrack.completed_on])
    except ValueError:
        raise RollbackError('No release date could be determined')

    oCurrentInprocess = Baseline_Revision.objects.get(baseline=oBaseline, version=oBaseline.current_inprocess_version)

    aRemainingHeaders = []
    aDuplicates = []

    for oHead in oCurrentActive.header_set.all():
        if any([oTrack for oTrack in oHead.headertimetracker_set.all() if
                abs(oTrack.created_on - oReleaseDate) > datetime.timedelta(minutes=1)]):
            aRemainingHeaders.append(oHead)

    for oHead in aRemainingHeaders:
        if oCurrentInprocess.header_set.filter(configuration_designation=oHead.configuration_designation, program=oHead.program):
            aDuplicates.append(oHead)

    return aDuplicates
#end def


def RollbackBaseline(oBaseline):
    """
    Function rolls back a baseline to the previous revision.
    All headers that were copied forward as part of an UpRev will be
    deleted, headers that were a part of the release that triggered
    the UpRev will be returned to an "In Procees/Pending" state.
    Headers that were made inactive in the previous active revision
    will returned to Active state.
    """

    aExistingRevs = sorted(
        list(set([oBaseRev.version for oBaseRev in oBaseline.baseline_revision_set.order_by('version')])),
        key=RevisionCompare
    )

    try:
        oReleaseDate = max([oTrack.completed_on for oHead in oBaseline.latest_revision.header_set.all() for oTrack in
                            oHead.headertimetracker_set.all() if oTrack.completed_on])
    except ValueError:
        raise RollbackError('No release date could be determined')

    oCurrentActive = oBaseline.latest_revision
    oCurrentInprocess = Baseline_Revision.objects.get(baseline=oBaseline, version=oBaseline.current_inprocess_version)
    oPreviousActive = None

    iPrevIndex = aExistingRevs.index(oBaseline.current_active_version) - 1
    if iPrevIndex >= 0:
        oPreviousActive = Baseline_Revision.objects.get(baseline=oBaseline, version=aExistingRevs[iPrevIndex])

    # print('Determined release date to be:', str(oReleaseDate))
    for oHead in oCurrentActive.header_set.all():
        if any([oTrack for oTrack in oHead.headertimetracker_set.all() if
                abs(oTrack.created_on - oReleaseDate) < datetime.timedelta(minutes=1)]):
            oHead.delete()
            # print('Deleting:', str(oHead))
        else:
            oHead.configuration_status = REF_STATUS.objects.get(name='In Process/Pending')
            oHead.save()
            # print('Changing to "In Process/Pending":', str(oHead))

            oLatestTracker = oHead.headertimetracker_set.last()
            if oLatestTracker and oLatestTracker.completed_on:
                oLatestTracker.completed_on = None
                oLatestTracker.brd_approver = None
                oLatestTracker.brd_approved_on = None
                oLatestTracker.brd_comment = None
                oLatestTracker.save()
                # print('Removing "Completed On" tracker info:', str(oLatestTracker))
            # end if
        # end if
    # end for

    for oHead in oCurrentInprocess.header_set.all():
        oHead.baseline = oCurrentActive
        oHead.baseline_version = oBaseline.current_active_version
        oHead.save()
        # print('Reverting from in-process revision:', str(oHead))
    # end for

    if oPreviousActive:
        for oHead in oPreviousActive.header_set.all():
            if oHead.configuration_status.name in ('Inactive', 'Obsolete'):
                oHead.configuration_status = REF_STATUS.objects.get(name='Active')
                oHead.change_comments = oHead.change_comments.replace('\nBaseline revision increment', '')\
                    .replace('Baseline revision increment', '')
                oHead.save()
                # print('Returning to "Active":', str(oHead))
            # end if
        # end for
    # end if

    oCurrentActive.completed_date = None
    oCurrentActive.save()
    # print('Removing Baseline revision release date:', str(oCurrentActive))
    oCurrentInprocess.delete()
    # print('Deleting Baseline revision:', str(oCurrentInprocess))

    RevisionHistory.objects.filter(baseline=oBaseline, revision__in=aExistingRevs[aExistingRevs
                                   .index(oBaseline.current_active_version):]).delete()
    # print('Deleting revision history:', *aExistingRevs[aExistingRevs.index(oBaseline.current_active_version):])

    oBaseline.current_inprocess_version = oBaseline.current_active_version
    if oPreviousActive:
        oBaseline.current_active_version = aExistingRevs[iPrevIndex]
    else:
        oBaseline.current_active_version = ''
    # end if
    oBaseline.save()
    # print('Reverting Baseline to current as {} and in-process as {}'.format(
    #     aExistingRevs[iPrevIndex] if oPreviousActive else '(None)', oBaseline.current_active_version))
# end def


def GenerateRevisionSummary(oBaseline, sPrevious, sCurrent):
    oDiscontinued = Q(configuration_status__name='Discontinued')
    oToDiscontinue = Q(bom_request_type__name='Discontinue')
    aDiscontinuedHeaders = [oHead for oHead in Baseline_Revision
        .objects.get(baseline=oBaseline, version=sCurrent).header_set.filter(oDiscontinued|oToDiscontinue)
        .exclude(program__name__in=('DTS',)).exclude(configuration_status__name='On Hold').exclude(configuration_status__name='In Process')]
    aAddedHeaders = [oHead for oHead in Baseline_Revision
        .objects.get(baseline=oBaseline, version=sCurrent).header_set.filter(bom_request_type__name='New')
        .exclude(program__name__in=('DTS',)).exclude(configuration_status__name='On Hold').exclude(configuration_status__name='In Process')]
    aUpdatedHeaders = [oHead for oHead in Baseline_Revision
        .objects.get(baseline=oBaseline, version=sCurrent).header_set.filter(bom_request_type__name='Update')
        .exclude(oDiscontinued).exclude(program__name__in=('DTS',)).exclude(configuration_status__name='On Hold').exclude(configuration_status__name='In Process')]

    aPrevHeaders = []
    aPrevButNotCurrent = []
    aCurrButNotPrev = []
    for oHead in aUpdatedHeaders:
        try:
            obj = Baseline_Revision.objects.get(baseline=oBaseline, version=sPrevious).header_set\
                .get(configuration_designation=oHead.configuration_designation, program=oHead.program)
            if not (obj.configuration_designation, obj.program) in aDiscontinuedHeaders:
                aPrevHeaders.append(obj)
            else:
                aPrevButNotCurrent.append(obj)
            # end if
        except (Header.DoesNotExist, Baseline_Revision.DoesNotExist):
            aCurrButNotPrev.append(oHead)
        # end try

    sNewSummary = 'Added:\n'
    sRemovedSummary = 'Discontinued:\n'

    for oHead in aAddedHeaders:
        if oHead.model_replaced:
            sNewSummary += '    {} replaces {}\n'.format(
                oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
                ('  {}'.format(oHead.configuration.get_first_line().customer_number)
                 if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else ''),

                oHead.model_replaced_link.configuration_designation +
                (" ({})".format(oHead.model_replaced_link.program.name) if
                 oHead.model_replaced_link.program else '') +
                ('  {}'.format(oHead.model_replaced_link.configuration.get_first_line().customer_number)
                 if not oHead.model_replaced_link.pick_list and
                    oHead.model_replaced_link.configuration.get_first_line().customer_number else '')
                if oHead.model_replaced_link else oHead.model_replaced
            )

            sRemovedSummary += '    {} is replaced by {}\n'.format(
                oHead.model_replaced_link.configuration_designation +
                (" ({})".format(oHead.model_replaced_link.program.name) if
                 oHead.model_replaced_link.program else '') +
                ('  {}'.format(oHead.model_replaced_link.configuration.get_first_line().customer_number)
                 if not oHead.model_replaced_link.pick_list and
                    oHead.model_replaced_link.configuration.get_first_line().customer_number else '')
                if oHead.model_replaced_link else oHead.model_replaced,

                oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
                ('  {}'.format(oHead.configuration.get_first_line().customer_number)
                 if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else '')
            )
        else:
            # If a previous revision exists and a matching header exists in previous revision and the Header has a
            # time tracker without a completed date or disapproved date, but is not In-Process, then the Header must
            # have been carried forward from a previous revision, and therefore is not ACTUALLY New / Added
            if Baseline_Revision.objects.filter(baseline=oBaseline, version=sPrevious) and \
                    Baseline_Revision.objects.get(baseline=oBaseline, version=sPrevious).header_set \
                    .filter(configuration_designation=oHead.configuration_designation, program=oHead.program) and \
                    not oHead.configuration_status.name == 'In Process/Pending' and \
                    oHead.headertimetracker_set.filter(completed_on=None, disapproved_on=None):
                continue

            sNewSummary += '    {} added\n'.format(
                oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
                ('  {}'.format(oHead.configuration.get_first_line().customer_number)
                 if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else '')
            )
        # end if
    # end for

    for oHead in aCurrButNotPrev:
        sNewSummary += '    {} added\n'.format(
            oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
            ('  {}'.format(oHead.configuration.get_first_line().customer_number)
             if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else '')
        )
    # end for

    for oHead in aDiscontinuedHeaders:
        if (oHead.model_replaced_link and any([obj in oHead.model_replaced_link.replaced_by_model.all() for obj in aAddedHeaders
                                               if hasattr(oHead.model_replaced_link, 'replaced_by_model')])) or\
                any([obj in oHead.replaced_by_model.all() for obj in aAddedHeaders if hasattr(oHead, 'replaced_by_model')]):
            continue

        sRemovedSummary += '    {} discontinued\n'.format(
            oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
                ('  {}'.format(oHead.configuration.get_first_line().customer_number)
                 if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else '')
        )
    # end for

    for oHead in aPrevButNotCurrent:
        sRemovedSummary += '    {} removed\n'.format(
            oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else '') +
                ('  {}'.format(oHead.configuration.get_first_line().customer_number)
                 if not oHead.pick_list and oHead.configuration.get_first_line().customer_number else '')
        )
    # end for

    # if aDiscontinuedHeaders:
    #     for oHead in aDiscontinuedHeaders:
    #         sRemovedSummary += '\t{} is replaced by {}\n'.format(oHead.model_replaced, oHead.configuration_designation + (' ({})'.format(oHead.program.name) if oHead.program else ''))
        # end for
    # end if

    sUpdateSummary = "Updated:\n"
    for oHead in aUpdatedHeaders:
        # print(oHead)
        sTemp = ''
        # aPotentialMatches = []
        try:
            oPrev = oHead.model_replaced_link or Header.objects.get(
                configuration_designation=oHead.configuration_designation,
                program=oHead.program,
                baseline_version=sPrevious
            )
            sTemp = HeaderComparison(oHead, oPrev)
        except Header.DoesNotExist:
            sTemp = ''
        # end try

        if sTemp:
            oHead.change_notes = sTemp
            oHead.save()
            sUpdateSummary += '    {}:\n'.format(oHead.configuration_designation + \
                                                 (' ({})'.format(oHead.program) if oHead.program else '') + \
                              ('  {}'.format(oHead.configuration.get_first_line().customer_number) if not oHead.pick_list
                                                     and oHead.configuration.get_first_line().customer_number else ''))
            for sLine in sTemp.split('\n'):
                sUpdateSummary += (' ' * 8) + sLine + '\n'
        # end if
    # end for

    # print(sNewSummary, sRemovedSummary, sUpdateSummary, sep='\n')
    sHistory = ''

    if sNewSummary != 'Added:\n':
        sHistory += sNewSummary
    if sRemovedSummary != 'Discontinued:\n':
        sHistory += sRemovedSummary
    if sUpdateSummary != "Updated:\n":
        sHistory += sUpdateSummary

    # print(sHistory)
    (oNew, _) = RevisionHistory.objects.get_or_create(baseline=oBaseline, revision=sCurrent)
    oNew.history = sHistory
    oNew.save()
# end def


def HeaderComparison(oHead, oPrev):
    sTemp = ''
    aPotentialMatches = []
    """
        Creating a dictionary for previous and current revision, keyed on (Part #, Line #), value of
        [Qty, Price, (Grandparent Part #, Parent Part #), Matching line key].
        This will be used to find a match between revisions, and track when a line has been moved rather than
        removed or replaced.
        """
    dPrevious = {}
    dCurrent = {}
    oATT = REF_CUSTOMER.objects.get(name='AT&T')

    for oConfigLine in oHead.configuration.configline_set.all():
        dCurrent[(oConfigLine.part.base.product_number, oConfigLine.line_number)] = [
            oConfigLine.order_qty,
            GrabValue(oConfigLine, 'linepricing.override_price') or GrabValue(oConfigLine,
                                                                'linepricing.pricing_object.unit_price') or None,
            (
                oHead.configuration.configline_set.get(line_number=oConfigLine.line_number[
                                                                   :oConfigLine.line_number.find(
                                                                       '.')]).part.base.product_number if oConfigLine.is_grandchild else None,
                oHead.configuration.configline_set.get(line_number=oConfigLine.line_number[
                                                                   :oConfigLine.line_number.rfind(
                                                                       '.')]).part.base.product_number if oConfigLine.is_child else None
            ),
            None
        ]

    for oConfigLine in oPrev.configuration.configline_set.all():
        dPrevious[(oConfigLine.part.base.product_number, oConfigLine.line_number)] = [
            oConfigLine.order_qty,
            GrabValue(oConfigLine, 'linepricing.override_price') or GrabValue(oConfigLine,
                                                                'linepricing.pricing_object.unit_price') or None,
            (
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.find(
                                    '.')]).part.base.product_number if oConfigLine.is_grandchild and
                                                                       oHead.configuration.configline_set.filter(
                                                                           line_number=oConfigLine.line_number[
                                                                                       :oConfigLine.line_number.find(
                                                                                           '.')]) else None,
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.rfind(
                                    '.')]).part.base.product_number if oConfigLine.is_child and
                                                                       oHead.configuration.configline_set.filter(
                                                                           line_number=oConfigLine.line_number[
                                                                                       :oConfigLine.line_number.rfind(
                                                                                           '.')]) else None
            ),
            None
        ]

    # print(dPrevious, dCurrent, sep='\n')

    for (sPart, sLine) in dPrevious.keys():
        if (sPart, sLine) in dCurrent.keys():
            dCurrent[(sPart, sLine)][3] = dPrevious[(sPart, sLine)][3] = (sPart, sLine)
            if dCurrent[(sPart, sLine)][0] != dPrevious[(sPart, sLine)][0] or dCurrent[(sPart, sLine)][1] != \
                    dPrevious[(sPart, sLine)][1]:
                # print('Qty/Price change for:', sLine, sPart)
                if dCurrent[(sPart, sLine)][0] != dPrevious[(sPart, sLine)][0]:
                    sTemp += '{} - {} quantity changed from {} to {}\n'.format(sLine, sPart,
                                                                                       dPrevious[(sPart, sLine)][0],
                                                                                       dCurrent[(sPart, sLine)][0])

                if dCurrent[(sPart, sLine)][1] != dPrevious[(sPart, sLine)][1] and \
                        ((oHead.customer_unit == oATT and not oHead.pick_list and sLine == '10') or
                         (oHead.customer_unit == oATT and oHead.pick_list) or
                         oHead.customer_unit != oATT):
                    sTemp += '{} - {} line price changed from {} to {}\n'.format(sLine, sPart,
                                                                                         dPrevious[(sPart, sLine)][1],
                                                                                         dCurrent[(sPart, sLine)][1])

        else:
            if any(sPart == key[0] and dPrevious[(sPart, sLine)][2] == dCurrent[key][2] and not dCurrent[key][3] for key
                   in dCurrent.keys()):
                for key in dCurrent.keys():
                    if key[0] == sPart and dPrevious[(sPart, sLine)][2] == dCurrent[key][2] and not dCurrent[key][3]:
                        dPrevious[(sPart, sLine)][3] = key
                        dCurrent[key][3] = (sPart, sLine)
                        if key in [curr for (_, curr, _) in aPotentialMatches]:
                            aPotentialMatches[list([curr for (_, curr, _) in aPotentialMatches]).index(key)][2] = False
                        break

                if dCurrent[dPrevious[(sPart, sLine)][3]][0] != dPrevious[(sPart, sLine)][0] or \
                                dCurrent[dPrevious[(sPart, sLine)][3]][1] != dPrevious[(sPart, sLine)][1]:
                    # print('Qty/Price change for:', sLine, sPart)
                    if dCurrent[dPrevious[(sPart, sLine)][3]][0] != dPrevious[(sPart, sLine)][0]:
                        sTemp += '{} - {} quantity changed from {} to {}\n'.format(dPrevious[(sPart, sLine)][3][1], sPart,
                                                                                           dPrevious[(sPart, sLine)][0],
                                                                                           dCurrent[dPrevious[
                                                                                               (sPart, sLine)][3]][0])

                    if dCurrent[dPrevious[(sPart, sLine)][3]][1] != dPrevious[(sPart, sLine)][1] and \
                            ((oHead.customer_unit == oATT and not oHead.pick_list and sLine == '10') or
                             (oHead.customer_unit == oATT and oHead.pick_list) or
                             oHead.customer_unit != oATT):
                        sTemp += '{} - {} line price changed from {} to {}\n'.format(dPrevious[(sPart, sLine)][3][1], sPart,
                                                                                             dPrevious[(sPart, sLine)][
                                                                                                 1],
                                                                                             dCurrent[dPrevious[
                                                                                                 (sPart, sLine)][3]][1])

            else:
                """
                If part is not in new version, but line number still is, the part may have been replaced.
                However, the new version's matching line number may be a part in the previous version that has
                not been reached in the key list, so we will add the potential match to a list of possible
                matches.  After the the whole dictionary has been checked, entries without matches will be
                checked against the list of potential matches.
                """
                if any(sLine == sLnum for (_, sLnum) in dCurrent.keys()):
                    for key in dCurrent.keys():
                        if key[1] == sLine:
                            aPotentialMatches.append([(sPart, sLine), key, True])

    # One more check of potential matches to make sure none were missed
    for key in dCurrent.keys():
        if key in [curr for (_, curr, _) in aPotentialMatches] and dCurrent[key][3]:
            aPotentialMatches[list([curr for (_, curr, _) in aPotentialMatches]).index(key)][2] = False

    for key in dPrevious.keys():
        if not dPrevious[key][3]:
            for aEntry in aPotentialMatches:
                if key == aEntry[0] and aEntry[2]:
                    aEntry[2] = False
                    dPrevious[key][3] = aEntry[1]
                    dCurrent[aEntry[1]][3] = key
                    # print(key[1], key[0], 'replaced by', dPrevious[key][3][0])
                    sTemp += '{} - {} replaced by {}\n'.format(key[1], key[0], dPrevious[key][3][0])
                    break

    for key in dPrevious.keys():
        if not dPrevious[key][3]:
            # print(key[1], key[0], 'removed')
            sTemp += '{} - {} removed{}\n'.format(key[1], key[0],
                                                  ' (line number remained)' if key in [prev for (prev, _, _) in
                                                                                       aPotentialMatches] else '')

    for key in dCurrent.keys():
        if not dCurrent[key][3]:
            # print(key[1], key[0], 'added')
            sTemp += '{} - {} added\n'.format(key[1], key[0])
            # print()

    aLines = sTemp.split('\n')[:-1]
    aLines.sort(key=lambda x: [int(y) for y in x[:x.find(' -')].split('.')])
    return '\n'.join(aLines)
# end def


def TitleShorten(sTitle):
    sTitle = re.sub('Optional', 'Opt', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('Hardware', 'HW', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('Pick List', 'PL', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('_+CLONE(\d*)_+', '_CLONE\1_', sTitle, flags=re.IGNORECASE)
    return sTitle


def StrToBool(sValue, bDefault = None):
    """Convert a string to a bool. If the string is empty and a default is
    provided, it is returned; otherwise an exception is raised. If the string is
    not one that can be clearly interpreted as a Boolean value, raises an
    exception."""

    if sValue is None:
        return False

    sUpper = sValue.strip().upper()
    if sUpper in ('Y', 'YES', 'T', 'TRUE', '1'):
        return True
    elif sUpper in ('N', 'NO', 'F', 'FALSE', '0'):
        return False
    elif not sUpper:
        if bDefault is None:
            ValueError("Empty string provided and no default to return.")
        #end if
        return bDefault
    else:
        TypeError("Unrecognized Boolean string: " + sValue)
    #end if
#end def


def DetectBrowser(oRequest):
    sUserAgent = oRequest.META['HTTP_USER_AGENT']
    oRegex = re.compile(r'(?:[^ (]|\([^)]*\))+')
    aTokens = oRegex.findall(sUserAgent)

    if "Windows" in sUserAgent and 'Chrome' in sUserAgent:
        return next(token for token in aTokens if 'Chrome' in token)
    elif "Windows" in sUserAgent and 'Firefox' in sUserAgent:
        return next(token for token in aTokens if 'Firefox' in token)
    elif "Windows" in sUserAgent:
        sTemp = 'Internet Explorer'
        sRev = ''
        if 'rv:' in sUserAgent:
            iStart = sUserAgent.find('rv:')
            iStop = sUserAgent.find(')', iStart)
            sRev = sUserAgent[iStart + 3:iStop]

        if sRev:
            sTemp += '/' + sRev

        return sTemp
    # end if
# end def
