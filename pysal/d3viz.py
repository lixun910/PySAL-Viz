import pysal
import os.path
import shutil
import webbrowser
import json
from websocket import create_connection
import shapefile

__author__='Xun Li <xunli@asu.edu>'
__all__=[]

WS_SERVER = "ws://localhost:9000"
default_work_dir = "./temp"

def setup(ws_address):
    global WS_SERVER
    WS_SERVER = ws_address

def shp2json(shp):
    reader = shapefile.Reader(shp.dataPath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    buffer = []
    for sr in reader.shapeRecords():
        atr = dict(zip(field_names, sr.record))
        geom = sr.shape.__geo_interface__
        buffer.append(dict(type="Feature", geometry=geom, properties=atr))
    
    return {"type": "FeatureCollection","features": buffer}

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
    msg = {
        "command": "add_layer",
        "content": {
            "uuid" : "abcdeft",
            "data" : data,
        }
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    print "send:", str_msg
    layer_uuid = ws.recv()
    print "receive:", layer_uuid
    ws.close()
    
# Test
shp = pysal.open(pysal.examples.get_path('columbus.shp'),'r')
show_map(shp)
#get_selected(shp)
#select(shp, [])

#show_table(shp)
#show_fields(shp)
#quantile_map(shp, var="crime", quantile=5)
    
    
    