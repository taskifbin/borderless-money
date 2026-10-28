# Manual QA record

What was verified by real browser automation on 2026-10-28 (production build,
`next start`, backend on :8000), and what still needs a physical device.

## Verified in browser (this repo, production build)

| Check | Result |
| :--- | :--- |
| 375 px class viewport (360×812): home screen | **no horizontal overflow** — `scrollWidth == clientWidth == 360`, zero elements extending past the viewport; hero, stat tiles, and send card wrap correctly (screenshot reviewed) |
| 375 px class viewport: quote screen (Bangla, 5 routes) | **no horizontal overflow**, headline ৳33,423.20 + route cards stack correctly |
| Bangla rendering (F5) | home, send card, quote screen, and /roi all render Bangla; `document.documentElement.lang == "bn"` after toggling; Bengali conjuncts render correctly (no tofu) on both pages |
| /roi reads persisted language | switching to বাং on `/` then opening `/roi` renders the calculator fully in Bangla |
| `?scenario=fuzzy_review` (F7) | quote decision becomes `FUZZY_MATCH_REVIEW` and the quote screen shows the amber **"Compliance hold — manual review required"** banner — verified live |
| `?scenario=high_risk` (F7) | quote decision becomes `HIGH_RISK` and the quote screen shows the **"Compliance review required"** banner — verified live |

## Requires device verification (cannot be automated here)

| Check | Why | Status |
| :--- | :--- | :--- |
| Android Chrome voice input (mic → amount) | uses the browser `SpeechRecognition` / `webkitSpeechRecognition` API, which only exists on real Chrome (desktop/Android); the automation browser does not expose it, and mic permission prompts cannot be granted headlessly | **requires device verification** — test on Android Chrome: tap mic, say "one thousand", confirm the amount field fills and the "Heard: …" line shows the transcript; Bengali recognition (`bn-BD`) depends on the device's Google voice services |
| iOS Safari voice input | same API gap — Safari has `webkitSpeechRecognition` behind a flag | **requires device verification** |
| Notch / safe-area insets and pinch-zoom on real phones | automation viewport has no OS chrome | **requires device verification** |

## Regression notes

- Recommended badge stays on the EV-winning route (Stellar Hybrid Anchor,
  ৳33,423.20) in both languages — the F1 pre-select behavior survived the
  i18n refactor (verified by clicking "Get best rate" in Bangla).
