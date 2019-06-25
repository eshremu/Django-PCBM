var hot, clean_form, container;
var form_save = false;
var hotarr=[]; var hotarr1=[];

$('button[value="multi_config"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){
    $(window).load(function(){
        form_resize();

        if(table_data.length > 0) {
            clean_form = JSON.stringify(hot.getSourceData());
        }

        if(program_list != undefined && program_list.length > 1){
            var message = "Multiple matching configurations were found.<br/>Please select the program & baseline for the desired configuration.";
            message += '<br/><label for="desiredprog" style="padding-right: 5px;">Program|Baseline:</label><select name="desiredprog">';
            for(var i=0; i<program_list.length; i++) {
                message += '<option value="'+ program_list[i][0] + "_" + baseline_list[i][0] +'">' +
                    program_list[i][1] + ' | ' + baseline_list[i][1] + '</option>';
            }
            message += '</select>';
            messageToModal('Multiple configurations found',
                message,
                function(){
                    $('input[name="program"]').val($('select[name="desiredprog"]').val().split("_")[0]);
                    $('input[name="baseline"]').val($('select[name="desiredprog"]').val().split("_")[1]);
                    $('#headersubform').submit();
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

        let data = []
        for(i=0; i < hotarr.length; i++){
            hotarr1.push(hotarr[i]);
            data.push(hotarr[i].getSourceData())

            form_save=true;
        }
        $('<input/>').attr('id', 'data_form').attr('type', 'hidden').attr('name','data_form').attr('value', JSON.stringify(data)).appendTo('#headersubform');

    });

    $('#search').click(function(event) {
        str = $('input[name="config"]').val();
        n = $('input[name="config"]').val().length;

        if(str[n-1]==";"){
           $('#config').val($('input[name="config"]').val().substring(0,n-1));
        }
        else{
           $('#headersubform').removeAttr('action');
        }
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

function removeLastSemiColon(strng){
    var n=strng.lastIndexOf(";");
    var a=strng.substring(0,n)
    return a;
}
function form_resize(){
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var displayformheight = $('#display_form').height();
    var bottombuttonheight = $('#formbuttons').height();
    var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (subformheight + bottombuttonheight + topbuttonheight + displayformheight + 5); //+ crumbheight);

    if(table_data.length > 0) {
         for(i=0; i<table_data.length; i++){

            sp = document.createElement('br');
//            if(i>=1){
                k = document.createElement('label');
                k.innerHTML = '<label for="net_value'+i+'">Net Value ($): </label><input type="text" id="net_value'+i+'" name="net_value'+i+'" style="border:none;" readonly/>';
                document.getElementById('main-body').append(k);
//            }

//            if(i>=1){
                l = document.createElement('label');
                l.innerHTML = '<label for="config'+i+'">Configuration: </label><input type="text" id="config'+i+'" name="config'+i+'" style="border:none;" readonly/>';
                document.getElementById('main-body').append(l);
//            }

//            if(i>=1){
                m = document.createElement('label');
                m.innerHTML = '<label for="catalog'+i+'">Catalog: </label><input type="text" id="catalog'+i+'" name="catalog'+i+'" style="border:none;" readonly/>';
                document.getElementById('main-body').append(m);
//            }

//            if(i>=1){
                n = document.createElement('label');
                n.innerHTML = '<label for="rev'+i+'">Rev: </label><input type="text" id="rev'+i+'" name="rev'+i+'" style="border:none;" readonly/>';
                document.getElementById('main-body').append(n);
//            }

            g = document.createElement('div');
            g.setAttribute("id", "table-wrapper"+i);
            document.getElementById('main-body').append(g);
            h = document.createElement('div');
            h.setAttribute("id", "datatable"+i);

            document.getElementById('main-body').append(h);
            document.getElementById('main-body').append(sp);

            $('#main-body').css("height", "auto");
            $('#main-body').css("margin-bottom", "40px;");
            $('#table-wrapper'+i).css("max-height", tableheight);
            $('#table-wrapper'+i).css("overflow", "hidden");

            $('#datatable'+i).css("overflow-x", "scroll");
            $('#datatable'+i).css("overflow", "hidden");
            $('#table-wrapper'+i).css("height", "auto");
            $('#datatable'+i).css("height", "auto");

            table_data1 = table_data[i];
            $('#catalog'+i).val(baselinesdata[i]);
            $('#catalog'+i).css("font-weight","normal");
            $('#rev'+i).val(baserevdata[i]);
            $('#rev'+i).css("font-weight","normal");
            $('#config'+i).val(configdata[i]);
            $('#config'+i).css("font-weight","normal");

            build_table(table_data1,i);
         }
         $('#formbuttons').css("display", "block");
         $('#formbuttons').css("z-index", "9999");
    }
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

function build_table(table_data1,i) {

    var headers = ['Line #','Product Number','Internal Product Number','Product Description','Order Qty','Unit Price',
        'Total Price','Manual Override for Total NET Price','Traceability Req. (Serialization)','Linkage','Material Group 5','HW/SW Indicator',
        'Comments (viewable by customer)','Additional Reference (viewable by customer)']; //S-05769: Addition of Product Traceability
    container = document.getElementById('datatable'+i);
    hot = new Handsontable(container, {
        data: table_data1,
        minRows: 1,
        maxRows: table_data1.length,
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

                    if(configstatusdata[i] != 'In Process/Pending'){
                         cellProperties.readOnly = true;
                    } else {
                         cellProperties.readOnly = false;
                    }

                    cellProperties.allowInvalid = false;
                    cellProperties.renderer = moneyRenderer;
                } else {
                    if(configstatusdata[i] != 'In Process/Pending'){
                        cellProperties.readOnly = true;
                    }
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

    calcValue(hot,i);

    hotarr[i] = hot;
}

function calcValue(instance,j){
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

    $('#net_value'+j).val(overall_total.toFixed(2));
    $('#net_value'+j).css("font-weight","normal");
}