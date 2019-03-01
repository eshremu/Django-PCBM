"""
Classes to use a basis for database tables, and other objects used in tool.
"REF_" classes refer to models/tables of objects that should change very
infrequently and are used as reference tables.
"""

from django.db import models, connections
from django.contrib.sessions.models import Session
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings

import re

authUser = settings.AUTH_USER_MODEL

# Create your models here.
class ParseException(Exception):
    """
    Custom class for exceptions during upload parsing
    """
    pass


class OrderedManager(models.Manager):
    """
    Class for handling querysets for objects with a "name" attribute.
    This object is used to return querysets in alphabetical order
    """
    def get_queryset(self):
        return super().get_queryset().order_by('name')
    # end def
# end class


class Alert(models.Model):
    """
    Model for Important tool alerts
    """
    Title = models.CharField(max_length=200, blank=True)
    Text = models.CharField(max_length=1000)
    PublishDate = models.DateTimeField('Date Published')

    def __str__(self):
        return self.Title
    # end def
# end class


class NewsItem(models.Model):
    """
    Model for tool-related news items
    """
    Title = models.CharField(max_length=200)
    Text = models.CharField(max_length=1000)
    PublishDate = models.DateTimeField('Date Published')

    def __str__(self):
        return self.Title
    # end def
# end class


class REF_CUSTOMER(models.Model):
    """
    Model for customer objects
    """
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
    """
    Model to store header record request types
    """
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
    """
    Model to store list of available technologies
    """
    class Meta:
        verbose_name = 'REF Technology'
        verbose_name_plural = 'REF Technologies'
    # end class

    name = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=0)    #S-05905 : Edit drop down option for BoM Entry Header - Technology: Added new field

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PRODUCT_AREA_1(models.Model):
    """
    Model to store list of product areas
    """
    class Meta:
        verbose_name = 'REF Product Area'
    # end class

    name = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=0) #S-05906 : Edit drop down option for BoM Entry Header - Product Area 1: Added new field

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_PRODUCT_AREA_2(models.Model):
    """
    Model to store list of sub-product areas.  Each product area 2 object MUST
    have a connection to an existing product area 1 (above)
    """
    class Meta:
        verbose_name = 'REF Sub-Product Area'
    # end class

    name = models.CharField(max_length=50)
    parent = models.ForeignKey(REF_PRODUCT_AREA_1)
    is_inactive = models.BooleanField(default=0) #S-05907 : Edit drop down option for BoM Entry Header - Product Area 2: Added new field

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_CUSTOMER_NAME(models.Model):
    """
    Model to store list of customer names.  Each customer MUST be associated to
    a customer unit (REF_CUSTOMER)

    ****This object is not currently used.  Customer name information is being
    retrieved via another database.  This object may be removed or modified in
    future iterations.****
    """
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
    """
    Model to store list of customer programs. Each program MUST be associated to
    a customer unit (REF_CUSTOMER)
    """
    class Meta:
        verbose_name = 'REF Program'
    # end class

    name = models.CharField(max_length=50)
    parent = models.ForeignKey(REF_CUSTOMER)
    is_inactive = models.BooleanField(default=0) #S-05903 :Edit drop down option for BoM Entry Header - Program: Added new field

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_CONDITION(models.Model):
    """
    Model to store list of line item conditions
    """
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
    """
    Model to store list of line item product package types
    """
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
    """
    Model to store list of line item material groups
    """
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
    """
    Model to store list of special pricing unit designations
    """
    class Meta:
        verbose_name = 'REF SPUD'
    # end class

    name = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=0) #S-05909 : Edit drop down option for BoM Entry Header - SPUD: Added new field

    objects = OrderedManager()

    def __str__(self):
        return self.name
    # end def
# end class


class REF_RADIO_BAND(models.Model):
    """
    Model to store list of radio bands
    """
    class Meta:
        verbose_name = 'REF Radio Band'
    # end class

    name = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=0) #S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band : Added new field

    def __str__(self):
        return self.name
    # end def
# end class


class REF_RADIO_FREQUENCY(models.Model):
    """
    Model to store list of radio frequencies
    """
    class Meta:
        verbose_name = 'REF Radio Frequency'
        verbose_name_plural = 'REF Radio Frequencies'
    # end class

    name = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=0) #S-05908 : Edit drop down option for BoM Entry Header - Radio Frequency / Band : Added new field

    def __str__(self):
        return self.name
    # end def
# end class


class REF_STATUS(models.Model):
    """
    Model to store list of configuration statuses
    """
    class Meta:
        verbose_name = 'REF Status'
        verbose_name_plural = 'REF Statuses'
    # end class

    name = models.CharField(max_length=50)

    objects = OrderedManager()

    def __str__(self):
        return self.name


class Baseline(models.Model):
    """
    Model for Baseline objects

    This is the overall baseline storage location.  This will up-rev with
    each revision.

    A baseline up-revs when the baseline/any attached config has been changed
    and submitted for approval
    """
    title = models.CharField(max_length=50, unique=True)
    # version = models.CharField(max_length=50)
    current_active_version = models.CharField(max_length=50, default='',
                                              blank=True)
    current_inprocess_version = models.CharField(max_length=50, default='A')
    customer = models.ForeignKey(REF_CUSTOMER, db_constraint=False, blank=True,
                                 null=True)
    isdeleted = models.BooleanField(default=0)
    # user = models.ForeignKey(authUser)

    def save(self, *args, **kwargs):
        """
        This function runs whenever a Baseline object is saved
        :param args: list of position arguments
        :param kwargs: dictionary of keyword arguments
        :return: None
        """
        # Remove ' rev' from the end of the baseline name, if found.
        # This is a remnant from the initial population of the tool.  The
        # original records were saved with revision information in the name
        if self.title.lower().endswith(' rev'):
            self.title = self.title[:-4]
        # end if

        super().save(*args, **kwargs)

        # If no Baseline_Revision objects have been attached to this baseline,
        # create a new Baseline_Revision object for the in-process revision
        if not self.baseline_revision_set.all():
            Baseline_Revision.objects.create(
                **{'baseline': self, 'version': self.current_inprocess_version})
        # end if
    # end def

    def __str__(self):
        return (self.title + "_" + self.current_inprocess_version + "_" +
                self.current_active_version)
    # end def

    @property
    def latest_revision(self):
        """
        Returns the Baseline_Revision with the same version as
        current_active_version, if it exists, else None
        :return: Baseline_Revision / None
        """
        try:
            return Baseline_Revision.objects.get(
                baseline=self,
                version=self.current_active_version)
        except Baseline_Revision.DoesNotExist:
            return None
    # end def
# end class


class Baseline_Revision(models.Model):
    """
    Model for Baseline_Revision objects

    This is the specific baseline storage location for each revision.
    This links to a collection of Header objects that exist within a revision.
    The object also stores the date the revision is released via the tool,
    meaning any new Headers will be added to the next revision.

    Baseline_Revision objects maintain a linked chain to previous and next
    revisions.
    """
    class Meta:
        verbose_name = 'Baseline Revision'
    # end class

    baseline = models.ForeignKey(Baseline, db_constraint=False)
    version = models.CharField(max_length=50, default='A')
    completed_date = models.DateField(blank=True, null=True)
    previous_revision = models.ForeignKey('Baseline_Revision', blank=True,
                                          null=True,
                                          related_name='next_revision')
    isdeleted = models.BooleanField(default=0)
    
    @property
    def title(self):
        """
        Returns the title of the associated Baseline
        :return: str
        """
        return self.baseline.title
    # end def

    @property
    def customer(self):
        """
        Returns the REF_CUSTOMER object of the associated Baseline
        :return: REF_CUSTOMER / None (this should be a rare case)
        """
        return self.baseline.customer
    # end def

    def __str__(self):
        return (self.title + " Rev " + self.version +
                (' ' + self.completed_date.strftime('%m%d%y') + 'C'
                 if self.completed_date else ''))
    # end def
# end class


class Header(models.Model):
    """
    Model for Header objects.
    Each Bill of Materials (BoM) is comprised of a Header and a Configuration
    """

 # S-05787: Re-alignment of Header tab of BOM Entry page for All Customers:- changed the order of the fields in the Headerform as per the mockup provided

    react_request = models.CharField(max_length=25,
                                     verbose_name='REACT Request', blank=True,
                                     null=True)
    bom_request_type = models.ForeignKey(REF_REQUEST,
                                         verbose_name='BoM Request Type',
                                         db_constraint=False)
    customer_unit = models.ForeignKey(REF_CUSTOMER,
                                      verbose_name='Customer Unit',
                                      db_constraint=False)
    person_responsible = models.CharField(max_length=50,
                                          verbose_name='Person Responsible')

    customer_name = models.CharField(max_length=50,
                                     verbose_name='Customer Name', blank=True,
                                     null=True)
    sales_office = models.CharField(max_length=50, verbose_name='Sales Office',
                                    blank=True, null=True)
    sales_group = models.CharField(max_length=50, verbose_name='Sales Group',
                                   blank=True, null=True)
    sold_to_party = models.IntegerField(verbose_name='Sold-to Party',
                                        blank=True, null=True)
    ship_to_party = models.IntegerField(verbose_name='Ship-to Party',
                                        blank=True, null=True)
    ericsson_contract = models.IntegerField(verbose_name='Ericsson Contract #',
                                            blank=True, null=True)
    bill_to_party = models.IntegerField(verbose_name='Bill-to Party',
                                        blank=True, null=True)
    payment_terms = models.CharField(max_length=50,
                                     verbose_name='Payment Terms', blank=True,
                                     null=True)
    configuration_designation = models.CharField(max_length=50,
                                                 verbose_name='Configuration')
    program = models.ForeignKey(REF_PROGRAM, verbose_name='Program', blank=True,
                                null=True, db_constraint=False)
    customer_designation = models.CharField(max_length=50,
                                            verbose_name='Customer Designation',
                                            blank=True, null=True)
    technology = models.ForeignKey(REF_TECHNOLOGY, verbose_name='Technology',
                                   blank=True, null=True, db_constraint=False)
    product_area1 = models.ForeignKey(REF_PRODUCT_AREA_1,
                                      verbose_name='Product Area 1', blank=True,
                                      null=True, db_constraint=False)
    product_area2 = models.ForeignKey(REF_PRODUCT_AREA_2,
                                      verbose_name='Product Area 2', blank=True,
                                      null=True, db_constraint=False)
    radio_frequency = models.ForeignKey(REF_RADIO_FREQUENCY,
                                        verbose_name='Radio Frequency',
                                        blank=True, null=True,
                                        db_constraint=False)
    radio_band = models.ForeignKey(REF_RADIO_BAND, verbose_name='Radio Band',
                                   blank=True, null=True, db_constraint=False)

    inquiry_site_template = models.IntegerField(verbose_name='Inquiry/Site Template #',
                                                blank=True, null=True)
    valid_from_date = models.DateField(verbose_name='Valid-from Date',
                                       blank=True, null=True)
    valid_to_date = models.DateField(verbose_name='Valid-to Date', blank=True,
                                     null=True)
    complete_delivery = models.BooleanField(verbose_name='Complete Delivery',
                                            default=True)
    no_zip_routing = models.BooleanField(default=False,
                                         verbose_name='No ZipRouting')
    shipping_condition = models.CharField(max_length=50,
                                          verbose_name='Shipping Condition',
                                          blank=True, null=True, default='71')

    baseline_impacted = models.CharField(max_length=50,
                                         verbose_name='Baseline Impacted',
                                         blank=True, null=True)
    model = models.CharField(max_length=50, verbose_name='Model', blank=True,
                             null=True)
    model_description = models.CharField(max_length=50,
                                         verbose_name='Model Description',
                                         blank=True, null=True)
    model_replaced = models.CharField(max_length=50,
                                      verbose_name='What Model is this replacing?',
                                      blank=True, null=True)
    initial_revision = models.CharField(max_length=50,
                                        verbose_name='Initial Revision',
                                        blank=True,
                                        null=True)  # This is the root model

    configuration_status = models.ForeignKey(REF_STATUS,
                                             verbose_name='Configuration/Ordering Status',
                                             default=1, db_index=False,
                                             db_constraint=False, unique=False)
    readiness_complete = models.IntegerField(verbose_name='Readiness Complete (%)',
                                             blank=True, null=False, default=0)

# S-08410:Adjust Model and BoM Header Tab:- Added below field to check whether to start from line 100 or not
    line_100 = models.BooleanField(verbose_name='Line 100?', default = False)

    pick_list = models.BooleanField(default=False, blank=True)
    projected_cutover = models.DateField(verbose_name='Projected Cut-over Date',
                                         blank=True, null=True)

    optional_free_text1 = models.CharField(max_length=50,
                                           verbose_name='Optional Free Text Field 1',
                                           blank=True, null=True)
    optional_free_text2 = models.CharField(max_length=50,
                                           verbose_name='Optional Free Text Field 2',
                                           blank=True, null=True)
    optional_free_text3 = models.CharField(max_length=50,
                                           verbose_name='Optional Free Text Field 3',
                                           blank=True, null=True)

    model_replaced_link = models.ForeignKey('Header',
                                            related_name='replaced_by_model',
                                            blank=True, null=True)

    old_configuration_status = models.ForeignKey(REF_STATUS, default=None,
                                                 related_name='old_status',
                                                 db_index=False,
                                                 db_constraint=False,
                                                 unique=False, null=True,
                                                 blank=True)
    workgroup = models.CharField(max_length=50, verbose_name='Workgroup',
                                 blank=True, null=True)
    name = models.CharField(max_length=50, verbose_name='Name', blank=True,
                            null=True)

    internal_notes = models.TextField(blank=True, null=True)
    external_notes = models.TextField(blank=True, null=True)

    """This is the config-specific storage of the baseline version.  This will
    match the 'version' of the Baseline_Revision to which this record is
    attached"""
    baseline_version = models.CharField(max_length=50, blank=True, null=True)
    bom_version = models.CharField(max_length=50, blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    change_notes = models.TextField(blank=True, null=True)
    change_comments = models.TextField(blank=True, null=True)
    baseline = models.ForeignKey(Baseline_Revision)

    class Meta:
        unique_together = ['configuration_designation', 'baseline_version',
                           'baseline', 'program', 'customer_name']
    # end class

    def __str__(self):
        return (self.configuration_designation +
                ("_{}".format(self.program.name) if self.program else '') +
                ("__" + self.baseline_version if self.baseline_version else ''))
    # end def

    def save(self, *args, **kwargs):
        """
        This function runs whenever a Baseline object is saved
        :param args: list of position arguments
        :param kwargs: dictionary of keyword arguments
        :return: None
        """
        # bMessage is used to determine if an email should be sent regarding
        # readiness_complete changes. oRequest is used to track the user making
        # the save call
        bMessage = kwargs.pop('alert', True)
        oRequest = kwargs.pop('request', None)

        # Creating a new Header
        if not self.pk:

            # If the user saved the record with a value in baseline_impacted,
            # find the baseline wuth the name provided. If no value was provided
            # attach to the 'No Associated Baseline' baseline, a special record
            # to collect non-baselined files
            if self.baseline_impacted:
                oBase = Baseline.objects.filter(
                    title__iexact=self.baseline_impacted).first()
            else:
                oBase = Baseline.objects.get(
                    title__iexact='No Associated Baseline')

            # Attach to the latest Baseline_Revision object associated to the
            # baseline determined above
            if oBase and not hasattr(self, 'baseline'):
                self.baseline = Baseline_Revision.objects.get(
                    baseline=oBase,
                    version=oBase.current_inprocess_version)
                self.baseline_version = self.baseline.version
            # end if

            if self.baseline_version in (None, ''):
                self.baseline_version = 'A'

            if self.bom_version in (None, ''):
                self.bom_version = '1'
        else:  # Update existing Header
            # Headers can only be updated while the record has a status of
            # "In Process".  Once out of this stage, the only update will be
            # making sure that the baseline_impacted field properly reflects the
            # attached baseline
            if self.configuration_status.name == 'In Process':
                """
                This block handles updating the baseline attachment for this
                record.  A record can be moved between baselines if needed.
                """

                # If the record is attached to a baseline and baseline_impacted
                # is not blank
                if self.baseline and self.baseline_impacted:
                    # If baseline_impacted does not refer to the currently
                    # attached baseline, reattach to the correct baseline
                    if self.baseline.baseline.title != self.baseline_impacted:
                        sLastRev = Baseline.objects.get(
                            title=self.baseline_impacted
                        ).current_inprocess_version
                        self.baseline = Baseline_Revision.objects.get(
                            baseline=Baseline.objects.get(
                                title=self.baseline_impacted),
                            version=sLastRev)
                # If the record is not attached to a baseline and
                # baseline_impacted is not blank, attach to the baseline
                # specified by baseline_impacted
                elif not self.baseline and self.baseline_impacted:
                    sLastRev = Baseline.objects.get(
                        title=self.baseline_impacted).current_inprocess_version
                    self.baseline = Baseline_Revision.objects.get(
                        baseline=Baseline.objects.get(
                            title=self.baseline_impacted),
                        version=sLastRev)
                # If the record is attached to a baseline and baseline_impacted
                # is blank, update baseline_impacted to match the title of the
                # attached baseline
                elif self.baseline and not self.baseline_impacted:
                    if self.baseline.title != 'No Associated Baseline':
                        self.baseline_impacted = self.baseline.title
                # If the record is not attached to a baseline and
                # baseline_impacted is blank, attach to the 'No Associated
                # Baseline' baseline
                elif not self.baseline and not self.baseline_impacted:
                    sLastRev = Baseline.objects.get(
                        title='No Associated Baseline'
                    ).current_inprocess_version
                    self.baseline = Baseline_Revision.objects.get(
                        baseline=Baseline.objects.get(
                            title='No Associated Baseline'),
                        version=sLastRev)
                # end if
            else:
                if self.baseline and self.baseline.title != \
                        'No Associated Baseline':
                    self.baseline_impacted = self.baseline.title
            # end if

            # Update baseline_version field
            if self.baseline:
                self.baseline_version = self.baseline.version
            # end if
        # end if

        # Set/update the readiness complete field, and send any notifications if
        # needed
        iPrevRC = self.readiness_complete
        if self.configuration_status.name == 'In Process':
            if self.bom_request_type.name == 'Preliminary':
                self.readiness_complete = 25
            else:
                self.readiness_complete = 50

                # If this header has a configuration attached and that
                # configuration's ready_for_forecast field is true, set the
                # readiness_complete to 70
                if hasattr(self, 'configuration') and \
                        self.configuration.ready_for_forecast:
                    self.readiness_complete = 70

                    # If this change to 70 caused an increase in
                    # readiness_complete value, send an email with this record
                    # attached to all users in the BOM_Forecast/Demand_Demand
                    # Manager group
                    # S-10576: Change the header of the tool to ACC :- Changed the tool name from pcbm to acc
                    if bMessage and iPrevRC < self.readiness_complete:
                        aRecips = User.objects.filter(groups__name__in=[
                            'BOM_Forecast/Demand_Demand_Manager']).values_list(
                            'email', flat=True)
                        oMessage = EmailMultiAlternatives(
                            subject='Review for Forecast Readiness',
                            body=('''\
Hello SCM user,

Log into the Agreed Customer Catalog (ACC) tool to review the \
following Configuration for forecast readiness.  \
Attached is a copy for your convenience and discussion with Forecasting and \
Commodity Planning.  \
This Configuration is currently at 70% Readiness Complete.

    {} - {} - {}

If there are questions, please contact the appropriate Configuration Manager.\
You can locate this information on the "Header" tab of the attached \
Configuration file.

ACC Link: https://rnamsupply.internal.ericsson.com/acc'''
                                  ).format(self.configuration_designation,
                                           self.baseline_impacted or '',
                                           self.react_request or ''),
                            from_email='acc.admin@ericsson.com',
                            to=aRecips,
                            cc=[oRequest.user.email] if oRequest else None)
                        oMessage.attach_alternative((
'''
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Configuration {0}</title>
        <style>
            body {{
                font-family: "Calibri", sans-serif;font-size: 11pt;
            }}
            a {{
                font-style: italic;font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <p>Hello SCM user,</p>
        <p>Log into the Agreed Customer Catalog (ACC) tool to \
review the following Configuration for forecast readiness.  \
Attached is a copy for your convenience and discussion with Forecasting and \
Commodity Planning.  This Configuration is currently at 70% Readiness Complete.
        </p>
        <ul>
            <li>{0} - {1} - {2}</li>
        </ul>
        <p>If there are questions, please contact the appropriate \
Configuration Manager.  You can locate this information on the "Header" tab of \
the attached Configuration file.</p>
        <p>ACC Link:
            <a href="https://rnamsupply.internal.ericsson.com/acc">
                https://rnamsupply.internal.ericsson.com/acc
            </a>
        </p>
    </body>
</html>
'''
                            ).format(self.configuration_designation,
                                     self.baseline_impacted or '',
                                     self.react_request or ''), 'text/html')

                        # Write this record to an BytesIO stream to attach to
                        # the email
                        from BoMConfig.views.download import WriteConfigToFile
                        from io import BytesIO
                        oStream = BytesIO()
                        WriteConfigToFile(self).save(oStream)
                        oMessage.attach(
                            filename=(self.configuration_designation + (
                                '_' + self.program.name if self.program else ''
                            ) + '.xlsx'),
                            content=oStream.getvalue(),
                            mimetype='application/ms-excel'
                        )

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
        # Create a HeaderTimeTracker and HeaderLock object if one of each does
        # not exist for this record
        if not hasattr(self, 'headertimetracker_set') or not \
                self.headertimetracker_set.all():
            HeaderTimeTracker.objects.create(**{'header': self})
        # end if

        if not hasattr(self, 'headerlock'):
            HeaderLock.objects.create(**{'header': self})
        # end if
    # end def

    @property
    def latesttracker(self):
        """
        Returns the most recent (per submitted_for_approval field)
        HeaderTimeTracker object attached to this record
        :return: HeaderTimeTracker
        """
        return self.get_all_trackers().first()
    # end def

    @property
    def last_disapproved_tracker(self):
        """
        Returns the most recently disapproved (disapproved_on field is NOT null)
        HeaderTimeTracker object attached to this record
        :return: HeaderTimeTracker
        """
        if self.headertimetracker_set:
            return self.headertimetracker_set.filter(
                disapproved_on__isnull=False).order_by(
                '-submitted_for_approval').first()

        return None
    # end def

    def get_all_trackers(self):
        """
        Returns all HeaderTimeTracker objects attached to this record, ordered
        by submission date with the most recent tracker first
        :return: QuerySet
        """
        if self.headertimetracker_set:
            return self.headertimetracker_set.order_by(
                '-submitted_for_approval')

        return None
    # end def

    @property
    def check_date(self):
        """
        Returns a date that falls within the valid period for this record
        (between valid_from_date and valid_to_date.

        :todo:: This function is not currently used and was intended to help
        auto-determine what pricing data should be associated to this record
        :return: DateTime object
        """
        if self.valid_from_date and self.valid_to_date:
            return self.valid_from_date + timezone.timedelta(
                seconds=(self.valid_to_date - self.valid_from_date
                         ).total_seconds()/2)
        elif not self.valid_from_date and self.valid_to_date:
            return self.valid_to_date - timezone.timedelta(days=1)
        elif self.valid_from_date and not self.valid_to_date:
            return self.valid_from_date + timezone.timedelta(days=1)
        elif not self.valid_from_date and not self.valid_to_date:
            return timezone.now().date()

    @property
    def contains_fap_parts(self):
        """
        Determines if this records configuration contains any part numbers that
        begin with FAP.  This is part of the determination of whether or not
        a SAP document can be created for this record
        :return: Boolean
        """
        for oLine in self.configuration.configline_set.all():
            if '.' in oLine.line_number:
                continue
            if oLine.part.product_number.upper().startswith('FAP'):
                return True
        return False

    def _core_document_eligible(self):
        """
        Determines if the record is complete enough for a SAP document to be
        created based on this record
        :return: Boolean
        """
        # Ensure critical fields have not been left empty
        if not self.sold_to_party:
            return False

        if not self.ship_to_party:
            return False

        if not self.bill_to_party:
            return False

        if not self.valid_from_date:
            return False

        if not self.valid_to_date:
            return False

        if not self.ericsson_contract:
            return False

        if not self.payment_terms:
            return False

        # Ensure every line item has a plant plant
        for oLine in self.configuration.configline_set.all():
            if '.' in oLine.line_number:
                continue
            if not oLine.plant:
                return False

            # This is commented out for now, but after a later release, these
            # will be the only allowed values, so there will be no need to have
            # separate checks for inquires and site templates as seen below

            # if oLine.item_category not in ['0002', 'Z002', 'ZB02', 'ZDSH',
            #                                'ZF25', 'ZORP', 'ZF26', 'ZGBA',
            #                                'ZGBD', 'ZORM', 'ZSMZ', 'ZSXM',
            #                                'VERP', 'ZERQ', '', None]:
            #     return False
            # if not oLine.item_category:
            #     return False

        # No "FAP" parts
        return not self.contains_fap_parts

    @property
    def site_template_eligible(self):
        """
        Specific checks to determine if a Site Template SAP document can be
        created using this record
        :return: Boolean
        """
        if not self.configuration:
            return False

        # Ensure each parent line (line number contains no decimals) has a
        # correct item_category value and a higher_level_item number
        for oLine in self.configuration.configline_set.all():
            if '.' in oLine.line_number:
                continue
            if oLine.line_number != '10' and oLine.item_category not in [
                    'ZSBS', 'ZSBU', 'ZSBT', 'ZSXS',
                    'ZSBM', 'ZF36', 'ZMX0', 'ZSW7',
                    '0002', 'Z002', 'ZB02', 'ZDSH',
                    'ZF25', 'ZORP', 'ZF26', 'ZGBA',
                    'ZGBD', 'ZORM', 'ZSMZ', 'ZSXM',
                    'VERP', 'ZERQ', '', None]:
                return False

            if oLine.higher_level_item in ('', None) and \
                    oLine.line_number != '10':
                return False

        return self._core_document_eligible()

    @property
    def inquiry_eligible(self):
        """
        Specific checks to determine if an Inquiry SAP document can be
        created using this record
        :return: Boolean
        """
        if not self.configuration:
            return False

        # Ensure any non-pick-list record has a netvalue and a total value
        if not self.pick_list and not (self.configuration.net_value or
                                       self.configuration.override_net_value):
            return False

        if not self.configuration.total_value:
            return False

        # Ensure each parent line (line number contains no decimals) has a
        # correct item_category value and no higher_level_item number
        for oLine in self.configuration.configline_set.all():
            if '.' in oLine.line_number:
                continue
            if oLine.line_number != '10' and oLine.item_category not in [
                    'ZTBI', 'ZI36', 'ZTNI', 'ZSXI',
                    'ZTFI', 'ZI25', 'ZAFP', 'ZSW7',
                    '0002', 'Z002', 'ZB02', 'ZDSH',
                    'ZF25', 'ZORP', 'ZF26', 'ZGBA',
                    'ZGBD', 'ZORM', 'ZSMZ', 'ZSXM',
                    'VERP', 'ZERQ', '', None]:
                return False

            if oLine.higher_level_item not in ('', None):
                return False

        return self._core_document_eligible()

    @property
    def pdf_allowed(self):
        """
        Determines if the record can have a PDF document created and stored.

        This is determined by whether or not the record has a valid
        react_request value
        :return: Boolean
        """
        if self.react_request:
            sQuery = ("SELECT [req_id] FROM dbo.ps_requests WHERE "
                      "[req_id]=%s AND [modified_by] IS NULL")

            oCursor = connections['REACT'].cursor()
            oCursor.execute(sQuery, [bytes(self.react_request, 'ascii')])
            oResults = oCursor.fetchall()
            return bool(oResults)
        else:
            return False

    @property
    def latestdocrequest(self):
        """
        Returns the most recently submitted DocumentRequest object attached to
        this record
        :return: DocumentRequest
        """
        return self.documentrequest_set.all().order_by('-new_req').first()

    @property
    def discontinue_can_proceed(self):
        """
        Determines if a record of request type "Discontinue" can have it's SAP
        document updated.  This is determined by checking if this record is
        replacing another and if that replaced record also has a replacement
        with a valid document number.
        :return: Boolean
        """
        if self.bom_request_type.name == 'Discontinue':
            if self.model_replaced_link and \
                    self.model_replaced_link.replaced_by_model.exclude(
                        id=self.id):
                if self.model_replaced_link.replaced_by_model.exclude(
                        id=self.id).first().inquiry_site_template is not None \
                        and self.model_replaced_link.replaced_by_model.exclude(
                            id=self.id).first().inquiry_site_template > 0:
                    return True
                else:
                    return False
            else:
                return True
        else:
            return False

    @property
    def is_locked(self):
        """
        Determines if this record is locked from editing
        :return: Boolean
        """
        if self.headertimetracker_set.first().session is not None:
            return True
        return False
# end class


class Configuration(models.Model):
    """
    Model for Configuration objects
    A configuration is part of a BoM, and contains the list of items in the BoM

    A Configuration object stores overall price information and links to a
    collection of ConfigLine objects
    """
    ready_for_forecast = models.BooleanField(default=False,
                                             verbose_name="Ready for Forecast")
    PSM_on_hold = models.BooleanField(default=False,
                                      verbose_name="PSM On Hold?")
    internal_external_linkage = models.BooleanField(default=False,
                                                    verbose_name="Internal/External Linkage")
    # FloatField changed to IntegerField for below 3 fields
    net_value = models.FloatField(blank=True, null=True,
                                  verbose_name="Net Value")
    override_net_value = models.FloatField(blank=True, null=True,
                                           verbose_name="Overriden Net Value")
    total_value = models.FloatField(blank=True, null=True,
                                    verbose_name="Total Net Value")
    zpru_total = models.FloatField(blank=True, null=True,
                                   verbose_name="ZPRU Total")
    header = models.OneToOneField(Header)
    needs_zpru = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Saves Configuration object
        :param args: List of positional arguments
        :param kwargs: Dictionary of keyword arguments
        :return: None
        """

        # If record is being placed on hold or taken off hold, update associated
        # Header configuration_status value
        if self.PSM_on_hold and self.header.configuration_status.name != \
                'On Hold':
            self.header.old_configuration_status = \
                self.header.configuration_status
            self.header.configuration_status = REF_STATUS.objects.get(
                name='On Hold')
        elif not self.PSM_on_hold and self.header.old_configuration_status is \
                not None:
            self.header.configuration_status = \
                self.header.old_configuration_status
            self.header.old_configuration_status = None
        # end if

        # Save associated header
        self.header.save(request=kwargs.pop('request', None))

        # If associated Header has a status of "In Process" or
        # "In Process/Pending", redetermine the overall price values for this
        # configuration
        if 'In Process' in self.header.configuration_status.name:
            self.DeterminePrice()

        super().save(*args, **kwargs)
    # end def

    def __str__(self):
        return self.title + ("__" + self.header.baseline_version if
                             self.header.baseline_version else '')
    # end def

    def get_first_line(self):
        """
        Returns the ConfigLine object representing the first line of the
        Configuration.  Line items have a magnitude-10 numbering system, with
        the first line always being 10.
        :return: ConfigLine object
        """
        oFirst = None
        line100 = self.header.line_100
        if line100:
            try:
                oFirst = self.configline_set.get(line_number='100')
            except ConfigLine.DoesNotExist:
                pass
            # end try
        else:
            try:
                oFirst = self.configline_set.get(line_number='10')
            except ConfigLine.DoesNotExist:
                pass
            # end try
        return oFirst
    # end def

    @property
    def first_line(self):
        """
        Property returning first ConfigLine
        :return: ConfigLine object
        """
        return self.get_first_line()

    @property
    def title(self):
        """
        Returns configuration_designation of associated Header object
        :return: str
        """
        return self.header.configuration_designation

    @property
    def version(self):
        """
        Returns baseline_version of associated Header object
        :return: str
        """
        return self.header.baseline_version or '(Not baselined)'

    def DeterminePrice(self):
        """
        Calculates the net_value, override_net_value, and total_value of this
        Configuration, based on pricing data attached to and stored in the
        associated ConfigLine objects.
        :return: None
        """
        net_total = override_net_total = zust_amount = None

        # Determine if any of the lines in the configuration contain a price
        # override.  This will ensure that the override net total is updated by
        # lines that do not contain an overriden price.
        bContainsOverride = bool(self.configline_set.filter(
            linepricing__override_price__isnull=False).count())

        # Loop though all ConfigLines (reverse ordered by line number, so bottom
        # up)
        for oCLine in sorted(self.configline_set.all(), key=lambda x: (
                [int(y) for y in x.line_number.split('.')]), reverse=True):
            # "ZUST" condition types get added to total value.  other conditions
            # do not.
            if str(oCLine.condition_type).upper() == 'ZUST':
                zust_amount = oCLine.amount

            # If ConfigLine has pricing data associated
            if oCLine.linepricing:
                # This flag indicates that the line we are on has updated
                # override_net_total
                bOverUpdate = False
                if oCLine.linepricing.override_price is not None:
                    # Any overriden price on line 10 for non-pick-list records
                    # defines the intended total value of the record.
                    #
                    # This is the reason the loop checks from bottom up.  The
                    # other values still need to be tallied, even though the
                    # final value can be determined from this override price and
                    # any ZUST value
                    if not self.header.pick_list and oCLine.line_number == '10':
                        override_net_total = oCLine.linepricing.override_price
                    else:
                        # Update override_net_total
                        if override_net_total is None:
                            override_net_total = 0
                        override_net_total += oCLine.linepricing.override_price
                    bOverUpdate = True

                if oCLine.linepricing.pricing_object:
                    # Update net_total (and override_net_total if need be) with
                    # the calculated line value (unit price * quantity)
                    if net_total is None:
                        net_total = 0
                    net_total += (oCLine.order_qty or 0) * (
                        oCLine.linepricing.pricing_object.unit_price or 0)
                    if not bOverUpdate and bContainsOverride:
                        if override_net_total is None:
                            override_net_total = 0
                        override_net_total += (oCLine.order_qty or 0) * (
                            oCLine.linepricing.pricing_object.unit_price or 0)

        # Set configuration fields to calculated values
        self.override_net_value = override_net_total
        self.net_value = net_total
        self.total_value = (override_net_total or net_total or 0) + (
            zust_amount or 0)
# end class


class PartBase(models.Model):
    """
    Model for PartBase objects.
    Stores product number and UOM information only
    """
    product_number = models.CharField(max_length=50, unique=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.product_number
    # end def
# end class


class Part(models.Model):
    """
    Model for Part objects.
    Stores combination of part description and PartBase object.  This allows the
    tool to store multiple parts with varying descriptions that are actually all
    the same part number, instead of storing duplicate part numbers for each
    different description
    """
    product_description = models.CharField(
        max_length=100, blank=True, null=True)
    base = models.ForeignKey(PartBase, blank=True, null=True)

    class Meta:
        unique_together = ('product_description', 'base')
    # end class

    def __str__(self):
        return str(self.pk) + " - " + self.product_number + " - " + (
            self.product_description if self.product_description else '(None)')
    # end def

    @property
    def product_number(self):
        """
        Property that return the attached Partbase object's product_number value
        :return: str
        """
        return self.base.product_number

    @property
    def description(self):
        """
        Property that returns the part object's product description
        :return: str
        """
        return self.product_description or '(None)'
# end class


class ConfigLine(models.Model):
    """
    Model for ConfigLine objects.
    A ConfigLine represents a single line item in a Configuration.  ConfigLines
    store part, line number, quantity information, etc.
    """
    line_number = models.CharField(max_length=50)
    order_qty = models.FloatField(blank=True, null=True)
    plant = models.CharField(max_length=50, blank=True, null=True)
    sloc = models.CharField(max_length=50, blank=True, null=True)
    item_category = models.CharField(max_length=50, blank=True, null=True)
    spud = models.ForeignKey(REF_SPUD, blank=True, null=True, unique=False,
                             db_constraint=False, db_index=False)
    internal_notes = models.TextField(blank=True, null=True)
    higher_level_item = models.CharField(max_length=50, blank=True, null=True)
    material_group_5 = models.CharField(max_length=50, blank=True, null=True)
    purchase_order_item_num = models.CharField(max_length=50, blank=True,
                                               null=True)
    condition_type = models.CharField(max_length=50, blank=True, null=True)
    amount = models.FloatField(blank=True, null=True)
    customer_asset = models.CharField(max_length=50, blank=True, null=True)
    customer_asset_tagging = models.CharField(max_length=50, blank=True,
                                              null=True)
    customer_number = models.CharField(max_length=50, blank=True, null=True)
    sec_customer_number = models.CharField(max_length=50, blank=True, null=True)
    vendor_article_number = models.CharField(max_length=50, blank=True,
                                             null=True)
    comments = models.TextField(blank=True, null=True)
    additional_ref = models.TextField(blank=True, null=True)
    config = models.ForeignKey(Configuration)
    part = models.ForeignKey(Part)
    is_child = models.BooleanField(default=False)
    is_grandchild = models.BooleanField(default=False)
    pcode = models.CharField(max_length=100, blank=True, null=True)
    commodity_type = models.CharField(max_length=50, blank=True, null=True)
    package_type = models.CharField(max_length=50, blank=True, null=True)
    # S-08473: Adjust configuration table to include new columns:- Added below 1 column
    current_portfolio_code = models.CharField(max_length=50, blank=True, null=True)
    REcode = models.CharField(max_length=50, blank=True, null=True)
    mu_flag = models.CharField(max_length=50, blank=True, null=True)
    x_plant = models.CharField(max_length=50, blank=True, null=True)
    # S-08473: Adjust configuration table to include new columns:- Added below 2 columns
    plant_specific_material_status = models.CharField(max_length=50, blank=True, null=True)
    distribution_chain_specific_material_status = models.CharField(max_length=50, blank=True, null=True)
    traceability_req = models.CharField(max_length=50, blank=True,
                                        null=True)  # TODO: Use CustomerPartInfo
    last_updated = models.DateTimeField(blank=True, null=True)
    contextId = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return str(self.config) + "_" + self.line_number
    # end def

    @property
    def title(self):
        """
        Returns the attached configuration's title
        :return: str
        """
        return self.config.title

    @property
    def version(self):
        """
        Returns the attached configuration's version
        :return: str
        """
        return self.config.version
# end class


class RevisionHistory(models.Model):
    """
    Model of RevisionHistory object.
    Used to store an overview of changes within the revision.  This is generated
    by comparing a Baseline's revision (Baseline_Revision object) to another
    revision.  This should only be performed on consequtive revisions within a
    single baseline.
    """
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
        """
        Returns the attached baseline's title
        :return: str
        """
        return self.baseline.title
# end class


class LinePricing(models.Model):
    """
    Model for LinePricing objects
    Stores pricing data for a ConfigLine object.  Also acts as a linking object
    between ConfigLines objects and PricingObject
    """
    # unit_price = models.FloatField(blank=True, null=True)
    override_price = models.FloatField(blank=True, null=True)
    pricing_object = models.ForeignKey('PricingObject', null=True)
    config_line = models.OneToOneField(ConfigLine)

    def __str__(self):
        return str(self.config_line) + (
            "_" + str(self.pricing_object.unit_price) if self.pricing_object
            else '')
    # end def

    @property
    def configuration_designation(self):
        """
        Returns the associated configuration's title, which is the attached
        header's configuration_designation
        :return: str
        """
        return self.config_line.config.title

    @property
    def version(self):
        """
        Returns the associated configuration's title, which is the attached
        header's configuration_designation
        :return: str / None
        """
        try:
            return self.config_line.config.version
        except AttributeError:
            return

    @property
    def line_number(self):
        """
        Returns the ConfigLine's line number
        :return: str
        """
        return self.config_line.line_number
# end class


class PricingObject(models.Model):
    """
    Class / model for storing unit pricing information for a Part.  Pricing
    is per customer, and can also have SPUD, Technology, & Sold-to as
    differentiating factors.  Objects contain a link to the previously entered
    data object.
    """
    unit_price = models.FloatField(blank=True, null=True, default=0.0)
    customer = models.ForeignKey(REF_CUSTOMER, to_field='id')
    sold_to = models.IntegerField(blank=True, null=True)
    spud = models.ForeignKey(REF_SPUD, to_field='id', null=True, blank=True)
    part = models.ForeignKey(PartBase, to_field='id')
    date_entered = models.DateTimeField(default=timezone.now)
    previous_pricing_object = models.ForeignKey('PricingObject', null=True,
                                                blank=True)
    is_current_active = models.BooleanField(default=False)
    cutover_date = models.DateField(null=True, blank=True)
    valid_from_date = models.DateField(null=True, blank=True)
    valid_to_date = models.DateField(null=True, blank=True)
    price_erosion = models.BooleanField(default=False)
    erosion_rate = models.FloatField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    technology = models.ForeignKey(REF_TECHNOLOGY, to_field='id', null=True,
                                   blank=True)

    def __str__(self):
        return (str(self.part) + "_" + str(self.customer) + "_" +
                str(self.sold_to) + "_" + str(self.spud) + "_" +
                self.date_entered.strftime('%m/%d/%Y'))

    @classmethod
    def getClosestMatch(cls, oConfigLine):
        """
        Determines the PricingObject that most closely matches the data provided
        in a ConfigLine object (Customer, PartBase, Header.sold_to_party,
        spud, technology), if one exists

        At minimum, a PricingObject must have the same Customer and PartBase,
        and be an active PricingObject.

        The function will then attempt to match based on all possible
        combinations of Sold_to, SPUD, and Technology (All 3, Sold-to and SPUD,
        Sold-to and tech, SPUD and tech, sold-to only, spud only, tech only)
        :param oConfigLine: ConfigLine object to attempt to match.  If none of
        these combinations match, the function will return the PricingObject
        that matches only Customer and Part, if one exists.
        :return: PricingObject / None
        """
        if not isinstance(oConfigLine, ConfigLine):
            raise TypeError(
                ('getClosestMatch takes ConfigLine argument.'
                 ' Unrecognized type {}').format(str(type(oConfigLine))))

        aPricingList = cls.objects.filter(
            customer=oConfigLine.config.header.customer_unit,
            part=oConfigLine.part.base,
            is_current_active=True)
 # Fix for D-04415- SPUD pricing in not pulled in for configs(SPUD pricing should not consider any other fields except for part number and SPUD. This will mean that we need
 #  to remove the filter by Sold To or any other conditions).Removed all the condition and made it base only on SPUD. If part no
 #        is entered without any spud then latest changed unit price without spud will be shown.)

        oPriceObj = aPricingList.filter(
            spud=oConfigLine.spud).last()

        return oPriceObj
    # end def


class HeaderLock(models.Model):
    """
    Model for HeaderLock object.
    Tracks the user, by session key, that is currently editing a BoM
    """
    header = models.OneToOneField(Header)
    session_key = models.OneToOneField(
        Session, default=None, blank=True, null=True, db_constraint=True,
        unique=False)

    def __str__(self):
        return str(self.header)
    # end def
# end class


class SecurityPermission(models.Model):
    """
    Model for SecurityPermission objects.
    A SecurityPermission object consists of whether the permission is for read
    or write access (only one), and a list of groups (which in turn contain
    users) with the permission.
    """
    class Meta:
        unique_together = ('read', 'write', 'title')
    # end class

    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    user = models.ManyToManyField(Group,
                                  limit_choices_to={'name__startswith': 'BOM_'})
    title = models.CharField(max_length=50)

    def __str__(self):
        return self.title
    # end def

    def clean(self):
        """
        Function run when checking if a SecurityPermission object is safe/valid
        to be stored to the database
        :return: None
        """
        if self.read and self.write:
            raise ValidationError('Cannot select Read AND Write permission')
        # end if

        if not(self.read or self.write):
            raise ValidationError('Must select Read or Write permission')
        # end if
    # end def
# end class


class HeaderTimeTracker(models.Model):
    """
    Model for HeaderTimeTracker object
    Used to track work flow time for the approval of a BoM.
    Tracks user and date/time of approval/disapproval for all levels of
    approval.  Also tracks and comments made, and any desired notifications.
    """
    header = models.ForeignKey(Header, db_constraint=False)
    created_on = models.DateTimeField(default=timezone.now, blank=True,
                                      null=True)

    submitted_for_approval = models.DateTimeField(blank=True, null=True)
    psm_config_approver = models.CharField(max_length=50, blank=True, null=True)
    # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added _hold_approval for each level,hold_on
    scm1_approver = models.CharField(max_length=50, blank=True, null=True)
    scm1_denied_approval = models.DateTimeField(blank=True, null=True)
    scm1_approved_on = models.DateTimeField(blank=True, null=True)
    scm1_hold_approval = models.DateTimeField(blank=True, null=True)
    scm1_comments = models.TextField(blank=True, null=True)
    scm1_notify = models.TextField(blank=True, null=True)

    scm2_approver = models.CharField(max_length=50, blank=True, null=True)
    scm2_denied_approval = models.DateTimeField(blank=True, null=True)
    scm2_approved_on = models.DateTimeField(blank=True, null=True)
    scm2_hold_approval = models.DateTimeField(blank=True, null=True)
    scm2_comments = models.TextField(blank=True, null=True)
    scm2_notify = models.TextField(blank=True, null=True)

    csr_approver = models.CharField(max_length=50, blank=True, null=True)
    csr_denied_approval = models.DateTimeField(blank=True, null=True)
    csr_approved_on = models.DateTimeField(blank=True, null=True)
    csr_hold_approval = models.DateTimeField(blank=True, null=True)
    csr_comments = models.TextField(blank=True, null=True)
    csr_notify = models.TextField(blank=True, null=True)

    cpm_approver = models.CharField(max_length=50, blank=True, null=True)
    cpm_denied_approval = models.DateTimeField(blank=True, null=True)
    cpm_approved_on = models.DateTimeField(blank=True, null=True)
    cpm_hold_approval = models.DateTimeField(blank=True, null=True)
    cpm_comments = models.TextField(blank=True, null=True)
    cpm_notify = models.TextField(blank=True, null=True)

    acr_approver = models.CharField(max_length=50, blank=True, null=True)
    acr_denied_approval = models.DateTimeField(blank=True, null=True)
    acr_approved_on = models.DateTimeField(blank=True, null=True)
    acr_hold_approval = models.DateTimeField(blank=True, null=True)
    acr_comments = models.TextField(blank=True, null=True)
    acr_notify = models.TextField(blank=True, null=True)

    blm_approver = models.CharField(max_length=50, blank=True, null=True)
    blm_denied_approval = models.DateTimeField(blank=True, null=True)
    blm_approved_on = models.DateTimeField(blank=True, null=True)
    blm_hold_approval = models.DateTimeField(blank=True, null=True)
    blm_comments = models.TextField(blank=True, null=True)
    blm_notify = models.TextField(blank=True, null=True)

    cust1_approver = models.CharField(max_length=50, blank=True, null=True)
    cust1_denied_approval = models.DateTimeField(blank=True, null=True)
    cust1_approved_on = models.DateTimeField(blank=True, null=True)
    cust1_hold_approval = models.DateTimeField(blank=True, null=True)
    cust1_comments = models.TextField(blank=True, null=True)
    cust1_notify = models.TextField(blank=True, null=True)

    cust2_approver = models.CharField(max_length=50, blank=True, null=True)
    cust2_denied_approval = models.DateTimeField(blank=True, null=True)
    cust2_approved_on = models.DateTimeField(blank=True, null=True)
    cust2_hold_approval = models.DateTimeField(blank=True, null=True)
    cust2_comments = models.TextField(blank=True, null=True)
    cust2_notify = models.TextField(blank=True, null=True)

    cust_whse_approver = models.CharField(max_length=50, blank=True, null=True)
    cust_whse_denied_approval = models.DateTimeField(blank=True, null=True)
    cust_whse_approved_on = models.DateTimeField(blank=True, null=True)
    cust_whse_hold_approval = models.DateTimeField(blank=True, null=True)
    cust_whse_comments = models.TextField(blank=True, null=True)
    cust_whse_notify = models.TextField(blank=True, null=True)

    evar_approver = models.CharField(max_length=50, blank=True, null=True)
    evar_denied_approval = models.DateTimeField(blank=True, null=True)
    evar_approved_on = models.DateTimeField(blank=True, null=True)
    evar_hold_approval = models.DateTimeField(blank=True, null=True)
    evar_comments = models.TextField(blank=True, null=True)
    evar_notify = models.TextField(blank=True, null=True)

    brd_approver = models.CharField(max_length=50, blank=True, null=True)
    brd_denied_approval = models.DateTimeField(blank=True, null=True)
    brd_approved_on = models.DateTimeField(blank=True, null=True)
    brd_hold_approval = models.DateTimeField(blank=True, null=True)
    brd_comments = models.TextField(blank=True, null=True)

    completed_on = models.DateTimeField(blank=True, null=True)
    disapproved_on = models.DateTimeField(blank=True, null=True)
    hold_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.header)

    # end def

    @property
    def end_date(self):
        """
        Returns this objects disapproved_on value if it exists, or the
        completed_on value if it exists
        :return: DateTime / None
        """
        return self.disapproved_on or self.completed_on or self.hold_on

    # end def

    @property
    def header_name(self):
        """
        Returns the name/title/designation_configuration of the attached Header
        :return: str
        """
        return self.header.configuration_designation

    @property
    def baseline(self):
        """
        Returns the title of the Baseline to which the attached header is
        attached, if the header is attached to a Baseline
        :return: str / None
        """
        return self.header.baseline.baseline.title if \
            self.header.baseline else None

    @property
    def version(self):
        """
        Returns the attached Header's baseline_version value
        :return: str
        """
        return self.header.baseline_version

    @property
    def next_approval(self):
        """
        Returns a string indicating the next approval level for which this
        record has no approver.
        :return: str / None
        """
        if not self.completed_on and not self.disapproved_on:
            for level in self.__class__.approvals():
                if not getattr(self, level + '_approver'):
                    return level
        else:
            return None

    @property
    def disapproved_level(self):
        """
        Returns the approval level that contains a valid denied_approval value
        :return: str / None
        """
        if self.disapproved_on:
            for level in self.__class__.approvals():
                if hasattr(self, level + '_denied_approval') and \
                        getattr(self, level + '_denied_approval'):
                    return level
        else:
            return None
    # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added def
    @property
    def hold_level(self):
        """
        Returns the approval level that contains a valid denied_approval value
        :return: str / None
        """
        if self.hold_on:
            for level in self.__class__.approvals():
                if hasattr(self, level + '_hold_approval') and \
                        getattr(self, level + '_hold_approval'):
                    return level
        else:
            return None

    @property
    def last_approval_comment(self):
        """
        Returns the comment(s) stored for the last possible approval level for
        this record that contains a valid approved_on value.
        :return: str / None
        """
        if not self.disapproved_on or not self.hold_on: # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added _hold_on
            levels = self.__class__.approvals()
            levels.reverse()
            for level in levels:
                if getattr(self, level + '_approved_on') and \
                                getattr(self, level + '_approved_on').strftime(
                                    '%Y-%m-%d') != timezone.datetime(
                            1900, 1, 1).strftime('%Y-%m-%d'):
                    return getattr(self, level + '_comments')
        else:
            return None

    @property
    def last_disapproval_comment(self):
        """
        Returns the comment(s) stored for the last possible approval level for
        this record that contains a valid denied_approval value.
        :return: str / None
        """
        if self.disapproved_on:
            return getattr(self, self.disapproved_level + '_comments')
        else:
            return None
    # S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added _hold_approval for each level
    @property
    def last_hold_comment(self):
        """
        Returns the comment(s) stored for the last possible approval level for
        this record that contains a valid denied_approval value.
        :return: str / None
        """
        if self.hold_on:
            return getattr(self, self.hold_level + '_comments')
        else:
            return None

    @property
    def next_chevron(self):
        """
        Returns a string that indicates the next needed approval in a format
        that will be used as a chevron title (displayed in tool)
        :return: str
        """
        val = self.next_approval
        if val:
            return re.sub(r'(\d+)', r' \1', val.upper()).replace('CUST_', '')
        else:
            return val

    @property
    def chevron_levels(self):
        """
        Returns a list of chevron titles that correspond to the approval levels
        this record needs for completion.
        :return: list of str
        """
        return [re.sub(r'(\d+)', r' \1', level.upper()).replace('CUST_', '') for
                level in self.__class__.approvals() if
                level != 'psm_config' and
                getattr(self, level + '_approver') != 'system']

    @property
    def get_class(self):
        """
        Returns this class.  Used to access class methods in template code
        :return: class
        """
        return self.__class__

    @classmethod
    def approvals(cls):
        """
        Returns a list of approval levels
        :return: list of str
        """
        return ['psm_config', 'scm1', 'scm2', 'csr', 'cpm', 'acr', 'blm',
                'cust1', 'cust2', 'cust_whse', 'evar', 'brd']
    # end def

    @classmethod
    def all_chevron_levels(cls):
        """
        Returns a list of titles for cheverons
        :return: list of str
        """
        return ['SCM 1', 'SCM 2', 'CSR', 'CPM', 'ACR', 'BLM', 'CUST 1',
                'CUST 2', 'WHSE', 'EVAR', 'BRD']

    @classmethod
    def permission_map(cls):
        """
        Returns a dict mapping approval levels to the required
        SecurityPermission object the user must possess
        :return: dict
        """
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
        """
        Given key, return the SecurityPermission list associated
        :param key: str value to be used as key against permission_map
        dictionary
        :return list of str / None
        """
        if key in cls.permission_map():
            return cls.permission_map()[key]
        return
    # end def
# end class


class DistroList(models.Model):
    """
    Model for DistroList object
    Stores a list of users that should receive a notification when a Baseline
    for the specified customer is released.  Also stores manually entered email
    addresses to receive notification.
    """
    customer_unit = models.OneToOneField(REF_CUSTOMER)
    users_included = models.ManyToManyField(User)
    additional_addresses = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.customer_unit.name
# end def

# S-06578 : Addition for User_Customer table
class User_Customer(models.Model):
    class Meta:
        verbose_name = 'User Customer'
        # end class

    user = models.ForeignKey(authUser, db_constraint = False, blank=True, null=True)
    customer = models.ForeignKey(REF_CUSTOMER, db_constraint = False, blank=True, null=True)
    is_deleted = models.BooleanField(default=0)
    customer_name = models.TextField(null=True, blank=True)

    def __str__(self):
        return (str(self.user)+ " - " + str(self.customer)+ " - " + str(self.customer_name)+" - " + str(self.is_deleted))
    # end def

class ApprovalList(models.Model):
    """
    Model for ApprovalList object
    Stores approval information per customer.  Each record submitted for
    approval will be required to receive each approval listed in required, does
    not require any approvals listed in disallowed, and can optionally be
    required to receive approval levels listed in optional.
    """
    customer = models.OneToOneField(REF_CUSTOMER)
    required = models.CharField(max_length=25, null=True, blank=True)
    optional = models.CharField(max_length=25, null=True, blank=True)
    disallowed = models.CharField(max_length=25, null=True, blank=True)

    def __str__(self):
        return str(self.customer)
# end class


class CustomerPartInfo(models.Model):
    """
    Model for CustomerPartInfo objects.
    Stores custoemr part number information for PartBase objects.
    Stores data on a per-customer basis.  Only one object may be active per
    PartBase/REF_CUSTOMER combination.

    Priority indicates that the object was manually entered by a user with
    permission to do so, and will not be overwritten by objects generated by
    document uploads.
    """
    part = models.ForeignKey(PartBase)
    customer = models.ForeignKey(REF_CUSTOMER)
    customer_number = models.CharField(max_length=50)
    second_customer_number = models.CharField(max_length=50, blank=True,
                                              null=True)
    customer_asset = models.NullBooleanField(blank=True)
    customer_asset_tagging = models.NullBooleanField(blank=True)
    traceability_req = models.NullBooleanField(blank=True)
    active = models.BooleanField(default=False)
    priority = models.BooleanField(default=False)

    def __str__(self):
        return str(self.part) + " - " + self.customer_number + (
            "/" + self.second_customer_number if self.second_customer_number
            else "") + " (" + self.customer.name + ")"
    # end def

    def __eq__(self, other):
        """
        Comparison function to determine if two CustomerPartInfo objects should
        be considered equivalent
        :param other: CustomerPartInfo object being compared
        :return: Boolean
        """
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
        """
        Function run when saving objects.
        :param args: list of positional arguments
        :param kwargs: dictionary of keyword arguments
        :return: None
        """
        dUpdate = {'active': False}

        if self.priority:
            dUpdate.update({'priority': False})

        # If the object being saved is active or priority, ensure all other
        # records for the same customer/part and customer/customer part number
        # have been marked as inactive and non-priority
        if self.active:
            self.__class__.objects.filter(
                part=self.part,
                customer=self.customer).exclude(pk=self.pk).update(**dUpdate)
            self.__class__.objects.filter(
                customer_number=self.customer_number,
                customer=self.customer).exclude(pk=self.pk).update(**dUpdate)
        # end def
        super().save(*args, **kwargs)
    # end def
# end class


class DocumentRequest(models.Model):
    """
    Model for DocumentRequest objects.
    Stores document parameters, request date, and any errors for each SAP
    document creation/update transaction requested in tool.
    """
    req_data = models.TextField()
    new_req = models.DateTimeField(null=True, default=None, blank=True)
    req_error = models.TextField(null=True, blank=True)
    record_processed = models.ForeignKey(Header)
# end class


def sessionstr(self):
    """
    Function to override the __str__ function of Session objects
    :param self: Session object
    :return: str
    """
    if '_auth_user_id' in self.get_decoded():
        return User.objects.get(
            pk=self.get_decoded()['_auth_user_id']).username + '_' + str(
            self.session_key)
    else:
        return str(self.session_key)
# end def

Session.__str__ = sessionstr
