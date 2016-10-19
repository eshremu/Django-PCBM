/**
 * Created by epastag on 10/10/2016.
 */
$('a:contains("Search")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc')
$('button[value="advanced"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
var xhr;
$(document).ready(function(){
    $('#search_button').click(function(){
        $('#search_form').submit();
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

            $td.append('<div style="display: inline;"><input id="'+idx+'" type="checkbox"></div>');
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
            var destination = reporturl + '?';
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

            window.open(destination, '_blank','left=100,top=100,height=150,width=500,menubar=no,toolbar=no,location=no,resizable=no,scrollbars=no');
        });
    });
});

function search(eventObj){
    $('#myModal').modal('show');
    xhr = $.ajax({
        url: searchurl,
        dataType: "html",
        type: "POST",
        data: {
            request: $('#request').val(),
            customer: $('#customer').val(),
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
    window.location.href = link.dataset.href;
}