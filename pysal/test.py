def test_cartodb():
    import pysal
    
    # load San Francisco plots data using PySAL
    shp_path = "../test_data/sfpd_plots.shp"
    plots_shp = pysal.open(shp_path)
    plots_dbf = pysal.open(shp_path[:-3]+"dbf")     
    
    import d3viz
    d3viz.setup()    
    
    d3viz.show_map(plots_shp)
    
    shp_path = "/data/sf_cartheft.shp"
    crime_shp = pysal.open(shp_path)
    crime_dbf = pysal.open(shp_path[:-3]+"dbf")
    
    d3viz.show_map(crime_shp)    
    
    d3viz.quantile_map(plots_shp,'cartheft',5)
    
    user_name = 'lixun910'
    api_key = '340808e9a453af9680684a65990eb4eb706e9b56'
    
    d3viz.setup_cartodb(api_key, user_name)    
    
    plots_table = d3viz.cartodb_upload(plots_shp)
    crime_table = d3viz.cartodb_upload(crime_shp)
    print plots_table
    print crime_table    
    
    d3viz.cartodb_show_maps(plots_shp, layers=[{'shp':crime_shp}])
    
    d3viz.cartodb_show_maps(plots_shp, layers=[{'shp':crime_shp, 'css':d3viz.CARTO_CSS_POINT_CLOUD}])
    
    new_cnt_col = "mycnt"
    d3viz.cartodb_count_pts_in_polys(plots_table, crime_table, new_cnt_col)    
    
    shp_path = d3viz.cartodb_get_data(plots_table, [new_cnt_col])
    
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
    w = pysal.rook_from_shapefile(shp_path)    
    
    import numpy as np
    y = np.array(dbf.by_col[new_cnt_col])
    lm = pysal.Moran_Local(y, w)
    
    new_lisa_table = "cartheft_lisa" 
    new_lisa_table = d3viz.cartodb_lisa(lm, new_lisa_table)    
    
    d3viz.cartodb_show_lisa_map(shp, new_lisa_table, uuid=plots_table)
    
    d3viz.cartodb_show_lisa_map(shp, new_lisa_table, uuid=plots_table, layers=[{'shp':crime_shp, 'css':d3viz.CARTO_CSS_POINT_CLOUD}])
    
    d3viz.quantile_map(shp, new_cnt_col, 5)
    
    d3viz.quantile_map(shp, new_cnt_col, 5, basemap="leaflet_map")
    
    d3viz.close_all()
    
def test_network():
    import pysal

    road_shp = pysal.open('../test_data/man_road.shp')    
    road_dbf = pysal.open('../test_data/man_road.dbf')    
    
    import d3viz
    d3viz.setup()

    d3viz.show_map(road_shp, rebuild=True)
    
    roadJsonFile = d3viz.get_json_path(road_shp)
    
    import network_cluster 
    #roadJsonFile = '../test_data/man_road.geojson'
    network = network_cluster.NetworkCluster(roadJsonFile)    

    # Segment the road network equally in 1,000 feet
    network.SegmentNetwork(1000) 
    
    # Read into car accident points file
    points_shp = pysal.open('../test_data/man_points.shp')
    d3viz.add_layer(points_shp)
    pointsJsonFile = d3viz.get_json_path(points_shp)
    points = network_cluster.GetJsonPoints(pointsJsonFile)    

    # Snap these points to nearest road segment
    network.SnapPointsToNetwork(points)    

    # Export the counts of points on each road segment to a new ShapeFile
    road_count_file = "../test_data/man_seg_road.shp"    
    network.ExportCountsToShp(road_count_file)
   
    road_shp = pysal.open(road_count_file)    
    d3viz.show_map(road_shp)    
    d3viz.equal_interval_map(road_shp, 'cnt', 5)
    
    # Visualization with CartoDB
    d3viz.setup_cartodb("340808e9a453af9680684a65990eb4eb706e9b56","lixun910")    

    # add a projection file, which is same with the points or road shape file
    import shutil
    shutil.copyfile("../test_data/man_points.prj", "../test_data/man_seg_road.prj")
    
    # upload the map to CartoDB since the Projection is not WGS
    road_table = d3viz.cartodb_upload(road_count_file)    
    
    # download the map with WGS84 projection
    # NOTE: this is required since brush/link with CartoDB requires WGS84 projection (only)
    prj_road_count_file = d3viz.cartodb_get_data(road_table, fields=[],loc="../test_data/")
    print prj_road_count_file    

    # Use PySAL to do LISA analysis
    
    road_shp = pysal.open(prj_road_count_file)
    road_dbf = pysal.open(prj_road_count_file[:-3] + "dbf")
    
    # show the basic map
    d3viz.show_map(road_shp, uuid=road_table, rebuild=True)    

    # show the map in CartoDB
    d3viz.cartodb_show_maps(road_shp, uuid=road_table)   
    
    # show quantile map in CartoDB
    d3viz.cartodb_quantile_map(road_shp, 'cnt', 5, uuid=road_table)    

    # Create a Queen Contiguity Weights based on the segmentation
    #network.CreateWeights()    

    # Export Weights to a GAL file
    roadWFile = '../test_data/man_road.gal'
    #network.ExportWeights(roadWFile)    
    
    # LISA
    import numpy as np
    road_w = pysal.open(roadWFile).read()    
    y = np.array(road_dbf.by_col["cnt"])
    lm = pysal.Moran_Local(y, road_w)    

    # Create a table on CartoDB to store LISA results
    new_lisa_table = "road_lisa"
    new_lisa_table = d3viz.cartodb_lisa(lm, new_lisa_table)    

    # Show LISA results in a map using CartoDB
    d3viz.cartodb_show_lisa_map(road_shp, "road_lisa", uuid=road_table)    

    d3viz.close_all()
    
def test():
    import pysal

    road_shp = pysal.open('/Users/xun/Dropbox/dog_bites/phoenix.osm-roads.shp')    
    road_dbf = pysal.open('/Users/xun/Dropbox/dog_bites/phoenix.osm-roads.dbf')    
    
    import d3viz
    d3viz.setup()

    d3viz.show_map(road_shp, rebuild=True)
    
    roadJsonFile = d3viz.get_json_path(road_shp)
    
    import network_cluster 
    #roadJsonFile = '../test_data/man_road.geojson'
    network = network_cluster.NetworkCluster(roadJsonFile)    

    # Segment the road network equally in 1,000 feet
    network.SegmentNetwork(1000) 
    
    # Read into car accident points file
    points_shp = pysal.open('/Users/xun/Dropbox/dog_bites/DogBitesOriginal/DogBitesOriginal.shp')
    d3viz.add_layer(points_shp)
    pointsJsonFile = d3viz.get_json_path(points_shp)
    points = network_cluster.GetJsonPoints(pointsJsonFile, encoding='latin-1')    

    # Snap these points to nearest road segment
    network.SnapPointsToNetwork(points)    

def test1():
    import d3viz
    d3viz.setup()   
    user_name = 'lixun910'
    api_key = '340808e9a453af9680684a65990eb4eb706e9b56'
    
    d3viz.setup_cartodb(api_key, user_name)    

    import pysal
    
    # load PHX block grounp data using PySAL
    shp_path = "/Users/xun/Dropbox/dog_bites/phx_selected.shp"
    plots_shp = pysal.open(shp_path)
    plots_dbf = pysal.open(shp_path[:-3]+"dbf") 
    
    plots_table = d3viz.cartodb_upload(plots_shp)    
    d3viz.show_map(plots_shp, rebuild=True)
    
    """
    Read and show dog bites data in the same area
    """
    dog_shp_path = "/Users/xun/Dropbox/dog_bites/DogBitesOriginal/dogbites.shp"
    dog_shp = pysal.open(dog_shp_path)
    dog_dbf = pysal.open(dog_shp_path[:-3]+"dbf")
    
    d3viz.add_layer(dog_shp)
    
    dog_table = d3viz.cartodb_upload(dog_shp)    

    """
    Read and show foreclosure data in the same area
    """
    shp_path = "/Users/xun/Dropbox/dog_bites/home_points.shp"
    home_shp = pysal.open(shp_path)
    home_dbf = pysal.open(shp_path[:-3]+"dbf")
    
    d3viz.add_layer(home_shp)
    
    home_table = d3viz.cartodb_upload(home_shp)

    dog_cnt_col = "dog_cnt"
    d3viz.cartodb_count_pts_in_polys(plots_table, dog_table, dog_cnt_col)
    print dog_cnt_col, " added."    

    home_cnt_col = "home_cnt"
    d3viz.cartodb_count_pts_in_polys(plots_table, home_table, home_cnt_col)
    print home_cnt_col, " added."   
    
    """
    Download the counting data for spatial analysis using PySAL
    """
    shp_path = d3viz.cartodb_get_data(plots_table, ["cartodb_id", dog_cnt_col, home_cnt_col])
    
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
    
    d3viz.show_map(shp, uuid=plots_table, rebuild=True)    
    
    d3viz.cartodb_show_maps(plots_shp, uuid=plots_table)
    #d3viz.cartodb_show_maps(plots_shp, layers=[{'shp':dog_shp}])
    #d3viz.cartodb_show_maps(plots_shp, layers=[{'shp':dog_shp}])    
    
    """
    Run LISA and store results in CartoDB in a new table ~ 5 seconds
    """
    w = pysal.queen_from_shapefile(shp_path)
    
    import numpy as np
    y = np.array(dbf.by_col[dog_cnt_col])
    
    dog_lm = pysal.Moran_Local(y, w)
    
    d3viz.lisa_map(shp, dog_cnt_col, dog_lm, uuid=plots_table)
    
    dog_lisa_table = "dog_lisa" 
    cartodb_ids = dbf.by_col["cartodb_id"]
    dog_lisa_table = d3viz.cartodb_lisa(dog_lm, dog_lisa_table, cartodb_ids=cartodb_ids)
    
    d3viz.cartodb_show_lisa_map(shp, dog_lisa_table, uuid=plots_table)    
    
    y = np.array(dbf.by_col[home_cnt_col])
    
    home_lm = pysal.Moran_Local(y, w)
    
    home_lisa_table = "home_lisa" 
    home_lisa_table = d3viz.cartodb_lisa(home_lm, home_lisa_table, cartodb_ids=cartodb_ids)
    
    d3viz.cartodb_show_lisa_map(shp, home_lisa_table, uuid=plots_table)    
    
    road_shp = pysal.open('/Users/xun/Dropbox/dog_bites/man_seg_road.shp')    
    road_dbf = pysal.open('/Users/xun/Dropbox/dog_bites/man_seg_road.dbf')   
    road_table = d3viz.cartodb_upload(road_shp)    
    
    shp_path = d3viz.cartodb_get_data(road_table)
    
    shp = pysal.open(shp_path)
    dbf = pysal.open(shp_path[:-3]+"dbf") 
    
    d3viz.add_layer(shp, uuid=road_table)
    d3viz.cartodb_show_maps(shp, uuid=road_table)
    d3viz.natural_map(shp, 'cnt', 5, )
    d3viz.natural_map(shp, 'cnt', 5, basemap="leaflet_map")
    

def test2():
    #d6cd52286e5d3e9e08a5a42489180df3.shp
    import pysal
    shp = pysal.open('../www/tmp/d6cd52286e5d3e9e08a5a42489180df3.shp')
    dbf = pysal.open('../www/tmp/d6cd52286e5d3e9e08a5a42489180df3.dbf')        
    
    w = pysal.queen_from_shapefile('../www/tmp/d6cd52286e5d3e9e08a5a42489180df3.shp')
    #d3viz.moran_scatter_plot(shp, dbf, "dog_cnt", w)    
    import numpy as np
    y = np.array(dbf.by_col["dog_cnt"])
    lm = pysal.Moran_Local(y, w)    
    
    for i,j in enumerate(lm.q):
        if lm.p_sim[i] >= 0.05:
            print 0
        else:
            print j
        
    import d3viz
    d3viz.setup()
    
    d3viz.show_map(shp)
    d3viz.scatter_plot(shp, ["dog_cnt","home_cnt"])
    
    d3viz.lisa_map(shp, "dog_cnt", lm)
#test_network()
#test_cartodb()
test1()