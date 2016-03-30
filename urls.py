from django.conf.urls import url, patterns
from django.contrib.auth import views as auth_views
from BoMConfig import views


urlpatterns = patterns(
    '',
    url(r'^$', views.Index, name='index'),
    url(r'^entry/$', views.AddHeader, name='entry'),
    url(r'^entry/header/$', views.AddHeader, {'sTemplate': 'BoMConfig/configheader.html'}, name='configheader'),
    url(r'^entry/config/$', views.AddConfig, name='config'),
    url(r'^entry/toc/$', views.AddTOC, name='configtoc'),
    url(r'^entry/revision/$', views.AddRevision, name='configrevision'),
    url(r'^entry/inquiry/$', views.AddInquiry, {'inquiry': True}, name='configinquiry'),
    url(r'^entry/sitetemplate/$', views.AddInquiry, {'inquiry': False}, name='configsite'),
    url(r'^search/$', views.Search, name='search'),
    url(r'^search/adv/$', views.Search, {'advanced': True}, name='searchadv'),
    url(r'^pricing/$', views.PartPricing, name='pricing'),
    url(r'^pricing_config/$', views.ConfigPricing, name='configpricing'),
    url(r'^pricing_report/$', views.OverviewPricing, name='basepricing'),
    # url(r'^priceretrieve/$', views.GetPartLine, name='priceretrieve'),
    url(r'^reporting/$', views.Report, name='reporting'),
    url(r'^approvals/$', views.Approval, name='approval'),
    url(r'^actions/$', views.Action, name='action'),
    url(r'^login/$', views.Login, name='login'),
    url(r'^validate/$', views.Validator, name='validator'),
    url(r'^download/$', views.Download, name='download'),
    url(r'^reactsearch/$', views.ReactSearch, name='reactsearch'),
    url(r'^upload/$', views.Upload, name='upload'),
    url(r'^baseline/$', views.BaselineMgmt, name='baseline'),
    url(r'^baselinedwnld/$', views.DownloadBaseline, name='baselinedownload'),
    url(r'^configretrieve/$', views.GetConfigLines, name='configretrieve'),
    url(r'^unlock/$', views.FinalUnlock, name='finalunlock'),
    url(r'^lock/$', views.InitialLock, name='initlock'),
    url(r'^logout/$', views.Logout, name='logout'),
    url(r'^list_fill/$', views.ListFill, name='list_fill'),
    url(r'^list_react_fill/$', views.ListREACTFill, name='list_react_fill'),
    url(r'^approve/$', views.AjaxApprove, name='approve'),
    url(r'^approval_data/$', views.ApprovalData, name='approve_info'),
    url(r'^password_change/$', auth_views.password_change, {'post_change_redirect': 'bomconfig:index'}, name='change_password')
)
