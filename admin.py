from django.contrib import admin

from BoMConfig.models import *
from BoMConfig.forms import LinePricingForm
from django.contrib.sessions.models import Session

# Register your models here.


class PartBaseAdmin(admin.ModelAdmin):
    ordering = ('product_number',)
# end class


class PartAdmin(admin.ModelAdmin):
    ordering = ('base__product_number',)
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
    list_display = ('header', 'created_on')
# end class


class HeaderAdmin(admin.ModelAdmin):
    list_display = ('configuration_designation', 'baseline_version', 'program')


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

admin.site.register(Alert)
admin.site.register(NewsItem)
admin.site.register(Header, HeaderAdmin)
admin.site.register(Configuration)
admin.site.register(ConfigLine)
admin.site.register(Part, PartAdmin)
admin.site.register(PartBase, PartBaseAdmin)
admin.site.register(Baseline)
admin.site.register(Baseline_Revision)
admin.site.register(RevisionHistory)
admin.site.register(LinePricing, LinePriceAdmin)
admin.site.register(PricingObject, PriceObjAdmin)
admin.site.register(REF_CUSTOMER)
admin.site.register(REF_REQUEST)
admin.site.register(Session, SessionAdmin)
admin.site.register(SecurityPermission)
admin.site.register(HeaderTimeTracker, TimeStampAdmin)
admin.site.register(HeaderLock, HeaderLockAdmin)
admin.site.register(REF_TECHNOLOGY)
admin.site.register(REF_PRODUCT_AREA_1)
admin.site.register(REF_PRODUCT_AREA_2)
admin.site.register(REF_CUSTOMER_NAME)
admin.site.register(REF_PROGRAM, ProgramAdmin)
admin.site.register(REF_CONDITION)
admin.site.register(REF_PRODUCT_PKG)
admin.site.register(REF_SPUD)
admin.site.register(REF_MATERIAL_GROUP)
admin.site.register(REF_RADIO_FREQUENCY)
admin.site.register(REF_RADIO_BAND)
admin.site.register(REF_STATUS)
