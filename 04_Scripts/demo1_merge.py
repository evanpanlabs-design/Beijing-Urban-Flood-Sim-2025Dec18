import os
import glob
import processing

# ================= 配置 =================
INPUT_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation/03_Output"
MERGE_OUTPUT_DIR = "E:/THESIS/99-Archive/Dec17_Precipitation/03_Output/Merged_Results"

if not os.path.exists(MERGE_OUTPUT_DIR):
    os.makedirs(MERGE_OUTPUT_DIR)

scenarios = ['10yr', '50yr', '100yr']

print("开始合并淹没深度栅格...")

for sc in scenarios:
    search_pattern = os.path.join(INPUT_DIR, f"Flood_*_{sc}.tif")
    files = glob.glob(search_pattern)
    
    if len(files) == 0:
        print(f"警告: 没有找到 {sc} 情景的文件！")
        continue
        
    print(f"正在合并 {sc} 情景，共 {len(files)} 个文件...")
    output_file = os.path.join(MERGE_OUTPUT_DIR, f"Final_Flood_Depth_{sc}.tif")
    
    try:
        processing.run("gdal:merge", {
            'INPUT': files,
            'PCT': False,
            'SEPARATE': False,
            'NODATA_INPUT': 0,
            'NODATA_OUTPUT': 0,
            'OPTIONS': '',
            # [关键修改] 6 代表 Float32，保留小数深度
            'DATA_TYPE': 6, 
            'OUTPUT': output_file
        })
        print(f" -> 成功生成: {output_file}")
    except Exception as e:
        print(f" -> 合并失败: {e}")

print("所有合并工作完成！")