"""
飞行监控模块 - 无人机状态监控与显示
"""
import time
import math
from datetime import datetime

class FlightMonitor:
    def __init__(self):
        self.vehicle_state = {
            "armed": False,
            "mode": "MANUAL",
            "latitude": 0.0,
            "longitude": 0.0,
            "altitude": 0.0,
            "relative_altitude": 0.0,
            "heading": 0.0,
            "groundspeed": 0.0,
            "airspeed": 0.0,
            "climb_rate": 0.0,
            "battery_voltage": 0.0,
            "battery_remaining": 0,
            "gps_satellites": 0,
            "gps_hdop": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "throttle": 0,
            "wp_distance": 0,
            "wp_number": 0,
            "time_boot_ms": 0
        }
        self.connection_status = {
            "gcs_connected": False,
            "obc_connected": False,
            "fcu_connected": False,
            "last_heartbeat": 0,
            "link_quality": 0
        }
        self.mission_log = []
        self.max_log_size = 1000
    
    def update_vehicle_state(self, **kwargs):
        """更新飞行器状态"""
        for key, value in kwargs.items():
            if key in self.vehicle_state:
                self.vehicle_state[key] = value
        self.vehicle_state["time_boot_ms"] = int(time.time() * 1000)
    
    def update_connection_status(self, **kwargs):
        """更新连接状态"""
        for key, value in kwargs.items():
            if key in self.connection_status:
                self.connection_status[key] = value
    
    def get_vehicle_state(self):
        """获取飞行器状态"""
        return self.vehicle_state.copy()
    
    def get_connection_status(self):
        """获取连接状态"""
        return self.connection_status.copy()
    
    def add_mission_log(self, message, level="INFO"):
        """添加任务日志"""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
            "level": level
        }
        self.mission_log.append(log_entry)
        if len(self.mission_log) > self.max_log_size:
            self.mission_log.pop(0)
    
    def get_mission_log(self, count=50):
        """获取最近的任务日志"""
        return self.mission_log[-count:]
    
    def is_healthy(self):
        """检查系统健康状态"""
        return (
            self.connection_status["fcu_connected"] and
            self.vehicle_state["battery_remaining"] > 20 and
            self.vehicle_state["gps_satellites"] >= 6
        )
    
    def get_flight_time_str(self):
        """获取飞行时间字符串"""
        if self.vehicle_state["time_boot_ms"] > 0:
            seconds = self.vehicle_state["time_boot_ms"] // 1000
            minutes = seconds // 60
            hours = minutes // 60
            return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
        return "00:00:00"
    
    def get_battery_status(self):
        """获取电池状态"""
        voltage = self.vehicle_state["battery_voltage"]
        remaining = self.vehicle_state["battery_remaining"]
        
        if remaining > 50:
            status = "良好"
        elif remaining > 20:
            status = "警告"
        else:
            status = "危险"
        
        return {
            "voltage": voltage,
            "remaining": remaining,
            "status": status
        }
    
    def get_gps_status(self):
        """获取GPS状态"""
        satellites = self.vehicle_state["gps_satellites"]
        hdop = self.vehicle_state["gps_hdop"]
        
        if satellites >= 10 and hdop < 1.0:
            status = "极佳"
        elif satellites >= 6 and hdop < 2.0:
            status = "良好"
        elif satellites >= 4:
            status = "一般"
        else:
            status = "差"
        
        return {
            "satellites": satellites,
            "hdop": hdop,
            "status": status
        }
    
    def get_attitude_str(self):
        """获取姿态信息字符串"""
        roll = self.vehicle_state["roll"]
        pitch = self.vehicle_state["pitch"]
        yaw = self.vehicle_state["yaw"]
        return {
            "roll": math.degrees(roll),
            "pitch": math.degrees(pitch),
            "yaw": math.degrees(yaw)
        }
