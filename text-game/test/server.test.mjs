import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { JevClient } from "../lib/jev.mjs";

// A stand-in for the Jev endpoint, answering like the real one.
function mockJev(handler) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let raw = "";
      req.on("data", (c) => (raw += c));
      req.on("end", () => handler(JSON.parse(raw), req, res));
    });
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

test("the client sends the three questions and parses a typed answer", async () => {
  let seen;
  const server = await mockJev((body, req, res) => {
    seen = { body, auth: req.headers.authorization };
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ model: "jev-1.13.0", usage: { input_tokens: 760 },
      answers: { element: { choice: "frost", confidence: 0.8, probabilities: { frost: 0.8 } }, target: { choice: "nearest", confidence: 0.7 },
                 power: { choice: "strong", confidence: 0.6 } } }));
  });
  const c = new JevClient({ provider: "typesafe", key: "k", baseUrl: `http://127.0.0.1:${server.address().port}/v1/systemone` });
  const a = await c.decide("Make it remember the longest January night");
  c.close(); server.close();
  assert.equal(seen.auth, "Bearer k");
  assert.equal(seen.body.model, "jev-1.13.0");
  assert.deepEqual(Object.keys(seen.body.questions), ["element", "target", "power"]);
  assert.match(seen.body.state, /January night/);
  assert.equal(a.ok, true);
  assert.equal(a.valid, true);
  assert.deepEqual(a.decision, { element: "frost", target: "nearest", power: "strong" });
  assert.ok(Math.abs(a.cost - 760 * 0.042 / 1e6) < 1e-12);
});

test("an answer outside the schema is a failure, marked invalid", async () => {
  const server = await mockJev((body, req, res) => res.end(JSON.stringify({ answers: { element: { choice: "plasma" }, target: { choice: "all" }, power: { choice: "weak" } } })));
  const c = new JevClient({ provider: "typesafe", key: "k", baseUrl: `http://127.0.0.1:${server.address().port}/x` });
  const a = await c.decide("plasma beam");
  c.close(); server.close();
  assert.equal(a.ok, false);
  assert.equal(a.valid, false);
  assert.match(a.error, /invalid answer/);
});

test("the API route answers through the client, without a key it says so", async () => {
  const { default: handler } = await import("../api/decide.js");
  const call = (method, body) => new Promise((resolve) => {
    const res = { headers: {}, setHeader(k, v) { this.headers[k] = v; }, end(s) { resolve({ status: this.statusCode, body: JSON.parse(s) }); } };
    handler({ method, headers: {}, body }, res);
  });
  delete process.env.TYPESAFE_API_KEY; delete process.env.OPENROUTER_API_KEY;
  const r = await call("POST", { spell: "fire" });
  assert.equal(r.status, 503);
  assert.match(r.body.error, /No API key/);
  assert.equal((await call("POST", { spell: "  " })).status, 400);
});
