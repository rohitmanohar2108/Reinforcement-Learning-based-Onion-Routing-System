# run_all_nodes.py
"""
Launcher to run all nodes (12 nodes) + destination.

Usage:
    python run_all_nodes.py thread   # runs nodes in threads (single process)
    python run_all_nodes.py proc     # runs nodes as separate processes (recommended)

Make sure node.py and destination.py are present in the same folder.
"""
import sys
import time
import json
import threading
import subprocess
import os
from pathlib import Path

# Node names (must match keys.json)
L1 = [f"L1_Node{c}" for c in ["A","B","C","D"]]
L2 = [f"L2_Node{c}" for c in ["A","B","C","D"]]
L3 = [f"L3_Node{c}" for c in ["A","B","C","D"]]
DEST = "Destination"

ALL_NODES = L1 + L2 + L3

def load_addrs():
    with open("keys.json", "r") as f:
        cfg = json.load(f)
    return cfg.get("addrs", {})

def run_thread_mode():
    """
    Import node.start_node and destination logic (destination.py should have a
    function start_destination or we will run destination.py as a subprocess).
    This mode keeps everything inside a single Python process using threads.
    """
    print("[launcher] Starting in THREAD mode...")
    # Import node.start_node lazily so this script can be used from any cwd
    try:
        from node import start_node
    except Exception as e:
        print("[launcher] ERROR: failed to import node.start_node:", e)
        print("Make sure node.py exists in the same directory and defines start_node(node_name).")
        return

    threads = []
    # start nodes
    for name in ALL_NODES:
        t = threading.Thread(target=start_node, args=(name,), daemon=True)
        t.start()
        threads.append(t)
        print(f"[launcher] Started thread for {name}")
        time.sleep(0.05)

    # start destination in a thread by running destination.py in a subprocess,
    # because destination.py in our examples listens in a loop and may not expose a start function.
    # If your destination.py defines start_destination(), you can import & call it instead.
    dest_proc = subprocess.Popen([sys.executable, "destination.py"])
    print("[launcher] Destination started as subprocess (destination.py) with PID", dest_proc.pid)

    print("[launcher] All nodes started (thread mode). Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[launcher] KeyboardInterrupt received, terminating destination subprocess...")
        dest_proc.terminate()
        dest_proc.wait(timeout=5)
        print("[launcher] Exiting.")


def run_proc_mode():
    """
    Starts each node and destination as separate processes using `python node.py <Name>`.
    This provides process isolation and is closer to running each node in its own terminal.
    """
    print("[launcher] Starting in PROCESS mode...")
    procs = []

    # start nodes: "python node.py <NodeName>"
    for name in ALL_NODES:
        p = subprocess.Popen([sys.executable, "node.py", name])
        procs.append((name, p))
        print(f"[launcher] Launched process for {name} (PID {p.pid})")
        time.sleep(0.05)

    # start destination process
    dest_p = subprocess.Popen([sys.executable, "destination.py"])
    print(f"[launcher] Launched destination process (PID {dest_p.pid})")
    procs.append((DEST, dest_p))

    print("[launcher] All processes started. Press Ctrl+C to stop them all.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[launcher] KeyboardInterrupt received, terminating child processes...")
        for name, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        # wait briefly
        time.sleep(1)
        for name, p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[launcher] All child processes terminated. Exiting.")


if __name__ == "__main__":
    mode = "proc"
    if len(sys.argv) >= 2:
        mode = sys.argv[1].lower()

    # sanity check: ensure keys.json exists
    if not Path("keys.json").exists():
        print("ERROR: keys.json not found in current directory. Run generate_keys.py first.")
        sys.exit(1)

    if mode not in ("thread", "proc"):
        print("Usage: python run_all_nodes.py [thread|proc]")
        sys.exit(1)

    if mode == "thread":
        run_thread_mode()
    else:
        run_proc_mode()
