from django.http import JsonResponse
from django.shortcuts import redirect

from BoMConfig.models import CustomerPartInfo, PartBase, REF_CUSTOMER
from BoMConfig.views.landing import Default

from baseString import StrToBool

import json


def CustomerAuditLand(oRequest):
    return redirect('bomconfig:customeraudit')


def CustomerAudit(oRequest):
    dContext = {
        'customer_list': REF_CUSTOMER.objects.all(),
        'data': json.dumps([[]]),
        'selectedCust': REF_CUSTOMER.objects.first()
    }

    if oRequest.POST:
        aData = json.loads(oRequest.POST.get('dataForm', '[]'))
        oCustomer = REF_CUSTOMER.objects.get(id=oRequest.POST.get('customerSelect'))

        if aData:
            aData = list(aLine for aLine in aData if any(aLine))

        for aLine in aData:
            try:
                (oPart,_) = PartBase.objects.get_or_create(product_number=aLine[0], defaults={'unit_of_measure': 'PC'})
            except PartBase.MultipleObjectsReturned:
                oPart = PartBase.objects.filter(product_number=aLine[0]).first()

            dNewCustInfo = {
                'customer': oCustomer,
                'customer_number': aLine[1],
                'part': oPart,
                'customer_asset_tagging': True if aLine[2] == 'Y' else False if aLine[2] == 'N' else None,
                'customer_asset': True if aLine[3] == 'Y' else False if aLine[3] == 'N' else None
            }

            # if bCreateNew:
            (oNewCustInfo, bCreated) = CustomerPartInfo.objects.get_or_create(**dNewCustInfo)

            oNewCustInfo.active = True
            oNewCustInfo.save()
        # end for

        dContext['data'] = json.dumps(aData)
        dContext['selectedCust'] = oCustomer

    return Default(oRequest, 'BoMConfig/customer_audit.html', dContext)
# end def


def CustomerAuditTableValidate(oRequest):
    received_data = json.loads(oRequest.POST['changed_data'])
    customer = oRequest.POST['customer']
    override = StrToBool(str(oRequest.POST.get('override', False)))

    response_data = {
        'table_data': {},
        'table_info': {},
    }

    for key in received_data.keys():
        response_data['table_data'][key] = [None] * 4
        response_data['table_info'][key] = [None] * 4

        part = None
        cust_info = None
        try:
            part = PartBase.objects.get(product_number=received_data[key][0])
            cust_info = part.customerpartinfo_set.get(customer__id=customer, active=True)
            response_data['table_data'][key][0] = part.product_number
            response_data['table_info'][key][0] = True
        except PartBase.DoesNotExist:
            if any(received_data[key]):
                response_data['table_data'][key][0] = received_data[key][0]
                response_data['table_info'][key][0] = None
            else:
                response_data['table_data'][key][0] = None
                response_data['table_info'][key][0] = None
        except (CustomerPartInfo.DoesNotExist, ValueError):
            response_data['table_data'][key][0] = part.product_number
            response_data['table_info'][key][0] = True
        # end try

        if not cust_info:
            try:
                cust_info = CustomerPartInfo.objects.get(customer_number=received_data[key][1], customer__id=customer, active=True)
                # if not response_data['table_data'][key][0]:
                response_data['table_data'][key][0] = cust_info.part.product_number

            except (CustomerPartInfo.DoesNotExist, ValueError):
                response_data['table_data'][key][1] = received_data[key][1]
                response_data['table_info'][key][1] = None
            # end try
        # end if

        if cust_info:
            if override:
                response_data['table_data'][key][0] = received_data[key][0] or cust_info.part.product_number
                response_data['table_info'][key][0] = True if cust_info.part.product_number == received_data[key][0] or not received_data[key][0] else None

                response_data['table_data'][key][1] = received_data[key][1] or cust_info.customer_number
                response_data['table_info'][key][1] = True if cust_info.customer_number == received_data[key][1] or not received_data[key][1] else None

                response_data['table_data'][key][2] = received_data[key][2] #or ('Y' if cust_info.customer_asset_tagging else 'N')
                response_data['table_data'][key][3] = received_data[key][3] #or ('Y' if cust_info.customer_asset else 'N')

                if cust_info.customer_asset_tagging is not None and received_data[key][2]:
                    response_data['table_info'][key][2] = True if bool(
                        cust_info.customer_asset_tagging == StrToBool(received_data[key][2], "")) else None
                elif cust_info.customer_asset_tagging is not None and not received_data[key][2]:
                    response_data['table_info'][key][2] = None
                elif cust_info.customer_asset_tagging is None:
                    response_data['table_info'][key][2] = None

                if cust_info.customer_asset is not None and received_data[key][3]:
                    response_data['table_info'][key][3] = True if bool(
                        cust_info.customer_asset == StrToBool(received_data[key][3], "")) else None
                elif cust_info.customer_asset is not None and not received_data[key][3]:
                    response_data['table_info'][key][3] = None
                elif cust_info.customer_asset is None:
                    response_data['table_info'][key][3] = None
            else:
                response_data['table_data'][key][0] = cust_info.part.product_number
                response_data['table_info'][key][0] = bool(cust_info.part.product_number == received_data[key][0])

                response_data['table_data'][key][1] = cust_info.customer_number
                response_data['table_info'][key][1] = bool(cust_info.customer_number == received_data[key][1])

                response_data['table_data'][key][2] = "Y" if cust_info.customer_asset_tagging else "N" if cust_info.customer_asset_tagging == False else ' '
                response_data['table_data'][key][3] = "Y" if cust_info.customer_asset else "N" if cust_info.customer_asset == False else ' '

                if cust_info.customer_asset_tagging is not None:
                    if received_data[key][2]:
                        response_data['table_info'][key][2] = bool(cust_info.customer_asset_tagging == StrToBool(received_data[key][2], ""))
                    elif not received_data[key][2]:
                        response_data['table_info'][key][2] = False
                else:
                    if not received_data[key][2]:
                        response_data['table_info'][key][2] = True
                    else:
                        response_data['table_info'][key][2] = False

                if cust_info.customer_asset is not None:
                    if received_data[key][3]:
                        response_data['table_info'][key][3] = bool(
                            cust_info.customer_asset == StrToBool(received_data[key][3], ""))
                    elif not received_data[key][3]:
                        response_data['table_info'][key][3] = False
                else:
                    if not received_data[key][3]:
                        response_data['table_info'][key][3] = True
                    else:
                        response_data['table_info'][key][3] = False
        else:
            response_data['table_data'][key][1] = received_data[key][1]
            response_data['table_data'][key][2] = received_data[key][2]
            response_data['table_data'][key][3] = received_data[key][3]
            if response_data['table_data'][key][1] and response_data['table_info'][key][1] is None:
                response_data['table_data'][key][2] = response_data['table_data'][key][2] #or 'N'
                response_data['table_info'][key][2] = None
                response_data['table_data'][key][3] = response_data['table_data'][key][3] #or 'N'
                response_data['table_info'][key][3] = None
        # end if

    return JsonResponse(response_data)
# end def


def CustomerAuditUpload(oRequest):
    return Default(oRequest, sTemplate='BoMConfig/customer_audit_upload.html')