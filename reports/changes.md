# Changements veille bons plans IA

- Généré le : `2026-08-25T02:32:50+00:00`
- Nouvelles offres : `7`
- Offres modifiées : `5`
- Offres disparues : `6`

## Nouvelles offres

### 🆕 Mistral AI Free Experiment Tier — Mistral AI
- Type : API LLM
- Région : Monde
- Score usage : 3/5
- Gain : Accès rate-limited à tous les modèles Mistral pour évaluation et prototypage. Pas de carte bancaire requise.
- Limites : Limites de débit (~1 RPS, 30 RPM). Pas suffisant pour la production.
- Pièges : Les limites de débit sont strictes pour la production. Les prompts peuvent être utilisés pour améliorer les modèles.
- Validité : Non précisé
- Lien : https://mistral.ai/technology/api/

### 🆕 OpenAI API Free Credits — OpenAI
- Type : API LLM
- Région : Monde
- Score usage : 3/5
- Gain : Crédits d'essai initiaux (historiquement $5-$18) pour tester les modèles GPT-4o Mini, GPT-3.5 Turbo.
- Limites : Crédits limités et expirant après 3 mois. Limites de débit strictes. Accès aux modèles avancés (GPT-4o, GPT-5) payant.
- Pièges : Les crédits sont temporaires et s'épuisent rapidement. Nécessite une carte bancaire pour dépasser les crédits gratuits.
- Validité : Non précisé
- Lien : https://openai.com/api/

### 🆕 Anthropic Claude API Free Credits — Anthropic
- Type : API LLM
- Région : Monde
- Score usage : 2/5
- Gain : Crédits initiaux pour les nouveaux comptes API.
- Limites : Montant des crédits et durée non précisés. Pas de free tier API continu.
- Pièges : Pas de free tier API continu, nécessite un paiement dès l'épuisement des crédits initiaux.
- Validité : Non précisé
- Lien : https://www.anthropic.com/api

### 🆕 Together AI Signup Credits — Together AI
- Type : API LLM (Inference)
- Région : Monde
- Score usage : 4/5
- Gain : Crédits d'inscription ($25-$50) pour accéder à plus de 200 modèles open-source.
- Limites : Crédits d'essai avec expiration typique de 30-90 jours. Programme startup jusqu'à $50k (nécessite éligibilité).
- Pièges : Les crédits d'inscription sont limités dans le temps. Le programme startup peut nécessiter une validation.
- Validité : Non précisé
- Lien : https://api.together.ai/

### 🆕 Replicate API Free Credits — Replicate
- Type : API Image, Video, Audio Generation
- Région : Monde
- Score usage : 3/5
- Gain : Crédits de calcul gratuits limités pour tester les modèles hébergés par la communauté.
- Limites : Crédits limités. La disponibilité et les performances des modèles peuvent varier.
- Pièges : Les crédits sont limités et peuvent s'épuiser rapidement. La performance dépend des modèles hébergés.
- Validité : Non précisé
- Lien : https://replicate.com/

### 🆕 Pixazo Free Tier (Image, Video, Audio) — Pixazo
- Type : API Image, Video, Audio Generation
- Région : Monde
- Score usage : 3/5
- Gain : Accès gratuit aux API de génération d'images (Flux Schnell, Stable Diffusion 3.5, SDXL), vidéo (LTX) et audio (Pixazo Tracks).
- Limites : Non précisé, mais implicitement limité pour un usage gratuit.
- Pièges : Les limites exactes du free tier ne sont pas clairement détaillées.
- Validité : Non précisé
- Lien : https://pixazo.com/

### 🆕 Nebius AI Lift Program (via NVIDIA Inception) — Nebius
- Type : GPU Cloud, Inference Credits
- Région : Monde
- Score usage : 5/5
- Gain : Jusqu'à $150,000 en crédits cloud + $10,000 en crédits d'inférence pour les membres NVIDIA Inception éligibles.
- Limites : Nécessite l'adhésion au programme NVIDIA Inception. Les crédits sont basés sur les besoins en calcul.
- Pièges : Conditionné par l'adhésion à NVIDIA Inception. Le montant exact dépend de la proposition.
- Validité : Non précisé
- Lien : https://nebius.com/ai-lift


## Offres modifiées

### ♻️ Gemini API (via AI Studio) — Google
- Type : API LLM, Image Generation
- Région : Monde
- Score usage : 5/5
- Gain : Accès gratuit et continu aux modèles Gemini Flash et Pro (texte, image). Généreux quotas journaliers pour le prototypage. Pas de carte bancaire requise pour AI Studio.
- Limites : Limites de débit réduites par rapport aux plans payants. Nécessite Vertex AI pour les charges de production.
- Pièges : Les quotas, bien que généreux, peuvent être limitants pour une utilisation intensive en production.
- Validité : Non précisé
- Lien : https://ai.google.dev/

### ♻️ Groq Free Tier — Groq
- Type : API LLM (Inference)
- Région : Monde
- Score usage : 4/5
- Gain : Inférence ultra-rapide sur modèles open-source (Llama, Qwen). 30 RPM, 14,400 RPD, 6,000 TPM. Pas de carte bancaire requise.
- Limites : Modèles open-source uniquement. Limites de débit strictes pour la production.
- Pièges : La sélection de modèles est limitée aux modèles open-source. Les limites de débit peuvent être atteintes rapidement en production.
- Validité : Non précisé
- Lien : https://groq.com/

### ♻️ Hugging Face Inference API (Serverless) — Hugging Face
- Type : API LLM, Image, Embeddings
- Région : Monde
- Score usage : 4/5
- Gain : Accès gratuit à des milliers de modèles open-source (sous 10B paramètres). Quelques centaines de requêtes par heure.
- Limites : Modèles limités à ~10B paramètres. Cold starts possibles. Limites de débit par heure.
- Pièges : Cold starts sur les modèles moins populaires. Limites de débit peuvent être contraignantes pour des usages intensifs.
- Validité : Non précisé
- Lien : https://huggingface.co/inference-api

### ♻️ Cloudflare Workers AI — Cloudflare
- Type : API Image Generation, LLM
- Région : Monde
- Score usage : 3/5
- Gain : 10,000 Neurons par jour gratuits pour l'inférence (incluant image et LLM). Accès à plus de 100 modèles.
- Limites : Quota journalier. Nécessite un plan Workers payant ($5/mois) pour dépasser le quota gratuit.
- Pièges : Le quota gratuit est limité. Nécessite un plan payant pour une utilisation plus poussée.
- Validité : Non précisé
- Lien : https://developers.cloudflare.com/workers-ai/

### ♻️ Vast.ai Startup Program — Vast.ai
- Type : GPU Cloud
- Région : Monde
- Score usage : 4/5
- Gain : $2,500 en crédits GPU gratuits pour les startups éligibles.
- Limites : Nécessite une application et une validation. Les crédits sont liés à la dépense.
- Pièges : Le programme est axé sur les startups et nécessite une application. Les crédits sont un match de dépenses, pas un don pur.
- Validité : Non précisé
- Lien : https://vast.ai/startup-program


## Offres disparues du top

- Crédits d'essai OpenAI — OpenAI
- Free Tier API (1000 appels/mois) — Cohere
- Free Tier GPU Cloud — RunPod
- Crédits de démarrage / Free Tier (limité) — Railway
- Free Tier (modèles open-source) — Mistral AI (La Plateforme)
- Crédits de démarrage (200 requêtes/jour) — Requesty
