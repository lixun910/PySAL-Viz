
(function(window,undefined){

  var d3viz = function(container) {
  
    this.map = undefined;
    this.version = "0.1";
    this.mapDict = {};
    this.dataDict = {};
    this.popupWins = {}; //messageID:window
    this.msgDict = {};
    
    this.canvas = undefined;
    this.container = container;
    
    this.ShowMap_callback = undefined;
    
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
        if ( uuid in mapDict ) {
          var map = mapDict[uuid];
          var ids = hl_ids[uuid];
          console.log("highlight");
          if ( uuid in hl_ext ) {
            map.highlightExt(ids, hl_ext[uuid]);
          } else if ( uuid in hl_ids ) {
            map.highlight(hl_ids[uuid]);
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
  
  /**
   * Show a base map
   * parameters: canvas -- $() jquery object
   * parameters: container -- $() jquery object
   */
  d3viz.prototype.ShowMap = function(msg) {
    if ( "uuid" in msg ){
      var canvas = this.canvas,
          container = this.container,
          uuid = msg.uuid,
          json_path = this.RandUrl("./tmp/" + uuid + ".json");
      if ( canvas && canvas.length > 0) {
        var old_uuid = canvas.attr('id');
        delete this.mapDict[old_uuid];
        delete this.dataDict[old_uuid];
        delete this.map;
        canvas.remove();
      }
      this.canvas = $('<canvas id="' + uuid + '"></canvas>').appendTo(container);
      this.GetJSON( json_path, function(data) {
        self.map = new GeoVizMap(new JsonMap(data), self.canvas);
        self.mapDict[uuid] = self.map;
        self.dataDict[uuid] = data;
      });
    }
    if (typeof this.ShowMap_callback === "function") {
      this.ShowMap_callback();
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
  d3viz.prototype.ShowThematicMap = function(msg) {
    if ("basemap" in msg) {
      // for basemap case e.g. leaflet map, the following will translate to 
      // leaflet_map(msg);
      d3viz[msg["basemap"]](msg);
    } else {
      var type = msg["type"],
          uuid = msg["uuid"];
      this.NewPopUp('map.html?type='+type+'&uuid='+uuid, msg);
    }
  };
  
  /**
   * Create a new Leaftlet map
   */
  d3viz.prototype.ShowLeafletMap = function(msg) {
    var type = msg["type"];
    var w = window.open(
      this.RandUrl('leaflet_map.html?type=' + type), // quantile, lisa,
      "_blank",
      "width=900, height=700, scrollbars=yes"
    );
    this.popupWins[msg.id] = w;
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
  
  /**
   * Setup WebSocket Server Communications
   */
   /*
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
    socket = new WebSocket("ws://127.0.0.1:9000");
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
  };
 
  // End and expose d3viz to 'window'
  window["d3viz"] = d3viz;
})(self);
