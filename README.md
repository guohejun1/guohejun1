# 无人机飞行监控与航线规划系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" />
  <img src="https://img.shields.io/badge/Streamlit-1.58+-red.svg" />
  <img src="https://img.shields.io/badge/Folium-0.20+-green.svg" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
</p>

基于 **Streamlit** 开发的无人机地面站可视化系统，集成地图定位、障碍物管理、航线规划、飞行监控、通信链路展示及 MAVLink 数据流解析等功能。

---

## 功能模块

| 模块 | 功能描述 |
|------|---------|
| **地图与航线规划** | 2D 地图显示（OpenStreetMap + 卫星地图），支持起点/终点设置，航线规划（直飞、左绕飞、右绕飞、最优路径） |
| **3D 地图** | 基于 PyDeck 的三维地形可视化，显示障碍物高度与航线立体关系 |
| **障碍物管理** | 多边形圈选障碍物，支持高度/安全半径设置，JSON 文件持久化记忆 |
| **坐标转换工具** | WGS-84 / GCJ-02 / BD-09 坐标系互相转换，参考坐标表与距离计算 |
| **飞行监控** | 实时显示飞行器状态（速度、高度、航向、电量、姿态、GPS） |
| **通信链路** | GCS-OBC-FCU 拓扑图、链路质量监测、数据流统计 |
| **MAVLink 数据流** | 心跳包、GPS、姿态、电池等报文实时显示与统计 |

---

## 项目结构

```
uav_flight_system/
|-- app.py                    # Streamlit 主应用入口
|-- coordinate_transform.py   # 坐标转换模块 (WGS-84/GCJ-02/BD-09)
|-- obstacle_manager.py       # 障碍物管理 (多边形/高度/JSON持久化)
|-- path_planner.py           # 航线规划模块 (左绕飞/右绕飞/最优路径)
|-- flight_monitor.py         # 飞行监控模块
|-- mavlink_handler.py        # MAVLink 通信处理模块
|-- comm_topology.py          # 通信拓扑展示模块
|-- requirements.txt          # Python 依赖
|-- obstacles.json            # 障碍物数据 (自动生成)
|-- .streamlit/
|   |-- config.toml           # Streamlit 主题与服务器配置
|-- README.md                 # 项目说明文档
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/uav-flight-system.git
cd uav-flight-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 本地运行

```bash
streamlit run app.py
```

浏览器将自动打开 `http://localhost:8501`。

---

## 坐标系说明

本项目使用 **GCJ-02（火星坐标系）** 作为地图显示坐标，内部同时支持：

- **WGS-84**：GPS 原始坐标
- **GCJ-02**：国内地图标准坐标（高德、腾讯等）
- **BD-09**：百度地图坐标

转换算法采用国家标准加密/解密公式，确保坐标精度。

---

## 航线规划算法

1. **碰撞检测**：检测起点到终点的直线是否与障碍物多边形相交
2. **左绕飞**：逆时针沿障碍物顶点绕行
3. **右绕飞**：顺时针沿障碍物顶点绕行
4. **最优路径**：基于切线圆弧计算最短绕飞路径
5. **安全半径**：飞行路径始终与障碍物保持设定安全距离

---

## 部署到 Streamlit Cloud

### 步骤 1：上传至 GitHub

```bash
git init
git add .
git commit -m "init: UAV flight monitoring system"
git branch -M main
git remote add origin https://github.com/你的用户名/uav-flight-system.git
git push -u origin main
```

### 步骤 2：在 Streamlit Cloud 部署

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 点击 **New app**
3. 选择你的 GitHub 仓库 `uav-flight-system`
4. 主文件路径填写 `app.py`
5. 点击 **Deploy**

部署完成后，你将获得一个公开访问链接，例如：
`https://uav-flight-system-xxx.streamlit.app`

---

## 配置说明

### 修改地图中心坐标

编辑 `app.py` 中的以下常量：

```python
MAP_CENTER_LNG = 118.749413   # 中心经度
MAP_CENTER_LAT = 32.234097    # 中心纬度
```

### 修改默认飞行参数

在侧边栏的 **全局设置 → 飞行参数设置** 中实时调整，或在代码中修改：

```python
st.session_state.flight_height = 50.0    # 默认飞行高度 (米)
st.session_state.safety_radius = 15.0    # 默认安全半径 (米)
```

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Streamlit | Web 应用框架 |
| Folium | 2D 地图渲染 |
| PyDeck | 3D 地图可视化 |
| Graphviz | 通信拓扑图绘制 |
| NumPy / Pandas | 数据计算与统计 |

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 作者

- **开发**：南京科技职业学院
- **版本**：v1.0
- **日期**：2026-06-30
