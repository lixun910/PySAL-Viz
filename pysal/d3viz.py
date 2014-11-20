import pysal
import numpy as np
import os.path
import json, shutil, webbrowser, md5, subprocess, re, threading, sys, random, string
from uuid import uuid4
from websocket import create_connection
import shapefile
import zipfile
import urllib2, urllib
from rdp import rdp
from network_cluster import NetworkCluster, GetJsonPoints
from time import sleep

__author__='Xun Li <xunli@asu.edu>'
__all__=['clean_ports','setup','getuuid','shp2json','show_map','get_selected', 'select','quantile_map','lisa_map','scatter_plot_matrix']

HTTP_ADDR = "http://127.0.0.1:8000"
PORTAL = "index.html"
WS_SERVER = "ws://localhost:9000"

# global variables
R_SHP_DICT = {}
# the dictionary of opened windows: key is winID and value is parameters used
# for this window
WIN_DICT = {}

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
CARTO_CSS_INVISIBLE_LINE = '#layer {line-opacity: 0;}'
                  
CARTO_CSS_LISA = ('#layer { '
                  'polygon-fill: #FFF; '
                  'polygon-opacity: 0.5; '
                  'line-color: #CCC; } '
                  '#layer[lisa=1]{polygon-fill: red;}'
                  '#layer[lisa=2]{polygon-fill: lightsalmon;}'
                  '#layer[lisa=3]{polygon-fill: blue;}'
                  '#layer[lisa=4]{polygon-fill: lightblue;}')

CARTO_CSS_LISA_LINE = ('#layer { '
                  'line-width: 3; '
                  'line-color: #CCC; '
                  'polygon-opacity: 0.5; '
                  'line-opacity: 0.5;} '
                  '#layer[lisa=1]{line-color: red;}'
                  '#layer[lisa=2]{line-color: lightsalmon;}'
                  '#layer[lisa=3]{line-color: blue;}'
                  '#layer[lisa=4]{line-color: lightblue;}')

def randomword(length):
    return ''.join(random.choice(string.lowercase) for i in range(length))    

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
                command = msg["command"]
                if command == "new_data":
                    uuid = msg["uuid"]
                    path = msg["path"]
                    ext = path.split(".")[-1]
                    if ext == "shp":
                        dbf_path = path[:-3] + "dbf"
                        shp = pysal.open(path,'r')
                        dbf = pysal.open(dbf_path, 'r')
                        self.parent.shp2json(shp, rebuild=True) 
                elif command == "request_params":
                    wid = msg["wid"]
                    params = WIN_DICT[wid]
                    msg = {
                        "command":"request_params",
                        "wid": wid,
                        "parameters": params
                    }
                    self.ws.send(json.dumps(msg))
                    
                elif command == "cartodb_get_all_tables":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    table_names = []
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        tables = self.parent.cartodb_get_all_tables()
                    msg = {"command" : "rsp_cartodb_get_all_tables"}
                    msg["wid"] = wid
                    msg["tables"] = tables # table_name:'Point'|Line|Polygon
                    self.ws.send(json.dumps(msg))
                    
                elif command == "cartodb_download_table":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    table_name = msg['table_name'] 
                    uuid = ""
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        print "start downloading table"
                        shp_path = self.parent.cartodb_get_data(table_name)
                        shp = pysal.open(shp_path,'r')
                        uuid = self.parent.shp2json(shp,rebuild=True) 
                    msg = {"command" : "rsp_cartodb_download_table"}
                    msg['wid'] = wid
                    msg["uuid"] = uuid
                    msg["name"] = os.path.basename(shp_path).split(".")[0]
                    prj_path = shp_path[:-3]+"prj" 
                    projection = open(prj_path,'r').read().strip()
                    msg["projection"] = projection
                    print "send back download cartodb"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "cartodb_upload_table":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    uuid = msg['uuid'] 
                    carto_table_name = ""
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        print "start uploading table"
                        shp = R_SHP_DICT[uuid]["shp"]
                        carto_table_name = self.parent.cartodb_upload(shp, overwrite=True)
                    msg = {"command" : "rsp_cartodb_upload_table"}
                    msg['wid'] = wid
                    msg["uuid"] = uuid
                    msg["new_table_name"] = carto_table_name
                    print "send back upload cartodb"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "cartodb_spatial_count":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    first_layer = msg['firstlayer'] 
                    second_layer = msg['secondlayer'] 
                    count_col_name = msg['columnname'] 
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    rtn = False
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        print "start spatial count"
                        rtn=cartodb_count_pts_in_polys(first_layer, second_layer, count_col_name)
                    msg = {"command" : "rsp_cartodb_spatial_count"}
                    msg['wid'] = wid
                    msg['result'] = rtn
                    print "send back cartodb spatial count"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "road_segment":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    uuid = msg['uuid'] 
                    length = msg['length'] 
                    ofn = msg['ofn'] 
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        print "start road segmentation"
                        shp = R_SHP_DICT[uuid]["shp"]
                        shpFileName = shp.dataPath
                        prefix = os.path.split(shpFileName)[0]
                        if ofn.endswith("shp"):
                            ofn = os.path.join(prefix, ofn)
                        else:
                            ofn = os.path.join(prefix, ofn + ".shp")
                        if 'network' not in R_SHP_DICT[uuid]:
                            jsonPath = os.path.join(prefix, uuid + ".json")
                            net = NetworkCluster(jsonPath, shpFileName)
                            R_SHP_DICT[uuid]['network'] = net
                        else:
                            net = R_SHP_DICT[uuid]['network']
                        net.SegmentNetwork(int(length))
                        net.ExportCountsToShp(ofn, counts=False)
                    msg = {"command" : "rsp_road_segment"}
                    msg['wid'] = wid
                    msg["uuid"] = uuid
                    msg["result"] = True
                    print "send back road segmentation"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "road_snap_point":
                    wid = msg["wid"]
                    uid = msg['uid'] if 'uid' in msg else CARTODB_DOMAIN 
                    key = msg['key'] if 'key' in msg else CARTODB_API_KEY
                    point_uuid = msg['pointuuid'] 
                    road_uuid = msg['roaduuid'] 
                    if uid and key:
                        CARTODB_DOMAIN = uid
                        CARTODB_API_KEY = key
                    if CARTODB_API_KEY and CARTODB_DOMAIN:
                        print "start road snapping point"
                        road_shp = R_SHP_DICT[road_uuid]["shp"]
                        road_shpFileName = road_shp.dataPath
                        prefix, shpName = os.path.split(road_shpFileName)
                        ofn = road_shpFileName
                        
                        if 'network' not in R_SHP_DICT[road_uuid]:
                            road_jsonPath = os.path.join(prefix, road_uuid + ".json")
                            net = NetworkCluster(road_jsonPath, road_shpFileName)
                            R_SHP_DICT[road_uuid]['network'] = net
                        else:
                            net = R_SHP_DICT[road_uuid]['network']
                        net.SegmentNetwork(sys.maxint)
                        
                        point_shp = R_SHP_DICT[point_uuid]["shp"]
                        point_jsonPath = os.path.join(prefix, point_uuid + ".json")
                        points = GetJsonPoints(point_jsonPath)
                        
                        net.SnapPointsToNetwork(points)
                        net.ExportCountsToShp(ofn)
                       
                    shp = pysal.open(ofn, 'r') 
                    uuid = self.parent.shp2json(shp,rebuild=True) 
                    msg = {"command" : "rsp_road_snap_point"}
                    msg['wid'] = wid
                    msg["uuid"] = uuid
                    msg["name"] = shpName[:-4]
                    msg["result"] = True
                    print "send back road snapping point"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "new_lisa_map":
                    wid = msg["wid"]
                    uuid = msg["uuid"]
                    var = msg["var"]
                    w_name = msg["w_name"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    dbf = R_SHP_DICT[uuid]["dbf"]
                    w = R_SHP_DICT[uuid]["weights"][w_name]["w"]
                    y = np.array(dbf.by_col[var])
                    lm = pysal.Moran_Local(y, w)
                    self.parent.lisa_map(shp, var, lm)
                    
                    msg = {"command" : "rsp_new_lisa_map"}
                    msg['wid'] = wid
                    msg["uuid"] = uuid
                    msg["result"] = True
                    print "send back LISA"
                    self.ws.send(json.dumps(msg))
                    
                elif command == "new_moran_scatter_plot":
                    uuid = msg["uuid"]
                    var = msg["var"]
                    w_name = msg["w_name"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    dbf = R_SHP_DICT[uuid]["dbf"]
                    w = R_SHP_DICT[uuid]["weights"][w_name]["w"]
                    self.parent.moran_scatter_plot(shp, dbf, var, w)
                elif command == "new_scatter_plot":
                    uuid = msg["uuid"]
                    var_x = msg["var_x"]
                    var_y = msg["var_y"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    self.parent.scatter_plot(shp, field_x=var_x, field_y=var_y)
                elif command == "new_choropleth_map":
                    uuid = msg["uuid"]
                    method = msg["method"]
                    var = msg["var"]
                    cat = msg["category"]
                    shp = R_SHP_DICT[uuid]["shp"]
                    self.parent.choropleth_map(shp, var, cat, method=method)
                elif command == "create_w":
                    uuid = msg["uuid"]
                    wid = msg["wid"]
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
                    w.name = w_name
                    if not "weights" in R_SHP_DICT[uuid]:
                        R_SHP_DICT[uuid]["weights"] = {}
                    R_SHP_DICT[uuid]["weights"][w_name] = {
                        'w':w, 'type':w_type
                    }
                    results = {'command':'rsp_create_w', 'wid': wid, \
                               'content': {w_name : {'type':w_type}}}
                    self.ws.send(json.dumps(results))
                
                elif command == "spatial_regression":
                    wid = msg["wid"] 
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
                        w_list = [R_SHP_DICT[uuid]["weights"][w_name]['w'] for w_name in w_model]
                        wk_list = [R_SHP_DICT[uuid]["weights"][w_name]['w'] for w_name in w_kernel]
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
                        result['wid'] = wid
                        result['command'] = 'rsp_spatial_regression'
                        self.ws.send(json.dumps(result))
            except:
                print "something wrong."
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
        
        if sys.platform == 'win32':
            sleep(1)
            
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
            os.chdir(os.path.split(current_path)[0])
        else:
            script = "cd %s && python %s" % (www_path, http_path)
            subprocess.Popen([script], shell=True)
        
    sleep(1)
    am = AnswerMachine(sys.modules[__name__])
    am.start()
    #global PORTAL
    #url = "http://127.0.0.1:8000/%s?%s" % (PORTAL, randomword(10)) 
    #webbrowser.open_new(url)
    #sleep(1)
    
def getuuid(shp):
    """
    Generate UUID using absolute path of shapefile
    """
    file_path = shp.dataPath
    file_name = os.path.basename(file_path).split(".")[0]
    return md5.md5(file_name).hexdigest()
   
def getmsguuid():
    """
    """
    return "m"+randomword(9)

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
    if uuid not in R_SHP_DICT or rebuild == True:
        R_SHP_DICT[uuid] = {"shp":None, "dbf":None,"json":None, "shp_path":"","prj":""}
        dbf = pysal.open(shp.dataPath[:-3]+"dbf") 
        R_SHP_DICT[uuid]["shp"] = shp
        R_SHP_DICT[uuid]["dbf"] = dbf
        R_SHP_DICT[uuid]["shp_path"] = shp.dataPath
        prj_path = shp.dataPath[:-3]+"prj" 
        try:
            projection = open(prj_path,'r').read().strip()
            R_SHP_DICT[uuid]["prj"] = projection
        except:
            pass
    
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
                atr = dict(zip(field_names, sr.record))
                atr["GEODAID"] = i
                geom = sr.shape.__geo_interface__
                buffer.append(dict(type="Feature", geometry=geom, properties=atr))
        except:
            dbf = R_SHP_DICT[uuid]["dbf"]
            field_names = dbf.header
            n = len(field_names)
            for i, geom in enumerate(shp):
                atr = {}
                for j in range(n):
                    atr[field_names[i][j]] = dbf[i][0][j]
                atr["GEODAID"] = i
                geo = geom.__geo_interface__
                buffer.append(dict(type="Feature", geometry=geo, properties=atr))
            
        geojson = open(www_path, "w")
        geojson.write(json.dumps({"type": "FeatureCollection","features": buffer}, ensure_ascii=False))
        geojson.close()
    else:
        print "The geojson data has been created before. If you want re-create geojson data, please call shp2json(shp, rebuild=True)."
    return uuid

def init_map(shp, rebuild=False, uuid=None):
    shp2json(shp, rebuild=rebuild, uuid=uuid)
    
def show_portal():
    wid = getmsguuid()
    WIN_DICT[wid] = None
    
    request_page = "new_portal.html?wid=%s" % (wid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    
def show_map(shp):
    uuid = getuuid(shp)

    if uuid not in R_SHP_DICT: 
        print "Please run init_map first."
        return
    
    wid = getmsguuid()
    WIN_DICT[wid] = None
    
    request_page = "new_map.html?wid=%s&json_url=%s&uuid=%s&param=0" % (wid, uuid, uuid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    
def add_layer(shp, rebuild=False, uuid=None):
    shp2json(shp, rebuild=rebuild, uuid=uuid)
        
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    if uuid == None: 
        uuid = getuuid(shp)
    
    msg = {
        "id" : getmsguuid(),
        "command": "add_layer",
        "uuid": uuid,
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    print "send:", str_msg
    ws.close()
    sleep(1)    
    
def close_all():
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "id" : getmsguuid(),
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
        "id" : getmsguuid(),
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
        "id" : getmsguuid(),
        "command": "select",
        "uuid":  uuid,
        "data": ids
    }
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
   
def equal_interval_map(shp, var, k, basemap=None, uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    dbf = R_SHP_DICT[uuid]['dbf']
    
    y = dbf.by_col[var]
    q = pysal.esda.mapclassify.Equal_Interval(np.array(y), k=k)    
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
        "id" : getmsguuid(),
        "command": "thematic_map",
        "type": "quantile",
        "uuid":  uuid,
        "title": "Equal interval for variable [%s], k=%d" %(var, len(id_array)),
        "bins": bins.tolist(),
        "data": id_array,
    }
    if basemap:
        msg["basemap"] = basemap
        
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def choropleth_map(shp, var, k, method="quantile", basemap="leaflet", uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    dbf = pysal.open(shp.dataPath[:-3] + "dbf")
    y = dbf.by_col[var]
    k = int(k)
    if method == "quantile":
        pysalFunc = pysal.Quantiles
    elif method == "equal interval":
        pysalFunc = pysal.Equal_Interval
    elif method == "natural breaks":
        pysalFunc = pysal.Natural_Breaks
    elif method == "fisher jenks":
        pysalFunc = pysal.Fisher_Jenks
    
    q = pysalFunc(np.array(y), k=k)    
    bins = q.bins
    id_array = []
    for i, upper in enumerate(bins):
        if i == 0: 
            id_array.append([j for j,v in enumerate(y) if v <= upper])
        else:
            id_array.append([j for j,v in enumerate(y) \
                             if bins[i-1] < v <= upper])
            
    projection = R_SHP_DICT[uuid]['prj']
    wid = getmsguuid()
    WIN_DICT[wid] = {
        "uuid":  uuid,
        "projection": projection,
        "type": method,
        "title": "%s map for variable [%s], k=%d" %(method, var, len(id_array)),
        "bins": bins if isinstance(bins, list) else bins.tolist(),
        "id_array": id_array,
    }

    base_page = "thematic_map.html" 
    if basemap == "leaflet": 
        base_page = "new_leaflet_map.html"
    request_page = "%s?wid=%s&json_url=%s&uuid=%s&param=1"%(base_page, wid, uuid, uuid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    
def quantile_map(shp, var, k, basemap=None, uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    dbf = pysal.open(shp.dataPath[:-3] + "dbf")
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
            
            
    wid = getmsguuid()
    WIN_DICT[wid] = {
        "uuid":  uuid,
        "type": "quantile",
        "title": "Quantile map for variable [%s], k=%d" %(var, len(id_array)),
        "bins": bins.tolist(),
        "id_array": id_array,
    }

    base_page = "thematic_map.html" 
    if basemap == "leaflet": 
        base_page = "new_leaflet_map.html"
    request_page = "%s?wid=%s&json_url=%s&uuid=%s&param=1"%(base_page, wid, uuid, uuid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    """ 
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "thematic_map",
        "uuid":  uuid,
        "type": "quantile",
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
    """
    
def natural_map(shp, var, k, basemap=None, uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run show_map first."
        return
    dbf = pysal.open(shp.dataPath[:-3] + "dbf")
    y = dbf.by_col[var]
    q = pysal.Natural_Breaks(np.array(y), k=k)    
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
        "command": "thematic_map",
        "uuid":  uuid,
        "type": "quantile",
        "title": "Natural break map for variable [%s], k=%d" %(var, len(id_array)),
        "bins": bins,
        "id_array": id_array,
    }
    if basemap:
        msg["basemap"] = basemap
        
    str_msg = json.dumps(msg)
    ws.send(str_msg)
    #print "send:", str_msg
    ws.close()
    
def lisa_map(shp, var, local_moran, basemap="leaflet", uuid=None):
    if uuid == None:
        uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run init_map first."
        return
    lm = local_moran 
    bins = ["Not Significant","High-High","Low-High","Low-Low","Hight-Low"]
    id_array = []
    id_array.append([i for i,v in enumerate(lm.p_sim) \
                     if lm.p_sim[i] >= 0.05])
    for j in range(1,5): 
        id_array.append([i for i,v in enumerate(lm.q) \
                         if v == j and lm.p_sim[i] < 0.05])
    
    wid = getmsguuid()
    WIN_DICT[wid] = {
        "command": "thematic_map",
        "type": "lisa",
        "uuid":  uuid,
        "title": "LISA map for variable [%s], w=%s" %(var, ".gal"),
        "bins": bins,
        "id_array": id_array,
    }
    base_page = "thematic_map.html" 
    if basemap == "leaflet": 
        base_page = "new_leaflet_map.html"
    request_page = "%s?wid=%s&json_url=%s&uuid=%s&param=1"%(base_page, wid, uuid, uuid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    
def moran_scatter_plot(shp, dbf, var, w):
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run init_map first."
        return
    y = np.array(dbf.by_col[var])
    y_lag = pysal.lag_spatial(w, y)
   
    y_z = (y - y.mean()) / y.std()
    y_lag_z = (y_lag - y_lag.mean()) / y_lag.std()
    
    wid = getmsguuid()
    WIN_DICT[wid] = {
        "uuid":  uuid,
        "title": "Moran Scatter plot for variable [%s]" % var,
        "data": { "x": y_z.tolist(), "y" : y_lag_z.tolist() },
        "fieldx": var,
        "fieldy": "lagged %s" % var
    }
    request_page = "new_moran_scatter_plot.html?wid=%s&json_url=%s&uuid=%s" % \
        (wid, uuid, uuid)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    
def scatter_plot(shp, field_x=None, field_y=None):
    uuid = getuuid(shp)
    if uuid not in R_SHP_DICT: 
        print "Please run init_map first."
        return
    dbf = R_SHP_DICT[uuid]["dbf"] 
    
    wid = getmsguuid()
    WIN_DICT[wid] = None
    
    request_page = "new_scatter_plot.html?wid=%s&json_url=%s&uuid=%s&fieldx=%s&fieldy=%s" % \
        (wid, uuid, uuid, field_x, field_y)
    url = "%s/%s&%s" % (HTTP_ADDR, request_page , randomword(10))
   
    webbrowser.open_new(url) 
    """
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
    """
    
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
    
    
CARTODB_API_KEY = '340808e9a453af9680684a65990eb4eb706e9b56'
CARTODB_DOMAIN = 'lixun910'

def setup_cartodb(api_key, user):
    global CARTODB_API_KEY, CARTODB_USER
    CARTODB_API_KEY = api_key
    CARTODB_USER = user

def cartodb_get_data(table_name, fields=[],loc=None,file_name=None):
    fields_str = '*'
    if len(fields) > 0:
        #if "ST_Transform(the_geom, 4326) as the_geom" not in fields:
        #    fields.append("ST_Transform(the_geom, 4326) as the_geom")
        if "the_geom" not in fields:
            fields.append("the_geom")
        fields_str = ", ".join(fields)
    global CARTODB_API_KEY, CARTODB_DOMAIN
    import requests
    sql = 'select %s from %s' % (fields_str, table_name)
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    params = {
        'filename': 'cartodb-query',
        'format': 'shp' ,
        'api_key': CARTODB_API_KEY,
        'q': sql,
    }
    r = requests.get(url, params=params, verify=False)
    if r.ok == False:
        # try again, sometime the CartoDB call doesn't work
        r = requests.get(url, params=params, verify=False)
    if r.ok == False:
        print "Get data from CartoDB faield!"
        return
    
    content = r.content 
   
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
            oldname = os.path.join(loc, filename)
            newname = os.path.join(loc, table_name + filename[-4:])
            #os.rename(oldname, newname)
            shutil.copy(oldname, newname)
    return os.path.join(loc, table_name + ".shp")

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
        if base_table[0].isdigit():
            base_table = "table_" + base_table
        
        
    tables = []
    table = {'name':base_table, 'type':cartodb_get_geomtype(shp)}
    if css:
        table["css"] = css
    tables.append(table)        
    
    for layer in layers:
        subshp = layer['shp']
        table_name = getuuid(subshp)
        if table_name[0].isdigit():
            table_name = "table_" + table_name
        table = {'name':table_name, 'type':cartodb_get_geomtype(subshp)}
        if 'css' in layer:
            css = layer['css']
            table["css"] = css            
        tables.append(table)
    cartodb_show_tables(tables)

def cartodb_show_tables(tables):
    default_cartocss = {}
    default_cartocss['poly'] = ('#layer {'
        'polygon-fill: #006400; '
        'polygon-opacity: 0.9; '
        'line-color: #CCCCCC; }')
    default_cartocss['line'] = ('#layer {'
        'line-width: 2; '
        'line-opacity: 0.9; '
        'line-color: #006400; }')
    default_cartocss['point'] = ('#layer { '
         'marker-fill: #FF6600; marker-opacity: 1; marker-width: 6;'
         'marker-line-color: white; marker-line-width: 1; '
         'marker-line-opacity: 0.9; marker-placement: point; '
         'marker-type: ellipse; marker-allow-overlap: true;}')
    sublayers = []
    uuids = []
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
        uuids.append(tables[0]["name"].split("_")[-1])
    uuid = uuids[0]
    layers = uuid[1:]
    global WS_SERVER 
    ws = create_connection(WS_SERVER)
    msg = {
        "command": "cartodb_mymap",
        "uuid": uuid,
        "layers": layers,
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
    print "Drop table " + table_name + "done:" + json.dumps(content)
   
def cartodb_lisa(local_moran, new_lisa_table, cartodb_ids=None):
    """
    add a csv table with LISA clusters, using cartodb_id to join table
    """
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
    try:
        os.remove(csv_loc)
    except:
        pass
    
    csv = open(csv_loc, "w")
    csv.write("cartodb_id, lisa\n")
    if cartodb_ids:
        for i,v in enumerate(lisa):
            csv.write("%s,%s\n" % (cartodb_ids[i], v))
    else:
        for i,v in enumerate(lisa):
            csv.write("%s,%s\n" % (i+1, v))
    csv.close()
    # create zip file for uploading
    zp_loc =  os.path.join(loc, "upload.zip")
    try:
        os.remove(zp_loc)
    except:
        pass
    orig_loc = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(loc)
    zp = zipfile.ZipFile("upload.zip","w")
    zp.write(new_lisa_table+".csv")
    zp.close()
    os.chdir(orig_loc)

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
        if table[0].isdigit():
            table = "table_" + table
       
    dbf = pysal.open(shp.dataPath[:-3] + "dbf")
    y = dbf.by_col[var]
    q = pysal.esda.mapclassify.Equal_Interval(np.array(y), k=k)    
    bins = q.bins
    n = len(bins)   
    colors = YLRD[n]
    geotype = shp.type
    if geotype == pysal.cg.shapes.Polygon:
        geotype = 'poly'
        css = '#layer {polygon-fill:#FFFFB2; polygon-opacity: 0.8; line-color:#CCCCCC; line-width:1; line-opacity:1;}'
        for i in range(n):
            upper = bins[n-1-i] 
            color = colors[n-1-i]
            css += '#layer [ %s <= %s] {polygon-fill: %s;}' % (var, upper, color)
    elif geotype == pysal.cg.shapes.LineSegment or geotype == pysal.cg.Chain:
        geotype = 'line'
        css = '#layer {polygon-opacity:0.6; line-color:#FFFFB2; line-width:3; line-opacity:0.8;}'
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
        if base_table[0].isdigit():
            base_table = "table_" + base_table
        
    lisa_sql = 'SELECT a.the_geom_webmercator,a.cartodb_id,b.lisa FROM %s AS a, %s AS b WHERE a.cartodb_id=b.cartodb_id' % (base_table, lisa_table)
    
    geotype = cartodb_get_geomtype(shp)
    invisible_css = CARTO_CSS_INVISIBLE
    lisa_css = CARTO_CSS_LISA
    if geotype == 'line':
        invisible_css = CARTO_CSS_INVISIBLE_LINE
        lisa_css = CARTO_CSS_LISA_LINE
    tables = [
        {'name':base_table, 'type':geotype, 'css': invisible_css},
        {'name':lisa_table, 'type':geotype, 'css': lisa_css, 'sql': lisa_sql}
    ]
    
    for layer in layers:
        subshp = layer['shp']
        table_name = getuuid(subshp)
        if table_name[0].isdigit():
            table_name = "table_" + table_name
        table = {'name':table_name, 'type':cartodb_get_geomtype(subshp)}
        if 'css' in layer:
            css = layer['css']
            table["css"] = css            
        tables.append(table)
    
    cartodb_show_tables(tables)
    
   
def cartodb_table_exists(shp):
    import requests
    file_path = shp.dataPath
    table_name = os.path.basename(file_path).split(".")[0]
    if table_name[0].isdigit():
        table_name = "table_" + table_name
        
    table_names = [table_name]
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
    shpPath = os.path.abspath(shp.dataPath)
    prefix = os.path.split(shpPath)[0]
    dbfPath = shpPath[:-3] + "dbf"
    shxPath = shpPath[:-3] + "shx"
    prjPath = shpPath[:-3] + "prj"
    orig_loc = os.path.split(os.path.realpath(__file__))[0]
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
    myzip.write(os.path.split(shpPath)[1])
    myzip.write(os.path.split(shxPath)[1])
    myzip.write(os.path.split(dbfPath)[1])
    myzip.write(os.path.split(prjPath)[1])
    myzip.close()
    os.chdir(orig_loc)
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
    
def cartodb_count_pts_in_polys(pt_tbl, poly_tbl, count_col_name):
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
        r = requests.get(url, params=params, verify=False)
        content = r.json()    
        if 'error' in content:
            print 'add column faield'
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
    r = requests.get(url, params=params, verify=False)
    content = r.json()    
    if "error" in content:
        return False
    return True
    

def cartodb_get_all_tables():
    import requests
    url = 'https://%s.cartodb.com/api/v1/sql' % CARTODB_DOMAIN
    sql = "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    params = { 'api_key': CARTODB_API_KEY, 'q': sql,}
    r = requests.get(url, params=params, verify=False)
    content = r.json()    
    table_names = []
    if "error" in content:
        print "get all tables () error:", content
    else:
        rows = content["rows"]
        for row in rows:
            table_name = row["table_name"] 
            if table_name not in ["raster_columns","raster_overviews", "spatial_ref_sys","geometry_columns","geography_columns"]:
                table_names.append(table_name)
    result = {}
    for tbl in table_names:
        sql = "SELECT ST_GeometryType(the_geom) FROM %s LIMIT 1" % tbl
        params = { 'api_key': CARTODB_API_KEY, 'q': sql,}
        r = requests.get(url, params=params, verify=False)
        content = r.json()
        if "error" not in content:
            rows = content["rows"]
            row = rows[0]
            print row
            if 'st_geometrytype' in row:
                geotype = row["st_geometrytype"]
                if geotype != None:
                    if geotype.find("Point") > -1 :
                        result[tbl] = 'Point'
                    elif geotype.find("Line") > -1:
                        result[tbl] = 'Line'
                    elif geotype.find("Poly") > -1:
                        result[tbl] = "Polygon"
    return result
                
#################################################
#
# Network
#
#################################################


