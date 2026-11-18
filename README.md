# DuckTrader flight bot ✈️

Watches Google Flights prices for **Singapore ⇄ Jeju** (7-night round trips leaving 24 May – 14 Jun 2027,
4 adults + 3 children, economy, **direct flights only**) and DMs Tan on Telegram when a price is cheap.

## What it does
| When | What |
|---|---|
| Every 6 hours | Checks **all 22 departure dates** → finds the cheapest week |
| Every hour | Checks your planned dates (**1–8 Jun**) + the current cheapest week → builds the "best time to buy" study |
| Any check | 🚨 DM only on a real low: **cheapest price of any week so far**, **lowest yet for your planned 1–8 Jun dates**, **15%+ below that week's 30-day average**, or under your **target price**. Lows need 3+ days of history first. |
| Sunday 18:37 SGT | 📊 Weekly report: cheapest week, best day/hour to buy heatmap, price trend |

Every check is saved in `data/prices.csv` (time checked, days before departure, airline, price in S$).
`data/last_run.json` shows whether the latest run worked.

## Change settings
Edit `config.json` on GitHub:
- `target_price_per_person_sgd` – e.g. `450` to get an alert under S$450/person (`null` = off)
- `depart_from` / `depart_to` / `nights` – the travel window
- `adults` / `children`
- `focus_departures` – dates checked every hour

Saving the file triggers a fresh check automatically.

## Notes
- **Direct flights only** (`direct_only: true`, Tan's choice 18 Nov 2026). Dates where Google shows no direct flight are listed as "no direct flight", not as errors. Prices without an airline + time are ignored. See `checks/` for manual spot checks.
- Prices come from Google Flights via the free open-source [fast-flights](https://github.com/AWeirdDev/flights) library. No API key, no cost.
  If Google changes its page the bot DMs a ⚠️ problem notice.
- Prices are converted to S$ with the free Frankfurter FX rate. Per-person = total ÷ 7 (kids' fares may differ slightly).
- Budget airline sales on their own sites (e.g. Scoot) may appear on Google Flights a little later.

Secrets: `FLIGHT_BOT_TOKEN`, `FLIGHT_CHAT_ID`.
