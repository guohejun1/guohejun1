"""
障碍物管理模块 - 多边形圈选、高度设置、JSON保存与读取
"""
import json
import os
import math
from coordinate_transform import haversine_distance

OBSTACLE_FILE = "obstacles.json"

class ObstacleManager:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.obstacles = []
        self.load_obstacles()
    
    def get_file_path(self):
        return os.path.join(self.data_dir, OBSTACLE_FILE)
    
    def load_obstacles(self):
        """从JSON文件加载障碍物"""
        file_path = self.get_file_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.obstacles = json.load(f)
                print(f"已加载 {len(self.obstacles)} 个障碍物")
            except Exception as e:
                print(f"加载障碍物失败: {e}")
                self.obstacles = []
        else:
            self.obstacles = []
    
    def save_obstacles(self):
        """保存障碍物到JSON文件"""
        file_path = self.get_file_path()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.obstacles, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存障碍物失败: {e}")
            return False
    
    def add_obstacle(self, name, polygon_points, height, safety_radius=10.0):
        """
        添加障碍物
        polygon_points: list of [lng, lat] in GCJ-02
        height: 障碍物高度（米）
        safety_radius: 安全半径（米）
        """
        obstacle = {
            "id": len(self.obstacles),
            "name": name,
            "polygon": polygon_points,
            "height": height,
            "safety_radius": safety_radius
        }
        self.obstacles.append(obstacle)
        self.save_obstacles()
        return obstacle["id"]
    
    def remove_obstacle(self, obstacle_id):
        """删除障碍物"""
        self.obstacles = [o for o in self.obstacles if o["id"] != obstacle_id]
        # 重新编号
        for i, obs in enumerate(self.obstacles):
            obs["id"] = i
        self.save_obstacles()
    
    def clear_all(self):
        """清除所有障碍物"""
        self.obstacles = []
        self.save_obstacles()
    
    def get_obstacles(self):
        """获取所有障碍物"""
        return self.obstacles
    
    def point_in_polygon(self, point, polygon):
        """
        判断点是否在多边形内（射线法）
        point: [lng, lat]
        polygon: list of [lng, lat]
        """
        x, y = point
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside
    
    def get_obstacle_center(self, polygon):
        """计算多边形中心点"""
        if not polygon:
            return None
        lng_sum = sum(p[0] for p in polygon)
        lat_sum = sum(p[1] for p in polygon)
        return [lng_sum / len(polygon), lat_sum / len(polygon)]
    
    def get_polygon_bounds(self, polygon):
        """获取多边形边界框"""
        if not polygon:
            return None
        lats = [p[1] for p in polygon]
        lngs = [p[0] for p in polygon]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lng": min(lngs),
            "max_lng": max(lngs)
        }
    
    def point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        """点到线段距离"""
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        return math.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)
    
    def point_to_polygon_distance(self, point, polygon):
        """计算点到多边形的最短距离"""
        min_dist = float('inf')
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            dist = self.point_to_segment_distance(point[0], point[1], x1, y1, x2, y2)
            min_dist = min(min_dist, dist)
        return min_dist
    
    def check_collision(self, point, flight_height):
        """
        检查点是否与障碍物碰撞
        返回: (是否碰撞, 碰撞的障碍物列表)
        """
        collisions = []
        for obs in self.obstacles:
            # 点在多边形内
            if self.point_in_polygon(point, obs["polygon"]):
                if flight_height <= obs["height"]:
                    collisions.append(obs)
            else:
                # 检查是否在安全半径内
                dist = self.point_to_polygon_distance(point, obs["polygon"])
                # 转换为米
                center = self.get_obstacle_center(obs["polygon"])
                if center:
                    dist_m = haversine_distance(point[0], point[1], center[0], center[1])
                    # 简化的距离检查，实际需要更精确计算
                    if dist_m < obs["safety_radius"]:
                        collisions.append(obs)
        return len(collisions) > 0, collisions

if __name__ == "__main__":
    # 测试
    om = ObstacleManager()
    om.clear_all()
    
    # 添加测试障碍物
    polygon = [
        [118.7770, 32.0560],
        [118.7775, 32.0560],
        [118.7775, 32.0565],
        [118.7770, 32.0565]
    ]
    om.add_obstacle("教学楼A", polygon, 30.0, 15.0)
    print(f"障碍物数量: {len(om.get_obstacles())}")
