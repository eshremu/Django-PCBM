function XHRQueue(hash) {
    this._storage = [];

    this.storageHash = hash;

    this._currentIndex = 0
    this._inWork = false;

    this.encodeParams = function(parameters) {
        var params = [];
        for (key in parameters) {
            if (parameters.hasOwnProperty(key)) {
                if (parameters[key] instanceof Array) {
                    for (var i=0; i < parameters[key].length; i++) {
                        params.push(encodeURIComponent(key + '[]') + "=" + encodeURIComponent(parameters[key][i] != null?parameters[key][i]:''));
                    }
                    params.push(encodeURIComponent(key + '[' + parameters[key].length + ']') + "=");
                } else if (parameters[key] instanceof Object) {
                    pass;
                } else {
                    params.push(encodeURIComponent(key) + "=" + encodeURIComponent(parameters[key] != null?parameters[key]:''));
                }
            }
        }

        return params.join('&');
    };

    this.parseParams = function(query_string) {
        var param = {};

        var pairs = query_string.split("&");
        pairs.forEach(function(pair, idx, pairs){
            var key_val = pair.split('=');
            var key = decodeURIComponent(key_val[0]);

            if(key.endsWith("[]")){
                if(param.hasOwnProperty(key.slice(0, -2))){
                    param[key.slice(0, -2)].push(decodeURIComponent(key_val[1]));
                } else {
                    param[key.slice(0, -2)] = [decodeURIComponent(key_val[1])];
                }
            } else {
                param[key] = decodeURIComponent(key_val[1]);
            }
        });

        return JSON.parse(JSON.stringify(param));
    };

    this.add = function(settings) {

        var storageObject = this;

        var xhr = new XMLHttpRequest();
        xhr.dataSet = this.encodeParams(settings['data']);
        xhr.isPost = settings['type'].toLowerCase() == 'post';
        xhr.location = settings['url'];
        xhr.type = settings['type'];
        xhr.headers = settings['headers'];

        xhr.onloadstart = function(){
            hot.setDataAtCell(settings['data'].row, 0, 'INW');
            UpdateValidation();
        };

        xhr.onload = function(){
            if (storageObject.storageHash){
                storageObject.storageHash.finish(settings['data'].row, settings['data'].col);
            }

            if (this.status == 200){
                var returneddata = JSON.parse(this.response);
                hot.setDataAtCell(returneddata.row, returneddata.col, returneddata.value, 'validation');
                if (hot.getCellMeta(returneddata.row, returneddata.col)['comment'] != undefined) {
                    hot.getCellMeta(returneddata.row, returneddata.col)['comment']['value'] = returneddata.error['value'];
                } else {
                    hot.setCellMeta(returneddata.row, returneddata.col, 'comment', returneddata.error);
                }
                hot.setCellMeta(returneddata.row, returneddata.col, 'cellStatus', returneddata.status);

                hot.render();

                for (var col in returneddata.propagate.line) {
                    if (returneddata.propagate.line.hasOwnProperty(col)) {
                        // Determine if a newer validation request has been entered into the storage hash
                        if(!(storageObject.storageHash.storage.hasOwnProperty(returneddata.row) && storageObject.storageHash.storage[returneddata.row].hasOwnProperty(col) && storageObject.storageHash.storage[returneddata.row][col].isInProcess)) {
                            if (returneddata.propagate.line[col].chain) {
                                hot.setDataAtRowProp(returneddata.row, parseInt(col), returneddata.propagate.line[col].value, 'edit');
                            } else {
                                hot.setDataAtRowProp(returneddata.row, parseInt(col), returneddata.propagate.line[col].value, 'validation');
                            }
                        }
                    }
                }

                for (var prop in returneddata.propagate) {
                    if (prop == 'line') {
                        continue;
                    }

                    if (returneddata.propagate.hasOwnProperty(prop)) {
                        $(`[name="${prop}"]`).val(returneddata.propagate[prop]);
                    }
                }
            } else {
                if (hot.getCellMeta(settings['data'].row, settings['data'].col)['comment'] != undefined) {
                    hot.getCellMeta(settings['data'].row, settings['data'].col)['comment']['value'] = '? - An error occurred while validating.\n';
                } else {
                    hot.setCellMeta(settings['data'].row, settings['data'].col, 'comment', {value: '? - An error occurred while validating.\n'});
                }
                
                hot.setCellMeta(settings['data'].row, settings['data'].col, 'cellStatus', '?');
            }

            storageObject.finish();
        };
        
        xhr.onerror = function(){
            if (storageObject.storageHash){
                storageObject.storageHash.finish(settings['data'].row, settings['data'].col);
            }

            if (hot.getCellMeta(settings['data'].row, settings['data'].col)['comment'] != undefined) {
                hot.getCellMeta(settings['data'].row, settings['data'].col)['comment']['value'] = '? - An error occurred while validating.\n';
            } else {
                hot.setCellMeta(settings['data'].row, settings['data'].col, 'comment', {value: '? - An error occurred while validating.\n'});
            }
            
            hot.setCellMeta(settings['data'].row, settings['data'].col, 'cellStatus', '?');

            storageObject.finish();
        };
        xhr.ontimeout = function(){
            if (storageObject.storageHash){
                storageObject.storageHash.finish(settings['data'].row, settings['data'].col);
            }

            if (hot.getCellMeta(settings['data'].row, settings['data'].col)['comment'] != undefined) {
                hot.getCellMeta(settings['data'].row, settings['data'].col)['comment']['value'] = '? - Validation timed out.\n';
            } else {
                hot.setCellMeta(settings['data'].row, settings['data'].col, 'comment', {value: '? - Validation timed out.\n'});
            }
            
            hot.setCellMeta(settings['data'].row, settings['data'].col, 'cellStatus', '?');

            storageObject.finish();
        };
        xhr.onabort = function(){
            if (storageObject.storageHash){
                storageObject.storageHash.finish(settings['data'].row, settings['data'].col);
            }

            if (hot.getCellMeta(settings['data'].row, settings['data'].col)['comment'] != undefined) {
                hot.getCellMeta(settings['data'].row, settings['data'].col)['comment']['value'] = '? - Validation was aborted.\n';
            } else {
                hot.setCellMeta(settings['data'].row, settings['data'].col, 'comment', {value: '? - Validation was aborted.\n'});
            }
            
            hot.setCellMeta(settings['data'].row, settings['data'].col, 'cellStatus', '?');
        };

        xhr.onloadend = function(){
            UpdateValidation(settings['data'].row);
        };

        if (this.storageHash){
            this.storageHash.add(settings['data'].row, settings['data'].col, xhr, settings);
        }

        this.enqueue(xhr);
    };

    this.enqueue = function(xhr) {
        this._storage.push(xhr);

        this.start();
    };

    this.start = function() {
        if (!this._inWork){
            var type = this._storage[this._currentIndex].type;
            var location = this._storage[this._currentIndex].location;
            var headers = this._storage[this._currentIndex].headers;

            this._storage[this._currentIndex].open(type, location, true);
            for (header in headers){
                this._storage[this._currentIndex].setRequestHeader(header, headers[header]);
            }

            if(this._storage[this._currentIndex].isPost){
                this._storage[this._currentIndex].send(this._storage[this._currentIndex].dataSet)
            } else {
                this._storage[this._currentIndex].send();
            }
            this._inWork = true;
        }
    };

    this.stop = function() {
        this._storage[this._currentIndex].abort();
        this._inWork = false;
    };

    this.finish = function() {
        this._inWork = false;
        delete this._storage[this._currentIndex];
        this._currentIndex++;

        if (this._currentIndex < this._storage.length){
            this.start();
        }
    };
}