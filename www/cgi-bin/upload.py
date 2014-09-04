#!/usr/bin/python
import os, cgi, md5

current_path = os.path.realpath(__file__)    
current_path = current_path[0:current_path.rindex('/')]
current_path = current_path[0:current_path.rindex('/')]
message = "{}"

form = cgi.FieldStorage()
if 'userfile' in form.keys():
   fileitems = form['userfile']
   
   if type(fileitems) != type([]):
      fileitems = [fileitems]
      
   for f in fileitems:
      fn = os.path.basename(f.filename)
      if f.file:
         fn = os.path.basename(f.filename)
         ext = fn.split(".")[-1]
         path =  '%s/%s' % (current_path, fn)
         
         if ext == "shp" or ext == "json" or ext == "geojson":
            shp_path = '%s/%s' % (current_path, "".join(fn.split(".")[:-1]))
            uuid = md5.md5(shp_path).hexdigest()
            message = '{"uuid":"%s","path":"%s"}' % (uuid, path)
            
         open(path, 'wb').write(f.file.read())
      
print 'Content-Type: text/javascript'
print
print message

