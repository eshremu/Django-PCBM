__author__ = 'epastag'

from django.utils import timezone
from django.contrib import messages
from django.db import IntegrityError

from BoMConfig.models import Header, Part, Configuration, ConfigLine,\
    PartBase, Baseline, Baseline_Revision, LinePricing, REF_CUSTOMER, REF_REQUEST, ParseException,\
    REF_TECHNOLOGY, REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, REF_PROGRAM, REF_RADIO_BAND, REF_RADIO_FREQUENCY, REF_STATUS
from BoMConfig.forms import FileUploadForm
from BoMConfig.BillOfMaterials import BillOfMaterials
from BoMConfig.utils import UpRev, MassUploaderUpdate, GrabValue
from BoMConfig.views.landing import Unlock, Default

import os
import traceback


def Upload(oRequest):
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

    if oRequest.method == 'POST' and oRequest.POST and oRequest.FILES:
        form = FileUploadForm(oRequest.POST, oRequest.FILES)
        if form.is_valid():
            try:
                sBOM = ParseUpload(oRequest.FILES['file'])
                dContext = {
                    'title': sBOM,
                }
                return Default(oRequest, sTemplate='BoMConfig/success.html', dContext=dContext)
            except Exception as ex:
                if 'No sheet found with title:' in str(ex):
                    messages.add_message(oRequest, messages.ERROR, 'File specified is not a correctly formatted Configuration file.')
                else:
                    print(traceback.format_exc())

                    if isinstance(ex, IntegrityError):
                        messages.add_message(oRequest, messages.ERROR, 'A record matching this upload already exists in the database.')
                    else:
                        messages.add_message(oRequest, messages.ERROR, 'An error occurred during upload. Please check input and/or notify tool admin.')
                # end if
            # end try
        else:
            for error in form.non_field_errors():
                messages.add_message(oRequest, messages.ERROR, error)
            # end for
        # end if
    else:
        if oRequest.method == 'POST' and not oRequest.FILES:
            messages.add_message(oRequest, messages.ERROR, 'No file specified.')
        # end if

        form = FileUploadForm()
    # end if


    dContext ={
        'form': form
    }
    return Default(oRequest, sTemplate='BoMConfig/upload.html', dContext=dContext)
# end def


def ParseUpload(oSourceFile):
    import platform
    import tempfile
    sOS = platform.system()

    stringisless = lambda x,y:bool(len(x.strip('1234567890')) < len(y.strip('1234567890'))
                                                                 or list(x.strip('1234567890')) < (['']*(len(x.strip('1234567890'))-len(y.strip('1234567890'))) +
                                                                                                   list(y.strip('1234567890')))) \
                              or (x.strip('1234567890') == y.strip('1234567890') and list(x) < list(y))

    if sOS in ('Linux', 'Windows'):
        # Write uploaded file to temporary file
        Temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        for chunk in oSourceFile.chunks():
            Temp.write(chunk)
        # end for
        Temp.close()

        # Process temporary file through BoM Parser
        oBOM = BillOfMaterials(tempfile.gettempdir(), os.path.abspath(Temp.name))
        oBOM.PullBOMFileData()

        # Delete temporary file
        os.remove(Temp.name)

        if oBOM.dHeaderData['Configuration/Ordering Status'] not in ['In Process','Active','Discontinued','Cancelled','Inactive']:
            raise ParseException(str(oBOM.dHeaderData['Configuration/Ordering Status']) + " is not a valid Configuration/Ordering Status")

        oBaseline = None
        # Build Baseline, Header, Configuration, PartBases, Parts, and ConfigLines for uploaded file
        if oBOM.dHeaderData['Baseline Impacted'] not in (None,'', 'None'):
            cleanedBaseline = oBOM.dHeaderData['Baseline Impacted'].strip()
            if cleanedBaseline.lower().endswith('rev'):
                cleanedBaseline = cleanedBaseline[:-3].strip()
            oBOM.dHeaderData['Baseline Impacted'] = cleanedBaseline
            (oBaseline, _) = Baseline.objects.get_or_create(title=oBOM.dHeaderData['Baseline Impacted'],
                                                            customer=REF_CUSTOMER.objects.get(name=oBOM.dHeaderData['Customer Unit']))
        # endif

        # If file is not an 'In Process' Configuration
        if oBOM.dHeaderData['Configuration/Ordering Status'] != 'In Process' and oBaseline:
            # Catch the Baseline up to the revision being uploaded, if the file revision exceeds the current active revision
            while stringisless(oBaseline.current_active_version, oBOM.dHeaderData['Baseline Revision']):
                UpRev(oBaseline, oBOM.dHeaderData['Configuration'],oBOM.dHeaderData['Baseline Revision'])
            # end while


            # Get or create the baseline_revision to which the file should be assigned
            # i.e.: If file is in revision A1, but revision A1 does not exist, create it
            (oBaseRev, oNew) = Baseline_Revision.objects.get_or_create(**{'baseline': oBaseline, 'version':oBOM.dHeaderData['Baseline Revision']})
            if oNew:
                oBaseRev.completed_date = timezone.now()
                oBaseRev.save()
        # Else if file is in-process, change file baseline_version to current inprocess version
        elif oBOM.dHeaderData['Configuration/Ordering Status'] == 'In Process' and oBaseline:
            oBOM.dHeaderData['Baseline Revision'] = oBaseline.current_inprocess_version
        # end if

        # Make Header argument dictionary
        dHeadDict = {
            'person_responsible': oBOM.dHeaderData['Person Responsible'],
            'react_request': oBOM.dHeaderData['REACT Request'],
            'bom_request_type': REF_REQUEST.objects.get(name__iexact=oBOM.dHeaderData['BoM Request Type']),
            'customer_unit': REF_CUSTOMER.objects.get(name__iexact=oBOM.dHeaderData['Customer Unit']),
            'customer_name': oBOM.dHeaderData['Customer Name'],
            'sales_office': oBOM.dHeaderData['Sales Office'],
            'sales_group': oBOM.dHeaderData['Sales Group'],
            'sold_to_party': oBOM.dHeaderData['Sold-to Party'],
            'ship_to_party': oBOM.dHeaderData['Ship-to Party'],
            'bill_to_party': oBOM.dHeaderData['Bill-to Party'],
            'ericsson_contract': oBOM.dHeaderData['Ericsson Contract #'],
            'payment_terms': oBOM.dHeaderData['Payment Terms'],
            'projected_cutover': oBOM.dHeaderData['Projected Cut-over Date'],
            'program': REF_PROGRAM.objects.get(name__iexact=oBOM.dHeaderData['Program'],
                                               parent=REF_CUSTOMER.objects.get(name__iexact=oBOM.dHeaderData['Customer Unit']))\
                if REF_PROGRAM.objects.filter(name__iexact=oBOM.dHeaderData['Program'],
                                              parent=REF_CUSTOMER.objects.get(name__iexact=oBOM.dHeaderData['Customer Unit'])) else None,
            'configuration_designation': oBOM.dHeaderData['Configuration'],
            'customer_designation': oBOM.dHeaderData['Customer Designation'],
            'technology': REF_TECHNOLOGY.objects.get(name__iexact=oBOM.dHeaderData['Technology']) if\
                REF_TECHNOLOGY.objects.filter(name__iexact=oBOM.dHeaderData['Technology']) else None,
            'product_area1': REF_PRODUCT_AREA_1.objects.get(name__iexact=oBOM.dHeaderData['Product Area 1']) if\
                REF_PRODUCT_AREA_1.objects.filter(name__iexact=oBOM.dHeaderData['Product Area 1']) else None,
            'product_area2': REF_PRODUCT_AREA_2.objects.get(name__iexact=oBOM.dHeaderData['Product Area 2']) if\
                REF_PRODUCT_AREA_2.objects.filter(name__iexact=oBOM.dHeaderData['Product Area 2']) else None,
            'radio_frequency': REF_RADIO_FREQUENCY.objects.get(name__iexact=oBOM.dHeaderData['Radio Frequency']) if\
                REF_RADIO_FREQUENCY.objects.filter(name__iexact=oBOM.dHeaderData['Radio Frequency']) else None,
            'radio_band': REF_RADIO_BAND.objects.get(name__iexact=oBOM.dHeaderData['Radio Band']) if\
                REF_RADIO_BAND.objects.filter(name__iexact=oBOM.dHeaderData['Radio Band']) else None,
            # 'optional_free_text1': oBOM.dHeaderData['Person Responsible'],
            # 'optional_free_text2': oBOM.dHeaderData['Person Responsible'],
            # 'optional_free_text3': oBOM.dHeaderData['Person Responsible'],
            'inquiry_site_template': oBOM.dHeaderData['Inquiry / Site Template Number'],
            'readiness_complete': oBOM.dHeaderData['Readiness Complete'],
            'complete_delivery': oBOM.dHeaderData['Complete Delivery'],
            'no_zip_routing': oBOM.dHeaderData['No ZipRouting'],
            'valid_to_date': oBOM.dHeaderData['Valid-to Date'],
            'valid_from_date': oBOM.dHeaderData['Valid-from Date'],
            'shipping_condition': oBOM.dHeaderData['Shipping Condition'],
            'baseline_impacted': oBOM.dHeaderData['Baseline Impacted'],
            'model': oBOM.dHeaderData['Model'],
            'model_description': oBOM.dHeaderData['Model Description'],
            'model_replaced': oBOM.dHeaderData['What Model is this replacing?'],
            'initial_revision': oBOM.dHeaderData['Initial Revision'],
            'configuration_status': REF_STATUS.objects.get(name__iexact=oBOM.dHeaderData['Configuration/Ordering Status'])\
                if REF_STATUS.objects.get(name__iexact=oBOM.dHeaderData['Configuration/Ordering Status']) else \
                REF_STATUS.objects.get(pk=1),
            'old_configuration_status': None,
            'workgroup': oBOM.dHeaderData['Workgroup'],
            'name': oBOM.dHeaderData['Name'],
            'pick_list': oBOM.dHeaderData['Is this a pick list?'],
            'internal_notes': oBOM.dHeaderData['Internal Notes'],
            'external_notes': oBOM.dHeaderData['External Notes'],
            'baseline_version': oBOM.dHeaderData['Baseline Revision'],
            'bom_version': oBOM.dHeaderData['System Revision'],
            'release_date': oBOM.dHeaderData['Release Date'],
            'change_comments': oBOM.dHeaderData['Changes/Comments'],
            'baseline': Baseline_Revision.objects.get(baseline=oBaseline,version=oBOM.dHeaderData['Baseline Revision'])\
                if Baseline_Revision.objects.filter(baseline=oBaseline,version=oBOM.dHeaderData['Baseline Revision']) else None,
        }

        # Attempt to find Header with configuration and baseline matching upload
        try:
            try:
                tempBase = Baseline_Revision.objects.get(baseline=oBaseline,version=oBOM.dHeaderData['Baseline Revision'])
            except Baseline_Revision.DoesNotExist:
                tempBase = None
            # end try

            oHeader = Header.objects.get(configuration_designation=oBOM.GetBOMIdentifier(),
                                         baseline_version__iexact=oBOM.dHeaderData['Baseline Revision'], baseline=tempBase,
                                         program=REF_PROGRAM.objects.get(name__iexact=oBOM.dHeaderData['Program'],
                                                                         parent=REF_CUSTOMER.objects.get(
                                                                             name__iexact=oBOM.dHeaderData['Customer Unit'])
                                                                         ) if\
                                             REF_PROGRAM.objects.filter(name__iexact=oBOM.dHeaderData['Program'],
                                                                        parent=REF_CUSTOMER.objects.get(
                                                                            name__iexact=oBOM.dHeaderData['Customer Unit'])
                                                                        ) else None
                                         )
        except Header.DoesNotExist:
            oHeader = None
        # end try

        # Update / Create new Header
        if str(GrabValue(oHeader, 'configuration_status.name')) in ('In Process', '', 'None'):
            oHeader = Header(pk=getattr(oHeader,'pk', None),**dHeadDict)
            oHeader.save()
        else:
            raise ValueError('Active Configuration ' + str(oHeader) + ' already exists.')
        # end if

        """
        At this point, the Header is either newly entered or an update of an existing 'In Process' configuration,
        so it can be overwritten with the data provided.
        """
        try:
            oConfig = Configuration.objects.get(header=oHeader)
        except Configuration.DoesNotExist:
            oConfig = None
        # end try

        dConfigDict = {
            'ready_for_forecast': oBOM.dConfigData['Reassign'],
            'PSM_on_hold': oBOM.dConfigData['PSM on Hold'],
            'internal_external_linkage': oBOM.dConfigData['Internal/External Linkage'],
            'net_value': "{:.2f}".format(round(float(oBOM.dConfigData['NET Value']),2)),
            'zpru_total': "{:.2f}".format(round(float(oBOM.dConfigData['ZPRU Total']), 2)) if oBOM.dConfigData['ZPRU Total'] else None,
            'needs_zpru': False,
            'header': oHeader
        }

        oConfig = Configuration(pk=getattr(oConfig,'pk', None),**dConfigDict)
        oConfig.save()

        ConfigLine.objects.filter(config=oConfig).delete()

        for sKey in oBOM.dItemData.keys():
            dPartBaseDict = {
                'product_number': oBOM.dItemData[sKey]['Product Number'].strip('.'),
                'unit_of_measure': oBOM.dItemData[sKey]['UoM'],
            }

            (oBase,_) = PartBase.objects.get_or_create(product_number=dPartBaseDict['product_number'])
            PartBase(pk=getattr(oBase, 'pk'),**dPartBaseDict).save()

            dPartDict = {
                'product_description': oBOM.dItemData[sKey]['Product Description'],
                'base': oBase,
            }

            (oPart,_) = Part.objects.get_or_create(**dPartDict)

            dConfigLineDict = {
                'line_number': oBOM.dItemData[sKey]['Line #'],
                'order_qty': oBOM.dItemData[sKey]['Order Qty'],
                'plant': oBOM.dItemData[sKey]['Plant'],
                'sloc': oBOM.dItemData[sKey]['SLOC'],
                'item_category': oBOM.dItemData[sKey]['Item Cat'],
                'spud': oBOM.dItemData[sKey]['SPUD'],
                'internal_notes': oBOM.dItemData[sKey]['Int Notes'],
                'higher_level_item': oBOM.dItemData[sKey]['Higher Level Item'],
                'material_group_5': oBOM.dItemData[sKey]['Material Group 5'],
                'purchase_order_item_num': oBOM.dItemData[sKey]['Purch Order Item No'],
                'condition_type': oBOM.dItemData[sKey]['Condition Type'],
                'amount': oBOM.dItemData[sKey]['Amount'],
                'customer_asset': oBOM.dItemData[sKey]['Customer Asset?'],
                'customer_asset_tagging': oBOM.dItemData[sKey]['Customer Asset Tagging Requirement'],
                'customer_number': oBOM.dItemData[sKey]['Customer Number'],
                'sec_customer_number': oBOM.dItemData[sKey]['Second Customer Number'],
                'vendor_article_number': oBOM.dItemData[sKey]['Vendor Article Number'],
                'comments': oBOM.dItemData[sKey]['Comments'],
                'additional_ref': oBOM.dItemData[sKey]['Additional Reference (if required)'],
                'config': oConfig,
                'part': oPart,
                'is_child': bool(str(sKey).count('.') == 1),
                'is_grandchild': bool(str(sKey).count('.') == 2),
                'pcode': oBOM.dItemData[sKey]['P-Code - Fire Code, Desc'],
                'commodity_type': oBOM.dItemData[sKey]['HW/SW Ind'],
                'package_type': oBOM.dItemData[sKey]['Prod Pkg Type'],
                'REcode': oBOM.dItemData[sKey]['RE-Code'],
                'mu_flag': oBOM.dItemData[sKey]['MU-Flag'],
                'x_plant': oBOM.dItemData[sKey]['X-plant matl status'],
                'traceability_req': oBOM.dItemData[sKey]['Traceability Req (Serialization)'],
            }

            oConfigLine = ConfigLine.objects.create(**dConfigLineDict)

            dLinePrice = {
                'unit_price': "{:.2f}".format(round(float(oBOM.dItemData[sKey]['Unit Price']), 2)) if\
                    oBOM.dItemData[sKey]['Unit Price'] else None,
                'override_price': None,
                'config_line': oConfigLine
            }

            LinePricing.objects.create(**dLinePrice)
        # end for

        if oBaseline:
            MassUploaderUpdate(oBaseline)

        return oBOM.GetBOMIdentifier()
    else:
        raise EnvironmentError('The system does not support your operating system')
    # end if
# end def