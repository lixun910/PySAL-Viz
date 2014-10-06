import pysal
import numpy as np
import os.path
import json, shutil, webbrowser, md5, subprocess, re, threading, sys
from uuid import uuid4
from websocket import create_connection
import shapefile
import zipfile
import urllib2, urllib
from rdp import rdp
from network_cluster import NetworkCluster

__author__='Xun Li <xunli@asu.edu>'
__all__=['clean_ports','setup','getuuid','shp2json','show_map','get_selected', 'select','quantile_map','lisa_map','scatter_plot_matrix']

PORTAL = "index.html"
WS_SERVER = "ws://localhost:9000"
R_SHP_DICT = {}


YLRD=  {
    3: ["#ffeda0","#feb24c","#f03b20"],
    4: ["#ffffb2","#fecc5c","#fd8d3c","#e31a1c"],
    5: ["#ffffb2","#fecc5c","#fd8d3c","#f03b20","#bd0026"],
    6: ["#ffffb2","#fed976","#feb24c","#fd8d3c","#f03b20","#bd0026"],
    7: ["#ffffb2","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c","#b10026"],
    8: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c","#b10026"],
    9: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c","#bd0026","#800026"]
}
CARTO_CSS_POINT_CLOUD = ('#layer {'
                   'first/marker-fill: #0011cc;'
                   'first/marker-opacity: 0.02; '
                   'first/marker-width: 60; '
                   'first/marker-line-width: 0; '
                   'first/marker-placement: point; '
                   'first/marker-allow-overlap: true; '
                   'first/marker-comp-op: lighten; '
                   'second/marker-fill: #00cc11; '
                   'second/marker-opacity: 0.05; '
                   'second/marker-width:50; '
                   'second/marker-line-width: 0; '
                   'second/marker-placement: point; '
                   'second/marker-allow-overlap: true; '
                   'second/marker-comp-op: lighten; '
                   'third/marker-fill: #00ff00; '
                   'third/marker-opacity: 0.1; '
                   'third/marker-width:20; '
                   'third/marker-line-width: 0; '
                   'third/marker-placement: point; '
                   'third/marker-allow-overlap: true; '
                   'third/marker-comp-op: lighten;}' )
    
CARTO_CSS_INVISIBLE = '#layer {polygon-opacity: 0;}'
                  
CARTO_CSS_LISA = ('#layer { '
                  'polygon-fill: #FFF; '
                  'polygon-opacity: 0.5; '
                  'line-color: #CCC; } '
                  '#layer[lisa="1"]{polygon-fill: red;}'
                  '#layer[lisa="2"]{polygon-fill: lightsalmon;}'
                  '#layer[lisa="3"]{polygon-fill: blue;}'
                  '#layer[lisa="4"]{polygon-fill: lightblue;}')
    
class AnswerMachine(threading.Thread):
    """
    Handle commands sent from Web Pages
    """
    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent
        global WS_SERVER 
        self.ws = create_connection(WS_SERVER)
        
    def run(self):
        from weights_dispatcher import CreateWeights
        from gs_dispatcher import Spmodel, DEFAULT_SPREG_CONFIG
        print "[Answering] running..." 
        global R_SHP_DICT
        count = 1
        while True:
            rsp = self.ws.recv()
            print "[Answering] " + rsp
            try:
                msg = json.loads(rsp)
                uuid = msg["uuid"]
                command = msg["command"]
                if command == "new_data":
                    path = msg["path"]
                    ext = path.split(".")[-1]
                    if ext == "shp":
                        dbf_path = path[:-3] + "dbf"
                        shp = pysal.open(path,'r')
                        dbf = pysal.open(dbf_path, 'r')
                        
                        if not uuid in R_SHP_DICT:
                            R_SHP_DICT[uuid] = {}
                        R_SHP_DICT[uuid]["shp"] = shp
                        R_SHP_DICT[uuid]["dbf"] = dbf
                        R_SHP_DICT[uuid]["shp_path"] = path
                        
                        self.parent.show_map(shp)
                    
                elif command == "new_quantile_map":
                    uuid = msg["uuid"]
                    var = msg["var"]
                    cat = msg["category"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    dbf = R_SHP_DICT[uuid]["dbf"]
                    
                    self.parent.quantile_map(shp, var, cat)
                    
                elif command == "create_w":
                    uuid = msg["uuid"]
                    parameters = msg["parameters"]
                    w_id = parameters["w_id"] \
                        if "w_id" in parameters else None
                    w_name = parameters["w_name"] \
                        if "w_name" in parameters else None
                    w_type = parameters["w_type"] \
                        if "w_type" in parameters else None
                    cont_type = parameters["cont_type"] \
                        if "cont_type" in parameters else None
                    cont_order = parameters["cont_order"] \
                        if "cont_order" in parameters else None
                    cont_ilo = parameters["cont_ilo"] \
                        if "cont_ilo" in parameters else None
                    dist_metric = parameters["dist_metric"] \
                        if "dist_metric" in parameters else None
                    dist_method = parameters["dist_method"] \
                        if "dist_method" in parameters else None
                    dist_value = parameters["dist_value"] \
                        if "dist_value" in parameters else None
                    kernel_type = parameters["kernel_type"] \
                        if "kernel_type" in parameters else None
                    kernel_nn = parameters["kernel_nn"] \
                        if "kernel_nn" in parameters else None
                    
                    shp_path = R_SHP_DICT[uuid]["shp_path"]
                    w = CreateWeights(shp_path, w_name, w_id, w_type,\
                                      cont_type = cont_type,
                                      cont_order = cont_order,
                                      cont_ilo = cont_ilo,
                                      dist_metric = dist_metric, 
                                      dist_method = dist_method,
                                      dist_value = dist_value,
                                      kernel_type = kernel_type,
                                      kernel_nn = kernel_nn)                    
                    
                    if not "weights" in R_SHP_DICT[uuid]:
                        R_SHP_DICT[uuid]["weights"] = {}
                    R_SHP_DICT[uuid]["weights"][w_name] = w
                    
                    self.ws.send('{"command":"rsp_create_w","success":1}')
                
                elif command == "spatial_regression":
                    uuid = msg["uuid"] 
                    w_model = msg["w"]  if "w" in msg else []
                    w_kernel = msg["wk"] if "wk" in msg else []
                    model_type = msg["type"] if "type" in msg else None
                    model_method = msg["method"] if "method" in msg else None 
                    error = msg["error"] if "error" in msg else None 
                    if len(error) == 0: error = [0, 0, 0]
                    white = int(error[0])
                    hac = int(error[0])
                    kp_het = int(error[2])
                    name_y = msg["y"] if "y" in msg else None
                    name_x = msg["x"] if "x" in msg else None
                    name_ye = msg["ye"] if "ye" in msg else None
                    name_h = msg["h"] if "h" in msg else None
                    name_r = msg["r"] if "r" in msg else None
                    name_t = msg["t"] if "t" in msg else None
                   
                    if not uuid and not name_y and not name_x \
                        and model_type not in [0,1,2,3] and \
                        model_method not in [0,1,2]:
                        self.ws.send('{"command":"rsp_spatial_regression","success":0}')
                    else: 
                        # These options are not available yet....
                        s = None
                        name_s = None
                        mtypes = {0: 'Standard', 1: 'Spatial Lag', 2: 'Spatial Error', \
                                  3: 'Spatial Lag+Error'}   
                        model_type = mtypes[model_type]
                        method_types = {0: 'ols', 1: 'gm', 2: 'ml'}
                        method = method_types[model_method]
                        w_list = [R_SHP_DICT[uuid]["weights"][w_name] for w_name in w_model]
                        wk_list = [R_SHP_DICT[uuid]["weights"][w_name] for w_name in w_kernel]
                        LM_TEST = False
                        if len(w_list) > 0 and model_type in ['Standard', 'Spatial Lag']:
                            LM_TEST = True
                            
                        dbf = R_SHP_DICT[uuid]["dbf"]
                        shp_path = R_SHP_DICT[uuid]["shp_path"]
                        
                        y = np.array([dbf.by_col(name_y)]).T
                        ye = np.array([dbf.by_col(name) for name in name_ye]).T if name_ye else None
                        x = np.array([dbf.by_col(name) for name in name_x]).T
                        h = np.array([dbf.by_col(name) for name in name_h]).T if name_h else []
                        r = np.array(dbf.by_col(name_r)) if name_r else None
                        t = np.array(dbf.by_col(name_t)) if name_t else None
                       
                        config = DEFAULT_SPREG_CONFIG
                        predy_resid = None # not write to file
                        models = Spmodel(
                            name_ds=shp_path,
                            w_list=w_list,
                            wk_list=wk_list,
                            y=y,
                            name_y=name_y,
                            x=x,
                            name_x=name_x,
                            ye=ye,
                            name_ye=name_ye,
                            h=h,
                            name_h=name_h,
                            r=r,
                            name_r=name_r,
                            s=s,
                            name_s=name_s,
                            t=t,
                            name_t=name_t,
                            model_type=model_type,  # data['modelType']['endogenous'],
                            # data['modelType']['spatial_tests']['lm'],
                            spat_diag=LM_TEST,
                            white=white,
                            hac=hac,
                            kp_het=kp_het,
                            # config.....
                            sig2n_k_ols=config['sig2n_k_ols'],
                            sig2n_k_tsls=config['sig2n_k_2sls'],
                            sig2n_k_gmlag=config['sig2n_k_gmlag'],
                            max_iter=config['gmm_max_iter'],
                            stop_crit=config['gmm_epsilon'],
                            inf_lambda=config['gmm_inferenceOnLambda'],
                            comp_inverse=config['gmm_inv_method'],
                            step1c=config['gmm_step1c'],
                            instrument_lags=config['instruments_w_lags'],
                            lag_user_inst=config['instruments_lag_q'],
                            vc_matrix=config['output_vm_summary'],
                            predy_resid=predy_resid,
                            ols_diag=config['other_ols_diagnostics'],
                            moran=config['other_residualMoran'],
                            white_test=config['white_test'],
                            regime_err_sep=config['regimes_regime_error'],
                            regime_lag_sep=config['regimes_regime_lag'],
                            cores=config['other_numcores'],
                            ml_epsilon=config['ml_epsilon'],
                            ml_method=config['ml_method'],
                            ml_diag=config['ml_diagnostics'],
                            method=method
                        ).output
                        model_result = {} 
                        for i,model in enumerate(models):
                            model_id = i
                            #if len(w_list) == len(models):
                            #    model_id = w_list[i].name
                            model_result[model_id] = {'summary':model.summary,'predy':model.predy.T.tolist(),'residuals':model.u.T.tolist()}
                        result = {}
                        result['report'] = model_result
                        result['success'] = 1                        
                        result['command'] = 'rsp_spatial_regression'
                        self.ws.send(json.dumps(result))
            except:
                pass
        print "[Answering] exiting..." 
        
def list_shp():
    global R_SHP_DICT
    return R_SHP_DICT.keys()

def get_json_path(shp):
    uuid = getuuid(shp)
    return R_SHP_DICT[uuid]["json"]
    
def get_shp(uuid):
    global R_SHP_DICT
    if uuid in R_SHP_DICT.keys():
        return R_SHP_DICT[uuid]["shp"]
    print "uuid not exists."
    return None

def get_dbf(uuid):
    global R_SHP_DICT
    if uuid in R_SHP_DICT.keys():
        return R_SHP_DICT[uuid]["dbf"]
    print "uuid not exists."
    return None

def clean_ports():
    ports = ['9000','8000']
    if sys.platform == 'win32':
        for p in ports:
            popen = subprocess.Popen('netstat -ano | findstr %s'%p,
                                     shell=True,
                                     stdout=subprocess.PIPE)
            (data, err) = popen.communicate()
            if data:
                pid = data.split()[4]
                subprocess.Popen('TaskKill /F /PID %s' % pid, shell=True)
    else:
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
        base_path = os.path.split(current_path)[0]
        ws_path = os.path.join(base_path, "..", "ws_server", "start_ws_server.py")
        if sys.platform == 'win32':
            subprocess.Popen([sys.executable, ws_path], shell=True)
        else:
            subprocess.Popen(["python %s"%ws_path], shell=True)
        
        print "starting http server..."
        www_path = os.path.join(base_path, "..", "www")
        http_path = os.path.join(base_path, "..", "www", "start_http_server.py")
        if sys.platform == 'win32':
            os.chdir(www_path)
            subprocess.Popen([sys.executable, http_path], shell=True)
        else:
            script = "cd %s && python %s" % (www_path, http_path)
            subprocess.Popen([script], shell=True)
        
    from time import sleep
    sleep(1)
    global PORTAL
    url = "http://127.0.0.1:8000/%s" % PORTAL
    webbrowser.open_new(url)
    
def getuuid(shp):
    """
    Generate UUID using absolute path of shapefile
    """
    return md5.md5(shp.dataPath).hexdigest()
   
def json2shp(uuid, json_path):
    global R_SHP_DICT
    if uuid in SHP_DICT:
        return
       
    print "creating shp from geojson..." 
    
def shp2json(shp, rebuild=False, uuid=None):
    """
    Create a GeoJson file from pysal.shp object and store it in www/ path.
    Which can be visited using http://localhost:8000/*.json
    """
    if uuid == None:
        uuid = getuuid(shp)
    
    global R_SHP_DICT
    if uuid not in R_SHP_DICT:
        R_SHP_DICT[uuid] = {"shp":None, "dbf":None,"json":None, "shp_path":""}
        dbf = pysal.open(shp.dataPath[:-3]+"dbf") 
        R_SHP_DICT[uuid]["shp"] = shp
        R_SHP_DICT[uuid]["dbf"] = dbf
        R_SHP_DICT[uuid]["shp_path"] = shp.dataPath
    
    print "creating geojson ..."
    current_path = os.path.realpath(__file__)    
    base_path = os.path.split(current_path)[0]
    www_path = os.path.join(base_path, "..", "www", "tmp", "%s.json" % uuid)
   
    R_SHP_DICT[uuid]["json"] = www_path
    
    if not os.path.exists(www_path) or rebuild==True: 
        print "reading data ..."
        buffer = []
        reader = shapefile.Reader(shp.dataPath)
        fields = reader.fields[1:]
        field_names = [field[0] for field in fields]
        try:
            for i, sr in enumerate(reader.shapeRecords()):
                field_names.append("GEODAID")
                sr.record.append(i)
                atr = dict(zip(field_names, sr.record))
                geom = sr.shape.__geo_interface__
                buffer.append(dict(type="Feature", geometry=geom, properties=atr))
        except:
            field_names = dbf.header
            for i, geom in enumerate(shp):
                atr = dict(zip(field_names, dbf[i][0]))
                atr["GEODAID"] = i
                geo = geom.__geo_interface__
                buffer.append(dict(type="Feature", geometry=geo, properties=atr))
            
        geojson = open(www_path, "w")
        geojson.write(json.dumps({"type": "FeatureCollection","features": buffer}))
        geojson.close()
    else:
        print "The geojson data has been created before. If you want re-create geojson data, please call shp2json(shp, rebuild=True)."

def show_map(shp, rebuild=False, uuid=None):
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
    shp2json(shp, rebuild=rebuild, uuid=uuid)
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    if uuid == None: 
        uuid = getuuid(shp)
    
    msg = {
        "command": "add_layer",
        "uuid": uuid,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    print "send:", str_msg
    ws.close()
    
def close_all():
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "close_all",
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    print "receiving..."
    rsp = ws.recv()
    ws.close()
    
def get_selected(shp,uuid=None):
    """
    Get shape object ids from web pages.
    """
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    
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
    ids = [int(id) for id in ids if id != '']
    return ids
    
def select(shp, ids=[], uuid=None):
    if len(ids) == 0:
        return
    if uuid == None: 
        uuid = getuuid(shp)
    
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
    
def quantile_map(shp, var, k, basemap=None, uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    dbf = R_SHP_DICT[uuid]['dbf']
    
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
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    y = dbf.by_col[var]
    lm = pysal.Moran_Local(np.array(y), w)
     
    bins = ["Not Significant","High-High","Low-High","Low-Low","Hight-Low"]
    id_array = []
    id_array.append([i for i,v in enumerate(lm.p_sim) \
                     if lm.p_sim[i] >= 0.05])
    for j in range(1,5): 
        id_array.append([i for i,v in enumerate(lm.q) \
                         if v == j and lm.p_sim[i] < 0.05])
    
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
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    y = np.array(dbf.by_col[var])
    y_lag = pysal.lag_spatial(w, y)
   
    y_z = (y - y.mean()) / y.std()
    y_lag_z = (y_lag - y_lag.mean()) / y_lag.std()
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "moran_scatter_plot",
        "uuid":  uuid,
        "title": "Moran Scatter plot for variable [%s]" % var,
        "data": { "x": y_z.tolist(), "y" : y_lag_z.tolist() },
        "fields": [var, "lagged %s" % var]
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def scatter_plot(shp, fields):
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    
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
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    
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
    
def start_webportal():
    global PORTAL
    PORTAL = "portal.html"
    setup()
    am = AnswerMachine(sys.modules[__name__])
    am.start()
    
CARTODB_API_KEY = '340808e9a453af9680684a65990eb4eb706e9b56'
CARTODB_DOMAIN = 'lixun910'

def setup_cartodb(api_key, user):
    global CARTODB_API_KEY, CARTODB_USER
    CARTODB_API_KEY = api_key
    CARTODB_USER = user

def cartodb_get_data(table_name, fields=[],loc=None):
    fields_str = '*'
    if len(fields) > 0:
        if "the_geom" not in fields:
            fields.append("the_geom")
        fields_str = ", ".join(fields)
    global CARTODB_API_KEY, CARTODB_DOMAIN
    sql = 'select %s from %s' % (fields_str, table_name)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'format': 'shp' ,
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    req = urllib2.Request(url, urllib.urlencode(params))
    response = urllib2.urlopen(req)
    content = response.read()
   
    if loc == None: 
        loc = os.path.realpath(__file__)    
        loc = os.path.split(loc)[0]
        loc = os.path.split(loc)[0]
        loc = os.path.join(loc, "www", "tmp")
    ziploc = os.path.join(loc, "tmp.zip")
    
    o = open(ziploc, "wb")
    o.write(content)
    o.close()
    
    zf = zipfile.ZipFile(ziploc)
    zf.extractall(loc)
    
    for filename in os.listdir(loc):
        if filename.startswith("cartodb-query"):
            os.rename(loc+filename, loc+table_name + filename[-4:])
    return loc + table_name + ".shp"

def cartodb_get_mapid():
    global CARTODB_API_KEY, CARTODB_DOMAIN
    url = 'https://%s.cartodb.com/api/v1/map/named/mytest2' % CARTODB_DOMAIN
    params = {
        'api_key': CARTODB_API_KEY,
    }
    req = urllib2.Request(url, urllib.urlencode(params))
    response = urllib2.urlopen(req)
    content = response.read()    
    
def cartodb_show_maps(shp, css=None, uuid=None, layers=[]):
    base_table = uuid
    if base_table == None:
        base_table = getuuid(shp)
        
    tables = []
    table = {'name':base_table, 'type':cartodb_get_geomtype(shp)}
    if css:
        table["css"] = css
    tables.append(table)        
    
    for layer in layers:
        table_name = getuuid(layer['shp'])
        table = {'name':table_name, 'type':cartodb_get_geomtype(layer)}
        if 'css' in layer:
            css = layer['css']
            table["css"] = css            
        tables.append(table)
    cartodb_show_tables(tables)

def cartodb_show_tables(tables):
    default_cartocss = {}
    default_cartocss['poly'] = ('#layer {'
        'polygon-fill: green; '
        'polygon-opacity: 0.8; '
        'line-color: #CCC; }')
    default_cartocss['line'] = ('#layer {'
        'line-width: 2; '
        'line-opacity: 0.8; '
        'line-color: #FF6600; }')
    default_cartocss['point'] = ('#layer { '
         'marker-fill: #FF6600; marker-opacity: 1; marker-width: 6;'
         'marker-line-color: white; marker-line-width: 1; '
         'marker-line-opacity: 0.9; marker-placement: point; '
         'marker-type: ellipse; marker-allow-overlap: true;}')
    sublayers = []
    for table in tables:
        name = table["name"] 
        sql = 'SELECT * FROM %s' % name
        if 'sql' in table:
            sql = table['sql']
        geotype = table["type"]
        css = default_cartocss[geotype]
        if 'css' in table:
            css = table['css']
        sublayer = {'sql':sql, 'cartocss': css, 'interactivity':'cartodb_id'}
        sublayers.append(sublayer)
    uuid = tables[0]["name"].split("_")[-1]
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "cartodb_mymap",
        "uuid": uuid,
        "sublayers": json.dumps(sublayers),
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
 
def cartodb_drop_table(table_name):
    import requests
    # delete existing lisa_table 
    sql = 'DROP TABLE %s' % (table_name)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    r = requests.get(url, params=params, verify=False)
    content = r.json()    
   
def cartodb_lisa(local_moran, new_lisa_table):
    import StringIO
    lisa = local_moran.q
    for i,v in enumerate(local_moran.p_sim):
        if local_moran.p_sim[i] >= 0.05:
            lisa[i] = 0
    loc = os.path.realpath(__file__)    
    loc = os.path.split(loc)[0]
    loc = os.path.split(loc)[0]
    loc = os.path.join(loc, "www", "tmp")
    
    csv_loc = os.path.join(loc, new_lisa_table + ".csv" )
    csv = open(csv_loc, "w")
    csv.write("cartodb_id, lisa\n")
    for i,v in enumerate(lisa):
        csv.write("%s,%s\n" % (i, v))
    csv.close()
    # create zip file for uploading
    zp_loc =  os.path.join(loc, "upload.zip")
    try:
        os.remove(zp_loc)
    except:
        pass
    os.chdir(loc)
    zp = zipfile.ZipFile("upload.zip","w")
    zp.write(new_lisa_table+".csv")
    zp.close()

    import requests
    # delete existing lisa_table 
    cartodb_drop_table(new_lisa_table)
    
    # upload new_lisa_table : none-geometry table
    import_url = "https://%s.cartodb.com/api/v1/imports/?api_key=%s" % \
        (CARTODB_DOMAIN, CARTODB_API_KEY)
    r = requests.post(import_url, files={'file':open(zp_loc, 'rb')}, verify=False)
    data = r.json()
    
    complete = False
    last_state = ''
    while not complete: 
        import_url = "https://%s.cartodb.com/api/v1/imports/%s?api_key=%s" %\
            (CARTODB_DOMAIN, data['item_queue_id'], CARTODB_API_KEY)
        req = urllib2.Request(import_url)
        response = urllib2.urlopen(req)
        d = json.loads(str(response.read()))
        if last_state!=d['state']:
            last_state=d['state']
            if d['state']=='uploading':
                print 'Uploading file...'
            elif d['state']=='importing':
                print 'Importing data...'
            elif d['state']=='complete':
                complete = True
                print 'Table "%s" created' % d['table_name']
        if d['state']=='failure':
            print d['get_error_text']['what_about']
    return d['table_name']
            
def cartodb_get_geomtype(shp):
    geotype = shp.type
    if geotype == pysal.cg.shapes.Polygon:
        geotype = 'poly'
    elif geotype == pysal.cg.shapes.LineSegment or geotype == pysal.cg.Chain:
        geotype = 'line'
    elif geotype == pysal.cg.shapes.Point:
        geotype = 'point'
    return geotype
    
def cartodb_quantile_map(shp, var, k, uuid=None):
    table = uuid
    if table == None:
        table = getuuid(shp)
       
    dbf = R_SHP_DICT[table]['dbf']
    y = dbf.by_col[var]
    q = pysal.esda.mapclassify.Equal_Interval(np.array(y), k=k)    
    bins = q.bins
    n = len(bins)   
    colors = YLRD[n]
    geotype = shp.type
    if geotype == pysal.cg.shapes.Polygon:
        geotype = 'poly'
    elif geotype == pysal.cg.shapes.LineSegment or geotype == pysal.cg.Chain:
        geotype = 'line'
        css = '#layer {polygon-opacity:0; line-color:#FFFFB2; line-width:3; line-opacity:0.8;}'
        for i in range(n):
            upper = bins[n-1-i] 
            color = colors[n-1-i]
            css += '#layer [ %s <= %s] {line-color: %s;}' % (var, upper, color)
    elif geotype == pysal.cg.shapes.Point:
        geotype = 'point'
    
    tables = [
        {'name':table, 'type':geotype, 'css': css }
    ]
    
    cartodb_show_tables(tables)
    
def cartodb_show_lisa_map(shp, lisa_table, uuid=None, layers=[]):
    
    base_table = uuid
    if base_table == None:
        base_table = getuuid(shp)
        
    lisa_sql = 'SELECT a.the_geom_webmercator,a.cartodb_id,b.lisa FROM %s AS a, %s AS b WHERE a.cartodb_id=b.cartodb_id' % (base_table, lisa_table)
    
    tables = [
        {'name':base_table, 'type':'poly', 'css': CARTO_CSS_INVISIBLE},
        {'name':lisa_table, 'type':'poly', 'css': CARTO_CSS_LISA, 'sql': lisa_sql}
    ]
    
    for layer in layers:
        table_name = getuuid(layer['shp'])
        table = {'name':table_name, 'type':cartodb_get_geomtype(layer)}
        if 'css' in layer:
            css = layer['css']
            table["css"] = css            
        tables.append(table)
    
    cartodb_show_tables(tables)
    
   
def cartodb_table_exists(shp):
    import requests
    uuid = getuuid(shp)
    table_names = [uuid, "table_" + uuid]
    for tbl_name  in table_names:
        sql = 'SELECT count(cartodb_id) FROM %s' % (tbl_name)
        url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
        params = {
            'api_key': CARTODB_API_KEY,
            'q': sql,
        }
        r = requests.get(url, params=params, verify=False)
        content = r.json()    
        if "error" not in content:
            print "table %s existed" % tbl_name
            return tbl_name
    return None
    
def zipshapefiles(shp):
    uuid = getuuid(shp)
    shpPath = os.path.abspath(shp.dataPath)
    prefix = os.path.split(shpPath)[0]
    dbfPath = shpPath[:-3] + "dbf"
    shxPath = shpPath[:-3] + "shx"
    prjPath = shpPath[:-3] + "prj"
    new_shpPath = os.path.join(prefix, uuid + ".shp")
    new_shxPath = os.path.join(prefix, uuid + ".shx")
    new_dbfPath = os.path.join(prefix, uuid + ".dbf")
    new_prjPath = os.path.join(prefix, uuid + ".prj")
    shutil.copy(shpPath, new_shpPath)
    shutil.copy(dbfPath, new_dbfPath)
    shutil.copy(shxPath, new_shxPath)
    shutil.copy(prjPath,  new_prjPath)
  
    os.chdir(prefix) 
    ziploc = os.path.join(prefix, "upload.zip")
    try:
        os.remove(ziploc)
    except:
        pass
    try:
        import zlib
        mode = zipfile.ZIP_DEFLATED
    except:
        mode = zipfile.ZIP_DEFLATED
    myzip = zipfile.ZipFile("upload.zip",'w', mode) 
    myzip.write(os.path.split(new_shpPath)[1])
    myzip.write(os.path.split(new_shxPath)[1])
    myzip.write(os.path.split(new_dbfPath)[1])
    myzip.write(os.path.split(new_prjPath)[1])
    myzip.close()
  
    #for path in [new_shpPath, new_shxPath, new_dbfPath, new_prjPath]: 
    #    os.remove(path) 
    return ziploc
        
def cartodb_upload(shp, overwrite=False):
    if isinstance(shp, str):
        shp = pysal.open(shp)
        
    tbl_name = cartodb_table_exists(shp)
    if tbl_name and not overwrite: 
        return tbl_name
    elif tbl_name and overwrite:
        print "overwrite existing table..."
        cartodb_drop_table(tbl_name)
    
    import requests
    ziploc = zipshapefiles(shp) 
    import_url = "https://%s.cartodb.com/api/v1/imports/?api_key=%s" % (CARTODB_DOMAIN, CARTODB_API_KEY)
    r = requests.post(import_url, files={'file': open(ziploc, 'rb')}, verify=False)
    data = r.json()
    if data['success']!=True:
        print "Upload failed"
    complete = False
    last_state = ''
    while not complete: 
        import_status_url = "https://%s.cartodb.com/api/v1/imports/%s?api_key=%s" % (CARTODB_DOMAIN, data['item_queue_id'], CARTODB_API_KEY)
        req = urllib2.Request(import_status_url)
        response = urllib2.urlopen(req)
        d = json.loads(str(response.read()))
        if last_state!=d['state']:
            last_state=d['state']
            if d['state']=='uploading':
                print 'Uploading file...'
            elif d['state']=='importing':
                print 'Importing data...'
            elif d['state']=='complete':
                complete = True
                print 'Table "%s" created' % d['table_name']
        if d['state']=='failure':
            print d['get_error_text']['what_about']
    return d['table_name']    
    
def cartodb_count_pts_in_polys(poly_tbl, pt_tbl, count_col_name):
    import requests
    sql = 'SELECT count(%s) FROM %s' % (count_col_name, poly_tbl)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    r = requests.get(url, params=params, verify=False)
    content = r.json()    
    if "error" in content:
        print "column not existed, adding %s..." % count_col_name
        sql = 'ALTER TABLE %s ADD COLUMN %s integer' % (poly_tbl, count_col_name)
        url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
        params = {
            'api_key': CARTODB_API_KEY,
            'q': sql,
        }
        req = urllib2.Request(url, urllib.urlencode(params))
        response = urllib2.urlopen(req)
        content = response.read()
    # call sql api to update
    """
    UPDATE polygon_table SET point_count = (SELECT count(*)
    FROM points_table WHERE ST_Intersects(points_table.the_geom, polygon_table.the_geom))    
    """
    sql = 'UPDATE %s SET %s = (SELECT count(*) FROM %s WHERE ST_Intersects(%s.the_geom, %s.the_geom))' % \
        (poly_tbl, count_col_name, pt_tbl, pt_tbl, poly_tbl)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    req = urllib2.Request(url, urllib.urlencode(params))
    response = urllib2.urlopen(req)
    content = response.read()
    

#################################################
#
# Network
#
#################################################

if __name__ == '__main__':
            
    setup()
    
    setup_cartodb("340808e9a453af9680684a65990eb4eb706e9b56","lixun910")
    
    #cartodb_quantile_map(road_shp, 'cnt', 5, uuid=road_table)
    
    shp_path = "../test_data/sfpd_plots.shp"
    plots_shp = pysal.open(shp_path)
    plots_dbf = pysal.open(shp_path[:-3]+"dbf") 
    
    plot_table = cartodb_upload(plots_shp)
    crime_table = cartodb_upload(crime_shp)
   
    show_map(plots_shp) 
    
    get_selected(plots_shp)
    
    shp_path = "../test_data/sf_cartheft.shp"
    crime_shp = pysal.open(shp_path)
    crime_dbf = pysal.open(shp_path[:-3]+"dbf")

    show_map(crime_shp)
    
    
    cartodb_show_maps(plots_shp, layers=[crime_shp])
    cartodb_show_maps(plots_shp, layers=[crime_shp], 
                      styles={crime_shp:d3viz.CARTO_CSS_POINT})
    
    count_col_name = "crime_cnt" 
    #counting points in polygon and save results to a new col in polygon table
    cartodb_count_pts_in_polys(plot_table, crime_table, count_col_name)
    
    # download data for LISA 
    shp_path = cartodb_get_data(plot_table, [count_col_name])
   
    # run LISA 
    count_shp = pysal.open(shp_path)
    count_dbf = pysal.open(shp_path[:-3]+"dbf") 
    w = pysal.rook_from_shapefile(shp_path)
   
    LISA_table = "cartheft_lisa" 
    LISA_table = cartodb_lisa(\
        count_shp, count_dbf, w, count_col_name, plot_table, LISA_table)
    
    cartodb_show_lisa_map(plot_table, LISA_table)
    
    # add more layers
    cartodb_show_lisa_map(plot_table, LISA_table, layers=[
        {'name':crime_table, 'type':'point'}, 
    ])
    cartodb_show_lisa_map(plot_table, LISA_table, layers=[
        {'name':crime_table, 'type':'point','css': CARTO_CSS_POINT_CLOUD}, 
    ])
