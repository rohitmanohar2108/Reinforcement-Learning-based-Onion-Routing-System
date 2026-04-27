import json, base64, socket, random, time, os, csv
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

# --- AES helpers ---
def b64e(b): return base64.b64encode(b).decode()
def b64d(s): return base64.b64decode(s)
def encrypt_aes(key, data_bytes):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(data_bytes, AES.block_size))
    return b64e(iv + ct)

# --- Simple Q-Learning Route Agent ---
class RouteRLAgent:
    def __init__(self, layers, alpha=0.1, gamma=0.9, epsilon=0.2, qfile="route_qtable.json"):
        self.layers = layers
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.qfile = qfile
        self.q_table = self.load()

    def load(self):
        if os.path.exists(self.qfile):
            with open(self.qfile, "r") as f:
                try:
                    return {tuple(eval(k)): v for k, v in json.load(f).items()}
                except Exception:
                    return {}
        return {}

    def save(self):
        with open(self.qfile, "w") as f:
            json.dump({str(k): v for k, v in self.q_table.items()}, f, indent=2)

    def choose_route(self):
        """Epsilon-greedy route selection."""
        if random.random() < self.epsilon or not self.q_table:
            route = (
                random.choice(self.layers["L1"]),
                random.choice(self.layers["L2"]),
                random.choice(self.layers["L3"])
            )
        else:
            route = max(self.q_table, key=self.q_table.get)
        return route

    def update(self, route, reward):
        old_val = self.q_table.get(route, 0)
        new_val = old_val + self.alpha * (reward - old_val)
        self.q_table[route] = new_val
        self.save()

# --- Logging helper ---
def log_performance(route, success, latency, reward, logfile="logs/performance_log.csv"):
    os.makedirs("logs", exist_ok=True)
    write_header = not os.path.exists(logfile)
    with open(logfile, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["timestamp", "route", "success", "latency", "reward"])
        writer.writerow([
            time.strftime('%Y-%m-%d %H:%M:%S'),
            "→".join(route),
            int(success),
            round(latency, 4),
            round(reward, 3)
        ])

# --- Congestion simulator ---
def simulate_network_conditions():
    """
    Randomly simulate congestion or packet drops.
    Returns (extra_delay, packet_dropped)
    """
    congestion_chance = random.random()
    drop_chance = random.random()

    # 20% chance of moderate congestion (adds delay)
    if congestion_chance < 0.2:
        delay = random.uniform(0.3, 1.2)
    # 10% chance of heavy congestion
    elif congestion_chance < 0.3:
        delay = random.uniform(1.2, 2.5)
    else:
        delay = random.uniform(0.05, 0.2)

    # 10% chance to drop packet completely
    packet_dropped = drop_chance < 0.1

    return delay, packet_dropped

# --- Load keys and addresses ---
with open("keys.json", "r") as f:
    cfg = json.load(f)

layers = {
    "L1": [n for n in cfg["keys"] if n.startswith("L1_")],
    "L2": [n for n in cfg["keys"] if n.startswith("L2_")],
    "L3": [n for n in cfg["keys"] if n.startswith("L3_")]
}

agent = RouteRLAgent(layers)

# --- Multi-message RL experiment ---
EPISODES = 10000
print(f"[Sender] Starting experiment: {EPISODES} episodes\n")

for episode in range(1, EPISODES + 1):
    route = agent.choose_route()
    n1, n2, n3 = route
    print(f"[Episode {episode}] Selected route (RL): {n1} → {n2} → {n3} → Destination")

    # Load AES keys
    k1 = b64d(cfg["keys"][n1])
    k2 = b64d(cfg["keys"][n2])
    k3 = b64d(cfg["keys"][n3])
    k_dest = b64d(cfg["keys"]["Destination"])

    # Build onion encryption
    message = f"Experiment message {episode}".encode()
    enc_for_dest = encrypt_aes(k_dest, message)
    layer3 = {"next_hop": "Destination", "payload": enc_for_dest}
    enc_layer3 = encrypt_aes(k3, json.dumps(layer3).encode())

    layer2 = {"next_hop": n3, "payload": enc_layer3}
    enc_layer2 = encrypt_aes(k2, json.dumps(layer2).encode())

    layer1 = {"next_hop": n2, "payload": enc_layer2}
    enc_layer1 = encrypt_aes(k1, json.dumps(layer1).encode())

    # Simulate congestion and drop
    delay, dropped = simulate_network_conditions()
    time.sleep(delay)  # simulate congestion

    start = time.time()
    success = False

    if dropped:
        print(f"[Sender] ⚠ Packet dropped due to network congestion! (Simulated)")
        reward = -15 - delay
    else:
        host, port = cfg["addrs"][n1]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.send(enc_layer1.encode())
            success = True
            print(f"[Sender] Onion sent successfully! (Delay: {delay:.2f}s)")
            reward = 10 - delay
        except Exception as e:
            print(f"[Sender] ❌ Sending failed: {e}")
            reward = -10 - delay

    latency = time.time() - start
    reward -= latency

    # Update Q-table and log performance
    agent.update(route, reward)
    log_performance(route, success, latency, reward)

    print(f"[Sender] Reward: {reward:.2f} | Latency: {latency:.2f}s | Success: {success}")

print("\n✅ Experiment completed with congestion simulation!")
print("📊 Logs saved in logs/performance_log.csv")
