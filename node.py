# node.py
import socket, json, base64, sys, os, time, random, threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BUFFER = 8192

def b64d(x): return base64.b64decode(x)

def decrypt_aes(key_bytes, enc_b64):
    raw = b64d(enc_b64)
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

def load_config():
    with open("keys.json","r") as f:
        return json.load(f)

# --- RL Trust Table for each node ---
class NodeTrust:
    def __init__(self, node_name):
        self.node_name = node_name
        self.filename = f"trust_{node_name}.json"
        self.scores = self.load()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename,"r") as f:
                try:
                    return json.load(f)
                except Exception:
                    return {}
        return {}

    def save(self):
        with open(self.filename,"w") as f:
            json.dump(self.scores, f, indent=2)

    def update(self, next_hop, success, alpha=0.1):
        reward = 5 if success else -5
        old = self.scores.get(next_hop, 0)
        self.scores[next_hop] = old + alpha * (reward - old)
        self.save()
        print(f"[{self.node_name}] Trust[{next_hop}] = {self.scores[next_hop]:.2f}")

# --- Node behavior for congestion & drops ---
class NodeBehavior:
    """Per-node behavior: base drop probability, processing delay, capacity and a queue counter."""
    def __init__(self, cfg, name):
        beh = cfg.get("behavior", {}).get(name, {})
        # defaults
        self.drop_prob = float(beh.get("drop_prob", 0.02))
        self.delay_mean = float(beh.get("delay_mean", 0.02))    # seconds
        self.delay_std = float(beh.get("delay_std", 0.01))
        self.capacity = int(beh.get("capacity", 10))
        # runtime state
        self.queue_len = 0
        self.lock = threading.Lock()

    def maybe_drop(self):
        """Return True if packet should be dropped (simulated)."""
        base = self.drop_prob
        overload_factor = max(0, (self.queue_len - self.capacity) / max(1, self.capacity))
        prob = min(0.99, base + overload_factor * 0.3)
        return random.random() < prob

    def processing_delay(self):
        """Return a processing delay that grows slightly with queue length."""
        delay = max(0, random.gauss(self.delay_mean, self.delay_std))
        delay += 0.001 * self.queue_len
        return delay

def start_node(node_name):
    cfg = load_config()
    if node_name not in cfg["keys"] or node_name not in cfg["addrs"]:
        print(f"[{node_name}] ERROR: node name not found in keys.json.")
        return

    key_b64 = cfg["keys"][node_name]
    key = b64d(key_b64)
    host, port = cfg["addrs"][node_name]

    trust = NodeTrust(node_name)
    behavior = NodeBehavior(cfg, node_name)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(10)
    print(f"[{node_name}] Listening on {host}:{port} ... (drop_prob={behavior.drop_prob}, delay_mean={behavior.delay_mean}, capacity={behavior.capacity})")

    while True:
        conn, addr = s.accept()
        data = conn.recv(BUFFER)
        conn.close()
        if not data:
            continue

        # increment queue length to simulate in-flight packets
        with behavior.lock:
            behavior.queue_len += 1

        def handle_packet(enc_packet_b64):
            try:
                # initial processing fraction
                delay = behavior.processing_delay()
                time.sleep(delay * 0.5)

                # early drop (simulate loss in queue/buffer)
                if behavior.maybe_drop():
                    print(f"[{node_name}] DROPPED packet early (queue={behavior.queue_len})")
                    # we don't know next_hop here; treat as a local drop (no trust update)
                    return

                # decrypt this node's layer
                plaintext = decrypt_aes(key, enc_packet_b64)
                payload_obj = json.loads(plaintext.decode())
                next_hop = payload_obj.get("next_hop")
                payload = payload_obj.get("payload")  # base64 string intended for next hop

                # remainder of processing
                time.sleep(delay * 0.5)

                print(f"[{node_name}] Decrypted layer. Next hop: {next_hop}")

                if next_hop not in cfg["addrs"]:
                    print(f"[{node_name}] Unknown next hop: {next_hop}")
                    return

                nh_host, nh_port = cfg["addrs"][next_hop]

                # potential drop before forwarding due to overload
                if behavior.maybe_drop():
                    print(f"[{node_name}] DROPPED before forwarding to {next_hop} (overload queue={behavior.queue_len})")
                    # update trust for next_hop as failed
                    trust.update(next_hop, False)
                    return

                # try forwarding to next hop
                start_time = time.time()
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
                        s2.settimeout(2.0)
                        s2.connect((nh_host, nh_port))
                        s2.send(payload.encode())
                    duration = time.time() - start_time
                    print(f"[{node_name}] Forwarded to {next_hop} ({duration:.3f}s)")
                    trust.update(next_hop, True)
                except Exception as e:
                    print(f"[{node_name}] Forwarding failed to {next_hop}: {e}")
                    trust.update(next_hop, False)

            except Exception as e:
                print(f"[{node_name}] Error during decrypt/forward: {e}")
            finally:
                with behavior.lock:
                    behavior.queue_len = max(0, behavior.queue_len - 1)

        t = threading.Thread(target=handle_packet, args=(data.decode(),), daemon=True)
        t.start()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node.py NodeName")
        sys.exit(1)
    start_node(sys.argv[1])
