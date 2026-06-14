# AI Deals Watch

Veille automatisée des bons plans IA avec :

- Gemini 2.5 Flash-Lite
- Google Search Grounding
- GitHub Actions mardi/vendredi
- JSON historique
- rapport Markdown
- issue GitHub si changement
- notification Discord webhook avec découpe anti-limites

## 1. Créer les secrets GitHub

Dans le repo : `Settings -> Secrets and variables -> Actions -> New repository secret`.

Secrets nécessaires :

- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL` optionnel

## 2. Lancer manuellement

`Actions -> AI Deals Watch -> Run workflow`

## 3. Sorties générées

- `data/latest.json`
- `data/history/*.json`
- `reports/latest.md`
- `reports/changes.md`

## 4. Discord

La notification Discord est volontairement courte :

- message `content` découpé sous 1900 caractères ;
- retry automatique sur HTTP 429 ;
- limite anti-spam via `DISCORD_MAX_MESSAGES` ;
- rapport complet disponible dans `reports/latest.md`.

## 5. Tests locaux

```bash
python -m unittest discover -s tests
```

## 6. Notes

Le workflow utilise `timezone: "Europe/Paris"` dans les schedules GitHub Actions. Si votre compte/instance ne supporte pas encore cette option, remplacez par un cron UTC.
