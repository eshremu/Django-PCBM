
$('button[value="price_report"]').css('outline','5px auto -webkit-focus-ring-color').css('background-color','#cccccc');
$(document).ready(function(){
    $(window).load(function(){
        form_resize();
    });
    
    $('#download').click(function(event){
        timer = setInterval(function(){
            if(document.cookie.split('fileMark=').length == 2 && document.cookie.split('fileMark=')[1].split(';')[0] == $('#cookie').val()) {
                clearInterval(timer);
                $('#myModal').modal('hide');
            }
        },1000);
    });
});

function form_resize(){
    var topbuttonheight = $('#action_buttons').outerHeight(true);
    var bottombuttonheight = $('#formbuttons').outerHeight(true);
    var subformheight = $("#headersubform").height() + parseInt($('#headersubform').css('margin-top')) + parseInt($('#headersubform').css('margin-bottom'));
    var crumbheight = $('#breadcrumbs').height() + parseInt($('#breadcrumbs').css('margin-top')) + parseInt($('#breadcrumbs').css('margin-bottom'));
    var bodyheight = $('#main-body').height();

    var tableheight = bodyheight - (topbuttonheight + bottombuttonheight + 5);//  + crumbheight + subformheight);

    $('#table-wrapper').css("height", tableheight);
    build_table();
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
    td.style.background = '#DDDDDD';
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
//# fix for S-05772 Add Valid From and Valid to columns on Pricing->Pricing Overview tab
    var headers = ['Part Number', 'Customer', 'Sold-To', 'SPUD', 'Technology', 'Latest Unit Price ($)','Valid From', 'Valid To'];
    for (var i = headers.length, j=1; i < max_length; i++, j++){
        var temp = new Date();

        headers.push(String(temp.getFullYear()-j) + ' Price ($)');
    }
    var container = document.getElementById('datatable');
    hot = new Handsontable(container, {
        data: data,
        minRows: 1,
        minCols: 6,
        maxCols: max_length,
        rowHeaders: false,
        colHeaders: headers,
        comments: true,
        cells: function(row, col, prop){
            var cellProperties = {};
//# fix for S-05772 Add Valid From and Valid to columns on Pricing->Pricing Overview tab(changed col>5 to col>7)
            if(col > 7){
                cellProperties.comment = comment_list[row][col - 8];
                cellProperties.renderer = moneyRenderer;
            } else {
                cellProperties.renderer = readonlyRenderer;
            }

            return cellProperties;
        }


    });
}


