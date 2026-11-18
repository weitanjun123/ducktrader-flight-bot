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

### Follow-up (18 Nov, 19:30)
- Raw Google page saved by the bot (debug run) only contains the Scoot nonstop; connecting
  flights load later in the browser, so the HTML scraper can't see them.
- Tried the `fli` library (Google's GetShoppingResults API): most calls from GitHub's servers
  got an error response; the one that worked also only returned Scoot (`checks/probe/probe.txt`).
- 19:28 full scan read only 5 of 22 dates ("No flights found" pages) — Google blocks/limits
  repeated requests from GitHub's servers.
- Bad "Airline not shown" rows removed from data/prices.csv; correction sent on Telegram.
