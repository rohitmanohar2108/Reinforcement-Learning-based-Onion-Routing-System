import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import ast

# === 1️⃣ TRUST HEATMAPS FROM route_qtable.json ===
with open("route_qtable.json", "r") as f:
    q_raw = json.load(f)

# Convert keys to tuples
q_table = {tuple(ast.literal_eval(k)): v for k, v in q_raw.items()}

# Split routes into L1→L2 and L2→L3 trust mappings
l1_nodes = sorted(list({r[0] for r in q_table}))
l2_nodes = sorted(list({r[1] for r in q_table}))
l3_nodes = sorted(list({r[2] for r in q_table}))

trust_l1_l2 = pd.DataFrame(0.0, index=l1_nodes, columns=l2_nodes)
trust_l2_l3 = pd.DataFrame(0.0, index=l2_nodes, columns=l3_nodes)

# Fill averages based on Q-values
for (l1, l2, l3), val in q_table.items():
    trust_l1_l2.loc[l1, l2] += val
    trust_l2_l3.loc[l2, l3] += val

# Average (normalize by count)
trust_l1_l2 = trust_l1_l2.divide(trust_l1_l2.replace(0, pd.NA).count(axis=1), axis=0).fillna(0)
trust_l2_l3 = trust_l2_l3.divide(trust_l2_l3.replace(0, pd.NA).count(axis=1), axis=0).fillna(0)

# --- Plot Heatmaps ---
plt.figure(figsize=(10, 5))
sns.heatmap(trust_l1_l2, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Trust Heatmap: L1 → L2 (Average Q-values)")
plt.xlabel("L2 Nodes")
plt.ylabel("L1 Nodes")
plt.tight_layout()
plt.savefig("1_trust_heatmap_L1_L2.png")
plt.show()

plt.figure(figsize=(10, 5))
sns.heatmap(trust_l2_l3, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Trust Heatmap: L2 → L3 (Average Q-values)")
plt.xlabel("L3 Nodes")
plt.ylabel("L2 Nodes")
plt.tight_layout()
plt.savefig("2_trust_heatmap_L2_L3.png")
plt.show()

print("✅ Saved trust heatmaps as 1_trust_heatmap_L1_L2.png and 2_trust_heatmap_L2_L3.png")

# === 2️⃣ SUCCESS RATE OVER TIME ===
df = pd.read_csv("logs/performance_log.csv")

if 'success' not in df.columns:
    print("⚠️ 'success' column not found in performance_logs.csv")
else:
    df['episode'] = range(1, len(df) + 1)
    df['rolling_success'] = df['success'].rolling(window=100).mean()

    plt.figure(figsize=(8, 5))
    plt.plot(df['episode'], df['rolling_success'], color='green', linewidth=2)
    plt.xlabel("Episode")
    plt.ylabel("Rolling Success Rate")
    plt.title("Success Rate Trend Over Time")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("3_success_rate_trend.png")
    plt.show()

    print("✅ Saved success rate graph as 3_success_rate_trend.png")

# === 3️⃣ TOP 5 MOST CHOSEN ROUTES ===
if 'route' in df.columns:
    route_counts = df['route'].value_counts().head(5)

    plt.figure(figsize=(9, 5))
    sns.barplot(x=route_counts.values, y=route_counts.index, palette="viridis")
    plt.xlabel("Selection Count")
    plt.ylabel("Route (L1 → L2 → L3)")
    plt.title("Top 5 Most Frequently Selected Routes")
    plt.tight_layout()
    plt.savefig("4_top5_routes.png")
    plt.show()

    print("✅ Saved top 5 route frequency graph as 4_top5_routes.png")
else:
    print("⚠️ 'route' column not found in performance_logs.csv")
