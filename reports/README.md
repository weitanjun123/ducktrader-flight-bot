# Flight Scout picture reports (9:16, 1080×1920)

Reference set chosen by Tan (25 Nov 2026) — reuse this exact look for future Jeju fare reports:
1. `1_jeju_fare_heatmap.png` — departure date × check day fare heatmap (gold = cheaper) + "Best time to buy" day × hour heatmap + 3 summary cards
2. `2_cheapest_dates.png` — departures ranked by today's fare, change since first check, this week's low–high range bar
3. `3_key_takeaways.png` — 6 takeaway cards + bottom line

Style: charcoal gradient, gold #d4af37/#f3d36b + white, Inter Display (Bebas/Oswald not installed in Claude's workspace), red only for price rises, DUCKTRADER4444 footer with data source + not-financial-advice.
`kit/` holds the HTML templates and the Python that computes their numbers from `data/prices.csv` (render with Playwright at 1080×1920).
