# xPay frontend refresh

## Implementation

Refresh the existing Next.js 14 frontend in place without changing the API contract or the send/quote/review/receipt lifecycle. The homepage remains the primary remittance workflow; `/roi` remains the operator-facing calculator. The updated homepage adds a responsive product shell, visible corridor context, a send-money panel, route intelligence summary, trust/compliance indicators, and a richer route quote comparison while preserving voice input, Bangla toggle, quote binding, and receipt details.

Project structure:
- `frontend/app/page.tsx`: client-side send, quote, review, and receipt screens.
- `frontend/app/globals.css`: global visual system, responsive layout helpers, custom controls, and motion.
- `frontend/app/layout.tsx`: metadata and document shell.
- `frontend/components/`: reusable existing flow, microphone, and blockchain trail components.
- `frontend/lib/`: existing API contracts, formatting helpers, types, and translations.
- `frontend/public/manus-routes.json`: route manifest for `/` and `/roi`.

## Design

Three candidate styles: **Night-market fintech** (0.06), **Editorial remittance ledger** (0.07), **Quiet utility banking** (0.05).

Chosen style — **Night-market fintech**.

- **Design Movement:** premium fintech dashboard with the contrast and warmth of a Dhaka night market: ink-black surfaces, saffron highlights, and emerald action states.
- **Core Principles:** recipient-first hierarchy; transparent economics; calm, grounded trust signals; fast scanning on mobile.
- **Color Philosophy:** near-black/navy creates focus and seriousness, warm sand makes numbers feel human and tactile, saffron owns the brand, and emerald is reserved for confirmed value and eligibility.
- **Layout Paradigm:** asymmetric two-column workspace with a persistent context rail and a dominant transaction canvas; quote cards read like a ranked market board rather than a generic form.
- **Signature Elements:** saffron route index markers, fine dashed ledger dividers, and a floating corridor status chip.
- **Interaction Philosophy:** every control answers one question, selected routes show their value delta, and actions remain reversible until the exact quote is confirmed.
- **Animation:** short ease-out lifts for cards, subtle pulse for live status, and no decorative motion during amount entry or compliance review.
- **Typography System:** Geist/system sans for UI and headlines; tabular numerals for money; compact uppercase labels for operational metadata.
- **Brand Essence:** the remittance co-pilot that makes the money arriving matter more than the fee advertised. Personality: clear, protective, quietly ambitious.
- **Brand Voice:** precise, warm, and direct. Example lines: “See what arrives before you send.” “Your quote is bound to this exact route.”
- **Wordmark & Logo:** a split-ring mark suggesting two currencies converging into one recipient outcome, paired with a compact wordmark.
- **Signature Brand Color:** saffron `#F4B942`.
