# frame-budget

Technical part of a bachelor thesis: can a decision model (Jev, by TypeSafe) make
decisions inside a game's real-time loop, and which architecture makes that
possible within a fixed time budget?

The game is a minimal wave shooter with no graphics and a simulated player. The
decision under study is difficulty: how many enemies the next wave has and how
hard they hit.

- **Start here:** [docs/JEV_GUIDE.md](docs/JEV_GUIDE.md), from API key to first measurement.
- **Each step** has its own branch (`step-0`, `step-1`, ...) and an explanation in `docs/steps/`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest           # all tests run offline
```
