"""
Classes used to create web forms in Django pages/views
"""

from django import forms
from django.db import connections
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User, Group
from django.contrib.admin.widgets import FilteredSelectMultiple

from BoMConfig.models import Header, Configuration, Baseline, REF_CUSTOMER, \
    LinePricing, PricingObject, DistroList, SecurityPermission, \
    HeaderTimeTracker, ApprovalList

import datetime
import os
import re


class HeaderForm(forms.ModelForm):
    """
    Header form, used in creation of Header objects
    """
    class Meta:
        """
        Metadata for HeaderForm object
        """
        model = Header
        exclude = ['internal_notes', 'external_notes', 'baseline_version',
                   'bom_version', 'release_date', 'change_notes',
                   'change_comments', 'baseline', 'old_configuration_status']
        widgets = {'model_replaced_link': forms.HiddenInput()}
    # end class

    def __init__(self, *args, **kwargs):
        bReadOnly = kwargs.pop('readonly', False)
        sBrowser = kwargs.pop('browser', None)

        # Alter "Inquiry/Site template number" field to reflect any in-progress
        # updates.  Only occurs for existing Header instances
        if 'instance' in kwargs and kwargs['instance'] and \
                kwargs['instance'].inquiry_site_template:
            if kwargs['instance'].inquiry_site_template == -1:
                kwargs.update(initial={'inquiry_site_template': '(Pending)'})
            elif kwargs['instance'].inquiry_site_template < -1:
                kwargs.update(
                    initial={
                        'inquiry_site_template': str(
                            kwargs['instance'].inquiry_site_template
                        )[1:] + ' (Pending Update)'})
            # end if
        # end if

        super().__init__(*args, **kwargs)

        self.fields['configuration_status'].widget.attrs['readonly'] = True
        self.fields['configuration_status'].widget.attrs['disabled'] = 'True'
        self.fields['configuration_status'].widget.attrs['style'] = \
            'border:none;'
        self.fields['configuration_status'].widget.attrs['style'] += \
            '-webkit-appearance:none;'

        self.fields['readiness_complete'].widget.attrs['readonly'] = True
        self.fields['readiness_complete'].widget.attrs['style'] = 'border:none;'
        self.fields['readiness_complete'].widget.attrs['style'] += \
            '-webkit-appearance:none;'

        self.fields['react_request'].widget.attrs['size'] = 25
        self.fields['model_description'].widget.attrs['size'] = 45

        # if inquiry/site template change is in-progress, make field readonly
        if self.instance.inquiry_site_template and \
                self.instance.inquiry_site_template < 0:
            self.fields['inquiry_site_template'] = forms.CharField()
            self.fields['inquiry_site_template'].widget.attrs['readonly'] = True
            self.fields['inquiry_site_template'].widget.attrs['style'] = \
                'border:none;'
        # end if

        # If the form is readonly or instance is in any status other than
        # "In process", make ALL fields readonly
        if bReadOnly or (hasattr(self.instance, 'configuration_status') and
                         self.instance.configuration_status.name != 'In Process'
                         ):
            for field in self.fields.keys():
                self.fields[field].widget.attrs['readonly'] = True
                self.fields[field].widget.attrs['style'] = 'border:none;'
                if self.initial:
                    if self.initial[field] and isinstance(
                            self.initial[field], str):
                        self.fields[field].widget.attrs['size'] = len(
                            self.initial[field]) + 5

                if isinstance(self.fields[field].widget,
                              (forms.widgets.Select,
                               forms.widgets.CheckboxInput)):
                    self.fields[field].widget.attrs['disabled'] = 'True'
                    if isinstance(self.fields[field].widget,
                                  forms.widgets.Select):
                        self.fields[field].widget.attrs['style'] += \
                            '-webkit-appearance:none;'
            # end for
        else:
            # Build list of existing Active headers, for use in
            # "What model is this replacing?" autoComplete field
            self.fields['model_replaced'].widget = AutocompleteInput(
                'header_list',
                sBrowser,
                list([(head.id,
                       head.configuration_designation +
                       (" (" + str(head.program) + ")" if head.program else ''),
                       (str(head.baseline.baseline.title) if head.baseline else
                        '')
                       ) for head in Header.objects.filter(
                    configuration_status__name='Active')]),
                attrs=self.fields['model_replaced'].widget.attrs
            )
        # end if
    # end def

    def clean(self):
        """
        Checks form data for validity
        :return: dictionary containing "cleaned" data
        """
        data = super().clean()

        data['sales_office'] = data['sales_office'].upper()
        data['sales_group'] = data['sales_group'].upper()

        # Remove any field errors generated by parent class function, since the
        # object is readonly and cannot be changed
        if self.fields['bom_request_type'].widget.attrs.get(
                'disabled', None) == 'True':
            keys = [key for key in self.errors]
            for key in keys:
                del self.errors[key]
            # end for
            return data

        # Ensure tool-generated "CLONE" tags have been removed from
        # configuration name, check name validity, and ensure acceptable length
        if 'configuration_designation' in data:
            if re.search(r"_+CLONE\d*_*$",
                         data['configuration_designation'].upper()):
                self.add_error(
                    'configuration_designation',
                    forms.ValidationError(
                        'Cloned configurations require rename ("_CLONE" still in name)'))
            elif data['configuration_designation'].upper().endswith('_'):
                self.add_error(
                    'configuration_designation',
                    forms.ValidationError(
                        'Configuration designation cannot end with underscore ("_")'))
            elif len(data['configuration_designation']) > 18 and not \
                    data['pick_list']:
                self.add_error(
                    'configuration_designation',
                    forms.ValidationError(
                        'Configuration title exceeds 18 characters'))
        # end if

        # Ensure Model (which should mirror name) is correct length for SAP
        # storage
        if 'model' in data and len(data['model']) > 18 and not \
                data['pick_list']:
            self.add_error(
                'model',
                forms.ValidationError('Model title exceeds 18 characters'))
        # end if

        # Ensure that if valid-to and valid-from are both provided, valid-from
        # is before valid-to
        if 'valid_to_date' in data and 'valid_from_date' in data and \
                data['valid_to_date'] and data['valid_from_date'] and \
                data['valid_to_date'] < data['valid_from_date']:
            self.add_error(
                'valid_to_date',
                forms.ValidationError(
                    'Valid-to Date cannot be BEFORE Valid-from Date'))
            self.add_error(
                'valid_from_date',
                forms.ValidationError(
                    'Valid-to Date cannot be BEFORE Valid-from Date'))
        # end if

        # Ensure that if projected cutover is provided, it is a future date
        if 'projected_cutover' in data and data['projected_cutover'] and \
                data['projected_cutover'] < datetime.date.today():
            self.add_error(
                'projected_cutover',
                forms.ValidationError(
                    'Projected Cutover date cannot be before current date'))

        # Ensure readiness complete is a positive value between, and including,
        # 0 and 100
        if 'readiness_complete' in data and data['readiness_complete'] and \
                not 0 <= data['readiness_complete'] <= 100:
            self.add_error(
                'readiness_complete',
                forms.ValidationError('Must be >= 0 and <= 100'))
        # end if

        # Ensure specified baseline exists
        if 'baseline_impacted' in data and data['baseline_impacted']:
            oBase = Baseline.objects.filter(
                title__iexact=data['baseline_impacted'])
            if not oBase:
                self.add_error(
                    'baseline_impacted',
                    forms.ValidationError('Baseline not found'))
            # end if
        # end if

        # Ensure configuration with this name and program does not already exist
        # in the baseline, if specified.  This only occurs when creating a new
        # record
        if 'configuration_designation' in data and \
                data['configuration_designation'] and 'baseline_impacted' in \
                data and data['baseline_impacted'] and not self.instance:
            if Header.objects.filter(
                    configuration_designation__iexact=data[
                        'configuration_designation']).filter(
                    baseline_impacted__iexact=data['baseline_impacted']).filter(
                    program=data['program']):
                self.add_error(
                    'configuration_designation',
                    forms.ValidationError(
                        'Configuration already exists in specified Baseline'))
            # end if
        # end if

        # Check customer unit corresponds to sales office and sales group
        # provided
        oCursor = connections['BCAMDB'].cursor()
        sQuery = ("SELECT [Sales Office Description], t1.[Sales Office], [Sales Group]"
                  " FROM dbo.REF_SALES_OFFICE t1 INNER JOIN dbo.REF_SALES_GROUP t2"
                  " ON t1.[Sales Office] = t2.[Sales Office]"
                  " WHERE [Sales Office Description] = %s")

        if 'customer_unit' in data and data['customer_unit']:
            oCursor.execute(sQuery, [bytes(REF_CUSTOMER.objects.get(
                name=data['customer_unit']).name, 'ascii')])
            oResults = oCursor.fetchall()
            if 'sales_office' in data and data['sales_office']:
                if (
                        REF_CUSTOMER.objects.get(
                        name=data['customer_unit']).name, data['sales_office']
                        ) not in [(obj[0], obj[1]) for obj in oResults]:
                    self.add_error(
                        'sales_office',
                        forms.ValidationError(
                            'No such sales office for customer unit. Make sure to only use "US##" values'))
            if 'sales_group' in data and data['sales_group']:
                if (
                        REF_CUSTOMER.objects.get(
                        name=data['customer_unit']).name, data['sales_group']
                        ) not in [(obj[0], obj[2]) for obj in oResults]:
                    self.add_error(
                        'sales_group',
                        forms.ValidationError(
                            'No such sales group for customer unit. Make sure to only use group code'))
            # end if
        # end if

        oCursor.close()

        # Set readiness complete value
        self.data._mutable = True
        if data['configuration_status'].name == 'In Process':
            if data['bom_request_type'].name == 'Preliminary':
                self.data['readiness_complete'] = 25
            else:
                self.data['readiness_complete'] = 50

                if hasattr(self.instance, 'configuration') and \
                        self.instance.configuration.ready_for_forecast:
                    self.data['readiness_complete'] = 70
        elif data['configuration_status'].name == 'In Process/Pending':
            self.data['readiness_complete'] = 90
        else:
            self.data['readiness_complete'] = 100
        self.data._mutable = False

        return data
    # end def
# end def


class ConfigForm(forms.ModelForm):
    """
    Used to create and edit Configuration objects
    """
    class Meta:
        """
        Metadata for ConfigForm object
        """
        model = Configuration
        exclude = ['header']
    # end class

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        self.fields['total_value'].widget.attrs['readonly'] = True
        self.fields['zpru_total'].widget.attrs['readonly'] = True
        self.fields['PSM_on_hold'].widget.attrs['readonly'] = True
    # end def

    def clean(self):
        """
        Function to clean inputs to ConfigForm
        :return: None
        """
        data = super().clean()

        # If record needs ZPRU validation (has ZPRU/ZPR1 condition) and the net
        # total and ZPRU total don't match, throw an error
        if data['needs_zpru'] and data['total_value'] != data['zpru_total']:
            raise forms.ValidationError('Net / ZPRU total mismatch')
        # end if
    # end def
# end class


class DateForm(forms.Form):
    """
    Used to validate and clean date field information
    """
    date = forms.DateField(input_formats=['%b. %d, %Y', '%Y-%m-%d', '%m/%d/%Y',
                                          '%m/%d/%y', '%b %d %Y', '%b %d, %Y',
                                          '%d %b %Y', '%d %b, %Y', '%B %d %Y',
                                          '%B %d, %Y', '%d %B %Y', '%d %B, %Y'])
# end class


class FileUploadForm(forms.Form):
    """
    Used to store and process file uploads (not the content of the file itself)
    """
    file = forms.FileField()

    def clean(self):
        """
        Function to clean/validate inputs to FileUploadForm
        :return:
        """
        data = super().clean()
        aAllowedExtensions = ('.xls', '.xlsx', '.xlsm', '.xlsb')
        sExt = os.path.splitext(data['file'].name)[1]
        if sExt not in aAllowedExtensions:
            raise forms.ValidationError(
                "File specified is not an allowed file type.")
        # end if
    # end def
# end class


class BaselineModelChoiceField(forms.ModelChoiceField):
    """
    Custom class to override how Baselines are displayed in dropdown menu for
    baseline management view
    """
    def label_from_instance(self, obj):
        return obj.title


class SubmitForm(forms.Form):
    """
    Form used during baseline management search to find baselines
    """
    baseline_title = BaselineModelChoiceField(
        queryset=Baseline.objects.exclude(title='No Associated Baseline'),
        empty_label="-- Show All --",
        required=False,
        label='Baseline')

    # def clean(self):
    #     """
    #     Function to clean/validate input data to SubmitForm
    #     :return:
    #     """
    #     data = super().clean()
    #
    #     if 'baseline_title' in data:
    #         try:
    #             Baseline.objects.get(title__iexact=data['baseline_title'])
    #         except Baseline.DoesNotExist:
    #             self.add_error('baseline_title',
    #                            forms.ValidationError(
    #                                'No matching Baseline found'))
    #         # end try
    #     # end if
    #
    #     return data
# end class


class LinePricingForm(forms.ModelForm):
    """
    Form used in administration of LinePricing objects
    """
    class Meta:
        """
        Metadata for LinePricingForm
        """
        model = LinePricing
        fields = '__all__'
    # end class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If this is not a new LinePricing instance (editing in admin), we do
        # want the user to be able to change which ConfigLine this object is
        # attached to, and we do not want the user to be able to assign an
        # inactive PricingObject, so limit to only active records for the part
        # stored in the ConfigLine
        if self.instance.id:
            self.fields['config_line'].widget.choices = [
                (self.instance.config_line.id, str(self.instance.config_line))]
            self.fields['pricing_object'].widget.choices = \
                [('', '--------')] + [(obj.id, str(obj)) for obj in
                                      PricingObject.objects.filter(
                                          is_current_active=True,
                                          part=self.instance.config_line.part.base
                                      )]
        # end if
    # end def
# end class


class AutocompleteInput(forms.TextInput):
    """
    Form input field that acts as an auto-completing text input field.
    As the user enters data into the field, a dropdown list attached to the
    field filters existing entries in "choices" to possible matches.

    ***HTML5 or better only***
    """
    def __init__(self, name, browser, choices=(), *args, **kwargs):
        super(AutocompleteInput, self).__init__(*args, **kwargs)
        self._name = name
        self._choices = choices
        self._browser = browser
        self.attrs.update({'list': 'list_{}'.format(self._name)})
    # end def

    def render(self, name, value, attrs=None):
        """
        Function to generate HTML to properly display an instance of this object
        :param name: String containing label of field
        :param value: String containing value of field
        :param attrs: Dictionary of field attributes
        :return: String containing HTML
        """
        # Firefox displays the options in "_choices" in a different way than
        # Chrome or IE, so we have to modify the displayed list a little
        if 'Firefox' in self._browser:
            iMinLength = 50
            for item in self._choices:
                if isinstance(item, (list, tuple)):
                    iMinLength = max(iMinLength, len(item[1] + item[2])+2)
                else:
                    iMinLength = max(iMinLength, len(item))
                # end if
            # end for

            attrs.update({'style': 'width: {}px'.format(iMinLength * 6 + 17)})
        # end if

        # Render the text input field, which is a standard text field
        input_html = super(AutocompleteInput, self).render(name, value,
                                                           attrs=attrs)

        # Render the datalist that associates to the text field.  This is what
        # displays the possible options
        datatlist_html = '<datalist id="list_{}">'.format(self._name)
        for item in self._choices:
            if isinstance(item, (list, tuple)):
                if 'Chrome' in self._browser:
                    datatlist_html += (
                        '<option data-value="{0}" value="{1}">{2}</option>'
                    ).format(item[0], item[1], item[2])
                else:
                    datatlist_html += (
                        '<option data-value="{0}" value="{1}">{1} - {2}'
                        '</option>'
                    ).format(item[0], item[1], item[2])
            else:
                datatlist_html += '<option value="{}"/>'.format(item)
        # end for

        return mark_safe(input_html + datatlist_html)
# end class


class DistroForm(forms.ModelForm):
    """
    Form for creation and editing of Distrolist objects
    """
    class Meta:
        """
        Metadata for DistroForm object
        """
        model = DistroList
        fields = '__all__'
        widgets = {
            'users_included': FilteredSelectMultiple('Users', False)
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this form has an existing instance attached, make customer unit a
        # readonly field
        if self.instance.id:
            self.fields['customer_unit'].widget.attrs['disabled'] = 'True'
            self.fields['customer_unit'].widget.attrs['style'] = \
                'border:none;-webkit-appearance:none;'

        # Limit the list of selectable users to only those users with access to
        # this tool
        self.fields['users_included'].queryset = User.objects.filter(
            groups__name__istartswith='BOM').exclude(
            groups__name__istartswith='BOM_BPMA').distinct()
        self.fields['users_included'].label_from_instance = \
            lambda y: "%s" % (y.get_full_name())
# end class


class SecurityForm(forms.ModelForm):
    """
    Form for creation and editing of SecurityPermission objects
    """
    class Meta:
        """
        Metadata for SecurityForm object
        """
        model = SecurityPermission
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label_from_instance = \
            lambda inst: "%s" % (
                inst.name.replace('BOM_', '').replace(
                    '_', ' - ', 1).replace('_', ' '))
    # end def
# end class


class UserForm(forms.Form):
    """
    Form for the editing of User objects
    """
    signum = forms.CharField(min_length=6, label='User SIGNUM')
    first_name = forms.CharField(label='First Name')
    last_name = forms.CharField(label='Last Name')
    email = forms.EmailField(label='Ericsson Email')
    assigned_group = forms.ModelMultipleChoiceField(
        Group.objects.filter(
            name__startswith='BOM_').exclude(
            name__contains='BPMA').exclude(name__contains='SuperApprover'),
        label='Assigned Group',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SIGNUM will always be readonly, as it cannot be changed.  Changes of
        # that type will have to be done in the Djanog user adminstration view
        self.fields['signum'].widget.attrs['readonly'] = True
        self.fields['signum'].widget.attrs['style'] = 'border: none;'
        self.fields['assigned_group'].label_from_instance = \
            lambda inst: "%s" % ((inst.name.replace('BOM_', '')
                                  .replace('_', ' - ', 1).replace('_', ' ')))

    def clean_email(self):
        """
        Function to clean/validate the email field of UserForm
        :return: String containing cleaned / validated version of value
        """
        # Ensure users can only add Ericsson emails to the tool
        if not self.cleaned_data['email'].lower().endswith('@ericsson.com'):
            raise forms.ValidationError(
                'Email address must be an Ericsson email address')

        return self.cleaned_data['email']
# end class


class UserAddForm(forms.Form):
    """
    Form for creating new User objects
    """
    signum = forms.CharField(min_length=6, required=True, label='User SIGNUM')

    def clean_signum(self):
        """
        Function to clean/validate the signum field of UserAddForm
        :return: String containing cleaned / validated version of value
        """
        submitted_signum = self.cleaned_data['signum']
        # Check to see if a user already exists with the provided SIGNUM
        try:
            testUser = User.objects.get(username=submitted_signum)
            if testUser.groups.filter(name__startswith='BOM'):
                raise forms.ValidationError("User already exists in the tool")
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        return submitted_signum
# end class


class CustomerApprovalLevelForm(forms.Form):
    """
    Form for the creation and editing of ApprovalList objects
    """
    customer = forms.ModelChoiceField(queryset=REF_CUSTOMER.objects.all())
    required_choices = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
    optional_choices = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
    disallowed_choices = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, **kwargs):
        self.readonly = kwargs.pop('readonly', False)
        super().__init__(*args, **kwargs)

        self.fields['customer'].widget.attrs['readonly'] = self.readonly

        if self.readonly:
            self.fields['customer'].widget.attrs['disabled'] = 'disabled'
            self.fields['customer'].widget.attrs['style'] = \
                'border:none;-webkit-appearance:none;'
        self.fields['required_choices'].choices = enumerate(
            HeaderTimeTracker.approvals()[1:-1], 1)
        self.fields['optional_choices'].choices = enumerate(
            HeaderTimeTracker.approvals()[1:-1], 1)
        self.fields['disallowed_choices'].choices = enumerate(
            HeaderTimeTracker.approvals()[1:-1], 1)

        # If this form is for a new object, limit the list of customers to only
        # those that do not already have an associated ApprovalList object
        if not self.readonly:
            self.fields['customer'].queryset = REF_CUSTOMER.objects.exclude(
                id__in=[app.customer.id for app in ApprovalList.objects.all()])
    # end def

    def clean(self):
        """
        Function to clean / validate data submitted inCustomerApprovalLevelForm
        :return: None
        """
        data = self.cleaned_data
        included_values = set(
            data['required_choices']
        ).union(set(data['optional_choices'])).union(
            set(data['disallowed_choices']))

        for index in range(1, len(HeaderTimeTracker.approvals())-1):
            if str(index) not in included_values:
                self.add_error(None, index)
    # end def
# end class
