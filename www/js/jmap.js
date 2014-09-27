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
    this.mapExtent = [];
    this.mapLeft = undefined;
    this.mapRight = undefined;
    this.mapBottom = undefined; 
    this.mapTop = undefined;
    this.mapWidth = undefined;
    this.mapHeight = undefined;
    this.screenObjects = [];
  };
  
  
  var ShpMap = function(shpFile ) {
  };

  /**
   * extent: if show this map on google map which has predefined extent
   */
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
          x, y;
      if ( coords[0][0] instanceof Array ) {
        // multi-geometries
        for ( var j=0, nParts=coords.length; j < nParts; j++ ) {
          var part =  coords[j];
          for ( var k=0, nPoints=part.length; k < nPoints; k++ ) {
            x = part[k][0], y = part[k][1];
            if (nPoints > 1) {
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
        }
      } else {
        for ( var k=0, nPoints=coords.length; k < nPoints; k++ ) {
          x = coords[k][0], y = coords[k][1];
          if ( nPoints > 1 ) {
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
    this.screenObjects = [];
    for ( var i=0, n=this.geojson.features.length; i<n; i++ ) {
      var coords = this.geojson.features[i].geometry.coordinates,
          screenCoords = [];
      if ( coords[0][0] instanceof Array ) {
        // multi-geometries
        for ( var j=0, nParts=coords.length; j < nParts; j++ ) {
          var part =  coords[j], 
              screenPart = [];
          for ( var k=0, nPoints=part.length; k < nPoints; k++ ) {
            var x = part[k][0], y = part[k][1];
            x = scaleX * (x - this.mapLeft) + offsetX;
            y = scaleY * (this.mapTop - y) + offsetY;
            screenPart.push([x,y]);
          }
          screenCoords.push( screenPart );
        }
      } else {
        for ( var k=0, nPoints=coords.length; k < nPoints; k++ ) {
          var x = coords[k][0], y = coords[k][1];
          screenCoords.push([x,y]);
        }
      }
      this.screenObjects.push(screenCoords);
    }
    this.offsetX = offsetX;
    this.offsetY = offsetY;
    this.scaleX = scaleX;
    this.scaleY = scaleY;
    this.scalePX = 1/scaleX;
    this.scalePY = 1/scaleY;
  };
  
  JsonMap.prototype.screenToMap = function(px, py) {
    var x = this.scalePX * (px - this.offsetX) + this.mapLeft;
    var y = this.mapTop - this.scalePY * (py - this.offsetY);
    return [x, y];
  };
  
  JsonMap.prototype.mapToScreen = function(x, y) {
    var px = this.scaleX * (x - this.mapLeft) + this.offsetX;
    var py = this.scaleY * (this.mapTop - y) + this.offsetY;
    return [x, y];
  };
  
  var GeoVizMap = function(map, mapcanvas, color_theme, id_category, extent) {
    // private members
    this.HLT_BRD_CLR = "#CCC";
    this.HLT_CLR = "yellow";
    this.STROKE_CLR = "#CCC";
    this.FILL_CLR = "green";
    this.LINE_WIDTH = 1;
  
    this.mapcanvas = mapcanvas instanceof jQuery ? mapcanvas[0] : mapcanvas;
    this.mapcanvas.width = this.mapcanvas.parentNode.clientWidth * 0.8;
    this.mapcanvas.height = this.mapcanvas.parentNode.clientHeight * 0.8;
    
    this.map = map;
    this.shpType = this.map.shpType; 
    
    this.color_theme = color_theme;
    this.id_category = id_category;
    
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
    
    this.mapcanvas.addEventListener('mousemove', this.OnMouseMove, false);
    this.mapcanvas.addEventListener('mousedown', this.OnMouseDown, false);
    this.mapcanvas.addEventListener('mouseup', this.OnMouseUp, false);
    this.mapcanvas.addEventListener('keydown', this.OnKeyDown, true);
    window.addEventListener('keypress', this.OnKeyDown, true);
    window.addEventListener('resize', this.OnResize, true);
    
     
    // draw map on Canvas
    this.map.fitScreen(this.mapcanvas.width, this.mapcanvas.height);
    this.draw(this.mapcanvas.getContext("2d"));
    
    // draw highlight map on hbuffer
    this.hbuffer = document.createElement("canvas");
    this.hbuffer.width = this.mapcanvas.width;
    this.hbuffer.height = this.mapcanvas.height;
    this.draw(this.hbuffer.getContext("2d"), this.HLT_CLR);
   
    /* 
      context = _self.mapcanvas.getContext("2d");
      context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
      context.drawImage( _self.hbuffer, 0, 0);
    */
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
      this.draw();
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
  
    highlight: function( ids, nolinking ) {
      context = _self.mapcanvas.getContext("2d");
      context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
      context.drawImage( _self.buffer, 0, 0);
      context.lineWidth = 1;
      context.strokeStyle = _self.HLT_BRD_CLR;
      context.fillStyle = _self.HLT_CLR;
      
      ids.forEach( function( id) {
        if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon") {
          _self.drawPolygon( context, _self.geojson.features[id] );
        } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
          _self.drawPoint( context, _self.geojson.features[id] );
        } else if (_self.shpType == "LineString" || _self.shpType == "Line") {
          _self.drawLine( context, _self.geojson.features[id] );
        }
      });
      if (nolinking == undefined) {
        localStorage["HL_LAYER"] = _self.mapcanvas.id;
        localStorage["HL_IDS"] = ids.toString();
      }
      return context;
    },
    
    drawPolygons: function(ctx, polygons, colors) {
      if ( colors == undefined ) { 
        for ( var i=0, n=polygons.length; i<n; i++ ) {
          ctx.beginPath();
          var obj = polygons[i];
          if ( obj[0][0] instanceof Array ) {
            // multi parts 
            for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
              ctx.moveTo(obj[j][0][0], obj[j][0][1]);
              for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                var x = obj[j][k][0], y = obj[j][k][1];
                ctx.lineTo(x, y);
              }
              ctx.stroke();
              ctx.fill();
            }
          } else {
            ctx.moveTo(obj[0][0], obj[0][1]);
            for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
              var x = obj[k][0], y = obj[k][1];
              ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.fill();
          }
        } 
      } else {
        for ( var c in colors ) {
          var ids = colors[c];
          for ( var i=0, n=ids.length; i< n; ++i) {
            ctx.beginPath();
            var obj = polygons[ids[i]];
            if ( obj[0][0] instanceof Array ) {
              // multi parts 
              for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
                ctx.moveTo(obj[j][0][0], obj[j][0][1]);
                for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                  var x = obj[j][k][0], y = obj[j][k][1];
                  ctx.lineTo(x, y);
                }
              }
              ctx.stroke();
              ctx.fillStyle = c;
              ctx.fill();
            } else {
              ctx.moveTo(obj[0][0], obj[0][1]);
              for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
                var x = obj[k][0], y = obj[k][1];
                ctx.lineTo(x, y);
              }
              ctx.stroke();
              ctx.fill();
            }
          }
        }
      }
    },
    
    drawLines: function( ctx, lines, lineWidth, colors ) {
      if ( colors == undefined ) { 
        ctx.stokeStyle = this.FILL_CLR;
        ctx.lineWidth = lineWidth;
        for ( var i=0, n=lines.length; i<n; i++ ) {
          ctx.beginPath();
          var obj = lines[i];
          if ( obj[0][0] instanceof Array ) {
            // multi parts 
            for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
              ctx.moveTo(obj[j][0][0], obj[j][0][1]);
              for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                var x = obj[j][k][0], y = obj[j][k][1];
                ctx.lineTo(x, y);
              }
              ctx.stroke();
            }
          } else {
            ctx.moveTo(obj[0][0], obj[0][1]);
            for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
              var x = obj[k][0], y = obj[k][1];
              ctx.lineTo(x, y);
            }
            ctx.stroke();
          }
        } 
      } else {
        for ( var c in colors ) {
          var ids = colors[c];
          for ( var i=0, n=ids.length; i< n; ++i) {
            ctx.beginPath();
            var obj = polygons[ids[i]];
            if ( obj[0][0] instanceof Array ) {
              // multi parts 
              for ( var j=0, nParts=obj.length; j<nParts; j++ ) {
                ctx.moveTo(obj[j][0][0], obj[j][0][1]);
                for ( var k=1, nPoints=obj[j].length; k<nPoints; k++) {
                  var x = obj[j][k][0], y = obj[j][k][1];
                  ctx.lineTo(x, y);
                }
                ctx.strokeStyle = c;
                ctx.stroke();
              }
            } else {
              ctx.moveTo(obj[0][0], obj[0][1]);
              for ( var k=1, nPoints=obj.length; k<nPoints; k++) {
                var x = obj[k][0], y = obj[k][1];
                ctx.lineTo(x, y);
              }
              ctx.stroke();
            }
          }
        }
      }  
    },
    
    drawPoints: function( ctx, points, colors ) {
      ctx.stokeStyle = this.STROKE_CLR;
      if ( colors == undefined ) { 
        ctx.fillStyle = this.FILL_CLR;
        for ( var i=0, n=points.length; i<n; i++ ) {
          var pt = points[i];
          ctx.fillRect(pt[0], pt[1], 2, 2);
        } 
      } else {
        for ( var c in colors ) {
          var ids = colors[c];
          for ( var i=0, n=ids.length; i< n; ++i) {
            ctx.fillStyle = c;
            var pt = points[ids[i]];
            ctx.fillRect(pt[0], pt[1], 2, 2);
          } 
        }
      }  
    },
    
    draw: function(context,  fillColor, strokeColor, colors) {
      context.imageSmoothingEnabled= false;
      if (_self.shpType == "LineString" || _self.shpType == "Line") {
        context.strokeStyle = fillColor ? fillColor : _self.FILL_CLR;
      } else {
        context.strokeStyle = strokeColor ? strokeColor : _self.STROKE_CLR;
        context.fillStyle = fillColor ? fillColor : _self.FILL_CLR;
      }
      
      if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon" ) {
        _self.drawPolygons( context, _self.map.screenObjects, colors) ;
      } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
        _self.drawPoints( context, _self.map.screenObjects, colors ) ;
      } else if (_self.shpType == "Line" || _self.shpType == "LineString") {
        _self.drawLines( context, _self.map.screenObjects, colors ) ;
      }
    }, 
    
    drawSelect: function( context, ids, strokeColor, fillColor ) {
      context.imageSmoothingEnabled= false;
      if (_self.shpType == "LineString" || _self.shpType == "Line") {
        context.strokeStyle = fillColor ? fillColor : _self.HLT_CLR;
      } else {
        context.strokeStyle = strokeColor ? strokeColor : _self.STROKE_CLR;
        context.fillStyle = fillColor ? fillColor : _self.HLT_CLR;
      }

      var selObjs = [];     
      for ( var i=0, n=ids.length; i<n; i++ ) {
        selObjs.push(_self.map.screenObjects[ids[i]]);
      }
      if (_self.shpType == "Polygon" || _self.shpType == "MultiPolygon") {
        _self.drawPolygons( context, selObjs );
      } else if (_self.shpType == "Point" || _self.shpType == "MultiPoint") {
        _self.drawPoints( context, selObjs );
      } else if (_self.shpType == "LineString" || _self.shpType == "Line") {
        _self.drawLines( context, selObjs );
      }
    },
    
    // register mouse events of canvas
    OnResize: function( e) {
      var newWidth = _self.mapcanvas.parentNode.clientWidth * 0.8;
      var newHeight = _self.mapcanvas.parentNode.clientHeight * 0.8;
      _self.mapcanvas.width = newWidth;
      _self.mapcanvas.height = newHeight;
      _self.map.fitScreen(newWidth, newHeight);
      _self.draw(_self.mapcanvas.getContext("2d"));
      console.log("OnResize");
    },
    OnKeyDown: function( e ) {
      if ( e.keyCode == 115 ) {
        _self.isKeyDown = true;
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
        context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
        context.drawImage( _self.buffer, 0, 0);
        _self.brushRect = undefined;
        _self.isBrushing = false;
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
        var hdraw= [];
        var ddraw = []; 
        if ( x == _self.startX && y == _self.startY ) {
        } else {
          var minPX = Math.min( pt0[0], pt1[0]),
              maxPX = Math.max( pt0[0], pt1[0]),
              minPY = Math.min( pt0[1], pt1[1]),
              maxPY = Math.max( pt0[1], pt1[1]);
          _self.selected = [];
          for ( var i=0, n=_self.map.centroids.length; i<n; ++i) {
            var pt = _self.map.centroids[i],
                inside = false;
            if ( pt[0] >= minPX && pt[0] <= maxPX && 
                 pt[1] >= minPY && pt[1] <= maxPY) {
              _self.selected.push(i);
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
        }
        context = _self.mapcanvas.getContext("2d");
        context.clearRect(0, 0, _self.mapcanvas.width, _self.mapcanvas.height);
        context.drawImage( _self.buffer, 0, 0);
        context.save();
        // draw a selection box
        context.beginPath();
        if ( _self.isBrushing == true ) {
          context.rect(startX, startY, 
                       _self.brushRect.GetW(), _self.brushRect.GetH());
        } else {
          var w = x - startX, 
              h = y - startY;
          context.rect( startX, startY, w, h);
        }
        context.closePath();
       
        context.clip();
        
        context.drawImage( _self.hbuffer, 0, 0);
        context.restore();
        console.log(hdraw.length);
        _self.drawSelect(context, hdraw, _self.HLT_BRD_CLR, _self.HLT_CLR);
        _self.drawSelect(context, ddraw, _self.STROKE_CLR, _self.FILL_CLR);
        
        context.beginPath();
        context.rect( startX, startY, w, h);
        context.strokeStyle = "black";
        context.stroke();
        context.closePath();
      }
    },
    OnMouseUp: function(evt) {
      //var x = evt.pageX, y = evt.pageY;
      var x = evt.offsetX, y = evt.offsetY;
      if ( _self.isMouseDown == true) {
        if ( _self.startX == x && _self.startY == y ) {
          // point select
          var pt = _self.screenToMap(x, y);
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
        }
        else if ( _self.isKeyDown == true ) {
          // setup brushing box
          _self.brushRect = new GRect( _self.startX, _self.startY, x, y);
        }
      }
      _self.isMouseDown = false;
    },
    
  };
  
  window["JsonMap"] = JsonMap;
  window["GeoVizMap"] = GeoVizMap;
})(self);
