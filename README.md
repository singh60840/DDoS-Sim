# DDoS Attack Simulation 
This  DDoS (Distributed Denial of Service) attack simulation framework is designed for educational and testing purposes. It provides a comprehensive toolset for simulating various types of DDoS attacks, to study attack patterns and develop effective defense mechanisms.

## Features

- Multiple attack methods: TCP SYN, UDP, HTTP GET/POST, ICMP, DNS Query, Slowloris, NTP Amplification, DNS Amplification
- IP spoofing with a large pool of source IP addresses
- Botnet simulation with configurable number of bots
- Real-time visualization of attack metrics
- Detailed post-simulation analysis and visualization
- Anomaly detection using Isolation Forest algorithm
- Command and Control (CnC) server for distributed attack simulation

## Requirements

- Python 3.7+
- Scapy
- NumPy
- Pandas
- Matplotlib
- scikit-learn
- websockets
- psutil

## Installation

1. Clone this repository: 
```git clone https://github.com/singh60840/DDoS-Sim.git 
cd ddos-simulation-framework
```

2. Install the required packages


## Usage

Run the simulation using the following command:

```python ddos.py <target_ip> [options]```


### Options:

- `--target-port`: Target port (default: 80)
- `--duration`: Duration of the attack in seconds (default: 300)
- `--rate`: Packets per second (default: 5000)
- `--methods`: Attack methods (default: TCP_SYN UDP HTTP_GET HTTP_POST ICMP DNS_QUERY SLOWLORIS NTP_AMPLIFICATION DNS_AMPLIFICATION)
- `--size`: Packet size in bytes (default: 128)
- `--distributed`: Run in distributed mode
- `--nodes`: Number of nodes for distributed attack (default: 1)
- `--num-bots`: Number of bots in the botnet simulation (default: 50)

### Example:

```python ddos.py 192.168.1.100 --target-port 80 --duration 300 --rate 5000 --methods TCP_SYN UDP HTTP_GET --size 128 --num-bots 50```


## Output

The simulation generates the following outputs:

1. Real-time visualization of attack metrics
2. CSV file with detailed attack statistics
3. Post-simulation visualization plots:
   - `detailed_visualization.png`: Various attack metrics over time
   - `ip_visualization.png`: Source IP distribution over time

## Disclaimer

This tool is for educational and research purposes only. Do not use it to attack systems you do not own or have explicit permission to test. The authors are not responsible for any misuse or damage caused by this program.

## Contributing

Contributions to improve the simulation framework are welcome. Please submit pull requests or open issues to suggest enhancements or report bugs.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
