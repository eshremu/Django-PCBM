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
});

function BuildTable(){
    if (table !== undefined){
        table.destroy();
    }
    table = $('#data_table').DataTable({
        'paging': false,
        'ordering': false,
        'info': false,
        'scrollX': true,
        'scrollY': parseInt($('.table-wrapper').css("height")) - 71,
        fixedColumns: {
            leftColumns: 3
        }
    });
}

function downloadModal(){
    messageToModal('Download Baseline',
            '<label>Revision</label><select>' + revision_list + '</select>',
            function(){
                $("#downloadform input[name='version']").val($('#messageModal .modal-body select').val());
                $('#downloadform').submit();
            }
    );
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
                            messageToModal('Rollback completed', 'Baseline has been rolled back to revision "' + returned.revision + '".',
                                function(){$('#id_baseline_title').val($('#rollbackform input[name="baseline"]').val()); $('#headersubform form').submit();}
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
                    error: function(){
                        messageToModal('Unknown error', 'An error occurred during rollback.  If this issue persists, contact a tool admin.');
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
    window.location.href = link.dataset.href;
}