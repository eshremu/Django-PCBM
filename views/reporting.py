__author__ = 'epastag'

from BoMConfig.views.landing import Default


def Report(oRequest):
    return Default(oRequest, 'BoMConfig/report.html')
# end def