
function cleanDataCheck(link){
    if (link.target == "_blank"){
        window.open(link.dataset.href);
    } else {
        window.location.href = link.dataset.href;
    }
}

$('button[value="audit"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
var outputdata = [[]];
var outputformat;
var inputTable = new Handsontable(document.getElementById('input-table'),{
    data: data,
    colHeaders: ['Ericsson Part','Customer Part','Sec Customer Part','Customer Asset tagging Req.', 'Customer Asset'],
    rowHeaders: false,
    minRows: 1,
    minCols: 5,
    minSpareRows: 1,
    afterCreateRow: function(index, amount, auto){
        addOutputRow(index, amount, auto);
    },
    beforeChange: function(changes, source){
        for (var i=0; i < changes.length; i++){
            if(typeof changes[i][3] === 'string') {
                changes[i][3] = $.trim(changes[i][3].toUpperCase());
            }
            if(changes[i][1] == 3 || changes[i][1] == 4){
                if([null, ''].indexOf(changes[i][3]) == -1){
                    if(['Y', 'E', 'C'].indexOf(changes[i][3]) != -1){
                        changes[i][3] = 'Y';
                    }else{
                        changes[i][3] = 'N';
                    }
                }
            }
        }
    },
    afterChange: function(changes, source){
        var altered_data = {};
        if (['alter', 'edit', 'paste'].indexOf(source) != -1) {
            // Gather changed data
            for (var idx in changes) {
                if (altered_data.hasOwnProperty(changes[idx][0])) {
                    altered_data[changes[idx][0]][changes[idx][1]] = changes[idx][3];
                } else {
                    altered_data[changes[idx][0]] = new Array(5).fill(null);
                    altered_data[changes[idx][0]][changes[idx][1]] = changes[idx][3];
                }
            }

            // Combine unchanged data (cell still containing null are assumed to have not been changed,
            // but may still reflect null after this loop
            for (var key in altered_data) {
                for (var i = 0; i < altered_data[key].length; i++) {
                    if (altered_data[key][i] == null) {
                        altered_data[key][i] = this.getDataAtCell(key, i);
                    }
                }
            }
        } else if (source == 'loadData'){
            for (var i = 0; i < this.countRows(); i++){
                altered_data[i] = this.getDataAtRow(i);
            }
        }

        if (altered_data != {}){
            $.ajax({
                url: validate_url,
                type: 'POST',
                headers:{
                    'X-CSRFToken': getcookie('csrftoken')
                },
                data: {
                    customer: $('#customer-select').val(),
                    changed_data: JSON.stringify(altered_data),
                    override: $('#override').prop('checked')
                },
                success: function(returned_data){
                    resultsDisplay(returned_data);
                },
                error: function(xhr, status, error){
                    console.log("ERROR: ", status, error);
                }
            });
        }
    }
});
var outputTable = new Handsontable(document.getElementById('output-table'),{
    data: outputdata,
    colHeaders: ['Ericsson Part','Customer Part','Sec Customer Part','Customer Asset tagging Req.', 'Customer Asset'],
    rowHeaders: false,
    minRows: 1,
    minCols: 5,
    minSpareRows: 1,
    cells: function(row, col, prop){
        var cellProperties = {};
        cellProperties.readOnly = true;
        cellProperties.renderer = customRenderer;
        return cellProperties;
    },
    afterRender: function(isForced){
        if(isForced){
            if(!checkSavableTable(this)){
                $('#save-button').attr('disabled', 'disabled');
            } else {
                $('#save-button').removeAttr('disabled');
            }
        }
    }
});

function addOutputRow(index, amount, auto){
    if (outputTable != undefined) {
        outputTable.alter('insert_row');
    }
}

function resultsDisplay(returned_data){
    var key;
    if(outputformat == undefined) {
        outputformat = returned_data.table_info;
    } else {
        for(key in returned_data.table_info){
            outputformat[key] = returned_data.table_info[key];
        }
    }
    for(key in returned_data.table_data){
        outputdata[key] = returned_data.table_data[key]
    }
    outputTable.loadData(outputdata);
    outputTable.render();
}

function customRenderer(instance, td, row, col, prop, value, cellProperties){
    $(td).removeClass('invalid-cell clean-cell changed-cell');
    if(outputformat != undefined && outputformat.hasOwnProperty(row)){
        if(outputformat[row][col] == true){
            td.style.background = '#90E990';
            $(td).addClass('clean-cell');
        } else if (outputformat[row][col] == false){
                td.style.background = '#E99090';
                $(td).addClass('invalid-cell');
        } else if (outputformat[row][col] == null){
            if ([null, ''].indexOf(value) != -1) {
                if((col == 0 || col == 1) &&
                        ([null, ''].indexOf(instance.getDataAtCell(row, 3)) == -1 ||
                        [null, ''].indexOf(instance.getDataAtCell(row, 4)) == -1))
                {
                    td.style.background = '#E99090';
                    $(td).addClass('invalid-cell');
                } else if ((col == 3 || col == 4) &&
                        $('#override').prop('checked') &&
                        ([null, ''].indexOf(instance.getDataAtCell(row, 0)) == -1 &&
                        [null, ''].indexOf(instance.getDataAtCell(row, 1)) == -1)){
                    td.style.background = '#85ADD6';
                    $(td).addClass('changed-cell');
                } else if ((col == 3 || col == 4) &&
                        !$('#override').prop('checked') &&
                        ([null, ''].indexOf(instance.getDataAtCell(row, 0)) == -1 && outputformat[row][0] == null &&
                        [null, ''].indexOf(instance.getDataAtCell(row, 1)) == -1 && outputformat[row][1] == null)){
                    td.style.background = '#85ADD6';
                    $(td).addClass('changed-cell');
                } else if (col == 2) {
                    if ($('#override').prop('checked') && !instance.isEmptyRow(row)){
                        td.style.background = '#85ADD6';
                        $(td).addClass('changed-cell');
                    } else {
                        td.style.background = '#DDDDDD';
                    }

                } else {
                    td.style.background = '#DDDDDD';
                }
            } else {
                td.style.background = '#85ADD6';
                $(td).addClass('changed-cell');
            }
        }
    } else {
        td.style.background = '#DDDDDD';
    }
    td.style.color = '#000000';
    Handsontable.renderers.TextRenderer.apply(this, arguments);
}

function checkSavableTable(tableCore){
    var countRow = tableCore.countRows();

    if(checkEmptyTable(tableCore)){
        return false;
    }

    for(var i=0; i < countRow - 1; i++){
        if(tableCore.isEmptyRow(i)){
            continue;
        }

        for(var j=0; j < tableCore.countCols(); j++){
            var cell = tableCore.getCell(i,j);
            if($(cell).hasClass('invalid-cell') || cell.style.background == "rgb(221, 221, 221)" || cell.style.background == "rgb(233, 144, 144)"){
                return false;
            }
        }
    }

    return true;
}

function checkEmptyTable(tableCore){
    var countRow = tableCore.countRows();
    for(var i=0; i < countRow; i++){
        if(!tableCore.isEmptyRow(i)){
            return false;
        }
    }
    return true;
}

function submitForm(){
    $('#dataForm').val(JSON.stringify(outputTable.getData()));
    $('#select-form').submit();
}

function duplicateCheck(list, allowBlank){
    allowBlank = allowBlank == undefined ? false : allowBlank;

    var duplicates = [];

    for(var i = 1; i < list.length; i++){
        if (list[i] == list[i-1]){
            if (!allowBlank || ['', null].indexOf(list[i]) == -1) {
                duplicates.push(list[i]);
            }
        }
   }

    if(duplicates.length > 0){
        var message = 'Multiple entries found for part number(s):<br>';

        if(duplicates.slice(0, -1).length > 0){
            message += duplicates.slice(0, -1).join(', ') + " and " + duplicates.slice(-1);
        } else {
            message += duplicates.join('');
        }

        message += '<br><br>Please correct this before continuing.';

        return message;
    }
}

function list_react_filler(parent, child, index){
            index = typeof(index) !== 'undefined' ? index : 0;

            if(parent == 'customer_unit'){
                $.ajax({
                    url: listreactfillurl,
                    dataType: "json",
                    type: "POST",
                    data: {
                        parent: parent,
                        id:  $('#customer-select').val(),
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

//  D-07795: Customer Audit / Search Tab: Customer name clearing on save, no selections available in dropdown:- Added below block to
// show the selected Customer name in the dropdown after saving
                        if(selectedCustName){
                            selectedCustName = selectedCustName.replace('&amp;','&')
                            $('#cuname').find("option:contains('"+selectedCustName+"')").attr("selected","selected");
                        }
                    },
                    error: function(){
                        var $child = $('#cuname');
                        $child.find('option:gt(' + index + ')').remove();
                    }
                });
            }
           else {
                var $child = $('#cuname');
                $child.find('option:gt(' + index + ')').remove();
            }
    }

$(document).ready(function(){
   $('a.headtitle:contains("Customer Audit")').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

//  D-07795: Customer Audit / Search Tab: Customer name clearing on save, no selections available in dropdown:- Added below block to
// load the customer_name list on page load
    $(window).load(function () {
//  S-14613: Customer Audit - Search/ Audit:Tier 1 Customer Unit/Customer name logic change: Added below condition to show the custname field on
// loading the page after save only for Non Tier-1 customers
         var cuname = $('#customer-select').val();
         if(cuname != '1' && cuname != '2' && cuname != '3' && cuname != '4'){
            $('#cnamelabel').show();
            $('#cuname').show();
            list_react_filler('customer_unit', 'customer_name');
         }
    });

    $('#customer-select').change(function(){
        var cuname = $('#customer-select').val();
//  S-14613: Customer Audit - Search/ Audit:Tier 1 Customer Unit/Customer name logic change: Added below condition to show the custname field on
// selecting the CU only for Non Tier-1 customers
        if(cuname != '1' && cuname != '2' && cuname != '3' && cuname != '4'){
            $('#cnamelabel').show();
            $('#cuname').show();
            list_react_filler('customer_unit', 'customer_name');
        }else{
            $('#cnamelabel').hide();
            $('#cuname').hide();
        }
    });

    $(document).on('change','#customer-select,#override', function(){
        if($(this).is($('#customer-select'))){
            $('#override').removeAttr('checked');
        }

        inputTable.loadData(inputTable.getData());
    });

    $('#save-button').click(function(){
        var bChangedData = false;
        var emptyRows = outputTable.countEmptyRows(true);

        for(var i = 0; i < outputTable.countRows() - emptyRows; i++){
            for(var j = 0; j < outputTable.countCols(); j++){
                if($(outputTable.getCell(i, j)).hasClass('changed-cell')){
                    bChangedData = true;
                }
            }
        }

        if(!bChangedData){
            messageToModal('No data changes', 'The data entered matches the stored data exactly.  No saving is neccesary.', null);
            return;
        }

        var pnum = outputTable.getDataAtCol(0).slice(0, -1 * emptyRows).sort();
        var message = duplicateCheck(pnum);
        if(message != null) {
            messageToModal('Duplicate data detected', message);
            return;
        }

        var cnum = outputTable.getDataAtCol(1).slice(0, -1 * emptyRows).sort();
        message = duplicateCheck(cnum);
        if(message != null) {
            messageToModal('Duplicate data detected', message);
            return;
        }

        var cnum2 = outputTable.getDataAtCol(2).slice(0, -1 * emptyRows).sort();
        message = duplicateCheck(cnum2, true);
        if(message != null) {
            messageToModal('Duplicate data detected', message);
            return;
        }

        if($('#override').prop('checked')){
            messageToModal('Confirm?', 'You have selected to overwrite existing customer part info.  Please confirm this decision.', submitForm);
        } else {
            submitForm();
        }
    });
});

