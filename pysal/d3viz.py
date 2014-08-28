import pysal
import numpy as np
import os.path
import json, shutil, webbrowser, md5
from uuid import uuid4
from websocket import create_connection
import shapefile

__author__='Xun Li <xunli@asu.edu>'
__all__=[]

WS_SERVER = "ws://localhost:9000"
SHP_DICT = {}

def setup(ws_address):
    global WS_SERVER
    WS_SERVER = ws_address

def getuuid(shp):
    """
    Generate UUID using absolute path of shapefile
    """
    return md5.md5(shp.dataPath).hexdigest()
    
def shp2json(shp):
    """
    Create a GeoJson file from pysal.shp object and store it in www/ path.
    Which can be visited using http://localhost:8000/*.json
    """
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
        
    global SHP_DICT
    if not shp in SHP_DICT:
        SHP_DICT[shp] = getuuid(shp)
    uuid = SHP_DICT[shp]
    
    current_path = os.path.realpath(__file__)    
    www_path = "%s/../www/%s.json" % \
        (current_path[0:current_path.rindex('/')], uuid)
   
    if not os.path.exists(www_path): 
        geojson = open(www_path, "w")
        geojson.write(json.dumps({"type": "FeatureCollection","features": buffer}))
        geojson.close()

def lzwJson(json):
    codes = dict([(chr(x), x) for x in range(256)])
    compressed_data = []
    code_count = 257
    current_string = ""
    for c in json:
        current_string = current_string + c
        if not (codes.has_key(current_string)):
            codes[current_string] = code_count
            compressed_data.append( codes[current_string[:-1]])
            code_count += 1
            current_string = c
    compressed_data.append( codes[current_string])
    return compressed_data

def show_map(shp):
    """
    Ideally, users need to open and process shapefile using:
    >>>> shp = pysal.open(pysal.examples.get_path('columbus.shp'),'r')
    
    then, users can call 
    
    >>>> layer_uuid = pysal.contrib.d3viz.show_map(shp) 
   
    to bring up a browser for showing the map.
    For further usage, e.g. create a quantile map, users need to call the 
    command with the uuid to specify the data.
    
    >>>> pysal.contrib.d3viz.quantile_map(layer_uuid, {'var':'T'..})
    
    To create a scatter plot, users need to 
    """
    #url = "http://127.0.0.1:8000/%s" % "index.html"
    #webbrowser.open_new(url)
     
    data = shp2json(shp)
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    global SHP_DICT
    uuid = SHP_DICT[shp]
    
    msg = {
        "command": "add_layer",
        "uuid": uuid,
        "data" : data,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
    ws.close()
    
def get_selected(shp):
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
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
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
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
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
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
    ws.close()

def lisa_map(shp, var, w):
    y = dbf.by_col[var]
    lm = pysal.Moran_Local(np.array(y), w)
     
    bins = ["Not Significant","High-High","Low-High","Low-Low","Hight-Low"]
    id_array = []
    for j in range(5): 
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
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
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
    print "send:", str_msg
    rsp = ws.recv()
    print "receive:", rsp
    ws.close()
    
# Test
shp = pysal.open(pysal.examples.get_path('NAT.shp'),'r')
dbf = pysal.open(pysal.examples.get_path('NAT.dbf'),'r')
show_map(shp)

quantile_map(shp, dbf, "HC60", 5, basemap="leaflet_map")

#ids = get_selected(shp)
#print ids

select_ids = [i for i,v in enumerate(dbf.by_col["HC60"]) if v < 20.0]
select(shp, ids=select_ids)


quantile_map(shp, dbf, "HC60", 5)


w = pysal.rook_from_shapefile(pysal.examples.get_path('NAT.shp'))
lisa_map(shp, "HC60", w)

scatter_plot_matrix(shp, ["HC60", "HC70"])
    
#show_table(shp)
    
    