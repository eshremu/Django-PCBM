"""
URL routing definitions for tool
"""

from django.conf.urls import url, patterns
from django.contrib.auth import views as auth_views
from BoMConfig import views

urlpatterns = patterns(
    '',
    url(r'^$', views.Index, name='index'),
    url(r'^entry/$', views.AddHeader, name='entry'),
    url(r'^entry/header/$', views.AddHeader,
        {'sTemplate': 'BoMConfig/configheader.html'}, name='configheader'),
    url(r'^entry/config/$', views.AddConfig, name='config'),
    url(r'^entry/toc/$', views.AddTOC, name='configtoc'),
    url(r'^entry/revision/$', views.AddRevision, name='configrevision'),
    url(r'^entry/inquiry/$', views.AddInquiry, {'inquiry': True},
        name='configinquiry'),
    url(r'^entry/sitetemplate/$', views.AddInquiry, {'inquiry': False},
        name='configsite'),
    url(r'^entry/clone/$', views.Clone, name='configclone'),
    url(r'^search/$', views.Search, name='search'),
    url(r'^search/adv/$', views.Search, {'advanced': True}, name='searchadv'),
    url(r'^pricing/$', views.PartPricing, name='pricing'),
    url(r'^pricing/download/$', views.PartPriceDownload,
        name='pricingdownload'),
    url(r'^pricing_config/$', views.ConfigPricing, name='configpricing'),
# S-11537: Multi Config sub tab - UI for Multiple Config tab :- Added below MultConfigPricing to show multiple configs
    url(r'^multi_config_pricing/$', views.MultiConfigPricing, name='multiconfigpricing'),
# S-11538: Open multiple revisions for each configuration - UI Elements :- Added below to show multiple revisions for each config
    url(r'^pricing_config/mult/$', views.MultiRevConfigPricing, name='multirevconfigpricing'),
    url(r'^pricing_config/download/$', views.ConfigPriceDownload,
        name='configpricingdownload'),
#S-11779- Multiconfig sub tab, download functionality
    url(r'^multi_config_pricing/download/$', views.MultiConfigPriceDownload, name='multiconfigpricingdownload'),
    url(r'^pricing_report/$', views.OverviewPricing, name='basepricing'),
    url(r'^pricing_report/download/$', views.PriceOverviewDownload,
        name='pricingoverviewdownload'),
    url(r'^pricing_erosion/$', views.PriceErosion, name='erosionpricing'),
    url(r'^pricing_erosion/search/$', views.ErosionAjax, name='erosionajax'),
    url(r'^pricing_erosion/download/$', views.ErosionDownload,
        name='erosiondownload'),
    url(r'^reporting/$', views.Report, name='reporting'),
    url(r'^approvals/$', views.Approval, name='approval'),
    url(r'^approvals/hold/$', views.ApprovalHold, name='approval_hold'),
    url(r'^actions/$', views.Action, name='action'),
    url(r'^actions/inprocess/$', views.Action, {'type':'inprocess'},
        name='action_inprocess'),
 # D-04023-Customer filter on Actions issue for Admin users :- Added below url to redirect to this page based on selected CU
    url(r'^actions/inprocess/customer/(?P<iCustId>\d+)/$', views.ActionCustomer, name='action_inprocess_customer'),
    url(r'^actions/active/$', views.Action, {'type':'active'},
        name='action_active'),
# S-10575: Add 3 filters for Customer, Baseline and Request Type in Documents Tab: Added below url to redirect to this page based on selected CU
    url(r'^actions/active/customer/(?P<iCustId>\d+)/$', views.ActiveCustomer, name='action_active_customer'),
    url(r'^actions/hold/$', views.Action, {'type':'hold'}, name='action_hold'),
    url(r'^actions/changepart/$', views.Action, {'type': 'changepart'},
        name='action_changepart'),
    url(r'^actions/changepart/post/$', views.ChangePart,
        name='action_changepart_post'),
    url(r'^login/$', views.Login, name='login'),
    url(r'^validate/$', views.Validator, name='validator'),
    url(r'^download/$', views.Download, name='download'),
    url(r'^downloadmulti/$', views.DownloadMultiple, name='downloadmulti'),
    url(r'^downloadresult/$', views.DownloadSearchResults,
        name='downloadresult'),
    url(r'^reactsearch/$', views.ReactSearch, name='reactsearch'),
    url(r'^upload/$', views.Upload, name='upload'),
    url(r'^baseline/$', views.BaselineMgmt, name='baseline'),
    url(r'^baselinedelete/$', views.DeleteBaseline, name='baselinedelete'),
    url(r'^baseload/$', views.BaselineLoad, name='baseload'),
    url(r'^baselinedwnld/$', views.DownloadBaseline, name='baselinedownload'),
    url(r'^baselinemasterdwnld/$', views.DownloadBaselineMaster,
        name='baselinemasterdownload'),
    url(r'^baselinerollback/$', views.BaselineRollback,
        name='baselinerollback'),
    url(r'^baselinerollbackcheck/$', views.BaselineRollbackTest,
        name='baselinerollbacktest'),
    url(r'^document/$', views.CreateDocument, name='document_create'),
    url(r'^unlock/$', views.FinalUnlock, name='finalunlock'),
    url(r'^lock/$', views.InitialLock, name='initlock'),
    url(r'^logout/$', views.Logout, name='logout'),
    url(r'^list_fill/$', views.ListFill, name='list_fill'),
    url(r'^list_react_fill/$', views.ListREACTFill, name='list_react_fill'),
    url(r'^approve/$', views.AjaxApprove, name='approve'),
# S-08947: Add filter functionality to show only on hold records and  S-08477: Add button for On hold filter /
    #  added below url
    url(r'^approve/hold/$', views.HoldApprove, name='approve_hold'),
    url(r'^approval_data/$', views.ApprovalData, name='approve_info'),
    url(r'^approval_list/$', views.AjaxApprovalForm, name='approve_list'),
    url(r'^password_change/$', auth_views.password_change,
        {'post_change_redirect': 'bomconfig:index'}, name='change_password'),
    url(r'^admin/mailing/$', views.MailingAdmin, name='mailadmin'),
    url(r'^admin/mailing/change/(?P<iRecordId>\d+)/$', views.MailingChange,
        name='mailchange'),
    url(r'^admin/mailing/add/$', views.MailingChange, name='mailadd'),
# Added below line for S-07533 New sub-tab drop-down admin base template creation
    url(r'^admin/dropdown/$', views.DropDownAdmin, name='dropdownadmin'),
# S-10578: Admin to unlock a locked config:- Added below to open unlock admin page with the list of locked configs
    url(r'^admin/unlock/$', views.UnlockAdmin, name='unlockadmin'),
# S-10578:-Admin to unlock a locked config: Added below to call the function with the functionality for unlocking the locked configs
    url(r'^admin/unlock/unlockconfig$', views.UnlockConfigAdmin, name='unlockconfigadmin'),
# S-05903, S-05905, S-05906, S-05907, S-05908,S-05909:- Added From 'productarea1admin' to 'radiofrequencybanddelete' for Admin dropdown functionalities
    url(r'^admin/dropdown/productarea1/$', views.ProductArea1Admin, name='productarea1admin'),
    url(r'^admin/dropdown/productarea1/add$', views.ProductArea1Add, name='productarea1add'),
    url(r'^admin/dropdown/productarea1/edit$', views.ProductArea1Edit, name='productarea1edit'),
    url(r'^admin/dropdown/productarea1/delete$', views.ProductArea1Delete, name='productarea1delete'),
    url(r'^admin/dropdown/productarea2/$', views.ProductArea2Admin, name='productarea2admin'),
    url(r'^admin/dropdown/productarea2/add$', views.ProductArea2Add, name='productarea2add'),
    url(r'^admin/dropdown/productarea2/edit$', views.ProductArea2Edit, name='productarea2edit'),
    url(r'^admin/dropdown/productarea2/delete$', views.ProductArea2Delete, name='productarea2delete'),
    url(r'^admin/dropdown/spud/$', views.SpudAdmin, name='spudadmin'),
    url(r'^admin/dropdown/spud/add$', views.SpudAdd, name='spudadd'),
    url(r'^admin/dropdown/spud/edit$', views.SpudEdit, name='spudedit'),
    url(r'^admin/dropdown/spud/delete$', views.SpudDelete, name='spuddelete'),
    url(r'^admin/dropdown/program/$', views.ProgramAdmin, name='programadmin'),
    url(r'^admin/dropdown/program/add$', views.ProgramAdd, name='programadd'),
    url(r'^admin/dropdown/program/edit$', views.ProgramEdit, name='programedit'),
    url(r'^admin/dropdown/program/delete$', views.ProgramDelete, name='programdelete'),
    url(r'^admin/dropdown/technology/$', views.TechnologyAdmin, name='technology'),
    url(r'^admin/dropdown/technology/add/$', views.TechnologyAdd, name='addtechnology'),
    url(r'^admin/dropdown/technology/change/$', views.TechnologyEdit, name='changetechnology'),
    url(r'^admin/dropdown/technology/delete/$', views.TechnologyDelete, name='deletetechnology'),
    url(r'^admin/dropdown/radiofrequencyband/$', views.RFAdmin, name='radiofrequencybandadmin'),
    url(r'^admin/dropdown/radiofrequencyband/add$', views.RFAdd, name='radiofrequencybandadd'),
    url(r'^admin/dropdown/radiofrequencyband/edit$', views.RFEdit, name='radiofrequencybandedit'),
    url(r'^admin/dropdown/radiofrequencyband/delete$', views.RFDelete, name='radiofrequencybanddelete'),
    url(r'^admin/user/$', views.UserAdmin, name='useradmin'),
    url(r'^admin/user/add/$', views.UserAdd, name='useradd'),
# S-07204:- Refine User Admin page: Added delete button logic  in user admin page
    url(r'^admin/user/delete/$', views.UserDelete, name='userdelete'),
    url(r'^admin/user/changeuser/(?P<iUserId>\d+)$', views.UserChange,
        name='userchange'),
# S-10578:-Admin to unlock a locked config: Added below to redirect to userchange page on clicking username from unlock page
    url(r'^admin/user/changeuser/(?P<iUserName>\w+)$', views.UserChangeFromUnlock, name='userchangefromunlock'),
    url(r'^admin/$', views.AdminLanding, name='adminlanding'),
    url(r'^admin/approval/$', views.ApprovalAdmin, name='approvaladmin'),
    url(r'^admin/approval/add/$', views.ApprovalChange, name='approvaladd'),
    url(r'^admin/approval/change/(?P<iObjId>\d+)/$', views.ApprovalChange,
        name='approvalchange'),
    url(r'^customer_audit/$', views.CustomerAuditLand,
        name='customerauditland'),
    url(r'^customer_audit/audit/$', views.CustomerAudit, name='customeraudit'),
    url(r'^customer_audit/validate/$', views.CustomerAuditTableValidate,
        name='audit_validate'),
    url(r'^customer_audit/upload/$', views.CustomerAuditUpload,
        name='customerauditupload'),
    url(r'^entry/validate/$', views.AjaxValidator, name='ajaxvalidator'),
)
