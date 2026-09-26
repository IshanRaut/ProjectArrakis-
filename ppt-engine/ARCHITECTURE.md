# ProjectArrakis presentation engine (design-intent architecture)

The planner chooses a short narrative and for each slide names one of seven
archetypes: `title_hero`, `big_stat`, `card_grid`, `split_image_text`, `quote`,
`timeline`, or `closing`. It chooses wording, emphasis, palette, image asset,
image side, and source note. It does not emit coordinates or font sizes.

`intent_layout.py` computes exact native element geometry for each archetype,
measures each text segment and chooses a readable size within the region. Text
that cannot fit is rejected; nothing is truncated. The geometry is checked by
`layout.py` and kept within a 13.333 x 7.5in canvas. The renderer in `engine.py`
turns these elements into editable PPTX shapes and text, exports a PDF and slide
previews. The PDF text-span audit checks final rendered text placement. A visual
critic reviews both design and objective defects; human inspection of all final
slides is still required before delivery.

The seven patterns are composition primitives, not slide templates with swapped
content: the model selects which to use, order, copy, colors and imagery. For a
new design treatment, add an archetype with measured geometry and tests. This
keeps visuals from breaking when a planner invents inconsistent coordinates.

`python3 -m unittest discover -p 'test_*.py'` runs the regressions and local
mock integration with no paid model requests. Real OpenRouter calls require a
user-provided process environment key. The paid planner uses a strict semantic
JSON schema; a :free model may produce JSON without server-side schema support.
