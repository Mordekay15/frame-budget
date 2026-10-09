"""Your first Jev call: send one game state, print everything that comes back.

    python -m scripts.jev_hello

If this works, your key and network are fine and every other script will work.
"""

import json
import time

from framebudget.decision import DecisionState, state_to_text
from framebudget.jev import JevClient, load_api_key

state = DecisionState(
    health=35, max_health=100, wave=6, last_count=8, last_mult=1.25,
    last_wave_damage=30, last_clear_time=6.5, dps_recent=4.6, kill_rate=1.2,
)
text = state_to_text(state)
print("State sent to Jev:\n ", text, "\n")

client = JevClient(load_api_key())
t0 = time.perf_counter()
out = client.raw_request(text)
ms = (time.perf_counter() - t0) * 1000
print(f"HTTP {out['http_status']} after {ms:.0f} ms (includes opening the connection)\n")
print(json.dumps(out["body"], indent=2))

res = client.decide(text)
print(f"\nSecond request on the same connection: {res.latency_ms:.0f} ms")
if res.ok:
    print(f"Decision: {res.decision.count} enemies, damage x{res.decision.mult}")
else:
    print("Failed:", res.http_status, res.error)
