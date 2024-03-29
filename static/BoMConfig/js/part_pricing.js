$('button[value="part_price"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

var hot, clean_form;
var form_save = false, first_run = true;

function customRenderer(instance, td, row, col, prop, value, cellProperties){
    var new_value;

    new_value = value;
    if (col < 4){
       td.style.background = '#DDDDDD';
        if(col < 3 && instance.getDataAtCell(row - 1, col) == value && instance.getDataAtCell(row, col - 1) == instance.getDataAtCell(row - 1, col - 1))
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
                    "Invalid cell found.  Please enter valid data before submitting the form.",
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
//S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab) added below blocks to show error message
    if(error_found=='True'){
        $('#error').css('visibility','visible');
    }else{
        $('#error').css('visibility','hidden');
    }


    $(window).load(function(){
        form_resize();
        if(hot !== undefined) {
            clean_form = JSON.stringify(hot.getSourceData());
        }
    });

    $('#part').keyup(function(){
       $('#part').val($('input[name="part"]').val().trim());
    });

    $(window).resize(function(){
        form_resize();
    });

    $('#saveForm').click(function(event){
        $('#headersubform').removeAttr('action');
        $('<input/>').attr('id','data_form').attr('type', 'hidden').attr('name','data_form').attr('value',JSON.stringify(hot.getSourceData())).appendTo('#headersubform');form_save=true;
        $('#headersubform').attr('onsubmit','return formSubmit();');
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
         //S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers
         //S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.
//            colHeaders: ['Part Number', 'Customer', 'Sold-To', 'SPUD', 'Technology', 'Latest Unit Price ($)','Valid From','Valid To', 'Cut-over Date', 'Price Erosion', 'Erosion Rate (%)', 'Comments'],
            colHeaders: ['Part Number', 'Customer', 'Sold-To', 'SPUD', 'Latest Unit Price ($)','Valid From','Valid To', 'Comments'],
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
                            cellProperties.validator = /.+/;
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

//                    case 4:
//                        if (row > (orig_length - 1) || (orig_length == 1 && orig_data[0].join().replace(/,/g, '') == $('#initial').val())) {
//                            cellProperties.type = "dropdown";
//                            // cellProperties.source = [''].concat({{ customer_list|safe }});
//                            cellProperties.source = tech_list;
//                            cellProperties.validator = /.+|^$/;
//                        } else {
//                            cellProperties.readOnly = true;
//                            cellProperties.renderer = customRenderer;
//                        }
//                        break;

                    case 4:
                        cellProperties.validator = /^\d+(.\d+)?$/;
                        cellProperties.renderer = moneyRenderer;
                        break;
//S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers( swapped case 7 to case 6 and viceversa)
                    case 5:
                        cellProperties.type = "date";
                        cellProperties.dateFormat = "MM/DD/YYYY";
                        cellProperties.correctFormat = true;
                        cellProperties.datePickerConfig = {
                            firstDay: 1,
                            showWeekNumber: true,
                            numberOfMonths: 3,
                            disableDayFn: function(date){
                                var today = new Date();
                                return date < new Date(today.getFullYear(), today.getMonth(), today.getDate()); // date.getDay() === 0 || date.getDay() === 6 ||
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

                    case 6:
                        cellProperties.type = "date";
                        cellProperties.dateFormat = "MM/DD/YYYY";
                        cellProperties.correctFormat = true;
                        cellProperties.datePickerConfig = {
                            firstDay: 1,
                            showWeekNumber: true,
                            numberOfMonths: 3,
                            disableDayFn: function(date){
                                var today = new Date();
// D-07148: Demo on S-12676: Account for valid to and valid from dates in Unit Price Mgmt (in Pricing tab): removed '+1 ' from today.getDate().
//Valid-to needs to make selection of today’s date possible
                                return date < new Date(today.getFullYear(), today.getMonth(), today.getDate()); // date.getDay() === 0 || date.getDay() === 6 ||
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

//                    case 8:
//                        cellProperties.type = "date";
//                        cellProperties.dateFormat = "MM/DD/YYYY";
//                        cellProperties.correctFormat = true;
//                        cellProperties.datePickerConfig = {
//                            firstDay: 1,
//                            showWeekNumber: true,
//                            numberOfMonths: 3,
//                            disableDayFn: function(date){
//                                var today = new Date();
//                                return date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
//                            }
//                        };
//                        cellProperties.validator = function(value, callback){
//                            if(!value){
//                                callback(true);
//                            } else {
//                                Handsontable.DateValidator.call(this, value, callback);
//                            }
//                        };
//                        break;
//
//                    case 9:
//                        cellProperties.type = 'checkbox';
//                        cellProperties.checkedTemplate = 'True';
//                        cellProperties.uncheckedTemplate = 'False';
//                        cellProperties.renderer = function(instance, td, row, col, prop, value, cellProperties){
//                            td.style.textAlign = 'center';
//                            if(value==""){
//                                value = null;
//                            }
//                            Handsontable.renderers.CheckboxRenderer.apply(this, [instance, td, row, col, prop, value, cellProperties]);
//                        };
//                        cellProperties.validator = function(value, callback){
//                            test_value = this.instance.getDataAtCell(this.row, this.col + 1);
//                            if(value == "False" && !(test_value == "" || test_value == null || test_value == undefined)){
//                                callback(false);
//                            } else {
//                                callback(true);
//                            }
//                        };
//                        break;
//
//                    case 10:
//                        cellProperties.validator = function(value, callback){
//                            if((value == "" || value == null || value == undefined) && this.instance.getDataAtCell(this.row, this.col - 1) == "True"){
//                                callback(false);
//                            } else {
//                                callback(true);
//                            }
//                        };
//                        break;

                    default:
                        cellProperties.renderer = customRenderer;
                }

                return cellProperties
            },
            beforeValidate: function(value, row, prop, source){
                var load_data = this.getData();
                if(load_data.length == 2 && load_data[0].join().replace(/,/g, '') == $('#initial').val() && load_data[1].join().replace(/,/g, '') == ""){
                    if(prop == 1 && value == ""){
                        value=" ";
                    }
//S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. changed 5 to 4
                    if(prop == 4 && value == ""){
                        value='0.00';
                    }
//S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers( swapped case 7 to case 6
//S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate. changed 6 to 5
                    if(prop == 5 && value == ""){
                        value="01/01/1900";
                    }
                }

                if (prop == 1 && value == null){
                    value = "";
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
            },
            afterValidate: function(valid, value, row, prop, source){
                if(!valid){
                    return valid;
                }

//S-05771 Swap position of Valid from and Valid to fields in Pricing-> Unit Price Management tab for all customers( swapped case 7 to case 6 and 6 to 7
//S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.changed 7 to 6
                if (prop == '6' && source == 'edit'){
                    if(Date.parse(value) <= (Date.parse(this.getDataAtCell(row, 5)) || new Date(Date.now()).setHours(0,0,0,0))){
                        return false;
                    }
// D-07148: Demo on S-12676: Account for valid to and valid from dates in Unit Price Mgmt (in Pricing tab): Added below block to make valid-to a mandatory field. Value should be 12/31/9999
                    else if (value == '' || value == undefined || value == null){
                    return false;
                    }
                }
//S-11541: Upload - pricing for list of parts in pricing tab:hide the fields Technology, Cut-over data, Price Erosion, and Erosion Rate.changed 6 to 5
                if((prop == '5' ) && source == 'edit'){
                    if (new Date(Date.now()).setHours(0,0,0,0) > Date.parse(value)){
                        return false;
                    }
//S - 12676: Unit Price Mgmt - Account for valid to and valid from dates in Unit Price Mgmt ( in Pricing tab)
                    else if (value == '' || value == undefined || value == null){
                    return false;
                    }


                }
            }
        });
    }
});
