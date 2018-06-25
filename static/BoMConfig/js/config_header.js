$('button[value="header"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
var clean_form;
var form_save = false;
var attached = true;
var model_replace_changed = false;
var model_replace_initial;
var model_replace_override = false;

$(document).ready(function(){
    var max = 0;
    $('tr td:first-child').each(function(idx, elem){max = Math.max(max, $(elem).width())});
    $('tr td:first-child').each(function(idx, elem){$(elem).width(max)});
    $('#id_valid_from_date').datepicker({dateFormat: "yy-mm-dd"});
    $('#id_valid_to_date').datepicker({dateFormat: "yy-mm-dd"});
    $('#id_projected_cutover').datepicker({dateFormat: "yy-mm-dd"});

    $('#searchSubmit').click(function(){
        req_search();
    });

    $('#reactReq').keydown(function(event){
        if(event.which == 13){
            req_search();
            event.stopPropagation();
            event.preventDefault();
            event.stopImmediatePropagation();
            return false;
        }
    });

    $(window).load(function(){
        form_resize();
        attached = $('#id_configuration_designation').val() == $('#id_model').val();
    });

    $(window).on('beforeunload',function(){
        var dirty_form = $('#headerform').serialize();
        if(closeButton && dirty_form != clean_form && !form_save){
            return "You have made changes to the form.  If you navigate away from this page without saving, all changes will be lost.";
        }
    });

    $(window).resize(function(){
        form_resize();
    });

    $('#download').click(function(){
        window.open(download_url, '_blank','left=100,top=100,height=150,width=500,menubar=no,toolbar=no,location=no,resizable=no,scrollbars=no');
    });

    $('#saveForm').click(function(){
        $('#formaction').val('save');
        $('#headerform').submit();
    });

    $('#saveexitForm').click(function(){
        $('#formaction').val('saveexit');
        $('#headerform').submit();
    });

    $('#nextForm').click(function(){
        $('#formaction').val('next');
        $('#headerform').submit();
    });

    $('#headerform').submit(function(){
        if(!model_replace_override){
            var $model_replaced = $('#id_model_replaced');
            if(model_replace_changed) {
                $('#id_model_replaced_link').val($('#list_header_list [value="' + $model_replaced.val() + '"]').data('value'));
                var aMatch = String($model_replaced.val()).match(/\s\(.+\)/);
                if (aMatch && aMatch.length > 0) {
                    $model_replaced.val(String($model_replaced.val()).replace(aMatch[0], ""));
                }
            }

            if(['Update','Discontinue','Replacement'].indexOf($('#id_bom_request_type option:selected').text()) != -1){
                if($model_replaced.val() == "") {
                    messageToModal('No replaced model',
                        'Record request type is "Update", "Discontinue", or "Replacement" ' +
                        'but "What Model is this replacing?" field is blank.  Are you sure this is what you intended?',
                        function () {
                            model_replace_override = true;
                            $('#headerform').submit();
                        }
                    );
                    return false;
                } else
                if ($model_replaced.val() != $('#id_configuration_designation').val()){
                    messageToModal('Replaced model mismatch',
                        'Record request type is "Update", "Discontinue", or "Replacement" ' +
                        'but "What Model is this replacing?" field does not match the "Configuration Designation" field.  Are you sure this is what you intended?',
                        function () {
                            model_replace_override = true;
                            $('#headerform').submit();
                        }
                    );
                    return false;
                } else {
                    save_form();
                }
            } else if($('#id_bom_request_type option:selected').text() == 'New' && $model_replaced.val() != "" && !alreadyDiscontinued){
                messageToModal('Discontinuation imminent',
                    'Record request type is "New" ' +
                    'but "What Model is this replacing?" field is not blank.  This will cause the replaced model to be discontinued.  Are you sure this is what you intended?',
                    function(){
                        model_replace_override = true;
                        $('#headerform').submit();
                    }
                );
                return false;
            }else if(model_replace_changed && $('#id_model_replaced_link').val() == "") {
                messageToModal('No matching model found',
                    "The model you intend to replace is not recognized as a currently active model.  Are you sure this is what you intended?",
                    function () {
                        model_replace_override = true;
                        $('#headerform').submit();
                    }
                );
                return false;
            } else {
                save_form();
            }
        } else {
            save_form();
        }
    });

    $('#id_configuration_designation').keyup(function(){
//    Commented out below line for fix- D-03195- Model name doesn't change when Clone/Active/New
//        if(!attached && $('#id_configuration_designation').val() == $('#id_model').val()){
//            attached = true;
//        }
//
//        if(attached) {
//
//        }
        $('#id_model').val($(this).val());
    });

    $('#id_react_request').keyup(function(){
       $('#id_react_request').val($('input[name="react_request"]').val().trim());
    });

    $('#id_model').keyup(function(){
        if ($('#id_configuration_designation').val() == $('#id_model').val()){
            attached = true;
        } else {
            attached = false;
        }
    });

    $('#id_product_area1').change(function(){
        list_filler('product_area1', 'product_area2');
    });

    $('#id_customer_unit').change(function(){
        list_react_filler('customer_unit', 'customer_name');
        list_filler('customer_unit', 'program');
        list_filler('customer_unit', 'baseline_impacted', 1);
    });

    $('#id_baseline_impacted').change(function(){
        if ($(this).val() === 'New'){
            $('#new_baseline').removeAttr('style');

        } else {
            $('#new_baseline').attr('style','display:none;');
            $('#new_baseline').val('');
        }
    });

    $('#id_radio_frequency').change(function(){
        $('#id_radio_band').val($(this).val());
    });

    $('#id_radio_band').change(function(){
        $('#id_radio_frequency').val($(this).val());
    });

    $('#id_model_replaced').change(function(){
        model_replace_changed = $(this).val() != model_replace_initial;
    });

    clean_form = $('#headerform').serialize();
    model_replace_initial = $('#id_model_replaced').val();
});

function cleanDataCheck(link){
    var dirty_form = $('#headerform').serialize();
    if(dirty_form != clean_form && !form_save){
        messageToModal('Unsaved changes detected',
                "You have made changes to the form.  If you navigate away from this page without saving, all changes will be lost.",
                function(){
                    if (link.target == "_blank"){
                        window.open(link.dataset.href);
                    } else {
                        window.location.href = link.dataset.href;
                    }
                }
        );
    } else {
        if (link.target == "_blank"){
            window.open(link.dataset.href);
        } else {
            window.location.href = link.dataset.href;
        }
    }
}

function list_filler(parent, child, index){
    index = typeof(index) !== 'undefined' ? index : 0;

    if($('#id_' + parent).val() != ''){
        $.ajax({
            url: listfill_url,
            dataType: "json",
            type: "POST",
            data: {
                parent: parent,
                id: $('#id_' + parent).val(),
                child: child
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
                for (var key in data){
                    if(data.hasOwnProperty(key)){
                        $child.append($('<option>',{value:key.toString().slice(1),text:data[key]}));
                    }
                }
            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    } else {
        var $child = $('#id_' + child);
        $child.find('option:gt(' + index + ')').remove();
    }
}

function list_react_filler(parent, child, index){
    index = typeof(index) !== 'undefined' ? index : 0;

    if($('#id_' + parent).val() != ''){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
            data: {
                parent: parent,
                id: $('#id_' + parent).val(),
                child: child
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
                for (var key in data){
                    if(data.hasOwnProperty(key)){
                        $child.append($('<option>',{value:key,text:data[key]}));
                    }
                }
            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    } else {
        var $child = $('#id_' + child);
        $child.find('option:gt(' + index + ')').remove();
    }
}

function form_resize(){
    var topbuttonheight = $('#action_buttons').height();
    var bottombuttonheight = $('#formbuttons').height();
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (topbuttonheight + bottombuttonheight + 6);

    $('#headerformtable').css("height", tableheight);
    $('#headerformtable').css("overflow", 'auto');
}
function save_form(){
    form_save = true;
    $('[readonly=true]').removeAttr('readonly');
    $('[disabled=true]').removeAttr('disabled');
    clean_form = $('#headerform').serialize();
}
function req_search(){
    if($(reactrequest_id).val() == null || $(reactrequest_id).val() == ''){
        messageToModal('', 'Please provide a REACT request number', function(){})
    } else {
        $('#myModal').modal('show');
        $.ajax({
            url: reactsearch_url,
            dataType: "html",
            type: "POST",
            data: {
                psm_req: $(reactrequest_id).val().trim()
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var returned = JSON.parse(data);
                $('#myModal').modal('hide');
                if(typeof returned.req_id === "undefined"){
                    setTimeout(function(){messageToModal('', 'No match found. Please note, you must use a complete REACT request number.', function(){});}, 300);
                } else {
                    $(personresponsible_id).val(returned.person_resp);
                    $(customername_id).val(returned.cust_name);
                    $(salesoffice_id).val(returned.sales_office.match(/^US../));
                    $(salesgroup_id).val(returned.sales_group.match(/^U../));
                    $(soldto_id).val(returned.sold_to);
                    $(shipto_id).val(returned.ship_to);
                    $(billto_id).val(returned.bill_to);
                    $(paymentterms_id).val(returned.terms);
                    $(workgroup_id).val(returned.workgroup);
                    $('#' + customerunit_id + ' option').filter(function(){return $(this).text() === returned.cust}).prop('selected', true);
                    $(customerunit_id).change();
                    $(ericssoncontract_id).val(returned.contract.match(/^\d+/));
                    setTimeout(function() {
                        $('#' + customername_id + ' option').filter(function () {
                            return $(this).text() === returned.cust_name
                        }).prop('selected', true);
                        $(customername_id).change();
                        }, 1000);
                }
            },
            error: function(xhr, status, error){
                $('#myModal').modal('hide');
            }
        });
    }
}

function cloneHeader(headerId){
    $('myModal').modal('show');
    $.ajax({
        url: clone_url,
        dataType: "json",
        type: "POST",
        data: {
            header: headerId
        },
        headers:{
            'X-CSRFToken': getcookie('csrftoken')
        },
        success: function(returned) {
            // var returned = JSON.parse(data);
            if(returned.status == 1) {
                messageToModal('Cloning completed', 'Configuration "' + returned.name + '" has been created.');
            } else {
                var errorMessage = 'The following errors occurred:';
                for(var index in returned.errors){
                    errorMessage += '<br/>' + returned.errors[index];
                }
                messageToModal('Cloning failed', errorMessage);
            }
            $('#myModal').modal('hide');
        },
        error: function(xhr, status, error){
            messageToModal('Unknown error', 'The following error occurred during cloning.<br/>' +
                status + ": " + error + '<br/>If this issue persists, contact a tool admin.');
            $('#myModal').modal('hide');
        }
    });
}
