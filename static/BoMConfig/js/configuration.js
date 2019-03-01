$('button[value="config"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');

function ValidationXHRHash () {
    // This will more of a dynamic staggered array than an actual hash
    // XHR objcts will be stored by row -> col in order to allow multiple validations to occur simultaneously
    this.storage = {};

    this.add = function(row, col, obj, settings){
        if (!this.storage.hasOwnProperty(row)) {
            this.storage[row] = {};
        }

        if (!this.storage[row].hasOwnProperty(col)) {
            this.storage[row][col] = {request: obj, isInProcess: obj.readyState !=4 , settings: settings};
        } else {
            if (this.storage[row][col]['request'] !== undefined && this.storage[row][col]['request'].readyState !=4){
                this.storage[row][col]['request'].abort();
            }
            this.storage[row][col]['request'] = obj;
            this.storage[row][col]['isInProcess'] = obj.readyState !=4;
            this.storage[row][col]['settings'] = settings;
        }
    };

    this.remove = function(row, col){
        if (this.storage.hasOwnProperty(row)){
            if (this.storage[row].hasOwnProperty(col)){
                if (this.storage[row][col]['request'] !== undefined && this.storage[row][col]['request'].readyState !=4){
                    this.storage[row][col]['request'].abort();
                }
                this.storage[row][col]['request'] = undefined;
                this.storage[row][col]['isInProcess'] = false;
                this.storage[row][col]['settings'] = undefined;
            }
        }
    };

    this.finish = function(row, col){
        if (this.storage.hasOwnProperty(row)) {
            if (this.storage[row].hasOwnProperty(col)) {
                this.storage[row][col]['isInProcess'] = this.storage[row][col]['request'].readyState !=4;
            }
        }
    };

    this.removeRow = function(row, amount){
        var keys = Object.keys(this.storage).sort();

        for(var idx in keys){
            var key = keys[idx];
            if(this.storage.hasOwnProperty(key)) {
                if (key >= row && key < row + amount) {
                    delete this.storage[key];
                } else if(key >= row + amount){
                    this.storage[key - amount] = this.storage[key];
                    delete this.storage[key];
                }
            }
        }
    };

    this.addRow = function(row, amount){
        var keys = Object.keys(this.storage).sort().reverse();

        for(var idx in keys){
            var key = keys[idx];
            if(this.storage.hasOwnProperty(key)) {
                if(key >= row){
                    this.storage[parseInt(key) + amount] = this.storage[key];
                    delete this.storage[key];
                }
            }
        }
    };

    this.validating = function(rowToCheck){
        var inprocess = false;

        if(rowToCheck === undefined) {
            for (var row in this.storage) {
                if (this.storage.hasOwnProperty(row)) {
                    for (var col in this.storage[row]) {
                        if(this.storage[row].hasOwnProperty(col)) {
                            if (this.storage[row][col]['isInProcess']) {
                                inprocess = true;
                            }
                        }
                    }
                }
            }
        } else {
            if (this.storage.hasOwnProperty(rowToCheck)) {
                for (var col in this.storage[rowToCheck]) {
                    if(this.storage[rowToCheck].hasOwnProperty(col)) {
                        if (this.storage[rowToCheck][col]['isInProcess']) {
                            inprocess = true;
                        }
                    }
                }
            }
        }

        return inprocess;
    };
}

var validationStorage = new ValidationXHRHash();
var validationQueue = new XHRQueue(validationStorage);

function cleanDataCheck(link){
    var dirty_form = hot.getSourceData();
    for(var i = 0; i < dirty_form.length; i++){
        if(typeof dirty_form[i] == 'object'){
            delete dirty_form[i][0];
        }
    }
    $('[name="data_form"]').remove();
    var dirty_sub = $('#configform').serialize();
    $('<input/>').attr('type', 'hidden').attr('name','data_form').attr('value',JSON.stringify(dirty_form)).appendTo('#configform');

    if(JSON.stringify(dirty_form) !== JSON.stringify(clean_form)|| JSON.stringify(dirty_sub) !== JSON.stringify(clean_sub)) {
        valid = false;
    }

    if (!valid && !form_save && !(frame_readonly || active_lock)){
        messageToModal('Unsaved changes detected',
                "You have made changes to the form.  If you navigate away from this page without saving, all changes will be lost.",
                function(){
                    if (link.target == "_blank"){
                        window.open(link.dataset.href);
                    } else {
                        window.location.href = link.dataset.href;
                    }
                }
        );
    } else {
        if (link.target == "_blank"){
            window.open(link.dataset.href);
        } else {
            window.location.href = link.dataset.href;
        }
    }
}

$(document).ready(function(){
    $(window).load(function(){
        form_resize();
    });

    $(window).on('beforeunload',function(){
        var dirty_form = hot.getSourceData();
        for(var i = 0; i < dirty_form.length; i++){
            if(typeof dirty_form[i] == 'object'){
                delete dirty_form[i][0];
            }
        }
        $('[name="data_form"]').remove();
        var dirty_sub = $('#configform').serialize();

        if(JSON.stringify(dirty_form) !== JSON.stringify(clean_form)|| JSON.stringify(dirty_sub) !== JSON.stringify(clean_sub)) {
            valid = false;
        }

        if (closeButton && !valid && !form_save){
            return "You have made changes to the form.  If you navigate away from this page without saving, all changes will be lost.";
        }
    });

    $(window).resize(function(){
        form_resize();
    });

    $('#saveForm').click(function(){
        if(!validating) {
            $('#formaction').val('save');
            submit();
        }
    });

    $('#saveexitForm').click(function(){
        if(!validating) {
            $('#formaction').val('saveexit');
            submit();
        }
    });

    $('#nextForm').click(function(){
        if(!validating) {
            $('#formaction').val('next');
            submit();
        }
    });

    $('#prevForm').click(function(){
        if(!validating) {
            $('#formaction').val('prev');
            submit();
        }
    });

     $('#validateForm').click(function () {
        if (configuration_status == 'In Process' || configuration_status == 'In Process/Pending') {
            $.ajax({
            <!--S-10576: Change the header of the tool to ACC :- Changed the tool name from pcbm to acc-->
                url: "/acc/entry/config/?validation=true",
                type: "GET",
                success: function () {
                    if (!validating) {
                         $('#formaction').val('validate');
                         submit();
                    }
                }
            });
        }
    });

    var endstr = "?validation=true";
    var end = window.location.href.endsWith(endstr);

    var findreadonly = window.location.href.indexOf("readonly");

    $("#saveexitForm").attr('disabled', 'disabled').css('color','gray');
    $("#saveForm").attr('disabled', 'disabled').css('color','gray');
    $("#status").css('color','#FF8800');
    $("#status").html('PAGE LOADED,VALIDATION PENDING');
    if(!end && findreadonly == -1){
       if (configuration_status == 'In Process' || configuration_status == 'In Process/Pending' ){
            $("#validateForm").trigger('click');
       }
     }
});

function submit(){
    $("#status").css('color','#AAAAAA');
    $("#status").html('VALIDATING...');
    if (configuration_status != 'In Process') {
        $('#configform').submit();
    } else {
        if(status !== 'ERROR'){
            $('#configform').submit();
        } else if (submit){
            $('#statuses').html('Error(s) found. Save failed.');
            setTimeout(function(){$('#statuses').fadeOut('slow')}, 10000);
        }
    }
}

function form_resize(){
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var bottombuttonheight = $('#formbuttons').outerHeight(true);
    var subformheight = $("#headersubform").outerHeight(true);// + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').outerHeight(true);// + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (topbuttonheight + bottombuttonheight + crumbheight + subformheight);

    $('#table-wrapper').css("height", tableheight);
    build_table();
}

function determineColumns(readonly, hidden_cols){
    if (bom_write_auth) {
        readonly.push(0);
    } else {
        readonly.push(0, 1, 2, 3, 4);
    }

    if(SAPVis === true && sap_read_auth){
        if (sap_write_auth) {
            readonly.push(5);
        } else {
            readonly.push(5, 6, 7, 8, 9, 10);
        }

        $('#viewsap').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(5, 6, 7, 8, 9, 10);
        $('#viewsap').removeAttr('style');
    }

    if(AttrVis === true && attr_read_auth){
// S-08473: Adjust configuration table to include new columns:- Added 'Portfolio-Code'(14),'Plant-Specific Material Status'(18),
// 'Distribution-Chain Specific Material Status' (19) as readonly & added in next 4 lists [added],
        if (attr_write_auth && configuration_status == 'In Process')
        {
            readonly.push( 14, 15, 16, 17, 18, 19, 21, 22);  //  [added]
        } else if (attr_write_auth) {
            readonly.push(11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22);   //  [added]
        } else {
            readonly.push(11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22);   //  [added]
        }

        // readonly.push(15, 16, 17); # ON HOLD UNTIL PRIM INTERFACE OBTAINED

        $('#viewattr').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22);   //  [added]
        $('#viewattr').removeAttr('style');
    }

    if(PriceVis === true && price_read_auth) {
        readonly.push(21,22);    //Added for readonly of 21 & 22 columns
        if (!price_write_auth) {
            readonly.push(23, 24, 25, 26, 27);
        } else if (price_write_auth && configuration_status == 'In Process/Pending') {
            readonly.push(23, 24, 25);
        }

        $('#viewprice').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(22, 23, 24, 25, 26, 27);
        $('#viewprice').removeAttr('style');
    }

    if(CustVis === true && cust_read_auth) {
        //readonly.push(24); # ON HOLD UNTIL PRIM INTERFACE OBTAINED
        readonly.push(29, 30, 31, 32);
        if (!cust_write_auth || (cust_write_auth && configuration_status != 'In Process')) {
            readonly.push(28);
        }

        $('#viewcust').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(28, 29, 30, 31, 32);
        $('#viewcust').removeAttr('style');
    }

    if(BaselineVis === true && baseline_read_auth){
        if (!baseline_write_auth) {
            readonly.push(33, 34, 35);
        } else if (baseline_write_auth && configuration_status != 'In Process' && next_approval == 'csr') {
            readonly.push(33, 34);
        } else if (baseline_write_auth && configuration_status != 'In Process' && next_approval == 'blm') {
            readonly.push(33, 35);
        }
        $('#viewbase').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(33, 34, 35);
        $('#viewbase').removeAttr('style');
    }
}

function statusRenderer(instance, td, row, col, prop, value, cellProperties){
    var newValue;

    switch(value){
        case 'OK':
            newValue = '<span class="glyphicon glyphicon-ok-sign" style="color:#00AA00;"></span>';
            break;
        case '!':
            newValue = '<span class="glyphicon glyphicon-exclamation-sign" style="color:#FF8800;"></span>';
            break;
        case 'X':
            newValue = '<span class="glyphicon glyphicon-remove-sign" style="color:#DD0000;"></span>';
            break;
        case '?':
            newValue = '<span class="glyphicon glyphicon-question-sign" style="color:#0055FF;"></span>';
            break;
        case 'INW':
            newValue = '<span class="glyphicon glyphicon-option-horizontal" style="top:3px;"></span>';
            break;
        default:
            newValue = value;
    }

    readonlyRenderer(instance, td, row, col, prop, newValue, cellProperties);
}

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties) {
    customRenderer(instance, td, row, col, prop, value, cellProperties);
    td.style.background = '#DDDDDD';
}
//  S-08480: Apply color background to portfolio code based on value:- Added the renderer function below to show the color of the cell based on value
function colorcodeRenderer(instance, td, row, col, prop, value, cellProperties) {
    customRenderer(instance, td, row, col, prop, value, cellProperties);
    td.style.color= 'black';
    if(value == 'GREEN' || value == 'Green' ){
         td.style.background = 'green';
    }else if(value == 'RED' || value == 'Red'){
         td.style.background = 'red';
    }else if(value == 'YELLOW'|| value == 'Yellow'){
         td.style.background = 'yellow';
    }else if(value == 'OBSOLETE'|| value == 'Obsolete'){
         td.style.background = 'orange';
    }else{
         td.style.background = 'rgb(221, 221, 221)';
    }
}

function moneyRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (cellProperties.readOnly){
        td.style.background = '#DDDDDD';
    }

    if (value != '' && value != undefined && value != null) {
        var result;
        var overridden = String(value).charAt(0) == "!";
        var dummy = String(value).replace("$","").replace(',','').replace(' ','').replace("!","");
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

        value = "$" + result + '.' + fracDummy;

        if (negative){
            value = "(" + value + ")";
        }

        if (overridden){
            value = "!" + value;
        }
    }
    customRenderer(instance, td, row, col, prop, value, cellProperties);
}

function customRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (row === 0 && col === 22 && typeof(value) == 'string' && value.charAt(0)==='!' && PriceVis){
        value = value.slice(1);
    }

    if (cellProperties.className != undefined && cellProperties.className.indexOf('hidden_cell') != -1) {
        td.style['white-space'] = 'nowrap';
    }

    if (/<[a-zA-Z][\s\S/]*>/.test(value) === false) {
        Handsontable.renderers.TextRenderer.apply(this, arguments);
    } else {
        Handsontable.renderers.HtmlRenderer.apply(this, arguments);
    }
}

// TODO: Figure out why hiding columns causes row height to change
function build_table() {
    determineColumns(readonly_columns, hidden_cols);
    var container = document.getElementById('datatable');
// S-08473: Adjust configuration table to include new columns:- Added colwidth as 90 for 'Portfolio-Code' at no.14, & 140 each for 'Plant-Specific Material Status' at no.18,
// 'Distribution-Chain Specific Material Status' at no.19,     
 	var colWidths = [50,50,150,342,72,50,74,50,50,62,264,81,103,50,90,68,63,117,140,140,65,125,125,
            119,116,162,105,62,160,118,246,124,176,151,250,250];         // S-05770 : Added a new colwidth for net price & resized unit price to 125
    hot = new Handsontable(container, {
        data: data,
        minRows: 1,
        minCols: 36,
        maxCols: 36,
        minSpareRows: overall_write_auth && !frame_readonly ? 5 : 0,
        rowHeaders: false,
//      S-05768-Rename Unit Price to Net Price and Add Unit Price- Added new column 'Unit Price' at no.18 and renamed existing unit price to 'Net Price' at no.19.
//      S-08473: Adjust configuration table to include new columns:- Added 'Portfolio-Code' at no.14,'Plant-Specific Material Status' at no.18,
//            'Distribution-Chain Specific Material Status' at no.19,
        colHeaders: [
            'Status', 'Line #', 'Product Number<br><span class="smallItalics">'+config_id+"</span>", "Product Description", 'Order Qty',
            'UoM', 'Context ID','Plant', 'SLOC', 'Item Cat', 'P-Code - Fire Code, Desc',
            'HW/SW Ind', 'Prod Pkg Type', 'SPUD', 'Portfolio-Code', 'RE-Code', 'MU-Flag', "X-Plant Mat'l Stat", 'Plant-Specific Material Status',
            'Distribution-Chain Specific Material Status','Int Notes',
            'Unit Price','Net Price', "Higher Level Item", 'Material Group 5', 'Purchase Order Item No', 'Condition Type', 'Amount',
            'Traceability Req. (Serialization)', 'Customer Asset', 'Customer Asset Tagging Requirement', 'Customer Number', 'Second Customer Number',
            'Vendor Article Number', 'Comments', 'Additional Reference (if required)',
        ],
        fixedColumnsLeft: 3,
        manualColumnFreeze: true,
        currentRowClassName: 'currentRow',
//       S-05768-Rename Unit Price to Net Price and Add Unit Price- Added {data:32}, as a new column got added.
//       S-08473: Adjust configuration table to include new columns:- Added {data:33},{data:34},{data:35} as 3 new columns got added.

      columns: [
            {data: 0}, {data: 1}, {data: 2}, {data: 3}, {data: 4}, {data: 5},
            {data: 6}, {data: 7}, {data: 8}, {data: 9}, {data: 10}, {data: 11},
            {data: 12}, {data: 13}, {data: 14}, {data: 15}, {data: 16}, {data: 17},
            {data: 18}, {data: 19}, {data: 20}, {data: 21}, {data: 22}, {data: 23},
            {data: 24}, {data: 25}, {data: 26}, {data: 27}, {data: 28}, {data: 29},
            {data: 30}, {data: 31}, {data: 32}, {data: 33}, {data: 34}, {data: 35}
        ],
        manualColumnResize: true,
        copyPaste: true,
        wordWrap: true,
        contextMenu: configuration_status == 'In Process' && !frame_readonly ? {
            items: {
                'undo': {},
                'redo': {},
                'row_above': {
                    disabled: function () {
                        if (!is_picklist){
                            return this.getSelected()[0] === 0;
                        }
                    }
                },
                'row_below': {},
                'remove_row': {
                    disabled: function () {
                        if (!is_picklist){
                            return this.getSelected()[0] === 0;
                        }
                    }
                }
            }
        } : false,
        comments: true,
        afterGetColHeader: function(col, th){
            if(hidden_cols.indexOf(parseInt(col)) != -1) {
                th.className += 'hidden_col';
            }
        },
        cells: function(row, col, prop){
            var cellProperties = {
                className: ''
            };

            if(hidden_cols.indexOf(parseInt(col)) != -1){
                if (this.instance.getPlugin('ManualColumnResize').manualColumnWidths.hasOwnProperty(parseInt(col)) &&
                        this.instance.getPlugin('ManualColumnResize').manualColumnWidths[parseInt(col)] != undefined &&
                        previous_widths[parseInt(col)] == undefined){
                    previous_widths[parseInt(col)] = this.instance.getPlugin('ManualColumnResize').manualColumnWidths[parseInt(col)];
                    this.instance.getPlugin('ManualColumnResize').manualColumnWidths[parseInt(col)] = 0;
                }
                cellProperties.width = 0;
                cellProperties.className += 'hidden_cell' + ' ';
            } else {
                if (previous_widths.hasOwnProperty(parseInt(col)) && previous_widths[parseInt(col)] != undefined){
                    this.instance.getPlugin('ManualColumnResize').manualColumnWidths[parseInt(col)] = previous_widths[parseInt(col)];
                    previous_widths[parseInt(col)] = undefined;
                }

                cellProperties.width = colWidths[parseInt(col)];
                if (cellProperties.className != undefined && cellProperties.className.indexOf('hidden_cell') != -1){
                    cellProperties.className = cellProperties.className.replace('hidden_cell', '');
                }
            }

            if(active_lock || (!is_picklist  && (row === 0 && [1,2,4].indexOf(col)!== -1)) || readonly_columns.indexOf(col) !== -1){
                cellProperties.readOnly = true;
   // S-05768-Rename Unit Price to Net Price and Add Unit Price- Renamed Unit to Net & also added 'Unit Price' for the currency format
                if (['Net Price', 'Amount', 'Unit Price'].indexOf(this.instance.getColHeader(col)) != -1){//(col == 17 || col == 23) && PriceVis){
                    cellProperties.renderer = moneyRenderer;
                } else {
                    cellProperties.renderer = readonlyRenderer;
                }
            } else {
   // S-05768-Rename Unit Price to Net Price and Add Unit Price- Renamed Unit to Net & also added 'Unit Price' for the currency format
               if (['Net Price', 'Amount','Unit Price'].indexOf(this.instance.getColHeader(col)) != -1){
                    cellProperties.renderer = moneyRenderer;
                } else {
                    cellProperties.renderer = customRenderer;
                }
            }


            if (['Status'].indexOf(this.instance.getColHeader(col)) != -1){
                cellProperties.renderer = statusRenderer;
            }

            if (['Amount'].indexOf(this.instance.getColHeader(col)) != -1){
                cellProperties.validator = function(value, callback){
                    if(/^(?:-)?(?:\$)?\d{1,3}(?:,\d{3})*(?:\.\d{2})?$|^(?:-)?\d+(?:\.\d{2})?$|^$|^null$|^undefined$/.test(value)){
                        callback(true);
                    } else {
                        callback(false);
                    }
                };
            }

            if(this.instance.getColHeader(col) == 'Order Qty'){
                cellProperties.validator = /^\d+(?:\.\d+)?$|^$/
            }
 //  S-08480: Apply color background to portfolio code based on value:- Added the renderer to show the color of the cell based on value
             if (['Portfolio-Code'].indexOf(this.instance.getColHeader(col)) != -1){
                cellProperties.renderer = colorcodeRenderer;
            }

            if (['Line #', 'Product Description', 'SPUD', 'Int Notes','P-Code - Fire Code, Desc', 'Vendor Article Number','Comments','Additional Reference (if required)'].indexOf(this.instance.getColHeader(col)) != -1){ //
                cellProperties.className += 'htLeft';
 // S-05768-Rename Unit Price to Net Price and Add Unit Price- Renamed Unit price to Net price
            } else if (['Net Price', 'Amount'].indexOf(this.instance.getColHeader(col)) != -1){
                cellProperties.className += 'htRight';
            } else if (/^Product Number/.test(this.instance.getColHeader(col))) {
                cellProperties.className += 'htLeft';
            } else {
                cellProperties.className += 'htCenter';
            }

            if(this.instance.getColHeader(col) == 'Condition Type'){
                cellProperties.type = 'dropdown';
                cellProperties.source = [''].concat(condition_list);
            }

            if(this.instance.getColHeader(col) == 'Material Group 5'){
                cellProperties.type = 'dropdown';
                cellProperties.source = [''].concat(material_group_list);
            }

            if(this.instance.getColHeader(col) == 'Prod Pkg Type'){
                cellProperties.type = 'dropdown';
                cellProperties.source = [''].concat(product_pkg_list);
            }

            if(this.instance.getColHeader(col) == 'SPUD'){
                cellProperties.type = 'dropdown';
                cellProperties.source = [''].concat(spud_list);
            }

            if(this.instance.getColHeader(col) == 'Item Cat'){
                cellProperties.type = 'dropdown';
                cellProperties.source = [''].concat(item_cat_list);
            }

            return cellProperties;
        },
        afterValidate: function(isValid, value, row, prop, source){
            if(this.isEmptyRow(row)){
                return true;
            } else if (!isValid){
                $('#prevForm').attr('disabled', 'disabled').css('color','gray');
                $("#saveexitForm").attr('disabled', 'disabled').css('color','gray');
                $("#saveForm").attr('disabled', 'disabled').css('color','gray');
                $("#nextForm").attr('disabled', 'disabled').css('color','gray');

                this.setCellMeta(row, prop, 'cellStatus', 'X');
                UpdateValidation(row, this);
            }
        },
        afterChange: function(changes, source){
            var tableThis = this;

            if($('.htInvalid').length == 0 && source != 'validation'){
                $('#prevForm').removeAttr('disabled').css('color','');
                $("#saveexitForm").removeAttr('disabled').css('color','');
                $("#saveForm").removeAttr('disabled').css('color','');
                $("#nextForm").removeAttr('disabled').css('color','');
            }

            if(!frame_readonly && !active_lock) {
                /*
                 Trigger validation for each change in "changes" and store request in XHR tracker
                 edits caused by user inputs will have source=='edit' but changes caused by validation will have source=='validation'
                 so we do nothing on 'validation' changes because we want to avoid creating a feedback loop
                 */

                // On "loadData", turn all data into an array of changes in order to validate
                if(source === 'loadData'){
                    var dataset = JSON.parse(JSON.stringify(tableThis.getSourceData()));
                    dataset.splice(-1 * tableThis.countEmptyRows(true));

                    changes = [];

                    for(var row in dataset){
                        if(!dataset.hasOwnProperty(row)){
                            continue;
                        }
                        for(var col in dataset[row]){
                            if(!dataset[row].hasOwnProperty(col)){
                                continue;
                            }

                            if(dataset[row][col] != null) {
                                changes.push([row, col, null, dataset[row][col]]);
                            }
                        }
                    }
                }

                if (['loadData','validation'].indexOf(source) == -1) {
                    for (var i = 0; i < changes.length; i++) {
                        // Validate any elements locally that we can and push the rest to the server for validation

                        // Get cellMeta for modifications
                        var cellMeta = tableThis.getCellMeta(parseInt(changes[i][0]), parseInt(changes[i][1]));
                        if(cellMeta['comment'] === undefined){
                            cellMeta['comment'] = {value: ''};
                        } else {
                            cellMeta['comment']['value'] = '';
                        }
                        cellMeta['cellStatus'] = 'OK';
                        var dataGenerator = function () {
                            return {
                                row: parseInt(changes[i][0]),
                                col: parseInt(changes[i][1]),
                                value: changes[i][3],
                                allowChain: source != 'loadData'
                            }
                        };

                        var data = dataGenerator();
                        switch(parseInt(changes[i][1])){
                            case 0: // Status
                                continue;
                                break;
                            case 1: // Line number
                                // Test format
                                if(!/^\d+(?:\.\d+){0,2}$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid format. Use #.#.# format.\n';
                                } else {
                                    var partnumber = tableThis.getDataAtCell(changes[i][0], 2);
                                    var other_lines = tableThis.getDataAtCol(1);
                                    other_lines.splice(-1 * tableThis.countEmptyRows(true));
                                    other_lines.splice(changes[i][0], 1);
                                    // Test duplication
                                    if (changes[i][3] && other_lines.indexOf(changes[i][3]) !== -1) {
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Line number already exists.\n';
                                    } else
                                    // Test parent exists
                                    if (changes[i][3] && changes[i][3].indexOf(".") > -1 && other_lines.indexOf(changes[i][3].slice(0, changes[i][3].lastIndexOf("."))) == -1) {
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Parent line item not found.\n';
                                    } else
                                    // Ensure part number has correct number of dots
                                    if(changes[i][3] && partnumber){
                                        var modPartnumber = partnumber.trim();
                                        modPartnumber = modPartnumber.replace(/^\.+/, '');
                                        modPartnumber = modPartnumber.toUpperCase();
                                        if(changes[i][3].split(".").length == 3){
                                            modPartnumber = ".." + modPartnumber;
                                        } else if(changes[i][3].split(".").length == 2) {
                                            modPartnumber = "." + modPartnumber;
                                        }
                                        if(modPartnumber != partnumber){
                                            tableThis.setDataAtRowProp(parseInt(changes[i][0]), 2, modPartnumber, 'validation');
                                        }
                                    }

                                    // Generate validation of Condition to ensure line number related errors are removed
                                    if(changes[i][2] !== changes[i][3]){
                                        tableThis.setDataAtRowProp(parseInt(changes[i][0]), 24, tableThis.getDataAtCell(parseInt(changes[i][0]), 24), 'edit');
                                    }
                                }
                                break;
                            case 2: // Product number
                                var partnumber = changes[i][3];
                                var old_partnumber = changes[i][2];
                                if(partnumber){
                                    // Convert to trimmed uppercase string
                                    partnumber = partnumber.toUpperCase().trim();

                     // Remove any leading dots pertaining to line number--> partnumber = partnumber.replace(/^\.+/, '');      //not required now
                                    if(old_partnumber){
                                        old_partnumber = old_partnumber.toUpperCase().trim();
                                        old_partnumber = old_partnumber.replace(/^\.+/, '');
                                    }

                                    var van = partnumber;

                                    // If partnumber is all digits, and slash to end
                                    if(/^\d+$/.test(partnumber)){
                                        partnumber += "/";
                                    }

                                    // Test if length of part number is too long
                                    if(partnumber.length > 18){
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Product Number exceeds 18 characters.\n';
                                    }
                                    // Add part number to data being sent to server before further modification
                                    data['value'] = partnumber;
                                    data['send'] = partnumber != old_partnumber;
                                    // If line number is populated, ensure part number has leading dots to match
                                    if(tableThis.getDataAtCell(changes[i][0], 1)){
                                        var lineNumber = tableThis.getDataAtCell(changes[i][0], 1);
                                        if(lineNumber.split(".").length == 3){
                                            partnumber = ".." + partnumber;
                                        } else if(lineNumber.split(".").length == 2) {
                                            partnumber = "." + partnumber;
                                        }
                                    }
                                    // If part number is not populated, generate a part number
                                    else {
                                        var lineEstimates = estimateLineNumbers([changes[i]], tableThis.getDataAtCol(1));
                                        tableThis.setDataAtRowProp(parseInt(changes[i][0]), 1, lineEstimates[changes[i][0]], "edit");
                                    }

                                    // Clean & set Vendor Article Number
                                    van = van.replace(/^\.+/, '').replace(/\/$/, '');
                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 33, van, 'edit');

                                    // Set current cell to updated & cleaned value
                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 2, partnumber, 'validation');

                                    if(partnumber && !tableThis.getDataAtCell(changes[i][0], 4)){
                                        var qtyMeta = tableThis.getCellMeta(parseInt(changes[i][0]), 4);

                                        if(qtyMeta['comment'] === undefined){
                                            qtyMeta['comment'] = {value: ''};
                                        }

                                        if(!(qtyMeta['cellStatus'] == 'X' && qtyMeta['comment']['value'].includes("X - Invalid Order Qty.\n"))) {
                                            qtyMeta['cellStatus'] = "X";
                                            qtyMeta['comment']['value'] += "X - Invalid Order Qty.\n";
                                        }

                                        tableThis.setCellMetaObject(parseInt(changes[i][0]), 4, qtyMeta);
                                    }
                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 2, partnumber, 'validation');
                                }
                                break;
                            case 3: // Product description
                                var description = changes[i][3] === null ? "" : changes[i][3].toUpperCase();

                                if(description.length > 40){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Product Description exceeds 40 characters.\n';
                                }

                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 3, description, 'validation');
                                break;
                            case 4: // Order qty
                                // Test format
                                if(!/^\d+(?:\.\d+)?$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid format. Use #.# format.\n';
                                } else {
                                    if(/^$/.test(changes[i][3]) && tableThis.getDataAtCell(changes[i][0], 2)){
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Invalid Order Qty.\n';
                                    } else {
                                        // Convert to float with at least one decimal
                                        var updatedQty = parseFloat(changes[i][3]);
                                        if(Number.isInteger(updatedQty)){
                                            updatedQty = updatedQty + ".0";
                                        } else {
                                            updatedQty = updatedQty.toString();
                                        }
                                        tableThis.setDataAtRowProp(parseInt(changes[i][0]), 4, updatedQty, 'validation');
                                    }
                                }
                                break;
                            case 5: // UoM
                                break;
                            case 6: // Context ID
                                if(!changes[i][3] && tableThis.getDataAtCell(parseInt(changes[i][0]), 12) == "Assembled Sales Object (ASO)"){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - ContextID must be populated for ASO parts.\n';
                                }
                                break;
                            case 7: // Plant
                                if(!/^\d{4}$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid Plant.\n';
                                } else if(/^\d{4}$/.test(changes[i][3])){
                                    data['value'] = changes[i][3];
                                    data['part_number'] = tableThis.getDataAtCell(parseInt(changes[i][0]), 2);
                                    data['send'] = changes[i][3] != changes[i][2];
                                }
                                break;
                            case 8: // SLOC
                                if(!/^\w{3,4}$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid SLOC.\n';
                                } else if(/^\w{3,4}$/.test(changes[i][3])){
                                    data['value'] = changes[i][3];
                                    data['plant'] = tableThis.getDataAtCell(parseInt(changes[i][0]), 7);
                                    data['part_number'] = tableThis.getDataAtCell(parseInt(changes[i][0]), 2);
                                    data['send'] = changes[i][3] != changes[i][2];
                                }
                                break;
                            case 9: // Item Category
                                break;
                            case 10: // P-Code
                                var p_code = changes[i][3] === null ? null : changes[i][3].toUpperCase();
                                
                                if(!/^\d{2,3}$|^\(\d{2,3}-\d{4}\).*$|^[A-Z]\d{2}$|^\([A-Z]\d{2}-\d{4}\).*$|^$/.test(p_code)){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid P-Code format.\n';
                                } else if (p_code) {
                                    var found = p_code.match(/^(\d{2,3})$|^\((\d{2,3})-\d{4}\).*$|^([A-Z]\d{2})$|^\(([A-Z]\d{2})-\d{4}\).*$|^$/);
                                    data['value'] = (found[1] || found[2] || found[3] || found[4]);
                                    //data['send'] = changes[i][3] != changes[i][2];
                                }
                                
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 10, p_code, 'validation');
                                break;
                            case 11: // HW/SW Indicatory
                                var commodity = changes[i][3] === null ? null : changes[i][3].toUpperCase();
                                if(!/^HW$|^SW$|^CS$|^$/.test(commodity)){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid HW/SW Ind.\n';
                                }

                                if(/^\(752-2487\) LTE RBS SW$|^\(872-2491\) RBS HWAC$|^752$|^872$/.test(tableThis.getDataAtCell(parseInt(changes[i][0]), 10))){
                                    commodity = "SW";
                                }

                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 11, commodity, 'validation');
                                break;
                            case 12: // Product Package Type
                                break;
                            case 13: // SPUD
                                break;
//   S-08474:- Pull BCAMDB on part addition / validation : added Portfolio code case for validation on adding part number
                            case 14: // Portfolio-Code
                                var portcode = changes[i][3] === null ? "" : changes[i][3].toUpperCase();

    // S-08475:- Adjust validation process to flag parts with non-green portfolio code: Added below to check if green or not, show warning message notifying if not green
                                if(portcode !=  'GREEN'){
                                    cellMeta['cellStatus'] = "!";
                                    cellMeta['comment']['value'] += '! - Portfolio code is Non-Green.\n';
                                }
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 14, portcode, 'validation');
                                break;
                            case 15: // RE-Code
                                var REerr=changes[i][3] ? changes[i][3].trim() : changes[i][3];
                                if(REerr == null){
                                continue;
                                }
                                else{
                                var RECode=REerr.substring(0,REerr.indexOf(","));
                                var REMsg = REerr.substring(REerr.indexOf(",")+1);
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 15, RECode ? RECode.trim() : RECode, 'validation');
                                //data['value'] = changes[i][3];
                                cellMeta['cellStatus'] = "OK";
                                cellMeta['comment']['value'] += REMsg;
                                }
                                break;
                            case 16: // MU-Flag
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 16, changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3], 'validation');
                                data['value'] = changes[i][3];
                                data['send'] = changes[i][3] && changes[i][3] != changes[i][2];
                                break;
                            case 17: // X-Plant Material Status
                                var Xplt=changes[i][3] ? changes[i][3].trim() : changes[i][3];
                                if(Xplt == null){
                                continue;
                                }
                                else{
                                var XpltCode=Xplt.substring(0,Xplt.indexOf(","));
                                var XpltErr = Xplt.substring(Xplt.indexOf(",")+1);
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 17, XpltCode ? XpltCode.trim() : XpltCode, 'validation');
                                //data['value'] = changes[i][3];
                                cellMeta['cellStatus'] = "OK";
                                cellMeta['comment']['value'] += XpltErr;
                                 }
                                break;
    //   S-08474:- Pull BCAMDB on part addition / validation : added Plant Specific Material Status case for validation on adding part number
                            case 18: // Plant Specific Material Status
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 18, changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3], 'validation');
                                data['value'] = changes[i][3];
                                data['send'] = changes[i][3] && changes[i][3] != changes[i][2];
                                break;
    //   S-08474:- Pull BCAMDB on part addition / validation : added Distribution Chain Specific Material Status case for validation on adding part number
                            case 19: // Distribution Chain Specific Material Status
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 19, changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3], 'validation');
                                data['value'] = changes[i][3];
                                data['send'] = changes[i][3] && changes[i][3] != changes[i][2];
                                break;
                            case 20: // Internal Notes
                                var int_notes = changes[i][3] ? changes[i][3].trim() : changes[i][3];
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 20, int_notes, 'validation');
                                break;
                            case 21: // S-05768-Rename Unit Price to Net Price and Add Unit Price- Unit Price (new unit price)
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 17, changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3], 'validation');
                                data['value'] = changes[i][3];
                                data['line_number'] = tableThis.getDataAtCell(parseInt(changes[i][0]), 1);
                                data['send'] = changes[i][3] && changes[i][3] != changes[i][2];
                                break;
                            case 22: // S-05768-Rename Unit Price to Net Price and Add Unit Price- Net Price renamed from Unit Price(Old Unit Price)
                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 17, changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3], 'validation');
                                data['value'] = changes[i][3];
                                data['line_number'] = tableThis.getDataAtCell(parseInt(changes[i][0]), 1);
                                data['send'] = changes[i][3] && changes[i][3] != changes[i][2];
                                break;
                            case 23: // Higher Level Item
                                if(changes[i][3]){
                                    var other_lines = tableThis.getDataAtCol(1);
                                    if(other_lines.indexOf(changes[i][3]) === -1){
                                        cellMeta['cellStatus'] = "!";
                                        cellMeta['comment']['value'] += '! - Item number not found.\n';
                                    }
                                }
                                break;
                            case 24: // Material Group 5
                                break;
                            case 25: // Purchase order Item number
                                break;
                            case 26: // Condition
                                var condition = changes[i][3] ? changes[i][3].toUpperCase().trim() : changes[i][3];
                                var line_number = tableThis.getDataAtCell(parseInt(changes[i][0]), 1);
                                var all_conds = tableThis.getDataAtCol(26);

// S-08410:Adjust Model and BoM Header Tab:- Added below if else block to see if config starts from line 10 or 100
                                if(is_line100){
                                    if(condition == "ZUST" && line_number !== "100"){       // for line 100
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - ZUST only allowed on line 100.\n';
                                    }
                                }else{
                                    if(condition == "ZUST" && line_number !== "10"){       //for line 10
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - ZUST only allowed on line 10.\n';
                                    }
                                }

                                if(condition == "ZPRU" || condition == "ZPR1"){
                                    $('[name="needs_zpru"]').val("True");
                                } else if(all_conds.indexOf("ZPRU") === -1 && all_conds.indexOf("ZPR1") === -1){
                                    $('[name="needs_zpru"]').val("False");
                                }

                                if(condition && !tableThis.getDataAtCell(parseInt(changes[i][0]), 27)){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Condition provided without Amount.\n';
                                }

                                if(changes[i][2] !== changes[i][3]){
                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 27, tableThis.getDataAtCell(parseInt(changes[i][0]), 27), 'edit');
                                }

                                if(condition){
                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 26, condition, 'validation');
                                }
                                break;
                            case 27: // Amount
                                var amount = changes[i][3] === null ? null : changes[i][3].trim();

                                if(amount !== null) {
                                    amount = amount.replace(/\$|,/g, '');

                                    if (!/^(?:-)?\d+(?:\.\d+)?$|^$/.test(amount)) {
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Invalid Amount.\n';
                                    }

                                    if (amount && !tableThis.getDataAtCell(parseInt(changes[i][0]), 26)) {
                                        cellMeta['cellStatus'] = "X";
                                        cellMeta['comment']['value'] += 'X - Amount provided without Condition.\n';
                                    }

                                    if (changes[i][2] !== changes[i][3]) {
                                        tableThis.setDataAtRowProp(parseInt(changes[i][0]), 26, tableThis.getDataAtCell(parseInt(changes[i][0]), 26), 'edit');
                                    }

                                    tableThis.setDataAtRowProp(parseInt(changes[i][0]), 27, amount, 'validation');
                                }
                                break;
                            case 28: // Traceability req.
                                var traceability = changes[i][3] === null ? null : changes[i][3].toUpperCase().trim();

                                if(!/^Y$|^N$|^$/.test(traceability)){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid Traceability Req.\n';
                                }

                                tableThis.setDataAtRowProp(parseInt(changes[i][0]), 28, traceability, 'validation');
                                break;
                            case 29: // Customer Asset
                                if(changes[i][3] !== null && !/^Y$|^N$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid Customer Asset.\n';
                                }
                                break;
                            case 30: // Customer Asset Tagging Req
                                /*if(changes[i][3] !== null && !/^Y$|^N$|^$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Invalid Customer Asset Tagging Req.\n';
                                } else if(changes[i][3] == 'Y' && tableThis.getDataAtCell(parseInt(changes[i][0]), 25) != 'Y'){
                                    cellMeta['cellStatus'] = "X";
                                    cellMeta['comment']['value'] += 'X - Cannot require asset tagging if part is not a customer asset.\n';
                                }*/
                                break;
                            case 31: // Customer Number
                                break;
                            case 32: // Second Customer Number
                                break;
                            case 33: // Vendor Article number
                                if(/^\.+.+|.+\/$/.test(changes[i][3])){
                                    cellMeta['cellStatus'] = "!";
                                    cellMeta['comment']['value'] += '! - Vendor Article Number should not start with "." or end with "/".\n';
                                }
                                break;
                            case 32: // Comments
                                break;
                            case 34: // Additional Refs
                                break;
                        }

                        // Make sure each comment only exists once
                        var comments = cellMeta['comment']['value'].split("\n");
                        var uniqueComments = [];
                        for(var idx in comments){
                            if(uniqueComments.indexOf(comments[idx]) == -1){
                                uniqueComments.push(comments[idx]);
                            }
                        }
                        cellMeta['comment']['value'] = uniqueComments.join("\n");


                        tableThis.setCellMetaObject(parseInt(changes[i][0]), parseInt(changes[i][1]), cellMeta);
                        UpdateValidation(parseInt(changes[i][0]), tableThis);

                        // If data needs to be sent and validated, send it now
                        if(data['send']){
                            (function (inputData) {
                                var settings = {
                                    url: ajax_validate_url,
                                    type: "POST",
                                    data: inputData,
                                    headers: {
                                        'X-CSRFToken': getcookie('csrftoken'),
                                        'Content-type': 'application/x-www-form-urlencoded',
                                        'Accept': 'application/json'
                                    }
                                };

                                validationQueue.add(settings, tableThis);
                            })(data);
                        }
                    }
                }
            }
        },
        beforeValidate: function(value, row, prop, source){
       // S-05768-Rename Unit Price to Net Price and Add Unit Price- Unit price renamed to Net Price
            if(['Net Price','Amount'].indexOf(this.getColHeader(prop)) != -1){
                value = value === null ? value : value.toString().replace(/$/g,'').replace(/,/g,'').replace(/\s/g,'');
                if (!isNaN(parseFloat(value))) {
                    value = String(parseFloat(value).toFixed(2));
                }
            }
            if (['Product Number'].indexOf(this.getColHeader(prop)) != -1) {
                value = value === null ? value : value.replace(/\s/g,'');
            }

            return value;
        },
        beforeChange: function(changes, source){
            for(var i = 0; i < changes.length; i++) {
           // S-05768-Rename Unit Price to Net Price and Add Unit Price- Unit price renamed to Net Price
                if (['Net Price', 'Amount'].indexOf(this.getColHeader(changes[i][1])) != -1) {
                    changes[i][3] = changes[i][3]== null ? changes[i][3] : changes[i][3].replace(/$/g,'').replace(/,/g,'').replace(/\s/g,'');
                    if (!isNaN(parseFloat(changes[i][3]))) {
                        changes[i][3] = String(parseFloat(changes[i][3]).toFixed(2));
                    }
                } else if (['Product Number'].indexOf(this.getColHeader(changes[i][1])) != -1) {
                    changes[i][3] = changes[i][3].replace(/\s/g,'');
                }
            }
        },
        afterCreateRow: function(index, amount){
            validationStorage.addRow(index, amount);
        },
        afterRemoveRow: function(index, amount){
            validationStorage.removeRow(index, amount);
        },
        beforeInitWalkontable: function(walkontableConfig){
            walkontableConfig['defaultColumnWidth'] = 0;
        }
    });
    hot.getPlugin('comments').editor.editorStyle.zIndex = "1050";

    if(firstLoad && !(frame_readonly || active_lock)) {
        for (var row = 0; row < errors.length; row++) {
            for (var col=0; col < errors[row].length; col++){
                if (hot.getCellMeta(row, col)['comment'] != undefined) {
                    hot.getCellMeta(row, col)['comment']['value'] = errors[row][col]['value'];
                } else {
                    hot.setCellMeta(row, col, 'comment', errors[row][col]);
                }
                if(col === 0) {
                    hot.setCellMeta(row, col, 'cellStatus', hot.getDataAtCell(row, col));
                } else {
                    hot.setCellMeta(row, col, 'cellStatus', hot.getCellMeta(row, col)['comment']['value'][0]);
                }
            }
        }

        UpdateValidation();

        valid = true;
        clean_form = JSON.parse(JSON.stringify(hot.getSourceData()));
        for(var i = 0; i < clean_form.length; i++){
            if(typeof clean_form[i] == 'object'){
                delete clean_form[i][0];
            }
        }
        $('[name="data_form"]').remove();
        clean_sub = $('#configform').serialize();
    }

    hot.render();
    hot.validateCells();
}

function estimateLineNumbers(changes, current_line_numbers) {

    var usedNumbers = current_line_numbers.filter(function(val){return val !== null;});

    for (var i=0; i < changes.length; i++){
        // If this change is for a part number and the corresponding line does not already have a line number
        // insert the part into the array at the corresponding index.  This will help determine the estimated order of new line numbers
        if (changes[i][1] == 2 && ['', null].indexOf(current_line_numbers[changes[i][0]]) != -1) {
            current_line_numbers[changes[i][0]] = changes[i][3];
        }
    }

    // Now step through each element in current_line_numbers.  if the element is already a line number (based on regexp matching)
    // update the last line number trackers, otherwise use the last line number trackers to create a new line number, assign it,
    // then update last trackers

//  S-08410:Adjust Model and BoM Header Tab:- Added below to check if config's parent line number should start from line 100 or not
    if(is_line100){
        var parent = 100, child = 1, grand = 1;
    }else{
         var parent = 10, child = 1, grand = 1;
    }
    for (i = 0; i < current_line_numbers.length; i++){
        if (current_line_numbers[i] == null){
            continue;
        }

        if (/^\d+(?:\.\d+){0,2}$/.test(current_line_numbers[i])){ // This is a line number
            var matchobj = current_line_numbers[i].match(/^(\d+)(?:\.(\d+))?(?:\.(\d+))?$/);
            parent = Math.max(matchobj[1] == undefined ? 0 : matchobj[1], parent);
            child = matchobj[2] == undefined ? 1 : parseInt(matchobj[2]);
            grand = matchobj[3] == undefined ? 1 : parseInt(matchobj[3]);
            usedNumbers.push(current_line_numbers[i]);
        } else { // This is not a line number and needs to have one assigned
            var decimalCount = (current_line_numbers[i].match(/\./g)||[]).length;
            var firstDot = current_line_numbers[i].slice(0,1);      //Added for First Dot
            var SecondDot = current_line_numbers[i].slice(0,2);     //Added for Second Dot
            var prefix;

            if (SecondDot == ".." ){            // grandchild
                prefix = parent.toString() + "." + child.toString();
                while (usedNumbers.indexOf(prefix + "." + grand.toString()) != -1 ) {
                    grand += 1;
                }
                current_line_numbers[i] = prefix + "." + grand.toString();
                usedNumbers.push(prefix);
                usedNumbers.push(current_line_numbers[i]);
               }else if (firstDot == "."){      // child
                prefix = parent.toString();
                while (usedNumbers.indexOf(prefix + "." + child.toString()) != -1 ) {
                    child += 1;
                }
                current_line_numbers[i] = prefix + "." + child.toString();
                usedNumbers.push(prefix);
                usedNumbers.push(current_line_numbers[i]);
            } else { // parent

//     S-08410:Adjust Model and BoM Header Tab:- Added below field to check if config starts from line 10 or 100; series for 100 is made 100,200,300 etc.
                 if(is_line100){
                    while (usedNumbers.indexOf(parent.toString()) != -1 ) {
                        if (parent % 100 != 0){
                            parent = Math.floor(parent/100) * 100;
                        } else {
                            parent += 100;
                        }
                    }
                 }else{
                     while (usedNumbers.indexOf(parent.toString()) != -1 ) {
                        if (parent % 10 != 0){
                            parent = Math.floor(parent/10) * 10;
                        } else {
                            parent += 10;
                        }
                    }
                 }
                current_line_numbers[i] = parent.toString();
                usedNumbers.push(parent.toString());
            }
        }
    }

    return current_line_numbers;
}

function UpdateValidation(row, table){
    table = table === undefined ? hot : table;
    var endstr = '?validation=true';
    var end = window.location.href.endsWith(endstr);
    if(end || is_picklist){    // added || is_picklist for D-02849
        if (row === undefined){
            // Update page status based on Status column
            if(!validationStorage.validating()){
                var sTableStatus = 'GOOD';
                var iTotalRows = table.countRows() - table.countEmptyRows(true);

                for(var currentRow = 0; currentRow < iTotalRows; currentRow++){
                    switch(table.getCellMeta(parseInt(currentRow), 0)['cellStatus']){
                        case 'X':
                            if(sTableStatus == 'GOOD' || sTableStatus == 'WARNING'){
                                sTableStatus = 'ERROR';
                            }
                            break;
                        case '?':
                            sTableStatus = 'FAILURE';
                            break;
                        case '!':
                            if(sTableStatus == 'GOOD'){
                                sTableStatus = 'WARNING';
                            }
                            break;
                        case 'INW':
                            sTableStatus = 'VALIDATING';
                            break;
                        case 'OK':
                        default:
                            break;
                    }
                }

                // Update Total net value and ZPRU total based on table data
                var fZpruTotal = 0.0;
                var fCurrentTotal;
                if($('#id_override_net_value').val()){
                    fCurrentTotal = parseFloat($('#id_override_net_value').val());
                } else if ($('#id_net_value').val()){
                    fCurrentTotal = parseFloat($('#id_net_value').val());
                } else {
                    fCurrentTotal = 0.0;
                }

                for(var i = 0; i < iTotalRows; i++){
                    if(!isNaN(table.getDataAtCell(parseInt(i), 27))){
                        if(table.getDataAtCell(parseInt(i), 26) == 'ZUST') {
                            fCurrentTotal += parseFloat(table.getDataAtCell(parseInt(i), 27));
                        } else if(table.getDataAtCell(parseInt(i), 26) == 'ZPR1'){
                            fZpruTotal += parseFloat(table.getDataAtCell(parseInt(i), 27));
                        }
                    }
                }

                if(fCurrentTotal != undefined) {
                    $('#id_total_value').val(fCurrentTotal.toFixed(2).toString());
                 }
                if(fZpruTotal != undefined) {
                    $('#id_zpru_total').val(fZpruTotal.toFixed(2).toString());
                }

                // Update page form and status
                if( $('[name="needs_zpru"]').val().toLowerCase() == 'true' && $('[name="zpru_total"]').val() != $('[name="total_value"]').val()){
                    $('#id_total_value').css('border', '3px solid red');
                    $('#id_zpru_total').css('border', '3px solid red');
                    sTableStatus = 'ERROR';
                } else {
                    $('#id_total_value').removeAttr('style');
                    $('#id_zpru_total').removeAttr('style');
                }

                // Disable save if errors are present
                if(sTableStatus === 'ERROR'){
                    $('#prevForm').attr('disabled', 'disabled').css('color','gray');
                    $("#saveexitForm").attr('disabled', 'disabled').css('color','gray');
                    $("#saveForm").attr('disabled', 'disabled').css('color','gray');
                    $("#nextForm").attr('disabled', 'disabled').css('color','gray');
                }

                $('#status').html(sTableStatus);
                if(sTableStatus === 'ERROR'){
                    $('#status').css('color','#DD0000');
                } else if (sTableStatus === 'WARNING') {
                    $('#status').css('color','#FF8800');
                } else if (sTableStatus === 'VALIDATING') {
                    $('#status').css('color','#AAAAAA');
                } else if (sTableStatus === 'FAILURE') {
                    $('#status').css('color','#0055FF');
                } else {
                    $('#status').css('color','#00AA00');
                }

                validating = false;

                if(firstLoad){
                    valid = true;
                    clean_form = JSON.parse(JSON.stringify(table.getSourceData()));
                    for(var i = 0; i < clean_form.length; i++){
                        if(typeof clean_form[i] == 'object'){
                            delete clean_form[i][0];
                        }
                    }
                    $('[name="data_form"]').remove();
                    clean_sub = $('#configform').serialize();
                    firstLoad = false;
                }
            } else {
                $('#status').html('VALIDATING');
                $('#status').css('color','#AAAAAA');
                validating = true;

            }
        } else {
            // Update Status column based on cellStatus in given row
            if(!validationStorage.validating(parseInt(row))){
                var sFinalStatus = 'OK';

                for(var col = 1; col < table.countCols(); col++){
                    if(hidden_cols.indexOf(col) != -1){
                        continue;
                    }

                    switch(table.getCellMeta(parseInt(row), col)['cellStatus']){
                        case 'X':
                            if(sFinalStatus == 'OK' || sFinalStatus == '!'){
                                sFinalStatus = 'X';
                            }
                            break;
                        case '?':
                            sFinalStatus = '?';
                            break;
                        case '!':
                            if(sFinalStatus == 'OK'){
                                sFinalStatus = '!';
                            }
                            break;
                        case 'OK':
                        default:
                            break;
                    }
                }

                table.setDataAtCell(parseInt(row), 0, sFinalStatus);
                table.setCellMeta(parseInt(row), 0, 'cellStatus', sFinalStatus);
                UpdateValidation(undefined, table);
            }
        }
    }else{
             $("#saveexitForm").attr('disabled', 'disabled').css('color','gray');
             $("#saveForm").attr('disabled', 'disabled').css('color','gray');
    }
}

function load_table() {
    readonly_columns = [];
    hidden_cols = [];
    determineColumns(readonly_columns, hidden_cols);
    hot.render();
}

function data_submit(eventObj) {
    $('[name="data_form"]').remove();
    $('<input/>').attr('type', 'hidden').attr('name','data_form').attr('value',JSON.stringify(hot.getSourceData())).appendTo('#configform');
    form_save = true;
}