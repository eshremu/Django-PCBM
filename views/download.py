from django.http import HttpResponse, Http404
from django.core.urlresolvers import reverse

from BoMConfig.models import Header, ConfigLine, Baseline, Baseline_Revision
from BoMConfig.templatetags.customtemplatetags import searchscramble
from BoMConfig.utils import GenerateRevisionSummary, GrabValue
from BoMConfig.views.configuration import BuildDataArray

from itertools import chain
import openpyxl
from openpyxl import utils
from openpyxl.styles import Font, Color, colors, Border, Alignment, Side, borders, GradientFill
import os
from functools import cmp_to_key


def Download(oRequest):
    download = oRequest.GET.get('download', None)
    if download:
        oHeader = download[5:-10]
    else:
        oHeader = oRequest.session.get('existing', None)
    # end if


    if oHeader:
        oHeader = Header.objects.get(pk=oHeader)
        sFileName = oHeader.configuration_designation + ".xlsx"

        oFile = openpyxl.load_workbook(
            str(os.path.join(os.getenv('PYTHONPATH', os.getcwd()).split(';')[0], 'BoMConfig/static/BoMConfig/PSM BoM Upload Template PA5 FORMULAS.xlsx'))
        )

        # Populate Header data
        oFile.active = oFile.sheetnames.index('1) BOM Config Header')
        oFile.active['B1'] = oHeader.person_responsible
        oFile.active['B2'] = oHeader.react_request
        oFile.active['B3'] = oHeader.bom_request_type.name
        oFile.active['B4'] = oHeader.customer_unit.name
        oFile.active['B5'] = oHeader.customer_name
        oFile.active['B6'] = oHeader.sales_office
        oFile.active['B7'] = oHeader.sales_group
        oFile.active['B8'] = oHeader.sold_to_party
        oFile.active['B9'] = oHeader.ship_to_party
        oFile.active['B10'] = oHeader.bill_to_party
        oFile.active['B11'] = oHeader.ericsson_contract
        oFile.active['B12'] = oHeader.payment_terms

        oFile.active['B14'] = oHeader.projected_cutover
        oFile.active['B15'] = oHeader.program.name if oHeader.program else None
        oFile.active['B16'] = oHeader.configuration_designation
        oFile.active['B17'] = oHeader.customer_designation
        oFile.active['B18'] = oHeader.technology.name if oHeader.technology else None
        oFile.active['B19'] = oHeader.product_area1.name if oHeader.product_area1 else None
        oFile.active['B20'] = oHeader.product_area2.name if oHeader.product_area2 else None
        oFile.active['B21'] = oHeader.radio_frequency.name if oHeader.radio_frequency else None
        oFile.active['B22'] = oHeader.radio_band.name if oHeader.radio_band else None
        oFile.active['B23'] = oHeader.optional_free_text1
        oFile.active['B24'] = oHeader.optional_free_text2
        oFile.active['B25'] = oHeader.optional_free_text3
        oFile.active['B26'] = oHeader.inquiry_site_template
        oFile.active['B27'] = oHeader.readiness_complete / 100 if oHeader.readiness_complete else oHeader.readiness_complete
        oFile.active['B28'] = ('X' if oHeader.complete_delivery else None)
        oFile.active['B29'] = ('X' if oHeader.no_zip_routing else None)
        oFile.active['B30'] = oHeader.valid_to_date
        oFile.active['B31'] = oHeader.valid_from_date
        oFile.active['B32'] = oHeader.shipping_condition

        oFile.active['B34'] = oHeader.baseline_impacted
        oFile.active['B35'] = oHeader.model
        oFile.active['B36'] = oHeader.model_description
        oFile.active['B37'] = oHeader.model_replaced
        oFile.active['B38'] = oHeader.initial_revision

        oFile.active['B40'] = oHeader.configuration_status.name

        oFile.active['B42'] = oHeader.workgroup
        oFile.active['B43'] = oHeader.name

        oFile.active['B45'] = ('X' if oHeader.pick_list else None)
        oFile.active.sheet_view.showGridLines = False

        # Populate Config Entry tab
        oFile.active = oFile.sheetnames.index('2) BOM Config Entry')
        oFile.active.sheet_view.showGridLines = False
        # img = Image(static('config_boxes.png'))
        # img.anchor(oFile.active['A1'])
        if oHeader.configuration:
            oFile.active['D5'] = ('X' if oHeader.configuration.reassign else None)
            oFile.active['D8'] = ('X' if oHeader.configuration.PSM_on_hold else None)
            oFile.active['N4'] = ('X' if oHeader.configuration.internal_external_linkage else None)
            oFile.active['Q4'] = ('$ ' + str(oHeader.configuration.zpru_total) if oHeader.configuration.zpru_total else '$ xx,xxx.xx')

            iRow = 13
            aConfigLines = ConfigLine.objects.filter(config=oHeader.configuration).order_by('line_number')
            aConfigLines = sorted(aConfigLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
            for oConfigLine in aConfigLines:
                oFile.active['A' + str(iRow)] = oConfigLine.line_number
                oFile.active['B' + str(iRow)] = ('..' if oConfigLine.is_grandchild else '.' if oConfigLine.is_child else '') + oConfigLine.part.base.product_number
                oFile.active['C' + str(iRow)] = oConfigLine.part.product_description
                oFile.active['D' + str(iRow)] = oConfigLine.order_qty
                oFile.active['E' + str(iRow)] = oConfigLine.part.base.unit_of_measure
                oFile.active['F' + str(iRow)] = oConfigLine.plant
                oFile.active['G' + str(iRow)] = oConfigLine.sloc
                oFile.active['H' + str(iRow)] = oConfigLine.item_category
                oFile.active['I' + str(iRow)] = oConfigLine.pcode
                oFile.active['J' + str(iRow)] = oConfigLine.commodity_type
                oFile.active['K' + str(iRow)] = oConfigLine.package_type
                oFile.active['L' + str(iRow)] = oConfigLine.spud
                oFile.active['M' + str(iRow)] = oConfigLine.REcode
                oFile.active['N' + str(iRow)] = oConfigLine.mu_flag
                oFile.active['O' + str(iRow)] = oConfigLine.x_plant
                oFile.active['P' + str(iRow)] = oConfigLine.internal_notes
                # oFile.active['Q' + str(iRow)] = oConfigLine.linepricing.unit_price
                oFile.active['Q' + str(iRow)] = str(oConfigLine.linepricing.override_price) if str(oConfigLine.line_number) == '10' and\
                    hasattr(oConfigLine,'linepricing') and oConfigLine.linepricing.override_price else oConfigLine.linepricing.pricing_object.unit_price\
                    if GrabValue(oConfigLine,'linepricing.pricing_object') else ''
                oFile.active['R' + str(iRow)] = oConfigLine.higher_level_item
                oFile.active['S' + str(iRow)] = oConfigLine.material_group_5
                oFile.active['T' + str(iRow)] = oConfigLine.purchase_order_item_num
                oFile.active['U' + str(iRow)] = oConfigLine.condition_type
                oFile.active['V' + str(iRow)] = oConfigLine.amount
                oFile.active['W' + str(iRow)] = oConfigLine.traceability_req
                oFile.active['X' + str(iRow)] = oConfigLine.customer_asset
                oFile.active['Y' + str(iRow)] = oConfigLine.customer_asset_tagging
                oFile.active['Z' + str(iRow)] = oConfigLine.customer_number
                oFile.active['AA' + str(iRow)] = oConfigLine.sec_customer_number
                oFile.active['AB' + str(iRow)] = oConfigLine.vendor_article_number
                oFile.active['AC' + str(iRow)] = oConfigLine.comments
                oFile.active['AD' + str(iRow)] = oConfigLine.additional_ref
                iRow += 1
            # end for
        # end if

        # Populate Config ToC tab
        oFile.active = oFile.sheetnames.index('2a) BoM Config ToC')
        oFile.active.sheet_view.showGridLines = False
        if oHeader.configuration:
            oFile.active['D5'] = ('X' if oHeader.configuration.reassign else None)
            oFile.active['D8'] = ('X' if oHeader.configuration.PSM_on_hold else None)
            oFile.active['A13'] = oHeader.configuration_designation
            oFile.active['B13'] = oHeader.customer_designation or None
            oFile.active['C13'] = oHeader.technology.name if oHeader.technology else None
            oFile.active['D13'] = oHeader.product_area1.name if oHeader.product_area1 else None
            oFile.active['E13'] = oHeader.product_area2.name if oHeader.product_area2 else None
            oFile.active['F13'] = oHeader.model or None
            oFile.active['G13'] = oHeader.model_description or None
            oFile.active['H13'] = oHeader.model_replaced or None
            oFile.active['J13'] = oHeader.bom_request_type.name
            oFile.active['K13'] = oHeader.configuration_status.name or None
            oFile.active['L13'] = oHeader.inquiry_site_template if str(oHeader.inquiry_site_template).startswith('1') else None
            oFile.active['M13'] = oHeader.inquiry_site_template if str(oHeader.inquiry_site_template).startswith('4') else None
            oFile.active['N13'] = oHeader.internal_notes
            oFile.active['O13'] = oHeader.external_notes
            oFile.active['I13'] = '=HYPERLINK("' + oRequest.build_absolute_uri(reverse('bomconfig:search')) +\
                                  '?config=' + searchscramble(oHeader.pk) + '","' +\
                                  oRequest.build_absolute_uri(reverse('bomconfig:search')) + '?config=' +\
                                  searchscramble(oHeader.pk) + '")'
        # end if

        # Populate Config Revision tab
        oFile.active = oFile.sheetnames.index('2b) BoM Config Revision')
        oFile.active.sheet_view.showGridLines = False
        if oHeader.configuration:
            iRow = 13
            aRevData = BuildDataArray(oHeader, revision=True)
            for oRev in aRevData:
                oFile.active['A' + str(iRow)] = oRev['0']
                oFile.active['B' + str(iRow)] = oRev['1']
                oFile.active['C' + str(iRow)] = oRev['2']
                oFile.active['D' + str(iRow)] = oRev['3']
                oFile.active['E' + str(iRow)] = oRev['4']
                oFile.active['F' + str(iRow)] = oRev['5']
                oFile.active['G' + str(iRow)] = oRev['6']
            # end for
        # end if

        # Populate SAP inquiry tab
        oFile.active = oFile.sheetnames.index('3a) SAP Inquiry Creation')
        oFile.active.sheet_view.showGridLines = False
        if oHeader.configuration:
            oFile.active['I4'] = ('X' if oHeader.configuration.internal_external_linkage else None)
            oFile.active['M4'] = ('$ ' + str(oHeader.configuration.zpru_total) if oHeader.configuration.zpru_total else '$ xx,xxx.xx')

            iRow = 13
            aConfigLines = ConfigLine.objects.filter(config=oHeader.configuration).order_by('line_number')
            aConfigLines = sorted(aConfigLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
            for oConfigLine in aConfigLines:
                if '.' in oConfigLine.line_number:
                    continue
                oFile.active['A' + str(iRow)] = oConfigLine.line_number
                oFile.active['B' + str(iRow)] = oConfigLine.part.base.product_number
                oFile.active['C' + str(iRow)] = oConfigLine.part.product_description
                oFile.active['D' + str(iRow)] = oConfigLine.order_qty
                oFile.active['E' + str(iRow)] = oConfigLine.plant
                oFile.active['F' + str(iRow)] = oConfigLine.sloc
                oFile.active['G' + str(iRow)] = oConfigLine.item_category
                # oFile.active['H' + str(iRow)] = oConfigLine.linepricing.unit_price
                oFile.active['H' + str(iRow)] = str(oConfigLine.linepricing.override_price) if str(oConfigLine.line_number) == '10' and\
                    hasattr(oConfigLine,'linepricing') and oConfigLine.linepricing.override_price else oConfigLine.linepricing.pricing_object.unit_price\
                    if GrabValue(oConfigLine,'linepricing.pricing_object') else ''
                oFile.active['J' + str(iRow)] = oConfigLine.material_group_5
                oFile.active['K' + str(iRow)] = oConfigLine.purchase_order_item_num
                oFile.active['L' + str(iRow)] = oConfigLine.condition_type
                oFile.active['M' + str(iRow)] = oConfigLine.amount
                iRow += 1
            # end for
        # end if

        # Populate SAP Site Template tab
        oFile.active = oFile.sheetnames.index('3b) SAP ST Creation')
        oFile.active.sheet_view.showGridLines = False
        if oHeader.configuration:
            iRow = 13
            aConfigLines = ConfigLine.objects.filter(config=oHeader.configuration).order_by('line_number')
            aConfigLines = sorted(aConfigLines, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
            for oConfigLine in aConfigLines:
                if '.' in oConfigLine.line_number:
                    continue

                oFile.active['A' + str(iRow)] = oConfigLine.line_number
                oFile.active['B' + str(iRow)] = oConfigLine.part.base.product_number
                oFile.active['C' + str(iRow)] = oConfigLine.part.product_description
                oFile.active['D' + str(iRow)] = oConfigLine.order_qty
                oFile.active['E' + str(iRow)] = oConfigLine.plant
                oFile.active['F' + str(iRow)] = oConfigLine.sloc
                oFile.active['G' + str(iRow)] = oConfigLine.item_category
                oFile.active['H' + str(iRow)] = oConfigLine.higher_level_item
                iRow += 1
            # end for
        # end if

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(sFileName)
        oFile.save(response)

        return response
    else:
        return HttpResponse()
# end def


def DownloadBaseline(oRequest):
    aColumnTitles = ['Line #', 'Product Number', 'Product Description', 'Order Qty', 'UoM', 'HW/SW Ind', 'Net Price 2015',
                     'Traceability Req. (Serialization)', 'Customer Asset?', 'Customer Asset Tagging Requirement',
                     'Customer number', 'Second Customer Number', 'Vendor Article Number', 'Comments',
                     'Additional Reference\n(if required)']

    if oRequest.method != 'POST' or not oRequest.POST:
        return Http404()
    # end if

    oBaseline = oRequest.POST['baseline']
    sVersion = oRequest.POST['version']
    sCookie = oRequest.POST['file-cookie']

    if oBaseline:
        oBaseline = Baseline.objects.get(title__iexact=oBaseline)
        sFileName = str(Baseline_Revision.objects.get(baseline=oBaseline, version=sVersion)) + ".xlsx"
        oFile = openpyxl.Workbook()

        oCentered = Alignment(horizontal='center')
        oRevFont = Font(name='Arial',size=10, bold=True)

        # Fill Revision tab
        oSheet = oFile.active
        oSheet.title = 'Revisions'
        oSheet.sheet_properties.tabColor = '0F243E'

        oSheet['A1'] = 'Revision'
        oSheet['A1'].font = oRevFont
        oSheet['A1'].alignment = oCentered
        oSheet['B1'] = ''
        oSheet['C1'] = 'Date'
        oSheet['C1'].font = oRevFont
        oSheet['C1'].alignment = oCentered

        oSheet.column_dimensions['A'].width = 90
        oSheet.column_dimensions['B'].width = 17
        oSheet.column_dimensions['C'].width = 17

        GenerateRevisionSummary(oBaseline,oBaseline.current_active_version, oBaseline.current_inprocess_version)
        aRevisions = [oRev.revision for oRev in oBaseline.revisionhistory_set.all()]
        aRevisions = sorted(list(set(aRevisions)), key=cmp_to_key(lambda x,y:(-1 if len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                                    or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))
                                                                                    or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y)) else 0 if x == y else 1)))
        aRevisions = aRevisions[:aRevisions.index(sVersion) + 1]
        iRow = 2
        iColorIndex = 0
        aColors = ['C0C0C0', '9999FF', 'FFFFCC', 'CCFFFF', 'FF8080', 'CCCCFF', '00CCFF', 'CCFFCC', 'FFFF99', '99CCFF',
                   'FF99CC', 'CC99FF', 'FFCC99', '33CCCC', '99CC00', 'FFCC00', 'FF9900', 'FF6600', '339966']
        for sRev in aRevisions:
            if not oBaseline.baseline_revision_set.get(version=sRev).header_set.all():
                continue
            sHistory = oBaseline.revisionhistory_set.get(revision=sRev).history
            if not sHistory or not sHistory.strip():
                continue
            # TODO: Print revision in multiple rows, not single cell
            sRevHistory = 'Revision ' + sRev + ':\n' + oBaseline.revisionhistory_set.get(revision=sRev).history
            aLines = sRevHistory.split('\n')
            for sLine in aLines:
                # oSheet['A' + str(iRow)] = 'Revision ' + sRev + ':\n' + oBaseline.revisionhistory_set.get(revision=sRev).history
                oSheet['A' + str(iRow)] = sLine
                oSheet['A' + str(iRow)].alignment = Alignment(wrap_text=True)
                oSheet['A' + str(iRow)].fill = GradientFill(type='linear', stop=[Color(aColors[iColorIndex]), Color(aColors[iColorIndex])])
                oSheet['B' + str(iRow)].fill = GradientFill(type='linear', stop=[Color(aColors[iColorIndex]), Color(aColors[iColorIndex])])
                oSheet['C' + str(iRow)].fill = GradientFill(type='linear', stop=[Color(aColors[iColorIndex]), Color(aColors[iColorIndex])])
                iRow += 1

            if Baseline_Revision.objects.get(baseline=oBaseline, version=sRev).completed_date:
                oSheet['C' + str(iRow)] = Baseline_Revision.objects.get(baseline=oBaseline, version=sRev).completed_date.strftime('%m/%d/%Y')
                oSheet['C' + str(iRow)].alignment = oCentered

            iRow += 2
            iColorIndex += 1
            if iColorIndex > len(aColors):
                iColorIndex = 0
        # end for

        if sVersion == oBaseline.current_inprocess_version:
            aHeaders = oBaseline.latest_revision \
                .header_set.exclude(configuration_status__name__in=('Discontinued', 'Inactive', 'On Hold')).exclude(
                program__name__in=('DTS',)) \
                .order_by('configuration_status', 'pick_list', 'configuration_designation')
            aHeaders = list(chain(Baseline_Revision.objects.get(
                baseline=oBaseline, version=oBaseline.current_inprocess_version
            ).header_set.exclude(configuration_status__name__in=('On Hold',)).order_by('configuration_status', 'pick_list', 'configuration_designation'), aHeaders))
        else:
            aHeaders = oBaseline.baseline_revision_set.get(version=sVersion) \
                .header_set.exclude(configuration_status__name__in=('On Hold',)).exclude(  # 'Discontinued', 'Obsolete',
                program__name__in=('DTS',)) \
                .order_by('configuration_status', 'pick_list', 'configuration_designation')
            aHeaders = list(aHeaders)

        for oHeader in list(aHeaders):
            if str(oHeader.configuration_designation) in oFile.get_sheet_names():
                aHeaders.remove(oHeader)
                continue

            if oHeader.configuration_status.name in ('In Process', 'In Process/Pending') and 'In Process' not in oFile.get_sheet_names():
                oSheet = oFile.create_sheet(title="In Process")
                oSheet.sheet_properties.tabColor = '80FF00'
            elif oHeader.configuration_status.name == 'Active' and 'Active' not in oFile.get_sheet_names():
                oSheet = oFile.create_sheet(title="Active")
                oSheet.sheet_properties.tabColor = '0062FF'
            elif oHeader.configuration_status.name == 'Discontinued' and 'Discontinued' not in oFile.get_sheet_names():
                oSheet = oFile.create_sheet(title="Discontinued")
                oSheet.sheet_properties.tabColor = 'FF0000'
            elif oHeader.configuration_status.name == 'Obsolete':
                continue

            iCurrentRow = 2
            aColumnWidths = [9, 23, 58, 12, 6, 15, 18, 18, 18, 12, 16, 22, 22, 23, 67, 83]
            sTitle = str(oHeader.configuration_designation)
            if len(sTitle) > 31:
                sTitle = sTitle.replace('Optional', 'Opt').replace('Hardware', 'HW').replace('Pick List', 'PL').replace(' - ','-').replace('_______CLONE_________',' CLONE ')

            oSheet = oFile.create_sheet(title=sTitle)
            # Build Header row
            for iIndex in range(len(aColumnTitles)):
                oSheet[str(utils.get_column_letter(iIndex + 1)) + '1'] = aColumnTitles[iIndex]
                oSheet[str(utils.get_column_letter(iIndex + 1)) + '1'].font = Font(bold=True)
                oSheet[str(utils.get_column_letter(iIndex + 1)) + '1'].border = Border(left=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                                       right=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                                       top=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                                       bottom=Side(color=colors.BLACK, border_style=borders.BORDER_MEDIUM))
                oSheet[str(utils.get_column_letter(iIndex + 1)) + '1'].alignment = Alignment(horizontal='center', vertical='center', wrapText=True)
                oSheet.column_dimensions[str(utils.get_column_letter(iIndex + 1))].width = aColumnWidths[iIndex]
                if iIndex in (6, ):
                    oSheet[str(utils.get_column_letter(iIndex + 1)) + '1'].fill = GradientFill(type='linear', stop=[Color(colors.GREEN), Color(colors.GREEN)])
            # end for

            oSheet.row_dimensions[1].height = 72.5
            oSheet.sheet_view.showGridLines = False
            oSheet.sheet_view.zoomScale = 60

            oBorder = Border(left=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                             right=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                             top=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                             bottom=Side(color=colors.BLACK, border_style=borders.BORDER_THIN))

            oFirstRowColor = GradientFill(type='linear', stop=[Color('77b6e3'), Color('77b6e3')])

            # Add line items (ordered by line number)
            aLineItems = oHeader.configuration.configline_set.all().order_by('line_number')
            aLineItems = sorted(aLineItems, key=lambda x: [int(y) for y in getattr(x, 'line_number').split('.')])
            oFirstItem = aLineItems[0]
            for oLineItem in aLineItems:
                oSheet['A' + str(iCurrentRow)] = oLineItem.line_number
                oSheet['A' + str(iCurrentRow)].alignment = oCentered
                oSheet['A' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['A' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['A' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['B' + str(iCurrentRow)] = ('..' if oLineItem.is_grandchild else '.' if oLineItem.is_child else '') + oLineItem.part.base.product_number
                oSheet['B' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['B' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['B' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['C' + str(iCurrentRow)] = oLineItem.part.product_description
                oSheet['C' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['C' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['C' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['D' + str(iCurrentRow)] = oLineItem.order_qty
                oSheet['D' + str(iCurrentRow)].alignment = oCentered
                oSheet['D' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['D' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['D' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['E' + str(iCurrentRow)] = oLineItem.part.base.unit_of_measure
                oSheet['E' + str(iCurrentRow)].alignment = oCentered
                oSheet['E' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['E' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['E' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['F' + str(iCurrentRow)] = oLineItem.commodity_type
                oSheet['F' + str(iCurrentRow)].alignment = oCentered
                oSheet['F' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['F' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['F' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['G' + str(iCurrentRow)] = GrabValue(oLineItem,'linepricing.pricing_object.unit_price') if oHeader.pick_list else ''
                oSheet['G' + str(iCurrentRow)].number_format = '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)'
                oSheet['G' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['G' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['G' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['H' + str(iCurrentRow)] = oLineItem.traceability_req
                oSheet['H' + str(iCurrentRow)].alignment = oCentered
                oSheet['H' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['H' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['H' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['I' + str(iCurrentRow)] = oLineItem.customer_asset
                oSheet['I' + str(iCurrentRow)].alignment = oCentered
                oSheet['I' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['I' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['I' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['J' + str(iCurrentRow)] = oLineItem.customer_asset_tagging
                oSheet['J' + str(iCurrentRow)].alignment = oCentered
                oSheet['J' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['J' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['J' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['K' + str(iCurrentRow)] = oLineItem.customer_number
                oSheet['K' + str(iCurrentRow)].alignment = oCentered
                oSheet['K' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['K' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['K' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['L' + str(iCurrentRow)] = oLineItem.sec_customer_number
                oSheet['L' + str(iCurrentRow)].alignment = oCentered
                oSheet['L' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['L' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['L' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['M' + str(iCurrentRow)] = oLineItem.vendor_article_number
                oSheet['M' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['M' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['M' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['N' + str(iCurrentRow)] = oLineItem.comments
                oSheet['N' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['N' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['N' + str(iCurrentRow)].font = Font(bold=True)
                oSheet['O' + str(iCurrentRow)] = oLineItem.additional_ref
                oSheet['O' + str(iCurrentRow)].border = oBorder
                if oLineItem == oFirstItem:
                    oSheet['O' + str(iCurrentRow)].fill = oFirstRowColor
                    oSheet['O' + str(iCurrentRow)].font = Font(bold=True)
                iCurrentRow += 1
            # end for
            if not oHeader.pick_list:
                oSheet['G2'] = GrabValue(oHeader.configuration.get_first_line(),'linepricing.override_price') or \
                               GrabValue(oHeader.configuration.get_first_line(),'linepricing.pricing_object.unit_price') or ''
            # end if

            # if oHeader.customer_unit.name == 'AT&T':
            #     oSheet['H1'] = 'Transportation Fee'
            #     oTransport = oHeader.configuration.configline_set.filter(condition_type__iexact='ZUST')
            #     if oTransport:
            #         oSheet['H2'] = oTransport[0].amount
            #     # end if
        # end for

        oSheet = oFile.create_sheet(0, 'ToC')
        aTOCTitles = ['Configuration', 'Customer Designation','Technology', 'Product Area 1', 'Product Area 2', 'Model',
                      'Model Description', 'What Model is this replacing?', 'BoM & Inquiry Details', 'BoM Request Type',
                      'Configuration / Ordering Status', 'Inquiry', 'Site Template', 'Ext Notes']
        aTOCFields = ['configuration_designation', 'customer_designation', 'technology', 'product_area1', 'product_area2',
                      'model', 'model_description', 'model_replaced', None, 'bom_request_type', 'configuration_status',
                      'inquiry_site_template', 'inquiry_site_template', 'external_notes']
        aTOCWidths = [25, 15, 15, 25, 10, 25, 50, 25, 25, 10, 15, 10, 10, 50]

        for iIndex in range(1, len(aTOCTitles)+1):
            oSheet[utils.get_column_letter(iIndex) + '1'].value = aTOCTitles[iIndex - 1]
            oSheet[utils.get_column_letter(iIndex) + '1'].alignment = Alignment(wrap_text=True)
            oSheet[utils.get_column_letter(iIndex) + '1'].font = Font(bold=True)
            oSheet[utils.get_column_letter(iIndex) + '1'].fill = GradientFill(type='linear',
                                                                                       stop=[Color('C0C0C0'),
                                                                                             Color('C0C0C0')])
            oSheet[utils.get_column_letter(iIndex) + '1'].border = Border(left=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                          right=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                          top=Side(color=colors.BLACK, border_style=borders.BORDER_THIN),
                                                                          bottom=Side(color=colors.BLACK, border_style=borders.BORDER_THIN))
            oSheet.column_dimensions[str(utils.get_column_letter(iIndex))].width = aTOCWidths[iIndex - 1]

        iCurrentRow = 2
        for oHeader in aHeaders:
            for iIndex in range(1, len(aTOCFields) + 1):
                if aTOCFields[iIndex - 1] and aTOCFields[iIndex - 1] != 'inquiry_site_template':
                    oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].value = str(getattr(oHeader, aTOCFields[iIndex - 1], '') or '').replace('/Pending','')
                elif aTOCFields[iIndex - 1] == 'inquiry_site_template':
                    if aTOCTitles[iIndex - 1] == 'Inquiry' and str(getattr(oHeader, aTOCFields[iIndex - 1], None)).startswith('1'):
                        oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].value = getattr(oHeader, aTOCFields[iIndex - 1])
                    elif aTOCTitles[iIndex - 1] == 'Site Template' and str(getattr(oHeader, aTOCFields[iIndex - 1], None)).startswith('4'):
                        oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].value = getattr(oHeader, aTOCFields[iIndex - 1])
                    else:
                        oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].value = None
                elif not aTOCFields[iIndex - 1]:
                    oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].value = str(oHeader.configuration_designation)
                    oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].hyperlink = "#'" + str(oHeader.configuration_designation) + "'!A1"
                    oSheet[utils.get_column_letter(iIndex) + str(iCurrentRow)].font = Font(color=colors.BLUE, underline='single')
            iCurrentRow += 1

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(sFileName)
        response.set_cookie('fileMark', sCookie, max_age=60)
        oFile.save(response)

        return response
    else:
        return HttpResponse()
# end def