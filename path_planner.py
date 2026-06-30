"""
航线规划模块 - 绕飞路径规划（左绕飞、右绕飞、最优路径）
"""
import math
import numpy as np
from coordinate_transform import haversine_distance, gcj02_to_wgs84, wgs84_to_gcj02

class PathPlanner:
    def __init__(self, obstacle_manager, safety_radius=10.0):
        self.obstacle_manager = obstacle_manager
        self.safety_radius = safety_radius
    
    def set_safety_radius(self, radius):
        """设置安全半径"""
        self.safety_radius = radius
    
    def line_intersects_polygon(self, start, end, polygon):
        """
        判断线段是否与多边形相交
        """
        def segments_intersect(p1, p2, p3, p4):
            def ccw(A, B, C):
                return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])
            return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)
        
        n = len(polygon)
        for i in range(n):
            if segments_intersect(start, end, polygon[i], polygon[(i+1)%n]):
                return True
        return False
    
    def get_polygon_vertices(self, polygon, safety_margin=0):
        """
        获取多边形顶点（可扩展安全边界）
        返回顶点列表，用于绕飞
        """
        if safety_margin == 0:
            return polygon
        
        # 简化处理：返回原始顶点
        return polygon
    
    def point_to_line_distance(self, point, line_start, line_end):
        """点到线段的距离"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        if x1 == x2 and y1 == y2:
            return math.sqrt((x0-x1)**2 + (y0-y1)**2)
        
        num = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
        den = math.sqrt((y2-y1)**2 + (x2-x1)**2)
        return num / den
    
    def get_tangent_points(self, center, radius, point):
        """
        计算从外部点到圆的两条切线的切点
        center: 圆心 [lng, lat]
        radius: 半径（度）
        point: 外部点 [lng, lat]
        返回: [切点1, 切点2]
        """
        cx, cy = center
        px, py = point
        dx = px - cx
        dy = py - cy
        d = math.sqrt(dx*dx + dy*dy)
        
        if d <= radius:
            return []
        
        # 计算切线角度
        base_angle = math.atan2(dy, dx)
        offset_angle = math.acos(radius / d)
        
        tangent1 = [
            cx + radius * math.cos(base_angle + offset_angle),
            cy + radius * math.sin(base_angle + offset_angle)
        ]
        tangent2 = [
            cx + radius * math.cos(base_angle - offset_angle),
            cy + radius * math.sin(base_angle - offset_angle)
        ]
        
        return [tangent1, tangent2]
    
    def plan_left_path(self, start, end, obstacles):
        """
        左绕飞路径规划（逆时针绕飞）
        start: [lng, lat] 起点
        end: [lng, lat] 终点
        obstacles: 障碍物列表
        返回: 路径点列表
        """
        path = [start]
        current = start
        
        for obs in obstacles:
            # 检查是否与障碍物相交
            if self.line_intersects_polygon(current, end, obs["polygon"]):
                center = self.obstacle_manager.get_obstacle_center(obs["polygon"])
                if center:
                    # 获取绕飞半径（安全半径 + 障碍物影响半径）
                    bounds = self.obstacle_manager.get_polygon_bounds(obs["polygon"])
                    if bounds:
                        width = haversine_distance(bounds["min_lng"], bounds["min_lat"], 
                                                   bounds["max_lng"], bounds["min_lat"])
                        height = haversine_distance(bounds["min_lng"], bounds["min_lat"], 
                                                    bounds["min_lng"], bounds["max_lat"])
                        obs_radius = max(width, height) / 2 + self.safety_radius
                        
                        # 简化为度
                        radius_deg = obs_radius / 111000
                        
                        # 生成左绕飞路径点（逆时针）
                        tangent_points = self.get_tangent_points(center, radius_deg, current)
                        if len(tangent_points) >= 2:
                            # 选择左侧切点
                            # 简化：直接沿多边形顶点绕行
                            for vertex in obs["polygon"]:
                                path.append(vertex)
        
        path.append(end)
        return path
    
    def plan_right_path(self, start, end, obstacles):
        """
        右绕飞路径规划（顺时针绕飞）
        """
        path = [start]
        current = start
        
        for obs in obstacles:
            if self.line_intersects_polygon(current, end, obs["polygon"]):
                center = self.obstacle_manager.get_obstacle_center(obs["polygon"])
                if center:
                    # 反向遍历顶点实现右绕飞
                    for vertex in reversed(obs["polygon"]):
                        path.append(vertex)
        
        path.append(end)
        return path
    
    def plan_optimal_path(self, start, end, obstacles):
        """
        最优路径规划（航程最短）
        生成圆弧路径避开障碍物
        """
        path = [start]
        current = start
        
        for obs in obstacles:
            if self.line_intersects_polygon(current, end, obs["polygon"]):
                center = self.obstacle_manager.get_obstacle_center(obs["polygon"])
                if center:
                    # 获取切点
                    bounds = self.obstacle_manager.get_polygon_bounds(obs["polygon"])
                    if bounds:
                        width = haversine_distance(bounds["min_lng"], bounds["min_lat"], 
                                                   bounds["max_lng"], bounds["min_lat"])
                        height = haversine_distance(bounds["min_lng"], bounds["min_lat"], 
                                                    bounds["min_lng"], bounds["max_lat"])
                        obs_radius = max(width, height) / 2 + self.safety_radius
                        radius_deg = obs_radius / 111000
                        
                        tangent_points = self.get_tangent_points(center, radius_deg, current)
                        if len(tangent_points) >= 2:
                            # 选择距离终点更近的切点
                            d1 = haversine_distance(tangent_points[0][0], tangent_points[0][1], 
                                                   end[0], end[1])
                            d2 = haversine_distance(tangent_points[1][0], tangent_points[1][1], 
                                                   end[0], end[1])
                            
                            chosen = tangent_points[0] if d1 < d2 else tangent_points[1]
                            path.append(chosen)
                            
                            # 生成圆弧路径点
                            arc_points = self.generate_arc_points(center, radius_deg, chosen, end, 8)
                            path.extend(arc_points)
        
        path.append(end)
        return path
    
    def generate_arc_points(self, center, radius, start_point, end_point, num_points=8):
        """
        生成圆弧路径点
        """
        cx, cy = center
        sx, sy = start_point
        ex, ey = end_point
        
        start_angle = math.atan2(sy - cy, sx - cx)
        end_angle = math.atan2(ey - cy, ex - cx)
        
        # 确保逆时针方向
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        
        arc_points = []
        for i in range(1, num_points + 1):
            t = i / (num_points + 1)
            angle = start_angle + t * (end_angle - start_angle)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            arc_points.append([x, y])
        
        return arc_points
    
    def calculate_path_length(self, path):
        """计算路径总长度（米）"""
        if len(path) < 2:
            return 0
        total = 0
        for i in range(len(path) - 1):
            total += haversine_distance(path[i][0], path[i][1], path[i+1][0], path[i+1][1])
        return total
    
    def plan_all_paths(self, start, end, flight_height):
        """
        规划所有路径类型
        返回: {
            "direct": 直线路径,
            "left": 左绕飞路径,
            "right": 右绕飞路径,
            "optimal": 最优路径,
            "distances": 各路径长度
        }
        """
        # 获取需要避开的障碍物
        colliding_obstacles = []
        for obs in self.obstacle_manager.get_obstacles():
            if flight_height <= obs["height"]:
                if self.line_intersects_polygon(start, end, obs["polygon"]):
                    colliding_obstacles.append(obs)
        
        direct_path = [start, end]
        
        if not colliding_obstacles:
            return {
                "direct": direct_path,
                "left": direct_path,
                "right": direct_path,
                "optimal": direct_path,
                "distances": {
                    "direct": self.calculate_path_length(direct_path),
                    "left": self.calculate_path_length(direct_path),
                    "right": self.calculate_path_length(direct_path),
                    "optimal": self.calculate_path_length(direct_path)
                }
            }
        
        left_path = self.plan_left_path(start, end, colliding_obstacles)
        right_path = self.plan_right_path(start, end, colliding_obstacles)
        optimal_path = self.plan_optimal_path(start, end, colliding_obstacles)
        
        return {
            "direct": direct_path,
            "left": left_path,
            "right": right_path,
            "optimal": optimal_path,
            "distances": {
                "direct": self.calculate_path_length(direct_path),
                "left": self.calculate_path_length(left_path),
                "right": self.calculate_path_length(right_path),
                "optimal": self.calculate_path_length(optimal_path)
            }
        }
