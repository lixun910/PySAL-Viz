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
    
test_cartodb()