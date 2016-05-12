var hot, clean_form;
var form_save = false;

$('button[value="config_price"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){
    $(window).load(function(){
        form_resize();

        if(table_data.length > 0) {
            clean_form = JSON.stringify(hot.getSourceData());
        }
    });

    $(window).resize(function(){
        form_resize();
    });
});

function form_resize(){
    var topbuttonheight = $('#action_buttons').height();
    var displayformheight = $('#display_form').height();
    var bottombuttonheight = $('#formbuttons').height();
    var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (subformheight + bottombuttonheight + topbuttonheight + displayformheight); //+ crumbheight);

    $('#table-wrapper').css("max-height", tableheight);
    $('#table-wrapper').css("height", tableheight);

    if(table_data.length > 0) {
        build_table();
    }
}

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties) {
    customRenderer(instance, td, row, col, prop, value, cellProperties);

    td.style.background = '#DDDDDD';
}

function moneyRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (cellProperties.readOnly){
        td.style.background = '#DDDDDD';
    }

    if (value != '' && value != undefined && value != null) {
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
        'Total Price','Manual Override for Total NET Price','Linkage','Material Group 5','HW/SW Indicator',
        'Comments (viewable by customer)','Additional Reference (viewable by customer)'];
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
                if(can_write) {
                    cellProperties.validator = function (value, callback) {
                        if (/^\d+(?:\.\d{2})?$|^$/.test(value)) {
                            callback(true);
                        } else {
                            callback(false);
                        }
                    };
                    cellProperties.allowInvalid = false;
                    cellProperties.renderer = customRenderer;
                } else {
                    cellProperties.readOnly = true;
                    cellProperties.renderer = readonlyRenderer;
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
                stated_total += parseFloat(instance.getSourceDataAtCell(i, 4)) * parseFloat(instance.getSourceDataAtCell(i, 5));
            } else {
                overall_total += parseFloat(instance.getSourceDataAtCell(i, 4)) * parseFloat(instance.getSourceDataAtCell(i, 5));
            }
        }
    }
    if (overall_total == 0 && stated_total != 0){
        overall_total = stated_total;
    }

    $('#net_value').val(overall_total.toFixed(2));
}