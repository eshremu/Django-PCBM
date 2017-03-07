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

        for(key of keys){
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

        for(key of keys){
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

    if (!valid && !form_save){
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
});

function submit(){
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
        if (attr_write_auth && configuration_status == 'In Process')
        {
            readonly.push(14, 15, 16);
        } else if (attr_write_auth) {
            readonly.push(11, 12, 14, 15, 16, 17);
        } else {
            readonly.push(11, 12, 13, 14, 15, 16, 17);
        }

        // readonly.push(15, 16, 17); # ON HOLD UNTIL PRIM INTERFACE OBTAINED

        $('#viewattr').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(11, 12, 13, 14, 15, 16, 17);
        $('#viewattr').removeAttr('style');
    }

    if(PriceVis === true && price_read_auth) {
        readonly.push(18);
        if (!price_write_auth) {
            readonly.push(19, 20, 21, 22, 23);
        } else if (price_write_auth && configuration_status == 'In Process/Pending') {
            readonly.push(19, 20, 21);
        }

        $('#viewprice').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(18, 19, 20, 21, 22, 23);
        $('#viewprice').removeAttr('style');
    }

    if(CustVis === true && cust_read_auth) {
        //readonly.push(24); # ON HOLD UNTIL PRIM INTERFACE OBTAINED
        readonly.push(25, 26, 27, 28);
        if (!cust_write_auth || (cust_write_auth && configuration_status != 'In Process')) {
            readonly.push(24);
        }

        $('#viewcust').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(24, 25, 26, 27, 28);
        $('#viewcust').removeAttr('style');
    }

    if(BaselineVis === true && baseline_read_auth){
        if (!baseline_write_auth) {
            readonly.push(29, 30, 31);
        } else if (baseline_write_auth && configuration_status != 'In Process' && next_approval == 'csr') {
            readonly.push(29, 30);
        } else if (baseline_write_auth && configuration_status != 'In Process' && next_approval == 'blm') {
            readonly.push(29, 31);
        }
        $('#viewbase').css('background-color', '#FFFF4D');
    } else {
        hidden_cols.push(29, 30, 31);
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
    if (row === 0 && col === 18 && typeof(value) == 'string' && value.charAt(0)==='!' && PriceVis){
        value = value.slice(1);
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
    var colWidths = [50,50,150,342,72,50,74,50,50,62,264,81,103,50,68,63,117,65,74,
            119,116,162,105,62,160,118,246,124,176,151,250,250]
    hot = new Handsontable(container, {
        data: data,
        minRows: 1,
        minCols: 32,
        maxCols: 32,
        minSpareRows: overall_write_auth && !frame_readonly ? 5 : 0,
        rowHeaders: false,
        colHeaders: [
            'Status', 'Line #', 'Product Number<br><span class="smallItalics">'+config_id+"</span>", "Product Description", 'Order Qty',
            'UoM', 'Context ID','Plant', 'SLOC', 'Item Cat', 'P-Code - Fire Code, Desc',
            'HW/SW Ind', 'Prod Pkg Type', 'SPUD', 'RE-Code', 'MU-Flag', "X-Plant Mat'l Stat", 'Int Notes',
            'Unit Price', "Higher Level Item", 'Material Group 5', 'Purchase Order Item No', 'Condition Type', 'Amount',
            'Traceability Req. (Serialization)', 'Customer Asset', 'Customer Asset Tagging Requirement', 'Customer Number', 'Second Customer Number',
            'Vendor Article Number', 'Comments', 'Additional Reference (if required)',
        ],
        fixedColumnsLeft: 3,
        manualColumnFreeze: true,
        currentRowClassName: 'currentRow',
        columns: [
            {data: 0}, {data: 1}, {data: 2}, {data: 3}, {data: 4}, {data: 5},
            {data: 6}, {data: 7}, {data: 8}, {data: 9}, {data: 10}, {data: 11},
            {data: 12}, {data: 13}, {data: 14}, {data: 15}, {data: 16}, {data: 17},
            {data: 18}, {data: 19}, {data: 20}, {data: 21}, {data: 22}, {data: 23},
            {data: 24}, {data: 25}, {data: 26}, {data: 27}, {data: 28}, {data: 29},
            {data: 30}, {data: 31},
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
            var cellProperties = {};

            if(hidden_cols.indexOf(parseInt(col)) != -1){
                cellProperties.width = 0;
            } else {
                cellProperties.width = colWidths[parseInt(col)];
            }

            if(active_lock || (!is_picklist  && (row === 0 && [1,2,4].indexOf(col)!== -1)) || readonly_columns.indexOf(col) !== -1){
                cellProperties.readOnly = true;
                if (['Unit Price', 'Amount'].indexOf(this.instance.getColHeader(col)) != -1){//(col == 17 || col == 22) && PriceVis){
                    cellProperties.renderer = moneyRenderer;
                } else {
                    cellProperties.renderer = readonlyRenderer;
                }
            } else {
                if (['Unit Price', 'Amount'].indexOf(this.instance.getColHeader(col)) != -1){
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

            cellProperties.className = 'htCenter';
            if (['Line #', 'Product Description', 'SPUD', 'Int Notes','P-Code - Fire Code, Desc', 'Vendor Article Number','Comments','Additional Reference (if required)'].indexOf(this.instance.getColHeader(col)) != -1){ //
                cellProperties.className = 'htLeft';
            } else if (['Unit Price', 'Amount'].indexOf(this.instance.getColHeader(col)) != -1){
                cellProperties.className = 'htRight';
            } else if (this.instance.getColHeader(col).startsWith('Product Number')) {
                cellProperties.className = 'htLeft';
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
            if (!isValid){
                $('#prevForm').attr('disabled', 'disabled').css('color','gray');
                $("#saveexitForm").attr('disabled', 'disabled').css('color','gray');
                $("#saveForm").attr('disabled', 'disabled').css('color','gray');
                $("#nextForm").attr('disabled', 'disabled').css('color','gray');
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

                if (source != 'validation') {
                    if (source == 'loadData' && firstLoad) {
                        return;
                        var sourceData = this.getSourceData();
                        changes = [];

                        var iTotalRows = this.countRows() - this.countEmptyRows(true);
                        for (var i = 0; i < iTotalRows; i++) {
                            for (var col in sourceData[i]) {
                                if ([2,7,8,11,18,19,22].indexOf(parseInt(col)) != -1 && sourceData[i].hasOwnProperty(col)) {
                                    changes.push([i, parseInt(col), null, sourceData[i][col]]);
                                }
                            }
                        }
                    }

                    var lineEstimates;
                    if (source == 'paste') {
                        lineEstimates = estimateLineNumbers(changes, this.getDataAtCol(1));
                    }

                    for (var i = 0; i < changes.length; i++) {
                        if (source != 'initLoad' && (changes[i][1] == 0 || (changes[i][2] == changes[i][3] && !(changes[i][1] == 4 || changes[i][1] == 26 || changes[i][1] == 22 || changes[i][1] == 23)))) {
                            continue;
                        }

                        var dataGenerator = function () {
                            return {
                                row: parseInt(changes[i][0]),
                                col: parseInt(changes[i][1]),
                                value: changes[i][3],
                                allowChain: source != 'initLoad'
                            }
                        };

                        var data = dataGenerator();

                        switch (parseInt(changes[i][1])) {
                            case 1:
                                data['other_lines'] = this.getDataAtCol(1);
                                data['other_lines'].splice(-1 * this.countEmptyRows(true));
                                data['other_lines'].splice(changes[i][0], 1);
                                data['part_number'] = this.getDataAtCell(changes[i][0], 2) ? this.getDataAtCell(changes[i][0], 2).replace(/^[\s]+|[\s]+$/g, '') : this.getDataAtCell(changes[i][0], 2);
                                break;
                            case 2:
                                data['quantity'] = this.getDataAtCell(changes[i][0], 4);
                                data['line_number'] = lineEstimates == undefined ? this.getDataAtCell(changes[i][0], 1) : lineEstimates[changes[i][0]];
                                data['row_index'] = changes[i][0];
                                data['other_lines'] = this.getDataAtCol(1);
                                data['other_lines'].splice(-1 * this.countEmptyRows(true));
                                data['context_id'] = this.getDataAtCell(changes[i][0], 6);
                                data['writeable'] = cust_write_auth;
                                break;
                            case 6:
                                data['part_number'] = this.getDataAtCell(changes[i][0], 2);
                                break;
                            case 7:
                                data['sloc'] = this.getDataAtCell(changes[i][0], 8);
                                data['part_number'] = this.getDataAtCell(changes[i][0], 2);
                                break;
                            case 8:
                                data['plant'] = this.getDataAtCell(changes[i][0], 7);
                                data['part_number'] = this.getDataAtCell(changes[i][0], 2);
                                break;
                            case 11:
                                data['pcode'] = this.getDataAtCell(changes[i][0], 10);
                                break;
                            case 14:
                                data['int_notes'] = this.getDataAtCell(changes[i][0], 17);
                                break;
                            case 18:
                                data['line_number'] = this.getDataAtCell(changes[i][0], 1);
                                break;
                            case 19:
                                data['other_lines'] = this.getDataAtCol(1);
                                data['other_lines'].splice(-1 * this.countEmptyRows(true));
                                break;
                            case 22:
                                data['other_conds'] = this.getDataAtCol(22);
                                data['other_conds'].splice(-1 * this.countEmptyRows(true));
                                data['other_conds'].splice(changes[i][0], 1);
                                data['line_number'] = this.getDataAtCell(changes[i][0], 1);
                                data['amount'] = this.getDataAtCell(changes[i][0], 23);
                                data['previous_value'] = changes[i][2]==undefined ? null : changes[i][2];
                                break;
                            case 23:
                                data['condition'] = this.getDataAtCell(changes[i][0], 22);
                                data['previous_value'] = changes[i][2]==undefined ? null : changes[i][2];
                                break;
                            case 26:
                                data['asset'] = this.getDataAtCell(changes[i][0], 25);
                            case 25:
                                data['tagging'] = this.getDataAtCell(changes[i][0], 26);
                            case 27:
                            case 28:
                                data['part_number'] = this.getDataAtCell(changes[i][0], 2) ? this.getDataAtCell(changes[i][0], 2).replace(/^[.\s]+|[.\s]+$/g, '') : this.getDataAtCell(changes[i][0], 2);
                                data['writeable'] = cust_write_auth;
                                break;
                        }

                        // (function (inputData) {
                        //     $.ajax({
                        //         url: ajax_validate_url,
                        //         type: "POST",
                        //         data: inputData,
                        //         headers: {
                        //             'X-CSRFToken': getcookie('csrftoken')
                        //         },
                        //         beforeSend: function (xhr, settings) {
                        //             validationStorage.add(inputData.row, inputData.col, xhr, settings);
                        //             tableThis.setDataAtCell(inputData.row, 0, 'INW');
                        //             UpdateValidation();
                        //         },
                        //         success: function (returneddata) {
                        //             validationStorage.finish(returneddata.row, returneddata.col);
                        //             tableThis.setDataAtCell(returneddata.row, returneddata.col, returneddata.value, 'validation');
                        //             if (tableThis.getCellMeta(returneddata.row, returneddata.col)['comment'] != undefined) {
                        //                 tableThis.getCellMeta(returneddata.row, returneddata.col)['comment']['value'] = returneddata.error['value'];
                        //             } else {
                        //                 tableThis.setCellMeta(returneddata.row, returneddata.col, 'comment', returneddata.error);
                        //             }
                        //             tableThis.setCellMeta(returneddata.row, returneddata.col, 'cellStatus', returneddata.status);
                        //
                        //             tableThis.render();
                        //
                        //             for (var col in returneddata.propagate.line) {
                        //                 if (returneddata.propagate.line.hasOwnProperty(col)) {
                        //                     if (returneddata.propagate.line[col].chain) {
                        //                         tableThis.setDataAtRowProp(returneddata.row, parseInt(col), returneddata.propagate.line[col].value, 'edit');
                        //                     } else {
                        //                         tableThis.setDataAtRowProp(returneddata.row, parseInt(col), returneddata.propagate.line[col].value, 'validation');
                        //                     }
                        //                 }
                        //             }
                        //
                        //             for (var prop in returneddata.propagate) {
                        //                 if (prop == 'line') {
                        //                     continue;
                        //                 }
                        //
                        //                 if (returneddata.propagate.hasOwnProperty(prop)) {
                        //                     $(`[name="${prop}"]`).val(returneddata.propagate[prop]);
                        //                 }
                        //             }
                        //         },
                        //         error: function (xhr, status, error) {
                        //             if (tableThis.getCellMeta(inputData.row, inputData.col)['comment'] != undefined) {
                        //                 tableThis.getCellMeta(inputData.row, inputData.col)['comment']['value'] = '? - An error occurred while validating.\n';
                        //             } else {
                        //                 tableThis.setCellMeta(inputData.row, inputData.col, 'comment', {value: '? - An error occurred while validating.\n'});
                        //             }
                        //
                        //             tableThis.setCellMeta(inputData.row, inputData.col, 'cellStatus', '?');
                        //             // $('#statuses').html('Error(s) found. Save failed.');
                        //             // setTimeout(function(){$('#statuses').fadeOut('slow')}, 10000);
                        //         },
                        //         complete: function (xhr, status) {
                        //             validationStorage.finish(inputData.row, inputData.col);
                        //             UpdateValidation(inputData.row);
                        //         }
                        //     });
                        // })(data);
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

                            validationQueue.add(settings);
                        })(data);
                    }
                }
            }
        },
        beforeValidate: function(value, row, prop, source){
            if(['Unit Price','Amount'].indexOf(this.getColHeader(prop)) != -1){
                value = value.replace(/$/g,'').replace(/,/g,'').replace(/\s/g,'');
                if (!isNaN(parseFloat(value))) {
                    value = String(parseFloat(value).toFixed(2));
                }
            }
            if (['Product Number'].indexOf(this.getColHeader(prop)) != -1) {
                value = value.replace(/\s/g,'');
            }

            return value;
        },
        beforeChange: function(changes, source){
            for(var i = 0; i < changes.length; i++) {
                if (['Unit Price', 'Amount'].indexOf(this.getColHeader(changes[i][1])) != -1) {
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

        var iTotalRows = hot.countRows() - hot.countEmptyRows(true);
        for (var row = 0; row < errors.length; row++) {
            for (var col=0; col < errors[row].length; col++){
                if (hot.getCellMeta(row, col)['comment'] != undefined) {
                    hot.getCellMeta(row, col)['comment']['value'] = errors[row][col]['value'];
                } else {
                    hot.setCellMeta(row, col, 'comment', errors[row][col]);
                }
                hot.setCellMeta(row, col, 'cellStatus', hot.getDataAtCell(row, col));
            }
            // for (var col of [2,7,8,11,18,19,22]){
            //     hot.setDataAtCell(row, col, hot.getDataAtCell(row, col), 'initLoad');
            // }

            // for (var col in sourceData[i]) {
            //     if ([2,7,8,11,18,19,22].indexOf(parseInt(col)) != -1 && sourceData[i].hasOwnProperty(col)) {
            //         changes.push([i, parseInt(col), null, sourceData[i][col]]);
            //     }
            // }
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
}

function estimateLineNumbers(changes, current_line_numbers) {
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
    var parent = 0, child = 1, grand = 1;
    var usedNumbers = [];

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
            var prefix;
            if (decimalCount == 2) { // grandchild
                prefix = parent.toString() + "." + child.toString();
                while (usedNumbers.indexOf(prefix + "." + grand.toString()) != -1 ) {
                    grand += 1;
                }
                current_line_numbers[i] = prefix + "." + grand.toString();
                usedNumbers.push(prefix);
                usedNumbers.push(current_line_numbers[i]);
            } else if (decimalCount == 1) { // child
                prefix = parent.toString();
                while (usedNumbers.indexOf(prefix + "." + child.toString()) != -1 ) {
                    child += 1;
                }
                current_line_numbers[i] = prefix + "." + child.toString();
                usedNumbers.push(prefix);
                usedNumbers.push(current_line_numbers[i]);
            } else { // parent
                while (usedNumbers.indexOf(parent.toString()) != -1 ) {
                    if (parent % 10 != 0){
                        parent = Math.floor(parent/10) * 10;
                    } else {
                        parent += 10;
                    }
                }
                current_line_numbers[i] = parent.toString();
                usedNumbers.push(parent.toString());
            }
        }
    }

    return current_line_numbers;
}

function UpdateValidation(row){
    if (row === undefined){
        // Update page status based on Status column
        if(!validationStorage.validating()){
            var sTableStatus = 'GOOD';
            var iTotalRows = hot.countRows() - hot.countEmptyRows(true);

            for(var currentRow = 0; currentRow < iTotalRows; currentRow++){
                switch(hot.getCellMeta(parseInt(currentRow), 0)['cellStatus']){
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
                if(!isNaN(hot.getDataAtCell(parseInt(i), 23))){
                    if(hot.getDataAtCell(parseInt(i), 22) == 'ZUST') {
                        fCurrentTotal += parseFloat(hot.getDataAtCell(parseInt(i), 23));
                    } else if(hot.getDataAtCell(parseInt(i), 22) == 'ZPR1'){
                        fZpruTotal += parseFloat(hot.getDataAtCell(parseInt(i), 23));
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
                clean_form = JSON.parse(JSON.stringify(hot.getSourceData()));
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

            for(var col = 1; col < hot.countCols(); col++){
                if(hidden_cols.indexOf(col) != -1){
                    continue;
                }

                switch(hot.getCellMeta(parseInt(row), col)['cellStatus']){
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

            hot.setDataAtCell(parseInt(row), 0, sFinalStatus);
            hot.setCellMeta(parseInt(row), 0, 'cellStatus', sFinalStatus);
            UpdateValidation();
        }
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