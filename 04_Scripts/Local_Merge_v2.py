# -*- coding: utf-8 -*-
"""
================================================================================
 QGIS Python Script: Merge Results (Version 2)
================================================================================
 Project: Beijing Six Districts Flood Analysis
 Author: AI Assistant & User
 Date: 2025-12-18
================================================================================
"""

import os
import glob
import processing

# ================= 配置区域 (Version 2) =================
# >>> [PATH] 输入目录 (必须与模拟脚本的输出目录一致)
INPUT_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation/03_Output/version 2"

# >>> [PATH] 合并结果存放目录
MERGE_OUTPUT_DIR = os.path.join(INPUT_DIR, "Merged_Results")

if not os.path.exists(MERGE_OUTPUT_DIR):
    os.makedirs(MERGE_OUTPUT_DIR)

# >>> [SCENARIO] 需要合并的情景名称列表
# 必须与模拟脚本中生成的后缀一致
scenarios = ['2021_100yr', '2031_100yr']

print("==================================================")
print("   开始合并淹没深度栅格 (Version 2)")
print("==================================================")

for sc in scenarios:
    # 1. 寻找文件
    # 匹配模式: Flood_任意ID_情景名.tif
    search_pattern = os.path.join(INPUT_DIR, f"Flood_*_{sc}.tif")
    files = glob.glob(search_pattern)

    if len(files) == 0:
        print(f"[警告] 没有找到情景 {sc} 的任何文件！")
        continue

    print(f"正在合并情景: {sc}")
    print(f" -> 找到 {len(files)} 个分块文件")

    # 2. 定义输出文件
    output_file = os.path.join(MERGE_OUTPUT_DIR, f"Final_Flood_Depth_{sc}.tif")

    # 3. 调用 GDAL Merge
    try:
        processing.run("gdal:merge", {
            'INPUT': files,
            'PCT': False,
            'SEPARATE': False,
            'NODATA_INPUT': 0,
            'NODATA_OUTPUT': 0,
            'OPTIONS': '',
            'DATA_TYPE': 6,  # 6 = Float32 (保留深度小数)
            'OUTPUT': output_file
        })
        print(f" -> [成功] 已生成: {output_file}")
    except Exception as e:
        print(f" -> [失败] 合并出错: {e}")

print("\n==================================================")
print("所有合并工作完成！")
print(f"结果保存在: {MERGE_OUTPUT_DIR}")
print("==================================================")