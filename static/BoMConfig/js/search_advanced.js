/**
 * Created by epastag on 10/10/2016.
 */
$('a:contains("Search")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc')
$('button[value="advanced"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
var xhr;
$(document).ready(function(){
    $('#status option[value="active"]').attr("selected",true);

    $('#search_button').click(function(){
        $('#search_form').submit();
    });
    $(window).load(function () {
    //  S-11564: Search - Basic & Advanced adjustments- Added below block to call the URL on CU selection for CName field data
        $('#customer').change(function(){
            list_react_filler('customer_unit', 'customer_name');
        });
    });
    $('#readiness').change(function(event){
        if($(this).val() < 0){
            $(this).val(0);
        }

        if($(this).val() > 100){
            $(this).val(100);
        }
    });

    $('input').keydown(function(e){
        if(e.keyCode == 13) {
            $('#search_form').submit();
        }
    });

    $(document).keydown(function(e){
        if(e.keyCode == 27 && xhr !== undefined && $('#myModal').hasClass('in')) {
            xhr.abort();
        }
    });

    $('#header_search_title, #entry_search_title, #revision_search_title').click(function(){
        $(this).next().collapse('toggle');
    });

    $('#header_search, #entry_search, #revision_search').on('hide.bs.collapse show.bs.collapse',function(event){
        if (event.type == 'hide'){
            $(this).prev().find('.caret').css({transform: 'rotate(-90deg)'});
        } else {
            $(this).prev().find('.caret').css({transform: 'rotate(0deg)'});
        }
    });

    $(document).on('click', '.selectall', function(){
        if($(this).prop('checked')){
            $('.recordselect').attr('checked', 'checked');
        } else {
            $('.recordselect').removeAttr('checked');
        }
        $($('.recordselect')[0]).change();
    });

    $(document).on('click change', '.recordselect',function(){
        if($('.recordselect:checked').length > 0) {
            $('#download').removeAttr('disabled');
            $('#downloadcustom').removeAttr('disabled');
        } else {
            $('#download').attr('disabled', 'disabled');
            $('#downloadcustom').attr('disabled', 'disabled');
        }
    });

    $(document).on('click', '#download', function(){
        var destination = downloadmultiurl;
        var list = '';
        $('.recordselect:checked').each(function(i, elem){
            list += $(elem).val() + ',';
        });
        destination += '?list=' + encodeURIComponent(list.slice(0, -1));
        window.open(destination, '_blank','left=100,top=100,height=150,width=500,menubar=no,toolbar=no,location=no,resizable=no,scrollbars=no');
    });

    $(document).on('click', '#downloadcustom', function(){
        var $table = $('<table style="white-space: nowrap">');
        var $row = $('<tr>');

        var $set = $('#result_table th:gt(0)');

        $set.each(function(idx, elem){
            var $td = $('<td>');
            
            if(idx==1){return;}

            $td.append('<div style="display: inline;"><input id="'+idx+'" type="checkbox" checked ' + (idx==0?'disabled':'') + '></div>');
            $td.append($('<label>').text($(elem).text()).attr('for', idx));
            $td.css('width', '25%');
            $td.css('padding-right', '10px');

            $row.append($td);
            if (Math.max(idx, 1) % 4 == 0 || idx == $set.length - 1){
                $table.append($row);
                if (idx != $set.length - 1) {
                    $row = $('<tr>');
                }
            }
        });

        messageToModal('Download Results', $table, function(){
// <!--D-06762- 414 Request-URI Too Large' error when downloading search results: made destination blank from var destination = reporturl + '?';-->
            var destination = '';
            var chosenFields = [];
            $('#messageModal .modal-body input:checked').each(function(idx, elem){
                chosenFields.push(parseInt($(this).attr('id')));
            });

            var $rowSet  = $('#result_table tbody tr').has('input:checked');
            $rowSet.each(function(idx, elem){
                $(this).find('td').each(function(){
                    if(chosenFields.indexOf(this.cellIndex-1) != -1) {
                        destination += 'row' + (idx + 1) + '=' + encodeURIComponent($(this).text()) + '&';
                    }
                });
            });

            var $rowSet  = $('#result_table thead tr');
            $rowSet.each(function(idx, elem){
                $(this).find('th').each(function(){
                    if(chosenFields.indexOf(this.cellIndex-1) != -1) {
                        destination += 'header=' + encodeURIComponent($(this).text()) + '&';
                    }
                });
            });

//<!--D-06762- 414 Request-URI Too Large' error when downloading search results: deleted window.open and added below code from line 130-157-->

            var today = new Date();
            var date = today.getFullYear()+ '_' + (today.getMonth()+1) + '_' + today.getDate()  + '_' + today.getHours() + today.getMinutes() + today.getSeconds();
            var filename = 'Search Results ' + date + '.xlsx'

            var request = new XMLHttpRequest();
            request.open('POST', reporturl, true);
            request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
            request.setRequestHeader('X-CSRFToken', getcookie('csrftoken'));
            request.responseType = 'blob';

            request.onload = function(e) {
                if (this.status === 200) {
                    var blob = this.response;
                    if(window.navigator.msSaveOrOpenBlob) {
                        window.navigator.msSaveBlob(blob, filename);
                    }
                    else{
                        var downloadLink = window.document.createElement('a');
                        var contentTypeHeader = request.getResponseHeader("Content-Type");
                        downloadLink.href = window.URL.createObjectURL(new Blob([blob], { type: contentTypeHeader }));
                        downloadLink.download = filename;
                        document.body.appendChild(downloadLink);
                        downloadLink.click();
                        document.body.removeChild(downloadLink);
                       }
                   }
               };
               request.send(destination);
        });
    });
});

//$('#soldto').mouseleave(function(){
//        list_react_filler('sold_to_party', 'ericsson_contract');
//    });

// S-11564: Search - Basic & Advanced adjustments- Added below block to populate  CName field data based on CU selection
function list_react_filler(parent, child, index){
            index = typeof(index) !== 'undefined' ? index : 0;

            if(parent == 'customer_unit'){
                $.ajax({
                    url: listreactfillurl,
                    dataType: "json",
                    type: "POST",
                    data: {
                        parent: parent,
                        id:  $('#customer').val(),
                        child: child,
                        name:'',
                        sold_to:'',
                        contract_number: ''
                    },
                    headers:{
                        'X-CSRFToken': getcookie('csrftoken')
                    },
                    success: function(data) {

                        var $child = $('#cuname');
                         $child.find('option:gt(' + index + ')').remove();

                        if(child == 'customer_name'){
                          for (var key in data){
                            if(data.hasOwnProperty(key)){
                                $child.append($('<option>',{value:key,text:data[key]}));
                            }
                          }
                        }
                     },
                    error: function(){
                        var $child = $('#cuname');
                        $child.find('option:gt(' + index + ')').remove();
                    }
                });
            }else if(parent=='sold_to_party'){
        $.ajax({
            url: listreactfillurl,
            dataType: "json",
            type: "POST",
            data: {
                id:'',
                parent: parent,
                child: child,
                name: '',
                sold_to:$('#soldto').val(),
                contract_number: ''
            },
            headers:{
                'X-CSRFToken': getcookie('csrftoken')
            },
            success: function(data) {
               var $child = $('#ericsson_contract');

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
           else {
                var $child = $('#cuname');
                $child.find('option:gt(' + index + ')').remove();
            }
    }

function search(eventObj){//alert($('#customer').val()+"--+----"+$('select#supply_chain_flow').val())
    var selectednumbers = [];
    if( $('#supply_chain_flow :selected').length > 0){
        //build an array of selected values
        $('#supply_chain_flow :selected').each(function(i, selected) {
            selectednumbers[i] = $(selected).val();
        });
    }

    var selectedcontnumbers = [];
    if( $('#ericsson_contract :selected').length > 0){
        $('#ericsson_contract :selected').each(function(i, selected) {
            selectedcontnumbers[i] = $(selected).val();
        });
    }

    var selectedportcode = [];
    if( $('#portfolio_code :selected').length > 0){
        $('#portfolio_code :selected').each(function(i, selected) {
            selectedportcode[i] = $(selected).val();
        });
    }
//alert(JSON.stringify(selectedcontnumbers))
    $('#myModal').modal('show');
    xhr = $.ajax({
        url: searchurl,
        dataType: "html",
        type: "POST",
        data: {
            request: $('#request').val(),
            customer: $('#customer').val(),
            cuname: $('#cuname').val(),
            sold_to: $('#soldto').val(),
            program: $('#program').val(),
            config_design: $('#config').val(),
            technology: $('#tech').val(),
            base_impact: $('#base_impact').val(),
            model: $("#model").val(),
            model_desc:$("#model_desc").val(),
            init_rev: $("#init_rev").val(),
            status: $('#status').val(),
            inquiry_site: $('#inquiry_site').val(),
            person: $('#person').val(),
            product1: $('#prod1').val(),
            product2: $('#prod2').val(),
            frequency: $('#freq').val(),
            band: $('#band').val(),
            readiness: $('#readiness').val(),
            readiness_param: $('#readiness_param').val(),

            product_num: $('#prod_num').val(),
            context_id: $('#contextID').val(),
            customer_num: $('#cust_num').val(),
            sec_customer_num: $('#sec_cust_num').val(),  //Added for S-05767:Addition of Second Cust No. in advance search filter
            description: $('#prod_desc').val(),

            base_rev: $('#base_rev').val(),
            release_param: $('#release_param').val(),
            release: $('#release').val(),
            latest_only: $('#latest_only').prop('checked')
        },
        headers:{
            'X-CSRFToken': getcookie('csrftoken')
        },
        success: function(data) {
            xhr = undefined;
            $('#search_results').empty();
            $('#search_results').append($('<h3>Search Results</h3>'));
            $('#search_results').append(data);
            $('#search_button').blur();
            if($('#header_search').hasClass('in')){
                $('#header_search').collapse('toggle');
            }
            if($('#entry_search').hasClass('in')){
                $('#entry_search').collapse('toggle');
            }
            if($('#revision_search').hasClass('in')){
                $('#revision_search').collapse('toggle');
            }
            $('#result_table').DataTable({
                paging: false,
                searching: false,
                info: false,
                order: [],
                columnDefs: [
                    {
                        orderable: false,
                        targets: [0, 2]
                    }
                ]
            });
            $('#myModal').modal('hide');
        },
        error: function(xhr, status, error) {
            console.log('ERROR:', status, error);
            $('#myModal').modal('hide');
        }
    });
    return false;
}
function cleanDataCheck(link){
    if (link.target == "_blank"){
        window.open(link.dataset.href);
    } else {
        window.location.href = link.dataset.href;
    }
}