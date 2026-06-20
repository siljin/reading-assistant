# Analysis Rubric

How to do the analytical work before rendering a paper report. Read this before drafting `analysis.json`.

The report serves two readers at once: a **newcomer** with no background and a **practitioner** deciding whether the result matters. The result should be understandable, opinionated, and grounded in evidence.

## The Default Failure Mode

Most paper summaries fail two ways: they restate the abstract without judgment, or they are only legible to people already inside the field. A good briefing has a point of view and gives a newcomer enough scaffolding to follow the argument.

## Simplify For The Newcomer

### ELI5 (`eli5`)

Write one vivid analogy plus two or three jargon-free sentences. A smart high-school student should understand what the paper does and why it matters. Avoid vague terms like "leveraging", "novel framework", and "state-of-the-art".

### Jargon Decoder (`glossary`)

Define four to ten terms a newcomer would trip on. Each definition should explain what the term means in this paper, not the textbook definition.

### Plain-Language Summary (`plain_summary`)

Write around 150 words. Re-explain the paper; do not translate the abstract sentence by sentence. Concrete examples and analogies are welcome.

### Figures And Demos

A figure caption should say what the figure is telling the reader. A demo earns its place only if interaction teaches the mechanism faster than prose. One clear demo beats several decorative ones.

## Analyze For The Practitioner

### Headline

One sentence: what is now believable that was not before? If the contribution is incremental, say so.

### Novelty

Frame novelty as "Before this paper, X. This paper makes Y more believable." Distinguish:

- Conceptually novel: a new idea.
- Methodologically novel: a new technique on a known idea.
- Empirically novel: known idea, stronger evidence.
- Engineering novel: known idea scaled or productized.

### Methods

Focus on choices that could have gone differently and why they matter. Skip routine details unless they change interpretation.

### Results

Capture headline numbers, baselines, metrics, and exact values where they matter. Then ask:

- Is the comparison fair?
- Are baselines strong?
- Are error bars, seeds, or confidence intervals reported?
- Does the result hold across settings or mainly in the headline case?
- Does the metric match what real users would care about?

### Limitations

Include the paper's stated limitations, but the value is in unstated ones: narrow domain, weak baselines, synthetic evaluation, missing ablations, compute barriers, untested failure modes, licensing, or a metric that misses user harm.

### Implementation And Product Reality

Could a real team use this? Cover prerequisites, effort level, data needs, compute needs, cheapest validation experiment, regulatory or safety constraints, and what would have to be true before deployment.

## Build The Adaptive Report Plan

The renderer provides a consistent visual shell. The paper decides the order and emphasis through `report_plan`.

Before writing long sections, fill the insight blocks that power the top of the report:

- `insight_dashboard`: two to six cards and optional primary visuals that orient the reader quickly.
- `evidence_profile`: load-bearing claims with support and risk scores from 0 to 10.
- `so_what`: concrete Research, Product, and Business lenses. Each lens needs a headline plus implications, risks, opportunities, or next actions. This is a primary output, not an afterthought.
- `opportunity_matrix`: when useful, a value/feasibility, risk/readiness, or evidence/impact matrix that turns the paper into decisions.

Set:

- `paper_archetype`: method, benchmark, dataset, theory, survey, systems, clinical, product/deployment, etc.
- `reader_goal`: learn the field, decide usefulness, reproduce the method, evaluate business/product potential, etc.
- `narrative_arc`: ordered section types chosen for this paper.
- `sections`: the actual blocks to render.

Section types:

- `problem_context`
- `core_contribution`
- `method_walkthrough`
- `architecture_or_pipeline`
- `experiment_design`
- `results_interpretation`
- `limitations_and_caveats`
- `real_world_implications`
- `business_or_product_insight`
- `learning_path`
- `quiz`

Choose the explanation shape by archetype:

- **Survey paper**: field map -> taxonomy heatmap -> maturity bars -> major agreements/disagreements -> opportunity matrix -> so-what lenses.
- **Method paper**: problem -> architecture/algorithm flow -> novelty comparison -> results/ablations -> implementation feasibility -> adoption risks.
- **Benchmark paper**: task setup -> dataset/eval protocol -> leaderboard or metric comparisons -> caveats -> usefulness matrix.
- **Dataset paper**: data source -> collection pipeline -> coverage/distribution -> bias/risk map -> use-case matrix.
- **Theory paper**: assumptions -> theorem or claim -> intuition ladder -> applicability limits -> research implications.
- **Systems paper**: architecture -> workload -> performance trade-offs -> operational constraints -> adoption readiness.
- **Clinical/deployment paper**: workflow -> study/evidence quality -> safety and regulatory matrix -> adoption readiness -> business/liability risks.

## Visual Selection

Use visuals when they reduce cognitive load. Do not force a visual just because it exists.

- `cards`: important counts, definitions, or takeaways.
- `flow`: process, pipeline, algorithm, clinical workflow.
- `bar_chart`: comparable quantities or score magnitudes.
- `line_chart`: trend, momentum, or timeline-as-quantity when the x-axis order matters.
- `matrix`: two-axis trade-offs, belief calibration, risk/value map.
- `timeline`: evolution of a field or follow-on work.
- `comparison`: before/after, old/new, baseline/proposed.
- `table`: compact evidence, limitations, or design choices.
- `heatmap`: many items across shared criteria.
- `funnel`: staged adoption, validation, or evidence narrowing.

## Learning Path And Quiz

End most reports with:

- Three suggested papers that help the reader go deeper into the field.
- Five MCQs: paper comprehension, field understanding, business insight, product insight, and general research context.

Questions should test understanding, not memorization. Explanations should teach why the right answer is right.

## Voice

- Active voice.
- Short sentences for facts; longer sentences for trade-offs.
- Calibrated opinions are useful. Pretend-neutrality is not.
- Say less when a detail does not change the reader's decision.
