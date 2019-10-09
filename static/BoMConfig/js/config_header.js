$('button[value="header"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
var clean_form;
var form_save = false;
var attached = true;
var model_replace_changed = false;
var model_replace_initial;
var model_replace_override = false;
// D-03595 - Problem saving new configuration when using REACT data:- Added below variable to change to true only when the REACT data is getting saved
var reactsearch = false;
//D-03994-Manual override pricing fix: Added below old conf name and new conf name to distinguish between clone and normal config
var old_conf_name;
var new_conf_name;

$(document).ready(function(){
// D-07037: Catalog Impacted selection empty after catalog name length error: Added below to lines to show/hide the model description field based on error condition found
$('#modeldesc1').show();
$('#modeldesc2').hide();
//D-03994-Manual override pricing fix: Added below old conf name  to distinguish between clone and normal config
old_conf_name = $('#id_configuration_designation').val();
// S-07112 - Change dropdown selection view and value:-Added below code to show the option selected in the sales_group & ericsson contract dropdown
// when an existing configuration is opened (since only the code is fetched from DB and the code with description is present in UI)
    if(headerformsalesgroup!='' || headerformericssoncontract!='' || headerformhub!='' ){
         var $salegchild = $('#id_sales_group');
         $salegchild.find("option:contains('"+headerformsalesgroup+"')").attr("selected","selected");

         var $ericchild = $('#id_ericsson_contract');
         $ericchild.find("option:contains('"+headerformericssoncontract+"')").attr("selected","selected");

// S-11475-Add region/market areas with the hub below it :- Added below code on hub to show the saved value pre-populated on page load
         var $hubchild = $('#id_hub');
         $hubchild.find("option:contains('"+headerformhub+"')").attr("selected","selected");
    }
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

//D-03994-Manual override pricing fix:
//When cloning a config, we should copy all manual override pricing from the previous config
//When status of that config (non-picklist) is changed to "New", then manual override pricing on line 10 should be removed
//When status of a picklist is changed to "New", no change should occur to the manual override pricing
//When status of a config (non-picklist) is changed to "Discontinue", no change should occur to the manual override pricing
//Added line 73-97
new_conf_name = $('#id_configuration_designation').val();
var status_type = $('#id_bom_request_type').val();

if(!($("#id_pick_list").is(':checked'))){
 if(old_conf_name.indexOf('_______CLONE')!= -1 && status_type== 1 ){
   if(new_conf_name.indexOf('_______CLONE')== -1){
           $.ajax({
            url: checkclone_url,
            dataType: "json",
            type: "POST",
            data: {
                headerID : header_id
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
            },
            error: function(){
            }
        });
    }
 }
}
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
            }
//  D-07037: Catalog Impacted selection empty after catalog name length error: Added below to check the error condition for model description before saving
            else if($('#id_model_description').val().length > 40){
                 var vali = $('#id_model_description').val();
//                   $('#id_model_description').hide();
                   $('#moderr').show();
                   document.getElementById("modeldesc1").style.border = "2px solid red";
                   document.getElementById("modeldesc1").style.maxheight = "48px";
                   return false;
            }
    // D-03595 - Problem saving new configuration when using REACT data:- Added below condition to hit only when the REACT data is getting saved
    // i.e if value of reactsearch variable found true
            else if(reactsearch){
                save_react_form();
            }
            else {
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

//S-06166- Shift header page to new reference table:Below added to show the dependency fields on CU change,CN,Sold to,Ericsson Contract
    $('#id_customer_unit').change(function(){
        list_react_filler('customer_unit', 'customer_name');
        list_react_filler('customer_unit', 'sales_office');
        list_react_filler('customer_unit', 'sales_group');
// S-11563: BoM Entry - Header sub - tab adjustments: Added the below lines to add dependency based on CU in BoM entry page,if CU is from Tier-1
// AT&T(1),Verizon(2),Sprint(3),T-Mobile(4) then the program & baseline get populated based on selected CU
        var cunit = $('#id_customer_unit').val();
        if( cunit == 1 || cunit == 2 || cunit == 3 || cunit == 4 ){
            list_filler('customer_unit', 'program');
            list_filler('customer_unit', 'baseline_impacted', 1);
        }else{
// D-07677: Program Admin- Customer Name should be optional for all customers - added this else block since program will be populated based
// on selected CU if the CNAME is blank/none
             list_filler('customer_unit', 'program');
        }
        list_filler('customer_unit', 'person_responsible');
    });

// S-11475-Add region/market areas with the hub below it :- Added on change block of Region field to show the data of dependent field of hub
     $('#id_region').change(function(){
        list_react_filler('region', 'hub');
    });

    $('#id_customer_name').change(function(){
        list_react_filler('customer_name', 'sold_to_party');
// S-11563: BoM Entry - Header sub - tab adjustments:  Added the below lines to add dependency based on CName in BoM entry page,if CU is apart from Tier-1
// AT&T(1),Verizon(2),Sprint(3),T-Mobile(4) then the program & baseline get populated based on selected CNAME
        var cunit = $('#id_customer_unit').val();
        if( cunit != '1' && cunit != '2' && cunit != '3' && cunit != '4' ){
            list_react_filler('customer_name', 'program');
            list_react_filler('customer_name', 'baseline_impacted', 1);
        }
    });

    $('#id_sold_to_party').change(function(){
        list_react_filler('sold_to_party', 'ericsson_contract');
    });

    $('#id_ericsson_contract').change(function(){
//        list_react_filler('ericsson_contract', 'ericsson_contract_desc');
        list_react_filler('ericsson_contract', 'bill_to_party');
        list_react_filler('ericsson_contract', 'payment_terms');
    });
// S-08410:Adjust Model and BoM Header Tab:- Added below if conditions to check the line 100 value of the config
// If a new config is opened then checkbox should be checked, if existing opens then depending on the value it will show checked or unchecked
    if(isline100==''){                          // For New config on BoM entry page load
     $('#id_line_100').prop('checked', true);
    }
    if(isline100 == 'True'){                    // For existing config on opening a line 100 config
         $('#id_line_100').prop('checked', true);
    }
    if(isline100 == 'False'){                   // For existing config on opening a line 10 config
        $('#id_line_100').prop('checked', false);
    }

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

// D-04026: Baseline dropdown not populated when starting config with REACT info: Added below to populate Program & Baseline Impacted
// dropdown based on populated CU on react search
    if(reactsearch){
// S-11563: BoM Entry - Header sub-tab adjustments - Added 2 if else condition below as when react req search is done, if resultant CU is tier 1 then
// prog & catalog will get populated based on CU; if tier-2,3 then based on resultant cname; data is prepared accordingly
       if(parent == 'customer_unit'){
            parentval = $("#id_customer_unit").attr("cust_val");    // to send the ID of CU if parent is CU & done through React search
       }
       if(parent == 'customer_name'){
            parentval = $("#id_customer_name").val();    // to send the cname as the parentval when CU is not Tier 1 and dependent on cname & done through React search
       }
    }else{
        parentval = $('#id_' + parent).val();
    }

    if($('#id_' + parent).val() != ''){
        $.ajax({
            url: listfill_url,
            dataType: "json",
            type: "POST",
            data: {
                parent: parent,
                id: parentval,
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

//    if(!isNaN($('#id_' + parent).val()) && $('#id_' + parent).val() != ''){

//S-06166- Shift header page to new reference table:Added to show the change based on CU change; name,sold_to,contract_number=''
    if(parent == 'customer_unit'){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
            data: {
                parent: parent,
                id: $('#id_' + parent).val(),
                child: child,
                name:'',
                sold_to:'',
                contract_number: ''
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {

                var $child = $('#id_' + child);
                 $child.find('option:gt(' + index + ')').remove();

                if(child == 'customer_name'){
                  for (var key in data){
                    if(data.hasOwnProperty(key)){
                        $child.append($('<option>',{value:key,text:data[key]}));
                    }
                  }
                }
  //S-06166- Shift header page to new reference table:Added to show the value of the sales office field appear in the textbox
                if(child == 'sales_office'){
                    if(Object.keys(data).length!=0){
                         for (var key in data){
                            if(data.hasOwnProperty(key)){
                                 $(salesoffice_id).val(key.match(/^US../));
                            }
                         }
                    }else{
                         $(salesoffice_id).val('');
                    }
                }
                if(child == 'sales_group'){
                  for (var key in data){
                        if(data.hasOwnProperty(key)){
                            $child.append($('<option>',{value:key.match(/^U../),text:data[key]}));
                        }
                     }
                }
// S-08412:-Override pay-term selection for AT&T only with z180: Added below to populate the field with 'z180' when AT&T gets selected
                if($("#id_customer_unit").val() == 1){
                    $(paymentterms_id).val('z180');
                }else{
                    $(paymentterms_id).val('');
                }
            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    }
//    else if(isNaN($('#id_' + parent).val()) && $('#id_' + parent).val()!=''){
//S-06166- Shift header page to new reference table:Added to show the change based on CN change; id,sold_to,contract_number=''
    else if(parent == 'customer_name'){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
            data: {
                id:'',
                cu:$('#id_customer_unit').val(), // S-12408: Admin adjustments- Added this parameter to send CU value
                parent: parent,
                child: child,
                name: $('#id_' + parent).val(),
                sold_to:'',
                contract_number: ''
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();

//S-06166- Shift header page to new reference table:Added to show the value of the sold_to_party field in the textbox field
                if(child == 'sold_to_party'){
                    for (var key in data){
                        if(data.hasOwnProperty(key)){
                            $child.append($('<option>',{value:key,text:data[key]}));
                        }
                     }
                }
// S-12408: Admin adjustments- Added below 2 blocks to populate program & baseline impacted based on CName selection
                if(child == 'program'){
                    for (var key in data){
                        if(data.hasOwnProperty(key)){
                            $child.append($('<option>',{value:key.toString(),text:data[key]}));
                        }
                     }
                }

                if(child == 'baseline_impacted'){
                    for (var key in data){
                        if(data.hasOwnProperty(key)){
                            $child.append($('<option>',{value:key.toString().slice(1),text:data[key]}));
                        }
                     }
                }

            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    }
    //S-06166- Shift header page to new reference table:Added to show the change based on sold_to_party change; id,name,contract_number=''
    else if(parent=='sold_to_party'){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
            data: {
                id:'',
                parent: parent,
                child: child,
                name: '',
                sold_to:$('#id_' + parent).val(),
                contract_number: ''
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
               var $child = $('#id_' + child);

//     S-07112- Change drop down selection view and value - Added below code to show the code & description in the UI but save only the code when sent to DB
               var contractnum=0;
                $child.find('option:gt(' + index + ')').remove();
                for (var key in data){
                    if(data.hasOwnProperty(key)){
                        contractnum = key.split('-');
                        $child.append($('<option>',{value:contractnum[0],text:data[key]}));
                    }
                }
            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    }
    //S-06166- Shift header page to new reference table:Added to show the change based on Ericsson contract # change; id,name,sold_to=''
    else if(parent=='ericsson_contract'){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
           data: {
                id: '',
                parent: parent,
                child: child,
                name: '',
                sold_to:'',
                contract_number: $('#id_' + parent).val()
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var $child = $('#id_' + child);

//S-06166- Shift header page to new reference table:Added to show the value of the bill_to_party & payment_terms in the textbox
                 if(child == 'bill_to_party'){
                    billtodata = JSON.stringify(data);
                     for (var key in data){
                        if(data.hasOwnProperty(key)){
                             $(billto_id).val(key);
                        }
                     }
                }
                 if(child == 'payment_terms'){
// S-08412:-Override pay-term selection for AT&T only with z180: Added below to populate the field with  payterm value only when AT&T is not selected
                 if($("#id_customer_unit").val() != 1){
                    paytermsdata = JSON.stringify(data);
                     for (var key in data){
                        if(data.hasOwnProperty(key)){
                             $(paymentterms_id).val(key);
                        }
                     }
                 }
                }

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
    }
// S-11475-Add region/market areas with the hub below it :- Added below else if block for Region field to show the data of dependent field of hub
    else if(parent == 'region'){
        $.ajax({
            url: listreactfill_url,
            dataType: "json",
            type: "POST",
            data: {
                id:'',
                parent: parent,
                child: child,
                name: $('#id_' + parent).val(),
                sold_to:'',
                contract_number: ''
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();

                if(child == 'hub'){
                    for (var key in data){
                        if(data.hasOwnProperty(key)){
                            $child.append($('<option>',{value:key,text:data[key]}));
                        }
                     }
                }

            },
            error: function(){
                var $child = $('#id_' + child);
                $child.find('option:gt(' + index + ')').remove();
            }
        });
    }
   else {
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
function save_form(){
   form_save = true;
    $('[readonly=true]').removeAttr('readonly');
    $('[disabled=true]').removeAttr('disabled');

// S-07112 - Change dropdown selection view and value:- Added below block to fetch the code of sales_group & ericsson contract # and then save it to DB
     var salesval = $('#id_sales_group').val().match(/^U../);
     var eric_cont = document.getElementById('id_ericsson_contract').value;
     var actval=''; var splitval=0;
     if(eric_cont.indexOf('-')!= -1){
            splitval = eric_cont.split('-');
            actval = splitval[0];
     }else{
            actval = eric_cont;
     }

    clean_form = $('#headerform').serialize();
// S-07112 - Change dropdown selection view and value:- Added below block to explicitly change the dropdown to textfield when clicked on save
// button so that the code value can be set and saved to DB
    $(salesgroup_id).replaceWith("<input id='id_sales_group' type='text' name='sales_group'  sales_val='"+salesval+"'>");
    $("#id_sales_group").val($("#id_sales_group").attr("sales_val"));

    $(ericssoncontract_id).replaceWith("<input id='id_ericsson_contract' type='text' name='ericsson_contract'  cont_val='"+actval+"'>");
    $("#id_ericsson_contract").val($("#id_ericsson_contract").attr("cont_val"));

}

// D-03595 - Problem saving new configuration when using REACT data:- Added below function to hit only when the REACT data is getting saved
function save_react_form(){
    form_save = true;
    $('[readonly=true]').removeAttr('readonly');
    $('[disabled=true]').removeAttr('disabled');

    clean_form = $('#headerform').serialize();
    $("#id_customer_unit").val($("#id_customer_unit").attr("cust_val"));
    clean_form = $('#headerform').serialize();
}

function req_search(){
// D-03595 - Problem saving new configuration when using REACT data:- set the value of reactsearch to true when the react search button is clicked
    reactsearch = true;
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
  //S-06166- Shift header page to new reference table:Added below to make all the default dropdown fields appear as textbox in case called from react request no. search

//D-03595- Problem saving new configuration when using REACT data:- Removed the custom fields added earlier below in S-06166 and used "replaceWith" instead
                    $(personresponsible_id).replaceWith("<input id='id_person_responsible' type='text' name='person_responsible'>");
                    $("#id_person_responsible").val(returned.person_resp);

                    $(customername_id).replaceWith("<input id='id_customer_name' type='text' name='customer_name'>");
                    $("#id_customer_name").val(returned.cust_name);

                    $(salesoffice_id).val(returned.sales_office.match(/^US../));

                    $(salesgroup_id).replaceWith("<input id='id_sales_group' type='text' name='sales_group'>");
                    $("#id_sales_group").val(returned.sales_group.match(/^U../));

                    $(soldto_id).replaceWith("<input id='id_sold_to_party' type='text' name='sold_to_party'>");
                    $("#id_sold_to_party").val(returned.sold_to);

                    $(shipto_id).val(returned.ship_to);
                    $(billto_id).val(returned.bill_to);
                    $(paymentterms_id).val(returned.terms);

                    $(workgroup_id).val(returned.workgroup);

//                    $('#' + customerunit_id + ' option').filter(function(){return $(this).text() === returned.cust}).prop('selected', true);

                    $(customerunit_id).replaceWith("<input id='id_customer_unit' type='text' name='customer_unit' cust='"+returned.cust+"' cust_val='"+returned.cust_val+"'>");
                    $("#id_customer_unit").val(returned.cust);
//                    $("#id_customer_unit").val($("#id_customer_unit").attr("cust_val"));

//                    $(customerunit_id).change();

                    $(ericssoncontract_id).replaceWith("<input id='id_ericsson_contract' type='text' name='ericsson_contract'>");
                    $("#id_ericsson_contract").val(returned.contract.match(/^\d+/));

// D-04026: Baseline dropdown not populated when starting config with REACT info: Added below to populate Program & Baseline Impacted
// dropdown based on populated CU on react search

// S-11563: BoM Entry - Header sub-tab adjustments - Added 2 if else condition below as when react req search is done, if resultant CU is tier 1 then
// prog & catalog will get populated based on CU; if tier-2,3 then based on resultant cname

                    var cunit = $('#id_customer_unit').val();
                    if( cunit == 'AT&T' || cunit == 'Verizon' || cunit == 'Sprint' || cunit == 'T-Mobile' ){
                        list_filler('customer_unit', 'program');
                        list_filler('customer_unit', 'baseline_impacted', 1);
                    }else{
                        list_filler('customer_name', 'program');
                        list_filler('customer_name', 'baseline_impacted', 1);
                    }

//                    var ericontdeschtml = "<input id='ericontractdesc' style='width:400px;' type='textbox'/>";
//                    $(ericssoncontractdesc_id).remove();
//                    $(".ericcontdesc").append(ericontdeschtml);
//                    $("#ericontractdesc").val(returned.contract_desc);

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

