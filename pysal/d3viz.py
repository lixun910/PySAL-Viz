import pysal
import numpy as np
import os.path
import json, shutil, webbrowser, md5, subprocess, re
from uuid import uuid4
from websocket import create_connection
import shapefile

__author__='Xun Li <xunli@asu.edu>'
__all__=['clean_ports','setup','getuuid','shp2json','show_map','get_selected', 'select','quantile_map','lisa_map','scatter_plot_matrix']

WS_SERVER = "ws://localhost:9000"
SHP_DICT = {}

def clean_ports():
    ports = ['9000','8000']
    for p in ports:
        popen = subprocess.Popen(['lsof -n -i4TCP:%s | grep LISTEN'%p],
                                 shell=True,
                                 stdout=subprocess.PIPE)
        (data, err) = popen.communicate()
        if data:
            pid = data.split()[1]
            subprocess.Popen(['kill', '-9', pid])
            
def setup(restart=True):
    if restart:
        clean_ports()
        current_path = os.path.realpath(__file__)    
        
        print "starting websocket server..."
        script = "python %s/../ws_server/start_ws_server.py" % \
            (current_path[0:current_path.rindex('/')])
        subprocess.Popen([script], shell=True)
        
        print "starting http server..."
        loc = current_path[0:current_path.rindex('/')]
        script = "cd %s/../www/ && python %s/../www/start_http_server.py" % \
            (loc, loc)
        subprocess.Popen([script], shell=True)
        
    from time import sleep
    sleep(1)
    url = "http://127.0.0.1:8000/index.html"
    webbrowser.open_new(url)
    
def getuuid(shp):
    """
    Generate UUID using absolute path of shapefile
    """
    return md5.md5(shp.dataPath).hexdigest()
    
def shp2json(shp,rebuild=False):
    """
    Create a GeoJson file from pysal.shp object and store it in www/ path.
    Which can be visited using http://localhost:8000/*.json
    """
    global SHP_DICT
    if not shp in SHP_DICT:
        SHP_DICT[shp] = getuuid(shp)
    uuid = SHP_DICT[shp]
    
    print "creating geojson ..."
    current_path = os.path.realpath(__file__)    
    www_path = "%s/../www/%s.json" % \
        (current_path[0:current_path.rindex('/')], uuid)
   
    if not os.path.exists(www_path) or rebuild==True: 
        print "reading data ..."
        reader = shapefile.Reader(shp.dataPath)
        fields = reader.fields[1:]
        field_names = [field[0] for field in fields]
        buffer = []
        for i, sr in enumerate(reader.shapeRecords()):
            field_names.append("GEODAID")
            sr.record.append(i)
            atr = dict(zip(field_names, sr.record))
            geom = sr.shape.__geo_interface__
            buffer.append(dict(type="Feature", geometry=geom, properties=atr))
        
        geojson = open(www_path, "w")
        geojson.write(json.dumps({"type": "FeatureCollection","features": buffer}))
        geojson.close()
    else:
        print "The geojson data has been created before. If you want re-create geojson data, please call shp2json(shp, rebuild=True)."

def open_web_portal(shp):
    global SHP_DICT
    if not shp in SHP_DICT:
        # Open a new web portal since this map is newly opened.
        pass
    else:
        # Check if this map has already been opened in a web portal
        uuid = SHP_DICT[shp]
        global WS_SERVER 
        ws = create_connection(WS_SERVER)
        msg = {
            "command": "check_active",
            "uuid": uuid
        }
        str_msg = json.dumps(msg)
        ws.send(str_msg)
        print "send:", str_msg
        rsp = ws.recv()
        print "receive:", rsp
        ws.close()
        rsp = json.loads(rsp)
        if rsp["response"] == "FAIL":
            pass
    
    
def show_map(shp):
    """
    Ideally, users need to open and process shapefile using:
    >>>> shp = pysal.open(pysal.examples.get_path('columbus.shp'),'r')
    
    then, users can call 
    
    >>>> pysal.contrib.d3viz.show_map(shp) 
   
    to bring up a browser for showing the map.
    For further usage, e.g. create a quantile map, users need to call the 
    command with the uuid to specify the data.
    
    >>>> pysal.contrib.d3viz.quantile_map(shp, 'var', 5)
    
    To create a scatter plot, users need to 
    """
    shp2json(shp)
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    global SHP_DICT
    uuid = SHP_DICT[shp]
    
    msg = {
        "command": "add_layer",
        "uuid": uuid,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    print "send:", str_msg
    ws.close()
    
def get_selected(shp):
    """
    Get shape object ids from web pages.
    """
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "get_selected",
        "uuid":  uuid,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    print "receiving..."
    rsp = ws.recv()
    ws.close()
    
    msg = json.loads(rsp)
    ids = msg["ids"].strip().split(",")
    ids = [int(id) for id in ids]
    return ids
    
def select(shp, ids=[]):
    if len(ids) == 0:
        return
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "select",
        "uuid":  uuid,
        "data": ids
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def quantile_map(shp, dbf, var, k, basemap=None):
    y = dbf.by_col[var]
    q = pysal.esda.mapclassify.Quantiles(np.array(y), k=k)    
    bins = q.bins
    id_array = []
    for i, upper in enumerate(bins):
        if i == 0: 
            id_array.append([j for j,v in enumerate(y) if v <= upper])
        else:
            id_array.append([j for j,v in enumerate(y) \
                             if bins[i-1] < v <= upper])
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "quantile_map",
        "uuid":  uuid,
        "title": "Quantile map for variable [%s], k=%d" %(var, len(id_array)),
        "bins": bins.tolist(),
        "data": id_array,
    }
    if basemap:
        msg["basemap"] = basemap
        
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()

def lisa_map(shp, dbf, var, w):
    y = dbf.by_col[var]
    lm = pysal.Moran_Local(np.array(y), w)
     
    bins = ["Not Significant","High-High","Low-High","Low-Low","Hight-Low"]
    id_array = []
    id_array.append([i for i,v in enumerate(lm.p_sim) \
                     if lm.p_sim[i] >= 0.05])
    for j in range(1,5): 
        id_array.append([i for i,v in enumerate(lm.q) \
                         if v == j and lm.p_sim[i] < 0.05])
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "lisa_map",
        "uuid":  uuid,
        "title": "LISA map for variable [%s], w=%s" %(var, ".gal"),
        "bins": bins,
        "data": id_array,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def moran_scatter_plot(shp, dbf, var, w):
    y = np.array(dbf.by_col[var])
    y_lag = pysal.lag_spatial(w, y)
   
    y = (y - y.mean()) / y.std()
    y_lag = (y_lag - y_lag.mean()) / y_lag.std()
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "moran_scatter_plot",
        "uuid":  uuid,
        "title": "Moran Scatter plot for variables [%s]" % var,
        "data": {
        },
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def scatter_plot(shp, fields):
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "scatter_plot",
        "uuid":  uuid,
        "title": "Scatter plot matrix for variables [%s]" %(",".join(fields)),
        "fields": fields,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def scatter_plot_matrix(shp, fields):
    
    global SHP_DICT 
    uuid = SHP_DICT[shp]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "scatter_plot_matrix",
        "uuid":  uuid,
        "title": "Scatter plot matrix for variables [%s]" %(",".join(fields)),
        "fields": fields,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def test():
    # Test
    setup()
    shp = pysal.open(pysal.examples.get_path('NAT.shp'),'r')
    dbf = pysal.open(pysal.examples.get_path('NAT.dbf'),'r')
    show_map(shp)
    
    scatter_plot(shp, ["HR90", "PS90"])
    
    quantile_map(shp, dbf, "HC60", 5, basemap="leaflet_map")
    
    #ids = get_selected(shp)
    #print ids
    
    select_ids = [i for i,v in enumerate(dbf.by_col["HC60"]) if v < 20.0]
    select(shp, ids=select_ids)
    
    
    quantile_map(shp, dbf, "HC60", 5)
    
    
    w = pysal.rook_from_shapefile(pysal.examples.get_path('NAT.shp'))
    lisa_map(shp, dbf, "HC60", w)
    
    scatter_plot_matrix(shp, ["HC60", "HC70"])
        
    #show_table(shp)
        
test() 