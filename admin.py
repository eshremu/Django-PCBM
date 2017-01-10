from django.contrib import admin
from django import forms

from BoMConfig.models import *
from BoMConfig.forms import LinePricingForm, DistroForm, SecurityForm
from BoMConfig.utils import RevisionCompare
from django.contrib.sessions.models import Session

# Register your models here.


class PartBaseAdmin(admin.ModelAdmin):
    ordering = ('product_number',)
    search_fields = ('product_number',)
# end class


class PartAdmin(admin.ModelAdmin):
    list_display = ('product_number', 'description')
    search_fields = ('base__product_number', 'product_description')
    ordering = ('base__product_number', 'product_description')
# end class


class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()
    ordering = ['session_key']
    list_display = ['__str__','expire_date']
    exclude = ['session_data']
    readonly_fields = ['session_key','_session_data','expire_date']
# end class


class TimeStampAdmin(admin.ModelAdmin):
    # fields = ('header','created_on' ,'submitted_for_approval','completed_on')
    # readonly_fields = ('header','created_on' ,'submitted_for_approval', 'completed_on')
    list_display = ('header_name', 'version', 'baseline', 'created_on', 'end_date')
    search_fields = ('header__configuration_designation', 'header__baseline_version', 'header__baseline__baseline__title')
# end class


class HeaderAdmin(admin.ModelAdmin):
    list_display = ('configuration_designation', 'baseline_version', 'program')
    search_fields = ('configuration_designation', 'baseline_version')


class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name','parent')


class PriceObjAdmin(admin.ModelAdmin):
    list_display = ('part','customer','sold_to', 'spud', 'is_current_active')
    ordering = ('part','customer','sold_to','spud','-date_entered')


class HeaderLockAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(session_key=None)


class LinePriceAdmin(admin.ModelAdmin):
    form = LinePricingForm
    list_display = ('configuration_designation',
                    'version',
                    'line_number',)
    search_fields = ('config_line__config__header__configuration_designation', 'config_line__config__header__baseline__version', 'config_line__line_number',)
    # ordering = ('config_line__config__header__configuration_designation',
    #             'config_line__config__header__baseline__version',
    #             'config_line__line_number',
    #             )


class RevisionAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'completed_date')
    search_fields = ('baseline__title', 'version')

    def render_change_form(self, request, context, *args, **kwargs):
        if context['original'] is not None:
            orderQuery = sorted(Baseline_Revision.objects\
                .filter(baseline__title=context['original'].baseline.title)\
                .order_by('version'), key=lambda x: RevisionCompare(x.version))
            orderQuery = orderQuery[:orderQuery.index(context['original'])]
        else:
            orderQuery = []
        choices = [(
                       context['adminform'].form.fields['previous_revision'].prepare_value(obj),
                       context['adminform'].form.fields['previous_revision'].label_from_instance(obj)
                   ) for obj in orderQuery]
        context['adminform'].form.fields['previous_revision'].choices = [('','----------')] + choices
        return super(RevisionAdmin, self).render_change_form(request, context, *args, **kwargs)


class DistroAdmin(admin.ModelAdmin):
    form = DistroForm
    filter_horizontal = ('users_included',)


class SecurityPermissionAdmin(admin.ModelAdmin):
    form = SecurityForm


class CustomerInfoAdmin(admin.ModelAdmin):
    list_display = ('part', 'customer_number', 'customer', 'customer_asset_tagging', 'customer_asset', 'active', 'priority')
    search_fields = ('part__product_number', 'customer_number')
    list_filter = ('active', 'priority')


class BaselineAdmin(admin.ModelAdmin):
    list_display = ('title', 'current_active_version', 'current_inprocess_version', 'customer')
    search_fields = ('title', 'customer__name')


class ConfigLineAdmin(admin.ModelAdmin):
    list_display = ('title','version','line_number')
    search_fields = ('config__header__configuration_designation', 'line_number', 'config__header__baseline_version')


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('title', 'version')
    search_fields = ('header__configuration_designation', 'header__baseline_version')


class RevHistoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'revision')
    search_fields = ('baseline__title', 'revision')


class SubProductAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')


class CustomerNameAdmin(admin.ModelAdmin):
    list_display = ('name','parent')


class DocumentAdmin(admin.ModelAdmin):
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
