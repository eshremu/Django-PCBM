/**
 * Created by epastag on 9/16/2016.
 */

$('button[value="price_erosion"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){
    $(window).load(function(){
        form_resize();
    });
    
    $('#data_form').submit(function(){
        $('#formData').val(JSON.stringify(hot.getData()));
        // $.ajax({
        //     url: '',
        //     type: 'POST',
        //     headers:{
        //         'X-CSRFToken': getcookie('csrftoken')
        //     },
        //     data: {
        //         changed_data: JSON.stringify(hot.getData()),
        //     },
        //     success: function(returned_data){
        //         //resultsDisplay(returned_data);
        //         console.log("SUCCESS: ", returned_data);
        //     },
        //     error: function(xhr, status, error){
        //         console.log("ERROR: ", status, error);
        //     }
        // });
    });
});

function form_resize(){
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var bottombuttonheight = $('#formbuttons').outerHeight(true);
    var subformheight = $("#headersubform").outerHeight(true);
    var crumbheight = $('#breadcrumbs').outerHeight(true);
    var bodyheight = $('#main-body').height();

    $("#main-body").css("height", bodyheight - 5);
    var tableheight = bodyheight - (topbuttonheight + bottombuttonheight);//  + crumbheight + subformheight);

    $('#table-wrapper').css("height", tableheight);
    build_table();
}

function calcRenderer (instance, td, row, col, prop, value, cellProperties) {
    var newVal = (parseFloat(instance.getSourceDataAtCell(row, 6)) * (1 - (parseFloat(instance.getSourceDataAtCell(row, 7))/100)));
    value = +(Math.round(newVal + 'e+2') + 'e-2');
    moneyRenderer(instance, td, row, col, prop, value, cellProperties);
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

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (cellProperties.readOnly) {
        td.style.background = '#DDDDDD';
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

function build_table() {
    var headers = ['Erode?', 'Part Number', 'Customer', 'Sold-To', 'SPUD', 'Technology', 'Latest Unit Price ($)', 'Erosion Rate (%)', 'Projected Unit Price ($)', 'Valid-From', 'Valid-To'];
    var container = document.getElementById('datatable');
    hot = new Handsontable(container, {
        data: data,
        minRows: 1,
        minCols: 11,
        maxCols: 11,
        rowHeaders: false,
        colHeaders: headers,
        cells: function(row, col, prop){
            var cellProperties = [];

            if(col != 0 && col != 9 && col != 10) {
                cellProperties.readOnly = true;
                cellProperties.className = 'htCenter';
            }

            if(col == 6 || col == 8){
                cellProperties.renderer = moneyRenderer;
            // } else if (col == 8){
            //     cellProperties.renderer = calcRenderer;
            } else if (col != 9 && col != 10){
                cellProperties.renderer = readonlyRenderer;
            }

            if (col == 9 || col == 10){
                cellProperties.type = "date";
                cellProperties.dateFormat = "MM/DD/YYYY";
                cellProperties.correctFormat = true;
                cellProperties.datePickerConfig = {
                    firstDay: 1,
                    showWeekNumber: true,
                    numberOfMonths: 3,
                    disableDayFn: function(date){
                        var today = new Date();
                        return date < new Date(today.getFullYear(), today.getMonth(), today.getDate() + (col - 9)); // date.getDay() === 0 || date.getDay() === 6 ||
                    }
                };
                cellProperties.validator = function(value, callback){
                    if(!value){
                        callback(true);
                    } else {
                        Handsontable.DateValidator.call(this, value, callback);
                    }
                };
            } else if (col == 0){
                cellProperties.type = 'checkbox';
                cellProperties.checkedTemplate = 'True';
                cellProperties.uncheckedTemplate = 'False';
                cellProperties.renderer = function(instance, td, row, col, prop, value, cellProperties){
                    td.style.textAlign = 'center';
                    if(value==""){
                        value = null;
                    }
                    Handsontable.renderers.CheckboxRenderer.apply(this, [instance, td, row, col, prop, value, cellProperties]);
                };
            }

            return cellProperties;
        },
        afterValidate: function(valid, value, row, prop, source){
                if(!valid){
                    return valid;
                }

                if (prop == '10' && source == 'edit'){
                    if(Date.parse(value) <= (Date.parse(this.getDataAtCell(row, 8)) || new Date(Date.now()).setHours(0,0,0,0))){
                        return false;
                    }
                }

                if((prop == '9') && source == 'edit'){
                    if (new Date(Date.now()).setHours(0,0,0,0) > Date.parse(value)){
                        return false;
                    }
                }
        }
    });

    for (var i=0; i < hot.countRows(); i++){
        var newVal = (parseFloat(hot.getSourceDataAtCell(i, 6)) * (1 - (parseFloat(hot.getSourceDataAtCell(i, 7))/100)));
        newVal = +(Math.round(newVal + 'e+2') + 'e-2');
        hot.setDataAtCell(i,8, newVal,'loadData');
    }
}