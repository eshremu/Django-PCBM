"""
Values used in overall site creation
"""

# Values used to create navigation bar
# Each entry must provide a title of the nav button
# If button goes to a new page, provide destination
# If button should provide a dropdown list, provide children, which contains
# button destination data
menulisting = [
    {'title':"BoM Entry","destination":"bomconfig:entry"},
    {'title':"Search","destination":"bomconfig:search"},
    # S-11550 Hide upload main tab
    # {'title':"Upload","destination":"bomconfig:upload"},
    {'title':"Baseline","destination":"bomconfig:baseload"},
    {'title':"Pricing","destination":"bomconfig:pricing"},
    {'title':"Actions","destination":"bomconfig:action"},
    {'title':"Approvals","destination":"bomconfig:approval"},
    {'title':"Customer Audit","destination":"bomconfig:customeraudit"},
    {'title':"Admin","destination":"bomconfig:adminlanding"},
    {'title':"Tools","children":[
        {'title':'REACT', 'destination':'http://eusaamw0065/REACT_test/default.asp?timesin=1', 'target':'_blank'},
        {'title': 'WFMS', 'destination': 'http://webopen2.bs.sw.ericsson.se/WFMS.Web/SubmitItem', 'target': '_blank'},
        ]
    },
]
# D-05950: Support button email address change :- changed pagetitle and supportcontact
# Page title, as viewed in browser
pagetitle = "Agreed Customer Catalog"

# Email address of user contacted when pressing "Support" button
supportcontact = "manisha.mahendra@ericsson.com"

# Specifies header and footer templates, if desired
headerFile = "BoMConfig/header.html"
footerFile = "BoMConfig/footer.html"
