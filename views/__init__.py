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
# S-11537: Multi Config sub tab - UI for Multiple Config tab :- Added MultConfigPricing to show multiple configs
# S-11538: Open multiple revisions for each configuration - UI Elements :-  Added MultRevConfigPricing to show multiple rev configs
# S-11541: Upload - pricing for list of parts in pricing tab: Added PriceUpload to upload pricing data
from BoMConfig.views.pricing import ConfigPricing, MultiConfigPricing, MultiRevConfigPricing, PriceUpload,  OverviewPricing, PartPricing, \
    PriceErosion, ErosionAjax
from BoMConfig.views.reporting import Report
from BoMConfig.views.upload import Upload
from BoMConfig.views.download import Download, DownloadBaseline, \
    DownloadMultiple, DownloadBaselineMaster, ConfigPriceDownload, \
    PriceOverviewDownload, PartPriceDownload, ErosionDownload, \
    DownloadSearchResults, MultiConfigPriceDownload
 # D-04023-Customer filter on Actions issue for Admin users :- Added ActionCustomer to populate baseline dropdown based on selected CU
# S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added ApprovalHold,HoldApprove
# S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added ActiveCustomer
from BoMConfig.views.approvals_actions import Approval, Action, AjaxApprove, \
    ApprovalData, AjaxApprovalForm, ChangePart, CreateDocument, ActionCustomer, ActiveCustomer, \
    ApprovalHold, HoldApprove, ActionCustomerNameBaseline,ApprovalCustomerCustomerName
# S-07204 Refine User Admin page added UserDelete logic  in user admin page
# S-07533 DropDownAdmin added for New sub-tab drop-down admin base template creation
# S-05903, S-05905, S-05906, S-05907, S-05908,S-05909:- Added From ProductArea1Admin to RFDelete for Admin dropdown functionalities
# S-10578: Admin to unlock a locked config: Added UnlockAdmin, UnlockConfigAdmin, UserChangeFromUnlock
#  for fetching the locked configs list, unlocking them, open the user change page on clicking the username from unlock page respectively
from BoMConfig.views.admin import MailingAdmin, MailingChange, UserAdmin,UserDelete, \
    AdminLanding, UserAdd, UserChange, UserChangeFromUnlock, ApprovalAdmin, ApprovalChange, DropDownAdmin, ProductArea1Admin, ProductArea1Add, SpudAdmin, SpudAdd, SpudEdit, SpudDelete, \
    ProgramAdmin, ProgramAdd, ProgramEdit, ProgramDelete, ProductArea1Admin, ProductArea1Add, ProductArea1Edit, ProductArea1Delete, \
    ProductArea2Admin, ProductArea2Add, ProductArea2Edit, ProductArea2Delete, TechnologyAdmin, UnlockAdmin, UnlockConfigAdmin, \
    TechnologyAdd, TechnologyEdit, TechnologyDelete, RFAdmin, RFAdd, RFEdit, RFDelete
from BoMConfig.views.customer_audit import CustomerAuditTableValidate, \
    CustomerAudit, CustomerAuditLand, CustomerAuditUpload
from BoMConfig.views.maintenance import Maintenance
