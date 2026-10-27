// Cache keys for spells. Two spells that deserve the same decision should get the
// same key, so the key throws detail away on purpose. `coarse` sets how much:
//
//   0  exact text (only identical spells share a decision)
//   1  lower case, punctuation and extra spaces removed
//   2  as 1, plus filler words dropped and the remaining words sorted,
//      so "a big ball of fire" and "fire, a big ball!" match
//
// Larger coarseness means more hits, but more different spells share one answer.

const FILLER = new Set(["a", "an", "the", "of", "and", "to", "at", "on", "in", "with", "my", "i", "them", "it", "that", "this", "is", "are", "be", "so", "very", "please", "cast"]);

export function signature(text, coarse = 1) {
  if (coarse <= 0) return text;
  const ws = text.toLowerCase().replace(/[^a-z0-9' ]+/g, " ").split(/\s+/).filter(Boolean);
  if (coarse < 2) return ws.join(" ");
  return ws.filter((w) => !FILLER.has(w)).sort().join(" ");
}
