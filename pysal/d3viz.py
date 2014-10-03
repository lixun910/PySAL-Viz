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


__author__='Xun Li <xunli@asu.edu>'
__all__=['clean_ports','setup','getuuid','shp2json','show_map','get_selected', 'select','quantile_map','lisa_map','scatter_plot_matrix']

PORTAL = "index.html"
WS_SERVER = "ws://localhost:9000"
R_SHP_DICT = {}


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
                        
                        self.parent.show_map(shp, dbf)
                    
                elif command == "new_quantile_map":
                    uuid = msg["uuid"]
                    var = msg["var"]
                    cat = msg["category"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    dbf = R_SHP_DICT[uuid]["dbf"]
                    
                    self.parent.quantile_map(shp, dbf, var, cat)
                    
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
    
def shp2json(shp,dbf, rebuild=False):
    """
    Create a GeoJson file from pysal.shp object and store it in www/ path.
    Which can be visited using http://localhost:8000/*.json
    """
    uuid = getuuid(shp)
    
    global R_SHP_DICT
    if uuid not in R_SHP_DICT:
        R_SHP_DICT[uuid] = {"shp":None, "dbf":None,"json":None, "shp_path":""}
    R_SHP_DICT[uuid]["shp"] = shp
    
    print "creating geojson ..."
    current_path = os.path.realpath(__file__)    
    www_path = "%s/../www/tmp/%s.json" % \
        (current_path[0:current_path.rindex('/')], uuid)
   
    R_SHP_DICT[uuid]["json"] = www_path
    
    if not os.path.exists(www_path) or rebuild==True: 
        print "reading data ..."
        buffer = []
        reader = shapefile.Reader(shp.dataPath)
        fields = reader.fields[1:]
        field_names = [field[0] for field in fields]
        """
        field_names = dbf.header
        for i, geom in enumerate(shp):
            atr = dict(zip(field_names, dbf[i][0]))
            atr["GEODAID"] = i
            geo = geom.__geo_interface__
            coords = geo["coordinates"]
            buffer.append(dict(type="Feature", geometry=geo, properties=atr))
        """
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

def show_map(shp, dbf):
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
    shp2json(shp, dbf)
    
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    uuid = getuuid(shp)
    
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
    ids = [int(id) for id in ids]
    return ids
    
def select(shp, ids=[]):
    if len(ids) == 0:
        return
    
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
    
def quantile_map(shp, dbf, var, k, basemap=None):
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
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

def cartodb_get_data(table_name, fields=[]):
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
    
    loc = os.path.realpath(__file__)    
    loc = loc[0:loc.rindex('/')]
    loc = loc[0:loc.rindex('/')] + "/www/tmp/"
    ziploc = loc + "tmp.zip"
    
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
    
def cartodb_show_maps(tables):
    default_cartocss = {}
    default_cartocss['poly'] = ('#layer {'
        'polygon-fill: green; '
        'polygon-opacity: 0.8; '
        'line-color: #CCC; }')
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
 
def cartodb_create_map():
    mapconfig = {
        "version": "0.0.1",
          "name": "mytest1",
          "auth": {
            "method": "open"
          },
          "layergroup": {
            "layers": [{
              "type": "cartodb",
              "options": {
                "cartocss_version": "2.1.1",
                "cartocss": "#layer { polygon-fill: #FFF; }",
                "sql": "select * from table_80f6b361d3143cee5a50ed3e27b07848"
              }
            }]
          }        
    }
    url = 'https://%s.cartodb.com/api/v1/map/named?api_key=%s' % \
        (CARTODB_DOMAIN, CARTODB_API_KEY)
    
    #opener = urllib2.build_opener()
    #req = urllib2.Request(url, data=json.dumps(mapconfig),
    #      headers={'Content-Type': 'application/json'})
    response = urllib2.urlopen(url, json.dumps(mapconfig))
    #response = opener.open(req)    
    content = response.read()
    
def cartodb_lisa_map(shp, dbf, var, w, poly_table, lisa_table_name):
    import StringIO
    y = dbf.by_col[var]
    lm = pysal.Moran_Local(np.array(y), w)
    lisa = lm.q
    
    for i,v in enumerate(lm.p_sim):
        if lm.p_sim[i] >= 0.05:
            lisa[i] = 0
    loc = os.path.realpath(__file__)    
    loc = loc[0:loc.rindex('/')]
    loc = loc[0:loc.rindex('/')] + "/www/tmp/"        
    csv_loc = loc + lisa_table_name + ".csv" 
    csv = open(csv_loc, "w")
    csv.write("cartodb_id, lisa\n")
    for i,v in enumerate(lisa):
        csv.write("%s,%s\n" % (i, v))
    csv.close()
  
    zp_loc =  loc + "upload.zip"
    zp = zipfile.ZipFile(zp_loc,"w")
    zp.write(csv_loc)
    zp.close()

    import requests
    import_url = "https://%s.cartodb.com/api/v1/imports/?api_key=%s" % (CARTODB_DOMAIN, CARTODB_API_KEY)
    r = requests.post(import_url, files={'file':open(zp_loc, 'rb')}, verify=False)
    data = r.json()
    
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
            
    lisa_table = d['table_name']
    cartodb_show_lisa_map(poly_table, lisa_table)
    
def cartodb_show_lisa_map(poly_table, lisa_table, point_tbl=None, show_points=False):
    lisa_color = ['#fff','darkred','lightsalmon','darkblue','lightblue']
    lisa_sql = 'select a.the_geom_webmercator,a.cartodb_id,b.lisa from %s as a, %s as b where a.cartodb_id=b.cartodb_id' % (poly_table, lisa_table)
    lisa_css= '#layer { polygon-fill: #FFF; polygon-opacity: 0.5; line-color: #CCC; } #layer[lisa="1"]{polygon-fill: red;} #layer[lisa="2"]{polygon-fill: lightsalmon;} #layer[lisa="3"]{polygon-fill: blue;} #layer[lisa="4"]{polygon-fill: lightblue;}'
    
    cartocsses = [lisa_css, CARTO_CSS_POINT] if point_tbl else [lisa_css]
    cartosqls = [lisa_sql,None] if point_tbl else [lisa_sql]
    if point_tbl:
        cartodb_show_maps([lisa_table,point_tbl],['poly', 'point'], cartocsses, cartosqls) 
    else:
        cartodb_show_maps([lisa_table],['poly'], cartocsses, cartosqls) 
   
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
    shpPath = shp.dataPath
    prefix = shpPath[0:shpPath.rindex('/')+1]
    dbfPath = shpPath[:-3] + "dbf"
    shxPath = shpPath[:-3] + "shx"
    prjPath = shpPath[:-3] + "prj"
    new_shpPath = prefix + uuid + ".shp"
    new_dbfPath = prefix + uuid + ".dbf"
    new_shxPath = prefix + uuid + ".shx"
    new_prjPath = prefix + uuid + ".prj"
    shutil.copy(shpPath, new_shpPath)
    shutil.copy(dbfPath, new_dbfPath)
    shutil.copy(shxPath, new_shxPath)
    shutil.copy(prjPath,  new_prjPath)
    
    loc = os.path.realpath(__file__)    
    loc = loc[0:loc.rindex('/')]
    loc = loc[0:loc.rindex('/')] + "/www/tmp/"
    ziploc = loc + "upload.zip"
    with zipfile.ZipFile(ziploc,'w') as myzip:
        myzip.write(new_shpPath) 
        myzip.write(new_shxPath) 
        myzip.write(new_dbfPath) 
        myzip.write(new_prjPath) 
    return ziploc
        
def cartodb_upload(shp):
    tbl_name = cartodb_table_exists(shp)
    if tbl_name: return tbl_name
    
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
    sql = 'UPDATE %s SET %s = (SELECT count(*) FROM %s WHERE ST_Intersects(%s.the_geom, %s.the_geom))' % (poly_tbl, count_col_name, pt_tbl, pt_tbl, poly_tbl)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    req = urllib2.Request(url, urllib.urlencode(params))
    response = urllib2.urlopen(req)
    content = response.read()
    
if __name__ == '__main__':
    setup()
    
    shp_path = "/data/sfpd_plots.shp"
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
   
    show_map(shp, dbf) 
    
    shp_path = "/data/sf_cartheft.shp"
    crime_shp = pysal.open(shp_path)
    crime_dbf = pysal.open(shp_path[:-3]+"dbf")

    show_map(crime_shp, crime_dbf)
    
    setup_cartodb("340808e9a453af9680684a65990eb4eb706e9b56","lixun910")
    
    plot_table = cartodb_upload(shp)
    crime_table = cartodb_upload(crime_shp)
    
    cartodb_show_maps([
        {'name':plot_table, 'type':'poly'}, 
        {'name':crime_table, 'type':'point'}, 
    ])
    
    cartodb_show_maps([
        {'name':plot_table, 'type':'poly'}, 
        {'name':crime_table, 'type':'point','css': CARTO_CSS_POINT_CLOUD}, 
    ])
    
    count_col_name = "crime_cnt" 
    #counting points in polygon and save results to a new col in polygon table
    cartodb_count_pts_in_polys(plot_table, crime_table, count_col_name)
    """ 
    poly_tbl ="sfpd_plots"
    point_tbl = "sf_cartheft"
    #upload polygon shapefile
    #upload point shapefile
    # show polygon + point map in CartoDB.js 
    #cartodb_show_maps([poly_tbl, point_tbl],['poly','point']) 
    
    cartodb_show_maps([point_tbl,point_tbl],['point','poly'], [CARTO_CSS_POINT_CLOUD,None]) 
    
    #counting points in polygon
    #cartodb_count_pts_in_polys("sfpd_plots","sf_cartheft","mycnt")
    
    # download data for LISA 
    shp_path = cartodb_get_data(poly_tbl, [var_name])
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
     
    # running LISA
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
    w = pysal.rook_from_shapefile(shp_path)
    new_lisa_table_name = "cartheft_lisa" 
    #cartodb_lisa_map(shp, dbf, var_name, w, poly_tbl, new_lisa_table_name)
    cartodb_show_lisa_map(poly_tbl, new_lisa_table_name, show_points=False)
    cartodb_show_lisa_map(poly_tbl, new_lisa_table_name, show_points=True)
       
    # show LISA map in CartoDB.js
    # show LISA map + point intensity map in CartoDB.js
    
    
    #cartodb_get_mapid()
    #cartodb_create_map()    
    
    
    #show_map(shp)
    #start_answermachine()
    """