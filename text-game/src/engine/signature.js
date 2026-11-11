// Cache keys for spells. Two spellings of the same spell should get the same key,
// so the key ignores letter case, punctuation and extra spaces: "Fire, a big ball!"
// and "fire a big  ball" share a decision, while any change of wording does not.

export function signature(text) {
  return text.toLowerCase().replace(/[^a-z0-9' ]+/g, " ").split(/\s+/).filter(Boolean).join(" ");
}
