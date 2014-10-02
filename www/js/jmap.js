// Author: xunli at asu.edu
(function(window,undefined){

  var GPoint = function( x, y ) {
    this.x = x;
    this.y = y;
  };
  
  GPoint.prototype = {
  };
  
  var GRect = function( x0, y0, x1, y1 ) {
    this.x0 = x0;
    this.y0 = y0;
    this.x1 = x1;
    this.y1 = y1;
  };
  
  GRect.prototype = {
    Contains: function( gpoint ) {
      return gpoint.x >= this.x0 && gpoint.x <= this.x1 && 
             gpoint.y >= this.y0 && gpoint.y <= this.y1;
    },
    GetW: function() {
      return this.x1 - this.x0;
    },
    GetH: function() {
      return this.y1 - this.y0;
    },
  };

  var BaseMap = function() {
    this.shpType = undefined;
    this.bbox = [];
    this.centroids = [];
    this.mapExtent = [];
    this.mapLeft = undefined;
    this.mapRight = undefined;
    this.mapBottom = undefined; 
    this.mapTop = undefined;
    this.mapWidth = undefined;
    this.mapHeight = undefined;
    this.screenObjects = [];
  };
  
  
  //////////////////////////////////////////////////////////////
  // ShpMap
  //////////////////////////////////////////////////////////////
  var ShpMap = function(shpFile) {
    this.shapefile = new Shapefile({shp:shpFile,jsRoot:'js'});
    this.shpType = this.shapefile.header.shapeType;
    this.mapLeft = this.shapefile.header.bounds.left;
    this.mapBottom = this.shapefile.header.bounds.bottom;
    this.mapRight = this.shapefile.header.bounds.right;
    this.mapTop = this.shapefile.header.bounds.top;
    this.mapHeight = this.mapTop - this.mapBottom;
    this.mapWidth = this.mapRight - this.mapLeft;
    this.extent = [this.mapLeft, this.mapRight, this.mapBottom, this.mapTop];
    this.bbox = [];
    this.centroids = [];
    this.screenCoords = [];
  };

  ShpMap.prototype.fitScreen = function(screenWidth, screenHeight) {
    // convert raw points to screen coordinators
    var whRatio = this.mapWidth / this.mapHeight,
        xyRatio = screenWidth / screenHeight,
        offsetX = 0.0,
        offsetY = 0.0; 
    if ( xyRatio >= whRatio ) {
      offsetX = (screenWidth - screenHeight * whRatio) / 2.0;
    } else if ( xyRatio < whRatio ) {
      offsetY = (screenHeight - screenWidth / whRatio) / 2.0;
    }
    screenWidth = screenWidth - offsetX * 2;
    screenHeight =  screenHeight - offsetY * 2;
    scaleX = screenWidth / this.mapWidth;
    scaleY = screenHeight / this.mapHeight;
    this.screenObjects = [];
    var parts, x, y, points;
    for ( var i=0, record; record = this.shapefile.records[i]; i++ ) {
      points = record.points;
      this.bbox.push( record.bounds);
      if ( record.shapeType == "Point" ) {
        for ( var p = 0; p < points.length; p++ ) {
          var point = points[p];
          x = point.x;
          y = point.y;
          this.centroids.push([x,y]);
          x = scaleX * (x - this.mapLeft) + offsetX;
          y = scaleY * (this.mapTop - y) + offsetY;
          this.screenObjects.push([x, y]);
        }
      } else {
        parts = record.parts;
        var screenPart = [];
        for ( var pt =0; pt < parts.length; pt++ ) {
          var partIndex = parts[pt],
              part = [],
              point;
          for ( var p = partIndex; p < (parts[pt+1] || points.length); p++) {
            point = points[p];
            x = point.x;
            y = point.y;
            x = scaleX * (x - this.mapLeft) + offsetX;
            y = scaleY * (this.mapTop - y) + offsetY;
            part.push([x, y]);
          }
          screenPart.push(part);
        }
        this.screenObjects.push(screenPart);
      }
    }
    this.offsetX = offsetX;
    this.offsetY = offsetY;
    this.scaleX = scaleX;
    this.scaleY = scaleY;
    this.scalePX = 1/scaleX;
    this.scalePY = 1/scaleY;
  };
  
  ShpMap.prototype.screenToMap = function(px, py) {
    var x = this.scalePX * (px - this.offsetX) + this.mapLeft;
    var y = this.mapTop - this.scalePY * (py - this.offsetY);
    return [x, y];
  };
  
  ShpMap.prototype.mapToScreen = function(x, y) {
    var px = this.scaleX * (x - this.mapLeft) + this.offsetX;
    var py = this.scaleY * (this.mapTop - y) + this.offsetY;
    return [px, py];
  };

  //////////////////////////////////////////////////////////////
  // JsonMap
  //////////////////////////////////////////////////////////////
  var JsonMap = function(geoJson, extent) {
    this.geojson = geoJson;
    this.shpType = this.geojson.features[0].geometry.type;
    this.bbox = [];
    this.centroids = [];
    this.extent = extent==undefined ? this.getExtent() : extent;
    this.mapLeft = this.extent[0];
    this.mapRight = this.extent[1];
    this.mapBottom = this.extent[2];
    this.mapTop = this.extent[3];
    this.mapWidth = this.extent[1] - this.extent[0];
    this.mapHeight = this.extent[3] - this.extent[2];
    this.screenObjects = [];
  };
  
  JsonMap.prototype.getExtent = function() {
    // Get extent from raw data
    var minX = Number.POSITIVE_INFINITY,
        maxX = Number.NEGATIVE_INFINITY,
        minY = Number.POSITIVE_INFINITY,
        maxY = Number.NEGATIVE_INFINITY;
    for ( var i=0, n=this.geojson.features.length; i<n; i++ ) {
      var bminX = Number.POSITIVE_INFINITY,
          bmaxX = Number.NEGATIVE_INFINITY,
          bminY = Number.POSITIVE_INFINITY,
          bmaxY = Number.NEGATIVE_INFINITY,
          coords = this.geojson.features[i].geometry.coordinates,
          x, y, j, k, part;
      if ( Array.isArray(coords[0][0])) {
        // multi-geometries
        for ( j=0, nParts=coords.length; j < nParts; j++ ) {
          part = coords[j];
          part =  Array.isArray(part[0][0])? part[0] : part;
          for ( k=0, nPoints=part.length; k < nPoints; k++ ) {
            x = part[k][0], y = part[k][1];
              if (x > maxX) {maxX = x;}
              if (x < minX) {minX = x;}
              if (y > maxY) {maxY = y;}
              if (y < minY) {minY = y;}
              if (x > bmaxX) {bmaxX = x;}
              if (x < bminX) {bminX = x;}
              if (y > bmaxY) {bmaxY = y;}
              if (y < bminY) {bminY = y;}
          }
        }
      } else {
        for ( k=0, nPoints=coords.length; k < nPoints; k++ ) {
          x = coords[k][0], y = coords[k][1];
            if (x > maxX) {maxX = x;}
            if (x < minX) {minX = x;}
            if (y > maxY) {maxY = y;}
            if (y < minY) {minY = y;}
            if (x > bmaxX) {bmaxX = x;}
            if (x < bminX) {bminX = x;}
            if (y > bmaxY) {bmaxY = y;}
            if (y < bminY) {bminY = y;}
        }
      }
      if ( this.shpType == "Polygon" || this.shpType == "MultiPolygon" ||
           this.shpType == "LineString" || this.shpType == "Line" ) {
        this.bbox.push([bminX, bmaxX, bminY, bmaxY]);
        this.centroids.push([bminX + ((bmaxX - bminX)/2.0), 
                             bminY + ((bmaxY - bminY)/2.0)]);
      } else {
        this.bbox.push([x, x, y, y]);
        this.centroids.push([x, y]);
      }
    }
    return [minX, maxX, minY, maxY];
  };
  
  JsonMap.prototype.fitScreen = function(screenWidth, screenHeight) {
    // convert raw points to screen coordinators
    var whRatio = this.mapWidth / this.mapHeight,
        xyRatio = screenWidth / screenHeight,
        offsetX = 0.0,
        offsetY = 0.0; 
    if ( xyRatio >= whRatio ) {
      offsetX = (screenWidth - screenHeight * whRatio) / 2.0;
    } else if ( xyRatio < whRatio ) {
      offsetY = (screenHeight - screenWidth / whRatio) / 2.0;
    }
    screenWidth = screenWidth - offsetX * 2;
    screenHeight =  screenHeight - offsetY * 2;
    scaleX = screenWidth / this.mapWidth;
    scaleY = screenHeight / this.mapHeight;
    
    this.offsetX = offsetX;
    this.offsetY = offsetY;
    this.scaleX = scaleX;
    this.scaleY = scaleY;
    this.scalePX = 1/scaleX;
    this.scalePY = 1/scaleY;
    
    this.screenObjects = [];
    this.latlon2Points(); 
  };
    
  JsonMap.prototype.latlon2Points = function() {
    this.screenObjects = [];
    var i, j, k, nParts, part, lastX, lastY, coords, pt,
        n = this.geojson.features.length;
    for ( i=0; i<n; i++ ) {
      var screenCoords = [];
      coords = this.geojson.features[i].geometry.coordinates;
      if ( Array.isArray(coords[0][0])) {
        // multi-geometries
        nParts=coords.length
        for ( j=0; j < nParts; j++ ) {
          var screenPart = [];
          part = coords[j];
          if ( Array.isArray(part[0][0])) {
            part = part[0];
          }
          nPoints = part.length;
          x = part[0][0];
          y = part[0][1];
          pt = this.mapToScreen(x, y);
          x = pt[0] | 0;
          y = pt[1] | 0;
          screenPart.push([x,y]);
          lastX = x;
          lastY = y; 
          for ( k=1; k < nPoints; k++ ) {
            x = part[k][0];
            y = part[k][1];
            pt = this.mapToScreen(x, y);
            x = pt[0] | 0;
            y = pt[1] | 0;
            if ( x!= lastX || y != lastY ){ 
              screenPart.push([x,y]);
              lastX = x;
              lastY = y;
            } 
          }
          screenCoords.push( screenPart );
        }
      } else {
        var x = coords[0][0], y = coords[0][1];
        pt = this.mapToScreen(x, y);
        x = pt[0] | 0;
        y = pt[1] | 0;
        screenCoords.push([x,y]);
        lastX = x;
        lastY = y; 
        for ( var k=0, nPoints=coords.length; k < nPoints; k++ ) {
          var x = coords[k][0], y = coords[k][1];
          pt = this.mapToScreen(x, y);
          x = pt[0] | 0;
          y = pt[1] | 0;
          if ( x!= lastX || y != lastY ) {
            screenCoords.push([x,y]);
            lastX = x;
            lastY = y;
          }
        }
      }
      this.screenObjects.push(screenCoords);
    }
  };
  
  JsonMap.prototype.screenToMap = function(px, py) {
    var x = this.scalePX * (px - this.offsetX) + this.mapLeft;
    var y = this.mapTop - this.scalePY * (py - this.offsetY);
    return [x, y];
  };
  
  JsonMap.prototype.mapToScreen = function(x, y) {
    var px = this.scaleX * (x - this.mapLeft) + this.offsetX;
    var py = this.scaleY * (this.mapTop - y) + this.offsetY;
    return [px, py];
  };
  
  //////////////////////////////////////////////////////////////
  // LeaftletMap inherited from JsonMap
  //////////////////////////////////////////////////////////////
  LeafletMap = function(geojson, LL, Lmap) {
    JsonMap.call(this, geojson);
   
    this.LL = LL; 
    this.Lmap = Lmap;
    this.Lmap.fitBounds([[this.mapBottom,this.mapLeft],[this.mapTop,this.mapRight]]);
    /* 
    this.zoom = this.Lmap.getZoom();
    this.bounds = this.Lmap.getBounds();
    
    this.mapLeft = this.bounds.getWest();
    this.mapRight = this.bounds.getEast();
    this.mapBottom = this.bounds.getNorth();
    this.mapTop = this.bounds.getSouth();
    this.mapWidth = this.mapRight - this.mapLeft;
    this.mapHeight = this.mapTop - this.mapBottom;
    */
  };
  
  LeafletMap.prototype = Object.create(JsonMap.prototype);
  
  LeafletMap.prototype.constructor = LeafletMap; // prepare for own constructor
  
  LeafletMap.prototype.fitScreen = function(screenWidth, screenHeight) {
    this.screenObjects = [];
    this.latlon2Points(); 
  };
  
  LeafletMap.prototype.screenToMap = function(px, py) {
    px = px - _self.offsetX;
    py = py - _self.offsetY;
    var pt = this.Lmap.layerPointToLatLng(new this.LL.point(px,py));
    return [pt.lng, pt.lat];
  };
  
  LeafletMap.prototype.mapToScreen = function(x, y) {
    var pt = this.Lmap.latLngToLayerPoint(new this.LL.LatLng(y,x));
    return [pt.x + _self.offsetX, pt.y + _self.offsetY];
  };
  //////////////////////////////////////////////////////////////
  // GeoVizMap
  //////////////////////////////////////////////////////////////
  var GeoVizMap = function(map, mapcanvas, params) {
    this.color_theme = params ? params["color_theme"] : undefined;
    this.hratio = params ? params["hratio"] : 0.8;
    this.vratio = params ? params["vratio"] : 0.8;
    if (!this.hratio) this.hratio = 0.8;
    if (!this.vratio) this.vratio = 0.8;
    // private members
    this.HLT_BRD_CLR = "#CCC";
    this.HLT_CLR = "yellow";
    this.STROKE_CLR = "#CCC";
    this.FILL_CLR = "green";
    this.LINE_WIDTH = 1;
    this.ALPHA = params ? params['alpha'] : 1;
    if (!this.ALPHA) this.ALPHA = 1;
  
    this.mapcanvas = mapcanvas instanceof jQuery ? mapcanvas[0] : mapcanvas;
    this.mapcanvas.width = this.mapcanvas.parentNode.clientWidth * this.hratio;
    this.mapcanvas.height = this.mapcanvas.parentNode.clientHeight * this.vratio;
    
    this.map = map;
    this.shpType = this.map.shpType; 
    
    
    _self = this;
    
    this.selected = [];
    this.brushRect = undefined;
    this.isBrushing = false;
    this.startX = -1;
    this.startY = -1;
    this.startPX = undefined;
    this.startPY = undefined;
    this.isMouseDown = false;
    this.isMouseUp = false;
    this.isMouseMove = false;
    this.isKeyDown = false;
    
    this.offsetX = 0;
    this.offsetY = 0;
    
    this.mapcanvas.addEventListener('mousemove', this.OnMouseMove, false);
    this.mapcanvas.addEventListener('mousedown', this.OnMouseDown, false);
    this.mapcanvas.addEventListener('mouseup', this.OnMouseUp, false);
    this.mapcanvas.addEventListener('keydown', this.OnKeyDown, true);
    this.mapcanvas.addEventListener('keyup', this.OnKeyUp, true);
    window.addEventListener('keydown', this.OnKeyDown, true);
    window.addEventListener('keyup', this.OnKeyUp, true);
    window.addEventListener('resize', this.OnResize, true);
    
    // draw map on Canvas
    this.map.fitScreen(this.mapcanvas.width, this.mapcanvas.height);
    this.draw(this.mapcanvas.getContext("2d"), this.color_theme);
    
    // draw highlight map on hbuffer
    this.hbuffer = document.createElement("canvas");
    this.hbuffer.width = this.mapcanvas.width;
    this.hbuffer.height = this.mapcanvas.height;
    this.draw(this.hbuffer.getContext("2d"), undefined, this.HLT_CLR);
   
    this.buffer = this.createBuffer(this.mapcanvas);
  };
  
  // multi constructors
  //GeoVizMap.fromComponents = function(geojson_url, canvas) {};
  //GeoVizMap.fromComponents = function(zipfile_url, canvas) {};
  
  // static variable
  GeoVizMap.version = "0.1";
  
  // 
  GeoVizMap.prototype = {
    // member functions
    updateColor: function(colorbrewer_obj) {
      this.color_theme  = colorbrewer_obj;
      this.draw(this.mapcanvas.getContext("2d"), this.color_theme);
      this.buffer = this.createBuffer(this.mapcanvas);
    },
    
    // create buffer canvas
    createBuffer: function() {
      var _buffer = document.createElement("canvas");
      _buffer.width = this.mapcanvas.width;
      _buffer.height = this.mapcanvas.height;
      var bufferCtx = _buffer.getContext("2d");
      bufferCtx.drawImage(this.mapcanvas, 0, 0);
      return _buffer;
    },
  
    highlight: function( ids, context, nolinking ) {
      if ( ids == undefined ) 
        return;
        
      if ( context == undefined) { 
        context = _self.mapcanvas.getContext("2d");
        context.imageSmoothingEnabled= false;
        context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
        context.drawImage( _self.buffer, 0, 0);
        context.lineWidth = 0.3;
      } 
      if (_self.shpType == "LineString" || _self.shpType == "Line") {
        context.strokeStyle = _self.HLT_CLR;
      } else {
        context.strokeStyle = _self.STROKE_CLR;
        context.fillStyle = _self.HLT_CLR;
      }
      
      var screenObjs = this.map.screenObjects; 
      var colors = {};
      colors[this.HLT_CLR] =  ids;
      
      if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon") {
        _self.drawPolygons( context, screenObjs, colors ); 
      } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
        _self.drawPoints( context, screenObjs, colors );
      } else if (_self.shpType == "LineString" || _self.shpType == "Line") {
        _self.drawLines( context, screenObjs, colors);
      }
      
      return context;
    },
    
    highlightExt: function( ids, extent, linking) {
      context = _self.mapcanvas.getContext("2d");
      context.imageSmoothingEnabled= false;
      context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
      context.globalAlpha = 1;
      context.drawImage( _self.buffer, 0, 0);
      context.globalAlpha = _self.ALPHA;
      
      if ( ids.length == 0) {
        return;
      }
      var x0 = extent[0], y0 = extent[1], x1 = extent[2], y1 = extent[3];
      var pt0 = _self.map.mapToScreen(x0, y0),
          pt1 = _self.map.mapToScreen(x1, y1);
      
      var startX = pt0[0], startY = pt0[1], 
          w = pt1[0] - startX, 
          h = pt1[1] - startY;
          
      if (w == 0 && h == 0) 
        return;
     
      var hdraw = [], ddraw = []; 
      var minPX = Math.min( pt0[0], pt1[0]),
          maxPX = Math.max( pt0[0], pt1[0]),
          minPY = Math.min( pt0[1], pt1[1]),
          maxPY = Math.max( pt0[1], pt1[1]);
          
      for ( var i=0, n=_self.map.centroids.length; i<n; ++i) {
        var pt = _self.map.centroids[i],
            inside = false;
        if ( pt[0] >= minPX && pt[0] <= maxPX && 
             pt[1] >= minPY && pt[1] <= maxPY) {
          inside = true;
        }
        // fine polygons on border of rect
        var bx = _self.map.bbox[i]; 
        if (bx[0] > x1 || bx[1] < x0 || bx[2] > y1 || bx[3] < y0) {
        } else if (x0 < bx[0] && bx[1] < x1 && y0 < bx[2] && bx[3] < y1) {
        } else {
          if (inside) {
            // draw it with highligh
            hdraw.push(i);
          } else {
            // draw it with default
            ddraw.push(i);
          }
        }
      }
      if ( hdraw.length + ddraw.length == 0) {
        return false;
      }
      
      context.save();
      // draw a selection box
      context.beginPath();
      if ( _self.isBrushing == true ) {
        context.rect(startX, startY, 
                     _self.brushRect.GetW(), _self.brushRect.GetH());
      } else {
        context.rect( startX, startY, w, h);
      }
      context.closePath();
     
      context.clip();
      
      context.globalAlpha = 1;
      context.drawImage( _self.hbuffer, 0, 0);
      context.restore();
      _self.highlight(hdraw, context);
      _self.drawSelect(ddraw, context);
      
     if (linking) {
        context.beginPath();
        context.rect( startX, startY, w, h);
        context.strokeStyle = "black";
        context.stroke();
        context.closePath();
        
        // trigger to brush/link
        var hl = {};
        if ( localStorage["HL_IDS"] ){ 
          hl = JSON.parse(localStorage["HL_IDS"]);
        }
        hl[_self.mapcanvas.id] = _self.selected;
        localStorage["HL_IDS"] = JSON.stringify(hl);
       
        var hl_map = {}; 
        if ( localStorage["HL_MAP"] ){ 
          hl_map = JSON.parse(localStorage["HL_MAP"]);
        }
        hl_map[_self.mapcanvas.id] = [x0, y0, x1, y1];
        localStorage["HL_MAP"] = JSON.stringify(hl_map);
    }
      return true;
    },
    
    drawPolygons: function(ctx, polygons, colors) {
      if ( polygons == undefined || polygons.length == 0) {
        return;
      }
      if ( colors == undefined ) { 
        for ( var i=0, n=polygons.length; i<n; i++ ) {
          ctx.beginPath();
          var obj = polygons[i];
          if ( Array.isArray(obj[0][0])) {
            // multi parts 
            for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
              ctx.moveTo(obj[j][0][0], obj[j][0][1]);
              for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                var x = obj[j][k][0],
                    y = obj[j][k][1];
                ctx.lineTo(x, y);
              }
            }
          } else {
            ctx.moveTo(obj[0][0], obj[0][1]);
            for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
              var x = obj[k][0],
                  y = obj[k][1];
              ctx.lineTo(x, y);
            }
          }
          ctx.fill();
          ctx.stroke();
        } 
      } else {
        for ( var c in colors ) {
          var ids = colors[c];
          ctx.fillStyle = c;
          for ( var i=0, n=ids.length; i< n; ++i) {
            ctx.beginPath();
            var obj = polygons[ids[i]];
            if ( Array.isArray(obj[0][0])) {
              // multi parts 
              for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
                ctx.moveTo(obj[j][0][0], obj[j][0][1]);
                for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                  var x = obj[j][k][0],
                      y = obj[j][k][1];
                  ctx.lineTo(x, y);
                }
              }
            } else {
              ctx.moveTo(obj[0][0], obj[0][1]);
              for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
                var x = obj[k][0],
                    y = obj[k][1];
                ctx.lineTo(x, y);
              }
            }
            ctx.fill();
            ctx.stroke();
          }
        }
      }
    },
    
    drawLines: function( ctx, lines, colors ) {
      if ( lines == undefined || lines.length == 0 )
        return;
      if ( colors == undefined ) { 
        ctx.beginPath();
        for ( var i=0, n=lines.length; i<n; i++ ) {
          var obj = lines[i];
          if ( Array.isArray(obj[0][0]) ) {
            // multi parts 
            for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
              ctx.moveTo(obj[j][0][0], obj[j][0][1]);
              for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                var x = obj[j][k][0], y = obj[j][k][1];
                ctx.lineTo(x, y);
              }
            }
          } else {
            ctx.moveTo(obj[0][0], obj[0][1]);
            for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
              var x = obj[k][0], y = obj[k][1];
              ctx.lineTo(x, y);
            }
          }
        } 
        ctx.stroke();
      } else {
        for ( var c in colors ) {
          var ids = colors[c];
          ctx.strokeStyle = c;
          for ( var i=0, n=ids.length; i< n; ++i) {
            ctx.beginPath();
            var obj = lines[ids[i]];
            if ( Array.isArray(obj[0][0]) ) {
              // multi parts 
              for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
                ctx.moveTo(obj[j][0][0], obj[j][0][1]);
                for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                  var x = obj[j][k][0], y = obj[j][k][1];
                  ctx.lineTo(x, y);
                }
              }
            } else {
              ctx.moveTo(obj[0][0], obj[0][1]);
              for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
                var x = obj[k][0], y = obj[k][1];
                ctx.lineTo(x, y);
              }
            }
            ctx.stroke();
          }
        }
      }  
    },
    
    drawPoints: function( ctx, points, colors ) {
      if ( colors == undefined ) { 
        for ( var i=0, n=points.length; i<n; i++ ) {
          var pt = points[i];
          ctx.fillRect(pt[0], pt[1], 2, 2);
        } 
      } else {
        for ( var c in colors ) {
          ctx.fillStyle = c;
          var ids = colors[c];
          for ( var i=0, n=ids.length; i< n; ++i) {
            var pt = points[ids[i]];
            ctx.fillRect(pt[0], pt[1], 2, 2);
          } 
        }
      }  
    },
    
    draw: function(context,  colors, fillColor, strokeColor, lineWidth) {
      context.imageSmoothingEnabled= false;
      context.lineWidth = 0.3;
      context.globalAlpha = this.ALPHA;
      if (_self.shpType == "LineString" || _self.shpType == "Line") {
        context.strokeStyle = fillColor ? fillColor : _self.FILL_CLR;
        context.lineWidth = lineWidth ? lineWidth: _self.LINE_WIDTH;
      } else {
        context.strokeStyle = strokeColor ? strokeColor : _self.STROKE_CLR;
        context.fillStyle = fillColor ? fillColor : _self.FILL_CLR;
      }
      
      if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon" ) {
        _self.drawPolygons( context, _self.map.screenObjects, colors) ;
      } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
        _self.drawPoints( context, _self.map.screenObjects, colors) ;
      } else if (_self.shpType == "Line" || _self.shpType == "LineString") {
        _self.drawLines( context, _self.map.screenObjects, colors) ;
      }
    }, 
    
    drawSelect: function( ids, context ) {
      context.globalAlpha = 0.6;
      var ids_dict = {};     
      for ( var i=0, n=ids.length; i<n; i++ ) {
        ids_dict[ids[i]] = 1;
      }
      var screenObjs = _self.map.screenObjects; 
      var colors = {}; 
      if ( _self.color_theme ) {
        for ( var c in _self.color_theme ) {
          var orig_ids = _self.color_theme[c];
          var new_ids = [];
          for (var i in orig_ids ) {
            var oid = orig_ids[i];
            if ( ids_dict[oid] == 1) {
              new_ids.push(oid);
            }
          }
          colors[c] = new_ids;
        }
      } else {
        colors[_self.FILL_CLR] = ids;
      }
      if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon") {
        _self.drawPolygons( context, screenObjs, colors);
      } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
        _self.drawPoints( context, screenObjs, colors );
      } else if (_self.shpType == "LineString" || _self.shpType == "Line") {
        _self.drawLines( context, screenObjs, colors );
      }
    },
    clean: function() {
      var context = _self.mapcanvas.getContext("2d");
      context.imageSmoothingEnabled= false;
      context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
      return context;
    },
    update: function(params) {
      if (params) {
        if (params['alpha']) this.ALPHA = alpha;
        this.offsetX = params['offsetX'] ? params['offsetX'] : 0;
        this.offsetY = params['offsetY'] ? params['offsetY'] : 0;
      }
      var newWidth = _self.mapcanvas.parentNode.clientWidth * _self.hratio;
      var newHeight = _self.mapcanvas.parentNode.clientHeight * _self.vratio;
      _self.mapcanvas.width = newWidth;
      _self.mapcanvas.height = newHeight;
      _self.map.fitScreen(newWidth, newHeight);
      _self.draw(_self.mapcanvas.getContext("2d"), _self.color_theme);
      
      
      _self.hbuffer = document.createElement("canvas");
      _self.hbuffer.width = _self.mapcanvas.width;
      _self.hbuffer.height = _self.mapcanvas.height;
      _self.draw(_self.hbuffer.getContext("2d"), undefined, _self.HLT_CLR);
     
      _self.buffer = _self.createBuffer(_self.mapcanvas);
    },
    // register mouse events of canvas
    OnResize: function( e) {
      this.update();
      console.log("OnResize");
    },
    OnKeyDown: function( e ) {
      if ( e.keyCode == 115 ) {
        _self.isKeyDown = true;
      } else if ( e.keyCode = 77 ) {
        _self.mapcanvas.style.pointerEvents= 'none';  
      }
    },
    OnKeyUp: function( e ) {
      if ( e.keyCode = 77 ) {
        _self.mapcanvas;  
        _self.mapcanvas.style.pointerEvents= 'auto';  
      }
    },
    OnMouseDown: function( evt ) {
      //var x = evt.pageX, y = evt.pageY;
      var x = evt.offsetX, y = evt.offsetY;
      _self.isMouseDown = true;
      _self.startX = x;
      _self.startY = y;
      if ( _self.isKeyDown == true ) {
        if (_self.brushRect && _self.brushRect.Contains(new GPoint(x, y)) ) {
          console.log("brushing");
          _self.isBrushing = true;
        }
      }
      if (_self.brushRect == undefined ||
          _self.brushRect && !_self.brushRect.Contains(new GPoint(x, y)) ) {
        console.log("cancel brushing");
        var context = _self.mapcanvas.getContext("2d");
        context.imageSmoothingEnabled= false;
        context.globalAlpha = 1;
        context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
        context.drawImage( _self.buffer, 0, 0);
        _self.brushRect = undefined;
        _self.isBrushing = false;
        context.globalAlpha = this.ALPHA;
      }
    },
    OnMouseMove: function(evt) {
      var x = evt.offsetX, y = evt.offsetY;
      var startX, 
          startY;
          
      if ( _self.isMouseDown == true ) {
        var context;
        if ( _self.isBrushing == true ) {
          var offsetX = x - _self.startX,
              offsetY = y - _self.startY;
          startX = _self.brushRect.x0 + offsetX;
          startY = _self.brushRect.y0 + offsetY;
        } else {
          startX = _self.startX;
          startY = _self.startY;
        }
        // highlight selection
        var pt0 = _self.map.screenToMap(startX, startY), 
            pt1;
        if ( _self.isBrushing == true ) {
          pt1 = _self.map.screenToMap(startX + _self.brushRect.GetW(), 
                                  startY + _self.brushRect.GetH());
        } else {
          pt1 = _self.map.screenToMap(x,y);
        } 
       
        var x0 = pt0[0] <= pt1[0] ? pt0[0] : pt1[0];
        var x1 = pt0[0] > pt1[0] ? pt0[0] : pt1[0];
        var y0 = pt0[1] <= pt1[1] ? pt0[1] : pt1[1];
        var y1 = pt0[1] > pt1[1] ? pt0[1] : pt1[1];
        _self.highlightExt([1], [x0, y0, x1, y1], true);
      }
    },
    OnMouseUp: function(evt) {
      //var x = evt.pageX, y = evt.pageY;
      var x = evt.offsetX, y = evt.offsetY;
      if ( _self.isMouseDown == true) {
        if ( _self.startX == x && _self.startY == y ) {
          // point select
          var pt = _self.map.screenToMap(x, y);
          x = pt[0];
          y = pt[1];
          _self.map.bbox.forEach( function( box, i ) {
            if ( x > box[0] && x < box[1] && 
                 y > box[2] && y < box[3] ) {
              _self.highlight([i]);
              _self.isMouseDown = false;
              
              return;
            }
          });
          // trigger brush/link
          var hl = {};
          if ( localStorage["HL_IDS"] ){ 
            hl = JSON.parse(localStorage["HL_IDS"]);
          }
          hl[_self.mapcanvas.id] = [];
          localStorage["HL_IDS"] = JSON.stringify(hl);
          
          var hl_map = {}; 
          if ( localStorage["HL_MAP"] ){ 
            hl_map = JSON.parse(localStorage["HL_MAP"]);
          }
          hl_map[_self.mapcanvas.id] = [0,0,0,0];
          localStorage["HL_MAP"] = JSON.stringify(hl_map);
        }
        else if ( _self.isKeyDown == true ) {
          // setup brushing box
          _self.brushRect = new GRect( _self.startX, _self.startY, x, y);
        }
      }
      _self.isMouseDown = false;
    },
    
  };
  
  window["ShpMap"] = ShpMap;
  window["JsonMap"] = JsonMap;
  window["LeafletMap"] = LeafletMap;
  window["GeoVizMap"] = GeoVizMap;
})(self);
