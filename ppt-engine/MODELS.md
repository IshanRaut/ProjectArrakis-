# OpenRouter model choices (checked 26 September 2026)

These are **starting picks**, not measured output-quality guarantees. The current OpenRouter public [model catalog](https://openrouter.ai/api/v1/models) lists the exact IDs, modality, supported parameters and prices below. Confirm account access, price and quality with a small run before committing to a full deck. The engine currently accepts `--model` and `--vision-model`; **it does not implement automatic fallback**, dollar ceilings or cost estimation. Change the flags and rerun if a model fails, and inspect the result.

| Stage | First pick | Why | Catalog list price per million input / output tokens |
| --- | --- | --- | --- |
| Planner | `inclusionai/ling-3.0-flash` | Low-cost text model, 262k context, catalog lists `response_format`; good candidate for geometry-rich JSON. Prior local design probe showed fast, styled HTML, but **this engine's JSON quality is untested live**. | **$0.021 / $0.063** |
| Vision critic | `google/gemini-2.5-flash-lite` | Image input and JSON/structured-output parameters in the catalog, inexpensive enough for all-slide image critique. Test whether it actually catches overlaps, missing figures and weak crops on your deck. | **$0.10 / $0.40**; catalog also lists image input at $0.10/M units/tokens, subject to provider accounting. |
| Zero-cost planner experiment | `nvidia/nemotron-3-super-120b-a12b:free` | Text/JSON-capable catalog entry, zero listed token price. Use only if a real plan is coherent and valid; free pool may be slower/limited. | **$0 / $0**, rate-limited |
| Zero-cost vision experiment | `google/gemma-4-31b-it:free` | Image input, zero listed price. **Not yet validated as a critic**; only use after a visual error-detection trial. | **$0 / $0**, rate-limited |
| Planner paid fallback | `google/gemini-2.5-flash` | Stronger flash candidate if the cheap planner misses structure/brief; test its JSON and style before assuming quality. | **$0.30 / $2.50** |
| Vision paid fallback | `google/gemini-2.5-flash` | Stronger multimodal candidate if Flash-Lite misses defects. | **$0.30 / $2.50** |

Pricing is OpenRouter's displayed per-token catalog price multiplied by one million; it may change. [FAQ](https://openrouter.ai/docs/faq) says the `:free` variant has low rate limits. Current listed free vision alternatives can be restricted or unreliable; free never guarantees availability. Don't silently switch models when the brief calls for an explicit spend cap.

## Spend shape, not a quote

The engine makes one planner call, then one vision-critic call per rendered revision, up to `1 + max_revisions` critic calls. Default `--max-revisions 2` therefore allows **up to four calls total**: one planner and three critics. It may fail earlier or make three HTTP retry attempts per call after errors; provider charging of failed/retried requests must be checked. The default `google/gemini-2.5-flash` in code is a **paid model** for both roles; pass both selected IDs explicitly.

Illustrative token-accounting example using **5,000 planner input + 4,000 output tokens** and **12,000 image/text input + 1,000 output tokens per critic call**:

- Ling planner: 5,000 × $0.021/M + 4,000 × $0.063/M = **$0.000357**.
- Flash-Lite critic: 12,000 × $0.10/M + 1,000 × $0.40/M = **$0.00160 per pass**. One pass + planner ≈ **$0.00196**; three passes + planner ≈ **$0.00516**.
- If both roles use Gemini 2.5 Flash with those same illustrative tokens: planner ≈ **$0.0115**, critic ≈ **$0.0061/pass**, or ≈ **$0.0298** for planner + three critic passes.

These are arithmetic examples, **not a cap or predicted bill**. Image tokenization, large image payloads, hidden reasoning, provider routing, prompt length and retries change the amount. An eight-slide image critic run sends every rendered slide as a separate image; actual image token count and bill may differ substantially. Some catalog models have separate image rates or other charges. Check the dashboard and provider-reported usage; set an account-side spend limit if available. The engine logs usage fields but does not calculate real dollars.

Run the two picks with `python3 engine.py --brief brief.txt --sources sources.txt --assets assets.json --output ./run-ganesh --model inclusionai/ling-3.0-flash --vision-model google/gemini-2.5-flash-lite --max-revisions 2`. No live OpenRouter deck run was performed in the repository's mock test. If the first model yields invalid JSON or weak slides, fall back deliberately, then visually review the final PDF yourself.
