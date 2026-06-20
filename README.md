# AI Deals Watch

Veille automatisée des bons plans IA avec :

- Gemini 2.5 Flash-Lite
- Google Search Grounding
- GitHub Actions mardi/vendredi
- JSON historique
- rapport Markdown
- issue GitHub si changement
- notification Discord webhook avec découpe anti-limites
- fallback robuste si Gemini renvoie une réponse vide, invalide ou rate-limitée

## 1. Créer les secrets GitHub

Dans le repo : `Settings -> Secrets and variables -> Actions -> New repository secret`.

Secrets nécessaires :

- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL` optionnel

## 2. Lancer manuellement

`Actions -> AI Deals Watch -> Run workflow`

Le workflow propose un mode `dry_run` pour tester GitHub Actions sans consommer de crédits Gemini.

## 3. Configuration Gemini

Le workflow force une configuration légère adaptée au free tier :

- `GEMINI_MODEL=gemini-2.5-flash-lite`
- `AI_DEALS_MAX_OFFERS=12`
- `GEMINI_MAX_OUTPUT_TOKENS=8192`
- `GEMINI_USE_GROUNDING=true`
- `GEMINI_MAX_RETRIES=1`

`GEMINI_MAX_RETRIES=1` évite de brûler plusieurs appels quand Gemini renvoie une réponse vide ou inutilisable.

## 4. Sorties générées

- `data/latest.json`
- `data/history/*.json`
- `reports/latest.md`
- `reports/changes.md`
- `reports/failed_raw_response.txt` uniquement si Gemini renvoie une réponse vide ou invalide

Quand `changed=false`, GitHub Actions ne commit pas les rapports. Les fichiers de debug sont tout de même disponibles dans l’artifact `ai-deals-debug` du run Actions.

## 5. Fallback Gemini

Si Gemini échoue avec quota/rate-limit, réponse vide `FinishReason.STOP`, ou JSON invalide :

1. le script réutilise `data/latest.json` ;
2. `reports/changes.md` indique que la dernière veille est conservée ;
3. la sortie GitHub `changed=false` évite de créer une issue factice ;
4. `reports/failed_raw_response.txt` capture le diagnostic quand il existe ;
5. l’artifact Actions `ai-deals-debug` permet de récupérer les rapports/debug même sans commit.

## 6. Discord

La notification Discord est volontairement courte :

- message `content` découpé sous 1900 caractères ;
- retry automatique sur HTTP 429 ;
- limite anti-spam via `DISCORD_MAX_MESSAGES` ;
- rapport complet disponible dans `reports/latest.md`.

## 7. Tests locaux

```bash
python -m py_compile scripts/run_watch.py
python -m unittest discover -s tests
```

## 8. Correction importante Gemini

Cette version n'utilise pas `response_mime_type="application/json"` avec `google_search`.
La combinaison Google Search tool + JSON MIME est rejetée ou fragile côté API Gemini.
Le script utilise donc Google Search Grounding en sortie texte, demande un JSON compact entre marqueurs, puis valide le JSON localement.

Marqueurs attendus :

```text
BEGIN_AI_DEALS_JSON
{...}
END_AI_DEALS_JSON
```

## 9. Notes

Le workflow utilise `timezone: "Europe/Paris"` dans les schedules GitHub Actions. Si votre compte/instance ne supporte pas encore cette option, remplacez par un cron UTC.
