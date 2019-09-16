/**
 * Created by epastag on 5/11/2016.
 */

$('a.headtitle:contains("Baseline")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

var timer, table, submitActor;
$(document).ready(function() {
    $(window).load(function () {
        form_resize();

        $('.first_row').each(function(ind, el){
            var next_sib = $(el).next();
            var search_string = "";
            while(next_sib.length > 0 && !next_sib.hasClass('first_row')){
                $(next_sib).find('td').each(function(id, elm){
                    search_string +=  $(elm).text() + " ";
                });
                next_sib = $(next_sib).next();
            }

            var searchlist = search_string.split(/\s+/);
            var searchset = new Set(searchlist);
            searchlist = [];
            searchset.forEach(function(val){
                searchlist.push(val);
            });
            search_string = searchlist.join(' ');

            var width = $(el).find('>:nth-child(2)').css('width');
            $(el).find('>:nth-child(2)').css('display','none').css('max-width', width).text(search_string);
        });

        BuildTable();

        $('#data_table_info').css('display','none');
        $('#data_table_info').parent().css('width','0');
    });

    $(window).resize(function () {
        form_resize();
        BuildTable();
    });

    $('#id_baseline_title').change(function(event){
        this.form.submit();
    });

    $('#deleteBaseline').click(function(){
        if($('.baselineChk:checked').length > 0) {
            messageToModal('Confirm deletion','STOP!!! Are you sure you wish to delete the selected records? This is permanent and CANNOT be undone.', function(source){
                $('#myModal').modal('show');
                process();
            }, this);
        } else {
            messageToModal('Error','Please select at least 1 record for deletion.', function(){});
        }
    });
});
function process(){
    var records = [];
    $('.baselineChk:checkbox:checked').each(function(i)
    {
      records[i] = $(this).val();
    });

        $('#myModal').modal('show');
        $.ajax({
            url: deletebaseline_url,
            type: "POST",
            data: {
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

function cust_filter(customer){
    if(customer !== 'All') {
        $('tbody tr').not('.' + customer).css('display','none');
        $('tbody tr.' + customer).css('display','');
        $('#cu_filter').html(customer.replace('-_',' ').replace("_","&") +" <span class=\"caret\"></span>");
    } else {
        $('tbody tr').css('display', '');
        $('#cu_filter').html('Customer <span class="caret"></span>');
    }
// S-11565:Baseline tab - main page adjustments - Added below to call function to fetch cust name list based on selected CU
    list_react_filler($('#cu_filter').text());
    table.draw();
}

function BuildTable(){
    var searchText;
    if (table !== undefined){
        searchText = $('.dataTables_filter input').val();
        table.destroy();
    }
    table = $('#data_table').DataTable({
        'paging': false,
        'ordering': false,
        'info': false,
        'autoWidth': false,
        'scrollX': true,
        'scrollY': parseInt($('.table-wrapper').css("height")) - 71,
        fixedColumns: {
            leftColumns: 2 //S-05745: Add Second Customer number in Baseline View
        }
    });

    if (searchText != undefined) {
        table.search(searchText).draw();
    }

}

function downloadModal(){
    var sMessage = '<label style="padding-right:5px;">Revision:</label><select name="rev">' + revision_list + '</select>';
    if($('#downloadform input[name="baseline"]').val() == 'No Associated Baseline') {
        sMessage += '<label style="padding-right:5px;">Customer:</label><select name="cust">' + cust_list + '</select>';
    }
//     S-11552: Baseline tab changes : changed pop-up message to catalog
    messageToModal('Download Catalog',
            sMessage,
            function(){
                $("#downloadform input[name='version']").val($('#messageModal .modal-body select[name="rev"]').val());
                if($('#downloadform input[name="baseline"]').val() == 'No Associated Baseline') {
                    $("#downloadform input[name='customer']").val($('#messageModal .modal-body select[name="cust"]').val());
                }
                $('#downloadform').submit();
            }
    );
}

// S-11565:Baseline tab - main page adjustments - Changed Customer to CU and added CNAME below it in the dialog
// S-11565:Baseline tab - main page adjustments - Changed the value set for CU based on UI changed now
// S-11565:Baseline tab - main page adjustments - Added the line below CU inside function to set value for selected CNAME
function pickCustomer(){
    messageToModal('Choose Customer',
            '<label style="padding-right:5px;">Customer Unit:</label><select id="id_customer_unit" onChange="list_react_filler1('+"'customer_unit'"+', '+"'customer_name'"+')">' + cust_list + '</select>' + '<br />' +
            '<label style="padding-right:5px;">Customer Name:</label><select id="id_customer_name"><option value="">-------</option></select>',
            function(){
//                $("#downloadform input[name='customer']").val($('#messageModal .modal-body select').val());
                $("#downloadform input[name='customer']").val($('#id_customer_unit').val());
                $("#downloadform input[name='customer_name']").val($('#id_customer_name').val());
                $('#downloadform').submit();
            }
    );
}

// S-11565:Baseline tab - main page adjustments - Added below function(called from UI) to fetch cust name list based on selected CU
function list_react_filler(cu, index){
        index = typeof(index) !== 'undefined' ? index : 0;

            $.ajax({
                url: listreactfill_url,
                dataType: "json",
                type: "POST",
                data: {
                    parent: 'customer_unit',
                    id:  cu,
                    child: 'customer_name',
                    name:'',
                    sold_to:'',
                    contract_number: ''
                },
                headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                success: function(data) {
                    $('#cnamefil').find('option:gt(' + index + ')').remove();

                     $('#cname_filter').replaceWith('<select id="cnamefil" type="button" name="basefil" onChange ="custname_filter()" style="background-color:#DDDDDD; border:1px solid transparent;" class="btn dropdown-toggle" data-toggle="dropdown">Catalog<option value="All">All</option></select>');
                     for (var key in data){
                        if(data.hasOwnProperty(key)){
                              $('#cnamefil').append('<option style="background-color:white; border-radius:4px; " value="' + key + '">'+data[key]);
                         }
                     }
                 },
                error: function(){
                    var $child = $('#programcname');
                    $child.find('option:gt(' + index + ')').remove();
                }
            });
}

// S-11565:Baseline tab - main page adjustments - Added below function(called from dialog box) to fetch cust name list based on selected CU
// Added this separately for CNAME population as the parameter list is different in both the cases
function list_react_filler1(parent, child, index){
        index = typeof(index) !== 'undefined' ? index : 0;

        if(parent == 'customer_unit'){
            $.ajax({
                url: listreactfill_url,
                dataType: "json",
                type: "POST",
                data: {
                    parent: parent,
                    id:  $('#id_customer_unit').val(),
                    child: child,
                    name:'',
                    sold_to:'',
                    contract_number: ''
                },
                headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                success: function(data) {
                    var $child = $('#id_customer_name');
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
                    var $child = $('#programcname');
                    $child.find('option:gt(' + index + ')').remove();
                }
            });
        }else {
            var $child = $('#programcname');
            $child.find('option:gt(' + index + ')').remove();
        }
}

function cust_filter0(customer){
    if(customer !== 'All') {
        $('tbody tr').not('.' + customer).css('display','none');
        $('tbody tr.' + customer).css('display','');
        $('#cu_filter').html(customer.replace('-_',' ').replace("_","&") +" <span class=\"caret\"></span>");
    } else {
        $('tbody tr').css('display', '');
        $('#cu_filter').html('Customer <span class="caret"></span>');
    }
    list_react_filler($('#cu_filter').text());
    table.draw();
}

//S-11565:Baseline tab - main page adjustments - Added below function to filter based on selected CNAME
function custname_filter(){
    var cust=$("#cu_filter").text().replace(' ','-_').replace('&','_');

    $('tbody tr').show();
    var rows = $('#data_table tbody tr').toArray();

    for (var row in rows) {
        let hide = false;
        var cuname=$("#cnamefil").val();
        if(($("#cnamefil").val() !== "All") && !$(rows[row]).hasClass(cuname)){
                hide = true;
        }

        if (hide){
            $(rows[row]).hide();
            $(rows[row]).find('input').removeAttr('checked');
        }
    }
    table.draw();
}

function custname_filter1(){
var cust=$("#cu_filter").text().replace(' ','-_').replace('&','_');

     if($("#cnamefil").val() !== "All"){//alert($("#cnamefil").val());
        var custname=$("#cnamefil").val().replace(/ /g,'_');
        var custname1 = custname.replace(/\./g,'_').replace(/\-/g,'_').replace(/\&/g,'_').replace(/\,/g,'_');
//        alert(cust+'--'+custname1)
//        .replace('-_',' ').replace("_","&").replace(".","_");alert(custname)
            $("#cname_filter").html($("#cnamefil").val() + "&nbsp;<span class='caret'></span>");
//customer.replace('-_',' ').replace("_","&")
            $('tbody tr').not('.'+custname1).css('display','none');
            $('tbody tr.'+ custname1).css('display','');
//        $('#cu_filter').html(customer.replace('-_',' ').replace("_","&") +" <span class=\"caret\"></span>");
        }
        else{
//            $('tbody tr.'+cust).css('display', '');
            $('tbody tr').not('.' + cust).css('display','none');
            $('tbody tr.' + cust).css('display','');
            $('#cname_filter').html('Customer Name<span class="caret"></span>');
        }

}

function rollbackTest(){
    $('#myModal').modal('show');
    $.ajax({
        url: rollbacktest_url,
        dataType: "json",
        type: "POST",
        data: {
            form: $('#rollbackform').serialize()
        },
        headers:{
            'X-CSRFToken': getcookie('csrftoken')
        },
        success: function(returned) {
            // var returned = JSON.parse(data);
            $('#myModal').modal('hide');
            if(returned.status == 1) {
                rollbackModal();
            } else {
                //     S-11552: Baseline tab changes : changed pop-up message to catalog
                var errorMessage = 'The catalog cannot be rolled back due to the following error:';
                for(var index in returned.errors){
                    errorMessage += '<br/>' + returned.errors[index];
                }
                messageToModal('Unable to rollback catalog', errorMessage);
            }
        },
        error: function(xhr, status, error){
            messageToModal('Unknown error', 'The following error occurred while checking rollback.<br/>' +
                status + ": " + error + '<br/>If this issue persists, contact a tool admin.');
            $('#myModal').modal('hide');
        }
    });
}

function rollbackModal(){
//     S-11552: Baseline tab changes : changed pop-up message to catalog
    messageToModal('Rollback Catalog',
            'You are about to rollback the latest revision of this catalog. This will return the latest "Active" revision to an "In-process" state.<br/><br/>'+
            '<em style="color: red; text-decoration: underline;">This CANNOT be undone!</em><br/><br/>'+
            'Are you sure you wish to proceed?',
            function(){
                $('#myModal').modal('show');
                $.ajax({
                    url: rollback_url,
                    dataType: "json",
                    type: "POST",
                    data: {
                        form: $('#rollbackform').serialize()
                    },
                    headers:{
                        'X-CSRFToken': getcookie('csrftoken')
                    },
                    success: function(returned) {
                        // var returned = JSON.parse(data);
                        if(returned.status == 1) {
                        //     S-11552: Baseline tab changes : changed pop-up message to catalog
                            messageToModal('Rollback completed', 'Catalog has been rolled back ' + returned.revision,
                                function(){$('#id_baseline_title').val($('#rollbackform input[name="baseline_title"]').val()); $('#headersubform form').submit();}
                            );
                        } else {
                            var errorMessage = 'The following errors occurred:';
                            for(var index in returned.errors){
                                errorMessage += '<br/>' + returned.errors[index];
                            }
                            messageToModal('Rollback failed', errorMessage);
                        }
                        $('#myModal').modal('hide');
                    },
                    error: function(xhr, status, error){
                        messageToModal('Unknown error', 'The following error occurred during rollback.<br/>' +
                            status + ": " + error + '<br/>If this issue persists, contact a tool admin.');
                        $('#myModal').modal('hide');
                    }
                });
            }
    );
}

function downloadtoken(){
    $('#myModal').modal('show');
    timer = setInterval(function(){
        if(document.cookie.split('fileMark=').length == 2 && document.cookie.split('fileMark=')[1].split(';')[0] == $('#cookie').val()) {
            clearInterval(timer);
            $('#myModal').modal('hide');
        }
    },1000);
}

function form_resize(){
    var $header = $('#headersubform');
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var subformheight = $header.outerHeight(true);
    var bodyheight = $('#main-body').height();
    if ($('#data_table_wrapper').length != 0){
        bodyheight -= 17;
    }

    var tableheight = bodyheight - (topbuttonheight + subformheight);

    $('.table-wrapper').css("height", tableheight);
}

function cleanDataCheck(link){
    if (link.target == "_blank"){
        window.open(link.dataset.href);
    } else {
        window.location.href = link.dataset.href;
    }
}