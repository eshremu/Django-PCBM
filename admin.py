from django.contrib import admin

from .models import *
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

admin.site.register(Alert)
admin.site.register(NewsItem)
admin.site.register(Header)
admin.site.register(Configuration)
admin.site.register(ConfigLine)
admin.site.register(Part, PartAdmin)
admin.site.register(PartBase, PartBaseAdmin)
admin.site.register(Baseline)
admin.site.register(Baseline_Revision)
admin.site.register(RevisionHistory)
admin.site.register(LinePricing)
admin.site.register(REF_CUSTOMER)
admin.site.register(REF_REQUEST)
admin.site.register(Session, SessionAdmin)
admin.site.register(SecurityPermission)
admin.site.register(HeaderTimeTracker, TimeStampAdmin)
admin.site.register(HeaderLock)
admin.site.register(REF_TECHNOLOGY)
admin.site.register(REF_PRODUCT_AREA_1)
admin.site.register(REF_PRODUCT_AREA_2)
admin.site.register(REF_CUSTOMER_NAME)
admin.site.register(REF_PROGRAM)
admin.site.register(REF_CONDITION)
admin.site.register(REF_PRODUCT_PKG)
admin.site.register(REF_SPUD)
admin.site.register(REF_MATERIAL_GROUP)
admin.site.register(REF_RADIO_FREQUENCY)
admin.site.register(REF_RADIO_BAND)