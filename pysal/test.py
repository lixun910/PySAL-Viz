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
    from network_cluster import NetworkCluster
    
    roadJsonFile = '../test_data/man_road.geojson'
    network = NetworkCluster(roadJsonFile)    

    # Segment the road network equally in 1,000 feet
    network.SegmentNetwork(1000) 
    
    # Create a Queen Contiguity Weights based on the segmentation
    #network.CreateWeights()    

    # Export Weights to a GAL file
    roadWFile = '../test_data/man_road.gal'
    #network.ExportWeights(roadWFile)    
    
    # Read into car accident points file
    from network_cluster import GetJsonPoints
    pointsJsonFile = "../test_data/man_points.geojson"
    points = GetJsonPoints(pointsJsonFile)    

    # Snap these points to nearest road segment
    network.SnapPointsToNetwork(points)    

    # Export the counts of points on each road segment to a new ShapeFile
    road_count_file = "../test_data/man_seg_road.shp"    
    network.ExportCountsToShp(road_count_file)
    
    # Visualization with CartoDB
    import d3viz
    d3viz.setup()
    d3viz.setup_cartodb("340808e9a453af9680684a65990eb4eb706e9b56","lixun910")    

    # add a projection file, which is same with the points or road shape file
    import shutil
    shutil.copyfile("../test_data/man_points.prj", "../test_data/man_seg_road.prj")
    
    # upload the map to CartoDB since the Projection is not WGS
    road_table = d3viz.cartodb_upload(road_count_file)    
    
    # download the map with WGS84 projection
    # NOTE: this is required since brush/link with CartoDB requires WGS84 projection (only)
    prj_road_count_file = d3viz.cartodb_get_data(road_table, fields=[], loc="../test_data/")
    print prj_road_count_file    

    # Use PySAL to do LISA analysis
    import pysal
    
    road_shp = pysal.open(prj_road_count_file)
    road_dbf = pysal.open(prj_road_count_file[:-3] + "dbf")
    road_w = pysal.open(roadWFile).read()    

    # show the basic map
    d3viz.show_map(road_shp, road_dbf, uuid=road_table)    

    # show the map in CartoDB
    d3viz.cartodb_show_maps(road_shp, uuid=road_table)   
    
    # show quantile map in CartoDB
    d3viz.cartodb_quantile_map(road_shp, 'cnt', 5, uuid=road_table)    

    # LISA
    import numpy as np
    y = np.array(road_dbf.by_col["cnt"])
    lm = pysal.Moran_Local(y, road_w)    

    # Create a table on CartoDB to store LISA results
    new_lisa_table = "road_lisa"
    new_lisa_table = d3viz.cartodb_lisa(lm, new_lisa_table)    

    # Show LISA results in a map using CartoDB
    d3viz.cartodb_show_lisa_map(road_shp, "road_lisa", uuid=road_table)    

    d3viz.close_all()
    
test_cartodb()
#test_network()