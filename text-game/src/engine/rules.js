// The rule baseline: a keyword parser. It is the fallback whenever Jev's answer
// is late or missing, and the "rules only" architecture.
//
// It is deliberately what a game programmer would write in an afternoon. It reads
// "ice" as frost, but it cannot read "make them remember the longest January night".
// How often it disagrees with Jev is a result in itself: it is Joonas's question,
// "why not just an if-statement?", measured.

const ELEMENT_WORDS = {
  frost: ["ice", "icy", "frost", "frosty", "freeze", "freezing", "frozen", "snow", "snowball", "snowstorm", "snowflake", "snowflakes", "cold", "blizzard", "chill", "hail"],
  fire: ["fire", "fireball", "flame", "flames", "burn", "burning", "blaze", "ember", "embers", "heat", "hot", "inferno", "lava"],
  wind: ["wind", "gust", "gusts", "storm", "breeze", "tornado", "whirlwind", "air", "blow", "hurricane"],
  water: ["water", "wave", "waves", "rain", "flood", "splash", "sea", "river", "bubble", "bubbles", "lake"],
  light: ["light", "sun", "sunlight", "shine", "glow", "bright", "star", "stars", "beam", "radiant", "sunbeam"],
  earth: ["rock", "rocks", "stone", "stones", "earth", "boulder", "quake", "earthquake", "mud", "ground", "pebble", "pebbles"],
  nature: ["vine", "vines", "root", "roots", "flower", "flowers", "tree", "trees", "leaf", "leaves", "thorn", "thorns", "moss", "bloom"],
};
const TARGET_WORDS = {
  shield: ["shield", "protect", "guard", "wall", "barrier", "shelter", "defend"],
  all: ["all", "every", "everyone", "everything", "whole", "entire"],
  strongest: ["biggest", "strongest", "largest", "boss", "toughest"],
};
const INTENSIFIERS = ["mighty", "huge", "giant", "enormous", "massive", "great", "powerful", "furious", "thousand"];

export function words(text) {
  return text.toLowerCase().match(/[a-z']+/g) || [];
}

export function rulesDecide(text) {
  const ws = words(text);
  const set = new Set(ws);
  let element = "fizzle", best = 0;
  for (const [el, list] of Object.entries(ELEMENT_WORDS)) {
    const n = list.reduce((k, w) => k + set.has(w), 0);
    if (n > best) { best = n; element = el; }
  }
  let target = "nearest";
  for (const [t, list] of Object.entries(TARGET_WORDS)) {
    if (list.some((w) => set.has(w))) { target = t; break; }
  }
  let level = ws.length < 4 ? 0 : ws.length < 10 ? 1 : 2;
  if (INTENSIFIERS.some((w) => set.has(w))) level += 1;
  if (element === "fizzle") level = 0;
  const power = ["weak", "medium", "strong", "mighty"][Math.min(level, 3)];
  return { element, target, power };
}
