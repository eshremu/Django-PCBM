from django.db import models
from django.contrib.sessions.models import Session
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

import re

# Create your models here.
class ParseException(Exception):
    pass


class OrderedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().order_by('name')
    # end def
# end class


class Alert(models.Model):
    Title = models.CharField(max_length=200, blank=True)
    Text = models.CharField(max_length=1000)
    PublishDate = models.DateTimeField('Date Published')

    def __str__(self):
        return self.Title
    # end def
# end class


class NewsItem(models.Model):
    Title = models.CharField(max_length=200)
    Text = models.CharField(max_length=1000)
    PublishDate = models.DateTimeField('Date Published')

    def __str__(self):
        return self.Title
    # end def
# end class


class REF_CUSTOMER(models.Model):
    class Meta:
        verbose_name = 'REF Customer'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_REQUEST(models.Model):
    class Meta:
        verbose_name = 'REF Request Type'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_TECHNOLOGY(models.Model):
    class Meta:
        verbose_name = 'REF Technology'
        verbose_name_plural = 'REF Technologies'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PRODUCT_AREA_1(models.Model):
    class Meta:
        verbose_name = 'REF Product Area'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PRODUCT_AREA_2(models.Model):
    class Meta:
        verbose_name = 'REF Sub-Product Area'
    # end class

    name = models.CharField(max_length=50)
    parent = models.ForeignKey(REF_PRODUCT_AREA_1)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_CUSTOMER_NAME(models.Model):
    class Meta:
        verbose_name = 'REF Customer Name'
    # end class

    name = models.CharField(max_length=200)
    parent = models.ForeignKey(REF_CUSTOMER)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PROGRAM(models.Model):
    class Meta:
        verbose_name = 'REF Program'
    # end class

    name = models.CharField(max_length=50)
    parent = models.ForeignKey(REF_CUSTOMER)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_CONDITION(models.Model):
    class Meta:
        verbose_name = 'REF Condition'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PRODUCT_PKG(models.Model):
    class Meta:
        verbose_name = 'REF Product Package Type'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_MATERIAL_GROUP(models.Model):
    class Meta:
        verbose_name = 'REF Material Group'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_SPUD(models.Model):
    class Meta:
        verbose_name = 'REF SPUD'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_RADIO_BAND(models.Model):
    class Meta:
        verbose_name = 'REF Radio Band'
    # end class

    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    # end def
# end class


class REF_RADIO_FREQUENCY(models.Model):
    class Meta:
        verbose_name = 'REF Radio Frequency'
        verbose_name_plural = 'REF Radio Frequencies'
    # end class

    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    # end def
# end class


class REF_STATUS(models.Model):
    class Meta:
        verbose_name = 'REF Status'
        verbose_name_plural = 'REF Statuses'
    # end class

    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Baseline(models.Model):
    title = models.CharField(max_length=50, unique=True)

    """ This is the overall baseline storage location.  This will up-rev with each revision
        A baseline up-revs when the baseline/any attached config has been changed and submitted for CUSTOMER approval"""
    # version = models.CharField(max_length=50)
    current_active_version = models.CharField(max_length=50, default='', blank=True)
    current_inprocess_version = models.CharField(max_length=50, default='A')
    customer = models.ForeignKey(REF_CUSTOMER, db_constraint=False)

    def save(self, *args, **kwargs):
        if self.title.lower().endswith(' rev'):
            self.title = self.title[:-4]
        # end if

        super().save(*args, **kwargs)

        if not self.baseline_revision_set.all():
            Baseline_Revision.objects.create(**{'baseline':self, 'version': self.current_inprocess_version})
        # end if
    # end def

    def __str__(self):
        return self.title+"_"+self.current_inprocess_version+"_"+self.current_active_version
    # end def

    @property
    def latest_revision(self):
        try:
            return Baseline_Revision.objects.get(baseline=self, version=self.current_active_version)
        except Baseline_Revision.DoesNotExist:
            return None
    # end def
# end class


class Baseline_Revision(models.Model):
    class Meta:
        verbose_name = 'Baseline Revision'
    # end class

    baseline = models.ForeignKey(Baseline, db_constraint=False)
    version = models.CharField(max_length=50, default='A')
    completed_date = models.DateField(blank=True, null=True)
    previous_revision = models.ForeignKey('Baseline_Revision', blank=True, null=True, related_name='next_revision')

    @property
    def title(self):
        return self.baseline.title
    # end def

    @property
    def customer(self):
        return self.baseline.customer
    # end def

    def __str__(self):
        return self.title + " Rev " + self.version + (' ' + self.completed_date.strftime('%m%d%y') + 'C' if self.completed_date else '')
    # end def
# end class


class Header(models.Model):
    person_responsible = models.CharField(max_length=50, verbose_name='Person Responsible')
    react_request = models.CharField(max_length=25, verbose_name='REACT Request', blank=True, null=True)
    bom_request_type = models.ForeignKey(REF_REQUEST, verbose_name='BoM Request Type', db_constraint=False)
    customer_unit = models.ForeignKey(REF_CUSTOMER, verbose_name='Customer Unit', db_constraint=False)
    customer_name = models.CharField(max_length=50, verbose_name='Customer Name', blank=True, null=True)
    sales_office = models.CharField(max_length=50, verbose_name='Sales Office', blank=True, null=True)
    sales_group = models.CharField(max_length=50, verbose_name='Sales Group', blank=True, null=True)
    sold_to_party = models.IntegerField(verbose_name='Sold-to Party', blank=True, null=True)
    ship_to_party = models.IntegerField(verbose_name='Ship-to Party', blank=True, null=True)
    bill_to_party = models.IntegerField(verbose_name='Bill-to Party', blank=True, null=True)
    ericsson_contract = models.IntegerField(verbose_name='Ericsson Contract #', blank=True, null=True)
    payment_terms = models.CharField(max_length=50, verbose_name='Payment Terms', blank=True, null=True)
    projected_cutover = models.DateField(verbose_name='Projected Cut-over Date', blank=True, null=True)
    program = models.ForeignKey(REF_PROGRAM, verbose_name='Program', blank=True, null=True, db_constraint=False)
    configuration_designation = models.CharField(max_length=50, verbose_name='Configuration')
    customer_designation = models.CharField(max_length=50, verbose_name='Customer Designation', blank=True, null=True)
    technology = models.ForeignKey(REF_TECHNOLOGY, verbose_name='Technology', blank=True, null=True, db_constraint=False)
    product_area1 = models.ForeignKey(REF_PRODUCT_AREA_1, verbose_name='Product Area 1', blank=True, null=True, db_constraint=False)
    product_area2 = models.ForeignKey(REF_PRODUCT_AREA_2, verbose_name='Product Area 2', blank=True, null=True, db_constraint=False)
    radio_frequency = models.ForeignKey(REF_RADIO_FREQUENCY, verbose_name='Radio Frequency', blank=True, null=True, db_constraint=False)
    radio_band = models.ForeignKey(REF_RADIO_BAND, verbose_name='Radio Band', blank=True, null=True, db_constraint=False)
    optional_free_text1 = models.CharField(max_length=50, verbose_name='Optional Free Text Field 1', blank=True, null=True)
    optional_free_text2 = models.CharField(max_length=50, verbose_name='Optional Free Text Field 2', blank=True, null=True)
    optional_free_text3 = models.CharField(max_length=50, verbose_name='Optional Free Text Field 3', blank=True, null=True)
    inquiry_site_template = models.IntegerField(verbose_name='Inquiry/Site Template #', blank=True, null=True)
    readiness_complete = models.IntegerField(verbose_name='Readiness Complete (%)', blank=True, null=False, default=0)
    complete_delivery = models.BooleanField(verbose_name='Complete Delivery', default=True)
    no_zip_routing = models.BooleanField(default=False, verbose_name='No ZipRouting')
    valid_from_date = models.DateField(verbose_name='Valid-from Date', blank=True, null=True)
    valid_to_date = models.DateField(verbose_name='Valid-to Date', blank=True, null=True)
    shipping_condition = models.CharField(max_length=50, verbose_name='Shipping Condition', blank=True, null=True, default='71')
    baseline_impacted = models.CharField(max_length=50, verbose_name='Baseline Impacted', blank=True, null=True)
    model = models.CharField(max_length=50, verbose_name='Model', blank=True, null=True)
    model_description = models.CharField(max_length=50, verbose_name='Model Description', blank=True, null=True)
    model_replaced = models.CharField(max_length=50, verbose_name='What Model is this replacing?', blank=True, null=True)
    model_replaced_link = models.ForeignKey('Header', related_name='replaced_by_model', blank=True, null=True)
    initial_revision = models.CharField(max_length=50, verbose_name='Initial Revision', blank=True, null=True)  # This is the root model
    configuration_status = models.ForeignKey(REF_STATUS, verbose_name='Configuration/Ordering Status',
                                             default=1, db_index=False,
                                             db_constraint=False, unique=False)
    old_configuration_status = models.ForeignKey(REF_STATUS, default=None, related_name='old_status', db_index=False,
                                                 db_constraint=False, unique=False, null=True, blank=True)
    workgroup = models.CharField(max_length=50, verbose_name='Workgroup', blank=True, null=True)
    name = models.CharField(max_length=50, verbose_name='Name', blank=True, null=True)
    pick_list = models.BooleanField(default=False, blank=True)
    internal_notes = models.TextField(blank=True, null=True)
    external_notes = models.TextField(blank=True, null=True)

    """This is the config-specific storage location.  This will up-rev with each revision, as long as the config is not discontinued
        A new config will have to be saved each time a revision happens, but if a config is discontinued, don't save a new one
        When a baseline is searched, pull all configs that have the same revision"""
    baseline_version = models.CharField(max_length=50, blank=True, null=True)
    bom_version = models.CharField(max_length=50, blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    change_notes = models.TextField(blank=True, null=True)
    change_comments = models.TextField(blank=True, null=True)
    baseline = models.ForeignKey(Baseline_Revision, blank=True, null=True)

    class Meta:
        unique_together = ['configuration_designation', 'baseline_version', 'baseline', 'program']
    # end class

    def __str__(self):
        return self.configuration_designation + ("_{}".format(self.program.name) if self.program else '') + ("__" + self.baseline_version if self.baseline_version else '')
    # end def

    def save(self, *args, **kwargs):
        bMessage = kwargs.pop('alert', True)
        oRequest = kwargs.pop('request', None)
        if not self.pk:
            oBase = Baseline.objects.filter(title__iexact=self.baseline_impacted)

            if oBase and not self.baseline:
                self.baseline = Baseline_Revision.objects.get(baseline=oBase[0],version=oBase[0].current_inprocess_version)
                self.baseline_version = self.baseline.version
            # end if

            if self.baseline_version in (None, ''):
                self.baseline_version = 'A'

            if self.bom_version in (None, ''):
                self.bom_version = '1'
        else: # Update existing Header
            if self.configuration_status.name == 'In Process':
                if self.baseline:
                    self.baseline_version = self.baseline.version
                # end if

                if self.baseline and not self.baseline_impacted:
                    self.baseline = None
                elif (not self.baseline and self.baseline_impacted) or (self.baseline and self.baseline.baseline.title != self.baseline_impacted):
                    sLastRev = Baseline.objects.get(title=self.baseline_impacted).current_inprocess_version
                    self.baseline = Baseline_Revision.objects.get(baseline=Baseline.objects.get(title=self.baseline_impacted),version=sLastRev)
                    self.baseline_version = sLastRev
                # end if
            # end if
        # end if

        iPrevRC = self.readiness_complete
        if self.configuration_status.name == 'In Process':
            if self.bom_request_type.name == 'Preliminary':
                self.readiness_complete = 25
            else:
                self.readiness_complete = 50

                if hasattr(self, 'configuration') and self.configuration.ready_for_forecast:
                    self.readiness_complete = 70
                    if bMessage and iPrevRC < self.readiness_complete:
                        # aRecips = User.objects.filter(groups__securitypermission__title__in=HeaderTimeTracker.permission_entry('scm1')).values_list('email', flat=True)
                        aRecips = User.objects.filter(groups__name__in=['BOM_Forecast/Demand_Demand_Manager']).values_list('email', flat=True)
                        oMessage = EmailMultiAlternatives(subject='Review for Forecast Readiness',
                                                          body=('Hello SCM user,\n\n'
                                                                'Log into the PSM Configuration & Baseline Management (PCBM) tool to review the following Configuration for forecast readiness.'
                                                                'Attached is a copy for your convenience and discussion with Forecasting and Commodity Planning.'
                                                                'This Configuration is currently at 70% Readiness Complete.\n\n'
                                                                '\t{} - {} - {}\n\n'
                                                                'If there are questions, please contact the appropriate Configuration Manager.'
                                                                'You can locate this information on the "Header" tab of the attacher Configuration file.\n\n'
                                                                'PCBM Link: https://rnamsupply.internal.ericsson.com/pcbm').format(self.configuration_designation,
                                                                                                                                   self.baseline_impacted or '',
                                                                                                                                   self.react_request or ''),
                                                          from_email='pcbm.admin@ericsson.com',
                                                          to=aRecips,
                                                          cc=[oRequest.user.email] if oRequest else None)
                        oMessage.attach_alternative(('<html lang="en"><head><meta charset="UTF-8"><title>Configuration {0}</title>'
                                                     '<style>body {{font-family: "Calibri", sans-serif;font-size: 11pt;}}'
                                                     'a {{font-style: italic;font-weight: bold;}}</style></head><body><p>Hello SCM user,</p>'
                                                     '<p>Log into the PSM Configuration & Baseline Management (PCBM) tool to review the following Configuration for forecast readiness.'
                                                     'Attached is a copy for your convenience and discussion with Forecasting and Commodity Planning.'
                                                     'This Configuration is currently at 70% Readiness Complete.</p>'
                                                     '<ul><li>{0} - {1} - {2}</li></ul>'
                                                     '<p>If there are questions, please contact the appropriate Configuration Manager.'
                                                     'You can locate this information on the "Header" tab of the attacher Configuration file.</p>'
                                                     '<p>PCBM Link: <a href="https://rnamsupply.internal.ericsson.com/pcbm">'
                                                     'https://rnamsupply.internal.ericsson.com/pcbm</a></p></body></html>').format(self.configuration_designation,
                                                                                                                        self.baseline_impacted or '',
                                                                                                                        self.react_request or ''), 'text/html')

                        from BoMConfig.views.download import WriteConfigToFile
                        from io import BytesIO
                        oStream = BytesIO()
                        WriteConfigToFile(self).save(oStream)
                        oMessage.attach(filename=self.configuration_designation + ('_' + self.program.name if self.program else '') + '.xlsx',
                                        content=oStream.getvalue(),
                                        mimetype='application/ms-excel')

                        oMessage.send()
                    # end if
                # end if
            # end if
        elif self.configuration_status.name == 'In Process/Pending':
            self.readiness_complete = 90
        else:
            self.readiness_complete = 100
        # end if

        super().save(*args, **kwargs)
        if not hasattr(self, 'headertimetracker_set') or not self.headertimetracker_set.all():
            HeaderTimeTracker.objects.create(**{'header':self})
        # end if

        if not hasattr(self, 'headerlock'):
            HeaderLock.objects.create(**{'header': self})
        # end if
    # end def

    @property
    def latesttracker(self):
        if self.headertimetracker_set:
            return self.headertimetracker_set.order_by('-submitted_for_approval')[0]

        return None
    # end def

    def get_all_trackers(self):
        if self.headertimetracker_set:
            return self.headertimetracker_set.order_by('-submitted_for_approval')

        return None
    # end def

    @property
    def check_date(self):
        if self.valid_from_date and self.valid_to_date:
            return self.valid_from_date + timezone.timedelta(seconds=(self.valid_to_date - self.valid_from_date).total_seconds()/2)
        elif not self.valid_from_date and self.valid_to_date:
            return self.valid_to_date - timezone.timedelta(days=1)
        elif self.valid_from_date and not self.valid_to_date:
            return self.valid_from_date + timezone.timedelta(days=1)
        elif not self.valid_from_date and not self.valid_to_date:
            return timezone.now().date()

    @property
    def site_template_eligible(self):
        if self.configuration:
            for oLine in self.configuration.configline_set.all():
                if oLine.item_category in ['ZBIL', 'ZERV']:
                    return False
        return True

    @property
    def inquiry_eligible(self):
        return True

    # @property
    # def site_template_eligible(self):
    #     if self.configuration:
    #         for oLine in self.configuration.configline_set.all():
    #             if oLine.item_category not in ['', 'ZSBS', 'ZSBU', 'ZSBT',
    #                                            'ZSXS',
    #                                            'ZSBM', 'ZF36', 'ZMX4', 'ZSW7',
    #                                            None]:
    #                 return False
    #             if oLine.higher_level_item in ('', None):
    #                 return False
    #     return True
    #
    # @property
    # def inquiry_eligible(self):
    #     if self.configuration:
    #         for oLine in self.configuration.configline_set.all():
    #             if oLine.item_category not in ['', 'ZTBI', 'ZI36', 'ZTNI',
    #                                            'ZSXI',
    #                                            'ZTFI', 'ZI25', 'ZAFP', 'ZSW7',
    #                                            None]:
    #                 return False
    #             if oLine.higher_level_item not in ('', None):
    #                 return False
    #     return True

    @property
    def latestdocrequest(self):
        return self.documentrequest_set.all().order_by('-new_req').first()
# end class


class Configuration(models.Model):
    ready_for_forecast = models.BooleanField(default=False, verbose_name="Ready for Forecast")
    PSM_on_hold = models.BooleanField(default=False, verbose_name="PSM On Hold?")
    internal_external_linkage = models.BooleanField(default=False, verbose_name="Internal/External Linkage")
    net_value = models.FloatField(blank=True, null=True, verbose_name="Net Value")
    override_net_value = models.FloatField(blank=True, null=True, verbose_name="Overriden Net Value")
    total_value = models.FloatField(blank=True, null=True, verbose_name="Total Net Value")
    zpru_total = models.FloatField(blank=True, null=True, verbose_name="ZPRU Total")
    header = models.OneToOneField(Header)
    needs_zpru = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.PSM_on_hold and self.header.configuration_status.name != 'On Hold':
            self.header.old_configuration_status = self.header.configuration_status
            self.header.configuration_status = REF_STATUS.objects.get(name='On Hold')
        elif not self.PSM_on_hold and self.header.old_configuration_status is not None:
            self.header.configuration_status = self.header.old_configuration_status
            self.header.old_configuration_status = None
        # end if
        self.header.save(request=kwargs.pop('request', None))

        super().save(*args, **kwargs)
    # end def

    def __str__(self):
        return self.title + ("__" + self.header.baseline_version if self.header.baseline_version else '')
    # end def

    def get_first_line(self):
        oFirst = None
        try:
            oFirst = self.configline_set.get(line_number='10')
        except ConfigLine.DoesNotExist:
            pass
        # end try
        return oFirst
    # end def

    @property
    def first_line(self):
        return self.get_first_line()

    @property
    def title(self):
        return self.header.configuration_designation

    @property
    def version(self):
        return self.header.baseline_version or '(Not baselined)'
# end class


class PartBase(models.Model):
    product_number = models.CharField(max_length=50, unique=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.product_number
    # end def
# end class


class Part(models.Model):
    product_description = models.CharField(max_length=100, blank=True, null=True)
    base = models.ForeignKey(PartBase, blank=True, null=True)

    class Meta:
        unique_together = ('product_description', 'base')
    # end class

    def __str__(self):
        return str(self.pk) + " - " + self.product_number + " - " + (self.product_description if self.product_description else '(None)')
    # end def

    @property
    def product_number(self):
        return self.base.product_number

    @property
    def description(self):
        return self.product_description or '(None)'
# end class


class ConfigLine(models.Model):
    line_number = models.CharField(max_length=50)
    order_qty = models.FloatField(blank=True, null=True)
    plant = models.CharField(max_length=50, blank=True, null=True)
    sloc = models.CharField(max_length=50, blank=True, null=True)
    item_category = models.CharField(max_length=50, blank=True, null=True)
    # spud = models.CharField(max_length=50, blank=True, null=True)
    spud = models.ForeignKey(REF_SPUD, blank=True, null=True, unique=False, db_constraint=False, db_index=False)
    internal_notes = models.TextField(blank=True, null=True)
    higher_level_item = models.CharField(max_length=50, blank=True, null=True)
    material_group_5 = models.CharField(max_length=50, blank=True, null=True)
    purchase_order_item_num = models.CharField(max_length=50, blank=True, null=True)
    condition_type = models.CharField(max_length=50, blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    customer_asset = models.CharField(max_length=50, blank=True, null=True)
    customer_asset_tagging = models.CharField(max_length=50, blank=True, null=True)
    customer_number = models.CharField(max_length=50, blank=True, null=True)
    sec_customer_number = models.CharField(max_length=50, blank=True, null=True)
    vendor_article_number = models.CharField(max_length=50, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    additional_ref = models.TextField(blank=True, null=True)
    config = models.ForeignKey(Configuration)
    part = models.ForeignKey(Part)
    is_child = models.BooleanField(default=False)
    is_grandchild = models.BooleanField(default=False)
    pcode = models.CharField(max_length=100, blank=True, null=True)
    commodity_type = models.CharField(max_length=50, blank=True, null=True)
    package_type = models.CharField(max_length=50, blank=True, null=True)
    REcode = models.CharField(max_length=50, blank=True, null=True)
    mu_flag = models.CharField(max_length=50, blank=True, null=True)
    x_plant = models.CharField(max_length=50, blank=True, null=True)
    traceability_req = models.CharField(max_length=50, blank=True, null=True)  # TODO: Move to CustomerPartInfo (when built)
    last_updated = models.DateTimeField(blank=True, null=True)
    contextId = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return str(self.config) + "_" + self.line_number
    # end def

    @property
    def title(self):
        return self.config.title

    @property
    def version(self):
        return self.config.version
# end class


class RevisionHistory(models.Model):
    revision = models.CharField(max_length=50)
    baseline = models.ForeignKey(Baseline)
    history = models.TextField()

    class Meta:
        unique_together = ('revision', 'baseline')
    # end class

    def __str__(self):
        return str(self.baseline) + "_" + self.revision
    # end def

    @property
    def title(self):
        return self.baseline.title
# end class


class LinePricing(models.Model):
    # unit_price = models.FloatField(blank=True, null=True)
    override_price = models.FloatField(blank=True, null=True)
    pricing_object = models.ForeignKey('PricingObject', null=True)
    config_line = models.OneToOneField(ConfigLine)

    def __str__(self):
        return str(self.config_line) + ("_" + str(self.pricing_object.unit_price) if self.pricing_object else '')
    # end def

    @property
    def configuration_designation(self):
        return self.config_line.config.header.configuration_designation

    @property
    def version(self):
        try:
            return self.config_line.config.header.baseline.version
        except AttributeError:
            return

    @property
    def line_number(self):
        return self.config_line.line_number
# end class


class PricingObject(models.Model):
    unit_price = models.FloatField(blank=True, null=True, default=0.0)
    # override_price = models.FloatField(blank=True, null=True)
    customer = models.ForeignKey(REF_CUSTOMER, to_field='id')
    sold_to = models.IntegerField(blank=True, null=True)
    spud = models.ForeignKey(REF_SPUD, to_field='id', null=True, blank=True)
    part = models.ForeignKey(PartBase, to_field='id')
    date_entered = models.DateTimeField(default=timezone.now)
    previous_pricing_object = models.ForeignKey('PricingObject', null=True, blank=True)
    is_current_active = models.BooleanField(default=False)
    cutover_date = models.DateField(null=True, blank=True)
    valid_from_date = models.DateField(null=True, blank=True)
    valid_to_date = models.DateField(null=True, blank=True)
    price_erosion = models.BooleanField(default=False)
    erosion_rate = models.FloatField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    technology = models.ForeignKey(REF_TECHNOLOGY, to_field='id', null=True, blank=True)

    def __str__(self):
        return str(self.part) + "_" + str(self.customer) + "_" + str(self.sold_to) + "_" + str(self.spud) + "_" + self.date_entered.strftime('%m/%d/%Y')

    @classmethod
    def getClosestMatch(cls, oConfigLine):
        if not isinstance(oConfigLine, ConfigLine):
            raise TypeError('getClosestMatch takes ConfigLine argument. Unrecognized type %s' % str(type(oConfigLine)))

        aPricingList = cls.objects.filter(customer=oConfigLine.config.header.customer_unit, part=oConfigLine.part.base,
                                          is_current_active=True)
        oPriceObj = aPricingList.filter(sold_to=oConfigLine.config.header.sold_to_party, spud=oConfigLine.spud,
                                        technology=oConfigLine.config.header.technology).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=oConfigLine.config.header.sold_to_party, spud=oConfigLine.spud,
                                            technology=None).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=oConfigLine.config.header.sold_to_party, spud=None,
                                            technology=oConfigLine.config.header.technology).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=None, spud=oConfigLine.spud,
                                            technology=oConfigLine.config.header.technology).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=oConfigLine.config.header.sold_to_party, spud=None,
                                            technology=None).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=None, spud=oConfigLine.spud, technology=None).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=None, spud=None,
                                            technology=oConfigLine.config.header.technology).first()

        if not oPriceObj:
            oPriceObj = aPricingList.filter(sold_to=None, spud=None, technology=None).first()

        return oPriceObj
    # end def


class HeaderLock(models.Model):
    header = models.OneToOneField(Header)
    session_key = models.OneToOneField(Session, default=None, blank=True, null=True, db_constraint=True, unique=False)

    def __str__(self):
        return str(self.header)
    # end def
# end class


class SecurityPermission(models.Model):
    class Meta:
        unique_together = ('read', 'write', 'title')
    # end class

    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    user = models.ManyToManyField(Group, limit_choices_to={'name__startswith': 'BOM_'})
    title = models.CharField(max_length=50)

    def __str__(self):
        return  self.title
    # end def

    def clean(self):
        if self.read and self.write:
            raise ValidationError('Cannot select Read AND Write permission')
        # end if

        if not(self.read or self.write):
            raise ValidationError('Must select Read or Write permission')
        # end if
    # end def
# end class


class HeaderTimeTracker(models.Model):
    header = models.ForeignKey(Header, db_constraint=False)
    created_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    submitted_for_approval = models.DateTimeField(blank=True, null=True)
    psm_config_approver = models.CharField(max_length=50, blank=True, null=True)

    scm1_approver = models.CharField(max_length=50, blank=True, null=True)
    scm1_denied_approval = models.DateTimeField(blank=True, null=True)
    scm1_approved_on = models.DateTimeField(blank=True, null=True)
    scm1_comments = models.TextField(blank=True, null=True)
    scm1_notify = models.TextField(blank=True, null=True)

    scm2_approver = models.CharField(max_length=50, blank=True, null=True)
    scm2_denied_approval = models.DateTimeField(blank=True, null=True)
    scm2_approved_on = models.DateTimeField(blank=True, null=True)
    scm2_comments = models.TextField(blank=True, null=True)
    scm2_notify = models.TextField(blank=True, null=True)

    csr_approver = models.CharField(max_length=50, blank=True, null=True)
    csr_denied_approval = models.DateTimeField(blank=True, null=True)
    csr_approved_on = models.DateTimeField(blank=True, null=True)
    csr_comments = models.TextField(blank=True, null=True)
    csr_notify = models.TextField(blank=True, null=True)

    cpm_approver = models.CharField(max_length=50, blank=True, null=True)
    cpm_denied_approval = models.DateTimeField(blank=True, null=True)
    cpm_approved_on = models.DateTimeField(blank=True, null=True)
    cpm_comments = models.TextField(blank=True, null=True)
    cpm_notify = models.TextField(blank=True, null=True)

    acr_approver = models.CharField(max_length=50, blank=True, null=True)
    acr_denied_approval = models.DateTimeField(blank=True, null=True)
    acr_approved_on = models.DateTimeField(blank=True, null=True)
    acr_comments = models.TextField(blank=True, null=True)
    acr_notify = models.TextField(blank=True, null=True)

    blm_approver = models.CharField(max_length=50, blank=True, null=True)
    blm_denied_approval = models.DateTimeField(blank=True, null=True)
    blm_approved_on = models.DateTimeField(blank=True, null=True)
    blm_comments = models.TextField(blank=True, null=True)
    blm_notify = models.TextField(blank=True, null=True)

    cust1_approver = models.CharField(max_length=50, blank=True, null=True)
    cust1_denied_approval = models.DateTimeField(blank=True, null=True)
    cust1_approved_on = models.DateTimeField(blank=True, null=True)
    cust1_comments = models.TextField(blank=True, null=True)
    cust1_notify = models.TextField(blank=True, null=True)

    cust2_approver = models.CharField(max_length=50, blank=True, null=True)
    cust2_denied_approval = models.DateTimeField(blank=True, null=True)
    cust2_approved_on = models.DateTimeField(blank=True, null=True)
    cust2_comments = models.TextField(blank=True, null=True)
    cust2_notify = models.TextField(blank=True, null=True)

    cust_whse_approver = models.CharField(max_length=50, blank=True, null=True)
    cust_whse_denied_approval = models.DateTimeField(blank=True, null=True)
    cust_whse_approved_on = models.DateTimeField(blank=True, null=True)
    cust_whse_comments = models.TextField(blank=True, null=True)
    cust_whse_notify = models.TextField(blank=True, null=True)

    evar_approver = models.CharField(max_length=50, blank=True, null=True)
    evar_denied_approval = models.DateTimeField(blank=True, null=True)
    evar_approved_on = models.DateTimeField(blank=True, null=True)
    evar_comments = models.TextField(blank=True, null=True)
    evar_notify = models.TextField(blank=True, null=True)

    brd_approver = models.CharField(max_length=50, blank=True, null=True)
    brd_denied_approval = models.DateTimeField(blank=True, null=True)
    brd_approved_on = models.DateTimeField(blank=True, null=True)
    brd_comments = models.TextField(blank=True, null=True)

    completed_on = models.DateTimeField(blank=True, null=True)
    disapproved_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.header)
    # end def

    @property
    def end_date(self):
        return self.disapproved_on or self.completed_on
    # end def

    @property
    def header_name(self):
        return self.header.configuration_designation

    @property
    def baseline(self):
        return self.header.baseline.baseline.title if self.header.baseline else None

    @property
    def version(self):
        return self.header.baseline_version

    @property
    def next_approval(self):
        if not self.completed_on and not self.disapproved_on:
            for level in self.__class__.approvals():
                if not getattr(self, level + '_approver'):
                    return level
        else:
            return None

    @property
    def disapproved_level(self):
        if self.disapproved_on:
            for level in self.__class__.approvals():
                if hasattr(self, level + '_denied_approval') and getattr(self, level + '_denied_approval'):
                    return level
        else:
            return None

    @property
    def last_approval_comment(self):
        if not self.disapproved_on:
            levels = self.__class__.approvals()
            levels.reverse()
            for level in levels:
                if getattr(self, level + '_approved_on') and getattr(self, level + '_approved_on').strftime('%Y-%m-%d') != timezone.datetime(1900, 1, 1).strftime('%Y-%m-%d'):
                    return getattr(self, level + '_comments')
        else:
            return None

    @property
    def last_disapproval_comment(self):
        if self.disapproved_on:
            levels = self.__class__.approvals()
            levels.reverse()
            for level in levels:
                if getattr(self, level + '_denied_approval'):
                    return getattr(self, level + '_comments')
        else:
            return None

    @property
    def next_chevron(self):
        val = self.next_approval
        if val:
            return re.sub(r'(\d+)', r' \1', val.upper()).replace('CUST_', '')
        else:
            return val

    @property
    def chevron_levels(self):
        return [re.sub(r'(\d+)', r' \1', level.upper()).replace('CUST_', '') for level in self.__class__.approvals() if level != 'psm_config' and getattr(self, level + '_approver') != 'system']

    @property
    def get_class(self):
        return self.__class__

    @classmethod
    def approvals(cls):
        return ['psm_config', 'scm1', 'scm2', 'csr', 'cpm', 'acr', 'blm', 'cust1', 'cust2', 'cust_whse', 'evar', 'brd']
    # end def

    @classmethod
    def all_chevron_levels(cls):
        return ['SCM 1', 'SCM 2', 'CSR', 'CPM', 'ACR', 'BLM', 'CUST 1', 'CUST 2', 'WHSE', 'EVAR', 'BRD']

    @classmethod
    def permission_map(cls):
        return {
            'psm_config': ['PSM_Approval_Write'],
            'scm1': ['SCM_Approval_Write'],
            'scm2': ['SCM_Approval_Write'],
            'csr': ['CSR_Approval_Write'],
            'cpm': ['CPM_Approval_Write'],
            'acr': ['ACR_Approval_Write'],
            'blm': ['BLM_Approval_Write'],
            'cust1': ['Customer_Approval_Write'],
            'cust2': ['Customer_Approval_Write'],
            'cust_whse': ['Cust_Whse_Approval_Write'],
            'evar': ['VAR_Approval_Write'],
            'brd': ['BOM_Approval_Write']
        }
    # end def

    @classmethod
    def permission_entry(cls, key):
        """Given key, return the SecurityPermission list associated"""
        if key in cls.permission_map():
            return cls.permission_map()[key]
        return
    # end def
# end class


class DistroList(models.Model):
    customer_unit = models.OneToOneField(REF_CUSTOMER)
    # customer_name = models.ForeignKey(REF_CUSTOMER_NAME, null=True)
    users_included = models.ManyToManyField(User)
    additional_addresses = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.customer_unit.name
#end def


class ApprovalList(models.Model):
    customer = models.OneToOneField(REF_CUSTOMER)
    required = models.CharField(max_length=25, null=True, blank=True)
    optional = models.CharField(max_length=25, null=True, blank=True)
    disallowed = models.CharField(max_length=25, null=True, blank=True)

    def __str__(self):
        return str(self.customer)
# end class


class CustomerPartInfo(models.Model):
    part = models.ForeignKey(PartBase)
    customer = models.ForeignKey(REF_CUSTOMER)
    customer_number = models.CharField(max_length=50)
    second_customer_number = models.CharField(max_length=50, blank=True, null=True)
    # customer_asset = models.CharField(max_length=50, blank=True, null=True)
    customer_asset = models.NullBooleanField(blank=True)
    # customer_asset_tagging = models.CharField(max_length=50, blank=True, null=True)
    customer_asset_tagging = models.NullBooleanField(blank=True)
    # traceability_req = models.CharField(max_length=50, blank=True, null=True)
    traceability_req = models.NullBooleanField(blank=True)
    active = models.BooleanField(default=False)
    priority = models.BooleanField(default=False)

    def __str__(self):
        return str(self.part) + " - " + self.customer_number + (
            "/" + self.second_customer_number if self.second_customer_number else "") + " (" + self.customer.name + ")"
    # end def

    def __eq__(self, other):
        if not isinstance(other, CustomerPartInfo):
            return False

        if self.part != other.part:
            return False
        if self.customer != other.customer:
            return False
        if self.customer_number != other.customer_number:
            return False
        if self.customer_asset_tagging != other.customer_asset_tagging:
            return False
        if self.customer_asset != other.customer_asset:
            return False

        return True
    # end def

    def save(self, *args, **kwargs):
        dUpdate = {'active': False}

        if self.priority:
            dUpdate.update({'priority': False})

        if self.active:
            self.__class__.objects.filter(part=self.part, customer=self.customer).exclude(pk=self.pk).update(**dUpdate)
            self.__class__.objects.filter(customer_number=self.customer_number, customer=self.customer).exclude(pk=self.pk).update(**dUpdate)
        # end def
        super().save(*args, **kwargs)
    # end def
# end class


class DocumentRequest(models.Model):
    req_data = models.TextField()
    new_req = models.DateTimeField(null=True, default=None, blank=True)
    req_error = models.TextField(null=True, blank=True)
    record_processed = models.ForeignKey(Header)
# end class


def sessionstr(self):
    if '_auth_user_id' in self.get_decoded():
        return User.objects.get(pk=self.get_decoded()['_auth_user_id']).username + '_' + str(self.session_key)
    else:
        return str(self.session_key)
# end def

Session.__str__ = sessionstr