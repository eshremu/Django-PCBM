$('button[value="part_price"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

var hot, clean_form;
var form_save = false, first_run = true;

function customRenderer(instance, td, row, col, prop, value, cellProperties){
    var new_value;

    new_value = value;
    if (col < 4){
        td.style.background = '#DDDDDD';
        if(col < 3 && instance.getDataAtCell(row - 1, col) == value)
        {
            new_value = '';
        }
    }

    if (/<[a-zA-Z]+[\s\S/]*>/.test(new_value) === false) {
        Handsontable.renderers.TextRenderer.apply(this, [instance, td, row, col, prop, new_value, cellProperties]);
    } else {
        Handsontable.renderers.HtmlRenderer.apply(this, [instance, td, row, col, prop, new_value, cellProperties]);
    }
}

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties){
    td.style.background = '#DDDDDD';
    Handsontable.renderers.TextRenderer.apply(this, arguments);
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

function formSubmit(event){
    if ($(document.activeElement).val() == 'search' || $(document.activeElement)[0] == $('#part')[0]){
        return true;
    }

    var i, j;

    if($(document.activeElement).val() == 'save' && $('#part').val() !== $('#initial').val()){
        messageToModal('The part number may have changed',
                "You have made changes to the form.  These changes will apply to the last searched part.",
                function(){$('#part').val($('initial').val()); $('#headersubform').submit();}
        );
        return false;
    } else {
        var clean_array = JSON.parse(clean_form);
        var dirty_array = hot.getSourceData();
        var changed_rows = [];

        for (i = 0; i < clean_array.length, i < dirty_array.length; i++) {
            if (JSON.stringify(clean_array[i]) !== JSON.stringify(dirty_array[i])) {
                changed_rows.push(dirty_array[i]);
            }
        }

        if(changed_rows.length < 1){
            messageToModal('No changes detected',
                    "There have been no changes made to the data.",
                    function(){}
            );
            return false;
        }

        for(i = 0; i < hot.countRows() - 1; i++){
            for(j = 0; j < hot.countCols(); j++){
                hot.validateCell(hot.getDataAtCell(i, j), hot.getCellMeta(i, j), function (valid) {}, "");
            }
        }

        if ($(document.activeElement).val() == 'save' && $('.htInvalid').length > 0) {
            messageToModal('The form contains invalid data',
                    "Required fields are missing.  Please enter the required data before submitting the form.",
                    function () {
                    }
            );
            return false;
        }

        $('<input/>').attr('id', 'data_form').attr('type', 'hidden').attr('name', 'data_form').attr('value', JSON.stringify(changed_rows)).appendTo('#headersubform');
        form_save = true;
        return true;
    }
}

$(document).ready(function(){
    definebodysize();

    $(window).load(function(){
        form_resize();
        if(hot !== undefined) {
            clean_form = JSON.stringify(hot.getSourceData());
        }
    });

    $(window).resize(function(){
        form_resize();
    });

    function form_resize() {
        var topbuttonheight = $('#action_buttons').outerHeight(true);
        var bottombuttonheight = $('#formbuttons').height();
        var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
        var crumbheight = 0;//$('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
        var bodyheight = $('#main-body').height();

        var tableheight = bodyheight - (topbuttonheight + bottombuttonheight + crumbheight + subformheight);

        $('#table-wrapper').css("height", tableheight);

        // var orig_data = {{ partlines|safe }};
        var orig_length = orig_data.length;
        var data = [];
        for(var i = 0; i < orig_data.length; i++){
            data[i] = orig_data[i].slice(0);
        }
        hot = new Handsontable($('#datatable')[0], {
            data: data,
            minSpareRows: 1,
            colHeaders: ['Part Number', 'Customer', 'Sold-To', 'SPUD', 'Latest Unit Price ($)','Valid To', 'Valid From', 'Cut-over Date', 'Price Erosion', 'Erosion Rate (%)', 'Comments'],
            cells: function(row, col, prop){
                var cellProperties = [];

                switch(col) {
                    case 0:
                        if (row > (orig_length - 1) || (orig_length == 1 && orig_data[0].join().replace(/,/g, '') == $('#initial').val())) {
                            cellProperties.readOnly = true;
                            cellProperties.renderer = readonlyRenderer;
                        } else {
                            cellProperties.readOnly = true;
                            cellProperties.renderer = customRenderer;
                        }
                        break;

                    case 1:
                        if (row > (orig_length - 1) || (orig_length == 1 && orig_data[0].join().replace(/,/g, '') == $('#initial').val())) {
                            cellProperties.type = "dropdown";
                            // cellProperties.source = [''].concat({{ customer_list|safe }});
                            cellProperties.source = cust_list;
                        } else {
                            cellProperties.readOnly = true;
                            cellProperties.renderer = customRenderer;
                        }
                        break;

                    case 2:
                        cellProperties.validator = /^\d{6}$|^$|null|(None)/;
                        if (row <= (orig_length - 1) && (orig_length != 1 || orig_data[0].join().replace(/,/g, '') != $('#initial').val())) {
                            cellProperties.readOnly = true;
                            cellProperties.renderer = customRenderer;
                        }
                        break;

                    case 3:
                        if (row > (orig_length - 1) || (orig_length == 1 && orig_data[0].join().replace(/,/g, '') == $('#initial').val())) {
                            cellProperties.type = "dropdown";
                            // cellProperties.source = [''].concat({{ spud_list|safe }});
                            cellProperties.source = spud_list;
                            cellProperties.validator = /\D+|^$/i
                        } else {
                            cellProperties.readOnly = true;
                            cellProperties.renderer = customRenderer;
                        }
                        break;

                    case 4:
                        cellProperties.validator = /^\d+(.\d+)?$/;
                        cellProperties.renderer = moneyRenderer;
                        break;

                    case 5:
                        cellProperties.type = "date";
                        cellProperties.dateFormat = "MM/DD/YYYY";
                        cellProperties.correctFormat = true;
                        cellProperties.datePickerConfig = {
                            firstDay: 1,
                            showWeekNumber: true,
                            numberOfMonths: 3,
                        };
                        cellProperties.validator = function(value, callback){
                            if(!value){
                                callback(true);
                            } else {
                                Handsontable.DateValidator.call(this, value, callback);
                            }
                        };
                        break;

                    case 6:
                        cellProperties.type = "date";
                        cellProperties.dateFormat = "MM/DD/YYYY";
                        cellProperties.correctFormat = true;
                        cellProperties.datePickerConfig = {
                            firstDay: 1,
                            showWeekNumber: true,
                            numberOfMonths: 3,
                        };
                        break;

                    case 7:
                        cellProperties.type = "date";
                        cellProperties.dateFormat = "MM/DD/YYYY";
                        cellProperties.correctFormat = true;
                        cellProperties.datePickerConfig = {
                            firstDay: 1,
                            showWeekNumber: true,
                            numberOfMonths: 3,
                            disableDayFn: function(date){
                                var today = new Date();
                                return date.getDay() === 0 || date.getDay() === 6 || date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
                            }
                        };
                        cellProperties.validator = function(value, callback){
                            if(!value){
                                callback(true);
                            } else {
                                Handsontable.DateValidator.call(this, value, callback);
                            }
                        };
                        break;

                    case 8:
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
                        cellProperties.validator = function(value, callback){
                            test_value = this.instance.getDataAtCell(this.row, this.col + 1);
                            if(value == "False" && !(test_value == "" || test_value == null || test_value == undefined)){
                                callback(false);
                            } else {
                                callback(true);
                            }
                        };
                        break;

                    case 9:
                        cellProperties.validator = function(value, callback){
                            if((value == "" || value == null || value == undefined) && this.instance.getDataAtCell(this.row, this.col - 1) == "True"){
                                callback(false);
                            } else {
                                callback(true);
                            }
                        };
                        break;

                    default:
                        cellProperties.renderer = customRenderer;
                }

                return cellProperties
            },
            beforeValidate: function(value, row, prop, source){
                var load_data = this.getData();
                if(load_data.length == 2 && load_data[0].join().replace(/,/g, '') == $('#initial').val() && load_data[1].join().replace(/,/g, '') == ""){
                    if(prop == 4){
                        value='0.00';
                    }

                    if(prop == 6){
                        value="01/01/1900";
                    }
                }
                return value;
            },
            afterChange: function(changes, source){
                if(source == "loadData"){
                    changes = changes == null ? orig_data.map(function(currVal, idx, arr){return [idx];}) : changes;
                }

                if(source != "empty") {
                    var rows_changed = [];
                    var i, j;
                    for(i = 0; i < changes.length; i++) {
                        // Get changed rows
                        if(rows_changed.indexOf(changes[i][0]) == -1){
                            rows_changed.push(changes[i][0]);
                        }
                    }

                    for(i = 0; i < rows_changed.length; i++){
                        if(this.getDataAtRow(rows_changed[i]).join().replace(/,/g, '') != "") {
                            for (j = 0; j < this.countCols(); j++) {
                                this.validateCell(this.getDataAtCell(rows_changed[i], j), this.getCellMeta(rows_changed[i], j), function (valid) {
                                }, source);
                            }
                        } else {
                            for (j = 0; j < this.countCols(); j++) {
                                this.getCellMeta(rows_changed[i], j).valid = true;

                            }
                            this.render();
                        }
                    }
                }
            }
        });
    }
});