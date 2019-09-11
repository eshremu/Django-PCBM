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
    # S-11552: Baseline tab changes : Changed to Catalog
    {'title':"Catalog","destination":"bomconfig:baseload"},
    {'title':"Pricing","destination":"bomconfig:pricing"},
    {'title':"Actions","destination":"bomconfig:action"},
    {'title':"Approvals","destination":"bomconfig:approval"},
    {'title':"Customer Audit","destination":"bomconfig:customeraudit"},
    {'title':"Admin","destination":"bomconfig:adminlanding"},
# S-12373- Add to the tools tab the following links:ESR,Portfolio & Commerce.
    {'title':"Tools","children":[
        {'title':'REACT', 'destination':'http://eusaamw0065/REACT_test/default.asp?timesin=1', 'target':'_blank'},
        {'title': 'WFMS', 'destination': 'http://webopen2.bs.sw.ericsson.se/WFMS.Web/SubmitItem', 'target': '_blank'},
        {'title': 'ESR', 'destination': 'https://siterollout.ericsson.net/', 'target': '_blank'},
        {'title': 'Portfolio & Commerce', 'destination': 'https://portfolio.ericsson.net/', 'target': '_blank'},
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
