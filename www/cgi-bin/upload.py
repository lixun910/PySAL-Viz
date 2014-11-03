#!/usr/bin/python
import os, cgi, md5
import shapefile
import json

current_path = os.path.realpath(__file__)    
current_path = os.path.split(current_path)[0]
current_path = os.path.split(current_path)[0]

message = "{}"

form = cgi.FieldStorage()
if 'userfile' in form.keys():
   fileitems = form['userfile']
   
   if type(fileitems) != type([]):
      fileitems = [fileitems]
      
   shp_path = None
   json_path = None
   shp_type = 0 
   for f in fileitems:
      if f.file:
         fn = os.path.basename(f.filename)
         ext = fn.split(".")[-1]
         path =  os.path.join(current_path, 'tmp', fn)
         
         if ext == "shp":
            shp_path = path
         elif ext == "json" or ext == "geojson":
            json_path = path
            
         open(path, 'wb').write(f.file.read())

   if shp_path:      
      # convert to geojson
      shpFileName = os.path.split(shp_path)[-1]
      shpFileNameNoExt = os.path.basename(shp_path).split(".")[0]
      uuid = md5.md5(shpFileNameNoExt).hexdigest()
      json_path = os.path.join(current_path, 'tmp', '%s.json' % uuid)
      if not os.path.exists(json_path):
         buffer = []
         reader = shapefile.Reader(shp_path)
         fields = reader.fields[1:]
         shp_type = reader.shapeType
         
         field_names = [field[0] for field in fields]
         for i, sr in enumerate(reader.shapeRecords()):
            atr = dict(zip(field_names, sr.record))
            atr["GEODAID"] = i
            geom = sr.shape.__geo_interface__
            buffer.append(dict(type="Feature", geometry=geom, properties=atr))
         geojson = open(json_path, "w")
         geojson.write(json.dumps({"type": "FeatureCollection","features": buffer}, ensure_ascii=False))
         geojson.close()
   
      message = {} 
      message["uuid"]  = uuid
      message["path"] = shp_path
      message["filename"] = shpFileName
      message = json.dumps(message)  
        
   elif json_path:
      # convert json to shape file
      pass
      
print 'Content-Type: text/javascript'
print
print message

