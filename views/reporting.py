__author__ = 'epastag'

from django.contrib.auth.decorators import login_required
from BoMConfig.views.landing import Default


@login_required
def Report(oRequest):
    return Default(oRequest, 'BoMConfig/report.html')
# end def