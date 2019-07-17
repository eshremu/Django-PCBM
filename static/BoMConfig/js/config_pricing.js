var hot, clean_form;
var form_save = false;

$('button[value="config_price"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){

    $(window).load(function(){
        form_resize();

        if(table_data.length > 0) {
            clean_form = JSON.stringify(hot.getSourceData());
        }

// S-11538: Open multiple revisions for each configuration - UI Elements :- modified below block to show the UI as per the requirement
        var baseln = '';
        if(program_list != undefined && program_list.length > 1){
        //     S-11552: Baseline tab changes : changed pop-up message to catalog
            var message = "Multiple matching configurations were found.<br/>Please select the catalog for the desired configuration.";

            message += '<label for="desiredprog" style="padding-right: 5px; margin-left: 30%;">Catalog / Revision - Program</label>';
            message += '<div style="width:100%;"><div style="width:20%; float:left;"><br/><input id="latest10btn" onclick="selectLatest10()" type="button" class="btn btn-primary" name="latest10" value="Select Latest 10"></input>&nbsp<br/><input id="deselectbtn" onclick="deselectAll()"  class="btn btn-primary" type="button" name="deselectall" value="Deselect All"></input></div>';

            message += '<div  style="width:100%;"><ul id="desiredprog" style="height: 155px; margin-left: 25%; width:70%; overflow: auto; list-style-type: none;  overflow-x: hidden;  border: 1px solid #000;">';
            for(var i=0; i<program_list.length; i++) {

               if(baseln !=  baseline_list[i][1]){
                    message += '<li><label>'+
                         baseline_list[i][1]+'</label></li>';
               }

//D-07038: On multiple revisions in pricing view, opened incorrect revisions from what was selected :- Added "baseline_list[i][2]" below in the value to include the actual rev value when selected
                message += '<li value="'+ program_list[i][0] + "_" + baseline_list[i][0]+'"><label for="'+i+'"><input type="checkbox" name="revs" id="'+i+'" value="'+ program_list[i][0] + "_" + baseline_list[i][0] + "_" + baseline_list[i][2] +'" >' +
                 ' Rev '+ baseline_list[i][2] + ' - ' + program_list[i][1] +'</label></li>';
                baseln = baseline_list[i][1];
            }
            message += '</ul></div></div>';
            message += '<label id="limiterr" style="color:midnightblue; display:none; margin-left: 30%;">*Limit of 10 Revisions</label>';
            message += '<label id="novalerr" style="color:midnightblue; display:none; margin-left: 30%;">*Please select a revision</label>';

            messageToModalPricing('Multiple configurations found',
                message,
                function(){
                        var unorderedList = document.getElementById('desiredprog');
                        ListItems = unorderedList.getElementsByTagName('li');
                        var list = [];
                        $.each($("input[name='revs']:checked"), function(){
                            list.push($(this).val());
                        });

                        for (var input, i = 0; i < list.length; i++) {
                             $('input[name="program"]').val( list[i].split("_")[0]);
                             $('input[name="baseline"]').val( list[i].split("_")[1]);
//D-07038: On multiple revisions in pricing view, opened incorrect revisions from what was selected :- Added below to set the rev value of the selected revisions in the input box
                             $('input[name="baselinerev"]').val( list[i].split("_")[2]);
                       }
                        if($('input[name="revs"]:checked').length <=10){
                            for(j=0; j<list.length; j++){
//D-07038: On multiple revisions in pricing view, opened incorrect revisions from what was selected :- Changed the value part of &rev from 'baseline_list[j][2]' below to show the rev value of the selected record and not according to the list from top
                                window.open('../pricing_config/mult/'+'?iBaseId='+list[j].split("_")[1]+'&iProgId='+list[j].split("_")[0]+'&iConf='+$('input[name="config"]').val()+'&rev='+list[j].split("_")[2] ,'','left=100,top=100,height=540,width=624,menubar=no,toolbar=no,location=no,resizable=yes,scrollbars=yes');
                            }
                        }else{
                            $('#limiterr').css("display", "block");
                        }
                }
            );
        }
    });

    $('#config').keyup(function(){
       $('#config').val($('input[name="config"]').val().trim());
    });

    $(window).resize(function(){
        form_resize();
    });
    
    $('#saveForm').click(function(event){
        $('#headersubform').removeAttr('action');
        $('<input/>').attr('id','data_form').attr('type', 'hidden').attr('name','data_form').attr('value',JSON.stringify(hot.getSourceData())).appendTo('#headersubform');form_save=true;
    });

    $('#search').click(function(event) {
        $('#headersubform').removeAttr('action');
    });
    $('#download').click(function(event){
        $('<input/>').attr('id','cookie').attr('type', 'hidden').attr('name','file_cookie').attr('value', file_cookie).appendTo('#headersubform');
        $('#headersubform').attr('action', download_url);
        timer = setInterval(function(){
            if(document.cookie.split('fileMark=').length == 2 && document.cookie.split('fileMark=')[1].split(';')[0] == $('#cookie').val()) {
                clearInterval(timer);
                $('#myModal').modal('hide');
            }
        },1000);
    });

});

// S-11538: Open multiple revisions for each configuration - UI Elements :- Added below function that gets called on deselect button click
function deselectAll(){
     $("input[name='revs']").removeAttr("checked");
}
// S-11538: Open multiple revisions for each configuration - UI Elements :- Added below function that gets called on Select latest 10 button click
function selectLatest10(){
    $('#novalerr').css("display", "none");
    var checkboxes=$("input[name='revs']");
// D-07042: Config Price Mgmt popup - select latest ten error :- Changed the i position from 0 to the checkbox length-1 as it will count from bottom
// and i >= checkbox length -10 as it will select 10 revisions from below which is claimed to be as the latest 10 revisions.
    for (var i = checkboxes.length -1; i >= checkboxes.length -10; i--) {
            checkboxes[i].checked = true;
    }
}
function form_resize(){
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var displayformheight = $('#display_form').height();
    var bottombuttonheight = $('#formbuttons').height();
    var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (subformheight + bottombuttonheight + topbuttonheight + displayformheight + 5); //+ crumbheight);

    $('#table-wrapper').css("max-height", tableheight);
    $('#table-wrapper').css("height", tableheight);

    if(table_data.length > 0) {
        build_table();
    }
}

function messageToModalPricing(title, message, callback){
    var params = [];
    for(var i = 3; i < arguments.length; i++){
        params.push(arguments[i]);
    }
    $('#messageModal .modal-header h4').text(title);
    $('#messageModal .modal-body').html(message);
    $('.modal_submit').off('click');
    $('.modal_submit').click(function(){

// S-11538: Open multiple revisions for each configuration - UI Elements :- Added below block if else to show the error lines
        if($('input[name="revs"]:checked').length == 0){            // if nothing is selected
              $('#novalerr').css("display", "block");
        }else if($('input[name="revs"]:checked').length >10){       // if more than 10 checkboxes are checked
              $('#limiterr').css("display", "block");
        }else{
              $('#messageModal').modal('hide');
        }
        if(callback != undefined) {
            callback.apply(this, params);
        }
    });
    $('#messageModal').modal('show');
}

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties) {
    td.style.background = '#DDDDDD';
    customRenderer(instance, td, row, col, prop, value, cellProperties);
}

function moneyRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (cellProperties.readOnly){
        td.style.background = '#DDDDDD';
    }

    if (String(value) != '' && value != undefined && value != null) {
        var result;
        var dummy = String(value).replace("$","").replace(',','').replace(' ','');
        var decimal = dummy.indexOf('.');
        var wholeDummy, fracDummy;

        if (decimal != -1){
            wholeDummy = dummy.slice(0, decimal);
            fracDummy = dummy.slice(decimal + 1);
            if (fracDummy.length >= 2){
                fracDummy = fracDummy.slice(0,2);
            } else {
                fracDummy += '0';
            }
        } else {
            wholeDummy = dummy;
            fracDummy = "00";
        }
        var negative = false;
        if(wholeDummy.indexOf('-') != -1){
            negative = true;
            wholeDummy = wholeDummy.slice(wholeDummy.indexOf('-') + 1);
        }
        var start = wholeDummy.length % 3 == 0 ? 3 : wholeDummy.length % 3;

        result = wholeDummy.slice(0,start);

        for(var i = 0; i < wholeDummy.length - start; i++){
            if (i % 3 == 0){
                result += ',';
            }
            result += wholeDummy.charAt(i + start);
        }

        value = result + '.' + fracDummy;

        if (negative){
            value = "(" + value + ")";
        }
    }
    customRenderer(instance, td, row, col, prop, value, cellProperties);
}

function customRenderer(instance, td, row, col, prop, value, cellProperties) {
    if(row == 0 && not_picklist){
        td.style.fontWeight = 'bold';
    }

    if (!instance.getDataAtCell(row, 0).includes('.') && cellProperties.readOnly){
        td.style.background = '#C8FF9F';
    }

    if (/<[a-zA-Z][\s\S/]*>/.test(value) === false) {
        Handsontable.renderers.TextRenderer.apply(this, arguments);
    } else {
        Handsontable.renderers.HtmlRenderer.apply(this, arguments);
    }
}

function calcRenderer (instance, td, row, col, prop, value, cellProperties) {
    value = parseInt(instance.getSourceDataAtCell(row, 4)) * parseFloat(instance.getSourceDataAtCell(row, 5));
    moneyRenderer(instance, td, row, col, prop, value, cellProperties);
}

function build_table() {
    var headers = ['Line #','Product Number','Internal Product Number','Product Description','Order Qty','Unit Price',
        'Total Price','Manual Override for Total NET Price','Traceability Req. (Serialization)','Linkage','Material Group 5','HW/SW Indicator',
        'Comments (viewable by customer)','Additional Reference (viewable by customer)']; //S-05769: Addition of Product Traceability
    var container = document.getElementById('datatable');
    hot = new Handsontable(container, {
        data: table_data,
        minRows: 1,
        maxRows: table_data.length,
        minCols: 13,
        maxCols: 13,
        minSpareRows:0,
        colHeaders: headers,
        cells: function(row, col, prop){
            var cellProperties = {};

            if(col != 5 && col != 6 && col != 7){
                cellProperties.readOnly = true;
                cellProperties.renderer = readonlyRenderer;
            } else if (col == 5) {
                cellProperties.readOnly = true;
                cellProperties.renderer = moneyRenderer;
            } else if (col == 6) {
                cellProperties.readOnly = true;
                cellProperties.renderer = calcRenderer;
            } else {
                if(can_write && !readonly) {
                    cellProperties.validator = function (value, callback) {
                        if (/^\d+(?:\.\d{2})?$|^$/.test(value)) {
                            callback(true);
                        } else {
                            callback(false);
                        }
                    };
                    cellProperties.allowInvalid = false;
                    cellProperties.renderer = moneyRenderer;
                } else {
                    cellProperties.readOnly = true;
                    cellProperties.renderer = moneyRenderer;
                }
            }

            cellProperties.className = 'htCenter';

            return cellProperties;
        },
        beforeChange: function(changes, source){
            if (changes[0][1] == 5 && not_picklist) {
                var net_total = 0;
                for (var i = 1; i < this.countRows(); i++) {
                    net_total += parseInt(this.getSourceDataAtCell(i, 4)) * parseFloat(this.getSourceDataAtCell(i, 5));
                }

                net_total -= this.getSourceDataAtCell(changes[0][0], parseFloat(changes[0][1]) - 1) * parseFloat(changes[0][2]);
                net_total += this.getSourceDataAtCell(changes[0][0], parseFloat(changes[0][1]) - 1) * parseFloat(changes[0][3]);

                changes.push([0, "5", this.getSourceDataAtCell(0, 5), net_total]);
            }
        },
        afterChange: function(changes, source){
            calcValue(this);
        }
    });
    calcValue(hot);
}

function calcValue(instance){
    overall_total = 0;
    stated_total = 0;

    for(var i=0; i < instance.countRows(); i++){
        if (instance.getSourceDataAtCell(i, 7) != ""){
            overall_total += parseFloat(instance.getSourceDataAtCell(i, 7));
            if (i == 0 && not_picklist){
                break;
            }
        } else {
            if (i == 0 && not_picklist){
                stated_total += parseInt(instance.getSourceDataAtCell(i, 4)) * parseFloat(instance.getSourceDataAtCell(i, 5));   //parseFloat changed to parseInt
            } else {
                overall_total += parseInt(instance.getSourceDataAtCell(i, 4)) * parseFloat(instance.getSourceDataAtCell(i, 5));  //parseFloat changed to parseInt
            }
        }
    }
    if (overall_total == 0 && stated_total != 0){
        overall_total = stated_total;
    }

    $('#net_value').val(overall_total.toFixed(2));
}