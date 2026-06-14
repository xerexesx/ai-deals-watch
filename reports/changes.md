# Changements veille bons plans IA

- Généré le : `2026-06-14T11:54:06+00:00`
- Nouvelles offres : `12`
- Offres modifiées : `2`
- Offres disparues : `15`

## Nouvelles offres

### 🆕 Free Tier API avec accès à tous les modèles — Groq
- Type : API Inference
- Région : Monde
- Score usage : 4/5
- Gain : Accès gratuit à tous les modèles open-source (Llama, Mixtral, Gemma, etc.) avec des vitesses d'inférence très élevées (jusqu'à 1000 tokens/sec).
- Limites : Limité à 30 requêtes/min, 6000 tokens/min, 14400 requêtes/jour au niveau de l'organisation. Pas de carte bancaire requise pour le free tier.
- Pièges : Les limites du free tier sont insuffisantes pour la production. Le catalogue est limité aux modèles open-source.
- Validité : Non précisé
- Lien : https://console.groq.com/

### 🆕 Crédits de démarrage gratuits — Together AI
- Type : API Inference
- Région : Monde
- Score usage : 3/5
- Gain : 5$ de crédits gratuits à l'inscription pour tester divers modèles open-source.
- Limites : Les crédits sont généralement valides pour 30-90 jours. Nécessite un achat minimum de 5$ pour accéder à la plateforme.
- Pièges : Nécessite un achat minimum pour activer l'accès. Les crédits gratuits ont une durée de vie limitée.
- Validité : Non précisé
- Lien : https://together.ai/

### 🆕 Paiement à l'usage pour l'inférence — Replicate
- Type : API Inference / GPU Cloud
- Région : Monde
- Score usage : 4/5
- Gain : Paiement à la seconde pour l'utilisation des GPUs (à partir de 0.000025$/sec pour CPU, 0.0014$/sec pour A100). Modèles populaires facturés par sortie (ex: 0.003-0.04$ par image).
- Limites : Les modèles publics ne sont facturés que pendant le temps de traitement actif. Les modèles privés sont facturés pour toute la durée de vie de l'instance (incluant le temps d'attente).
- Pièges : Le coût peut augmenter rapidement pour les modèles privés ou les charges de travail intermittentes en raison du temps d'attente facturé.
- Validité : Non précisé
- Lien : https://replicate.com/

### 🆕 Crédits de démarrage gratuits — OpenAI
- Type : API LLM
- Région : Monde
- Score usage : 2/5
- Gain : 5$ de crédits gratuits pour les nouveaux utilisateurs.
- Limites : Les crédits sont à usage unique et peuvent avoir une durée de vie limitée. Nécessite une carte bancaire pour dépasser le quota initial.
- Pièges : Les crédits gratuits sont limités et ne suffisent que pour un prototypage très basique. OpenAI ne propose plus de crédits gratuits récurrents pour l'API.
- Validité : Non précisé
- Lien : https://platform.openai.com/

### 🆕 Free Tier Généreux pour Gemini API — Google AI Studio / Vertex AI
- Type : API LLM
- Région : Monde
- Score usage : 4/5
- Gain : Accès gratuit et continu aux modèles Gemini Flash et Pro avec des limites de requêtes généreuses.
- Limites : Limites de requêtes par minute et tokens par jour. Pas de carte bancaire requise pour AI Studio.
- Pièges : Les données d'utilisation peuvent être utilisées pour l'entraînement des modèles dans le free tier.
- Validité : Non précisé
- Lien : https://ai.google.dev/

### 🆕 Paiement à l'usage pour l'inférence GPU — Vast.ai
- Type : GPU Cloud
- Région : Monde
- Score usage : 4/5
- Gain : Tarifs très compétitifs pour la location de GPUs, souvent inférieurs à RunPod (ex: L40 40GB à 0.31$/hr).
- Limites : Les prix fluctuent quotidiennement. L'environnement est moins stable que les fournisseurs cloud traditionnels.
- Pièges : Moins de fiabilité et de support que les grands fournisseurs cloud. La disponibilité des GPUs peut varier.
- Validité : Non précisé
- Lien : https://vast.ai/

### 🆕 Free Tier pour API LLM et Multimodal — Cohere
- Type : API LLM / Embeddings
- Région : Monde
- Score usage : 3/5
- Gain : Free tier pour les API de génération de texte, embeddings et reranking.
- Limites : Limité à 100 RPM (requêtes par minute). Utilisable pour le prototypage et les applications à petite échelle.
- Pièges : Les limites de RPM peuvent être restrictives pour des applications plus intensives.
- Validité : Non précisé
- Lien : https://cohere.com/

### 🆕 API Gateway avec Free Tier — Cloudflare
- Type : API Gateway / Router
- Région : Monde
- Score usage : 3/5
- Gain : Fonctionnalités de base gratuites (analytics, caching, rate limiting). Les coûts proviennent de l'utilisation des Workers et des fournisseurs de modèles sous-jacents.
- Limites : Le plan gratuit des Workers inclut 100 000 logs AI Gateway/mois. L'utilisation au-delà nécessite un plan payant.
- Pièges : Les coûts réels dépendent de l'utilisation des Workers et des appels aux fournisseurs d'API IA sous-jacents. Pas de frais directs pour l'AI Gateway elle-même.
- Validité : Non précisé
- Lien : https://www.cloudflare.com/products/workers-ai/

### 🆕 Crédits pour développeurs et startups — Together AI
- Type : API Inference / GPU Cloud
- Région : Monde
- Score usage : 2/5
- Gain : Programme Startup Accelerator offrant jusqu'à 50 000$ de crédits pour les startups qualifiées.
- Limites : Programme basé sur une application, lié au stade de financement de la startup. Nécessite une société.
- Pièges : Non adapté aux freelances ou solo builders sans société. Processus de candidature potentiellement long.
- Validité : Non précisé
- Lien : https://www.together.ai/startup-accelerator

### 🆕 Free Tier pour API LLM — Mistral AI
- Type : API LLM
- Région : Monde
- Score usage : 2/5
- Gain : Accès à certains modèles via une API avec des limites de débit.
- Limites : Les détails du free tier et ses limites ne sont pas toujours clairement communiqués et peuvent varier. Souvent via des programmes d'essai ou des allocations limitées.
- Pièges : Le free tier est souvent limité dans le temps ou en volume, et peut nécessiter une inscription à des programmes spécifiques.
- Validité : Non précisé
- Lien : https://mistral.ai/

### 🆕 Crédits de démarrage pour développeurs — Vercel
- Type : Plateforme / AI Gateway
- Région : Monde
- Score usage : 2/5
- Gain : Crédits gratuits pour l'utilisation de l'AI Gateway et des fonctions serverless.
- Limites : Le plan Hobby est gratuit mais limité. Le plan Pro (20$/utilisateur/mois) inclut des crédits et des quotas plus élevés. Les crédits AI Gateway sont déduits d'un solde prépayé.
- Pièges : Les coûts d'utilisation de l'AI Gateway et des fonctions serverless peuvent s'accumuler rapidement. Le plan gratuit est très limité pour l'IA.
- Validité : Non précisé
- Lien : https://vercel.com/pricing

### 🆕 Paiement à l'usage pour l'inférence — Azure OpenAI Service
- Type : API LLM
- Région : Monde
- Score usage : 3/5
- Gain : Accès aux modèles OpenAI avec des options de tarification standard (pay-as-you-go) et provisionnée (PTU). Réduction de 50% avec l'API Batch.
- Limites : Les prix varient selon le modèle et le type de déploiement (Standard, Provisioned, Batch).
- Pièges : Pas de free tier significatif pour l'API. Les coûts peuvent être élevés pour les modèles les plus performants.
- Validité : Non précisé
- Lien : https://azure.microsoft.com/en-us/products/ai-services/openai-service/


## Offres modifiées

### ♻️ Free Tier pour API LLM et Speech-to-Text — Groq
- Type : API Inference
- Région : Monde
- Score usage : 3/5
- Gain : Accès gratuit à Whisper Large v3 pour la transcription audio (2000 requêtes/jour).
- Limites : Limité à 2000 requêtes audio par jour. Les limites globales du free tier s'appliquent.
- Pièges : Les limites quotidiennes peuvent être atteintes rapidement pour des volumes importants.
- Validité : Non précisé
- Lien : https://groq.com/

### ♻️ Paiement à l'usage pour l'inférence GPU — RunPod
- Type : GPU Cloud
- Région : Monde
- Score usage : 4/5
- Gain : Tarifs compétitifs pour la location de GPUs (ex: L40S à 0.86$/hr, A100 PCIe à 1.39$/hr). Paiement à la seconde.
- Limites : Les prix varient selon la configuration (GPU, RAM, CPU) et l'environnement (Community vs Secure Cloud).
- Pièges : Les coûts de stockage additionnels (disque conteneur, stockage réseau). La différence de prix entre Community et Secure Cloud peut être significative.
- Validité : Non précisé
- Lien : https://www.runpod.io/


## Offres disparues du top

- Crédits AWS Activate pour Startups — AWS
- Programme Cloud Google pour Startups (Crédits IA) — Google Cloud
- Crédits Gratuits OpenAI API — OpenAI
- Programme Startup Runpod — RunPod
- Free Tier API Mistral — Mistral AI
- Free Tier API Google Gemini (AI Studio) — Google
- Free Tier Hugging Face Hub — Hugging Face
- Crédits Gratuits Fireworks AI — Fireworks AI
- Crédits Cloud Microsoft pour Startups — Microsoft Azure
- Programme OpenAI pour Startups — OpenAI
- Programme AI Startup Bright Data — Bright Data
- Free Tier Ollama — Ollama
- Crédits Gratuits pour Startups (Divers) — Divers (AWS, GCP, Azure, NVIDIA)
- Programme Codex for Open Source (OpenAI) — OpenAI
- Free Tier API Google Gemini (Vertex AI) — Google Cloud
