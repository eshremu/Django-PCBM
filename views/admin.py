"""
Views related to in-tool, user/customer level administration.
"""

from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connections, IntegrityError
from django.http import HttpResponse, Http404
import json

from BoMConfig.models import DistroList, ApprovalList, User_Customer, Header, REF_CUSTOMER
from BoMConfig.forms import DistroForm, UserForm, UserAddForm, CustomerApprovalLevelForm
from BoMConfig.views.landing import Default


@login_required
def AdminLanding(oRequest):
    return Default(oRequest, 'BoMConfig/adminlanding.html')
# end def


@login_required
def MailingAdmin(oRequest):
    """
    Landing view for administration of distribution lists and other mailing
    related items
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'list': DistroList.objects.all()
    }
    sTemplate = 'BoMConfig/adminmail.html'
    return Default(oRequest, sTemplate, dContext)
# end def


@login_required
def MailingChange(oRequest, iRecordId=''):
    """
    View for creating new or editing/viewing existing DistroList objects
    :param oRequest: Django request object
    :param iRecordId: ID value of existing DistroForm object
    :return: HTML response via Default function
    """
    oNew = None

    # If the request is a POST request, we are saving a new record
    # or editing an existing record
    if oRequest.method == 'POST' and oRequest.POST:
        # Create an instance of a DistroForm using the data sent in post
        # If iRecordId was provided, link the form instance to the existing
        # DistroList object
        form = DistroForm(data=oRequest.POST, instance=DistroList.objects.get(id=iRecordId) if iRecordId else None)
        if form.is_valid():
            oNew = form.save()
    else:
        # Create an instance of DistroForm using data stored in an existing
        # DistroList object if iRecordId was provided, otherwise create a blank
        # DistroForm instance
        form = DistroForm(instance=DistroList.objects.get(id=iRecordId) if iRecordId else None)

    dContext = {
        'form': form,
        'grappelli_installed': 'grappelli' in settings.INSTALLED_APPS
    }
    sTemplate = 'BoMConfig/adminmailchange.html'

    # If this request was a creation of a new DistroList, redirect to this view
    # with the new DistroList's id provided
    if not iRecordId and oNew:
        return redirect(reverse('bomconfig:mailchange', kwargs={'iRecordId': oNew.id}))
    else:
        return Default(oRequest, sTemplate, dContext)
# end def


@login_required
def UserAdmin(oRequest):
    """
    Landing view for administration of users
    :param oRequest: Django request object
    :return: HTML response via Default function
    """



    dContext = {
        'users': set(
            get_user_model().objects.filter(groups__name__startswith='BOM_').exclude(groups__name__startswith='BOM_BPMA')
        ),
        'approval_wait': Header.objects.filter(
            configuration_status__name='In Process/Pending').filter(baseline__isdeleted=0),
        'usercu': User_Customer.objects.all(),
        'usercuname': REF_CUSTOMER.objects.all(),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False),
        'customer_list': ['All'] + [obj.name for obj in
                                    REF_CUSTOMER.objects.all()],

    }
    # print(dContext)
    # print('usercu')
    return Default(oRequest, 'BoMConfig/adminuser.html', dContext)
# end def

# S-07204 Refine User Admin page added delete button logic  in user admin page
@login_required
def UserDelete(oRequest):

    if oRequest.method == 'POST' and oRequest.POST:
        # When deleting a user, we don't actually remove the user from
        # the system, because they may have access to multiple tools.
        # Instead, we just remove the user from any groups that have
        # access permissions to this tool
        for record in json.loads(oRequest.POST.get('data')):
            oUser = get_user_model().objects.get(username=record)
            oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
            oRequest.session['errors'] = ['User deleted successfully']
            oRequest.session['message_is_error'] = False

        return HttpResponse()
    else:
        raise Http404()
    # end if

@login_required
def UserAdd(oRequest):
    """
    View for adding new users to the tool (and system if they do not exist)
    :param oRequest: Django request object
    :return: HTML response via Default function
    """

    # Create empty form instance
    oForm = UserAddForm()

    # If this is a form submission
    if oRequest.method == 'POST' and oRequest.POST:
        # Create a form instance using the submitted data
        oForm = UserAddForm(oRequest.POST)
        if oForm.is_valid():
            # Check if signum entered references a completely new user or just a user not in the tool
            if not get_user_model().objects.filter(username=oForm.cleaned_data['signum']):
                # Create New user by signum and default password
                newUser = get_user_model()(username=oForm.cleaned_data['signum'])
                newUser.set_password('123')
                newUser.save()
            else:
                # Retrieve existing user by signum
                newUser = get_user_model().objects.get(username=oForm.cleaned_data['signum'])

            # Redirect to UserChange view
            return redirect(reverse('bomconfig:userchange', kwargs={'iUserId': newUser.pk}))

    dContext={
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuseradd.html', dContext)
# end def


@login_required
def UserChange(oRequest, iUserId=''):
    """

    :param oRequest: Django request object
    :param iUserId: ID number of user object being changed
    :return: HTML response via Default function
    """

    # Find and retrieve the User object by iUserId
    if get_user_model().objects.filter(pk=iUserId):
        oUser = get_user_model().objects.get(pk=iUserId)

        # Create form defaults from User object information
        dInitial = {
            'signum': oUser.username,
            'first_name': oUser.first_name,
            'last_name': oUser.last_name,
            'email': oUser.email,
            'assigned_group': oUser.groups.filter(name__startswith='BOM_') if oUser.groups.filter(name__startswith='BOM_') else None
        }

    # Added for CU initial checked view
        aMatrixEntries = User_Customer.objects.filter(user_id=iUserId)
        dInitial['customer'] = list([str(oSecMat.customer_id) for oSecMat in aMatrixEntries.filter(user_id=iUserId)])

        # If this request is a form submission
        if oRequest.method == 'POST' and oRequest.POST:
            # Build a UserForm instance from the data submitted, using data in
            # dInitial to fill in blank fields.  It must be done this way
            # because UserForm is a standard Form object and not a ModelForm
            # object
            oForm = UserForm(oRequest.POST, initial=dInitial)

            # Save changes to user
            if oRequest.POST['action'] == 'save':
                if oForm.is_valid():
                    if oForm.has_changed():
                        # Process changes
                        for field in oForm.changed_data:
                            if field in ('signum', 'first_name', 'last_name', 'email'):
                                # Update user object personal info values
                                if field == 'signum':
                                    oUser.username = oForm.cleaned_data[field]

                                if field == 'first_name':
                                    oUser.first_name = oForm.cleaned_data[field]

                                if field == 'last_name':
                                    oUser.last_name = oForm.cleaned_data[field]

                                if field == 'email':
                                    oUser.email = oForm.cleaned_data[field]
                            elif field == 'assigned_group':
                                oUser.groups.add(*tuple(oForm.cleaned_data[field]))
                                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_').exclude(pk__in=oForm.cleaned_data[field])))
                            # end if
                    # S-06578: Added For CU options in Admin page
                            elif field == 'customer':
                                UserCustomerRelationEntries = User_Customer.objects.filter(user_id=iUserId)
                                aNewUserCustomerRelationEntries = []

                                for iCustomer in oForm.cleaned_data[field]:
                                    for obj in  REF_CUSTOMER.objects.filter(id=iCustomer):
                                        UserCustomerName = obj.name
                                    if UserCustomerRelationEntries.filter(customer_id=iCustomer,is_deleted=0,customer_name= UserCustomerName):
                                        aNewUserCustomerRelationEntries.append(
                                            UserCustomerRelationEntries.get(customer_id=iCustomer, is_deleted=0,customer_name= UserCustomerName))
                                    else:
                                        aNewUserCustomerRelationEntries.append(User_Customer(
                                            user_id=iUserId,
                                            customer_id=iCustomer,
                                            customer_name=UserCustomerName,
                                            is_deleted=0))
                                    # end if
                                # end for

                                for oSecMatrix in UserCustomerRelationEntries:
                                    if oSecMatrix not in aNewUserCustomerRelationEntries:
                                        oSecMatrix.delete()

                                for oSecMatrix in aNewUserCustomerRelationEntries:
                                    oSecMatrix.save()

                        # end for
                        oUser.save()
                        oRequest.session['errors'] = ['User changed successfully']
                        oRequest.session['message_is_error'] = False
                    else:
                        oRequest.session['errors'] = ['No changes detected']
                        oRequest.session['message_is_error'] = False
                    # end if
                # end if
            # Delete user
            elif oRequest.POST['action'] == 'delete':
                # When deleting a user, we don't actually remove the user from
                # the system, because they may have access to multiple tools.
                # Instead, we just remove the user from any groups that have
                # access permissions to this tool
                print(oUser)
                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
                oRequest.session['errors'] = ['User deleted successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:useradmin'))
            # end if
        else:
            # Build a UserForm instance from the data in dInitial
            oForm = UserForm(initial=dInitial)
    else:
        # If no such User is found, create an error and redirect to the UserAdd
        # view
        oRequest.session['errors'] = ['User not found']
        oRequest.session['message_is_error'] = True
        return redirect(reverse('bomconfig:useradd'))
    # end if

    dContext = {
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuserchange.html', dContext)
# end def


@login_required
def ApprovalAdmin(oRequest):
    """
    Landning view for administration of ApprovalList objects, used to
    determine which levels of approval are required for records per each
    customer.
    :param oRequest: Django request object
    :return: HTML response via Default function
    """
    dContext = {
        'list': ApprovalList.objects.all(),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    sTemplate = 'BoMConfig/adminapproval.html'
    return Default(oRequest, sTemplate, dContext)


@login_required
def ApprovalChange(oRequest, iObjId=None):
    """
    View for adding or changing ApprovalList objects
    :param oRequest: Django request object
    :param iObjId:
    :return: HTML response via Default function
    """
    dInit = {}
    oApproveList = None

    # If changing an existing ApprovalList, retrieve the object and build the
    # forms initial data
    if iObjId:
        try:
            oApproveList = ApprovalList.objects.get(id=iObjId)
            dInit.update({
                'customer': oApproveList.customer,
                'required_choices': oApproveList.required.split(','),
                'optional_choices': oApproveList.optional.split(','),
                'disallowed_choices': oApproveList.disallowed.split(',')
            })
        except ApprovalList.DoesNotExist:
            return redirect(reverse('bomconfig:approvaladd'))

    # Create a CustomerApprovalLevelForm instance, and use data from the
    # existing ApprovalList object if we are changing it
    form = CustomerApprovalLevelForm(initial=dInit, readonly=bool(oApproveList))

    # if this request is a form submission
    if oRequest.POST:
        # Create a CustomerApprovalLevelForm instance, and use data from the
        # existing ApprovalList object if we are changing it
        form = CustomerApprovalLevelForm(oRequest.POST, readonly=bool(oApproveList))
        if form.is_valid():
            if oApproveList:
                # Update and save existing object
                oApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oApproveList.save()
                oRequest.session['errors'] = ['Changes saved successfully']
                oRequest.session['message_is_error'] = False
            else:
                # Populate and save new object, then redirect to ApprovalChange
                # view with id of new ApprovalList object
                oNewApproveList = ApprovalList()
                oNewApproveList.customer = form.cleaned_data['customer']
                oNewApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oNewApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oNewApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oNewApproveList.save()
                oRequest.session['errors'] = ['Approval created successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:approvalchange', kwargs={'iObjId': oNewApproveList.id}))

    dContext = {
        'form': form,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminapprovalchange.html', dContext)
# end def
