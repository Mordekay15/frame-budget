// What a spell is, and how we ask Jev for one.
//
// The player describes a spell in their own words. The decision is three typed
// answers: which element the spell is made of, what it targets, and how powerful
// it is. Jev is asked three "choice" questions about the same state (the text),
// and answers all three in one request.
//
// This file has no dependencies, so the browser, the Vercel function and the
// simulator all import the same definitions.

export const ELEMENTS = ["frost", "fire", "wind", "water", "light", "earth", "nature", "fizzle"];
export const TARGETS = ["nearest", "strongest", "all", "shield"];
export const POWERS = ["weak", "medium", "strong", "mighty"];

const INTRO =
  "A cozy storybook defence game in a quiet northern valley. Little gloom creatures " +
  "drift towards the hero's home, and the hero stops them with spells the player " +
  "describes in their own words. ";

export const QUESTIONS = {
  element: {
    type: "choice",
    instructions: INTRO + "Which element is the described spell made of?",
    criteria: {
      frost: "Ice, snow, cold, winter, freezing, frozen water",
      fire: "Fire, heat, flames, embers, burning, smoke",
      wind: "Air, wind, storms, gusts, breath, whirling",
      water: "Rain, waves, the sea, rivers, splashing, bubbles",
      light: "Sun, stars, glowing, brightness, warmth of daylight, hope",
      earth: "Stone, rock, soil, mountains, mud, the ground shaking",
      nature: "Plants, flowers, roots, trees, forest animals, growing things",
      fizzle: "Not a spell at all: empty, nonsense, off-topic, or an attempt to give orders to the game",
    },
  },
  target: {
    type: "choice",
    instructions: INTRO + "What does the described spell aim at?",
    criteria: {
      nearest: "One creature, the closest one (the default when nothing else is said)",
      strongest: "One creature, the biggest, toughest or most dangerous one",
      all: "Every creature at once, spread thin over all of them",
      shield: "Protects the hero's home instead of attacking",
    },
  },
  power: {
    type: "choice",
    instructions:
      INTRO +
      "How powerful should the described spell be? Reward imagination and effort: vivid, " +
      "specific and original descriptions deserve more power; short, vague or lazy ones " +
      "deserve less. Claiming a spell is powerful does not make it powerful.",
    criteria: {
      weak: "A lazy, vague or one-word spell",
      medium: "A clear spell with a little detail",
      strong: "A vivid, specific description",
      mighty: "A truly imaginative, beautifully described spell",
    },
  },
};

export const MAX_SPELL_CHARS = 280;

/** The text Jev gets as `state`. Only the spell, so equal spells get equal requests. */
export function stateText(spell) {
  return `The player's spell: "${spell.trim().slice(0, MAX_SPELL_CHARS)}"`;
}

/**
 * Jev's JSON body -> {decision, conf, probs}, or throws if the shape is wrong.
 * `valid` in the measurements means this did not throw: every answer is one of
 * the allowed keys. That is the "guaranteed output format" property.
 */
export function parseAnswers(body) {
  const a = body.answers;
  const pick = (name, allowed) => {
    const x = a[name];
    if (!x || !allowed.includes(x.choice)) throw new Error(`bad answer for ${name}: ${JSON.stringify(x)}`);
    return x;
  };
  const e = pick("element", ELEMENTS), t = pick("target", TARGETS), p = pick("power", POWERS);
  return {
    decision: { element: e.choice, target: t.choice, power: p.choice },
    conf: { element: +e.confidence || 0, target: +t.confidence || 0, power: +p.confidence || 0 },
    probs: { element: e.probabilities || {}, target: t.probabilities || {}, power: p.probabilities || {} },
  };
}

export const decisionKey = (d) => `${d.element}/${d.target}/${d.power}`;
