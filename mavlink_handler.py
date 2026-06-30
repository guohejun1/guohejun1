"""
MAVLink通信处理模块 - 心跳包接收与数据流解析
"""
import struct
import time
import threading
from datetime import datetime

# 模拟MAVLink数据（当没有实际连接时使用）
class SimulatedMAVLink:
    """模拟MAVLink数据源，用于测试"""
    def __init__(self):
        self.sequence = 0
        self.base_lat = 32.234097
        self.base_lon = 118.749413
        self.base_alt = 50.0
    
    def get_heartbeat(self):
        """生成心跳包数据"""
        self.sequence = (self.sequence + 1) % 256
        return {
            "type": "HEARTBEAT",
            "sequence": self.sequence,
            "timestamp": time.time(),
            "system_id": 1,
            "component_id": 1,
            "base_mode": 81,
            "custom_mode": 0,
            "system_status": 4,
            "mavlink_version": 3
        }
    
    def get_gps_raw(self):
        """生成GPS原始数据"""
        import random
        return {
            "type": "GPS_RAW_INT",
            "lat": int((self.base_lat + random.uniform(-0.001, 0.001)) * 1e7),
            "lon": int((self.base_lon + random.uniform(-0.001, 0.001)) * 1e7),
            "alt": int((self.base_alt + random.uniform(-5, 5)) * 1000),
            "eph": 120,
            "epv": 200,
            "vel": random.randint(0, 15),
            "cog": random.randint(0, 3600),
            "satellites_visible": random.randint(8, 12)
        }
    
    def get_attitude(self):
        """生成姿态数据"""
        import random
        return {
            "type": "ATTITUDE",
            "time_boot_ms": int(time.time() * 1000) % 4294967296,
            "roll": random.uniform(-0.5, 0.5),
            "pitch": random.uniform(-0.5, 0.5),
            "yaw": random.uniform(0, 6.28),
            "rollspeed": random.uniform(-0.1, 0.1),
            "pitchspeed": random.uniform(-0.1, 0.1),
            "yawspeed": random.uniform(-0.1, 0.1)
        }
    
    def get_battery_status(self):
        """生成电池状态数据"""
        import random
        return {
            "type": "BATTERY_STATUS",
            "id": 0,
            "battery_function": 0,
            "type": 3,
            "temperature": 350,
            "voltages": [random.randint(3700, 4200) for _ in range(10)],
            "current_battery": random.randint(-1000, 5000),
            "current_consumed": random.randint(1000, 5000),
            "energy_consumed": random.randint(1000, 5000),
            "battery_remaining": random.randint(40, 95)
        }
    
    def get_vfr_hud(self):
        """生成VFR HUD数据"""
        import random
        return {
            "type": "VFR_HUD",
            "airspeed": random.uniform(5.0, 15.0),
            "groundspeed": random.uniform(5.0, 15.0),
            "heading": random.randint(0, 360),
            "throttle": random.randint(30, 80),
            "alt": self.base_alt + random.uniform(-10, 10),
            "climb": random.uniform(-2.0, 2.0)
        }

class MAVLinkHandler:
    """MAVLink通信处理器"""
    def __init__(self, use_simulation=True):
        self.use_simulation = use_simulation
        self.simulator = SimulatedMAVLink() if use_simulation else None
        self.connected = False
        self.message_count = 0
        self.last_heartbeat_time = 0
        self.heartbeat_interval = 1.0  # 秒
        
        # 最新数据缓存
        self.latest_data = {
            "heartbeat": None,
            "gps": None,
            "attitude": None,
            "battery": None,
            "vfr_hud": None
        }
        
        # 数据流历史
        self.message_history = []
        self.max_history = 100
        
        # 消息统计
        self.message_stats = {}
    
    def connect(self):
        """建立连接"""
        if self.use_simulation:
            self.connected = True
            return True
        # 实际连接逻辑可以在这里添加
        return False
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
    
    def is_connected(self):
        """检查连接状态"""
        if self.use_simulation:
            return True
        return self.connected
    
    def update(self):
        """更新数据（模拟接收）"""
        if not self.use_simulation or not self.connected:
            return
        
        current_time = time.time()
        if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
            self.last_heartbeat_time = current_time
            
            # 模拟接收各类消息
            heartbeat = self.simulator.get_heartbeat()
            self.latest_data["heartbeat"] = heartbeat
            self._add_message(heartbeat)
            
            gps = self.simulator.get_gps_raw()
            self.latest_data["gps"] = gps
            self._add_message(gps)
            
            attitude = self.simulator.get_attitude()
            self.latest_data["attitude"] = attitude
            self._add_message(attitude)
            
            battery = self.simulator.get_battery_status()
            self.latest_data["battery"] = battery
            self._add_message(battery)
            
            vfr = self.simulator.get_vfr_hud()
            self.latest_data["vfr_hud"] = vfr
            self._add_message(vfr)
            
            self.message_count += 5
    
    def _add_message(self, msg):
        """添加消息到历史记录"""
        msg_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "type": msg.get("type", "UNKNOWN"),
            "data": msg
        }
        self.message_history.append(msg_entry)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # 更新统计
        msg_type = msg.get("type", "UNKNOWN")
        self.message_stats[msg_type] = self.message_stats.get(msg_type, 0) + 1
    
    def get_latest_data(self):
        """获取最新数据"""
        return self.latest_data.copy()
    
    def get_message_history(self, count=20):
        """获取消息历史"""
        return self.message_history[-count:]
    
    def get_message_stats(self):
        """获取消息统计"""
        return self.message_stats.copy()
    
    def get_vehicle_position(self):
        """获取飞行器位置"""
        if self.latest_data["gps"]:
            gps = self.latest_data["gps"]
            return {
                "lat": gps["lat"] / 1e7,
                "lon": gps["lon"] / 1e7,
                "alt": gps["alt"] / 1000.0
            }
        return None
    
    def get_vehicle_attitude(self):
        """获取飞行器姿态"""
        if self.latest_data["attitude"]:
            att = self.latest_data["attitude"]
            return {
                "roll": att["roll"],
                "pitch": att["pitch"],
                "yaw": att["yaw"]
            }
        return None
    
    def get_battery_info(self):
        """获取电池信息"""
        if self.latest_data["battery"]:
            bat = self.latest_data["battery"]
            avg_voltage = sum(bat["voltages"][:6]) / 6000.0
            return {
                "voltage": round(avg_voltage, 2),
                "remaining": bat["battery_remaining"],
                "current": bat["current_battery"] / 100.0
            }
        return None
    
    def format_message(self, msg):
        """格式化消息显示"""
        msg_type = msg.get("type", "UNKNOWN")
        
        if msg_type == "HEARTBEAT":
            return f"HEARTBEAT seq={msg.get('sequence', 0)} sys={msg.get('system_id', 0)} comp={msg.get('component_id', 0)}"
        elif msg_type == "GPS_RAW_INT":
            return f"GPS lat={msg.get('lat', 0)/1e7:.6f} lon={msg.get('lon', 0)/1e7:.6f} alt={msg.get('alt', 0)/1000:.1f}m sats={msg.get('satellites_visible', 0)}"
        elif msg_type == "ATTITUDE":
            return f"ATT roll={msg.get('roll', 0):.3f} pitch={msg.get('pitch', 0):.3f} yaw={msg.get('yaw', 0):.3f}"
        elif msg_type == "BATTERY_STATUS":
            return f"BATT remain={msg.get('battery_remaining', 0)}%"
        elif msg_type == "VFR_HUD":
            return f"VFR_HUD spd={msg.get('groundspeed', 0):.1f}m/s hdg={msg.get('heading', 0)} alt={msg.get('alt', 0):.1f}m"
        else:
            return f"{msg_type} {str(msg)[:80]}"
