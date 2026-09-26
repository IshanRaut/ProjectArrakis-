# Ganesh deck decision trail

A learning record, not a set of reusable slide slots. The redesigned eight-slide deck was made through explicit creative decisions and native PowerPoint composition; the subsequent `engine.py` encodes a possible model-planner/render/critic pipeline but its bundled test is mock-only. Do not claim that the final Ganesh deck was produced by this engine.

## 1. The first PPTAgent proof was "mid"

**Decision:** Stop treating an exported PowerPoint as good just because the model's source HTML looked promising and the file opened.

**Why:** The initial PPTAgent run made visually interesting HTML, then the `html2pptx` last mile had to be repaired manually. The converted PPTX lost numerical values on three of seven slides, clipped/overflowed text on others, and exceeded the requested six-slide count. Some confident financial figures were not grounded in checked sources. The user called the result "mid." Editability alone did not make the artifact trustworthy.

**Lesson:** Validate facts before design, then inspect the exact final *converted* file at full size. Missing figures, overflows and off-spec length are release failures, not minor polish notes. A lossy conversion can erase the most important part of a beautiful slide.

## 2. Literal template substitution also failed

**Decision:** Reject the v3 approach of replacing text inside the Sales Kickoff template while preserving its visual theme and structure.

**Why:** The v3 processor kept native PPTX objects and avoided the HTML conversion losses. But it retained the wrong sales theme, inherited graphics, navigation and content slots. Fit problems remained: stat values overlapped and a headline crossed a divider before manual repair. It improved conversion fidelity while missing the actual topic and taste request.

**Lesson:** Technical correctness is not editorial fitness. When a reference is for taste, copying its slots can make the new subject look like an awkward reskin. Ask what the reference *teaches* about hierarchy and rhythm rather than what objects can be overwritten.

## 3. The voice-note pivot

**Decision:** Rebuild as a topic-led festival/economy story rather than repair more sales slides.

**Why:** The user's critique steered away from rigid deterministic output: a model should decide the creative direction live, while code handles rendering. The proof deck therefore chose a fresh narrative and appearance based on the subject. The later engine design separates live planning from mechanical PPTX rendering and image critique. Do not describe the proof deck as a live model execution: its creative direction came from the working agent, recorded explicitly, and the deployable engine has only a mock call test so far.

**Lesson:** User taste feedback can invalidate a technically working architecture. Preserve the intent in the next design and be honest about which parts were human/agent judgment versus automated runtime decisions.

## 4. Mine the reference; do not wear its costume

**Decision:** Extract Sales Kickoff's 16:9 ratio, strong Inter-style type hierarchy, asymmetric color fields and card rhythm. Discard its sales graphics, corporate labels, literal page structure and navigation.

**Why:** Those design principles support short projector-readable claims, but copied sales furniture would imply the wrong genre for a Ganesh Chaturthi economy story.

**Lesson:** Write a keep/translate/reject design-decode sheet before touching layout. A reference should give a visual grammar, not a script.

## 5. Choose colors from the subject

**Decision:** Use deep plum for grounding/contrast, saffron or marigold for energy and festival associations, and cream for breathing room and legibility, with restrained accents.

**Why:** This palette fits Ganesh/pandal imagery and lets large numbers and photographs lead without copying generic rainbow gradients from a sales template. It also supports alternating dense data and quieter photographic slides.

**Lesson:** Color choice should tie theme, image set and hierarchy together. Check contrast and cultural fit rather than assuming a bright palette is enough.

## 6. Write a story, then slides

**Decision:** Move from scale to local network: festival-wide projected business -> pandals/people and supply chain -> spending categories -> actual mandal budget examples -> uncertainty and sources. Give each slide one distinct takeaway.

**Why:** The economic network is easier to understand when an aggregate number leads into what makes it and who participates. A closing source/uncertainty beat prevents trade projections from being mistaken for audited totals. The redesigned deck stayed within eight slides, per the corrected brief.

**Lesson:** Narrative sequencing is an editorial decision, not a template slide order. Never force additive charts when source categories may overlap; label estimates as estimates.

## 7. Use real representative imagery carefully

**Decision:** Source Ganesh idol and pandal photography with URLs and attribution, select crops that suit each slide, and treat photos as representative atmosphere rather than evidence of 2025 transactions or a named mandal's spending.

**Why:** The first generated deck lacked dependable photo tools, while the literal template retained off-topic graphics. Topic-appropriate stock made the redesigned deck feel situated in the festival without pretending an image proves a statistic. Four sample photos and source URLs appear in this engine's `assets.json`; the redesigned proof also used another Ganesh photo documented in its separate source bundle.

**Lesson:** Asset relevance, rights, crop and evidence status all need a decision. Track provenance; do not create placeholder images or infer a number from a photo.

## 8. Catch defects in the rendered artifact

**Decision:** Render the revised native PPTX to PDF, open *every* slide image, repair defects, rerender, and check the exact final output.

**Why:** In the template-native iterations, adjacent stat values collided and one headline crossed a divider. Both were caught visually, corrected, and checked again. The redesigned proof was reviewed as an eight-page PDF, with native editable text objects in the PPTX; LibreOffice rendering was verified, but PowerPoint rendering on the user's VPS/device was not.

**Lesson:** Neither a valid PPTX nor a model approval is sufficient. Visual QA must catch overlap, clipping, missing numbers, contrast and mismatched imagery after export. A fix only counts after another render of the final file.

## 9. Separate creative and mechanical responsibility

**Decision:** Use a **live model planner** for narrative, layout, wording, palette and imagery choices; a **deterministic native renderer** for geometry and file construction; and a **vision critic** for rendered-page review and revision suggestions.

**Why:** A fixed template/text swap suppresses creative judgment, while unguarded model-to-HTML-to-PPTX conversion lost content. The three-stage design puts judgment where it is useful and deterministic code where exact mechanics matter. The bundled `engine.py` implements a draft version of that loop for PPTX/PDF only; `test_engine.py` proves wiring against a localhost fake endpoint, **not** live OpenRouter quality or a production-ready deployment.

**Lesson:** Keep claims about the system at the level actually tested. Future runs need grounded source retrieval, rights checks, schema repair, model quality trials, dollar caps and human final viewing before they become reliable deliverables. See `PLAYBOOK.md` for the reusable process and `MODELS.md` for dated model picks.
