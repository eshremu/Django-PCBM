__author__ = 'epastag'
from django.utils import timezone
from .models import Header, Baseline, RevisionHistory, Baseline_Revision
from copy import deepcopy
from functools import cmp_to_key

stringisless = lambda x,y:bool(len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                 or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))) \
                              or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y))

def UpRev(oRecord, sExceptionHeader=None, sExceptionRev=None, sCopyToRevision=None):
    if not isinstance(oRecord,(Baseline, Header)):
        raise TypeError('UpRev can only be passed a Baseline or Header type object')
    # end if

    if isinstance(oRecord,Header) and not sCopyToRevision:
        raise ValueError('Must provide sCopyToRevision when passing a Header to this function')
    # end if

    if isinstance(oRecord, Baseline):
        sCurrentActiveRev = oRecord.current_active_version
        try:
            oCurrActiveRev = Baseline_Revision.objects.get(**{'baseline':oRecord, 'version': sCurrentActiveRev})
            aHeaders = oCurrActiveRev.header_set.exclude(configuration_status='Discontinued').exclude(configuration_status='Cancelled').exclude(configuration_status='Obsolete')
        except Baseline_Revision.DoesNotExist:
            aHeaders = []

        sCurrentInProcRev = oRecord.current_inprocess_version
        oCurrInprocRev = Baseline_Revision.objects.get(**{'baseline':oRecord, 'version': sCurrentInProcRev})

        # Need to create a new in-process revision : new in-p = increm(curr in-p) or revision being uploaded
        if sExceptionRev and stringisless(sCurrentInProcRev,sExceptionRev) and stringisless(sExceptionRev,IncrementRevision(sCurrentInProcRev)):
            sNewInprocessRev = sExceptionRev
        else:
            sNewInprocessRev = IncrementRevision(sCurrentInProcRev)
        (oNewInprocRev, _) = Baseline_Revision.objects.get_or_create(**{'baseline':oRecord, 'version': sNewInprocessRev})

        # Move in-process & in-process/pending records from current in-process rev to new in-process rev
        aHeadersToMoveToInProc = oCurrInprocRev.header_set.filter(configuration_status__in=['In Process', 'In Process/Pending'])

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

                oNewPrice = deepcopy(oConfigLine.linepricing)
                oNewPrice.pk = None
                oNewPrice.config_line = oNewLine
                oNewPrice.save()
            # end for
        # end if

        # 'Obsolete' current active version of records
        oHeader.configuration_status = 'Obsolete'
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

        oRecord.current_active_version = sCurrentInProcRev
        oRecord.current_inprocess_version = sNewInprocessRev
        oRecord.save()

        # GenerateRevisionSummary(oRecord, sCurrentActiveRev, sCurrentInProcRev)
        MassUploaderUpdate(oRecord)
    # end if
# end def

def IncrementRevision(sRevision):
    assert isinstance(sRevision, str)
    if not sRevision.isalpha():
        sRevision = sRevision.rstrip('1234567890')
    # end if

    bCarry = False
    aCurrent = list(sRevision)
    iIndex = -1

    while True:
        bCarry = aCurrent[iIndex] == 'Z'
        aCurrent[iIndex] = chr((ord(aCurrent[iIndex]) - 63) % 27 + (64 if aCurrent[iIndex] != 'Z' else 65))
        iIndex -= 1
        if not bCarry or iIndex < -(len(aCurrent)):
            break
    # end while

    if bCarry:
        return 'A' + ''.join(aCurrent)
    else:
        return ''.join(aCurrent)
# end def

def MassUploaderUpdate(oBaseline=None):
    """
    After a mass upload, this function will go through the database and make changes to the data to ensure conformity:
        - For each baseline:
            -- Each header will be checked to make sure it is in the most recent revision if still active
            -- Historical entries will be made in order to show progress from previous revisions
                I.E.: If a configuration is Active on revision AD, and another configuration is active on AF, and the
                baseline is on revision AF, then the AD config needs to be on AF, but we also need to create a copy on
                revision AE, so that we can maintain a historical track of what configs were on which revisions, etc.
            -- Historical entries will be corrected to show status as 'Obsolete' so that only the most recent revision
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
                               key=cmp_to_key(lambda x,y:(-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                  list(y.strip('1234567890')))
                                                                or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1)))

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
                if oHeader.configuration_status == 'Active':
                    if key in dHeadersToMoveForward:
                        dHeadersToMoveForward[key][-1][1] = rev
                        dHeadersToMoveForward[key][-1][2] = oHeader.configuration_status
                        dHeadersToMoveForward[key].append([rev,'',''])
                    else:
                        dHeadersToMoveForward[key] = [[rev, '','']]
                    # end if
                elif oHeader.configuration_status in ('Discontinued', 'Cancelled', 'Obsolete'):
                    if key in dHeadersToMoveForward:
                        if dHeadersToMoveForward[key][-1][1] == '':
                            dHeadersToMoveForward[key][-1][1] = rev
                            dHeadersToMoveForward[key][-1][2] = oHeader.configuration_status
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
                    oHeader.configuration_status = 'Obsolete'
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

def GenerateRevisionSummary(oBaseline, sPrevious, sCurrent):
    """
    Compares two revisions of a baseline and generates a summary of configurations dropped and added.  Also generates
    a summary of changes made on configurations found in both revisions.
    """

    if sPrevious:
        oPrevBaseline = Baseline_Revision.objects.get(**{'baseline': oBaseline, 'version': sPrevious})
        aPrevHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oPrevBaseline.header_set.all()]
    else:
        aPrevHeaders = []
    # end if

    oCurrBaseline = Baseline_Revision.objects.get(**{'baseline': oBaseline, 'version': sCurrent})
    aCurrHeaders = [(oHead.configuration_designation, oHead.program) for oHead in oCurrBaseline.header_set.all()]

    aNew = set(aCurrHeaders).difference(set(aPrevHeaders))
    aRemoved = set(aPrevHeaders).difference(set(aCurrHeaders))
    sNewSummary = 'Added:\n'
    for (sNew,_) in aNew:
        sNewSummary += '    - {}\n'.format(sNew)
    # end for

    sRemoveSummary = 'Removed:\n'
    for (sRemove,_) in aRemoved:
        sRemoveSummary += '    - {}\n'.format(sRemove)
    # end for

    dUpdates = {}
    for (sHeader, oProg) in set(aCurrHeaders).intersection(set(aPrevHeaders)):
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

            if oCurrLine.plant != oPrevLine.plant:
                dUpdates[sHeader].append('{0} - Changed plant from {1} to {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.plant,
                                                                              oCurrLine.plant))
            # end if

            if oCurrLine.sloc != oPrevLine.sloc:
                dUpdates[sHeader].append('{0} - Changed SLOC from {1} to {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.sloc,
                                                                              oCurrLine.sloc))
            # end if

            if oCurrLine.item_category != oPrevLine.item_category:
                dUpdates[sHeader].append('{0} - Changed Item Cat. from {1} to {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.item_category,
                                                                              oCurrLine.item_category))
            # end if

            if oCurrLine.pcode != oPrevLine.pcode:
                dUpdates[sHeader].append('{0} - Changed P-Code from {1} to {2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.pcode,
                                                                              oCurrLine.pcode))
            # end if

            if getattr(oCurrLine,'linepricing', None) and getattr(oPrevLine,'linepricing', None)\
                    and oCurrLine.linepricing.unit_price != oPrevLine.linepricing.unit_price:
                dUpdates[sHeader].append('{0} - Changed Unit Price from ${1} to ${2}'.format(oCurrLine.line_number,
                                                                              oPrevLine.linepricing.unit_price,
                                                                              oCurrLine.linepricing.unit_price))
            # end if
        # end for

        if not dUpdates[sHeader]:
            del dUpdates[sHeader]
        # end if
    # end for

    sHistory = ''
    if len(sNewSummary) > 7:
        sHistory += sNewSummary
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
