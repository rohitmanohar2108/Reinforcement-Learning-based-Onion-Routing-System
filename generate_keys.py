# generate_keys.py
import json, base64
from Crypto.Random import get_random_bytes

def b64(b): return base64.b64encode(b).decode()

keys = {}
addrs = {}
base_port = 5000

# 4 nodes per layer
for i in range(1, 4 + 1):
    keys[f"L1_Node{i}"] = b64(get_random_bytes(16))
    addrs[f"L1_Node{i}"] = ["127.0.0.1", base_port + i]

for i in range(1, 4 + 1):
    keys[f"L2_Node{i}"] = b64(get_random_bytes(16))
    addrs[f"L2_Node{i}"] = ["127.0.0.1", base_port + 100 + i]

for i in range(1, 4 + 1):
    keys[f"L3_Node{i}"] = b64(get_random_bytes(16))
    addrs[f"L3_Node{i}"] = ["127.0.0.1", base_port + 200 + i]

# Destination
keys["Destination"] = b64(get_random_bytes(16))
addrs["Destination"] = ["127.0.0.1", base_port + 999]

with open("keys.json", "w") as f:
    json.dump({"keys": keys, "addrs": addrs}, f, indent=2)

print("[+] keys.json generated successfully (12 nodes + destination)")
