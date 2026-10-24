# Business Validation Framework

**Status: framework only. The results file ships EMPTY — there is no invented
customer evidence in this repository.** Every entry below gets filled only by
real interviews/pilots, dated and sourced.

## 1. Discovery interview guide

Consent script: "We're building decision-support software for remittance
routing. Nothing you say is attributed to you or your company without written
permission. ~25 minutes."

### A. Remittance operators / exchange houses (the buyer we claim)

1. Walk me through the last week's UAE→BD transfers: how did you choose the
   route/exchange for each? Who decided?
2. What did that decision cost you last month in fees + FX spread — how do you
   even measure it? (Do they have a number?)
3. How do you handle compliance screening today? Who signs off a hold?
4. What happens when a recipient name almost matches a sanctions entry?
5. If a tool told you "route X gives the recipient ৳300 more than your default,
   with evidence", what would you need to trust it? What would you pay for it?
6. Who would block this purchase internally (compliance? IT? owner)?
7. Have you tried/built anything like this? What happened?

### B. Remittance senders & recipients (the end users, for the demo narrative)

1. How do you send money home? Why that way?
2. Do you know the exact amount your family received last time? How do you find out?
3. Have you heard of the government 2.5% incentive? Did you get it?
4. What would you change about the current process?

### C. Fintech product managers (integration partners)

1. How do you add international payout to your product today?
2. What does a payout-integration build cost you in eng-months?
3. What would make you integrate a third-party routing API instead of building?
4. What's your procurement/security review process for a vendor like us?

### D. Payments & compliance professionals

1. What would make you trust an automated screening recommendation enough to
   rely on it (vs your current process)?
2. What audit trail does your regulator expect on a routing decision?
3. Where do fuzzy-matching false positives cost you the most?

## 2. Results log (EMPTY — fill with real evidence only)

| # | Date | Segment | Interviewee role | Segment size signal | Key quotes/evidence | Implication for assumption # | Confirmed / Contradicted / Unclear |
| :- | :- | :- | :- | :- | :- | :- | :- |
| 1 | | | | | | | |

## 3. Riskiest assumptions register

| # | Assumption | Why it matters | How we'd validate | Kill criterion |
| :- | :- | :- | :- | :- |
| 1 | Operators route ≥ 50% of eligible volume through a third-party API | Drives the entire ROI model | 5 operator interviews + pilot data | < 20% in pilot → rethink WTP model |
| 2 | Operators can share real all-in cost baselines | ROI needs honest baseline input | Interview Q-A2 | If unanswerable → sell audit/compliance value instead of savings |
| 3 | UAE SME operators buy without enterprise procurement | Defines reachable segment | Interview Q-A6 + one pilot negotiation | procurement demands SOC 2/ISO → move up-market timeline out |
| 4 | Per-execution pricing acceptable | Pricing model choice | Interview Q-A5 | Insist on flat → model A (SaaS) |
| 5 | Intelligence (not the transfer itself) is what they pay for | Positioning | Interview Q-A5 | If they only value execution → we need licensed partners before revenue |

## 4. Pilot design (what "validated" means)

A corridor pilot is validated when: ≥ 1 operator runs ≥ 2 weeks of real
volume with the API in shadow mode (recommendations logged vs their actual
choices), producing measured delta in all-in cost and screening outcomes, with
the operator's written permission to cite anonymized numbers. Shadow mode
first — recommendations only, no execution — is the trust-building step.
