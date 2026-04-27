# destination.py
import socket, json, base64, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BUFFER = 8192
def b64d(x): return base64.b64decode(x)

# load keys and addresses
with open("keys.json", "r") as f:
    cfg = json.load(f)

dest_name = "Destination"
if dest_name not in cfg["keys"] or dest_name not in cfg["addrs"]:
    raise RuntimeError("Destination key/address missing in keys.json")

dest_key = b64d(cfg["keys"][dest_name])
host, port = cfg["addrs"][dest_name]

def decrypt_aes(key_bytes, enc_b64):
    raw = b64d(enc_b64)
    iv = raw[:16]
    ct = raw[16:]
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))
s.listen(5)
print(f"[Destination] Listening on {host}:{port} ...")

while True:
    conn, addr = s.accept()
    data = conn.recv(BUFFER)
    conn.close()
    if not data:
        continue
    try:
        enc_payload = data.decode()
        plaintext = decrypt_aes(dest_key, enc_payload)
        payload_obj = json.loads(plaintext.decode())

        # innermost payload expected to contain 'message' and 'reply_to'
        message = payload_obj.get("message")
        reply_to = payload_obj.get("reply_to")  # e.g. ["127.0.0.1", 55000]
        print(f"[Destination] Received message: {message}")

        # send ACK back if reply_to present
        if reply_to and isinstance(reply_to, list) and len(reply_to) == 2:
            ack_ip, ack_port = reply_to[0], int(reply_to[1])
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ack_sock:
                    ack_sock.settimeout(2.0)
                    ack_sock.connect((ack_ip, ack_port))
                    ack_sock.send(b"ACK")
                print(f"[Destination] Sent ACK to {reply_to}")
            except Exception as e:
                print(f"[Destination] Failed to send ACK to {reply_to}: {e}")

    except Exception as e:
        print("[Destination] Decrypt/processing error:", e)
