#!/usr/bin/python
import os, cgi, md5, sys
import shapefile
import zipfile
from shutil import copyfileobj

orig_loc = os.path.split(os.path.realpath(__file__))[0]
current_path = os.path.realpath(__file__)    
current_path = os.path.split(current_path)[0]
current_path = os.path.split(current_path)[0]

message = "{}"

form = cgi.FieldStorage()
if 'name' in form.keys():
    filename = form['name'].value
    prefix = os.path.join(current_path, 'tmp')
    os.chdir(prefix) 
    ziploc = os.path.join(prefix, "%s.zip" % filename)
    
    try:
        os.remove(ziploc)
    except:
        pass
    try:
        import zlib
        mode = zipfile.ZIP_DEFLATED
    except:
        mode = zipfile.ZIP_DEFLATED
        
    myzip = zipfile.ZipFile("%s.zip" % filename, 'w', mode) 
    myzip.write(filename + ".shp")
    myzip.write(filename + ".dbf")
    myzip.write(filename + ".shx")
    myzip.write(filename + ".prj")
    myzip.close()
     
    print "Content-type: application/octet-stream"
    print "Content-Disposition: attachment; filename=%s.zip" %(filename)
    print
   
    f = open('%s.zip' % filename, 'rb')
    print f.read()
    f.close()
    os.chdir(orig_loc)
else:
    print 'Content-Type: text/html'
    print 
    print "something wrong"

