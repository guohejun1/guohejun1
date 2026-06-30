"""
通信链路展示模块 - GCS-OBC-FCU拓扑图绘制
"""
import json
import time
import math

class CommTopology:
    """通信拓扑管理器"""
    def __init__(self):
        self.nodes = {
            "GCS": {
                "id": "GCS",
                "name": "地面站 (GCS)",
                "type": "ground_station",
                "status": "online",
                "ip": "192.168.1.100",
                "port": 14550,
                "last_seen": time.time()
            },
            "OBC": {
                "id": "OBC",
                "name": "机载计算机 (OBC)",
                "type": "onboard_computer",
                "status": "online",
                "ip": "192.168.1.101",
                "port": 14540,
                "last_seen": time.time()
            },
            "FCU": {
                "id": "FCU",
                "name": "飞控单元 (FCU)",
                "type": "flight_controller",
                "status": "online",
                "ip": "192.168.1.102",
                "port": 14560,
                "last_seen": time.time()
            }
        }
        
        self.links = {
            "GCS_OBC": {
                "source": "GCS",
                "target": "OBC",
                "protocol": "UDP",
                "bandwidth": "10 Mbps",
                "latency": 15,
                "packet_loss": 0.5,
                "status": "active"
            },
            "OBC_FCU": {
                "source": "OBC",
                "target": "FCU",
                "protocol": "MAVLink",
                "bandwidth": "1 Mbps",
                "latency": 5,
                "packet_loss": 0.1,
                "status": "active"
            },
            "GCS_FCU": {
                "source": "GCS",
                "target": "FCU",
                "protocol": "MAVLink",
                "bandwidth": "500 Kbps",
                "latency": 25,
                "packet_loss": 1.2,
                "status": "standby"
            }
        }
        
        # 数据流统计
        self.data_flow = {
            "GCS_OBC": {
                "tx_bytes": 1024000,
                "rx_bytes": 2048000,
                "tx_packets": 5000,
                "rx_packets": 10000
            },
            "OBC_FCU": {
                "tx_bytes": 512000,
                "rx_bytes": 1024000,
                "tx_packets": 2500,
                "rx_packets": 5000
            },
            "GCS_FCU": {
                "tx_bytes": 128000,
                "rx_bytes": 256000,
                "tx_packets": 600,
                "rx_packets": 1200
            }
        }
    
    def get_nodes(self):
        """获取所有节点"""
        return self.nodes
    
    def get_links(self):
        """获取所有链路"""
        return self.links
    
    def update_node_status(self, node_id, status):
        """更新节点状态"""
        if node_id in self.nodes:
            self.nodes[node_id]["status"] = status
            self.nodes[node_id]["last_seen"] = time.time()
    
    def update_link_status(self, link_id, status):
        """更新链路状态"""
        if link_id in self.links:
            self.links[link_id]["status"] = status
    
    def get_topology_data(self):
        """获取拓扑图数据（用于可视化）"""
        nodes_list = []
        for node_id, node in self.nodes.items():
            nodes_list.append({
                "id": node_id,
                "name": node["name"],
                "type": node["type"],
                "status": node["status"],
                "ip": node["ip"]
            })
        
        links_list = []
        for link_id, link in self.links.items():
            links_list.append({
                "id": link_id,
                "source": link["source"],
                "target": link["target"],
                "protocol": link["protocol"],
                "latency": link["latency"],
                "packet_loss": link["packet_loss"],
                "status": link["status"]
            })
        
        return {"nodes": nodes_list, "links": links_list}
    
    def get_link_quality_color(self, latency, packet_loss):
        """根据链路质量返回颜色"""
        if latency < 10 and packet_loss < 0.5:
            return "#00FF00"  # 绿色 - 优秀
        elif latency < 20 and packet_loss < 1.0:
            return "#FFFF00"  # 黄色 - 良好
        elif latency < 50 and packet_loss < 2.0:
            return "#FFA500"  # 橙色 - 一般
        else:
            return "#FF0000"  # 红色 - 差
    
    def generate_mermaid_diagram(self):
        """生成Mermaid拓扑图"""
        diagram = "graph LR\n"
        
        # 定义节点样式
        for node_id, node in self.nodes.items():
            if node["status"] == "online":
                style = f"style {node_id} fill:#90EE90"
            elif node["status"] == "offline":
                style = f"style {node_id} fill:#FFB6C1"
            else:
                style = f"style {node_id} fill:#FFE4B5"
            
            diagram += f"    {node_id}[{node['name']}]\n"
            diagram += f"    {style}\n"
        
        # 定义链路
        for link_id, link in self.links.items():
            src = link["source"]
            tgt = link["target"]
            proto = link["protocol"]
            latency = link["latency"]
            
            color = self.get_link_quality_color(latency, link["packet_loss"])
            
            if link["status"] == "active":
                diagram += f"    {src} -->|{proto}<br/>{latency}ms| {tgt}\n"
            else:
                diagram += f"    {src} -.->|{proto}<br/>待机| {tgt}\n"
        
        return diagram
    
    def get_data_flow_summary(self):
        """获取数据流摘要"""
        summary = []
        for link_id, flow in self.data_flow.items():
            link = self.links.get(link_id, {})
            total_tx = flow["tx_bytes"]
            total_rx = flow["rx_bytes"]
            
            summary.append({
                "link": link_id,
                "source": link.get("source", ""),
                "target": link.get("target", ""),
                "tx_mb": round(total_tx / 1048576, 2),
                "rx_mb": round(total_rx / 1048576, 2),
                "tx_packets": flow["tx_packets"],
                "rx_packets": flow["rx_packets"]
            })
        
        return summary
    
    def simulate_data_transmission(self):
        """模拟数据传输，更新统计"""
        import random
        for link_id in self.data_flow:
            # 模拟数据增长
            tx_rate = random.randint(1000, 10000)
            rx_rate = random.randint(1000, 10000)
            
            self.data_flow[link_id]["tx_bytes"] += tx_rate
            self.data_flow[link_id]["rx_bytes"] += rx_rate
            self.data_flow[link_id]["tx_packets"] += random.randint(10, 50)
            self.data_flow[link_id]["rx_packets"] += random.randint(10, 50)
            
            # 模拟延迟和丢包率变化
            self.links[link_id]["latency"] = max(1, self.links[link_id]["latency"] + random.randint(-2, 2))
            self.links[link_id]["packet_loss"] = max(0, self.links[link_id]["packet_loss"] + random.uniform(-0.1, 0.1))

if __name__ == "__main__":
    topo = CommTopology()
    print(topo.generate_mermaid_diagram())
    print(json.dumps(topo.get_topology_data(), indent=2, ensure_ascii=False))
