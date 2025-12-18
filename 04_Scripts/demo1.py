# -*- coding: utf-8 -*-
"""
================================================================================
 QGIS Python Script: Flood Depth Simulation (SCS-CN Model)
================================================================================
 Project: Beijing Flood Analysis
 Author: AI Assistant & User
 Environment: QGIS 3.36 + PyQGIS
 Version: Depth Output Version (Float32)
================================================================================
"""

import os
import processing
import numpy as np
from osgeo import gdal
from qgis.core import (QgsRasterLayer, QgsVectorLayer, QgsVectorFileWriter, 
                       QgsProject, QgsFeature)

# ==============================================================================
# [USER CONFIGURATION MANIFEST] 用户配置清单
# ==============================================================================
class Config:
    # --------------------------------------------------------------------------
    # 1. 路径设置 (Path Settings)
    # --------------------------------------------------------------------------
    # >>> [PATH-01] 项目根目录
    BASE_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation"
    
    # >>> [PATH-02] 输入文件夹
    INPUT_DIR = os.path.join(BASE_DIR, "01_Input")
    
    # >>> [PATH-03] 输出文件夹
    OUTPUT_DIR = os.path.join(BASE_DIR, "03_Output")
    
    # --------------------------------------------------------------------------
    # 2. 自动构建完整路径
    # --------------------------------------------------------------------------
    DEM_PATH = os.path.join(INPUT_DIR, "Beijing_DEM_30m.tif")
    CN_PATH = os.path.join(INPUT_DIR, "Beijing_CN_10m.tif")
    WATERSHED_PATH = os.path.join(INPUT_DIR, "Beijing_Watersheds_L8.shp")
    
    # --------------------------------------------------------------------------
    # 3. 字段与参数设置
    # --------------------------------------------------------------------------
    # >>> [PARAM-01] 流域唯一ID字段名
    WATERSHED_ID_FIELD = "HYBAS_ID"
    
    # >>> [PARAM-02] 降雨情景 (mm)
    RAINFALL_SCENARIOS = {
        '10yr':  115.0,
        '50yr':  170.0,
        '100yr': 230.0
    }

# ==============================================================================
# [CORE LOGIC] 核心计算逻辑
# ==============================================================================

def calculate_scs_volume(P, avg_cn, area_m2):
    """计算总径流体积 (SCS-CN模型)"""
    if avg_cn <= 10 or avg_cn >= 100: return 0
    S = (25400.0 / avg_cn) - 254.0
    Ia = 0.2 * S
    if P <= Ia:
        Q_depth_mm = 0
    else:
        Q_depth_mm = ((P - Ia) ** 2) / (P - Ia + S)
    return (Q_depth_mm / 1000.0) * area_m2

def get_volume_below_elevation(dem_array, pixel_area, elevation):
    """计算DEM数组中，低于指定高程的空隙体积"""
    depths = elevation - dem_array
    depths[depths < 0] = 0
    return np.sum(depths) * pixel_area

def find_flood_elevation(dem_array_valid, target_vol, pixel_area):
    """二分查找法：寻找对应体积的水位高程"""
    if target_vol <= 0: return np.min(dem_array_valid)
    min_elev = np.min(dem_array_valid)
    max_elev = np.max(dem_array_valid)
    low = min_elev
    high = max_elev + (max_elev - min_elev) * 0.1
    
    for _ in range(25):
        mid = (low + high) / 2
        calc_vol = get_volume_below_elevation(dem_array_valid, pixel_area, mid)
        if calc_vol < target_vol:
            low = mid
        else:
            high = mid
    return high

def main():
    print("==================================================")
    print("   开始执行雨洪淹没模拟 (输出深度版)")
    print("==================================================")
    
    if not os.path.exists(Config.OUTPUT_DIR):
        os.makedirs(Config.OUTPUT_DIR)

    # 1. 加载图层
    dem_layer = QgsRasterLayer(Config.DEM_PATH, "DEM")
    ws_layer = QgsVectorLayer(Config.WATERSHED_PATH, "Watersheds", "ogr")
    
    if not dem_layer.isValid() or not ws_layer.isValid():
        print("[错误] 无法加载数据，请检查路径！")
        return

    # 获取DEM信息
    pixel_size_x = dem_layer.rasterUnitsPerPixelX()
    pixel_size_y = dem_layer.rasterUnitsPerPixelY()
    pixel_area = abs(pixel_size_x * pixel_size_y)
    crs = dem_layer.crs()

    # 2. 遍历流域
    features = ws_layer.getFeatures()
    total_feats = ws_layer.featureCount()
    
    print(f"共检测到 {total_feats} 个流域，开始处理...")
    
    for idx, feature in enumerate(features):
        ws_id = feature[Config.WATERSHED_ID_FIELD]
        print(f"\n>>> [{idx+1}/{total_feats}] 处理流域 ID: {ws_id}")
        
        # 定义临时文件路径
        temp_mask_shp = os.path.join(Config.OUTPUT_DIR, f'mask_{ws_id}.shp')
        temp_dem_clip = os.path.join(Config.OUTPUT_DIR, f'temp_dem_{ws_id}.tif')
        temp_cn_clip = os.path.join(Config.OUTPUT_DIR, f'temp_cn_{ws_id}.tif')
        
        try:
            # 步骤 A: 创建临时 Shapefile
            temp_layer = QgsVectorLayer(f"Polygon?crs={ws_layer.crs().authid()}", "temp", "memory")
            prov = temp_layer.dataProvider()
            prov.addFeatures([feature])
            QgsVectorFileWriter.writeAsVectorFormat(temp_layer, temp_mask_shp, "UTF-8", ws_layer.crs(), "ESRI Shapefile")
            
            # 步骤 B: 裁剪 DEM
            processing.run("gdal:cliprasterbymasklayer", {
                'INPUT': Config.DEM_PATH, 'MASK': temp_mask_shp, 'NODATA': -9999,
                'KEEP_RESOLUTION': True, 'OUTPUT': temp_dem_clip
            })
            
            # 步骤 C: 裁剪并重采样 CN
            temp_dem_layer = QgsRasterLayer(temp_dem_clip, "TempDEM")
            if not temp_dem_layer.isValid(): continue

            processing.run("gdal:warpreproject", {
                'INPUT': Config.CN_PATH, 'TARGET_CRS': crs,
                'TARGET_EXTENT': temp_dem_layer.extent(), 'TARGET_RESOLUTION': pixel_size_x,
                'RESAMPLING': 0, 'NODATA': 0, 'OUTPUT': temp_cn_clip
            })

            # 步骤 D: 读取与计算
            ds_dem = gdal.Open(temp_dem_clip)
            ds_cn = gdal.Open(temp_cn_clip)
            
            if ds_dem and ds_cn:
                arr_dem = ds_dem.ReadAsArray()
                arr_cn = ds_cn.ReadAsArray()
                
                nodata_val = ds_dem.GetRasterBand(1).GetNoDataValue()
                valid_mask = (arr_dem != nodata_val) & (arr_cn > 0)
                
                if np.sum(valid_mask) > 0:
                    ws_cn_values = arr_cn[valid_mask]
                    avg_cn = np.mean(ws_cn_values)
                    ws_area = np.sum(valid_mask) * pixel_area
                    dem_valid = arr_dem[valid_mask]

                    for scenario, P in Config.RAINFALL_SCENARIOS.items():
                        target_vol = calculate_scs_volume(P, avg_cn, ws_area)
                        flood_elev = find_flood_elevation(dem_valid, target_vol, pixel_area)
                        
                        print(f"   -> {scenario}: P={P} | CN={avg_cn:.1f} | 水位={flood_elev:.2f}m")
                        
                        # ------------------------------------------------------
                        # [关键修改] 计算淹没深度 (Depth = WaterLevel - DEM)
                        # ------------------------------------------------------
                        # 初始化深度数组 (Float32)
                        flood_depth = np.zeros_like(arr_dem, dtype=np.float32)
                        
                        # 淹没条件: 有效区域 且 地面低于水位
                        flood_condition = valid_mask & (arr_dem < flood_elev)
                        
                        # 计算深度
                        if np.any(flood_condition):
                            flood_depth[flood_condition] = flood_elev - arr_dem[flood_condition]
                        
                        # ------------------------------------------------------
                        # 保存为 Float32 格式
                        # ------------------------------------------------------
                        out_tif = os.path.join(Config.OUTPUT_DIR, f'Flood_{ws_id}_{scenario}.tif')
                        driver = gdal.GetDriverByName('GTiff')
                        # 注意这里使用 GDT_Float32
                        out_ds = driver.Create(out_tif, ds_dem.RasterXSize, ds_dem.RasterYSize, 1, gdal.GDT_Float32)
                        out_ds.SetGeoTransform(ds_dem.GetGeoTransform())
                        out_ds.SetProjection(ds_dem.GetProjection())
                        out_ds.GetRasterBand(1).WriteArray(flood_depth)
                        out_ds.GetRasterBand(1).SetNoDataValue(0) # 0表示无淹没
                        out_ds = None
            
            ds_dem = None
            ds_cn = None

        except Exception as e:
            print(f"   [异常] {e}")
            
        finally:
            # 清理临时文件
            # 1. 清理 Shapefile 及其附属文件
            base_shp = temp_mask_shp.replace('.shp', '')
            # 遍历所有可能的扩展名
            for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.tif']:
                f = base_shp + ext
                # 必须分行写，不能写在一行
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass # 如果删不掉（比如被占用），就跳过，不报错
            
            # 2. 清理单独定义的 TIF 临时文件
            if os.path.exists(temp_dem_clip):
                try:
                    os.remove(temp_dem_clip)
                except:
                    pass
            
            if os.path.exists(temp_cn_clip):
                try:
                    os.remove(temp_cn_clip)
                except:
                    pass
    print("\n==================================================")
    print("全部完成！输出结果现在包含淹没深度信息。")
    print("==================================================")

# 执行主程序
main()