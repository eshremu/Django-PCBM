__author__ = 'epastag'

from BoMConfig.views.landing import Index, Login, Logout, InitialLock, FinalUnlock
from BoMConfig.views.configuration import AddHeader, AddConfig, AddTOC, AddRevision, AddInquiry, Validator, ListFill, ListREACTFill, ReactSearch, Clone, BuildDataArray
from BoMConfig.views.search import Search
from BoMConfig.views.baseline_mgmt import BaselineMgmt, BaselineLoad, BaselineRollback
from BoMConfig.views.pricing import ConfigPricing, OverviewPricing, PartPricing, GetConfigLines#, GetPartLine
from BoMConfig.views.reporting import Report
from BoMConfig.views.upload import Upload
from BoMConfig.views.download import Download, DownloadBaseline, DownloadMultiple
from BoMConfig.views.approvals_actions import Approval, Action, AjaxApprove, ApprovalData
from BoMConfig.views.admin import MailingAdmin, MailingChange
