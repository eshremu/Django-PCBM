"""
Views module initialization
"""

from BoMConfig.views.landing import Index, Login, Logout, InitialLock, \
    FinalUnlock
from BoMConfig.views.configuration import AddHeader, AddConfig, AddTOC, \
    AddRevision, AddInquiry, Validator, ListFill, ListREACTFill, ReactSearch, \
    Clone, BuildDataArray, AjaxValidator
from BoMConfig.views.search import Search
from BoMConfig.views.baseline_mgmt import BaselineMgmt, BaselineLoad, \
    BaselineRollback, BaselineRollbackTest, DeleteBaseline

from BoMConfig.views.pricing import ConfigPricing, OverviewPricing, PartPricing, \
    PriceErosion, ErosionAjax
from BoMConfig.views.reporting import Report
from BoMConfig.views.upload import Upload
from BoMConfig.views.download import Download, DownloadBaseline, \
    DownloadMultiple, DownloadBaselineMaster, ConfigPriceDownload, \
    PriceOverviewDownload, PartPriceDownload, ErosionDownload, \
    DownloadSearchResults
from BoMConfig.views.approvals_actions import Approval, Action, AjaxApprove, \
    ApprovalData, AjaxApprovalForm, ChangePart, CreateDocument
# S-07204 Refine User Admin page added UserDelete logic  in user admin page
from BoMConfig.views.admin import MailingAdmin, MailingChange, UserAdmin,UserDelete, \
    AdminLanding, UserAdd, UserChange, ApprovalAdmin, ApprovalChange
from BoMConfig.views.customer_audit import CustomerAuditTableValidate, \
    CustomerAudit, CustomerAuditLand, CustomerAuditUpload
from BoMConfig.views.maintenance import Maintenance
