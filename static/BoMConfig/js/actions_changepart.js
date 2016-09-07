/**
 * Created by epastag on 9/1/2016.
 */
function submitForm(submitter){
    var data = {};
    $('.messageblock').css('display','none');
    if (submitter.value == 'search'){
        data['part'] = $('#part').val();
    } else if (submitter.value == 'replace'){
        data['part'] = $('#initial').val();
        data['replacement'] = $('#replace_part').val();
        var records = [];
        $('.replacement:checked').each(function(){
            records.push($(this).data('id'));
        });
        data['records'] = JSON.stringify(records);
    }

    data['action'] = submitter.value;
    
    $('#myModal').modal('show');
    $.ajax({
        url: change_url,
        type: "POST",
        data: data,
        headers:{
            'X-CSRFToken': getcookie('csrftoken')
        },
        success: function(data) {
            if(!data['error']){
                if(data['type']=='search') {
                    $('#initial').val(data['part']);
                    $('.replace_row').css('display', '');
                    $('#info_div').css('display', '');
                    var table = $('<table>');
                    var row = $('<tr>');
                    $('<th>').appendTo(row);
                    $('<th>').css('width', '25px').appendTo(row);
                    $('<th>').text('Configuration Designation').appendTo(row);
                    $('<th>').css('width', '25px').appendTo(row);
                    $('<th>').text('Program').appendTo(row);
                    $('<th>').css('width', '25px').appendTo(row);
                    $('<th>').text('Status').appendTo(row);
                    $('<th>').css('width', '25px').appendTo(row);
                    $('<th>').text('Status').appendTo(row);
                    table.append($('<thead>').append(row));

                    for (obj in data['records']) {
                        row = $('<tr>');
                        $('<td>').append($('<input>').attr('type', 'checkbox').addClass('replacement').data('id',
                            data['records'][obj]['id']).attr('disabled', !data['records'][obj]['selectable'])).appendTo(row);
                        $('<td>').appendTo(row);
                        if(data['records'][obj]['selectable']) {
                            $('<td>').text(data['records'][obj]['configuration_designation']).appendTo(row);
                        } else {
                            $('<td>').html(data['records'][obj]['configuration_designation'] + '<span style="color:red;font-size:14pt;">*</span>').appendTo(row);
                        }
                        $('<td>').appendTo(row);
                        $('<td>').text(data['records'][obj]['program']).appendTo(row);
                        $('<td>').appendTo(row);
                        $('<td>').text(data['records'][obj]['status']).appendTo(row);
                        $('<td>').appendTo(row);
                        $('<td>').text(data['records'][obj]['baseline']).appendTo(row);

                        table.append(row);
                    }
                    $('#table-wrapper').empty();
                    $('#table-wrapper').append(table);
                } else if (data['type']=='replace'){
                    $('#table-wrapper').empty();

                    $('#part').val('');
                    $('#initial').val('');
                    $('.replace_row').css('display', 'none').val('');
                    $('#info_div').css('display', 'none');

                    $('.messageblock').empty();
                    $('.messageblock').removeClass('successblock errorblock').addClass('successblock').append($('<p>').text(data['status']));
                    $('.messageblock').css('display','');
                }
            } else {
                if(data['type']=='search') {
                    $('#table-wrapper').empty();
                    $('#info_div').css('display', 'none');
                }

                $('.messageblock').empty();
                $('.messageblock').removeClass('successblock errorblock').addClass('errorblock').append($('<p>').text(data['status']));
                $('.messageblock').css('display','');
            }
            $('#myModal').modal('hide');
        },
        error: function(){
            $('#myModal').modal('hide');
            messageToModal('Error Occurred','A network error occurred while processing your request.<br/>If this continues, contact a tool administrator for assistance.')
        }
    });
    return false;
}
