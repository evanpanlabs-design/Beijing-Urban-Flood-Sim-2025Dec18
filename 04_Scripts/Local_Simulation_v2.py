# -*- coding: utf-8 -*-
"""
================================================================================
 QGIS Python Script: Flood Depth Simulation (Version 2)
================================================================================
 Project: Beijing Six Districts Flood Analysis (Multi-Scenario)
 Author: AI Assistant & User
 Date: 2025-12-18
 Version: 2.0 (Dynamic LU-to-CN Mapping)
================================================================================
"""

import os
import processing
import numpy as np
from osgeo import gdal
from qgis.core import (QgsRasterLayer, QgsVectorLayer, QgsVectorFileWriter,
                       QgsProcessingFeatureSourceDefinition)


# ==============================================================================
# [USER CONFIGURATION MANIFEST] 用户配置清单 (Version 2)
# ==============================================================================
class Config:
    # --------------------------------------------------------------------------
    # 1. 路径设置 (Path Settings)
    # --------------------------------------------------------------------------
    # >>> [PATH-01] 输入数据所在文件夹 (Version 2)
    INPUT_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation/01_Input/version 2"

    # >>> [PATH-02] 输出结果文件夹
    OUTPUT_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation/03_Output/version 2"

    # --------------------------------------------------------------------------
    # 2. 文件名设置 (请确保文件名与文件夹内一致)
    # --------------------------------------------------------------------------
    # >>> [FILE-01] DEM 文件
    DEM_FILENAME = "Beijing6D_DEM_30m.tif"

    # >>> [FILE-02] 流域矢量文件 (建议使用 Level 12 微型流域)
    WATERSHED_FILENAME = "Beijing_SixDistricts_Watersheds_L12.shp"

    # >>> [PARAM-01] 流域唯一ID字段名
    WATERSHED_ID_FIELD = "HYBAS_ID"

    # --------------------------------------------------------------------------
    # 3. 情景设置 (Scenarios: Year + Rainfall + LU File)
    # --------------------------------------------------------------------------
    # >>> [SCENARIO] 定义不同年份的情景
    # 结构: '情景名': {'P': 降雨量mm, 'LU_File': 土地利用文件名}
    SCENARIOS = {
        '2021_100yr': {
            'P': 297.343,
            'LU_File': "LU_2021.tif"
        },
        '2031_100yr': {
            'P': 313.994,
            'LU_File': "LU_2031.tif"
        }
    }

    # --------------------------------------------------------------------------
    # 4. 土地利用 -> CN值 映射规则 (CN Mapping)
    # --------------------------------------------------------------------------
    # >>> [MAPPING] 合作者提供的对应关系
    # 逻辑: [土地利用代码列表] : CN值 (0-100)
    # 注意: 这里已将原系数乘以100 (0.15->15, 1->100) 以适配SCS模型
    LU_TO_CN_RULES = [
        {'codes': [1, 2, 3, 4], 'cn': 15},  # 0.15 -> 15
        {'codes': [5], 'cn': 100},  # 1.0  -> 100
        {'codes': [7], 'cn': 30},  # 0.3  -> 30
        {'codes': [8], 'cn': 85}  # 0.85 -> 85
    ]
    # 未定义的代码默认 CN 值
    DEFAULT_CN = 50

    # --------------------------------------------------------------------------
    # 5. 自动构建绝对路径 (无需修改)
    # --------------------------------------------------------------------------
    DEM_PATH = os.path.join(INPUT_DIR, DEM_FILENAME)
    WATERSHED_PATH = os.path.join(INPUT_DIR, WATERSHED_FILENAME)


# ==============================================================================
# [CORE LOGIC] 核心计算逻辑
# ==============================================================================

def remap_lu_to_cn(lu_array):
    """
    将土地利用数组转换为 CN 值数组
    """
    # 创建一个默认值的 CN 数组
    cn_array = np.full_like(lu_array, Config.DEFAULT_CN, dtype=np.float32)

    # 遍历规则进行赋值
    for rule in Config.LU_TO_CN_RULES:
        codes = rule['codes']
        cn_val = rule['cn']
        # 使用 numpy 的 isin 函数快速查找
        mask = np.isin(lu_array, codes)
        cn_array[mask] = cn_val

    return cn_array


def calculate_scs_volume(P, avg_cn, area_m2):
    """计算总径流体积 (SCS-CN模型)"""
    if avg_cn <= 10 or avg_cn > 100: return 0
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
    high = max_elev + (max_elev - min_elev) * 0.1  # 10% buffer

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
    print("   开始执行雨洪淹没模拟 (Version 2 - Multi-LU)")
    print("==================================================")

    if not os.path.exists(Config.OUTPUT_DIR):
        os.makedirs(Config.OUTPUT_DIR)
        print(f"已创建输出目录: {Config.OUTPUT_DIR}")

    # 1. 加载基础图层
    dem_layer = QgsRasterLayer(Config.DEM_PATH, "DEM")
    ws_layer = QgsVectorLayer(Config.WATERSHED_PATH, "Watersheds", "ogr")

    if not dem_layer.isValid() or not ws_layer.isValid():
        print("[错误] 无法加载 DEM 或 流域数据，请检查路径！")
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
        print(f"\n>>> [{idx + 1}/{total_feats}] 处理流域 ID: {ws_id}")

        # 定义临时文件路径
        temp_mask_shp = os.path.join(Config.OUTPUT_DIR, f'mask_{ws_id}.shp')
        temp_dem_clip = os.path.join(Config.OUTPUT_DIR, f'temp_dem_{ws_id}.tif')

        try:
            # ------------------------------------------------------
            # 步骤 A: 物理提取当前流域 (Mask)
            # ------------------------------------------------------
            temp_layer = QgsVectorLayer(f"Polygon?crs={ws_layer.crs().authid()}", "temp", "memory")
            prov = temp_layer.dataProvider()
            prov.addFeatures([feature])
            QgsVectorFileWriter.writeAsVectorFormat(temp_layer, temp_mask_shp, "UTF-8", ws_layer.crs(),
                                                    "ESRI Shapefile")

            # ------------------------------------------------------
            # 步骤 B: 裁剪 DEM
            # ------------------------------------------------------
            processing.run("gdal:cliprasterbymasklayer", {
                'INPUT': Config.DEM_PATH, 'MASK': temp_mask_shp, 'NODATA': -9999,
                'KEEP_RESOLUTION': True, 'OUTPUT': temp_dem_clip
            })

            ds_dem = gdal.Open(temp_dem_clip)
            if not ds_dem: continue
            arr_dem = ds_dem.ReadAsArray()
            nodata_val = ds_dem.GetRasterBand(1).GetNoDataValue()

            # ------------------------------------------------------
            # 步骤 C: 循环处理不同年份的情景 (2021, 2031)
            # ------------------------------------------------------
            for sc_name, sc_params in Config.SCENARIOS.items():
                P = sc_params['P']
                lu_filename = sc_params['LU_File']
                lu_path = os.path.join(Config.INPUT_DIR, lu_filename)

                if not os.path.exists(lu_path):
                    print(f"   [警告] 找不到土地利用文件: {lu_filename}，跳过该情景。")
                    continue

                # C1. 裁剪并重采样当前年份的 Land Use
                temp_lu_clip = os.path.join(Config.OUTPUT_DIR, f'temp_lu_{ws_id}_{sc_name}.tif')

                # 获取临时DEM的范围，确保LU完全对齐
                temp_dem_layer = QgsRasterLayer(temp_dem_clip, "TempDEM")

                processing.run("gdal:warpreproject", {
                    'INPUT': lu_path,
                    'TARGET_CRS': crs,
                    'TARGET_EXTENT': temp_dem_layer.extent(),
                    'TARGET_RESOLUTION': pixel_size_x,
                    'RESAMPLING': 0,  # Nearest Neighbour
                    'NODATA': 0,
                    'OUTPUT': temp_lu_clip
                })

                # C2. 读取 LU 并转换为 CN
                ds_lu = gdal.Open(temp_lu_clip)
                if not ds_lu: continue
                arr_lu = ds_lu.ReadAsArray()

                # *** 核心: 动态映射 CN 值 ***
                arr_cn = remap_lu_to_cn(arr_lu)

                # C3. 计算有效区域
                # 有效 = DEM有值 且 LU有值(非0)
                valid_mask = (arr_dem != nodata_val) & (arr_lu > 0)

                if np.sum(valid_mask) > 0:
                    ws_cn_values = arr_cn[valid_mask]
                    avg_cn = np.mean(ws_cn_values)
                    ws_area = np.sum(valid_mask) * pixel_area
                    dem_valid = arr_dem[valid_mask]

                    # C4. 计算体积与水位
                    target_vol = calculate_scs_volume(P, avg_cn, ws_area)
                    flood_elev = find_flood_elevation(dem_valid, target_vol, pixel_area)

                    print(f"   -> {sc_name}: P={P:.1f} | AvgCN={avg_cn:.1f} | 水位={flood_elev:.2f}m")

                    # C5. 计算深度并输出
                    flood_depth = np.zeros_like(arr_dem, dtype=np.float32)
                    flood_condition = valid_mask & (arr_dem < flood_elev)

                    if np.any(flood_condition):
                        flood_depth[flood_condition] = flood_elev - arr_dem[flood_condition]

                    out_tif = os.path.join(Config.OUTPUT_DIR, f'Flood_{ws_id}_{sc_name}.tif')
                    driver = gdal.GetDriverByName('GTiff')
                    out_ds = driver.Create(out_tif, ds_dem.RasterXSize, ds_dem.RasterYSize, 1, gdal.GDT_Float32)
                    out_ds.SetGeoTransform(ds_dem.GetGeoTransform())
                    out_ds.SetProjection(ds_dem.GetProjection())
                    out_ds.GetRasterBand(1).WriteArray(flood_depth)
                    out_ds.GetRasterBand(1).SetNoDataValue(0)
                    out_ds = None

                # 清理 LU 临时文件
                ds_lu = None
                if os.path.exists(temp_lu_clip): 
                    try: os.remove(temp_lu_clip) 
                    except: pass

            ds_dem = None

        except Exception as e:
            print(f"   [异常] {e}")

        finally:
            # 清理 DEM 和 Mask 临时文件
            base_shp = temp_mask_shp.replace('.shp', '')
            for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.tif']:
                f = base_shp + ext
                if os.path.exists(f): 
                    try: os.remove(f) 
                    except: pass
            if os.path.exists(temp_dem_clip): 
                try: os.remove(temp_dem_clip) 
                except: pass

    print("\n==================================================")
    print("全部完成！请检查 version 2 输出目录。")
    print("==================================================")


# 执行主程序
main()