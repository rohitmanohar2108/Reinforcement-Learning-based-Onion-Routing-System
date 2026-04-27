# Reinforcement Learning–Based Onion Routing System

## Overview

This project simulates an anonymous communication network inspired by the Tor (The Onion Router) architecture. It combines classical onion routing principles with a Reinforcement Learning (RL) agent to enable intelligent, adaptive route selection across a distributed network of relay nodes. The system continuously learns from network feedback — such as packet success rates, latency, and node congestion — to improve routing decisions over time.

---

## What is Onion Routing?

Onion routing is a technique for anonymous communication over a network. A message is encrypted in multiple layers (like the layers of an onion) and passed through a series of relay nodes. Each node decrypts only its own layer to learn the identity of the next hop, without knowing the full path or the original sender. By the time the message reaches the destination, no single node in the chain has complete knowledge of the communication.

This project simulates that process across three layers of relay nodes (L1, L2, L3) before reaching a final destination.

---

## System Architecture

The network consists of the following components:

**Sender** — The origin of all messages. It selects a route through the network using a Q-learning agent, encrypts the message in multiple AES layers (one per node), and transmits the outermost encrypted packet to the first relay node.

**Relay Nodes (L1, L2, L3)** — Each layer contains four nodes (NodeA through NodeD), giving a total of 12 relay nodes. Each node listens on a socket, decrypts its own encryption layer, reads the identity of the next hop, and forwards the inner payload onward. Nodes operate independently and concurrently using threads.

**Destination** — The final recipient. It decrypts the innermost layer and recovers the original plaintext message. It also sends an acknowledgement (ACK) back to the sender if a reply address is included.

---

## Encryption

Each message is encrypted using AES (Advanced Encryption Standard) in CBC (Cipher Block Chaining) mode. The sender wraps the message in four layers of encryption — one for the destination and one for each relay node — in reverse order. This means:

- Layer 3 is encrypted with the destination's key.
- Layer 2 is encrypted with L3's key, and contains Layer 3 as its payload.
- Layer 1 is encrypted with L2's key, and contains Layer 2 as its payload.
- The outermost layer is encrypted with L1's key, and is what the sender transmits.

Each node peels away exactly one layer, learning only the address of the next hop and passing the remaining encrypted blob forward. No node ever sees the original message or the full routing path.

Keys are generated once using a dedicated key generation script and stored in a shared configuration file alongside the network addresses of all nodes.

---

## Reinforcement Learning for Route Selection

The sender uses a **Q-learning** agent to choose the best route through the network.

### State and Action Space

The network has three layers, each with four nodes. A route is a tuple of three node names — one selected from each layer. The agent's action space is the set of all such possible routes.

### Q-Table

The agent maintains a Q-table that maps each route to an estimated value, representing the expected cumulative reward from taking that route. The table is persisted to disk after every episode so that learning carries over across runs.

### Epsilon-Greedy Exploration

The agent balances exploration and exploitation using an epsilon-greedy strategy. With probability epsilon, it picks a random route to explore unknown paths. Otherwise, it selects the route with the highest Q-value to exploit learned knowledge.

### Reward Function

After each transmission attempt, the agent receives a reward based on the outcome:

- A successful delivery earns a positive base reward.
- A dropped or failed packet incurs a negative penalty.
- Additional penalty is applied proportional to the latency experienced.
- Congestion-induced delays reduce the reward further.

### Q-Value Update

The Q-table is updated using the standard Q-learning rule — the old value is nudged toward the observed reward, scaled by a learning rate (alpha) and discounted by a factor (gamma).

---

## Trust Model

Each relay node maintains a local **trust score** for its downstream neighbors. After every forwarding attempt:

- A successful forward increases the trust score for the next hop.
- A failed forward decreases it.

Trust scores are updated using a simple weighted average rule (similar to Q-learning) and are saved to individual JSON files per node. Over time, nodes learn which downstream neighbors are reliable, which can inform future routing decisions and fault analysis.

---

## Congestion and Packet Drop Simulation

To make the simulation realistic and test the system under load, two levels of congestion are modeled.

**Sender-side simulation** introduces random delays and packet drops before transmission. Roughly 20% of episodes experience moderate congestion, 10% experience heavy congestion, and 10% result in the packet being dropped entirely before it is even sent.

**Node-side simulation** models each relay node's behavior with configurable parameters: a base drop probability, a processing delay (sampled from a Gaussian distribution), and a maximum queue capacity. As a node's queue fills up, its effective drop probability increases — simulating network overload. Processing delay also grows slightly with queue depth.

Together, these mechanisms simulate a realistic distributed network under variable load conditions.

---

## Logging and Performance Tracking

Every episode is logged to a CSV file containing the timestamp, the route taken, whether the transmission succeeded, the observed latency, and the computed reward. This data is used to analyze system performance and generate the result visualizations.

---

## Result Visualizations

The project includes a plotting module that generates several graphs from the performance log:

- **Success Rate Over Time** — how often packets are successfully delivered as the agent learns.
- **Latency Distribution** — spread of latency values across all episodes.
- **Latency by Outcome** — comparison of latency for successful vs. failed deliveries.
- **Average Reward Over Time** — trend of reward values showing learning progress.
- **Success Rate Trend** — rolling success rate to observe convergence.
- **Route Frequency** — how often each route is selected.
- **Top 5 Routes** — the most frequently chosen routes after training.
- **Success Rate per Route** — reliability of each specific route.
- **Reward vs. Latency** — scatter plot exploring the trade-off between speed and reliability.
- **Q-Table Heatmap** — visual representation of the learned Q-values across all routes.
- **Trust Score Heatmaps** — per-layer heatmaps showing node-to-node trust values.

---

## Technologies Used

- **Python** — core implementation language
- **PyCryptodome** — AES encryption and decryption
- **Socket Programming** — TCP-based inter-node communication
- **Threading** — concurrent packet handling at each relay node
- **Subprocess** — process-level isolation for node deployment
- **Q-Learning** — reinforcement learning algorithm for route optimization
- **JSON** — configuration, key storage, Q-table, and trust score persistence
- **CSV** — performance logging
- **Matplotlib / Seaborn** — result visualization

---

## Project Structure

Tor-Network-with-RL/
│
├── generate_keys.py        # Generates AES keys and network addresses for all nodes
├── keys.json               # Stores keys and socket addresses for all nodes
│
├── run_all_nodes.py        # Launcher: starts all 12 relay nodes + destination
├── node.py                 # Relay node logic: decrypt, forward, trust update
├── destination.py          # Final destination: decrypt and acknowledge
├── sender.py               # RL agent + onion encryption + congestion simulation
│
├── plot_graphs.py          # Generates all result graphs from the performance log
│
├── logs/
│   └── performance_log.csv # Episode-by-episode transmission log
│
├── Trust scores/
│   └── trust_<node>.json   # Per-node trust scores for downstream hops
│
├── route_qtable.json        # Persisted Q-table for the routing agent
│
└── Results/                 # Output graphs and visualizations


---

## Key Concepts

| Term | Description |
|---|---|
| Onion Routing | Layered encryption where each node only knows the next hop |
| Q-Learning | A model-free RL algorithm that learns action values through trial and error |
| Epsilon-Greedy | Exploration strategy that balances trying new routes vs. using the best known |
| Trust Score | A per-node rating of downstream neighbor reliability, updated after each forward |
| Congestion Simulation | Randomized delays and drops that test routing robustness |
| Q-Table | A lookup table mapping routes to expected rewards, updated each episode |