# Analysis Rubric

How to do the actual analytical work for a paper. Read this before drafting the report.

The report serves two readers at once: a **newcomer** with no background, and a **practitioner** deciding whether the result matters. The "simplify" sections below carry the first; the analysis sections carry the second. Neither should crowd out the other.

## The default failure mode

Most paper summaries fail two ways: they're *too neutral* (restate the abstract, list contributions, stop) and they're *only legible to people who already understand the field*. A good briefing has a point of view AND lets a newcomer in.

## Simplify sections (for the newcomer)

### ELI5 (`eli5`)
One vivid **analogy** plus 2–3 jargon-free sentences. Test: a smart 12th-grader finishes it knowing what the paper does and why anyone cares. Banned words: "leveraging", "novel framework", "state-of-the-art", "paradigm". If you used a term-of-art, you failed — move it to the glossary.

### Jargon decoder (`glossary`)
4–10 terms a newcomer trips on. Each gets a one-line plain definition (not the textbook one — the "what it actually means here" one). Example: `RLHF` → "Teaching a model by giving it human thumbs-up / thumbs-down on its answers."

### Figures (`figures`)
For a key figure, write a caption that says what the picture is *telling you*, not what it depicts. "The line keeps climbing past the dashed baseline — bigger models keep getting better with no plateau yet" beats "Accuracy vs. parameters on ImageNet."

### Demos (`demos`)
A demo earns its place only if interacting with it teaches the mechanism faster than prose. Good candidates: a slider over a hyperparameter, a before/after toggle, a small animated process. Author it as standalone HTML+JS (inline `<script>`); it runs in a sandboxed iframe. One good demo beats three weak ones. Skip entirely if nothing clarifies.

## Analysis sections (for the practitioner)

### TL;DR / headline (1 sentence)
The single sharpest thing. Not "this paper proposes a new method for X" — what is now true (or believable) that wasn't before? If the answer is "not much, it's incremental", say that.

### Plain-language summary (~150 words)
Re-explain, don't translate. A non-specialist should understand what's going on and why anyone cares. Concrete example or analogy welcome.

### What's novel (and what isn't)
Frame as "Before this paper, X. This paper claims Y." Distinguish:
- Conceptually novel (new idea)
- Methodologically novel (new technique on a known idea)
- Empirically novel (known idea, new evidence)
- Engineering novel (known idea, scaled or productized)

If 80% is borrowed and the contribution is one loss term, say so — that's calibration, not criticism.

### Methods — what they actually did
Skip standard practice. Focus on choices that *could have gone differently* and why they went that way. A reader should be able to imagine implementing it.

### Results — and what they support
Headline numbers, on what benchmarks, vs. what baselines. Then the skeptical pass:
- Is the comparison fair? (Same compute? Same data?)
- Single seed or averaged? Error bars?
- Does the improvement hold across conditions or just the headline one?
- Are baselines strong, or chosen to flatter the new method?

### Limitations
The paper's own limitations are table stakes — include but don't dwell. The value is the *unstated* ones: single dataset/domain; metrics that may not match what users care about; compute that makes replication unrealistic; strong data-quality assumptions; no ablation on the component claimed to do the work.

### Implementation notes
Could the user actually use this? Cover: what you'd need to build/deploy (libraries, models, data, compute); rough effort (afternoon / week / quarter / research project); the cheapest viable experiment to validate it on their own data; gotchas (license, data access, model availability).

### Knowledge graph
8–15 nodes, 10–25 edges. Nodes are *concepts*, not sentences: techniques, datasets/benchmarks, prior works, claims, domains. Edges are short directed verb-phrases: `builds_on`, `outperforms`, `evaluated_on`, `assumes`, `contradicts`, `enables`, `requires`. Node `type` ∈ {`technique`, `dataset`, `prior_work`, `claim`, `domain`, `concept`} (the renderer color-codes by type). Avoid full-sentence nodes, isolated nodes, and the paper's own title as a node (it's the subject, use the `this_paper` id for edges from it).

### So-what implications
1. **For research** — the natural next paper; what opened or closed.
2. **For practice** — should a team building real systems care? What would they do differently if this holds?
3. **For the user** — if you have context on their work, tie the paper to it. Otherwise write practice more thoroughly and skip personal.

### People to reach out to
**Start from the user's own network, then spread out.** Order: warm first, cold last. Format each:
```
{
  "name": "...",
  "role": "Senior Researcher, DeepMind",
  "why": "First author — knows the experiments that didn't make the paper.",
  "connection_path": "1st-degree: your connection"
                     | "2nd-degree: via <your connection>"
                     | "cold: <why reachable>",
  "linkedin": "https://linkedin.com/in/..." OR null,
  "search_hint": "Search LinkedIn for '<name> <affiliation>'"   (only when linkedin is null)
}
```
Use `find_people.py` against `data/connections.csv` to seed the 1st-degree set. Spread to 2nd-degree via web search on the best in-network matches. Add authors / critics / practitioners as cold options. Don't fabricate URLs — leave `linkedin` null and give a `search_hint`.

## Voice

- Active voice. Present tense for what the paper claims, past tense for what they did.
- Short sentences for facts; longer for trade-offs.
- It's OK to say "this is impressive" or "this is weak" when justified. Calibrated opinions are useful; pretend-neutrality is not.
