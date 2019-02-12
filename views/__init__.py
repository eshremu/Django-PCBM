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
 # D-04023-Customer filter on Actions issue for Admin users :- Added ActionCustomer to populate baseline dropdown based on selected CU
# S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added ApprovalHold,HoldApprove
from BoMConfig.views.approvals_actions import Approval, Action, AjaxApprove, \
    ApprovalData, AjaxApprovalForm, ChangePart, CreateDocument,ActionCustomer,ApprovalHold,HoldApprove
# S-07204 Refine User Admin page added UserDelete logic  in user admin page
# S-07533 DropDownAdmin added for New sub-tab drop-down admin base template creation
# S-05903, S-05905, S-05906, S-05907, S-05908,S-05909:- Added From ProductArea1Admin to RFDelete for Admin dropdown functionalities
from BoMConfig.views.admin import MailingAdmin, MailingChange, UserAdmin,UserDelete, \
    AdminLanding, UserAdd, UserChange, ApprovalAdmin, ApprovalChange, DropDownAdmin, ProductArea1Admin, ProductArea1Add, SpudAdmin, SpudAdd, SpudEdit, SpudDelete, \
    ProgramAdmin, ProgramAdd, ProgramEdit, ProgramDelete, ProductArea1Admin, ProductArea1Add, ProductArea1Edit, ProductArea1Delete, \
    ProductArea2Admin, ProductArea2Add, ProductArea2Edit, ProductArea2Delete, TechnologyAdmin, \
    TechnologyAdd, TechnologyEdit, TechnologyDelete, RFAdmin, RFAdd, RFEdit, RFDelete
from BoMConfig.views.customer_audit import CustomerAuditTableValidate, \
    CustomerAudit, CustomerAuditLand, CustomerAuditUpload
from BoMConfig.views.maintenance import Maintenance
