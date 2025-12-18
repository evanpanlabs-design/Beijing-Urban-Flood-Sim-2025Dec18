// =======================================================
// 1. 定义研究区：使用用户上传的高精度北京市边界
// =======================================================

// 读取用户上传的 Asset
var beijing = ee.FeatureCollection("projects/personalresearchpyx/assets/Beijing6districts");

// 获取几何形状 (用于后续裁剪和导出范围)
var region_geom = beijing.geometry();

Map.centerObject(beijing, 9);
Map.addLayer(beijing, {color: 'red', fillColor: '00000000'}, 'Beijing High-Res Boundary');

// =======================================================
// 2. 获取数据源
// =======================================================

// --- 2.1 DEM 数据 (NASADEM 30m) ---
var dem = ee.Image("NASA/NASADEM_HGT/001")
    .select('elevation')
    .clip(beijing); // 使用高精度边界裁剪

Map.addLayer(dem, {min: 0, max: 2000, palette: ['green', 'yellow', 'brown']}, 'DEM');

// --- 2.2 土地利用数据 (ESA WorldCover 10m v200) ---
var worldcover = ee.ImageCollection("ESA/WorldCover/v200")
    .first()
    .clip(beijing);

Map.addLayer(worldcover, {}, 'Land Use');

// --- 2.3 流域数据 (HydroATLAS Level 08) ---
// 筛选与高精度北京边界相交的流域
var watersheds = ee.FeatureCollection("WWF/HydroATLAS/v1/Basins/level12")
    .filterBounds(beijing);

print('关联流域数量:', watersheds.size());
Map.addLayer(watersheds, {color: 'blue'}, 'Watersheds');

// =======================================================
// 3. 数据预处理：生成 CN 值栅格
// =======================================================
// 映射关系：[原始分类代码] -> [CN值]
var fromValues = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100];
var toValues   = [36, 48, 61, 78, 92, 85, 30, 100, 100, 100, 85];

var cn_raster = worldcover.remap(fromValues, toValues)
    .rename('CN')
    .toByte()
    .clip(beijing);

Map.addLayer(cn_raster, {min: 30, max: 100, palette: ['blue', 'green', 'red']}, 'CN Raster');

// =======================================================
// 4. 数据导出
// =======================================================
var crs_target = 'EPSG:32650'; // UTM Zone 50N

// 4.1 导出 DEM
Export.image.toDrive({
  image: dem,
  description: 'Beijing_DEM_30m',
  folder: 'Flood_Analysis_Input',
  region: region_geom, // 使用高精度几何范围
  scale: 30,
  crs: crs_target,
  maxPixels: 1e13
});

// 4.2 导出 CN 栅格
Export.image.toDrive({
  image: cn_raster,
  description: 'Beijing_CN_10m',
  folder: 'Flood_Analysis_Input',
  region: region_geom,
  scale: 10,
  crs: crs_target,
  maxPixels: 1e13
});

// =======================================================
// 4.3 导出流域矢量 (修正版：解决字段超限问题)
// =======================================================

// HydroATLAS 字段太多(>255)，Shapefile 存不下。
// 我们只保留核心字段：
// HYBAS_ID: 唯一ID (Python脚本必须用)
// UP_AREA: 上游集水面积 (参考用)
// ORDER: 河流等级 (参考用)

var watersheds_export = watersheds.select(['HYBAS_ID', 'UP_AREA', 'ORDER']);

Export.table.toDrive({
  collection: watersheds_export,
  description: 'Beijing_Watersheds_L12',
  folder: 'Flood_Analysis_Input',
  fileFormat: 'SHP'
});