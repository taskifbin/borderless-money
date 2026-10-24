# pacs.008 mapping — documented subset (v1)

The receipt's ISO 20022 payload is **shaped like pacs.008** and validated against
this documented subset (tests/test_core.py::TestCompliance.test_pacs008_mapping).
It is NOT schema-validated against the full ISO 20022 XSD — that requires the
official schema package and is labeled accordingly.

## Fields emitted

| JSON path | Source | Rule |
| :--- | :--- | :--- |
| `MsgId` | transaction id | `"BM" + first 8 chars`, max 16 chars, uppercase |
| `CreDtTm` | transaction | ISO-8601 UTC timestamp |
| `Dbtr` | sender name | string |
| `Cdtr` | recipient name | string |
| `IntrBkSttlmAmt` | **gross − fees** | The interbank settlement amount is what actually settles bank-to-bank. **The government's 2.5% incentive is paid separately by the government**, so it is NOT part of this amount (correction from the earlier mapping). |
| `GovtIncentiveAmt` | incentive | Documented extension field carrying the incentive amount + currency, so the audit trail still shows it. |
| `SttlmInf.SttlmMtd` | constant | `"INGD"` (instructed) |
| `SttlmInf.ClrSys` | route rail | The selected hybrid rail name |

## Verification (one command)

```bash
python3 backend/tests/test_core.py TestCompliance
```

Asserts: field presence, `IntrBkSttlmAmt == gross − fees`, `GovtIncentiveAmt ==
incentive`, currency `BDT`, two-decimal formatting, MsgId ≤ 16 chars.
