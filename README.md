# DuckTrader flight bot ✈️

Watches Google Flights prices for **Singapore ⇄ Jeju** (7-night round trips leaving 24 May – 14 Jun 2027,
4 adults + 3 children, economy) and DMs Tan on Telegram when a price is cheap.

## What it does
| When | What |
|---|---|
| Every 6 hours | Checks **all 22 departure dates** → finds the cheapest week |
| Every hour | Checks your planned dates (**1–8 Jun**) + the current cheapest week → builds the "best time to buy" study |
| Any check | 🚨 DM if a price is a **new low**, **15%+ below its 30-day average**, or under your **target price** |
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
- Prices come from Google Flights via the free open-source [fast-flights](https://github.com/AWeirdDev/flights) library. No API key, no cost.
  If Google changes its page the bot DMs a ⚠️ problem notice.
- Prices are converted to S$ with the free Frankfurter FX rate. Per-person = total ÷ 7 (kids' fares may differ slightly).
- Budget airline sales on their own sites (e.g. Scoot) may appear on Google Flights a little later.

Secrets: `FLIGHT_BOT_TOKEN`, `FLIGHT_CHAT_ID`.
