$('button[value="baseline_report"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){
    $(window).load(function(){
        form_resize();
        timer = setTimeout(getTableRows, 500);
    });
});

function form_resize(){
    var topbuttonheight = $('#action_buttons').height();
    var bottombuttonheight = $('#formbuttons').height();
    var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (topbuttonheight);// + bottombuttonheight + crumbheight + subformheight);

    $('#table-wrapper').css("height", tableheight);
    build_table();
}

function readonlyRenderer(instance, td, row, col, prop, value, cellProperties) {
    customRenderer(instance, td, row, col, prop, value, cellProperties);

    if (instance.getSourceDataAtCell(row, 1) == '10') {
        td.style.background = '#C4D79B';
    } else {
        td.style.background = '#DDDDDD';
    }
}

function customRenderer(instance, td, row, col, prop, value, cellProperties) {
    if (/<[a-zA-Z][\s\S/]*>/.test(value) === false) {
        Handsontable.renderers.TextRenderer.apply(this, arguments);
    } else {
        Handsontable.renderers.HtmlRenderer.apply(this, arguments);
    }
}

function calcRenderer (instance, td, row, col, prop, value, cellProperties) {
    value = parseInt(instance.getSourceDataAtCell(row, 5)) * parseFloat(instance.getSourceDataAtCell(row, 7));
    readonlyRenderer(instance, td, row, col, prop, value, cellProperties);
}

function build_table() {
    var headers = ['Baseline','Line #','Configuration','Model','Part Number','Qty','Description','Unit Price','Net Total','Customer NET Total'];
    var container = document.getElementById('datatable');
    hot = new Handsontable(container, {
        data: data,
        minRows: 1,
        minCols: 10,
        maxCols: 10,
        rowHeaders: false,
        colHeaders: headers,
        cells: function(row, col, prop){
            var cellProperties = {};

            if(col !== 7 || (this.instance.getSourceDataAtCell(row, 1) == '10')){
                cellProperties.readOnly = true;
                cellProperties.renderer = readonlyRenderer;
                if((this.instance.getSourceDataAtCell(row, 1) != '10' || this.instance.getSourceDataAtCell(row, 7) != '') && col === 8){
                    cellProperties.renderer = calcRenderer;
                }
            } else {
                cellProperties.readOnly = true;
                cellProperties.renderer = readonlyRenderer;
            }

            cellProperties.className = 'htCenter';

            return cellProperties;
        }

    });
}