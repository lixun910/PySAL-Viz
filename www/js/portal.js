var html_load_img = "<img src=img/loading_small.gif>",
    html_check_img = "<img src=img/checkmark.png>",
    html_uncheck_img = "<img src=img/uncheckmark.png>";

function ShowMsgBox(title, content) {
  $("#msg-title").text(title);
  $("#msg-content").text(content);
  $('#dlg-msg').dialog('open');
}

var viz, foreground, lmap, map, uuid, winID, 
    prj,
    gHasProj     =false, 
    gShowLeaflet =false, 
    gAddLayer    =false;

$(document).ready(function() {
  //////////////////////////////////////////////////////////////
  //  Map
  //////////////////////////////////////////////////////////////
  winID = getParameterByName("wid");
  
  // create Leaflet map 
  lmap = L.map('map');
  L.tileLayer('https://{s}.tiles.mapbox.com/v3/{id}/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' + 
    '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
    'Imagery © <a href="http://mapbox.com">Mapbox</a>',
    id: 'examples.map-20v6611k'
  }).addTo(lmap);

  // Local Storage Brushing/Linking
  localStorage.clear();  
  viz = new d3viz(winID, $('#map-container')); 
  viz.SetupBrushLink();
  viz.SetupWebSocket();
  
  var OnMapShown = function() {
    $('#loading').remove();
    $('#dialog-open-file').dialog('close');
    
    InitDialogs();
    
    if (gShowLeaflet == true) {
      map = viz.map;
      lmap.on('zoomstart', function() {
        map.clean();
      });
      lmap.on('zoomend', function() {
        map.update();
      });
      lmap.on('movestart', function(e) {
        map.clean();
      });
      lmap.on('moveend', function(e) {
        var op = e.target.getPixelOrigin();
        var np = e.target._getTopLeftPoint();
        var offsetX = -np.x + op.x;
        var offsetY = -np.y + op.y;
        map.update({"offsetX":offsetX, "offsetY":offsetY});
      });
    } else {
      $('#map').hide();
    }
  };
  
  var InitDialogs = function(){
    // fill dialogs
    if (uuid && uuid in viz.dataDict) {
      var data = viz.dataDict[uuid];
      var field_names = [];
      for (var field in data.features[0].properties) {
        field_names.push(field);
      }
      field_names.sort();
      var var_combobox= ['#sel-var', '#sel-w-id', '#sel-scatter-x', '#sel-scatter-y', '#sel-moran-var','#sel-lisa-var'];
      $.each( var_combobox, function(i, var_cmb ) {
        $(var_cmb).find('option').remove().end();
        $.each(field_names, function(j, field_name) {
          $(var_cmb).append($('<option>', {value: field_name}).text(field_name));
        });
      });
      // in regression dialog
      //var boxes = ['#y_box','#y_box','#y_box','#y_box']; 
      if ( !$('#y_box').find(".placeholder")) 
        $('#y_box').find('li').remove().end();
      if ( !$('#x_box').find(".placeholder")) 
        $('#x_box').find('li').remove().end();
      if ( !$('#ye_box').find(".placeholder")) 
        $('#ye_box').find('li').remove().end();
      if ( !$('#inst_box').find(".placeholder")) 
        $('#inst_box').find('li').remove().end();
      if ( !$('#r_box').find(".placeholder")) 
        $('#r_box').find('li').remove().end();
      $('#ul-x-variables').find('li').remove().end();
      $.each(field_names, function(i, field_name) {
        var item = $('#ul-x-variables').append('<li><p class="name">'+field_name+'</p></li>');
      });
      $( "#vars ul li" ).draggable({ helper: "clone" });
      new List('vars', {valueNames:['name']});
    }
  };
  //////////////////////////////////////////////////////////////
  //  Init UI
  //////////////////////////////////////////////////////////////
  $('#divPop').hide();
  jQuery.fn.popupDiv = function (divToPop, text) {
    var pos=$(this).offset();
    var h=$(this).height();
    var w=$(this).width();
    if (w == 0) w = 40;
    if ( text != undefined ) {
      $(divToPop).html(text);
    }
    $(divToPop).css({ left: pos.left + w , top: pos.top - h });
    $(divToPop).show(function() {
      setTimeout(function(){ $(divToPop).fadeOut('slow');}, 2000);
    });
  };
  $('#img-id-chk').hide();
  $('#img-id-spin').hide();
  $('#img-id-nochk').hide();
  $( "#dlg-msg" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400, height: 200, autoOpen: false, modal: true,
    buttons: {OK: function() {$( this ).dialog( "close" );}}
  });
  $('#dlg-msg').hide();
  $('.dlg-loading').hide();
  $('#btnOpenData').click(function(){
    gAddLayer = false;
    $('#dialog-open-file').dialog('option','title','Open Map Dialog');
    $('#dialog-open-file').dialog('open');
  });
  $('#btnAddLayer').click(function(){
    gAddLayer = true;
    $('#dialog-open-file').dialog('option','title','Add Layer Dialog');
    $('#dialog-open-file').dialog('open');
  });
  $('#btnCartoDB').click(function(){$('#dialog-cartodb').dialog('open');});
  $('#btnRoadNetwork').click(function(){$('#dialog-road').dialog('open');});
  $('#btnSpaceTime').click(function(){$('#dialog-spacetime').dialog('open');});
  $('#btnCreateW').click(function(){$('#dialog-weights').dialog('open');});
  $('#btnSpreg').click(function(){$('#dialog-regression').dialog('open');});
  $('#btnNewMap').click(function(){$('#dlg-quantile-map').dialog('open');});
  $('#btnScatterPlot').click(function(){$('#dlg-scatter-plot').dialog('open');});
  $('#btnMoran').click(function(){$('#dlg-moran-scatter-plot').dialog('open');});
  $('#btnLISA').click(function(){$('#dlg-lisa-map').dialog('open');});
  //////////////////////////////////////////////////////////////
  //  Open File 
  //////////////////////////////////////////////////////////////
  $('#tabs-dlg-open-file').tabs();
  $( "#dialog-open-file" ).dialog({
    height: 380,
    width: 480,
    autoOpen: true,
    modal: false,
    dialogClass: "dialogWithDropShadow",
    buttons: [
      {
        text: "OK",
        click: function() {
          var sel_id = $("#tabs-dlg-open-file").tabs('option','active');
          if (sel_id == 1) {
            // cartodb: download map from cartodb
          }
          $( this ).dialog( "close" );
        },
      },
      {
        text: "Close",
        click: function() {
          $( this ).dialog( "close" );
        },
      }
    ]
  });
  //$('#dialog-open-file').dialog('open');
  // switch leaflet
  var showLeafletMap = function(uuid) {
    if (uuid && viz) {
      gShowLeaflet = true;
      if ( gHasProj && prj == undefined) {
        // wait for reading *.prj file 
        setTimeout(function(){showLeafletMap(uuid);}, 10);  
      } else {
        $('#map').show();
        viz.ShowLeafletMap(uuid, L, lmap, prj, {
          "hratio": 1, "vratio": 1, "alpha": 0.8,
        }, OnMapShown);
      }
    }
  };
  var showPlainMap = function(uuid) {
    if (uuid && viz) {
      gShowLeaflet = false;
      viz.ShowMap(uuid,OnMapShown); 
    }
  };
  
  $("#switch").switchButton({
    checked: false,
    on_label: 'ON',
    off_label: 'Leaflet Background? OFF',
    on_callback: function() {
      gShowLeaflet = true;
      showLeafletMap(uuid);
    },
    off_callback: function() {
      gShowLeaflet = false;
      showPlainMap(uuid);
    },
  });
   //////////////////////////////////////////////////////////////
  //  Drag & Drop
  //////////////////////////////////////////////////////////////
  var reader;
  var dropZone = document.getElementById('drop_zone');
  var progress = document.querySelector('.percent');
  if (typeof window.FileReader === 'undefined') {
    console.log( 'File API not available.');
  }
  function updateProgress(evt) {
    // evt is an ProgressEvent.
    if (evt.lengthComputable) {
      var percentLoaded = Math.round((evt.loaded / evt.total) * 100);
      // Increase the progress bar length.
      if (percentLoaded < 100) {
        progress.style.width = percentLoaded + '%';
        progress.textContent = percentLoaded + '%';
      }
    }
  }
  dropZone.ondragover = function(evt) {
    $("#"+evt.target.id).css("color", "black");
    return false;
  };
  dropZone.ondragend = function(evt) {
    $("#"+evt.target.id).css("color", "#bbb");
    return false;
  };
  dropZone.ondrop = function(evt) {
    evt.preventDefault();
    $("#"+evt.target.id).css("color", "#bbb");
    // Reset progress indicator on new file selection.
    progress.style.width = '0%';
    progress.textContent = '0%';
    reader = new FileReader();
    reader.onload = function(e) {
      console.log(reader.result);
      // read *.prj file
      var ip = reader.result;
      prj = proj4(ip, proj4.defs('WGS84'));
    };
    var formData = new FormData(),
        files = evt.dataTransfer.files, // FileList object.
        bJson = 0, bShp = 0, bDbf =0, bShx =0,
        shpFileName = "", shpFile;
    gHasProj = false,
    $.each(files, function(i, f) {
      var name = f.name,
          suffix = getSuffix(name);
      if (suffix === 'geojson' || suffix === 'json') {
        bJson = 1;
        shpFileName = name;
        shpFile = f;
      } else if (suffix === "shp") {
        bShp = 1;
        shpFileName = name;
        shpFile = f;
      } else if (suffix === "shx") {
        bShx = 1;
      } else if (suffix === "dbf") {
        bDbf = 1;
      } else if (suffix === "prj") {
        gHasProj = true;
        reader.readAsText(f);
      }
    });
    // check files
    if (!bJson && !bShp && !bShx && !bDbf ) {
      ShowMsgBox("Error", "Please drag&drop either one json/geojson file, or ESRI Shapefiles (*.shp, *.dbf, *.shx and *.prj) ");
      return false;
    } else if (!bJson && (!bShp || !bShx || !bDbf )) {
      ShowMsgBox("Error", "Please drag&drop three files (*.shp, *.dbf, *.shx and *.prj)  at the same time. (Tips: use ctrl (windows) or command (mac) to select multiple files.)");
      return false;
    } 
    if (!bJson && !gHasProj ) {
      ShowMsgBox("Info", "The *.prj file is not found. The map will not be shown using Leaflet."); 
    }
    $.each(files, function(i, f) {
      if ($.inArray(getSuffix(f.name), ['json','geojson','shp','shx','dbf', 'prj'] ) >=0) {
        formData.append('userfile', f, f.name);
      }
    });
    // upload files to server
    var xhr = new XMLHttpRequest();
    xhr.open('POST', './cgi-bin/upload.py');
    xhr.onload = function() {
      console.log("[Upload]", this.responseText);
      try{
        var data = JSON.parse(this.responseText);
        if ( data['uuid'] != undefined) {
          var path = data["path"];
          if ( gAddLayer == false ) { // open new map
            uuid = data["uuid"];
            foreground = $('#foreground').attr("id", uuid); 
            viz.canvas = foreground;
            if ( gHasProj || gShowLeaflet == true) {
              showLeafletMap(uuid);
            } else {
              showPlainMap(uuid);
            }
          } else { // add new layer
            var subUuid = data["uuid"];
            if ( gHasProj || gShowLeaflet == true) {
              viz.AddLeafletMap(subUuid, L, lmap, prj);
            } else {
              viz.AddPlainMap(subUuid);
            }
          }
          var msg =  {"command":"new_data", "uuid": data['uuid'],"path":path};
          viz.NewDataFromWeb(msg);
        }
      } catch(e){
        console.log("[Error][Upload Files]", e);
      }
      // Ensure that the progress bar displays 100% at the end.
      progress.style.width = '100%';
      progress.textContent = '100%';
      setTimeout("document.getElementById('progress_bar').className='';", 2000);
    }; 
    xhr.upload.onprogress = updateProgress;
    xhr.send(formData);
    document.getElementById('progress_bar').className = 'loading';
  };
 
  //////////////////////////////////////////////////////////////
  //  CartoDB
  //////////////////////////////////////////////////////////////
  $('#tabs-dlg-cartodb').tabs();
  $( "#dialog-cartodb" ).dialog({
    height: 380,
    width: 480,
    autoOpen: false,
    modal: false,
    dialogClass: "dialogWithDropShadow",
    buttons: [
      {
        text: "OK",
        click: function() {
          var sel_id = $("#tabs-dlg-cartodb").tabs('option','active');
          if (sel_id == 1) {
            // cartodb: download map from cartodb
          }
          $( this ).dialog( "close" );
        },
      },
      {
        text: "Close",
        click: function() {
          $( this ).dialog( "close" );
        },
      }
    ]
  });
  
  //////////////////////////////////////////////////////////////
  //  Road
  //////////////////////////////////////////////////////////////
  $('#tabs-dlg-road').tabs();
  $( "#dialog-road" ).dialog({
    height: 380,
    width: 480,
    autoOpen: false,
    modal: false,
    dialogClass: "dialogWithDropShadow",
    buttons: [
      {
        text: "OK",
        click: function() {
          var sel_id = $("#tabs-dlg-road").tabs('option','active');
          if (sel_id == 1) {
            // cartodb: download map from cartodb
          }
          $( this ).dialog( "close" );
        },
      },
      {
        text: "Close",
        click: function() {
          $( this ).dialog( "close" );
        },
      }
    ]
  });
  
  //////////////////////////////////////////////////////////////
  //  Space Time
  //////////////////////////////////////////////////////////////
  $('#datepicker-start').datepicker();
  $('#datepicker-end').datepicker();
  $('#tabs-dlg-spacetime').tabs();
  $( "#dialog-spacetime" ).dialog({
    height: 580,
    width: 480,
    autoOpen: false,
    modal: false,
    dialogClass: "dialogWithDropShadow",
    buttons: [
      {
        text: "OK",
        click: function() {
          var sel_id = $("#tabs-dlg-spacetime").tabs('option','active');
          if (sel_id == 1) {
            // cartodb: download map from cartodb
          }
          $( this ).dialog( "close" );
        },
      },
      {
        text: "Close",
        click: function() {
          $( this ).dialog( "close" );
        },
      }
    ]
  });
  //////////////////////////////////////////////////////////////
  //  Weights creation
  //////////////////////////////////////////////////////////////
  $('#sel-w-files').change( function() {
    var uuid = localStorage['HL_LAYER'];
    var w_name = $('#sel-w-files').val();
    if ( w_name && uuid ) {
      var w_type = $('#sel-w-type').val();
      $.download(
        "../download_w/",
        "uuid=" + uuid + "&w_name=" + w_name + "&w_type=" + w_type,
        "get"
      ); 
    }
    $(this).prop("selectedIndex", -1);
  });
  
  $("#img-id-chk, #img-id-nochk, #img-id-spin").hide();          
  $('#dist-slider').slider({
    min: 0, max: 100,
    slide: function( event, ui ) { $('#txt-dist-thr').val(ui.value); }
  });
  $('#spn-pow-idst, #spn-cont-order, #spn-dist-knn').spinner();
  $('#tabs-dlg-weights').tabs();
  $('#sel-w-id').prop("selectedIndex", -1);
  
  $( "#dialog-weights" ).dialog({
    height: 380, width: 480,
    autoOpen: false, modal: false,
    dialogClass: "dialogWithDropShadow",
    buttons: [
      {
        text: "Create",
        id: "btn-create-w",
        click: function() {
          if ( viz == undefined ) return;
          var w_name = $('#txt-w-name').val(),
          w_id = $('#sel-w-id').find(":selected").val(),
          active = $('#tabs-dlg-weights').tabs("option","active");
          if ( w_name.length == 0 ) {
            ShowMsgBox("Error", "Weights name can't be empty.");
            return;
          }
          if ( w_id.length == 0 || $('#img-id-nochk').is(":visible") ) {
            ShowMsgBox("Error", "An unique ID for weights creation is required.");
            return;
          }
          var post_param = {'w_id': w_id, 'w_name': w_name, };
          if ( active == 0 ) {
            var cont_type = $('#sel-cont-type').find(":selected").val(),
                cont_order = $('#spn-cont-order').val(),
                cont_ilo = $('#cbx-cont-ilo').prop("checked");
                post_param['cont_type'] = parseInt(cont_type);
                post_param['cont_order'] = parseInt(cont_order);
                post_param['cont_ilo'] = cont_ilo;
          } else if ( active == 1) {
            var dist_value = "",
                dist_metric = $('#sel-dist-metr').val(),
                dist_method =$('input:radio[name=rdo-dist]:checked').attr("id");
            if ( dist_method == 0 ) {
              dist_value = $('#spn-dist-knn').val();
            } else if ( dist_method == 1 ) {
              dist_value = $('#txt-dist-thr').val();
            } else if ( dist_method == 2 ) {
              dist_value = $('#txt-dist-thr').val() + "," + $('#spn-pow-idst').val();
            } else {
              ShowMsgBox("","Please select a distance method.");
              return;
            }
            post_param['dist_metric'] = dist_metric;
            post_param['dist_method'] = dist_method;
            post_param['dist_value'] = parseFloat(dist_value);
          } else if ( active == 2) {
            post_param['kernel_type'] = $("#sel-kel-type").val(); 
            post_param['kernel_nn'] = parseInt($("#txt-kel-nn").val());
          }
    
          // submit request
          $("#btn-create-w").attr("disabled",true).fadeTo(0, 0.5);
          $(html_load_img).insertBefore("#btn-create-w");
          post_param['w_type'] = active;
          
          var msg = {"uuid": uuid, "wid": winID, "command":"create_w", 
          "parameters": post_param};
          viz.CreateWeights( msg, OnWeightsCreated);
        }
      },
      {
        text: "Close",
        click: function() {
          $( this ).dialog( "close" );
        },
      }
    ]
  });
  var OnWeightsCreated = function(data) {
    var w_names = [];
    for ( var key in data ) {
      w_names.push(key); 
    }
    w_names.sort();
    w_combobox= ['#sel-model-w-files', '#sel-kernel-w-files', '#sel-w-files','#sel-moran-w','#sel-lisa-w'];
    $.each( w_combobox, function(i, w_cmb ) {
      //$(w_cmb).find('option').remove().end();
      $.each(w_names, function(j, w_name) {
        wtype = data[w_name]["type"];
        if ( (wtype <= 1 && w_cmb == w_combobox[0]) 
              || (wtype == 2 && w_cmb == w_combobox[1]) 
              || w_cmb == w_combobox[2] ) {
          $(w_cmb).append($('<option>', {value: w_name}).text(w_name));
        } else {
          $(w_cmb).append($('<option>', {value: w_name}).text(w_name));
        }
      });
    });
    $('#sel-w-files').prop("selectedIndex", -1);
    $("#btn-create-w").attr("disabled",false).fadeTo(0, 1.0).prev().remove();
    ShowMsgBox("","Create weights done.");
  };
  //////////////////////////////////////////////////////////////
  //  Spatial Regression 
  //////////////////////////////////////////////////////////////
  var prev_obj;
  // save spreg result to datasource
  $('#btn-save-predy').click(function() {
    var count=0, param;
    $('#txt-spreg-predy').children("table").each(function(i,tbl) {
      var content = $(tbl).html().replace(/\<th\>|\<\/th\>|\<tbody\>|\<\/tbody\>|\<tr\>|\<\/tr\>|\<\/td\>/g,"").replace(/\<td\>/g,",");
      if (param == undefined) param = {};
      param["predy" + i] = content;
      count = i;
    });
    var uuid = localStorage['HL_LAYER'];
    if (param && uuid) {
      param["n"] = count+1;
      param["uuid"] = uuid;
  
      $(this).attr("disabled", "disabled");
      $(html_load_img).insertAfter("#btn-save-predy");
    
      $.post("../save_spreg_result/", param, function() {
      }).done( function(result) {
        console.log(result);
      }).always( function() {
        $("#btn-save-predy").next().remove();
        $(html_check_img).insertAfter("#btn-save-predy");
      });
    }
  });
  // save spreg result to csv
  $('#btn-export-predy').on('click', function(event) {
    exportTableToCSV.apply(this, [$('#txt-spreg-predy>table'),'export.csv']);
  });
   // reset Spreg dialog
  var restSpreg = function() {
    $.each($('#x_box li, #y_box li, #ye_box li, #inst_box li, #r_box li'), function(i, v) { $(v).dblclick();});
    $('input[name="model_type"][value="0"]').prop('checked', true)
    $('input[name="method"]').prop('disabled', true)
    $('input[name="method"][value="0"]').prop('checked', true).prop('disabled', false);
    $('input:checkbox[name=stderror]').each(function(i,obj){
      $(obj).prop('checked', false);
    });
  };
  // init Spreg dialg: tabs
  $( "#y_catalog" ).accordion();
  $( "#x_catalog" ).accordion();
  $( "#w_catalog_model" ).accordion();
  $( "#w_catalog_kernel" ).accordion();
  $( "#vars ul li" ).draggable({
    helper: "clone"
  });
  $( ".drop_box ol li" ).dblclick(function() {});
  $( ".drop_box ol" ).droppable({
    activeClass: "ui-state-default",
    hoverClass: "ui-state-hover",
    accept: ":not(div)",
    drop: function( event, ui ) {
      $( this ).find( ".placeholder" ).remove();
      // customized behavior for different dropbox
      var box_id = $(this).closest("div").attr("id");
      var n_items = $(this).children().length;
      if ( n_items > 0) {
        if (box_id === 'y_box'||box_id==='r_box') 
          return; 
      }
      // drop gragged item
      $( "<li></li>" ).text( ui.draggable.text() ).appendTo( this ).dblclick(function(){
        $(this).remove();
        ui.draggable.show();
      });
      ui.draggable.hide();
    }
  }).sortable({
    items: "li:not(.placeholder)",
    sort: function() {
      // gets added unintentionally by droppable interacting with sortable
      // using connectWithSortable fixes this, but doesn't allow you to customize active/hoverClass options
      $( this ).removeClass( "ui-state-default" );
    }
  });

  // model type
  $('input:radio[name=model_type]').click( function() {
    var model_type = $(this).val();
    if ( model_type == 0 ) {
      $("input[name='method'], input[name='stderror']").prop('disabled', false);
      $('#ml, #gmm, #het').prop('disabled', true);
      $('#ols').prop('checked', true);
      $("input[name='stderror']").prop('checked', false);
    } else if ( model_type == 1 ) {
      $("input[name='method'], input[name='stderror']").prop('disabled', false);
      $('#ols, #het').prop('disabled', true);
      $('#gmm').prop('checked', true);
      $("input[name='stderror']").prop('checked', false);
    } else if ( model_type == 2 ) {
      $("input[name='method'], input[name='stderror']").prop('disabled', false);
      $('#ols, #white, #hac').prop('disabled', true);
      $('#gmm').prop('checked', true);
      $("input[name='stderror']").prop('checked', false);
    } else if ( model_type == 3 ) {
      $("input[name='method'], input[name='stderror']").prop('disabled', false);
      $('#ols, #ml, #white, #hac').prop('disabled', true);
      $('#gmm').prop('checked', true);
      $("input[name='stderror']").prop('checked', false);
    }
  });
  $('input:radio[name=model_type]:first').click();

  $( "#dialog-preference" ).dialog({
    height: 400,
    width: 580,
    autoOpen: false,
    modal: true,
    dialogClass: "dialogWithDropShadow",
    buttons: {
      "Restore Defaults": function() {
        $( this ).dialog( "close" );
      },
      "Restore System Defaults": function() {
        $( this ).dialog( "close" );
      },
      Cancel: function() {
        $( this ).dialog( "close" );
      },
      "Save": function() {
        console.log($("#form-pref").serialize());
        $.ajax({
        url: "../save_spreg_p/",
          type: "post",
          data: $("#form-pref").serialize(),
          success: function( data ) {}
        });
      },
    }
  });
  $( "#dialog-spreg-result" ).dialog({
    height: 500,
    width: 800,
    autoOpen: false,
    modal: true,
    dialogClass: "dialogWithDropShadow",
    buttons: {
      Cancel: function() {$( this ).dialog( "close" );},
    }
  });
  
  var options = { valueNames: ['name'] };
  var varList = new List('vars', options);
  
  $( "#dialog-regression" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 900,
    height: 600,
    autoOpen: false,
    modal: true,
  });
    
  $( "#dlg-add-uniqid" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Add": function() {
        var that = $(this);
        var uuid = localStorage.getItem('HL_LAYER');
        if ( uuid ) {
          var name = $('#uniqid_name').val(),
              conti = true;
          $.each($('#sel-w-id').children(), function(i,j) { 
            if( name == $(j).text()) {
              ShowMsgBox("","Input unique ID field already exists.");
              conti = false;
              return;
            }
          })
          if ( conti == true ) {
            params = { 'uuid': uuid, 'name': name};
            $.post("../add_UID/", params, function() {
            }).done(function(data) { 
              console.log("add_uid", data); 
              if (data["success"] == 1) {
                loadFieldNames(function(){
                  $('#sel-w-id').val(name).change()
                });
                that.dialog( "close" );
                ShowMsgBox("", "Add uniue ID successful.");
                ;
              }
            });
          }
        }
      },
      Cancel: function() {$( this ).dialog( "close" );},
    }
  });
  $( "#dlg-save-model" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Save": function() {
        var uuid = localStorage.getItem('HL_LAYER');
        if ( uuid ) {
          var w_list = $.GetValsFromObjs($('#sel-model-w-files :selected'));
          var wk_list = $.GetValsFromObjs($('#sel-kernel-w-files :selected'));
          var model_type = $('input:radio[name=model_type]:checked').val();
          var method = $('input:radio[name=method]:checked').val();
          var name = $('#model_name').val();
          var x = $.GetTextsFromObjs($('#x_box li'));
          var y = $.GetTextsFromObjs($('#y_box li'));
          var ye = $.GetTextsFromObjs($('#ye_box li'));
          var h = $.GetTextsFromObjs($('#inst_box li'));
          var r = $.GetTextsFromObjs($('#r_box li'));
          //var t = $.GetTextsFromObjs($('#t_box li'));
          var t = [];
          var error = [0,0,0];
          $('input:checkbox[name=stderror]').each(function(i,obj){
            if (obj.checked) error[i] = 1;
          });
          params = { 'uuid': uuid, 'name': name, 'w': w_list, 'wk': wk_list, 'type': model_type, 'method': method, 'error': error, 'x': x, 'y': y, 'ye': ye, "h": h, "r": r, "t": t};
          console.log(params);
          
          $.post("../save_spreg_model/", params, function() {
          }).done(function(data) { 
            console.log(data); 
            loadModelNames();
            ShowMsgBox("","Save model done.");
          });
        }
        $(this).dialog("close");
      },
      Cancel: function() {$( this ).dialog( "close" );},
    }
  });
    
  $( "#dlg-open-model" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Open": function() {
        var uuid = localStorage.getItem('HL_LAYER');
        if ( uuid ) {
          var model_name = $('#open_spreg_model').val();
          if (model_name ) {
            $.get("../load_spreg_model/", {'uuid':uuid,'name':model_name}, function(){})
            .done(function(data) {
              console.log(data);
              if ( data["success"] != 1 ) {
                console.log("load spreg model failed.");
              } else {
                resetSpreg();
                $('input[name="model_type"][value='+data['type']+']').prop('checked', true);
                $('input[name="method"][value='+data['method']+']').prop('checked', true);
                var error = data['stderror'];
                $('input:checkbox[name=stderror]').each(function(i,obj){
                  if (error[i] == 1) $(obj).prop('checked', true);
                });
                $.each( data['w'], function(i, w) {$('#sel-model-w-files').val(w);});
                $.each( data['kw'], function(i, w) {$('#sel-kernel-w-files').val(w);});
                var load_vars = function( vars, box ) {
                  $.each( vars, function(i, v) {
                    if ( v && v.length > 0 ) {
                      if (i == 0) box.find( ".placeholder" ).remove();
                      var item = $('#ul-x-variables p').filter(function(i, p){ 
                        return $(p).text() == v;
                      }).parent().hide();
                      var ctn = box.closest("div").children().first();
                      $( "<li></li>" ).text(v).appendTo(ctn).dblclick(function(){
                        $(this).remove();
                        item.show();
                      });
                    }
                  });
                };
                load_vars( data['y'], $('#y_box') );
                load_vars( data['x'], $('#x_box') );
                load_vars( data['ye'], $('#ye_box') );
                load_vars( data['h'], $('#inst_box') );
                load_vars( data['r'], $('#r_box') );
                //load_vars( data['t'], $('#t_box') );
              } 
            });
          }
        }
        $(this).dialog("close");
      },
      Cancel: function() {$( this ).dialog( "close" );},
    },
  });
 $( "#btn_run" ).button({icons: {primary: "ui-icon-circle-triangle-e",}})
  .click(function() {
    if (  viz == undefined ) return;
    var w_list = $.GetValsFromObjs($('#sel-model-w-files :selected'));
    var wk_list = $.GetValsFromObjs($('#sel-kernel-w-files :selected'));
    var model_type = $('input:radio[name=model_type]:checked').val();
    var method = $('input:radio[name=method]:checked').val();
    // y, x, w, 
    var x = $.GetTextsFromObjs($('#x_box li'));
    var y = $.GetTextsFromObjs($('#y_box li'))[0];
    var ye = $.GetTextsFromObjs($('#ye_box li'));
    var h = $.GetTextsFromObjs($('#inst_box li'));
    var r = $.GetTextsFromObjs($('#r_box li'));
    //var t = $.GetTextsFromObjs($('#t_box li'));
    var t = [];
    // check error flag 
    var error = [0,0,0];
    var conti = true;
    $('input:checkbox[name=stderror]').each(function(i,obj){
      if (obj.checked){ 
      error[i] = 1;
        if ( i==1 && w_list.length == 0 ) {
          ShowMsgBox("","Please select weights file for model.");
          conti = false;
          return;
        }
        if ( i==1 && wk_list.length == 0 ) {
          ShowMsgBox("","Please select kernel weights file for model.");
          conti = false;
          return;
        }
      }
    });
    if ( conti == false) return;
    // run model
    $('#dlg-run').dialog("open").html('<img src="img/loading.gif"/><br/>Loading ...');
    $('#dlg-run').siblings('.ui-dialog-titlebar').hide();
    params = {'command': 'spatial_regression', 'wid': winID,
      'uuid': uuid, 'w': w_list, 'wk': wk_list, 
      'type': parseInt(model_type), 'method': parseInt(method), 'error': error, 
      'x': x, 'y': y, 'ye': ye, "h": h, "r": r, "t": t,
    };
    
    viz.RunSpreg(params, OnSpregDone);
    $('#btn_result').hide();
  });
  
  var OnSpregDone = function(msg) {
    if ( msg["success"] == 1) {
      $('#dlg-run').dialog("close");
      if ( msg['report'] ) {
        $('#btn_result').show();
        var predy = "", summary = "", cnt= 0;
        $.each(msg['report'], function(id, result) { 
          cnt+=1;
        });
        cnt = cnt.toString();
        $.each(msg['report'], function(id, result) {
          var idx = parseInt(id) + 1
          summary += "Report " + idx + "/" + cnt + 
            "\n\n"+result['summary'] + "\n\n";
          predy += "<b>Report " + idx + "/" + cnt +"</b><br/><br/>";
          predy += "<table border=1 width=100% id='predy" + id + 
            "'><tr><th>Predicted Values</th><th>Residuals</th></tr>";
          var n = result['predy'][0].length;
          for ( var i=0; i< n; i++ ) {
            predy += "<tr><td>" + result['predy'][0][i] + "</td><td>" + 
              result['residuals'][0][i] + "</td></tr>";
          }
          predy += "</table><br/><br/>";
        });
        $('#txt-spreg-predy').html(predy);
        $('#txt-spreg-summary').text(summary);
      }
      $('#btn_result').popupDiv('#divPop','Click this button to see result.');
    } else {
      $('#dlg-run').dialog("close");
      ShowMsgBox("Erro","Spatial regression failed.");
    }
  };
  
  //////////////////////////////////////////////////////////////
  //   LISA Map
  //////////////////////////////////////////////////////////////
  
  $( "#dlg-lisa-map" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Open": function() {
        if (!viz) return;
        var sel_var = $('#sel-lisa-var').val();
        var sel_w = $('#sel-lisa-w').text();
        if (!sel_w || sel_w.length == 0) {
          ShowMsgBox("Info", "Please select a weights first. Note: You can create a weights by click the weights creation button");
          return;
        }
        var msg = {"command":"new_lisa_map","wid": winID,"uuid":uuid,
        "var": sel_var, "w_name": sel_w};
        viz.NewLISAMap(msg);
        $(this).dialog("close");
      }, 
      Cancel: function() {$( this ).dialog( "close" );},
    },
  });  
  //////////////////////////////////////////////////////////////
  //  Moran Scatter Plot
  //////////////////////////////////////////////////////////////
  
  $( "#dlg-moran-scatter-plot" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Open": function() {
        if (!viz) return;
        var sel_var = $('#sel-moran-var').val();
        var sel_w = $('#sel-moran-w').text();
        if (!sel_w || sel_w.length == 0) {
          ShowMsgBox("Info", "Please select a weights first. Note: You can create a weights by click the weights creation button");
          return;
        }
        var msg = {"command":"new_moran_scatter_plot","wid": winID,"uuid":uuid,
        "var": sel_var, "w_name": sel_w};
        viz.NewMoranScatterPlot(msg);
        $(this).dialog("close");
      }, 
      Cancel: function() {$( this ).dialog( "close" );},
    },
  });
  
  //////////////////////////////////////////////////////////////
  //  Scatter Plot
  //////////////////////////////////////////////////////////////
  
  $( "#dlg-scatter-plot" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Open": function() {
        if (!viz) return;
        var sel_x = $('#sel-scatter-x').val();
        var sel_y = $('#sel-scatter-y').val();
        var msg = {"command":"new_scatter_plot","wid": winID,"uuid":uuid,
        "var_x": sel_x, "var_y": sel_y};
        viz.NewScatterPlot(msg);
        $(this).dialog("close");
      }, 
      Cancel: function() {$( this ).dialog( "close" );},
    },
  });
  
  //////////////////////////////////////////////////////////////
  //  Thematic Map
  //////////////////////////////////////////////////////////////
  
  $( "#dlg-quantile-map" ).dialog({
    dialogClass: "dialogWithDropShadow",
    width: 400,
    height: 200,
    autoOpen: false,
    modal: true,
    buttons: {
      "Open": function() {
        if (!viz) return;
        var sel_method = $('#sel-quan-method').val();
        var sel_var = $('#sel-var').val();
        var sel_cat = $('#quan-cate').val();
        var msg = {"command":"new_choropleth_map","wid": winID,"uuid":uuid,
        "method": sel_method, "var": sel_var, "category": sel_cat};
        viz.NewChoroplethMap(msg);
        $(this).dialog("close");
      }, 
      Cancel: function() {$( this ).dialog( "close" );},
    },
  });
  
  $( "#tabs" ).tabs();
  $( "#spreg-result-tabs" ).tabs();
  
  $( "#btn_open_model" ).button({icons: {primary: "ui-icon-folder-open"}})
  .click(function() {
    $('#dlg-open-model').dialog('open');
  });
  $( "#btn_save_model" ).button({icons: {primary: "ui-icon-disk"}})
  .click(function() {
    $('#dlg-save-model').dialog('open');
  });
  
  $( "#btn_reset_model" ).button({icons: {primary: "ui-icon-)circle-close"}})
  .click(function() { restSpreg(); });
  
  $( "#btn_preference" ).button({icons:{primary: "ui-icon-gear",}})
  .click(function(){ $('#dialog-preference').dialog('open');});
  
  $( "#btn_result" ).button({icons: {primary: "ui-icon-document",}})
  .click(function(){
    $('#dialog-spreg-result').dialog('open').draggable('disable');
  }).hide();
    
  $( "#btn_create_w" ).button({icons: {primary: "ui-icon-plus",}})
  .click(function(){
    $('#dialog-weights').dialog('open');
  });
    
   
});



