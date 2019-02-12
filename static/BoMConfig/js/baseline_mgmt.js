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

    messageToModal('Download Baseline',
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

function pickCustomer(){
    messageToModal('Choose Customer',
            '<label style="padding-right:5px;">Customer:</label><select>' + cust_list + '</select>',
            function(){
                $("#downloadform input[name='customer']").val($('#messageModal .modal-body select').val());
                $('#downloadform').submit();
            }
    );
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
                var errorMessage = 'The baseline cannot be rolled back due to the following error:';
                for(var index in returned.errors){
                    errorMessage += '<br/>' + returned.errors[index];
                }
                messageToModal('Unable to rollback baseline', errorMessage);
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
    messageToModal('Rollback Baseline',
            'You are about to rollback the latest revision of this baseline. This will return the latest "Active" revision to an "In-process" state.<br/><br/>'+
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
                            messageToModal('Rollback completed', 'Baseline has been rolled back ' + returned.revision,
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