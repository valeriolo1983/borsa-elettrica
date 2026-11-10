# Borsa Elettrica Europa

Dashboard dei prezzi elettrici europei: https://valeriolo1983.github.io/borsa-elettrica/

- **Ingrosso** (mercato del giorno prima, €/MWh) per 41 zone, da [Energy-Charts](https://energy-charts.info) (Fraunhofer ISE). Andamenti, confronti tra zone, profilo a 15 minuti, classifica.
- **Bollette domestiche** per paese da [Eurostat nrg_pc_204](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table) e per capitale da HEPI.

I dati in `data/` vengono aggiornati da GitHub Actions (`.github/workflows/update.yml`) più volte al giorno.
Per un aggiornamento manuale: scheda **Actions → Aggiorna prezzi → Run workflow**.
