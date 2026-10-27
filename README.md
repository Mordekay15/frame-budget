# frame-budget

Technical part of a bachelor thesis: can a decision model (Jev, by TypeSafe) make decisions inside a
game's real-time loop, and which architecture makes that possible within a fixed time budget?

Everything is in **[text-game/](text-game/README.md)**: a web game where the player describes spells in
their own words and Jev reads them (element, target, power), a simulator that plays it with a bot to
compare the architectures, and the code that measures Jev.

The first test bench (a wave game whose decision was difficulty adjustment, in Python) was removed from
this branch on 23 Oct 2026. It is still on the `step-0` to `step-10` branches.
