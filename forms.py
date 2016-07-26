from django import forms
from django.db import connections
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User, Group
from django.contrib.admin.widgets import FilteredSelectMultiple

from BoMConfig.models import Header, Configuration, Baseline, REF_CUSTOMER, LinePricing, ConfigLine, PricingObject, DistroList, SecurityPermission

import datetime
import os
import re


class HeaderForm(forms.ModelForm):
    class Meta:
        model = Header
        exclude = ['internal_notes', 'external_notes', 'baseline_version', 'bom_version', 'release_date',
                   'change_notes', 'change_comments', 'baseline', 'old_configuration_status']
        widgets = {'model_replaced_link': forms.HiddenInput()}
    # end class

    def __init__(self, *args, **kwargs):
        bReadOnly = False

        if 'readonly' in kwargs:
            bReadOnly = kwargs['readonly']
            del kwargs['readonly']
        # end if

        super().__init__(*args, **kwargs)

        self.fields['configuration_status'].widget.attrs['readonly'] = 'True'
        self.fields['configuration_status'].widget.attrs['disabled'] = 'True'
        self.fields['configuration_status'].widget.attrs['style'] = 'border:none;'
        self.fields['configuration_status'].widget.attrs['style'] += '-webkit-appearance:none;'

        self.fields['react_request'].widget.attrs['size'] = 25
        self.fields['model_description'].widget.attrs['size'] = 45

        if (hasattr(self.instance, 'configuration_status') and self.instance.configuration_status.name != 'In Process') or bReadOnly:
            for field in self.fields.keys():
                self.fields[field].widget.attrs['readonly'] = 'True'
                self.fields[field].widget.attrs['style'] = 'border:none;'
                if self.initial:
                    if self.initial[field] and isinstance(self.initial[field], str):
                        self.fields[field].widget.attrs['size'] = len(self.initial[field]) + 5

                if isinstance(self.fields[field].widget, (forms.widgets.Select, forms.widgets.CheckboxInput)):
                    self.fields[field].widget.attrs['disabled'] = 'True'
                    if isinstance(self.fields[field].widget, (forms.widgets.Select)):
                        self.fields[field].widget.attrs['style'] += '-webkit-appearance:none;'
            # end for
        else:
            self.fields['model_replaced'].widget = AutocompleteInput(
                'header_list',
                list([(head.id,
                       head.configuration_designation +
                       (" (" + str(head.program) + ")" if head.program else ''),
                       (str(head.baseline.baseline.title) if head.baseline else '')
                       ) for head in Header.objects.filter(configuration_status__name='Active')]),
                attrs=self.fields['model_replaced'].widget.attrs
            )
        # end if
    # end def

    def clean(self):
        data = super().clean()

        data['sales_office'] = data['sales_office'].upper()
        data['sales_group'] = data['sales_group'].upper()
        # print(data)
        if self.fields['bom_request_type'].widget.attrs.get('disabled', None) == 'True':
            keys = [key for key in self.errors]
            for key in keys:
                del self.errors[key]
            # end for
            return data

        if 'configuration_designation' in data:
            if re.search(r"_+CLONE_*$", data['configuration_designation'].upper()):
                self.add_error('configuration_designation', forms.ValidationError('Cloned configurations require rename ("_CLONE" still in name)'))
            elif data['configuration_designation'].upper().endswith('_'):
                self.add_error('configuration_designation', forms.ValidationError('Configuration designation cannot end with underscore ("_")'))
            elif len(data['configuration_designation']) > 18 and not data['pick_list']:
                self.add_error('configuration_designation', forms.ValidationError('Configuration title exceeds 18 characters'))
        # end if

        if 'model' in data and len(data['model']) > 18 and not data['pick_list']:
            self.add_error('model', forms.ValidationError('Model title exceeds 18 characters'))
        # end if

        if 'valid_to_date' in data and 'valid_from_date' in data and data['valid_to_date'] and\
                data['valid_from_date'] and data['valid_to_date'] < data['valid_from_date']:
            self.add_error('valid_to_date', forms.ValidationError('Valid-to Date cannot be BEFORE Valid-from Date'))
            self.add_error('valid_from_date', forms.ValidationError('Valid-to Date cannot be BEFORE Valid-from Date'))
        # end if

        if 'projected_cutover' in data and data['projected_cutover'] and data['projected_cutover'] < datetime.date.today():
            self.add_error('projected_cutover', forms.ValidationError('Projected Cutover date cannot be before current date'))

        if 'readiness_complete' in data and data['readiness_complete'] and not 0 <= data['readiness_complete'] <= 100:
            self.add_error('readiness_complete', forms.ValidationError('Must be >= 0 and <= 100'))
        # end if

        if 'baseline_impacted' in data and data['baseline_impacted']:
            oBase = Baseline.objects.filter(title__iexact=data['baseline_impacted'])
            if not oBase:
                self.add_error('baseline_impacted', forms.ValidationError('Baseline not found'))
            # end if
        # end if

        if 'configuration_designation' in data and data['configuration_designation'] and\
                'baseline_impacted' in data and data['baseline_impacted'] and not self.instance:
            if Header.objects.filter(configuration_designation__iexact=data['configuration_designation'])\
                    .filter(baseline_impacted__iexact=data['baseline_impacted']).filter(program=data['program']):
                self.add_error('configuration_designation', forms.ValidationError('Configuration already exists in specified Baseline'))
            # end if
        # end if

        # if data['configuration_status'] == 'In Process' and 'react_request' in data and data['react_request']:
        #     sQuery = "SELECT [req_id],[assigned_to],[customer_name],[sales_o],[sales_g],[sold_to_code]," +\
        #              "[ship_to_code],[bill_to_code],[pay_terms],[workgroup],[cu] FROM dbo.ps_requests" +\
        #              " WHERE [req_id] = %s AND [Modified_by] IS NULL"
        #     oCursor = connections['REACT'].cursor()
        #     oCursor.execute(sQuery, [data['react_request']])
        #     oResults = oCursor.fetchall()
        #     if oResults:
        #         tREACT = oResults[0]
        #         if tREACT[1][:-13].replace('.',' ') != data.get('person_responsible', None):
        #             self.add_error('person_responsible', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[2] != data.get('customer_name', None):
        #             self.add_error('customer_name', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[3].upper() != data.get('sales_office', None):
        #             self.add_error('sales_office', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[4].upper() != data.get('sales_group', None):
        #             self.add_error('sales_group', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if int(tREACT[5]) != data.get('sold_to_party', None):
        #             self.add_error('sold_to_party', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if int(tREACT[6]) != data.get('ship_to_party', None):
        #             self.add_error('ship_to_party', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if int(tREACT[7]) != data.get('bill_to_party', None):
        #             self.add_error('bill_to_party', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[8] != data.get('payment_terms', None):
        #             self.add_error('payment_terms', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[9] != data.get('workgroup', None):
        #             self.add_error('workgroup', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #         if tREACT[10] != data.get('customer_unit', None):
        #             self.add_error('customer_unit', forms.ValidationError('Does not match REACT request data'))
        #         # end if
        #     else:
        #         self.add_error('react_request', forms.ValidationError('Invalid REACT request number'))
        #     # end if
        # # end if

        oCursor = connections['BCAMDB'].cursor()
        sQuery = ("SELECT [Sales Office Description], t1.[Sales Office], [Sales Group]"
                  " FROM dbo.REF_SALES_OFFICE t1 INNER JOIN dbo.REF_SALES_GROUP t2"
                  " ON t1.[Sales Office] = t2.[Sales Office]"
                  " WHERE [Sales Office Description] = %s")

        if 'customer_unit' in data and data['customer_unit']:
            oCursor.execute(sQuery, [REF_CUSTOMER.objects.get(name=data['customer_unit']).name])
            oResults = oCursor.fetchall()
            if 'sales_office' in data and data['sales_office']:
                if (REF_CUSTOMER.objects.get(name=data['customer_unit']).name, data['sales_office']) not in [(obj[0],obj[1]) for obj in oResults]:
                    self.add_error('sales_office', forms.ValidationError('No such sales office for customer unit. Make sure to only use "US##" values'))
            if 'sales_group' in data and data['sales_group']:
                if (REF_CUSTOMER.objects.get(name=data['customer_unit']).name, data['sales_group']) not in [(obj[0],obj[2]) for obj in oResults]:
                    self.add_error('sales_group', forms.ValidationError('No such sales group for customer unit. Make sure to only use group code'))
            # end if
        # end if

        return data
    # end def
# end def


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Configuration
        exclude = ['header']
    # end class

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.fields['net_value'].widget.attrs['readonly'] = 'True'
        self.fields['zpru_total'].widget.attrs['readonly'] = 'True'
    # end def

    def clean(self):
        data = super().clean()
        if data['needs_zpru'] and data['net_value'] != data['zpru_total']:
            raise forms.ValidationError('Net / ZPRU total mismatch')
        # end if
    # end def
# end class


class DateForm(forms.Form):
    date = forms.DateField(input_formats=['%b. %d, %Y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d %Y', '%b %d, %Y',
                                          '%d %b %Y', '%d %b, %Y', '%B %d %Y', '%B %d, %Y', '%d %B %Y', '%d %B, %Y'])
# end class


class FileUploadForm(forms.Form):

    file = forms.FileField()

    def clean(self):
        data = super().clean()
        aAllowedExtensions = ('.xls', '.xlsx', '.xlsm', '.xlsb')
        sExt = os.path.splitext(data['file'].name)[1]
        if sExt not in aAllowedExtensions:
            raise forms.ValidationError("File specified is not an allowed file type.")
        # end if
    # end def
# end class


class SubmitForm(forms.Form):
    baseline_title = forms.CharField(max_length=50, label='Baseline')

    def clean(self):
        data = super().clean()

        if 'baseline_title' in data:
            try:
                Baseline.objects.get(title__iexact=data['baseline_title'])
            except Baseline.DoesNotExist:
                self.add_error('baseline_title', forms.ValidationError('No matching Baseline found'))
            # end try
        # end if

        return data
# end class


class LinePricingForm(forms.ModelForm):
    class Meta:
        model = LinePricing
        fields = '__all__'
    # end class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If this is not a new LinePricing instance (add in admin)
        if self.instance.id:
            self.fields['config_line'].widget.choices = [(self.instance.config_line.id, str(self.instance.config_line))]
            self.fields['pricing_object'].widget.choices = [('', '--------')] + [(obj.id, str(obj)) for obj in PricingObject.objects.filter(
                is_current_active=True, part=self.instance.config_line.part.base)]
        # end if
    # end def
# end class


class AutocompleteInput(forms.TextInput):
    def __init__(self, name, choices=(), *args, **kwargs):
        super(AutocompleteInput, self).__init__(*args, **kwargs)
        self._name = name
        self._choices = choices
        self.attrs.update({'list': 'list_{}'.format(self._name)})
    # end def

    def render(self, name, value, attrs=None):
        input_html = super(AutocompleteInput, self).render(name, value, attrs=attrs)
        datatlist_html = '<datalist id="list_{}">'.format(self._name)
        for item in self._choices:
            if isinstance(item, (list, tuple)):
                datatlist_html += '<option data-value="{}" value="{}">{}</option>'.format(item[0], item[1], item[2])
            else:
                datatlist_html += '<option value="{}"/>'.format(item)
        # end for

        return mark_safe(input_html + datatlist_html)
# end class


class DistroForm(forms.ModelForm):
    class Meta:
        model = DistroList
        fields = '__all__'
        widgets = {
            'users_included': FilteredSelectMultiple('Users', False)
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['customer_unit'].widget.attrs['disabled'] = 'True'
            self.fields['customer_unit'].widget.attrs['style'] = 'border:none;-webkit-appearance:none;'

        self.fields['users_included'].queryset = User.objects.filter(groups__name__istartswith='BOM')\
            .exclude(groups__name__istartswith='BOM_BPMA').distinct()
        self.fields['users_included'].label_from_instance = lambda y:"%s" % (y.get_full_name())
# end class


class SecurityForm(forms.ModelForm):
    class Meta:
        model=SecurityPermission
        fields='__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label_from_instance = lambda inst: "%s" % (inst.name.replace('BOM_','').replace('_',' - ', 1).replace('_',' '))
    # end def
# end class


class UserForm(forms.Form):
    signum = forms.CharField(min_length=7, label='User SIGNUM')
    first_name = forms.CharField(label='First Name')
    last_name = forms.CharField(label='Last Name')
    email = forms.EmailField(label='Ericsson Email')
    assigned_group = forms.ModelMultipleChoiceField(Group.objects.filter(name__startswith='BOM_')
                                            .exclude(name__contains='BPMA')
                                            .exclude(name__contains='SuperApprover'), label='Assigned Group')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['signum'].widget.attrs['readonly'] = 'True'
        self.fields['signum'].widget.attrs['style'] = 'border: none;'
        self.fields['assigned_group'].label_from_instance = lambda inst: "%s" % (inst.name.replace('BOM_', '').replace('_', ' - ', 1).replace('_', ' '))

    def clean_email(self):
        if not self.cleaned_data['email'].lower().endswith('@ericsson.com'):
            raise forms.ValidationError('Email address must be an Ericsson email address')

        return self.cleaned_data['email']
# end class


class UserAddForm(forms.Form):
    signum = forms.CharField(min_length=7, required=True, label='User SIGNUM')

    def clean_signum(self):
        submitted_signum = self.cleaned_data['signum']
        try:
            testUser = User.objects.get(username=submitted_signum)
            if testUser.groups.filter(name__startswith='BOM'):
                raise forms.ValidationError("User already exists in the tool")
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        return submitted_signum
# end class
