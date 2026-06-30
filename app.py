"""
无人机飞行监控与航线规划系统 - Streamlit主应用
"""
import streamlit as st
import folium
from folium.plugins import Draw, Fullscreen, MiniMap
from streamlit_folium import st_folium
import json
import math
import time
import numpy as np
from datetime import datetime

# 导入自定义模块
from coordinate_transform import wgs84_to_gcj02, gcj02_to_wgs84, haversine_distance
from obstacle_manager import ObstacleManager
from path_planner import PathPlanner
from flight_monitor import FlightMonitor
from mavlink_handler import MAVLinkHandler
from comm_topology import CommTopology

# ============== 页面配置 ==============
st.set_page_config(
    page_title="无人机飞行监控与航线规划系统",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== 样式定制 ==============
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    .status-online {
        color: #00cc00;
        font-weight: bold;
    }
    .status-offline {
        color: #cc0000;
        font-weight: bold;
    }
    .status-warning {
        color: #ff9900;
        font-weight: bold;
    }
    .log-info { color: #0066cc; }
    .log-warning { color: #ff9900; }
    .log-error { color: #cc0000; }
    .log-success { color: #00cc00; }
</style>
""", unsafe_allow_html=True)

# ============== 初始化Session State ==============
if 'obstacle_manager' not in st.session_state:
    st.session_state.obstacle_manager = ObstacleManager(data_dir=".")

if 'path_planner' not in st.session_state:
    st.session_state.path_planner = PathPlanner(st.session_state.obstacle_manager)

if 'flight_monitor' not in st.session_state:
    st.session_state.flight_monitor = FlightMonitor()

if 'mavlink_handler' not in st.session_state:
    st.session_state.mavlink_handler = MAVLinkHandler(use_simulation=True)
    st.session_state.mavlink_handler.connect()

if 'comm_topology' not in st.session_state:
    st.session_state.comm_topology = CommTopology()

if 'current_page' not in st.session_state:
    st.session_state.current_page = "地图与航线规划"

if 'point_a' not in st.session_state:
    st.session_state.point_a = [118.749413, 32.234097]  # 默认A点

if 'point_b' not in st.session_state:
    st.session_state.point_b = [118.751413, 32.236097]  # 默认B点

if 'flight_height' not in st.session_state:
    st.session_state.flight_height = 50.0

if 'safety_radius' not in st.session_state:
    st.session_state.safety_radius = 15.0

if 'map_center' not in st.session_state:
    st.session_state.map_center = [32.234097, 118.749413]

if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 16

if 'selected_obstacles' not in st.session_state:
    st.session_state.selected_obstacles = []

if 'drawing_mode' not in st.session_state:
    st.session_state.drawing_mode = False

# ============== 地图中心坐标 ==============
MAP_CENTER_LNG = 118.749413
MAP_CENTER_LAT = 32.234097
NJCP_CENTER = [32.234097, 118.749413]  # GCJ-02坐标
NJCP_BOUNDS = {
    "north": 32.2370,
    "south": 32.2310,
    "east": 118.7530,
    "west": 118.7450
}

# ============== 侧边栏导航 ==============
st.sidebar.markdown("## 🚁 系统导航")
page = st.sidebar.radio(
    "选择模块",
    ["地图与航线规划", "3D地图", "障碍物管理", "坐标转换工具", "飞行监控", "通信链路", "MAVLink数据流"]
)
st.session_state.current_page = page

# ============== 全局设置 ==============
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ 全局设置")

with st.sidebar.expander("飞行参数设置", expanded=False):
    flight_height = st.number_input(
        "飞行高度 (米)",
        min_value=10.0,
        max_value=500.0,
        value=st.session_state.flight_height,
        step=5.0,
        key="flight_height_input"
    )
    st.session_state.flight_height = flight_height
    st.session_state.path_planner.set_safety_radius(flight_height * 0.3)
    
    safety_radius = st.number_input(
        "安全半径 (米)",
        min_value=5.0,
        max_value=100.0,
        value=st.session_state.safety_radius,
        step=5.0,
        key="safety_radius_input"
    )
    st.session_state.safety_radius = safety_radius
    st.session_state.path_planner.set_safety_radius(safety_radius)

# ============== 页面1: 地图与航线规划 ==============
if page == "地图与航线规划":
    st.markdown('<div class="main-header">🗺️ 地图定位与航线规划</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">南京科技职业学院无人机飞行监控系统</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### 📍 航点设置")
        
        # A点设置
        st.markdown("**起点 A**")
        a_lng = st.number_input("A点经度", value=st.session_state.point_a[0], format="%.6f", key="a_lng")
        a_lat = st.number_input("A点纬度", value=st.session_state.point_a[1], format="%.6f", key="a_lat")
        st.session_state.point_a = [a_lng, a_lat]
        
        # B点设置
        st.markdown("**终点 B**")
        b_lng = st.number_input("B点经度", value=st.session_state.point_b[0], format="%.6f", key="b_lng")
        b_lat = st.number_input("B点纬度", value=st.session_state.point_b[1], format="%.6f", key="b_lat")
        st.session_state.point_b = [b_lng, b_lat]
        
        st.markdown("---")
        
        # 航线规划
        st.markdown("### ✈️ 航线规划")
        if st.button("🔄 规划航线", use_container_width=True):
            with st.spinner("正在规划航线..."):
                paths = st.session_state.path_planner.plan_all_paths(
                    st.session_state.point_a,
                    st.session_state.point_b,
                    st.session_state.flight_height
                )
                st.session_state.planned_paths = paths
                st.success("航线规划完成！")
        
        # 显示路径结果
        if 'planned_paths' in st.session_state:
            paths = st.session_state.planned_paths
            st.markdown("**路径长度对比**")
            
            path_data = []
            for path_type, dist in paths["distances"].items():
                path_name = {"direct": "直飞", "left": "左绕飞", "right": "右绕飞", "optimal": "最优路径"}.get(path_type, path_type)
                path_data.append({"类型": path_name, "距离(m)": round(dist, 1)})
            
            st.table(path_data)
            
            # 选择显示的路径
            st.markdown("**显示路径**")
            show_direct = st.checkbox("直飞", value=True, key="show_direct")
            show_left = st.checkbox("左绕飞", value=False, key="show_left")
            show_right = st.checkbox("右绕飞", value=False, key="show_right")
            show_optimal = st.checkbox("最优路径", value=True, key="show_optimal")
    
    with col1:
        # 创建地图
        m = folium.Map(
            location=st.session_state.map_center,
            zoom_start=st.session_state.map_zoom,
            tiles="OpenStreetMap"
        )
        
        # 添加卫星图层
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="卫星地图",
            overlay=False,
            control=True
        ).add_to(m)
        
        # 添加标准地图
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="标准地图",
            overlay=False,
            control=True
        ).add_to(m)
        
        # 图层控制
        folium.LayerControl(position='topright').add_to(m)
        
        # 添加全屏控件
        Fullscreen(position='topright').add_to(m)
        
        # 添加迷你地图
        MiniMap(position='bottomright').add_to(m)
        
        # 绘制校园边界
        campus_bounds = [
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["west"]],
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["east"]],
            [NJCP_BOUNDS["north"], NJCP_BOUNDS["east"]],
            [NJCP_BOUNDS["north"], NJCP_BOUNDS["west"]],
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["west"]]
        ]
        folium.Polygon(
            locations=campus_bounds,
            color="blue",
            weight=2,
            fill=True,
            fillColor="blue",
            fillOpacity=0.1,
            popup="南京科技职业学院"
        ).add_to(m)
        
        # 添加标记点A和B
        folium.Marker(
            location=[st.session_state.point_a[1], st.session_state.point_a[0]],
            popup=f"起点 A<br>经度: {st.session_state.point_a[0]:.6f}<br>纬度: {st.session_state.point_a[1]:.6f}",
            icon=folium.Icon(color="green", icon="play", prefix="fa")
        ).add_to(m)
        
        folium.Marker(
            location=[st.session_state.point_b[1], st.session_state.point_b[0]],
            popup=f"终点 B<br>经度: {st.session_state.point_b[0]:.6f}<br>纬度: {st.session_state.point_b[1]:.6f}",
            icon=folium.Icon(color="red", icon="stop", prefix="fa")
        ).add_to(m)
        
        # 显示障碍物
        for obs in st.session_state.obstacle_manager.get_obstacles():
            polygon = obs["polygon"]
            # 转换坐标用于显示 [lat, lng]
            folium_polygon = [[p[1], p[0]] for p in polygon]
            
            folium.Polygon(
                locations=folium_polygon,
                color="red",
                weight=2,
                fill=True,
                fillColor="red",
                fillOpacity=0.3,
                popup=f"{obs['name']}<br>高度: {obs['height']}m<br>安全半径: {obs['safety_radius']}m"
            ).add_to(m)
            
            # 显示中心点标签
            center = st.session_state.obstacle_manager.get_obstacle_center(polygon)
            if center:
                folium.Marker(
                    location=[center[1], center[0]],
                    popup=obs["name"],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 10px; color: red; font-weight: bold;">{obs["name"]}</div>'
                    )
                ).add_to(m)
        
        # 显示规划的航线
        if 'planned_paths' in st.session_state:
            paths = st.session_state.planned_paths
            colors = {"direct": "gray", "left": "orange", "right": "purple", "optimal": "green"}
            names = {"direct": "直飞", "left": "左绕飞", "right": "右绕飞", "optimal": "最优路径"}
            
            checkboxes = {
                "direct": show_direct if 'show_direct' in locals() else True,
                "left": show_left if 'show_left' in locals() else False,
                "right": show_right if 'show_right' in locals() else False,
                "optimal": show_optimal if 'show_optimal' in locals() else True
            }
            
            for path_type, path_points in paths.items():
                if path_type == "distances":
                    continue
                if checkboxes.get(path_type, False):
                    folium_path = [[p[1], p[0]] for p in path_points]
                    folium.PolyLine(
                        locations=folium_path,
                        color=colors.get(path_type, "blue"),
                        weight=3,
                        opacity=0.8,
                        popup=names.get(path_type, path_type)
                    ).add_to(m)
        
        # 渲染地图
        map_data = st_folium(m, width=800, height=600, key="main_map")
        
        # 处理地图点击事件
        if map_data and 'last_clicked' in map_data and map_data['last_clicked']:
            clicked_lat = map_data['last_clicked']['lat']
            clicked_lng = map_data['last_clicked']['lng']
            st.info(f"点击位置: 经度 {clicked_lng:.6f}, 纬度 {clicked_lat:.6f}")

# ============== 页面2: 3D地图 ==============
elif page == "3D地图":
    st.markdown('<div class="main-header">🌐 3D地图视图</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">南京科技职业学院 - 三维地形与航线可视化</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### 📍 坐标点设置")
        
        st.markdown("**起点 A (GCJ-02)**")
        a3d_lng = st.number_input("A点经度", value=st.session_state.point_a[0], format="%.6f", key="a3d_lng")
        a3d_lat = st.number_input("A点纬度", value=st.session_state.point_a[1], format="%.6f", key="a3d_lat")
        a3d_alt = st.number_input("A点高度(m)", value=0.0, step=5.0, key="a3d_alt")
        
        st.markdown("**终点 B (GCJ-02)**")
        b3d_lng = st.number_input("B点经度", value=st.session_state.point_b[0], format="%.6f", key="b3d_lng")
        b3d_lat = st.number_input("B点纬度", value=st.session_state.point_b[1], format="%.6f", key="b3d_lat")
        b3d_alt = st.number_input("B点高度(m)", value=st.session_state.flight_height, step=5.0, key="b3d_alt")
        
        st.markdown("---")
        st.markdown("### 🎨 显示选项")
        show_terrain = st.checkbox("显示地形", value=True)
        show_buildings = st.checkbox("显示建筑物", value=False)
        show_paths_3d = st.checkbox("显示航线", value=True)
    
    with col1:
        import pydeck as pdk
        
        # 准备数据
        points_data = []
        
        # A点
        points_data.append({
            "lng": a3d_lng,
            "lat": a3d_lat,
            "alt": a3d_alt,
            "name": "起点 A",
            "color": [0, 255, 0]
        })
        
        # B点
        points_data.append({
            "lng": b3d_lng,
            "lat": b3d_lat,
            "alt": b3d_alt,
            "name": "终点 B",
            "color": [255, 0, 0]
        })
        
        # 障碍物点
        for obs in st.session_state.obstacle_manager.get_obstacles():
            center = st.session_state.obstacle_manager.get_obstacle_center(obs["polygon"])
            if center:
                points_data.append({
                    "lng": center[0],
                    "lat": center[1],
                    "alt": obs["height"],
                    "name": obs["name"],
                    "color": [255, 100, 100]
                })
        
        # 路径数据
        path_data = []
        if 'planned_paths' in st.session_state and show_paths_3d:
            paths = st.session_state.planned_paths
            colors_3d = {
                "direct": [128, 128, 128],
                "left": [255, 165, 0],
                "right": [128, 0, 128],
                "optimal": [0, 255, 0]
            }
            for path_type, path_points in paths.items():
                if path_type == "distances":
                    continue
                coords = [[p[0], p[1], b3d_alt] for p in path_points]
                path_data.append({
                    "path": coords,
                    "name": path_type,
                    "color": colors_3d.get(path_type, [0, 0, 255])
                })
        
        # 如果没有规划路径，显示AB连线
        if not path_data:
            path_data.append({
                "path": [[a3d_lng, a3d_lat, b3d_alt], [b3d_lng, b3d_lat, b3d_alt]],
                "name": "direct",
                "color": [0, 100, 255]
            })
        
        # 点图层
        point_layer = pdk.Layer(
            "ScatterplotLayer",
            data=points_data,
            get_position=["lng", "lat", "alt"],
            get_color="color",
            get_radius=30,
            pickable=True,
            opacity=0.8
        )
        
        # 路径图层
        path_layer = pdk.Layer(
            "PathLayer",
            data=path_data,
            get_path="path",
            get_color="color",
            get_width=5,
            pickable=True
        )
        
        # 文本标注图层
        text_layer = pdk.Layer(
            "TextLayer",
            data=points_data,
            get_position=["lng", "lat", "alt"],
            get_text="name",
            get_size=16,
            get_color=[0, 0, 0],
            get_angle=0,
            pickable=False
        )
        
        # 初始视图
        view_state = pdk.ViewState(
            longitude=(a3d_lng + b3d_lng) / 2,
            latitude=(a3d_lat + b3d_lat) / 2,
            zoom=16,
            pitch=45,
            bearing=0
        )
        
        # 渲染3D地图
        r = pdk.Deck(
            layers=[point_layer, path_layer, text_layer],
            initial_view_state=view_state,
            tooltip={"text": "{name}\n高度: {alt}m"},
            map_style="mapbox://styles/mapbox/satellite-v9" if show_terrain else "mapbox://styles/mapbox/light-v9"
        )
        
        st.pydeck_chart(r)
        
        st.info("提示：使用鼠标左键旋转视角，右键平移，滚轮缩放")

# ============== 页面3: 障碍物管理 ==============
elif page == "障碍物管理":
    st.markdown('<div class="main-header">🚧 障碍物管理</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### ➕ 添加障碍物")
        
        obs_name = st.text_input("障碍物名称", value="新障碍物")
        obs_height = st.number_input("障碍物高度 (米)", min_value=1.0, max_value=200.0, value=30.0, step=5.0)
        obs_safety = st.number_input("安全半径 (米)", min_value=5.0, max_value=100.0, value=15.0, step=5.0)
        
        st.markdown("**多边形顶点 (经纬度，JSON格式)**")
        st.markdown("""
        示例格式：
        ```json
        [
          [118.7770, 32.0560],
          [118.7775, 32.0560],
          [118.7775, 32.0565],
          [118.7770, 32.0565]
        ]
        ```
        """)
        
        polygon_json = st.text_area(
            "输入多边形顶点",
            value='[\n  [118.7770, 32.0560],\n  [118.7775, 32.0560],\n  [118.7775, 32.0565],\n  [118.7770, 32.0565]\n]',
            height=150
        )
        
        if st.button("✅ 添加障碍物", use_container_width=True):
            try:
                polygon = json.loads(polygon_json)
                if isinstance(polygon, list) and len(polygon) >= 3:
                    obs_id = st.session_state.obstacle_manager.add_obstacle(
                        obs_name, polygon, obs_height, obs_safety
                    )
                    st.success(f"障碍物 '{obs_name}' 添加成功！ID: {obs_id}")
                    st.rerun()
                else:
                    st.error("多边形至少需要3个顶点")
            except json.JSONDecodeError:
                st.error("JSON格式错误，请检查输入")
        
        st.markdown("---")
        
        # 快速添加示例障碍物
        st.markdown("### 📝 快速添加")
        if st.button("添加示例障碍物1（教学楼）", use_container_width=True):
            polygon = [
                [118.7770, 32.0562],
                [118.7774, 32.0562],
                [118.7774, 32.0566],
                [118.7770, 32.0566]
            ]
            st.session_state.obstacle_manager.add_obstacle("教学楼A", polygon, 35.0, 20.0)
            st.success("教学楼A 添加成功！")
            st.rerun()
        
        if st.button("添加示例障碍物2（实验楼）", use_container_width=True):
            polygon = [
                [118.7782, 32.0572],
                [118.7786, 32.0572],
                [118.7786, 32.0576],
                [118.7782, 32.0576]
            ]
            st.session_state.obstacle_manager.add_obstacle("实验楼B", polygon, 25.0, 15.0)
            st.success("实验楼B 添加成功！")
            st.rerun()
        
        if st.button("添加示例障碍物3（图书馆）", use_container_width=True):
            polygon = [
                [118.7790, 32.0555],
                [118.7795, 32.0555],
                [118.7795, 32.0560],
                [118.7790, 32.0560]
            ]
            st.session_state.obstacle_manager.add_obstacle("图书馆", polygon, 40.0, 25.0)
            st.success("图书馆 添加成功！")
            st.rerun()
        
        if st.button("🗑️ 清除所有障碍物", use_container_width=True):
            st.session_state.obstacle_manager.clear_all()
            st.warning("所有障碍物已清除")
            st.rerun()
    
    with col1:
        st.markdown("### 🗺️ 障碍物地图")
        
        m = folium.Map(
            location=NJCP_CENTER,
            zoom_start=16,
            tiles="OpenStreetMap"
        )
        
        # 添加卫星图层
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="卫星地图"
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        # 校园边界
        campus_bounds = [
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["west"]],
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["east"]],
            [NJCP_BOUNDS["north"], NJCP_BOUNDS["east"]],
            [NJCP_BOUNDS["north"], NJCP_BOUNDS["west"]],
            [NJCP_BOUNDS["south"], NJCP_BOUNDS["west"]]
        ]
        folium.Polygon(
            locations=campus_bounds,
            color="blue",
            weight=2,
            fill=True,
            fillColor="blue",
            fillOpacity=0.1,
            popup="南京科技职业学院"
        ).add_to(m)
        
        # 显示障碍物
        obstacles = st.session_state.obstacle_manager.get_obstacles()
        for obs in obstacles:
            polygon = obs["polygon"]
            folium_polygon = [[p[1], p[0]] for p in polygon]
            
            folium.Polygon(
                locations=folium_polygon,
                color="red",
                weight=2,
                fill=True,
                fillColor="red",
                fillOpacity=0.3,
                popup=f"{obs['name']}<br>高度: {obs['height']}m<br>安全半径: {obs['safety_radius']}m"
            ).add_to(m)
            
            center = st.session_state.obstacle_manager.get_obstacle_center(polygon)
            if center:
                folium.Marker(
                    location=[center[1], center[0]],
                    popup=obs["name"],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 12px; color: red; font-weight: bold; background: white; padding: 2px;">{obs["name"]}</div>'
                    )
                ).add_to(m)
        
        st_folium(m, width=700, height=500, key="obstacle_map")
        
        # 障碍物列表
        st.markdown("### 📋 障碍物列表")
        if obstacles:
            obs_data = []
            for obs in obstacles:
                center = st.session_state.obstacle_manager.get_obstacle_center(obs["polygon"])
                obs_data.append({
                    "ID": obs["id"],
                    "名称": obs["name"],
                    "高度(m)": obs["height"],
                    "安全半径(m)": obs["safety_radius"],
                    "顶点数": len(obs["polygon"]),
                    "中心经度": round(center[0], 6) if center else "N/A",
                    "中心纬度": round(center[1], 6) if center else "N/A"
                })
            st.table(obs_data)
            
            # 删除障碍物
            st.markdown("**删除障碍物**")
            del_id = st.number_input("输入要删除的障碍物ID", min_value=0, max_value=len(obstacles)-1, value=0)
            if st.button("🗑️ 删除"):
                st.session_state.obstacle_manager.remove_obstacle(del_id)
                st.success(f"障碍物 ID {del_id} 已删除")
                st.rerun()
        else:
            st.info("暂无障碍物，请在右侧添加")

# ============== 页面4: 坐标转换工具 ==============
elif page == "坐标转换工具":
    st.markdown('<div class="main-header">🔄 坐标转换工具</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">WGS-84 / GCJ-02 / BD-09 坐标系互相转换</div>', unsafe_allow_html=True)
    
    st.markdown("### 📐 单点坐标转换")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**输入坐标**")
        input_lng = st.number_input("经度", value=118.749413, format="%.6f", key="ct_lng")
        input_lat = st.number_input("纬度", value=32.234097, format="%.6f", key="ct_lat")
        input_coord = st.selectbox("输入坐标系", ["WGS-84", "GCJ-02", "BD-09"], key="ct_in")
        output_coord = st.selectbox("输出坐标系", ["GCJ-02", "WGS-84", "BD-09"], key="ct_out")
        
        if st.button("🔄 转换", key="ct_btn"):
            result_lng, result_lat = input_lng, input_lat
            
            # 输入 -> WGS-84
            if input_coord == "GCJ-02":
                result_lng, result_lat = gcj02_to_wgs84(input_lng, input_lat)
            elif input_coord == "BD-09":
                from coordinate_transform import bd09_to_wgs84
                result_lng, result_lat = bd09_to_wgs84(input_lng, input_lat)
            
            # WGS-84 -> 输出
            if output_coord == "GCJ-02":
                result_lng, result_lat = wgs84_to_gcj02(result_lng, result_lat)
            elif output_coord == "BD-09":
                from coordinate_transform import wgs84_to_bd09
                result_lng, result_lat = wgs84_to_bd09(result_lng, result_lat)
            
            st.session_state.ct_result = (result_lng, result_lat)
    
    with col2:
        st.markdown("**转换结果**")
        if 'ct_result' in st.session_state:
            rlng, rlat = st.session_state.ct_result
            st.success(f"经度: {rlng:.6f}")
            st.success(f"纬度: {rlat:.6f}")
            
            # 显示在地图上
            m = folium.Map(location=[rlat, rlng], zoom_start=17)
            folium.Marker([rlat, rlng], popup=f"转换结果<br>经度: {rlng:.6f}<br>纬度: {rlat:.6f}").add_to(m)
            st_folium(m, width=400, height=300, key="ct_map")
    
    st.markdown("---")
    st.markdown("### 📋 南京科技职业学院参考坐标")
    
    ref_data = [
        {"位置": "地图中心 (WGS-84)", "经度": 118.749413, "纬度": 32.234097},
        {"位置": "地图中心 (GCJ-02)", "经度": round(wgs84_to_gcj02(118.749413, 32.234097)[0], 6), "纬度": round(wgs84_to_gcj02(118.749413, 32.234097)[1], 6)},
        {"位置": "偏移北点 (WGS-84)", "经度": 118.749413, "纬度": 32.2370},
        {"位置": "偏移南点 (WGS-84)", "经度": 118.749413, "纬度": 32.2310},
    ]
    st.table(ref_data)
    
    st.markdown("---")
    st.markdown("### 📏 距离计算")
    
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.markdown("**点1**")
        d1_lng = st.number_input("经度", value=118.749413, format="%.6f", key="d1_lng")
        d1_lat = st.number_input("纬度", value=32.234097, format="%.6f", key="d1_lat")
    with dcol2:
        st.markdown("**点2**")
        d2_lng = st.number_input("经度", value=118.7795, format="%.6f", key="d2_lng")
        d2_lat = st.number_input("纬度", value=32.0580, format="%.6f", key="d2_lat")
    
    if st.button("📏 计算距离"):
        dist = haversine_distance(d1_lng, d1_lat, d2_lng, d2_lat)
        st.success(f"两点间距离: {dist:.2f} 米 ({dist/1000:.3f} 公里)")

# ============== 页面5: 飞行监控 ==============
elif page == "飞行监控":
    st.markdown('<div class="main-header">📊 飞行监控</div>', unsafe_allow_html=True)
    
    # 更新MAVLink数据（多次调用以生成实时数据）
    for _ in range(3):
        st.session_state.mavlink_handler.update()
    latest = st.session_state.mavlink_handler.get_latest_data()
    
    # 更新飞行监控状态
    if latest["gps"]:
        gps = latest["gps"]
        st.session_state.flight_monitor.update_vehicle_state(
            latitude=gps["lat"] / 1e7,
            longitude=gps["lon"] / 1e7,
            altitude=gps["alt"] / 1000.0
        )
    
    if latest["attitude"]:
        att = latest["attitude"]
        st.session_state.flight_monitor.update_vehicle_state(
            roll=att["roll"],
            pitch=att["pitch"],
            yaw=att["yaw"]
        )
    
    if latest["battery"]:
        bat = latest["battery"]
        voltages = bat["voltages"]
        avg_voltage = sum(voltages[:6]) / 6000.0
        st.session_state.flight_monitor.update_vehicle_state(
            battery_voltage=avg_voltage,
            battery_remaining=bat["battery_remaining"]
        )
    
    if latest["vfr_hud"]:
        vfr = latest["vfr_hud"]
        st.session_state.flight_monitor.update_vehicle_state(
            airspeed=vfr["airspeed"],
            groundspeed=vfr["groundspeed"],
            heading=vfr["heading"],
            throttle=vfr["throttle"],
            relative_altitude=vfr["alt"],
            climb_rate=vfr["climb"]
        )
    
    state = st.session_state.flight_monitor.get_vehicle_state()
    
    # 状态卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("地速", f"{state['groundspeed']:.1f} m/s", delta=None)
        st.metric("空速", f"{state['airspeed']:.1f} m/s", delta=None)
    
    with col2:
        st.metric("相对高度", f"{state['relative_altitude']:.1f} m", delta=None)
        st.metric("爬升率", f"{state['climb_rate']:.1f} m/s", delta=None)
    
    with col3:
        st.metric("航向", f"{state['heading']:.0f}°", delta=None)
        st.metric("油门", f"{state['throttle']}%", delta=None)
    
    with col4:
        battery = st.session_state.flight_monitor.get_battery_status()
        st.metric("电池电压", f"{battery['voltage']:.1f}V", delta=None)
        st.metric("剩余电量", f"{battery['remaining']}%", 
                 delta="良好" if battery['remaining'] > 50 else "警告" if battery['remaining'] > 20 else "危险")
    
    st.markdown("---")
    
    # 位置和姿态
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📍 位置信息")
        pos_data = {
            "纬度": f"{state['latitude']:.6f}°",
            "经度": f"{state['longitude']:.6f}°",
            "海拔高度": f"{state['altitude']:.1f} m",
            "相对高度": f"{state['relative_altitude']:.1f} m"
        }
        for k, v in pos_data.items():
            st.write(f"**{k}**: {v}")
    
    with col2:
        st.markdown("### 🔄 姿态信息")
        attitude = st.session_state.flight_monitor.get_attitude_str()
        att_data = {
            "横滚 (Roll)": f"{attitude['roll']:.1f}°",
            "俯仰 (Pitch)": f"{attitude['pitch']:.1f}°",
            "偏航 (Yaw)": f"{attitude['yaw']:.1f}°"
        }
        for k, v in att_data.items():
            st.write(f"**{k}**: {v}")
    
    st.markdown("---")
    
    # GPS状态
    st.markdown("### 🛰️ GPS状态")
    gps_status = st.session_state.flight_monitor.get_gps_status()
    gps_col1, gps_col2, gps_col3 = st.columns(3)
    with gps_col1:
        st.metric("可见卫星", state['gps_satellites'])
    with gps_col2:
        st.metric("HDOP", state['gps_hdop'])
    with gps_col3:
        st.write(f"**信号质量**: {gps_status['status']}")
    
    st.markdown("---")
    
    # 飞行器在地图上的位置
    st.markdown("### 🗺️ 实时位置")
    if state['latitude'] != 0 and state['longitude'] != 0:
        m = folium.Map(
            location=[state['latitude'], state['longitude']],
            zoom_start=17,
            tiles="OpenStreetMap"
        )
        
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="卫星地图"
        ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        # 飞行器位置
        folium.Marker(
            location=[state['latitude'], state['longitude']],
            popup=f"无人机<br>高度: {state['relative_altitude']:.1f}m<br>航向: {state['heading']:.0f}°",
            icon=folium.Icon(color="blue", icon="plane", prefix="fa")
        ).add_to(m)
        
        # 航向指示
        heading_rad = math.radians(state['heading'])
        arrow_len = 0.0002
        end_lat = state['latitude'] + arrow_len * math.cos(heading_rad)
        end_lng = state['longitude'] + arrow_len * math.sin(heading_rad)
        
        folium.PolyLine(
            locations=[[state['latitude'], state['longitude']], [end_lat, end_lng]],
            color="red",
            weight=3,
            arrow_head=True
        ).add_to(m)
        
        st_folium(m, width=800, height=400, key="flight_map")
    else:
        st.info("等待GPS定位数据...")
    
    # 刷新按钮
    if st.button("🔄 刷新数据", key="refresh_flight"):
        st.rerun()

# ============== 页面4: 通信链路 ==============
elif page == "通信链路":
    st.markdown('<div class="main-header">📡 通信链路展示</div>', unsafe_allow_html=True)
    
    # 更新数据
    st.session_state.comm_topology.simulate_data_transmission()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🌐 网络拓扑图")
        
        nodes = st.session_state.comm_topology.get_nodes()
        links = st.session_state.comm_topology.get_links()
        
        # 尝试使用Graphviz显示拓扑，云端未安装则回退到文本表格
        try:
            import graphviz
            dot = graphviz.Digraph()
            dot.attr(rankdir='LR')
            dot.attr('node', shape='box', style='rounded,filled')
            
            for node_id, node in nodes.items():
                if node['status'] == 'online':
                    color = '#90EE90'
                elif node['status'] == 'offline':
                    color = '#FFB6C1'
                else:
                    color = '#FFE4B5'
                dot.node(node_id, f"{node['name']}\n{node['ip']}", fillcolor=color)
            
            for link_id, link in links.items():
                if link['status'] == 'active':
                    style = 'solid'
                    color = 'green'
                else:
                    style = 'dashed'
                    color = 'gray'
                label = f"{link['protocol']}\n{link['latency']}ms"
                dot.edge(link['source'], link['target'], label=label, style=style, color=color)
            
            st.graphviz_chart(dot.source)
        except Exception:
            # 云端未安装graphviz系统包，使用文本表格回退
            st.info("拓扑图以表格形式展示（云端环境未安装Graphviz系统包）")
            topo_data = []
            for link_id, link in links.items():
                topo_data.append({
                    "链路": f"{link['source']} → {link['target']}",
                    "协议": link['protocol'],
                    "延迟(ms)": link['latency'],
                    "状态": link['status']
                })
            st.table(topo_data)
    
    with col2:
        st.markdown("### 📊 节点状态")
        
        for node_id, node in nodes.items():
            status_color = "status-online" if node['status'] == 'online' else "status-offline"
            st.markdown(f"""
            <div class="metric-card">
                <b>{node['name']}</b><br>
                IP: {node['ip']}:{node['port']}<br>
                状态: <span class="{status_color}">{node['status']}</span><br>
                最后在线: {datetime.fromtimestamp(node['last_seen']).strftime('%H:%M:%S')}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📈 链路质量")
        
        for link_id, link in links.items():
            latency = link['latency']
            packet_loss = link['packet_loss']
            
            if latency < 10 and packet_loss < 0.5:
                quality = "优秀"
                color = "green"
            elif latency < 20 and packet_loss < 1.0:
                quality = "良好"
                color = "orange"
            else:
                quality = "一般"
                color = "red"
            
            st.markdown(f"""
            <div class="metric-card">
                <b>{link['source']} ↔ {link['target']}</b><br>
                协议: {link['protocol']}<br>
                延迟: {latency}ms | 丢包: {packet_loss:.1f}%<br>
                质量: <span style="color: {color}">{quality}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📦 数据流统计")
        
        flow_summary = st.session_state.comm_topology.get_data_flow_summary()
        for flow in flow_summary:
            st.write(f"**{flow['source']} → {flow['target']}**")
            st.write(f"发送: {flow['tx_mb']} MB ({flow['tx_packets']} 包)")
            st.write(f"接收: {flow['rx_mb']} MB ({flow['rx_packets']} 包)")
            st.write("---")
    
    # 刷新按钮
    if st.button("🔄 刷新数据", key="refresh_comm"):
        st.rerun()

# ============== 页面5: MAVLink数据流 ==============
elif page == "MAVLink数据流":
    st.markdown('<div class="main-header">📻 MAVLink数据流</div>', unsafe_allow_html=True)
    
    # 更新数据（多次调用以积累历史记录）
    for _ in range(5):
        st.session_state.mavlink_handler.update()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📨 实时报文")
        
        history = st.session_state.mavlink_handler.get_message_history(30)
        
        for msg in reversed(history):
            timestamp = msg["timestamp"]
            msg_type = msg["type"]
            formatted = st.session_state.mavlink_handler.format_message(msg["data"])
            
            if msg_type == "HEARTBEAT":
                icon = "💓"
                color_class = "log-success"
            elif msg_type == "GPS_RAW_INT":
                icon = "🛰️"
                color_class = "log-info"
            elif msg_type == "ATTITUDE":
                icon = "🔄"
                color_class = "log-info"
            elif msg_type == "BATTERY_STATUS":
                icon = "🔋"
                color_class = "log-warning"
            else:
                icon = "📄"
                color_class = "log-info"
            
            st.markdown(f"""
            <div style="font-family: monospace; font-size: 12px; margin: 2px 0;">
                <span style="color: #888;">[{timestamp}]</span> 
                {icon} <span class="{color_class}">{formatted}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 消息统计")
        
        stats = st.session_state.mavlink_handler.get_message_stats()
        
        if stats:
            stats_data = []
            for msg_type, count in stats.items():
                stats_data.append({"消息类型": msg_type, "数量": count})
            
            import pandas as pd
            df = pd.DataFrame(stats_data)
            st.bar_chart(df.set_index("消息类型"))
        
        st.markdown("---")
        st.markdown("### 📋 当前状态")
        
        latest = st.session_state.mavlink_handler.get_latest_data()
        
        if latest["heartbeat"]:
            hb = latest["heartbeat"]
            st.write(f"**心跳包序列号**: {hb['sequence']}")
            st.write(f"**系统ID**: {hb['system_id']}")
            st.write(f"**组件ID**: {hb['component_id']}")
        
        pos = st.session_state.mavlink_handler.get_vehicle_position()
        if pos:
            st.write(f"**纬度**: {pos['lat']:.6f}°")
            st.write(f"**经度**: {pos['lon']:.6f}°")
            st.write(f"**高度**: {pos['alt']:.1f} m")
        
        att = st.session_state.mavlink_handler.get_vehicle_attitude()
        if att:
            st.write(f"**横滚**: {math.degrees(att['roll']):.1f}°")
            st.write(f"**俯仰**: {math.degrees(att['pitch']):.1f}°")
            st.write(f"**偏航**: {math.degrees(att['yaw']):.1f}°")
        
        batt = st.session_state.mavlink_handler.get_battery_info()
        if batt:
            st.write(f"**电池电压**: {batt['voltage']:.1f}V")
            st.write(f"**剩余电量**: {batt['remaining']}%")
        
        st.markdown("---")
        st.markdown("### 🔌 连接状态")
        
        if st.session_state.mavlink_handler.is_connected():
            st.markdown('<span class="status-online">● 已连接</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-offline">● 未连接</span>', unsafe_allow_html=True)
        
        st.write(f"**消息总数**: {st.session_state.mavlink_handler.message_count}")
    
    # 刷新按钮
    if st.button("🔄 刷新数据", key="refresh_mavlink"):
        st.rerun()

# ============== 页脚 ==============
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ 关于")
st.sidebar.info("""
**无人机飞行监控与航线规划系统**

- 坐标系: WGS-84 / GCJ-02
- 地图: OpenStreetMap / 卫星地图
- 通信: MAVLink协议
- 学校: 南京科技职业学院

版本: v1.0
""")
