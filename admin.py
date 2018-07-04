"""
Classes used in Django-admin level administration
"""
from django.contrib import admin

from BoMConfig.models import *
from BoMConfig.forms import LinePricingForm, DistroForm, SecurityForm
from BoMConfig.utils import RevisionCompare
from django.contrib.sessions.models import Session


# Register your models here.
class PartBaseAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    ordering = ('product_number',)
    search_fields = ('product_number',)
# end class


class PartAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('product_number', 'description')
    search_fields = ('base__product_number', 'product_description')
    ordering = ('base__product_number', 'product_description')
# end class


class SessionAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    def _session_data(self, obj):
        """
        Function to return data from object for display/use in adminstration
        views
        :param obj: Object to use
        :return: String containing decoded text of session key
        """
        return obj.get_decoded()

    ordering = ['session_key']
    list_display = ['__str__', 'expire_date']
    exclude = ['session_data']
    readonly_fields = ['session_key', '_session_data', 'expire_date']
# end class


class TimeStampAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('header_name', 'version', 'baseline', 'created_on',
                    'end_date')
    search_fields = ('header__configuration_designation',
                     'header__baseline_version',
                     'header__baseline__baseline__title')
# end class


class HeaderAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('configuration_designation', 'baseline_version', 'program')
    search_fields = ('configuration_designation', 'baseline_version')


class ProgramAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('name', 'parent')


class PriceObjAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('part', 'customer', 'sold_to', 'spud', 'is_current_active')
    ordering = ('part', 'customer', 'sold_to', 'spud', '-date_entered')


class HeaderLockAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    def get_queryset(self, request):
        """
        Function specifying result set when all() is used for underlying Model
        :param request: Django HTTP request object
        :return: QuerySet containing desired results
        """
        qs = super().get_queryset(request)
        return qs.exclude(session_key=None)


class LinePriceAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    form = LinePricingForm
    list_display = ('configuration_designation',
                    'version',
                    'line_number',)
    search_fields = ('config_line__config__header__configuration_designation',
                     'config_line__config__header__baseline__version',
                     'config_line__line_number',)
    # ordering = ('config_line__config__header__configuration_designation',
    #             'config_line__config__header__baseline__version',
    #             'config_line__line_number',
    #             )


class RevisionAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('title', 'version', 'completed_date')
    search_fields = ('baseline__title', 'version')

    def render_change_form(self, request, context, *args, **kwargs):
        """
        This function is used to limit and order the possible previous revisions
        that are provided when changing a Baseline_Revision object
        """
        if context['original'] is not None:
            orderQuery = sorted(Baseline_Revision.objects.filter(
                baseline__title=context['original'].baseline.title
            ).order_by('version'), key=lambda x: RevisionCompare(x.version))
            orderQuery = orderQuery[:orderQuery.index(context['original'])]
        else:
            orderQuery = []
        choices = [(context['adminform'].form.fields[
                        'previous_revision'].prepare_value(obj),
                    context['adminform'].form.fields[
                        'previous_revision'].label_from_instance(obj)
                    ) for obj in orderQuery]
        context['adminform'].form.fields['previous_revision'].choices = \
            [('', '----------')] + choices
        return super(RevisionAdmin, self).render_change_form(
            request, context, *args, **kwargs)


class DistroAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    form = DistroForm
    filter_horizontal = ('users_included',)


class SecurityPermissionAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    form = SecurityForm


class CustomerInfoAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('part', 'customer_number', 'customer',
                    'customer_asset_tagging', 'customer_asset', 'active',
                    'priority')
    search_fields = ('part__product_number', 'customer_number')
    list_filter = ('active', 'priority')


class BaselineAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('title', 'current_active_version',
                    'current_inprocess_version', 'customer')
    search_fields = ('title', 'customer__name')


class UserCustomerAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('user', 'customer','customer_name',
                    'is_deleted')

class ConfigLineAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('title', 'version', 'line_number')
    search_fields = ('config__header__configuration_designation', 'line_number',
                     'config__header__baseline_version')


class ConfigAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('title', 'version')
    search_fields = ('header__configuration_designation',
                     'header__baseline_version')


class RevHistoryAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('title', 'revision')
    search_fields = ('baseline__title', 'revision')


class SubProductAreaAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('name', 'parent')


class CustomerNameAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('name', 'parent')


class DocumentAdmin(admin.ModelAdmin):
    """
    ModelAdmin specifying how model should behave in built-in Django
    administration views
    """
    list_display = ('id', 'new_req')


admin.site.register(Alert)
admin.site.register(NewsItem)
admin.site.register(Header, HeaderAdmin)
admin.site.register(Configuration, ConfigAdmin)
admin.site.register(ConfigLine, ConfigLineAdmin)
admin.site.register(Part, PartAdmin)
admin.site.register(PartBase, PartBaseAdmin)
admin.site.register(Baseline, BaselineAdmin)
admin.site.register(Baseline_Revision, RevisionAdmin)
admin.site.register(RevisionHistory, RevHistoryAdmin)
admin.site.register(LinePricing, LinePriceAdmin)
admin.site.register(PricingObject, PriceObjAdmin)
admin.site.register(REF_CUSTOMER)
admin.site.register(REF_REQUEST)
admin.site.register(Session, SessionAdmin)
admin.site.register(SecurityPermission, SecurityPermissionAdmin)
admin.site.register(HeaderTimeTracker, TimeStampAdmin)
admin.site.register(HeaderLock, HeaderLockAdmin)
admin.site.register(REF_TECHNOLOGY)
admin.site.register(REF_PRODUCT_AREA_1)
admin.site.register(REF_PRODUCT_AREA_2, SubProductAreaAdmin)
admin.site.register(REF_CUSTOMER_NAME, CustomerNameAdmin)
admin.site.register(REF_PROGRAM, ProgramAdmin)
admin.site.register(REF_CONDITION)
admin.site.register(REF_PRODUCT_PKG)
admin.site.register(REF_SPUD)
admin.site.register(REF_MATERIAL_GROUP)
admin.site.register(REF_RADIO_FREQUENCY)
admin.site.register(REF_RADIO_BAND)
admin.site.register(REF_STATUS)
admin.site.register(DistroList, DistroAdmin)
admin.site.register(ApprovalList)
admin.site.register(CustomerPartInfo, CustomerInfoAdmin)
admin.site.register(DocumentRequest, DocumentAdmin)
admin.site.register(User_Customer,UserCustomerAdmin)  # S-06578 : Addition for User_Customer table in Django Admin UI
