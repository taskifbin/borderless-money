# Borderless Money — Submission Plan (Oct 24 → Oct 31) — v2, corrected

Deadline: **Oct 31, 2026, 11:59 PM GMT+6** (Idea to Unicorn preliminary). **Plan: submit Oct 29** — do not wait for Oct 31. The engineering is done; the packaging is the only thing between us and the preliminary. This v2 supersedes the earlier plan: recording moved up to Oct 25–26, submission to Oct 29, and three concrete artifacts are assigned today/tomorrow (portal-requirements paragraph, unit economics, NRB outreach log).

## ⚙️ Decision record

**Zero to Launch: NOT entering.** (Decided Oct 24.) No dedicated sub-team exists; a live-build format would cannibalize the video, NRB outreach, and recording week. Revisit only if the preliminary is submitted early (Oct 29) AND a two-person sub-team volunteers. Otherwise this is closed — nobody relitigates it on Day 5.

## 📋 Portal requirements (fill TODAY from the submission form)

> **[TEAM LEAD — open the portal form and complete this paragraph before anything else.]**
> Video: length limit **[___]** · format **[___]** · upload target (YouTube public/unlisted?) **[___]** · caption/subtitle rules **[___]** · file/link field **[___]**.
> Also required on the form: **[team member fields, NRB collaborator field?, one-pager attachment?, demo URL field?, KPI field?, track/challenge selection = FinSphere AI → Borderless Money]**.
> Submission status: **[ ] not started / [ ] in progress / [ ] submitted (screenshot saved)**

## 📇 NRB outreach log (start TODAY)

Template (three sentences): one on the product, one on the ask, one on the time commitment.

> "I'm building Borderless Money — an AI remittance router for the UAE→Bangladesh corridor that optimizes for the exact taka a family receives, including the government's 2.5% incentive — for the AI Builders Congress (Idea to Unicorn). Could I get 30 minutes of your time, or an advisor letter, as our NRB collaborator? Total commitment is one call now and a name on the submission."

| # | Name | Role / corridor | Channel | Sent | Replied | Outcome |
| -- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | | | LinkedIn | | | |
| 2 | | | LinkedIn | | | |
| … | *(15 messages by end of today — least technical teammate owns this)* | | | | | |

Rule: if none respond by Oct 30, omit the NRB claim entirely — never fabricate.

## The 7 days (corrected)

| Day | Action | Owner | Output |
| :--- | :--- | :--- | :--- |
| **Today (Oct 24)** | Open the portal submission form; record every video requirement in the section above. | Team lead | Portal-requirements paragraph filled |
| **Today (Oct 24)** | Send 15 NRB LinkedIn messages (template above); track replies in the log. | Least technical teammate | 15 sent; log live |
| **Today (Oct 24)** | ✅ Unit-economics model drafted — business lead validates the three numbers (take rate, CAC, 6-month target) and tunes the assumptions. | Business lead | [docs/unit-economics.md](unit-economics.md) |
| **Oct 25** | Verify the money figures against Bangladesh Bank releases (no unverified stat goes on camera); finalize one-pager text. | Routing lead | Verified stats in script |
| **Oct 25–26** | **Record the video** against the five segments (docs/demo-script.md): fuzzy-hold shot at 1:30, Bangla quote screen at 1:45. Rough cut by Oct 26 night. | Frontend + editor | Rough cut |
| **Oct 27** | Internal screening: someone who has NOT seen the product watches once and says what it does. If they can't, re-cut same day. | Whole team | Final cut |
| **Oct 27** | Host the demo publicly (Vercel + Render/Fly, or docker compose on a VPS). Keep local fallback + offline backup recording. | Backend lead | A URL a judge can click |
| **Oct 28** | Draft the 3-minute spoken pitch (docs/pitch-script.md — already drafted; rehearse twice with a stopwatch) | Presenter | Rehearsed pitch |
| **Oct 29** | **Submit** the video and all portal fields. Screenshot the confirmation. | Team lead | Confirmation |
| **Oct 30–31** | Buffer: NRB follow-ups, one-pager polish, portal corrections. | All | — |

## P1 — score lifters (only if the table above is green)

- Replace the sample SDN list with the current official XML/CSV export + cite it.
- Add a third corridor config (my_bd.json) — three corridors on screen beats two.
- Public `/metrics` dashboard route for the video's closing shot.
- Retrain the GNN on a public financial-fraud dataset and swap eval.json.

## P2 — in-person round (Dec 26; nothing this week)

Hosted demo + offline backup, 5-slide deck mapped to the six criteria, responsible-AI one-pager, unit-economics deep dive with pilot data replacing assumptions, and two more full rehearsals of docs/pitch-script.md.

## Risk register

| Risk | Mitigation |
| :--- | :--- |
| "Mocked GNN" question in Q&A | Trained GCN shipped with honest eval (AUC 0.9038, synthetic benchmark, ceiling documented). One-liner in docs/pitch-script.md. |
| "Thin wrapper" objection | The jurisdiction rule engine (incentive math, sanctions, ISO 20022, corridor configs) + the B2B API — show `/docs` and the corridor table. |
| Stellar regulatory question | "Retail crypto-to-fiat is restricted in Bangladesh, so the hybrid model keeps digital-asset settlement institutional and back-end — sender and recipient only ever see taka." |
| Live demo failure on Dec 26 | Hosted URL + offline backup recording + local fallback; pitch script works without any screen. |
| Unverified statistics on camera | Only Bangladesh Bank-verified figures; participant counts only from the portal on submission day. |
| NRB gap at submission | 15 messages Oct 24; if none by Oct 30, omit the claim — never fabricate. |
| Invented numbers | Forbidden. Everything quoted comes from `/metrics`, docs/unit-economics.md (labeled assumptions), or verified sources. |
