from django.http import JsonResponse

from BoMConfig.models import CustomerPartInfo, PartBase, REF_CUSTOMER
from BoMConfig.views.landing import Default

from baseString import StrToBool

import json


def CustomerAudit(oRequest):
    dContext = {
        'customer_list': REF_CUSTOMER.objects.all(),
        'data': [[]],
        'selectedCust': REF_CUSTOMER.objects.first()
    }

    if oRequest.POST:
        data = json.loads(oRequest.POST.get('dataForm', '[]'))
        customer = REF_CUSTOMER.objects.get(pk=oRequest.POST.get('customerSelect'))
        override = 'override' in oRequest.POST

        if data:
            data = list(line for line in data if any(line))

        print(data, customer, override)
        dContext['data'] = data
        dContext['selectedCust'] = customer

    return Default(oRequest, 'BoMConfig/customer_audit.html', dContext)
# end def


def TableValidate(oRequest):
    received_data = json.loads(oRequest.POST['changed_data'])
    customer = oRequest.POST['customer']
    override = StrToBool(oRequest.POST.get('override', False))

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
            cust_info = part.customerpartinfo_set.get(customer__id=customer)
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
                cust_info = CustomerPartInfo.objects.get(customer_number=received_data[key][1], customer__id=customer)
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

                response_data['table_data'][key][2] = received_data[key][2] or ('Y' if cust_info.customer_asset_tagging else 'N')
                response_data['table_data'][key][3] = received_data[key][3] or ('Y' if cust_info.customer_asset else 'N')

                if cust_info.customer_asset_tagging is not None and received_data[key][2]:
                    response_data['table_info'][key][2] = True if bool(
                        cust_info.customer_asset_tagging == StrToBool(received_data[key][2], "")) else None
                elif cust_info.customer_asset_tagging is not None and not received_data[key][2]:
                    response_data['table_info'][key][2] = True
                elif cust_info.customer_asset_tagging is None:
                    response_data['table_info'][key][2] = None

                if cust_info.customer_asset is not None and received_data[key][3]:
                    response_data['table_info'][key][3] = True if bool(
                        cust_info.customer_asset == StrToBool(received_data[key][3], "")) else None
                elif cust_info.customer_asset is not None and not received_data[key][3]:
                    response_data['table_info'][key][3] = True
                elif cust_info.customer_asset is None:
                    response_data['table_info'][key][3] = None
            else:
                response_data['table_data'][key][0] = cust_info.part.product_number
                response_data['table_info'][key][0] = bool(cust_info.part.product_number == received_data[key][0])

                response_data['table_data'][key][1] = cust_info.customer_number
                response_data['table_info'][key][1] = bool(cust_info.customer_number == received_data[key][1])

                response_data['table_data'][key][2] = "Y" if cust_info.customer_asset_tagging else "N" if not cust_info.customer_asset_tagging else None
                response_data['table_data'][key][3] = "Y" if cust_info.customer_asset else "N" if not cust_info.customer_asset else None

                if cust_info.customer_asset_tagging is not None and received_data[key][2]:
                    response_data['table_info'][key][2] = bool(cust_info.customer_asset_tagging == StrToBool(received_data[key][2], ""))
                elif cust_info.customer_asset_tagging is not None and not received_data[key][2]:
                    response_data['table_info'][key][2] = False
                elif cust_info.customer_asset_tagging is None:
                    response_data['table_info'][key][2] = None

                if cust_info.customer_asset is not None and received_data[key][3]:
                    response_data['table_info'][key][3] = bool(cust_info.customer_asset == StrToBool(received_data[key][3], ""))
                elif cust_info.customer_asset is not None and not received_data[key][3]:
                    response_data['table_info'][key][3] = False
                elif cust_info.customer_asset is None:
                    response_data['table_info'][key][3] = None

            # response_data['table_info'][key][0] = bool(cust_info.part.product_number == received_data[key][0])
            #
            # response_data['table_data'][key][1] = cust_info.customer_number
            # response_data['table_info'][key][1] = bool(cust_info.customer_number == received_data[key][1])
        else:
            response_data['table_data'][key][1] = received_data[key][1]
            response_data['table_data'][key][2] = received_data[key][2]
            response_data['table_data'][key][3] = received_data[key][3]
            if response_data['table_data'][key][1] and response_data['table_info'][key][1] is None:
                response_data['table_data'][key][2] = response_data['table_data'][key][2] or 'N'
                response_data['table_info'][key][2] = None
                response_data['table_data'][key][3] = response_data['table_data'][key][3] or 'N'
                response_data['table_info'][key][3] = None
        # end if

    return JsonResponse(response_data)
# end def