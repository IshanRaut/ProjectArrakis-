MODEL-DIRECTED PRESENTATION ENGINE - VPS PACKAGE

What this proves
- A live OpenRouter model receives the brief, evidence, image manifest, and reference-design guidance. It decides slide count, narrative, theme, image placement, text, palette and geometry, returning a new plan every run. No fixed slide layouts, deck topic or text slots are encoded in the renderer.
- A small Python renderer turns the model's plan into native editable PowerPoint text and shapes, plus image layers. LibreOffice exports PDF and slide images. A vision-capable model sees every rendered page and can either approve or return a fully revised plan. A rejected last iteration exits nonzero and its files remain drafts, not deliverables.
- The engine calls the model at runtime. The included photos and brief are sample inputs, NOT a deck produced by this engine. The local mock test proves HTTP planner -> PPTX -> PDF -> image critic -> approval wiring, NOT real OpenRouter output quality. There is no legitimate API key in this package and no live paid model call was made here.

Model choices: see MODELS.md (live OpenRouter catalog checked 26 Sep 2026); the first picks are inclusionai/ling-3.0-flash for planning and google/gemini-2.5-flash-lite for vision critique. Pass both model flags explicitly: the code defaults to a paid flash model. Per-call price arithmetic and fallbacks are in MODELS.md.
The reusable decision process is in PLAYBOOK.md; the Ganesh decision trail is in DECISION-LOG.md.

Setup on Ubuntu VPS
  sudo apt update && sudo apt install -y python3 python3-venv libreoffice fonts-inter
  git clone git@github.com:IshanRaut/ProjectArrakis-.git
  cd ProjectArrakis-/ppt-engine
  python3 -m venv .venv && . .venv/bin/activate
  pip install -r requirements.txt
  # If ProjectArrakis already supplies OPENROUTER_API_KEY to this process, reuse it.
  # If not, configure the existing key in the service environment/secret manager; do not create another key.
  test -n "${OPENROUTER_API_KEY:-}" || { echo "OPENROUTER_API_KEY missing in this process"; exit 1; }
  python3 engine.py --brief brief.txt --sources sources.txt --assets assets.json --output ./run-ganesh --model inclusionai/ling-3.0-flash --vision-model google/gemini-2.5-flash-lite --max-revisions 2

The engine reads the same OPENROUTER_API_KEY environment variable as your existing ProjectArrakis setup, but only if that variable is actually inherited by the ppt-engine process. An existing key on the VPS is not proof that every shell or service sees it. Never echo it or put it in the repo. Do not paste keys into chat, commit them, write them into the assets file, or put them on the command line. Secure the output directory, since run plans and previews can contain private brief/source content. The sample photos are locally packaged with attribution links in assets.json. For another topic, change the brief, source evidence, and assets manifest. A planner should search/ground new topic facts beforehand; this engine does not itself browse or fact-check sources. Do not reuse Ganesh figures for another topic.

The returned run-ganesh/deck.pptx and deck.pdf are deliverables only if the command exits 0 and run-log.json says approved. Inspect the exact PDF yourself, particularly before external distribution. If the critic's revision does not pass, the command exits 3 and keeps only drafts. To run without a vision model, pass --vision-model '' and expect exit code 2 and unverified output. Never deliver that as visually passed.

Costs: model selection is explicit at invocation. The default is a flash model, but check current OpenRouter availability/price on your account before running. Calls are capped at one planner + at most three critic calls for --max-revisions 2, each max 6500/7000 completion tokens. Multimodal image input and prompts also cost money; there is no dollar ceiling enforcement because OpenRouter pricing varies. Check usage and stop when appropriate. For free-model experiments pass a valid current :free model ID that accepts image inputs for --vision-model; if no vision model is available, it cannot pass the critique gate. The package records provider token usage in run-log.json, not actual billable dollars.

Other output formats: this implementation only supports editable PPTX and PDF export. It refuses Word/Excel requests in the model prompt; add native DOCX/XLSX renderer adapters, format-specific planning schemas and visual verification before promising them. A renderer is deterministic at the mechanics level, as requested, but the agent's decisions are live. The model may return invalid JSON or geometry; in that case it fails clearly, not silently. Production hardening should add a repair prompt on schema errors and source-claim verification.

Run a no-key mock smoke test:
  python3 test_engine.py
This uses a localhost fake model endpoint and tests two model calls, image critic request, file rendering, and approval; it does NOT generate a real deck.
