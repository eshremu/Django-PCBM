from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings

from BoMConfig.models import DistroList, ApprovalList
from BoMConfig.forms import DistroForm, UserForm, UserAddForm, CustomerApprovalLevelForm
from BoMConfig.views.landing import Default


def AdminLanding(oRequest):
    return Default(oRequest, 'BoMConfig/adminlanding.html')
# end def


def MailingAdmin(oRequest):
    dContext = {
        'list': DistroList.objects.all()
    }
    sTemplate = 'BoMConfig/adminmail.html'
    return Default(oRequest, sTemplate, dContext)
# end def


def MailingChange(oRequest, id=''):
    oNew = None
    if oRequest.method == 'POST' and oRequest.POST:
        form = DistroForm(data=oRequest.POST, instance=DistroList.objects.get(id=id) if id else None)
        if form.is_valid():
            oNew = form.save()
    else:
        form = DistroForm(instance=DistroList.objects.get(id=id) if id else None)

    dContext = {
        'form': form,
        'grappelli_installed': 'grappelli' in settings.INSTALLED_APPS
    }
    sTemplate = 'BoMConfig/adminmailchange.html'
    if not id and oNew:
        return redirect(reverse('bomconfig:mailchange', kwargs={'id': oNew.id}))
    else:
        return Default(oRequest, sTemplate, dContext)
# end def


def UserAdmin(oRequest):
    dContext = {
        'users': set(
            get_user_model().objects.filter(groups__name__startswith='BOM_').exclude(groups__name__startswith='BOM_BPMA')
        ),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuser.html', dContext)
# end def


def UserAdd(oRequest):
    oForm = UserAddForm()
    if oRequest.method == 'POST' and oRequest.POST:
        oForm = UserAddForm(oRequest.POST)
        if oForm.is_valid():
            # Check if signum entered references a completely new user or just a user not in the tool
            if not get_user_model().objects.filter(username=oForm.cleaned_data['signum']):
                #Create New user by signum and default password
                newUser = get_user_model()(username=oForm.cleaned_data['signum'])
                newUser.set_password('123')
                newUser.save()
            else:
                newUser = get_user_model().objects.get(username=oForm.cleaned_data['signum'])

            return redirect(reverse('bomconfig:userchange', kwargs={'id': newUser.pk}))
    dContext={
        'form': oForm,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    return Default(oRequest, 'BoMConfig/adminuseradd.html', dContext)
# end def


def UserChange(oRequest, id=''):
    if get_user_model().objects.filter(pk=id):
        oUser = get_user_model().objects.get(pk=id)

        dInitial = {
            'signum': oUser.username,
            'first_name': oUser.first_name,
            'last_name': oUser.last_name,
            'email': oUser.email,
            'assigned_group': oUser.groups.filter(name__startswith='BOM_') if oUser.groups.filter(name__startswith='BOM_') else None
        }

        if oRequest.method == 'POST' and oRequest.POST:
            oForm = UserForm(oRequest.POST, initial=dInitial)
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
                        # end for
                        oUser.save()
                        oRequest.session['errors'] = ['User changed successfully']
                        oRequest.session['message_is_error'] = False
                    else:
                        oRequest.session['errors'] = ['No changes detected']
                        oRequest.session['message_is_error'] = False
                    # end if
                # end if
            elif oRequest.POST['action'] == 'delete':
                oUser.groups.remove(*tuple(Group.objects.filter(name__startswith='BOM_')))
                oRequest.session['errors'] = ['User deleted successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:useradmin'))
            # end if
        else:
            oForm = UserForm(initial=dInitial)
    else:
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


def ApprovalAdmin(oRequest):
    dContext = {
        'list': ApprovalList.objects.all(),
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }
    sTemplate = 'BoMConfig/adminapproval.html'
    return Default(oRequest, sTemplate, dContext)


def ApprovalChange(oRequest, id=None):
    dInit = {}
    oApproveList = None

    if id:
        try:
            oApproveList = ApprovalList.objects.get(id=id)
            dInit.update({
                'customer': oApproveList.customer,
                'required_choices': oApproveList.required.split(','),
                'optional_choices': oApproveList.optional.split(','),
                'disallowed_choices': oApproveList.disallowed.split(',')
            })
        except ApprovalList.DoesNotExist:
            return redirect(reverse('bomconfig:approvaladd'))

    form = CustomerApprovalLevelForm(initial=dInit, readonly=bool(oApproveList))

    if oRequest.POST:
        form = CustomerApprovalLevelForm(oRequest.POST, readonly=bool(oApproveList))
        if form.is_valid():
            if oApproveList:  # Update existing
                oApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oApproveList.save()
                oRequest.session['errors'] = ['Changes saved successfully']
                oRequest.session['message_is_error'] = False
            else:
                oNewApproveList = ApprovalList()
                oNewApproveList.customer = form.cleaned_data['customer']
                oNewApproveList.required = ','.join(form.cleaned_data['required_choices'])
                oNewApproveList.optional = ','.join(form.cleaned_data['optional_choices'])
                oNewApproveList.disallowed = ','.join(form.cleaned_data['disallowed_choices'])
                oNewApproveList.save()
                oRequest.session['errors'] = ['Approval created successfully']
                oRequest.session['message_is_error'] = False
                return redirect(reverse('bomconfig:approvalchange', kwargs={'id': oNewApproveList.id}))

    dContext = {
        'form': form,
        'errors': oRequest.session.pop('errors', None),
        'message_type_is_error': oRequest.session.pop('message_is_error', False)
    }

    return Default(oRequest, 'BoMConfig/adminapprovalchange.html', dContext)
# end def
