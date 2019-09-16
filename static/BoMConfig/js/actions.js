    /**
* Created by epastag on 7/11/2016.
*/

$('a.headtitle:contains("Actions")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

document.createEvent("CustomEvent").initCustomEvent('pcbm.modal.formdisplay', false, false, {});

var iIndex = -1;
var keys=[];
var returnedFormData = null;
var approvalFormData = {};

// S-12405:Actions & Approvals adjustments - Declared baseline filter field globally
var $child = $('#basefil');
function cleanDataCheck(link){
    if (link.target == "_blank"){
        window.open(link.dataset.href);
    } else {
        window.location.href = link.dataset.href;
   }
}
//S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added below function to populate CU in document page
function customer_filter(customer){
    if(customer !== 'All') {
        $('#cust_filter').html(customer +" <span class=\"caret\"></span>");
        baselineonselectcuactive();
    } else {
        $('#cust_filter').html('Customer <span class="caret"></span>');
    }
    updateFiltersActive();
}
function cust_filter(customer){
    if(customer !== 'All') {
        $('#cu_filter').html(customer +" <span class=\"caret\"></span>");
// S-12405:Actions & Approvals adjustments - Removed the code space here as the baseline field will get populated based on CNAME selection
    } else {
        $('#cu_filter').html('Customer <span class="caret"></span>');
    }
    updateFilters();
}

// S-12405:Actions & Approvals adjustments - Added below block to function Baseline field filter accordingly
function catalog_filter(){
    if($("#basefil").val() !== "All"){
        $("#baseline_filter").html($("#basefil").val() + "&nbsp;<span class='caret'></span>");

    } else {
        $('#baseline_filter').html('Catalog <span class="caret"></span>');
    }
    updateFilters();
}

//S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added baselineonselectcuactive() to populate baseline dropdown based on selected CU
function baselineonselectcuactive(){
            var cu=  $('#cust_filter').text().trim().replace(/&/g, "_").replace(/ /g, '-_');
            $.ajax({
            url: action_active_customer_url,
            type: "POST",
            data: {
                data: cu,
                page: 'actions'         // S-12405:Actions & Approvals adjustments - Added this parameter so that the call can be recognised for which page
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {

            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
                console.log('Error returned from list call', status, error);
            }
        });
}

// D-04023-Customer filter on Actions issue for Admin users :- Added baselineonselectcu() to populate baseline dropdown based on selected CU
function baselineonselectcu(){
            var cu=  $('#cu_filter').text().trim().replace(/&/g, "_").replace(/ /g, '-_');
            $.ajax({
            url: action_inprocess_customer_url,
            type: "POST",
            data: {
                data: cu
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
                console.log('Error returned from list call', status, error);
            }
        });
}
//S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added req_filter() to populate request type in Document page
function req_filter(request){
    if(request !== "All"){
        $("#req_filter").html(request + "&nbsp;<span class='caret'></span>");
    }
    else{
        $("#req_filter").html("Request Type" + "&nbsp;<span class='caret'></span>");
    }
    updateFiltersActive();
}

function request_filter(request){
    if(request !== "All"){
        $("#request_filter").html(request + "&nbsp;<span class='caret'></span>");
    }
    else{
        $("#request_filter").html("Request Type" + "&nbsp;<span class='caret'></span>");
    }
    updateFilters();
}

// S-12405:Actions & Approvals adjustments - Added below block to populate catalog filter based on CNAME selection
function populateCatalogonCname(cname,index){
     var endstr = 'active';
            var end = window.location.href.indexOf("active");
            if(end > -1){
                 var pagename = 'actions_active';
            }else{
                 var pagename = 'actions';
            }
    index = typeof(index) !== 'undefined' ? index : 0;
    $.ajax({
            url: action_customername_baseline_url,
            type: "POST",
            dataType: "json",
            data: {
                custname: cname,
                page: pagename
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {

                $('#basefil').find('option:gt(' + index + ')').remove();

                $('#baseline_filter').replaceWith('<select id="basefil" type="button" name="basefil" onChange ="catalog_filter()" style="background-color:#DDDDDD; border:1px solid transparent;" class="btn dropdown-toggle" data-toggle="dropdown">Catalog<option value="All">All</option></select>');
                for (var key in data){
                    if(data.hasOwnProperty(key)){
                          $('#basefil').append('<option style="background-color:white; border-radius:4px; " value="' + key + '">'+data[key]);
                    }
                }
            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
                console.log('Error returned from list call', status, error);
            }
    });
}

// S-12405:Actions & Approvals adjustments - Added below block to function customer name filter accordingly
function custname_filter(custname){
    if(custname !== 'All') {
        $('#cname_filter').html(custname +"<span class=\"caret\"></span>");
    } else {
        $('#cname_filter').html('Customer Name<span class="caret"></span>');
    }
    updateFilters();
    populateCatalogonCname(custname);
}

function updateFilters(){
    var customer = $('#cu_filter').text().trim().replace(/&/g, "_").replace(/ /g, '-_');
    var request = $("#request_filter").text().trim();
    // S-12405:Actions & Approvals adjustments - Added below line to pick the text on page load
    var baseline1 = $("#baseline_filter").text();
    // S-12405:Actions & Approvals adjustments - Added below line to pick the baseline value on selection
    var baseline2 = $("#basefil").val();
    if(baseline1){
        baseline = baseline1.trim();
    }else{
        baseline = baseline2.trim();
    }

    var cuname = $('#cname_filter').text();

    $('tbody tr').show();
     var endstr = 'active';
            var end = window.location.href.indexOf("active");
            if(end > -1){
                 var rows = $('#document_records tbody tr').toArray();
            }else{
                 var rows = $('#in_process_records tbody tr').toArray();
            }

    for (var row in rows) {
        let hide = false;
        // S-12405:Actions & Approvals adjustments - Deleted customer unit condition block since,filtering happens on new page redirection

        // S-12405: Actions & Approvals adjustments - Added below for customer name
        if(cuname !== "Customer Name" && !$(rows[row]).hasClass(cuname)){
                hide = true;
        }

// S-11553: Actions tab changes : Changed Baseline to Catalog when we select All
// S-12405: Actions & Approvals adjustments - Changed condition block for baseline filtering
          if(baseline !== "Catalog" && baseline !== "All" && !$(rows[row]).hasClass(baseline)){
                hide = true;
        }

        if(request !== "Request Type"){
            var request_row = $(rows[row]).find('td:nth-of-type(11):contains("' + request + '")');
            if (!(request_row.length !== 0 && $(request_row[0]).text() == request)) {
                hide = true;
            }
        }

        if (hide){
            $(rows[row]).hide();
            $(rows[row]).find('input').removeAttr('checked');
        }
    }
}

//S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added req_filter() to populate baseline in Document page
function base_filter(baseline){
    if(baseline !== "All"){
        $("#base_filter").html(baseline + "&nbsp;<span class='caret'></span>");
    }
    else{
//   S-11553: Actions tab changes : Changed Baseline to Catalog when we select All
        $("#base_filter").html("Catalog" + "&nbsp;<span class='caret'></span>");
    }
    updateFiltersActive();
}

function baseline_filter(baseline){
    if(baseline !== "All"){
        $("#baseline_filter").html(baseline + "&nbsp;<span class='caret'></span>");
    }
    else{
  //   S-11553: Actions tab changes : Changed Baseline to Catalog when we select All
        $("#baseline_filter").html("Catalog" + "&nbsp;<span class='caret'></span>");
    }
    updateFilters();
}
//S-10575: Add 3 filters for Customer, Baseline and Request Type  in Documents Tab: Added updateFiltersActive() for updating filter/view in Document page
function updateFiltersActive(){
    var customer = $('#cust_filter').text().trim().replace(/&/g, "_").replace(/ /g, '-_');
    var request = $('#req_filter').text().trim();
    var baseline = $('#base_filter').text().trim();

    $('tbody tr').show();

    var rows = $('#document_records tbody tr').toArray();

    for (var row in rows) {
        let hide = false;
        if(customer !== "Customer" && !$(rows[row]).hasClass(customer)){
            hide = true;
        }
        //   S-11553: Actions tab changes : Changed Baseline to Catalog when we select All
        if(baseline !== "Catalog"){
            var baseline_row = $(rows[row]).find('td:nth-of-type(3):contains("' + baseline + '")');
            if (!(baseline_row.length !== 0 && $(baseline_row[0]).text() == baseline)){
                hide = true;

            }
        }

        if(request !== "Request Type"){
            var request_row = $(rows[row]).find('td:nth-of-type(4):contains("' + request + '")');
            if (!(request_row.length !== 0 && $(request_row[0]).text() == request)) {
                hide = true;
            }
        }

        if (hide){
            $(rows[row]).hide();
            $(rows[row]).find('input').removeAttr('checked');
        }
    }
}


function process(action){
    var records = [];

    if(action === 'send_to_approve' || action === 'delete' || action === 'hold' || action === 'cancel') {
        $('.inprocess:checked').each(function (index, element) {
            records.push(element.dataset.index);
        });
    } else if (action === 'clone'){
        $('.active:checked').each(function (index, element) {
            records.push(element.dataset.index);
        });
    } else if (action === 'unhold'){
        $('.hold:checked').each(function (index, element) {
            records.push(element.dataset.index);
        });
    }

    if(action === 'send_to_approve'){
        $('#myModal').modal('show');
        $.ajax({
            url: approve_list_url,
            type: "POST",
            data: {
                data: JSON.stringify(records)
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                keys = Object.keys(data);
                returnedFormData = data;
                $('#myModal').one('hidden.bs.modal', function(){
                    $(document).trigger('pcbm.modal.formdisplay');
                });
                $('#myModal').modal('hide');
            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
                console.log('Error returned from list call', status, error);
            }
        });
    } else {
        $.ajax({
            url: approve_url,
            type: "POST",
            data: {
                action: action,
                data: JSON.stringify(records)
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                if(data){
                    location.href = data;
                } else {
                    location.reload(true);
                }
            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
                messageToModal('Submission Error','The following error occurred during submission:<br/>' +
                    status + ": " + error + '<br/>Please try again or contact a tool admin.', function(){});
            }
        });
    }
}

function credentialTest(event){
    if($('input#sap_username').val() != '' && $('input#sap_password').val() != ''){
        $('#messageModal button.modal_submit').removeAttr('disabled');
    } else {
        $('#messageModal button.modal_submit').attr('disabled','disabled');
    }
}

$(document).ready(function(){
    $('#approval_submit').click(function(){
        if($('.inprocess:checked').length > 0) {
            messageToModal('Confirm submission','Are you sure you wish to submit the selected records for approval?', function(source){
                returnedFormData = null;
                iIndex = -1;
                approvalFormData = {};
                $('#messageModal').one('hidden.bs.modal', function(){
                    process($(source).val());
               });
            }, this);
        } else {
            messageToModal('Error','Please select at least 1 record for approval.', function(){});
        }
    });

    $('#cancel').click(function(){
        if($('.inprocess:checked').length > 0) {
            messageToModal('Confirm cancellation','Are you sure you wish to cancel the selected records?', function(source){
                $('#myModal').modal('show');
                process($(source).val());
            }, this);
        } else {
           messageToModal('Error','Please select at least 1 record for cancellation.', function(){});
        }
    });

    $('#delete').click(function(){
        if($('.inprocess:checked').length > 0) {
            messageToModal('Confirm deletion','STOP!!! Are you sure you wish to delete the selected records? This is permanent and CANNOT be undone.', function(source){
                $('#myModal').modal('show');
                process($(source).val());
            }, this);
        } else {
            messageToModal('Error','Please select at least 1 record for deletion.', function(){});
        }
    });

    $('#clone').click(function(){
        if($('.active:checked').length === 1) {
            messageToModal('Confirm cloning','Are you sure you wish to clone the selected record?', function(source){
                $('#myModal').modal('show');
                process($(source).val());
            }, this);
        } else {
            messageToModal('Error','Please select a single record for cloning.', function(){});
        }
    });

    $('#hold').click(function(){
        if($('.inprocess:checked').length > 0) {
            messageToModal('Confirm hold','Are you sure you wish to place the selected records on hold?', function(source){
                $('#myModal').modal('show');
                process($(source).val());
            }, this);
        } else {
            messageToModal('Error','Please select at least 1 record to place on hold.', function(){});
        }
    });

    $('#unhold').click(function(){
        if($('.hold:checked').length > 0) {
            messageToModal('Confirm hold release','Are you sure you wish to release the selected records from hold?', function(source){
                $('#myModal').modal('show');
                process($(source).val());
            }, this);
        } else {
            messageToModal('Error','Please select at least 1 record to release from hold.', function(){});
        }
    });

    $(document).on("change", '#toggle_pass', function(event){
        var curVal = $('#sap_password').val();

        if($(event.target).prop('checked')){
            $('#sap_password').attr('type', 'text');
        } else {
            $('#sap_password').attr('type', 'password');
        }

        $('#sap_password').val(curVal);
    });

    $('.doc_button').click(function(){
        var title = 'Confirm document ' + (this.dataset.update=="0"?"creation":"update");
        var message = '<p>You are about to ' + (this.dataset.update=="0"?"create":"update") + ' a(n) ' + (this.dataset.type == "0" ? "Inquiry" : "Site Template") + ' for ' + $($(this).parent().siblings()[1]).text() + '.  Are you sure?</p>';

        if (this.dataset.type=="0" && this.dataset.pdf_allowed=="1") {
            message += '<label for="makepdf">Create PDF:&nbsp;&nbsp;</label><input id="makepdf" type="checkbox"/>';
        }

        var data = {};
        messageToModal(title, message, function(source){
            data = {
                    id: source.dataset.id,
                    type: source.dataset.type,
                    update: source.dataset.update,
                    pdf: $('#makepdf').prop('checked')
                };
            $('#messageModal').one('hidden.bs.modal', function () {
                messageToModal('SAP Credentials',
                    '<p>Please enter your SAP username and password:</p>'+
                    '<label for="sap_username">Username</label>&nbsp;&nbsp;<input type="text" id="sap_username" name="username" oninput="credentialTest()"/><br/>'+
                    '<label for="sap_password">Password</label>&nbsp;&nbsp;<input type="password" id="sap_password" name="password" oninput="credentialTest()"/><br/>'+
                    '<input type="checkbox" id="toggle_pass" name="passwordtoggle"/><label for="toggle_pass">Show characters</label>',
                    function(){
                        data['user'] = $('#sap_username').val();
                        data['pass'] = $('#sap_password').val();
                        $('#messageModal').one('hidden.bs.modal', function () {
                            $.ajax({
                                url: doc_url,
                                type: "POST",
                                data: data,
                                headers: {
                                    'X-CSRFToken': getcookie('csrftoken')
                                },
                                success: function () {
                                    window.location.reload(true);
                                },
                                error: function (xhr, status, error) {
                                    if (xhr.status == 409 && error == "Invalid replacement"){
                                        messageToModal("Replacement document missing / in-work", "The record replacing this record has no SAP document number or the document is currently being created. Please allow the document to finish before proceeding.");
                                    } else {
                                        messageToModal("Unknown error", "An error occurred while attempting to process you request.  If this continues, please request support via the Support button");
                                    }
                                }
                            });
                        });
                    }
                );
                $('#messageModal button.modal_submit').attr('disabled','disabled');
            });
        }, this);
    });

    $(document).on("pcbm.modal.formdisplay", processForms);

    $('#messageModal').on('keyup afterShow change', 'input[name$="-email"]', function(event){
        var test = event.target.value;
        var email_regex = /^[-a-z0-9~!$%^&*_=+}{\'?]+(\.[-a-z0-9~!$%^&*_=+}{\'?]+)*@([a-z0-9_][-a-z0-9_]*(\.[-a-z0-9_]+)*\.(aero|arpa|biz|com|coop|edu|gov|info|int|mil|museum|name|net|org|pro|travel|mobi|[a-z][a-z])|([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}))(:[0-9]{1,5})?$/i

        if (!email_regex.test(test)){
            $(event.target).addClass('input-invalid');
        } else {
            $(event.target).removeClass('input-invalid');
        }

        if($('#messageModal .input-invalid').length > 0){
            $('.modal_submit.btn.btn-primary').attr('disabled','disabled');
        } else {
            $('.modal_submit.btn.btn-primary').removeAttr('disabled');
        }
    });

    $('#messageModal').on('afterHide', 'input[name$="-email"]', function(event){
        $(event.target).removeClass('input-invalid');

        if($('#messageModal .input-invalid').length > 0){
            $('.modal_submit.btn.btn-primary').attr('disabled','disabled');
        } else {
            $('.modal_submit.btn.btn-primary').removeAttr('disabled');
        }
    });

    $('#messageModal').on('hidden.bs.modal', function(){
        $('.modal_submit.btn.btn-primary').removeAttr('disabled');
    });

    $('.approval div').mouseenter(function(e) {
        var hovertext ='';
        if($(this).find('.glyphicon').length > 0){
            xhr = $.ajax({
                url: approval_url,
                type: "POST",
                data: {
                    id: this.dataset.id,
                    level: this.dataset.level
                },
                headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                success: function(data) {
                    hovertext = 'By: ' + data.person + "<br/>";

                    if(data.type != 'S'){
                        hovertext += "On: " + data.date + "<br/>";
                        hovertext += 'Comments: ' + data.comments + "<br/>";
                        if(data.type == 'A'){
                            $('#hintBox').css('background-color', 'rgba(0,150,0,0.9)');
                        } else {
                            $('#hintBox').css('background-color', 'rgba(150,0,0,0.9)');
                        }
                    } else {
                        $('#hintBox').css('background-color', 'rgba(0,0,0,0.9)');
                    }
                    xhr = undefined;
                    $('#hintBox').html(hovertext).show();
                    var y_location;
                    if(e.clientY + 20 + $('#hintBox').outerHeight() > $(window).height()){
                        y_location = e.pageY - 10 - $('#hintBox').outerHeight();
                    } else {
                        y_location = e.pageY + 20;
                    }
                    $('#hintBox').css('top', y_location).css('left', e.pageX-210);
                },
                error: function(){
                    hovertext = '<span>Could not find</span>';
                    $('#hintBox').css('background-color', 'rgba(0,0,0,0.9)');
                }
            });
        }
    }).mousemove(function(e){
        var y_location;
        if(e.clientY + 20 + $('#hintBox').outerHeight() > $(window).height()){
            y_location = e.pageY - 10 - $('#hintBox').outerHeight();
        } else {
            y_location = e.pageY + 20;
        }
        $('#hintBox').css('top', y_location).css('left', e.pageX-210);
    }).mouseleave(function() {
        $('#hintBox').hide();
        if (xhr !== undefined){
            xhr.abort();
            xhr = undefined;
        }
    });

    //changes done for-- to open single popup to send notification for multiple models
    function processForms(){
        //S-05766:Identify Emails from Test System---Added to check the window URL
        var windowurlval = '';
        if(window.location.href.indexOf('localhost')!=-1){          //for local
            windowurlval='local';
        }else if(window.location.href.indexOf('eusaalx0054')!=-1){      //for test
            windowurlval='test';
        }else{
             windowurlval='prod';                                       //for prod
        }
        if (returnedFormData == null){

        } else if ((iIndex + 1) >= keys.length) {
            $('#myModal').modal('show');
            $.ajax({
                url: approve_url,
                type: "POST",
                data: {
                    action: 'send_to_approve',
                    windowurl: windowurlval,                               //S-05766:Identify Emails from Test System---sending the current window url as a parameter to back end
                    data: JSON.stringify(keys),
                    approval: JSON.stringify(approvalFormData)
                },
                headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                success: function(data) {
                    if(data){
                        location.href = data;
                    } else {
                        location.reload(true);
                    }
                },
                error: function(xhr, status, error){
                    $('#myModal').modal('hide');
                    messageToModal('Submission Error','The following error occurred during record submission.<br/>' +
                       status + ": " + error + '<br/>If the error continues, contact a tool admin.', function(){});
                }
            });
        } else {
            iIndex++;

            if(keys.length == 1){
                    var message = 'Select Approval levels and desired Points of Contact ' + returnedFormData[keys[iIndex]][0];
//                messageToModal('Select Approval levels and desired Points of Contact ' + returnedFormData[keys[iIndex]][0], returnedFormData[keys[iIndex]][1], function () {
           }else{
                    var message = 'Select Approval levels and desired Points of Contact for selected models';
           }


            messageToModal(message,  returnedFormData[keys[iIndex]][1], function () {

                for (var iIndex=0; iIndex<keys.length;iIndex++){
                approvalFormData[keys[iIndex]]={};
                for (var i=0; i < approval_levels.length; i++){
                    approvalFormData[keys[iIndex]][approval_levels[i]]=[];
                    approvalFormData[keys[iIndex]][approval_levels[i]][0]= String($("input[name='" + approval_levels[i] + "']").prop('checked'));
                    approvalFormData[keys[iIndex]][approval_levels[i]][1]= $("select[name='" + approval_levels[i] + "-notify" + "']").val();
                    approvalFormData[keys[iIndex]][approval_levels[i]][2]= $("input[name='" + approval_levels[i] + "-email" + "']").val();
                }
//                 iIndex++;
                 }
//                $('#messageModal').one('hidden.bs.modal', function () {
//                    $(document).trigger('pcbm.modal.formdisplay');
//                });

            if ((iIndex) >= keys.length) {
            $('#myModal').modal('show');
            $.ajax({
                url: approve_url,
                type: "POST",
                data: {
                    action: 'send_to_approve',
                    windowurl: windowurlval,                                //S-05766:Identify Emails from Test System---sending the current window url as a parameter to back end
                    data: JSON.stringify(keys),
                    approval: JSON.stringify(approvalFormData)
                },
               headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                success: function(data) {
                    if(data){
                        location.href = data;
                    } else {
                        location.reload(true);
                    }
                },
                error: function(xhr, status, error){
                    $('#myModal').modal('hide');
                    messageToModal('Submission Error','The following error occurred during record submission.<br/>' +
                        status + ": " + error + '<br/>If the error continues, contact a tool admin.', function(){});
                }
            });
            }
            });
        }
    }
});

