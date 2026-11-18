# Manual checks

Spot checks of the bot's prices against Google Flights, newest first.

## 18 Nov 2026 — SIN ⇄ CJU, 24 → 31 May 2027, 4 adults + 3 children, economy
Screenshot from Tan's phone: `2026-11-18_google_24-31May_screenshot.png`

| Flight | Google (round trip, all 7) | Bot read |
|---|---|---|
| Scoot nonstop 12:35am → 7:25am, 5h50 | SGD 5,463 | US$4,254 ≈ S$5,483 ✅ |
| Cathay Pacific / HK Express via HKG, 9h20 | **SGD 4,283** (cheapest) | ❌ missed |
| Shenzhen Airlines via SZX, 9h55 | SGD 5,187 | ❌ missed |

Finding: prices are round-trip totals for all 7 (correct), but the parser only read the
nonstop flight and missed cheaper 1-stop itineraries. Fix in progress.
