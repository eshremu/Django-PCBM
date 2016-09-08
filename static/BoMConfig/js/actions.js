/**
 * Created by epastag on 7/11/2016.
 */

$('a.headtitle:contains("Actions")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

new Event("pcbm.modal.formdisplay", {'cancelable': false, "bubbles": false});
var iIndex = -1;
var keys=[];
var returnedFormData = null;
var approvalFormData = {};

function cleanDataCheck(link){
    window.location.href = link.dataset.href;
}

function cust_filter(customer){
    if(customer !== 'All') {
        $('tr').not('.' + customer).attr('style', 'display:none;');
        $('tr:not(".' + customer + '") input').removeAttr('checked');
        $('tr.' + customer).removeAttr('style');
        $('#cu_filter').html(customer.replace('-_',' ').replace("_","&") +" <span class=\"caret\"></span>");
    } else {
        $('tr').removeAttr('style');
        $('#cu_filter').html('Customer <span class="caret"></span>');
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

    function processForms(){
        if (returnedFormData == null){

        } else if ((iIndex + 1) >= keys.length) {
            $('#myModal').modal('show');
            $.ajax({
                url: approve_url,
                type: "POST",
                data: {
                    action: 'send_to_approve',
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
                    // returnedFormData = null;
                    // iIndex = -1;
                    // approvalFormData = {};
                    // $('#myModal').modal('hide');
                },
                error: function(xhr, status, error){
                    $('#myModal').modal('hide');
                    messageToModal('Submission Error','The following error occurred during record submission.<br/>' +
                        status + ": " + error + '<br/>If the error continues, contact a tool admin.', function(){});
                }
            });
        } else {
            iIndex++;
            messageToModal('Select Approval levels and desired Points of Contact for ' + returnedFormData[keys[iIndex]][0], returnedFormData[keys[iIndex]][1], function () {
                approvalFormData[keys[iIndex]]={};
                for (var i=0; i < approval_levels.length; i++){
                    approvalFormData[keys[iIndex]][approval_levels[i]]=[];
                    approvalFormData[keys[iIndex]][approval_levels[i]][0]= String($("input[name='" + approval_levels[i] + "']").prop('checked'));
                    approvalFormData[keys[iIndex]][approval_levels[i]][1]= $("select[name='" + approval_levels[i] + "-notify" + "']").val();
                    approvalFormData[keys[iIndex]][approval_levels[i]][2]= $("input[name='" + approval_levels[i] + "-email" + "']").val();
                }
                $('#messageModal').one('hidden.bs.modal', function () {
                    $(document).trigger('pcbm.modal.formdisplay');
                });
            });
        }
    }
});