
(function(window,undefined){

  /***
   * One web page <---> one d3viz
   */
  var d3viz = function(wid, container, canvas) {
  
    this.id = wid;
    this.socket = undefined;
    this.map = undefined;
    this.version = "0.1";
    this.mapDict = {};
    this.dataDict = {};
    this.popupWins = {}; //messageID:window
    this.msgDict = {};
    
    this.canvas = canvas;
    this.container = container;
    
    this.RequestParam_callback = undefined;
    this.CreateWeights_callback = undefined;
    this.RunSpreg_callback = undefined;
    
    self = this;
  };
 
  d3viz.prototype.GetJSON = function(url, successHandler, errorHandler) {
    var xhr = new XMLHttpRequest();
    xhr.open('get', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
      var status = xhr.status;
      if (status == 200) {
        successHandler && successHandler(xhr.response);
      } else {
        errorHandler && errorHandler(status);
      }
    };
    xhr.send();
  };

  /**
   * Setup Brushing/Linking for base map
   */
  d3viz.prototype.SetupBrushLink = function() { 
    mapDict = this.mapDict;
    window.addEventListener('storage', function(e) {
      var hl_ids = JSON.parse(localStorage.getItem('HL_IDS')),
          hl_ext = JSON.parse(localStorage.getItem('HL_MAP'));
      for ( var uuid in hl_ids ) {
        if ( mapDict && uuid in mapDict ) {
          var map = mapDict[uuid];
          var ids = hl_ids[uuid];
          if ( hl_ext && uuid in hl_ext ) {
            map.highlightExt(ids, hl_ext[uuid]);
          } else if ( hl_ids && uuid in hl_ids ) {
            var context = undefined;
            var nolinking = true;
            map.highlight(hl_ids[uuid], context, nolinking);
          }
        }
      }
    }, false);
  };
    
   
  /**
   * Setup and function for PopUp window
   */
  d3viz.prototype.RandUrl = function(url) {
    var rnd = Math.random().toString(36).substring(7)
    if ( url.indexOf('?')  === -1 ) {
      return url + "?" + rnd;
    }
    return url + "&" + rnd;
  };
 
  d3viz.prototype.NewPopUp = function(url, msg) {
    if ( url.indexOf('?')  === -1 ) {
      url = url + "?msgid=" + msg.id;
    } else {
      url = url + "&msgid=" + msg.id;
    }
    var win = window.open(
      this.RandUrl(url),
      "_blank",
      "width=600, height=500, scrollbars=yes"
    );
    this.popupWins[msg.id] = win;
  };
 
   
  d3viz.prototype.GetJsonUrl = function(uuid) {
    var json_url = "./tmp/" + uuid + ".json";
    return json_url; 
  };
  
  /**
   * Show a base map
   * parameters: canvas -- $() jquery object
   * parameters: container -- $() jquery object
   */
  d3viz.prototype.ShowMap = function(uuid, callback) {
    var json_url = this.GetJsonUrl(uuid);
    this.canvas = $('<canvas id="' + uuid + '"></canvas>').appendTo(this.container);
    this.GetJSON( json_url, function(data) {
      self.map = new GeoVizMap(new JsonMap(data), self.canvas);
      self.mapDict[uuid] = self.map;
      self.dataDict[uuid] = data;
    });
    if (typeof callback === "function") {
      callback();
    }
  };
  
  /**
   * add layer in an existing map
   * parameters: canvas -- $() jquery object
   * parameters: container -- $() jquery object
   */
  d3viz.prototype.AddLayer = function(msg) {
    if ( "uuid" in msg && this.canvas && this.canvas.length > 0 ){
      var uuid = msg.uuid,
          json_path = this.RandUrl("./tmp/" + uuid + ".json");
      
      this.GetJSON( json_path, function(data) {
        self.map.addLayer(uuid, new JsonMap(data)); 
        //self.mapDict[uuid] = self.map;
        self.dataDict[uuid] = data;
      });
    }
  };
  
  /**
   * Create a new thematic map
   */
  d3viz.prototype.ShowThematicMap = function(uuid, colorTheme, callback) {
    var json_url = this.GetJsonUrl(uuid);
    this.canvas = $('<canvas id="' + uuid + '"></canvas>').appendTo(this.container);
    this.GetJSON( json_url, function(data) {
      self.map = new GeoVizMap(new JsonMap(data), self.canvas, {
        "color_theme" : colorTheme
      });
      self.mapDict[uuid] = self.map;
      self.dataDict[uuid] = data;
      if (typeof callback === "function") {
        callback();
      }
    });
  };
  
  d3viz.prototype.UpdateThematicMap = function(uuid, newColorTheme, callback) {
    var map = self.mapDict[uuid];
    map.updateColor(newColorTheme);
    if (typeof callback === "function") {
      callback();
    }
  };
  
  /**
   * Create a new Leaftlet map
   */
  d3viz.prototype.ShowLeafletMap = function(uuid, L, lmap, options, callback) {
    var json_url = this.GetJsonUrl(uuid);
    //already have canvas as foreground
    //this.canvas = $('<canvas id="' + uuid + '"></canvas>').appendTo(this.container);
    this.GetJSON( json_url, function(data) {
      self.map = new GeoVizMap(new LeafletMap(data, L, lmap), self.canvas, options);
      self.mapDict[uuid] = self.map;
      self.dataDict[uuid] = data;
      if (typeof callback === "function") {
        callback();
      }
    });
  };
 
  /**
   * Create a new Leaftlet map
   */
  d3viz.prototype.ShowScatterPlot = function(msg) {
    var w = window.open(
      this.RandUrl('scatterplot_loess.html'), // quantile, lisa,
      "_blank",
      "width=900, height=700, scrollbars=yes"
    );
    this.popupWins[msg.id] = w;
  };
  
  /**
   * Create a new Moran Scatter Plot
   */
  d3viz.prototype.ShowMoranScatterPlot = function(msg) {
    var w = window.open(
      this.RandUrl('moran_scatter.html'), // quantile, lisa,
      "_blank",
      "width=900, height=700, scrollbars=yes"
    );
    this.popupWins[msg.id] = w;
  };

  /**
   * Create a new Cartodb map
   */
  d3viz.prototype.ShowCartodbMap= function(msg) {
    var w = window.open(
      this.RandUrl('cartodb_map.html'), // quantile, lisa,
      "_blank",
      "width=900, height=700, scrollbars=yes"
    );
    this.popupWins[msg.id] = w;
  };
  
  /**
   * Close all PopUp windows
   */
  d3viz.prototype.CloseAllPopUps = function() {
    for (var i in this.popupWins ) {
      this.popupWins[i].close();
    }
  };
 
  /**
   * Get selected ids from map
   */
  d3viz.prototype.GetSelected = function(msg) {
    var uuid = msg["uuid"];
    var select_ids = "";
    if (localStorage.getItem('HL_IDS')) {
      var hl_ids = JSON.parse(localStorage.getItem('HL_IDS'));
      if ( uuid in hl_ids) {
        var ids = hl_ids[uuid];
        for (var i=0, n=ids.length; i<n; i++ ) {
          select_ids += ids[i] + ",";
        }
      }
    }
    var rsp = {"uuid":uuid,"ids":select_ids};
    return rsp;
  };
   
  d3viz.prototype.SelectOnMap = function(msg) {
    var hl_ids = JSON.parse(localStorage.getItem('HL_IDS')),
        hl_ext = JSON.parse(localStorage.getItem('HL_MAP'));
    if (!hl_ids) hl_ids = {};
    if (!hl_ext) hl_ext = {};
    var uuid = msg.uuid;
    if (uuid in this.mapDict ) {
      var map = this.mapDict[uuid];
      var ids = msg.data;
      
      if ( hl_ext && uuid in hl_ext ) {
        map.highlightExt(ids, hl_ext[uuid]);
      } else {
        map.highlight(ids);
      }
      hl_ids[uuid] = ids;
    }
    localStorage['HL_IDS'] = JSON.stringify(hl_ids);
  };
  
  d3viz.prototype.NewDataFromWeb = function(msg) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
    } else {
      setTimeout(function(){self.NewDataFromWeb(msg)}, 10);
    }
  };
  
  d3viz.prototype.NewChoroplethMap = function(msg) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
    } else {
      setTimeout(function(){self.NewChoroplethMap(msg)}, 10);
    }
  };
  
  d3viz.prototype.NewScatterPlot = function(msg) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
    } else {
      setTimeout(function(){self.NewMoranScatterPlot(msg)}, 10);
    }
  };
  
  d3viz.prototype.NewMoranScatterPlot = function(msg) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
    } else {
      setTimeout(function(){self.NewMoranScatterPlot(msg)}, 10);
    }
  };
  
  d3viz.prototype.NewLISAMap= function(msg) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
    } else {
      setTimeout(function(){self.NewLISAMap(msg)}, 10);
    }
  };
  
  d3viz.prototype.RunSpreg = function(msg, callback) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
      this.RunSpreg_callback = callback;
    } else {
      setTimeout(function(){self.RunSpreg(msg, callback)}, 10);
    }
  };
  
  d3viz.prototype.CreateWeights = function(msg, callback) {
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
      this.CreateWeights_callback = callback;
    } else {
      setTimeout(function(){self.CreateWeights(msg, callback)}, 10);
    }
  };
  
  d3viz.prototype.RequestParameters = function( winID, callback) {
    var msg = {'command':'request_params', 'wid' : winID};
    if (this.socket.readyState == 1) {
      this.socket.send(JSON.stringify(msg));
      this.RequestParam_callback = callback;
    } else {
      setTimeout(function(){self.RequestParameters( winID, callback)}, 10);
    }
  };
  /**
   * Setup WebSocket Server Communications
  PySal can send a command "add_layer:{uri:abc.shp}" to ws server.
  Ws serverthen notifies all app web pages.--- ? Let's make it simple:
  There is only one main web page that communicate with WS server.
  This main web page can popup many child/sub pages for different maps/plots, 
  and they will communicate with each other using LocalStorage.
  
  If the user send "add_layer" command again with different data. This main page
  should stack the new layer as multi-layer scenario.
  */
  d3viz.prototype.SetupWebSocket = function(server_addr) {
    if (! ("WebSocket" in window)) WebSocket = MozWebSocket; // firefox
    this.socket = new WebSocket("ws://127.0.0.1:9000");
    var socket = this.socket;
    socket.onopen = function(event) {
      //socket.send('{connected:'+ pageid + '}');
      var msg, command, winID, addMsg, rspMsg;
      socket.onmessage = function(e) {
        try {
          msg = JSON.parse(e.data);
          command = msg.command;  
          winID = msg.wid;
          
          if ( command == "request_params" && self.id == winID) {
            if (typeof self.RequestParam_callback === "function") {
              self.RequestParam_callback(msg.parameters);
            }
          } else if ( command == "rsp_create_w" && self.id == winID) {
            self.CreateWeights_callback(msg.content);
            
          } else if ( command == "rsp_spatial_regression" && self.id == winID) {
            self.RunSpreg_callback(msg);
            
          } else if ( command == "select" ) {
            self.SelectOnMap(msg); //
          } 
        } catch (err) {
          console.error("Parsing server msg error:", msg, err);            
        }
      };
    };
    /*
    socket.onopen = function(event) {
      //socket.send('{connected:'+ pageid + '}');
      var msg, command, addMsg, rspMsg;
      socket.onmessage = function(e) {
        try {
          msg = JSON.parse(e.data);
          command = msg.command;  
          if ( command == "close_all" ) {
            self.CloseAllPopUps(); //
          } else if ( command == "show_map" ) {
            self.ShowMap(msg); //
          } else if ( command == "add_layer" ) {
            self.AddLayer(msg); //
          } else if ( command == "remove_layer" ) {
            //
          } else if ( command == "select" ) {
            self.SelectOnMap(msg); //
          } else if ( command == "clear_select" ) {
            //
          } else if ( command == "get_select" ) {
            addMsg = self.GetSelected(msg); //
          } else if ( command == "thematic_map" ) {
            self.ShowThematicMap(msg); //
          //} else if ( command == "equal_interval_map" ){
          //} else if ( command == "fisher_jenks_map" ) {
          } else if ( command == "histogram" ){
            //
          } else if ( command == "moran_scatter_plot" ){
            self.ShowMoranScatterPlot(msg);  //
          } else if ( command == "scatter_plot" ){
            self.ShowScatterPlot(msg);  //
          } else if ( command == "scatter_plot_matrix" ){
            self.ShowScatterPlotMatrix(msg);  //
          } else if ( command == "cartodb_map" ){
            self.ShowCartodbMap(msg); //
          }
         
          rspMsg = {'command': msg.command, 'response': 'OK'};
          for (var key in addMsg) {
            if (addMsg.hasOwnProperty(key)) {
              rspMsg[key] = addMsg[key];
            }
          }

          socket.send( JSON.stringify(rspMsg) );
        } catch (err) {
          console.error("Parsing server msg error:", msg, err);            
        }
      };
    };
    */
  };
 
  // End and expose d3viz to 'window'
  window["d3viz"] = d3viz;
})(self);
