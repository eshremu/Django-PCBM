"""
Utility functions that are used in various parts of the tool
"""
from django.utils import timezone
from django.db.models import Q
from BoMConfig.models import Header, Baseline, RevisionHistory,\
    Baseline_Revision, REF_STATUS, LinePricing, REF_CUSTOMER, REF_REQUEST
from copy import deepcopy
import datetime
from functools import cmp_to_key
import re

"""
Comparator to ensure Baseline revision values get sorted properly
(A, ..., Z, AA, ..., ZZ, AAA, etc.)
"""
RevisionCompare = cmp_to_key(
    lambda x, y: (
        -1 if len(x.strip('1234567890')) < len(y.strip('1234567890')) or
        list(x.strip('1234567890')) < (
                  ['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                  list(y.strip('1234567890'))) or
        (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y))
        else 0 if x == y
        else 1))


def UpRev(oRecord, sExceptionHeader=None, sExceptionRev=None,
          sCopyToRevision=None):
    """
    Function to perform revision incrementation.  When a new baseline revision
    is released, Header records in the currently active revision may need to be
    copied forward into the revision being released (i.e.: the record is
    currently active and not discontinued or replaced in the releasing revision)

    This function performs the task of copying forward any necessary Headers,
    giving the released version a completion date, and updating the baseline
    tracking of in-process and active revisions.

    This function can be provided a specific sExceptionHeader and sExceptionRev
    to cause all records to move forward EXCEPT the Header identified by the
    parameters.  This feature is currently only used during file upload.

    This function can also be run on a single Header record to copy if into a
    specific revision, as provided in sCopyToRevision.

    :param oRecord: Header or Baseline object on which to operate
    :param sExceptionHeader: string specifying the configuration_designation of
                             a Header record to exclude
    :param sExceptionRev: string specifying the baseline_version of a Header
                          record to exclude
    :param sCopyToRevision: string specifying the baseline revision into which a
                            Header record will be copied
    :return: None
    """
    if not isinstance(oRecord, (Baseline, Header)):
        raise TypeError(
            'UpRev can only be passed a Baseline or Header type object')
    # end if

    if isinstance(oRecord, Header) and not sCopyToRevision:
        raise ValueError(
            'Must provide sCopyToRevision when passing a Header to this function')
    # end if

    oNewInprocRev = None
    sNewInprocessRev = ''
    if isinstance(oRecord, Baseline):
        sCurrentActiveRev = oRecord.current_active_version
        try:
            # Get the Baseline_Revision object that corresponds to the
            # Baseline's current_active_revision value
            oCurrActiveRev = Baseline_Revision.objects.get(
                **{'baseline': oRecord, 'version': sCurrentActiveRev})

            # This function will not move forward Header records that are
            # discontinued, cancelled, or inactive
            aHeaders = oCurrActiveRev.header_set.exclude(
                configuration_status__name='Discontinued').exclude(
                configuration_status__name='Cancelled').exclude(
                configuration_status__name='Inactive')
        except Baseline_Revision.DoesNotExist:
            aHeaders = []

        sCurrentInProcRev = oRecord.current_inprocess_version
        oCurrInprocRev = Baseline_Revision.objects.get(
            **{'baseline': oRecord, 'version': sCurrentInProcRev})

        # Need to determine a new in-process revision
        # The new value will either be the next incremental step after
        # current_inprocess_version or the revision being uploaded, which is
        # provided in sExceptionRev

        # If the exception revision fits between the current active version and
        # the current inprocess version
        # *** NOTE: This should only happen during upload ***
        # In the legacy system, baselines could get odd revisions such as AA2,
        # Z4, etc.  This tool does not continue that labeling system, but allows
        # such values to exist or posterity of legacy data
        if sExceptionRev and (
                        RevisionCompare(sCurrentInProcRev) <
                        RevisionCompare(sExceptionRev) <
                RevisionCompare(IncrementRevision(sCurrentInProcRev))):
            sNewInprocessRev = sExceptionRev
        else:
            sNewInprocessRev = IncrementRevision(sCurrentInProcRev)
        (oNewInprocRev, _) = Baseline_Revision.objects.get_or_create(
            **{'baseline': oRecord, 'version': sNewInprocessRev})

        # Move in-process & in-process/pending records from current in-process
        # rev to new in-process rev
        aHeadersToMoveToInProc = oCurrInprocRev.header_set.filter(
            configuration_status__name__in=['In Process', 'In Process/Pending',
                                            'On Hold'])

        for oHeader in aHeadersToMoveToInProc:
            oHeader.baseline = oNewInprocRev
            oHeader.baseline_version = sNewInprocessRev
            oHeader.save()
        # end for
    else:
        aHeaders = [oRecord]
        sCurrentInProcRev = sCopyToRevision
        oCurrInprocRev = Baseline_Revision.objects.get(
            **{'baseline': oRecord.baseline.baseline,
               'version': sCurrentInProcRev})
    # end if

    # Copy active records from current active rev to current in-proc rev (or
    # revision specified by sCopyToRevision)
    for oHeader in aHeaders:
        # Check if the destination revision has a Header record that matches the
        # current Header
        oNextHeader = Header.objects.filter(
            configuration_designation=oHeader.configuration_designation,
            program=oHeader.program, baseline_version=sCurrentInProcRev)

        # the current header is not the exception header and does not already
        # exist in the destination revision
        if not((oHeader.configuration_designation == sExceptionHeader and
                IncrementRevision(oHeader.baseline_version) ==
                sExceptionRev) or oNextHeader):

            # Create an exact copy of the current header, place it in the
            # destination revision, and link it back to this header.
            # *** This section is very similar to the CloneHeader function in
            # approvals_actions.py, with a few differences regarding baseline
            # destinations and record links.  These differences could
            # potentially be consolidated into a single function at some
            # point.***
            oNewHeader = deepcopy(oHeader)
            oNewHeader.pk = None
            oNewHeader.baseline_version = sCurrentInProcRev
            if oNewHeader.react_request is None:
                oNewHeader.react_request = ''
            # end if
            oNewHeader.baseline = oCurrInprocRev
            oNewHeader.model_replaced_link = oHeader
            if oNewHeader.bom_request_type.name == 'New':
                oNewHeader.bom_request_type = REF_REQUEST.objects.get(
                    name='Update')
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

                oNewPrice = deepcopy(oConfigLine.linepricing) if hasattr(
                    oConfigLine, 'linepricing') else LinePricing()
                oNewPrice.pk = None
                oNewPrice.config_line = oNewLine
                oNewPrice.save()
            # end for
        # end if

        # Set current active version of records to 'Inactive' status
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
        # Give releasing revision a completion date
        oCurrInprocRev.completed_date = timezone.now()
        oCurrInprocRev.save()

        if oNewInprocRev:
            # Link new inprocess revision to releasing revision
            oNewInprocRev.previous_revision = oCurrInprocRev
            oNewInprocRev.save()

        # Make current in-proc rev into curr active rev
        oRecord.current_active_version = sCurrentInProcRev
        oRecord.current_inprocess_version = sNewInprocessRev
        oRecord.save()

        # GenerateRevisionSummary(oRecord, sCurrentActiveRev, sCurrentInProcRev)
        MassUploaderUpdate(oRecord)
    # end if
# end def


def IncrementRevision(sRevision):
    """
    Takes an alphnumeric string and increments the last (rightmost) character.
    If character incremented was 'Z', it rolls back around to 'A' and the
    character to the left is incremented.

    Purpose is to maintain a revision chain of A, ..., Z, AA, ... BZ, CA, etc.

    :param sRevision: string of revision value to increment
    :return: str
    """
    if not isinstance(sRevision, str):
        raise TypeError(
            "Function must be passed type 'str'. Unrecognized type: " +
            str(type(sRevision)))

    if not sRevision.isalpha():
        sRevision = sRevision.rstrip('1234567890')
    # end if

    sRevision = sRevision.upper()

    return GetLetterCode(char_to_num(sRevision) + 1)


def char_to_num(sString):
    """
    Converts Base 26 sString (Using A-Z) to Base 10 decimal.
    :param sString:
    :return:
    """
    # if not sString:
    #     return 0
    #
    # return char_to_num(sString[:-1])*26 + (ord(sString[-1]) - 64)
    i = 0
    for iIndex, sLetter in enumerate(sString):
        i += (ord(sLetter) - 64) * (26 ** (len(sString) - iIndex - 1))
    return i


def GetLetterCode(iColumn):
    """
    Converts iColumn to its corresponding letter(s) value.
    :param iColumn:
    :return:
    """

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
    """
    Performs the opposite task of IncrementRevision
    :param sRevision: string of revision to decrement
    :return: str
    """
    if not isinstance(sRevision, str):
        raise TypeError(
            "Function must be passed type 'str'. Unrecognized type: " +
            str(type(sRevision)))

    if not sRevision.strip():
        raise Exception('Revision cannot be decremented any further')

    if not sRevision.isalpha():
        raise ValueError('String must not contain non-alphabet characters')
    # end if

    sRevision = sRevision.upper()

    return GetLetterCode(char_to_num(sRevision) - 1)


def MassUploaderUpdate(oBaseline=None):
    """
    After a mass upload, this function will go through the database and make
    changes to the data to ensure conformity:
        - For each baseline:
            -- Each header will be checked to make sure it is in the most recent
                revision if still active
            -- Historical entries will be made in order to show progress from
               previous revisions
                I.E.: If a configuration is Active on revision AD, and another
                configuration is active on AF, and the baseline is on revision
                AF, then the AD config needs to be on AF, but we also need to
                create a copy on revision AE, so that we can maintain a
                historical track of what configs were on which revisions, etc.
            -- Historical entries will be corrected to show status as 'Inactive'
                so that only the most recent revision is active, but historical
                data still exists
            -- Revision History items will be generated/updated for each
                baseline revision from earliest to current
        - If 'oBaseline' is provided, the above will only be done for the
            Baseline provided

    :param oBaseline: Baseline object on which to perform update (optional)
    :return None
    """
    if oBaseline:
        aBaselines = [oBaseline]
    else:
        aBaselines = Baseline.objects.all()
    # end if

    for oBase in aBaselines:
        # Get list of revisions that exist
        aExistingRevs = sorted(list(set([oBaseRev.version for oBaseRev in
                                         oBase.baseline_revision_set.order_by(
                                             'version')])),
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
            oPrevBaseRev = Baseline_Revision.objects.get(baseline=oBase,
                                                         version=rev)
            for oHeader in oPrevBaseRev.header_set.all():
                key = (oHeader.configuration_designation, oHeader.program)
                if oHeader.configuration_status.name == 'Active':
                    if key in dHeadersToMoveForward:
                        dHeadersToMoveForward[key][-1][1] = rev
                        dHeadersToMoveForward[key][-1][2] = \
                            oHeader.configuration_status.name
                        dHeadersToMoveForward[key].append([rev, '', ''])
                    else:
                        dHeadersToMoveForward[key] = [[rev, '', '']]
                    # end if
                elif oHeader.configuration_status.name in (
                        'Discontinued', 'Cancelled', 'Inactive'):
                    if key in dHeadersToMoveForward:
                        if dHeadersToMoveForward[key][-1][1] == '':
                            dHeadersToMoveForward[key][-1][1] = rev
                            dHeadersToMoveForward[key][-1][2] = \
                                oHeader.configuration_status.name
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

                while iFrom < (iTo - 1):
                    oHeader = Header.objects.get(
                        configuration_designation=config_name,
                        baseline_version=aExistingRevs[iFrom], program=prog)

                    try:
                        UpRev(oHeader, sCopyToRevision=aExistingRevs[iFrom + 1])
                    except:
                        pass
                    iFrom += 1
                # end while

                if iFrom != len(aExistingRevs) - 1:
                    oHeader = Header.objects.get(
                        configuration_designation=config_name,
                        baseline_version=aExistingRevs[iFrom], program=prog)
                    oHeader.configuration_status = REF_STATUS.objects.get(
                        name='Inactive')
                    if oHeader.change_comments:
                        oHeader.change_comments += \
                            '\nBaseline revision increment'
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
            GenerateRevisionSummary(oBase, aExistingRevs[index],
                                    aExistingRevs[index + 1])
        # end for
    # end for
# end def


def GrabValue(oStartObj, sAttrChain, default=None):
    """
    Performs a safe, chained, attribute return similar to getattr().
    :param oStartObj: Base object to begin attribute chain
    :param sAttrChain: string of '.' separated attributes
    :param default: any, the value to be returned if the attribute chain is
                    invalid or results in None
    :return: Any
    """
    import functools
    try:
        value = functools.reduce(lambda x, y: getattr(x, y),
                                 sAttrChain.split('.'), oStartObj)
        if value is None:
            return default
        else:
            return value
    except AttributeError:
        return default
# end def


class RollbackError(Exception):
    """
    Custom class of exception used to detect errors in the baseline rollback
    process that are not related to Python raised errors.
    """
    pass


def TestRollbackBaseline(oBaseline):
    """
    This function checks if a baseline revision can be rolled back (reverted to
    a previous revision).  If the function returns anything other than an empty
    list, it signifies that the baseline cannot be reverted.
    :param oBaseline: Baseline object to revert
    :return: list of Header objects
    """

    # Retrieve lastest released revision
    oCurrentActive = oBaseline.latest_revision

    if oCurrentActive is None:
        raise RollbackError('No previous revision exists')

    # Determine release datetime (since Baseline_Revision completed_on field
    # is date only, it does not provide the accuracy needed for reverting, but
    # HeaderTimeTracker completed_on does.)
    # Find the latest completed_on field
    try:
        oReleaseDate = max([oTrack.completed_on for oHead in
                            oBaseline.latest_revision.header_set.all() for
                            oTrack in oHead.headertimetracker_set.all() if
                            oTrack.completed_on])
    except ValueError:
        raise RollbackError('No release date could be determined')

    # Retrieve the current in-process revision
    oCurrentInprocess = Baseline_Revision.objects.get(
        baseline=oBaseline, version=oBaseline.current_inprocess_version)

    aRemainingHeaders = []
    aDuplicates = []

    # For each header's time tracker set, find (if it exists) the tracker
    # that has a created_on value outside 1 minute of difference from the
    # determined release date. This means that the tracker (and header) was part
    # of the previously in-process revision that was released. Add the header
    # to the list of headers that will remain after rollback.
    for oHead in oCurrentActive.header_set.all():
        if any([oTrack for oTrack in oHead.headertimetracker_set.all() if
                abs(oTrack.created_on - oReleaseDate) > datetime.timedelta(
                    minutes=1)]):
            aRemainingHeaders.append(oHead)

    # For each header in the list of remaining headers, check if a header with
    # the same name and program exist in the currently in-process revision and
    # add those headers to the duplicate list
    for oHead in aRemainingHeaders:
        if oCurrentInprocess.header_set.filter(
                configuration_designation=oHead.configuration_designation,
                program=oHead.program):
            aDuplicates.append(oHead)

    return aDuplicates
# end def


def RollbackBaseline(oBaseline):
    """
    Function rolls back a baseline to the previous revision.
    All headers that were copied forward as part of an UpRev will be
    deleted, headers that were a part of the release that triggered
    the UpRev will be returned to an "In Procees/Pending" state.
    Headers that were made inactive in the previous active revision
    will returned to Active state. Any records currently in-process or
    in-process/pending will remain in-process but will be moved back to the
    previous revision

    :param oBaseline: Baseline to revert
    :return: None
    """

    # Create a sorted list of revisions for the Baseline provided
    aExistingRevs = sorted(
        list(set([oBaseRev.version for oBaseRev in
                  oBaseline.baseline_revision_set.order_by('version')])),
        key=RevisionCompare
    )

    # Determine release datetime by finding the latest completed_on field each
    # tracker for each header in the currently released baseline revision (since
    # Baseline_Revision completed_on field is date only, it does not provide the
    # accuracy needed for reverting, but HeaderTimeTracker completed_on does.)
    try:
        oReleaseDate = max([oTrack.completed_on for oHead in
                            oBaseline.latest_revision.header_set.all() for
                            oTrack in oHead.headertimetracker_set.all() if
                            oTrack.completed_on])
    except ValueError:
        raise RollbackError('No release date could be determined')

    # Retrieve the currently released and currently in-process
    # Baseline_Revision's
    oCurrentActive = oBaseline.latest_revision
    oCurrentInprocess = Baseline_Revision.objects.get(
        baseline=oBaseline, version=oBaseline.current_inprocess_version)
    oPreviousActive = None

    # Determine which revision (if any) was previous to the currently active
    # revision
    iPrevIndex = aExistingRevs.index(oBaseline.current_active_version) - 1
    if iPrevIndex >= 0:
        oPreviousActive = Baseline_Revision.objects.get(
            baseline=oBaseline, version=aExistingRevs[iPrevIndex])

    """
    Each Header in the currently active revision (being reverted) can only have
    one of two cases.  Either A)the header was copied forward from a previous
    revision during release, or B)the header was (one of) the record(s) approved
    and released that triggered the revision increase.

    If A, the header can be deleted because nothing was actually done to the
    record.

    If B, the header will be returned to "In Process/Pending" status and the
    latest tracker can have its completed_on field, and final approval fields,
    emptied.

    Which path the header takes is determined by whether ot not the latest
    tracker's created_on date is within 1 minute of the release date.  This is
    because a new tracker is created for each record copied forward from the
    previous revision at the time of release.
    """
    for oHead in oCurrentActive.header_set.all():
        if any([oTrack for oTrack in oHead.headertimetracker_set.all() if
                abs(oTrack.created_on - oReleaseDate) < datetime.timedelta(
                    minutes=1)]):
            oHead.delete()
        else:
            oHead.configuration_status = REF_STATUS.objects.get(
                name='In Process/Pending')
            oHead.save()

            oLatestTracker = oHead.headertimetracker_set.last()
            if oLatestTracker and oLatestTracker.completed_on:
                oLatestTracker.completed_on = None
                oLatestTracker.brd_approver = None
                oLatestTracker.brd_approved_on = None
                oLatestTracker.brd_comment = None
                oLatestTracker.save()
            # end if
        # end if
    # end for

    # Move all headers in the in-process record (which are still in-process or
    # in-process/pending back to the active revision being reverted
    for oHead in oCurrentInprocess.header_set.all():
        oHead.baseline = oCurrentActive
        oHead.baseline_version = oBaseline.current_active_version
        oHead.save()
    # end for

    # If there is a previously active revision available, return all inactive
    # records to active status and remove any automated change notes
    if oPreviousActive:
        for oHead in oPreviousActive.header_set.all():
            if oHead.configuration_status.name in ('Inactive', 'Obsolete'):
                oHead.configuration_status = REF_STATUS.objects.get(
                    name='Active')
                oHead.change_comments = oHead.change_comments.replace(
                    '\nBaseline revision increment', '').replace(
                    'Baseline revision increment', '')
                oHead.save()
            # end if
        # end for
    # end if

    # Remove the completed_on date from the reverted revision, and delete the
    # in-process revision, and all revision histories for the reverted revision
    # and deleted revision
    oCurrentActive.completed_date = None
    oCurrentActive.save()
    oCurrentInprocess.delete()

    RevisionHistory.objects.filter(
        baseline=oBaseline,
        revision__in=aExistingRevs[aExistingRevs.index(
            oBaseline.current_active_version):]).delete()

    # Adjust the baseline tracking values to properly reflect which revision is
    # active and which is in-process
    oBaseline.current_inprocess_version = oBaseline.current_active_version
    if oPreviousActive:
        oBaseline.current_active_version = aExistingRevs[iPrevIndex]
    else:
        oBaseline.current_active_version = ''
    # end if
    oBaseline.save()
# end def


def GenerateRevisionSummary(oBaseline, sPrevious, sCurrent):
    """
    Generates a summary of differences between two revisions of a baseline.
    Changes are from the stand-point of the revision specified by sCurrent,
    showing what changes occurred on sPrevious revision to make sCurrent
    revision.
    :param oBaseline: Baseline object
    :param sPrevious: string specifying previous revision
    :param sCurrent: string specifying current revision (
    :return: None
    """
    oDiscontinued = Q(configuration_status__name='Discontinued')
    oToDiscontinue = Q(bom_request_type__name='Discontinue')

    # Generate a list of Headers in the sCurrent revision of oBaseline that are
    # Discontinued (and were not copied forward) or are marked to be
    # discontinued. Ignore records in "On Hold" or "In Process" status. If
    # working with any other baseline other than 'No Associated Baseline',
    # ignore records that are in the DTS program
    aDiscontinuedHeaders = [oHead for oHead in
                            Baseline_Revision.objects.get(baseline=oBaseline,
                                                          version=sCurrent
                                                          ).header_set.filter(
                                oDiscontinued | oToDiscontinue).exclude(
                                program__name__in=(
                                    'DTS',) if oBaseline.title !=
                                'No Associated Baseline' else []).exclude(
                                configuration_status__name__in=('On Hold',
                                                                'In Process'))]

    # Generate a list of Headers in the sCurrent revision of oBaseline that are
    # New or Legacy (added as active). Ignore records in "On Hold" or "In
    # Process" status. If working with any other baseline other than 'No
    # Associated Baseline', ignore records that are in the DTS program
    aAddedHeaders = [oHead for oHead in
                     Baseline_Revision.objects.get(baseline=oBaseline,
                                                   version=sCurrent
                                                   ).header_set.filter(
                         bom_request_type__name__in=('New', 'Legacy')).exclude(
                         program__name__in=(
                            'DTS',) if oBaseline.title !=
                         'No Associated Baseline' else []).exclude(
                         configuration_status__name__in=('On Hold',
                                                         'In Process'))]

    # Generate a list of Headers in the sCurrent revision of oBaseline that are
    # updates. Ignore records in "On Hold" or "In Process" status. If
    # working with any other baseline other than 'No Associated Baseline',
    # ignore records that are in the DTS program
    aUpdatedHeaders = [oHead for oHead in
                       Baseline_Revision.objects.get(baseline=oBaseline,
                                                     version=sCurrent
                                                     ).header_set.filter(
                           bom_request_type__name='Update').exclude(
                           oDiscontinued).exclude(
                           program__name__in=('DTS',) if
                           oBaseline.title != 'No Associated Baseline' else []
                       ).exclude(
                           configuration_status__name__in=('On Hold',
                                                           'In Process'))]

    # For each updated Header, determine if the previous revision contains the
    # record the Header claims to update or not
    # aPrevHeaders = []
    # aPrevButNotCurrent = []
    aCurrButNotPrev = []
    for oHead in aUpdatedHeaders:
        try:
            Baseline_Revision.objects.get(baseline=oBaseline,
                                          version=sPrevious).header_set.get(
                configuration_designation=oHead.configuration_designation,
                program=oHead.program)

            # This check never fails because aDiscontinuedHeaders contains
            # headers not tuples, and aPrevHeaders never gets used
            # if not (obj.configuration_designation, obj.program) in \
            #         aDiscontinuedHeaders:
            #     aPrevHeaders.append(obj)
            # else:
            #     aPrevButNotCurrent.append(obj)
            # # end if
        except (Header.DoesNotExist, Baseline_Revision.DoesNotExist):
            aCurrButNotPrev.append(oHead)
        # end try

    sNewSummary = 'Added:\n'
    sRemovedSummary = 'Discontinued:\n'

    # Append the formatted string for each Header in aAddedHeaders
    for oHead in aAddedHeaders:
        if oHead.model_replaced:
            sNewSummary += '    {} replaces {}\n'.format(
                oHead.configuration_designation + (
                    ' ({})'.format(oHead.program.name) if oHead.program else ''
                ) + (
                    '  {}'.format(
                        oHead.configuration.get_first_line().customer_number
                    ) if not oHead.pick_list and
                    oHead.configuration.get_first_line().customer_number else ''
                ),

                oHead.model_replaced_link.configuration_designation + (
                    " ({})".format(oHead.model_replaced_link.program.name) if
                    oHead.model_replaced_link.program else ''
                ) + (
                    '  {}'.format(
                        oHead.model_replaced_link.configuration.get_first_line()
                        .customer_number
                    ) if not oHead.model_replaced_link.pick_list and
                    oHead.model_replaced_link.configuration.get_first_line()
                    .customer_number else ''
                ) if oHead.model_replaced_link else oHead.model_replaced
            )

            sRemovedSummary += '    {} is replaced by {}\n'.format(
                oHead.model_replaced_link.configuration_designation + (
                    " ({})".format(
                        oHead.model_replaced_link.program.name
                    ) if oHead.model_replaced_link.program else '') +
                (
                    '  {}'.format(
                        oHead.model_replaced_link.configuration.get_first_line()
                        .customer_number
                    ) if not oHead.model_replaced_link.pick_list and
                    oHead.model_replaced_link.configuration
                    .get_first_line().customer_number else ''
                ) if oHead.model_replaced_link else oHead.model_replaced,

                oHead.configuration_designation + (
                    ' ({})'.format(oHead.program.name) if oHead.program else ''
                ) + (
                    '  {}'.format(
                        oHead.configuration.get_first_line().customer_number
                    ) if not oHead.pick_list and oHead.configuration
                    .get_first_line().customer_number else '')
            )
        else:
            # If a previous revision exists and a matching header exists in
            # previous revision and the Header has a time tracker without a
            # completed date or disapproved date, but is not In-Process, then
            # the Header must have been carried forward from a previous
            # revision, and therefore is not ACTUALLY New / Added
            if Baseline_Revision.objects.filter(baseline=oBaseline,
                                                version=sPrevious) and \
                    Baseline_Revision.objects.get(
                        baseline=oBaseline,
                        version=sPrevious).header_set.filter(
                        configuration_designation=oHead.configuration_designation,
                        program=oHead.program
                    ) and not oHead.configuration_status.name == \
                    'In Process/Pending' and oHead.headertimetracker_set.filter(
                    completed_on=None, disapproved_on=None):
                continue

            sNewSummary += '    {} added\n'.format(
                oHead.configuration_designation + (
                    ' ({})'.format(oHead.program.name) if oHead.program else ''
                ) + (
                    '  {}'.format(
                        oHead.configuration.get_first_line().customer_number
                    ) if not oHead.pick_list and
                    oHead.configuration.get_first_line().customer_number
                    else ''
                )
            )
        # end if
    # end for

    # Add a line for each Header that is an "Update" but has not previous record
    # in the previous revision
    for oHead in aCurrButNotPrev:
        sNewSummary += '    {} added\n'.format(
            oHead.configuration_designation + (
                ' ({})'.format(oHead.program.name) if oHead.program else ''
            ) + (
                '  {}'.format(
                    oHead.configuration.get_first_line().customer_number
                ) if not oHead.pick_list and
                oHead.configuration.get_first_line().customer_number
                else ''
            )
        )
    # end for

    # Add a line for each discontinued Header. Skip headers that have been
    # replaced and that replacement is in aAddedHeaders, since we have already
    # added a description of that transaction earlier
    for oHead in aDiscontinuedHeaders:
        if (oHead.model_replaced_link and any(
                [obj in oHead.model_replaced_link.replaced_by_model.all() for
                 obj in aAddedHeaders if hasattr(oHead.model_replaced_link,
                                                 'replaced_by_model')]
        )) or any(
            [obj in oHead.replaced_by_model.all() for obj in aAddedHeaders if
             hasattr(oHead, 'replaced_by_model')]):
            continue

        sRemovedSummary += '    {} discontinued\n'.format(
            oHead.configuration_designation + (
                ' ({})'.format(oHead.program.name) if oHead.program else ''
            ) + (
                '  {}'.format(
                    oHead.configuration.get_first_line().customer_number
                ) if not oHead.pick_list and
                oHead.configuration.get_first_line().customer_number
                else ''
            )
        )
    # end for

    # This list never gets populated, so we don't need to do this
    # for oHead in aPrevButNotCurrent:
    #     sRemovedSummary += '    {} removed\n'.format(
    #         oHead.configuration_designation + (
    #             ' ({})'.format(oHead.program.name) if oHead.program else ''
    #         ) + (
    #             '  {}'.format(
    #                 oHead.configuration.get_first_line().customer_number
    #             ) if not oHead.pick_list and
    #                  oHead.configuration.get_first_line().customer_number
    #             else ''
    #         )
    #     )
    # # end for

    # Calculate and add changes for updated headers
    sUpdateSummary = "Updated:\n"
    for oHead in aUpdatedHeaders:
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
            sUpdateSummary += '    {}:\n'.format(
                oHead.configuration_designation + (
                    ' ({})'.format(oHead.program) if oHead.program else ''
                ) + (
                    '  {}'.format(
                        oHead.configuration.get_first_line().customer_number
                    ) if not oHead.pick_list and
                    oHead.configuration.get_first_line().customer_number
                    else ''
                )
            )

            for sLine in sTemp.split('\n'):
                sUpdateSummary += (' ' * 8) + sLine + '\n'
        # end if
    # end for

    sHistory = ''

    if sNewSummary != 'Added:\n':
        sHistory += sNewSummary
    if sRemovedSummary != 'Discontinued:\n':
        sHistory += sRemovedSummary
    if sUpdateSummary != "Updated:\n":
        sHistory += sUpdateSummary

    # Save revision history
    (oNew, _) = RevisionHistory.objects.get_or_create(baseline=oBaseline,
                                                      revision=sCurrent)
    oNew.history = sHistory
    oNew.save()
# end def



def HeaderComparison(oHead, oPrev):
    """
    Performs a line-by-line comparison of two Headers (oHead, oPrev) and
    determines how oHead differs from oPrev
    :param oHead: Header object. Differences are focused on this record
    :param oPrev: Header object. Starting point to determine changes
    :return: string listing all changes found
    """
    sTemp = ''
    aPotentialMatches = []
    """
    Creating a dictionary for previous and current revision,
        key: (Part #, Line #)
        value: [Qty,
                Price,
                Product Description,
                Comments,
                Additional Reference,
                (Grandparent Part #, Parent Part #),
                Matching line key].
    This will be used to find a match between revisions, and track when a line
    has been moved rather than removed or replaced.
    """
    dPrevious = {}
    dCurrent = {}
    oATT = REF_CUSTOMER.objects.get(name='AT&T')
    # D-06102: Unit Price column incorrectly highlighted in Baseline download: Added below line for MTW cu only
    oMTW = REF_CUSTOMER.objects.get(name='MTW')
    oFirstLine = oHead.configuration.get_first_line()

    # Build dictionary from oHead ConfigLine set
    for oConfigLine in oHead.configuration.configline_set.all():
        dCurrent[
            (oConfigLine.part.base.product_number, oConfigLine.line_number)
        ] = [
            oConfigLine.order_qty,
            GrabValue(
                oConfigLine, 'linepricing.override_price'
            ) or GrabValue(
                oConfigLine, 'linepricing.pricing_object.unit_price'
            ) or None,
            (
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.find('.')
                                ]
                ).part.base.product_number if oConfigLine.is_grandchild else
                None,
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.rfind('.')
                                ]
                ).part.base.product_number if oConfigLine.is_child else None
            ),
            None,
            # S-07842   Revision change adjustment( Added for description, add_ref, comments)
            oConfigLine.part.product_description or None,
            oConfigLine.comments or None,
            oConfigLine.additional_ref or None,
        # D-06102: Unit Price column incorrectly highlighted in Baseline download: Added belwo two lines to hold the value of unit price & net Price
            GrabValue(
                oConfigLine, 'linepricing.pricing_object.unit_price'),
            GrabValue(
                oConfigLine, 'linepricing.override_price'
            ),
        ]

    # end for

    # Build dictionary from oPrev ConfigLine set
    for oConfigLine in oPrev.configuration.configline_set.all():
        dPrevious[
            (oConfigLine.part.base.product_number, oConfigLine.line_number)
        ] = [
            oConfigLine.order_qty,
            GrabValue(
                oConfigLine, 'linepricing.override_price'
            ) or GrabValue(
                oConfigLine,
                'linepricing.pricing_object.unit_price'
            ) or None,
            (
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.find('.')
                                ]
                ).part.base.product_number if
                oConfigLine.is_grandchild and
                oHead.configuration.configline_set.filter(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.find('.')]) else None,
                oHead.configuration.configline_set.get(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.rfind('.')
                                ]
                ).part.base.product_number if
                oConfigLine.is_child and
                oHead.configuration.configline_set.filter(
                    line_number=oConfigLine.line_number[
                                :oConfigLine.line_number.rfind('.')]) else None
            ),
            None,
            # S-07842   Revision change adjustment( Added for description, add_ref, comments)
            oConfigLine.part.product_description or None,
            oConfigLine.comments or None,
            oConfigLine.additional_ref or None,
        # D-06102: Unit Price column incorrectly highlighted in Baseline download: Added belwo two lines to hold the value of unit price & net Price
            GrabValue(
                oConfigLine, 'linepricing.pricing_object.unit_price'),
            GrabValue(
                oConfigLine, 'linepricing.override_price'
            ),
        ]

    # For each key in dPrevious, check if the key is in dCurrent.
    for (sPart, sLine) in dPrevious.keys():
        if (sPart, sLine) in dCurrent.keys():
            # if it is, assign the key as a match key value in both dictionary
            # entries. This allows us to track which entries in each dictionary
            # have been matched.
            dCurrent[(sPart, sLine)][3] = dPrevious[(sPart, sLine)][3] = (sPart,
                                                                          sLine)

            # Check if quantity or price or description or comments or additional_ref changed from oPrev entry to oHead entry
# Added for S-07842   Revision change adjustment( changed for description, add_ref, comments)(spart,sline[4],spart,sline[5],spart,sline[6])
# D-06102: Unit Price column incorrectly highlighted in Baseline download: Added (sPart, sLine)][7], (sPart, sLine)][8] for unit price & net Price of MTW
            if dCurrent[(sPart, sLine)][0] != dPrevious[(sPart, sLine)][0] or \
                dCurrent[(sPart, sLine)][1] != dPrevious[(sPart, sLine)][1] or \
                dCurrent[(sPart, sLine)][4] != dPrevious[(sPart, sLine)][4] or \
                dCurrent[(sPart, sLine)][5] != dPrevious[(sPart, sLine)][5] or \
                dCurrent[(sPart, sLine)][6] != dPrevious[(sPart, sLine)][6] or \
                dCurrent[(sPart, sLine)][7] != dPrevious[(sPart, sLine)][7] or \
                dCurrent[(sPart, sLine)][8] != dPrevious[(sPart, sLine)][8]:

                if dCurrent[(sPart, sLine)][0] != dPrevious[(sPart, sLine)][0]:
                    sTemp += '{} - {} quantity changed from {} to {}\n'.format(
                        sLine, sPart,  dPrevious[(sPart, sLine)][0],
                        dCurrent[(sPart, sLine)][0]
                    )

                # The pricing change is only calculated in the following cases:
                # 1. If record is for AT&T & is not a pick list, compare line 10
                # (configuration unit price) only.
                # 2. If record is for AT&T & is a pick list
                # 3. If record is not for AT&T
                if oHead.customer_unit != oMTW and dCurrent[(sPart, sLine)][1] != dPrevious[(sPart, sLine)][1]:
                    if oHead.customer_unit == oATT and not oHead.pick_list and \
                            ((sLine != '10' and not oHead.line_100) or (sLine != '100' and oHead.line_100)):

                        continue
                    sTemp += ('{} - {} line price changed\n'  # S-05747: Remove price from Comments upon baseline file download in revision tab removed,deleted from {} to {} and commented below lines
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][1],
                        dCurrent[(sPart, sLine)][1])
                if oHead.customer_unit == oMTW and (((sLine != '100' and oHead.line_100)) or (sLine != '10' and not oHead.line_100)) \
                        and not oHead.pick_list and dCurrent[(sPart, sLine)][1] != dPrevious[(sPart, sLine)][1]:
                    sTemp += ('{} - {} line price changed\n'  # S-05747: Remove price from Comments upon baseline file download in revision tab removed,deleted from {} to {} and commented below lines
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][1],
                        dCurrent[(sPart, sLine)][1])
                if oHead.customer_unit == oMTW  \
                        and oHead.pick_list and dCurrent[(sPart, sLine)][1] != dPrevious[(sPart, sLine)][1]:
                    sTemp += ('{} - {} line price changed\n'  # S-05747: Remove price from Comments upon baseline file download in revision tab removed,deleted from {} to {} and commented below lines
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][1],
                        dCurrent[(sPart, sLine)][1])
# Added for S-07842   Revision change adjustment( changed for description, add_ref, comments)(spart,sline[4],spart,sline[5],spart,sline[6])
                if dCurrent[(sPart, sLine)][4] != dPrevious[(sPart, sLine)][4]:
                    sTemp += ('{} - {} description changed\n'
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][4],
                        dCurrent[(sPart, sLine)][4])

                if dCurrent[(sPart, sLine)][5] != dPrevious[(sPart, sLine)][5]:
                    sTemp += ('{} - {} comments changed\n'
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][5],
                        dCurrent[(sPart, sLine)][5])

                if dCurrent[(sPart, sLine)][6] != dPrevious[(sPart, sLine)][6]:
                    sTemp += ('{} - {} Additional Reference changed\n'
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][6],
                        dCurrent[(sPart, sLine)][6])
            # D-06102: Unit Price column incorrectly highlighted in Baseline download: Added below block to determine the changes
            # on net price for line 10 and 100 for MTW customer.
                if oHead.customer_unit == oMTW and (((sLine == '100' and oHead.line_100)) or (sLine == '10' and not oHead.line_100)) and not oHead.pick_list and\
                    dCurrent[(sPart, sLine)][8] != dPrevious[(sPart, sLine)][8]:
                    sTemp += ('{} - {} net price changed\n'
                              ).format(
                        sLine, sPart, dPrevious[(sPart, sLine)][8],
                        dCurrent[(sPart, sLine)][8])


        else:
            # if the key is not in dCurrent, we need to find potential matches
            # to the Part number stored as part of the key.

            # If any key in dCurrent has the Part number of the dPrevious key,
            # the dPrevious and dCurrent entry have the same part ancestry (same
            # parent and grandparent part), and the dCurrent entry has not been
            # matched, we will consider this a match that has moved line numbers
            if any(sPart == key[0] and dPrevious[
                (sPart, sLine)][2] == dCurrent[key][2] and not dCurrent[key][3]
                   for key in dCurrent.keys()):

                # Find the first key in dCurrent that met the above condition,
                # and assign it as a match to the current dPrevious key.  If the
                # key was in the list of potential matches, remove it
                for key in dCurrent.keys():
                    if key[0] == sPart and dPrevious[(sPart, sLine)][2] == \
                            dCurrent[key][2] and not dCurrent[key][3]:
                        dPrevious[(sPart, sLine)][3] = key
                        dCurrent[key][3] = (sPart, sLine)
                        if key in [curr for (_, curr, _) in aPotentialMatches]:
                            aPotentialMatches[
                                list(
                                    [curr for (_, curr, _) in aPotentialMatches]
                                ).index(key)][2] = False
                        break

                # Check the match for changes to quantity and price
                # D-06102: Unit Price column incorrectly highlighted in Baseline download: Added (sPart, sLine)][7], (sPart, sLine)][8] for unit price & net Price of MTW
                if dCurrent[dPrevious[(sPart, sLine)][3]][0] != \
                        dPrevious[(sPart, sLine)][0] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][1] != \
                        dPrevious[(sPart, sLine)][1] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][4] != \
                        dPrevious[(sPart, sLine)][4] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][5] != \
                        dPrevious[(sPart, sLine)][5] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][6] != \
                        dPrevious[(sPart, sLine)][6] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][7] != \
                        dPrevious[(sPart, sLine)][7] or \
                        dCurrent[dPrevious[(sPart, sLine)][3]][8] != \
                        dPrevious[(sPart, sLine)][8]:

                    if dCurrent[dPrevious[(sPart, sLine)][3]][0] != \
                            dPrevious[(sPart, sLine)][0]:
    # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][1] to dPrevious[(sPart, sLine)][1]
    #  It was getting stuck at this point while releasing baselines
                         sTemp += ('{} - {} quantity changed from {} to {}\n'
                                  ).format(
                            dPrevious[(sPart, sLine)][1],
                            sPart, dPrevious[(sPart, sLine)][0],
                            dCurrent[dPrevious[(sPart, sLine)][3]][0]
                            )

                    if oHead.customer_unit != oMTW and dCurrent[dPrevious[(sPart, sLine)][3]][1] != \
                            dPrevious[(sPart, sLine)][1]:
                        if oHead.customer_unit == oATT and not oHead.pick_list \
                                and ((sLine != '10' and not oHead.line_100) or (sLine != '100' and oHead.line_100)):
                            continue
    # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][1] to dPrevious[(sPart, sLine)][1]
    #  It was getting stuck at this point while releasing baselines due to formatting issue with data
                        sTemp += ('{} - {} line price changed \n' # S-05747: Remove price from Comments upon baseline file download in revision tab removed,deleted from {} to {}
                                  ).format(
                            dPrevious[(sPart, sLine)][1], sPart,
                            dPrevious[(sPart, sLine)][1],
                            dCurrent[dPrevious[(sPart, sLine)][3]][1]
                        )

                    if dCurrent[dPrevious[(sPart, sLine)][3]][4] != \
                            dPrevious[(sPart, sLine)][4]:
    # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][4] to dPrevious[(sPart, sLine)][4]
    #  It was getting stuck at this point while releasing baselines due to formatting issue with data
                        sTemp += ('{} - {} description changed \n'
                                  )\
                            .format(
                            dPrevious[(sPart, sLine)][4],
                            sPart, dPrevious[(sPart, sLine)][4],
                            dCurrent[dPrevious[(sPart, sLine)][3]][4]
                        )

                    if dCurrent[dPrevious[(sPart, sLine)][3]][5] != \
                            dPrevious[(sPart, sLine)][5]:
    # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][5] to dPrevious[(sPart, sLine)][5]
    #  It was getting stuck at this point while releasing baselines due to formatting issue with data
                        sTemp += ('{} - {} comments changed\n'
                                  ).format(
                            dPrevious[(sPart, sLine)][5],
                            sPart, dPrevious[(sPart, sLine)][5],
                            dCurrent[dPrevious[(sPart, sLine)][3]][5]
                        )

                    if dCurrent[dPrevious[(sPart, sLine)][3]][6] != \
                            dPrevious[(sPart, sLine)][6]:
    # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][6] to dPrevious[(sPart, sLine)][6]
    #  It was getting stuck at this point while releasing baselines due to formatting issue with data
                        sTemp += ('{} - {} Additional Reference changed \n'
                                  ).format(
                            dPrevious[(sPart, sLine)][6],
                            sPart, dPrevious[(sPart, sLine)][6],
                            dCurrent[dPrevious[(sPart, sLine)][3]][6]
                        )
                # D-06102: Unit Price column incorrectly highlighted in Baseline download: commented belwo two blocks to determine the changes
                        # on unit price and net price individually.

    #                 if oHead.customer_unit == oMTW and dCurrent[dPrevious[(sPart, sLine)][3]][7] != \
    #                         dPrevious[(sPart, sLine)][7] and (sLine != '10' or (sLine != '100' and not oHead.line_100)):
    # # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][7] to dPrevious[(sPart, sLine)][7]
    # #  It was getting stuck at this point while releasing baselines due to formatting issue with data
    #                     sTemp += ('{} - {} line price changed\n'
    #                               ).format(
    #                         dPrevious[(sPart, sLine)][7],
    #                         sPart, dPrevious[(sPart, sLine)][7],
    #                         dCurrent[dPrevious[(sPart, sLine)][3]][7]
    #                     )
    #                 if oHead.customer_unit == oMTW and dCurrent[dPrevious[(sPart, sLine)][3]][8] != \
    #                         dPrevious[(sPart, sLine)][8] and (sLine == '10' or (sLine == '100' and not oHead.line_100)):
    # # D-06135: Error during bulk approval :- Changed the 1st parameter in format function from dPrevious[(sPart, sLine)][3][8] to dPrevious[(sPart, sLine)][8]
    # #  It was getting stuck at this point while releasing baselines due to formatting issue with data
    #                     sTemp += ('{} - {} net price changed\n'
    #                               ).format(
    #                         dPrevious[(sPart, sLine)][8],
    #                         sPart, dPrevious[(sPart, sLine)][8],
    #                         dCurrent[dPrevious[(sPart, sLine)][3]][8]
    #                     )

            else:
                """
                If part is not in new version, but line number still is, the
                part may have been replaced. However, the new version's matching
                line number may be a part in the previous version that has not
                been reached in the key list, so we will add the potential match
                to a list of possible matches.  After the the whole dictionary
                has been checked, entries without matches will be checked
                against the list of potential matches.
                """
                if any(sLine == sLnum for (_, sLnum) in dCurrent.keys()):
                    for key in dCurrent.keys():
                        if key[1] == sLine:
                            aPotentialMatches.append([(sPart, sLine), key,
                                                      True])

    # Now do a check of the potential matches list to make sure none were missed

    # First double check that any key in dCurrent that has been matched is
    # removed from the potential match list
    for key in dCurrent.keys():
        if key in [curr for (_, curr, _) in aPotentialMatches] and \
                dCurrent[key][3]:
            aPotentialMatches[list(
                [curr for (_, curr, _) in aPotentialMatches]
            ).index(key)][2] = False

    # Check all non-matched keys in dPrevious against the potential match list
    for key in dPrevious.keys():
        if not dPrevious[key][3]:
            for aEntry in aPotentialMatches:
                # The dPrevious key and potential match entry share part number
                # and the entry is still available, we will consider it a match
                if key == aEntry[0] and aEntry[2]:
                    aEntry[2] = False
                    dPrevious[key][3] = aEntry[1]
                    dCurrent[aEntry[1]][3] = key
                    sTemp += '{} - {} replaced by {}\n'.format(
                        key[1], key[0], dPrevious[key][3][0]
                    )
                    break

    # At this point, any keys in dPrevious that have not been matched are
    # considered to have been removed
    for key in dPrevious.keys():
        if not dPrevious[key][3]:
            sTemp += '{} - {} removed{}\n'.format(
                key[1], key[0],
                ' (line number remained)' if key in [prev for (prev, _, _) in
                                                     aPotentialMatches] else '')

    # At this point any unmatched keys in dCurrent are considered to be new
    # additions
    for key in dCurrent.keys():
        if not dCurrent[key][3]:
            sTemp += '{} - {} added\n'.format(key[1], key[0])

    # Sort the changes by line number, and return the string
    aLines = sTemp.split('\n')[:-1]
    # D-06135: Error during bulk approval :- Commented out the below line as it was getting stuck at this line while releasing baseline
    #  Have done thorough testing and found no change in behaviour after commenting out the below line
    # aLines.sort(key=lambda x: [int(y) for y in x[:x.find(' -')].split('.')])
    return '\n'.join(aLines)
# end def


def TitleShorten(sTitle):
    """
    Shortens a string by replacing certain words in the string
    :param sTitle: string to be shortened
    :return: str
    """
    sTitle = re.sub('Optional', 'Opt', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('Hardware', 'HW', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('Pick List', 'PL', sTitle, flags=re.IGNORECASE)
    sTitle = re.sub('_+CLONE(\d*)_+', '_CLONE\1_', sTitle, flags=re.IGNORECASE)
    return sTitle


def StrToBool(sValue, bDefault=None):
    """
    Convert a string to a bool. If the string is empty and a default is
    provided, it is returned; otherwise an exception is raised. If the string is
    not one that can be clearly interpreted as a Boolean value, raises an
    exception.
    :param sValue:
    :param bDefault:
    :return: Boolean
    """

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
        # end if
        return bDefault
    else:
        TypeError("Unrecognized Boolean string: " + sValue)
    # end if
# end def


def DetectBrowser(oRequest):
    """
    Inspects the HTTP request user agent data to determine if the request came
    from Chrome, Firefox, or Internet Explorer. Returns the determined browser

    TODO: This should be updated to handle other browsers, such as Opera or
    Safari, but those browsers were not available to us at development

    :param oRequest: Django HTTP request object
    :return: str
    """
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

