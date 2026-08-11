# Changements veille bons plans IA

- Généré le : `2026-08-11T03:12:36+00:00`
- Nouvelles offres : `9`
- Offres modifiées : `3`
- Offres disparues : `9`

## Nouvelles offres

### 🆕 Google AI Studio & Gemini API Free Tier — Google
- Type : LLM API, Image Generation
- Région : Monde
- Score usage : 5/5
- Gain : Jusqu'à 1000 requêtes/jour (Gemini Flash) ou 250 requêtes/jour (Gemini Pro) sur le modèle d'image. Accès API Gemini.
- Limites : Limites de requêtes par jour/minute. L'éligibilité dépend de la région et de l'âge (18+). Nécessite un compte Google Cloud pour dépasser les limites.
- Pièges : Les quotas peuvent être stricts. La disponibilité des modèles peut varier. Nécessite un compte Google Cloud pour une utilisation plus poussée.
- Validité : Non précisé
- Lien : https://ai.google.dev/studio/pricing

### 🆕 Cloudflare AI Gateway Free Tier — Cloudflare
- Type : API Gateway, Rate Limiting, Caching
- Région : Monde
- Score usage : 4/5
- Gain : Accès aux fonctionnalités de base (analytics, caching, rate limiting) sans frais par appel. 100 000 logs AI Gateway par mois.
- Limites : Limite de 100 000 logs par mois sur le plan gratuit. L'utilisation intensive des Workers peut entraîner des coûts. Les logs au-delà du quota ne sont pas stockés.
- Pièges : Le plafond de logs peut être rapidement atteint pour des applications à fort trafic. Les coûts des Workers peuvent s'accumuler si l'utilisation est très élevée.
- Validité : Non précisé
- Lien : https://www.cloudflare.com/fr-fr/products/ai-gateway/

### 🆕 Amazon Polly Free Tier — AWS
- Type : Text-to-Speech API
- Région : Monde
- Score usage : 3/5
- Gain : 5 millions de caractères par mois pendant les 12 premiers mois.
- Limites : Valable pour les 12 premiers mois suivant la création du compte AWS. Nécessite un compte AWS.
- Pièges : La limite de 12 mois peut être un piège pour une utilisation à long terme. Nécessite une configuration AWS.
- Validité : Non précisé
- Lien : https://aws.amazon.com/polly/pricing/

### 🆕 Google Cloud TTS Free Tier — Google Cloud
- Type : Text-to-Speech API
- Région : Monde
- Score usage : 4/5
- Gain : 1 million de caractères par mois (voix standard) ou 250 000 caractères (voix WaveNet/Neural2).
- Limites : Nécessite un compte Google Cloud et l'activation de la facturation (pas de frais tant que les limites ne sont pas dépassées).
- Pièges : Activation de la facturation requise, ce qui peut être un frein pour certains. Les limites de caractères peuvent être atteintes rapidement avec des textes longs.
- Validité : Non précisé
- Lien : https://cloud.google.com/text-to-speech/pricing

### 🆕 Microsoft Azure TTS Free Tier — Microsoft Azure
- Type : Text-to-Speech API
- Région : Monde
- Score usage : 3/5
- Gain : 500 000 caractères neuronaux par mois.
- Limites : Nécessite un compte Azure. Pas de date d'expiration précisée pour le niveau F0.
- Pièges : Nécessite une configuration Azure. Le quota peut être limitant pour des projets à gros volume.
- Validité : Non précisé
- Lien : https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/

### 🆕 Vast.ai Marketplace — Vast.ai
- Type : GPU Cloud, Inference
- Région : Monde
- Score usage : 4/5
- Gain : Accès à une large gamme de GPUs à des prix compétitifs (à partir de 0.02$/hr pour des GPUs plus anciens).
- Limites : Prix fluctuants basés sur l'offre et la demande. Minimum de dépôt de 5$ requis (carte bancaire ou crypto). Le stockage est facturé séparément.
- Pièges : La fiabilité peut varier considérablement entre les hôtes. Le stockage est facturé même lorsque les instances sont arrêtées. Nécessite une carte bancaire ou crypto pour le dépôt.
- Validité : Non précisé
- Lien : https://vast.ai/

### 🆕 AWS Free Tier (Selected AI Services) — AWS
- Type : Various AI Services (Rekognition, Comprehend, Lex, Transcribe, Polly)
- Région : Monde
- Score usage : 4/5
- Gain : Limites mensuelles généreuses pour plusieurs services IA (ex: 1000 images/mois pour Rekognition, 5M caractères/mois pour Comprehend pendant 12 mois).
- Limites : Certains services sont limités aux 12 premiers mois. D'autres sont 'toujours gratuits' avec des limites mensuelles. Nécessite un compte AWS.
- Pièges : La limite de 12 mois pour certains services est un piège. La complexité de l'écosystème AWS peut être intimidante. Risque de dépassement des quotas.
- Validité : Non précisé
- Lien : https://aws.amazon.com/free/

### 🆕 Google Cloud Free Tier ($300 Credits) — Google Cloud
- Type : Cloud Services, AI APIs
- Région : Monde
- Score usage : 4/5
- Gain : 300$ de crédits pour essayer les produits Google Cloud pendant une période limitée.
- Limites : Les crédits sont valables pour une durée limitée (souvent 90 jours) et doivent être utilisés pour tester des services. Nécessite un compte Google Cloud et l'activation de la facturation.
- Pièges : Les crédits expirent. L'activation de la facturation est requise. L'écosystème GCP peut être complexe.
- Validité : Non précisé
- Lien : https://cloud.google.com/free

### 🆕 AssemblyAI Free Tier — AssemblyAI
- Type : Speech-to-Text API
- Région : Monde
- Score usage : 3/5
- Gain : Crédits gratuits à l'inscription pour tester l'API (montant non précisé mais suffisant pour du prototypage).
- Limites : Les crédits sont à l'inscription et sont limités. Le passage en production est payant.
- Pièges : Les crédits gratuits sont limités et destinés au test. Le passage en production peut être coûteux.
- Validité : Non précisé
- Lien : https://www.assemblyai.com/


## Offres modifiées

### ♻️ Hugging Face Inference API (Serverless Free Tier) — Hugging Face
- Type : Inference API, Model Hosting
- Région : Monde
- Score usage : 4/5
- Gain : Quelques centaines de requêtes par heure pour les modèles < 10B paramètres. Idéal pour le prototypage.
- Limites : Limité aux modèles < 10B paramètres. Cold starts possibles sur les modèles moins populaires (10-30s).
- Pièges : Les limites de requêtes peuvent être restrictives pour une utilisation intensive. Les cold starts peuvent impacter la latence.
- Validité : Non précisé
- Lien : https://huggingface.co/inference-api

### ♻️ RunPod Starter Tier Credits — RunPod
- Type : GPU Cloud, Inference
- Région : Monde
- Score usage : 3/5
- Gain : 1000$ de crédits pour l'accès à la plateforme.
- Limites : Destiné aux startups. La préférence est donnée aux entreprises ayant levé des fonds. L'offre peut être soumise à une validation.
- Pièges : Principalement orienté startups et potentiellement VC-backed. Peut nécessiter une validation d'éligibilité.
- Validité : Non précisé
- Lien : https://www.runpod.io/startup-program

### ♻️ Together AI Trial Credits — Together AI
- Type : Inference API, Model Hosting
- Région : Monde
- Score usage : 4/5
- Gain : 25$ à 50$ de crédits d'essai pour les nouveaux comptes.
- Limites : Les crédits ont une durée de validité typique de 30-90 jours.
- Pièges : Les crédits d'essai ont une durée de vie limitée. L'offre Startup Accelerator ($50K) est plus adaptée aux entreprises établies.
- Validité : Non précisé
- Lien : https://api.together.ai/


## Offres disparues du top

- Google Gemini API (AI Studio) — Google
- Groq Free Tier — Groq
- Mistral AI Free Tier (La Plateforme) — Mistral AI
- OpenAI Free Credits — OpenAI
- Anthropic Free Credits — Anthropic
- Fireworks AI New User Credits — Fireworks AI
- AWS Free Tier (SageMaker) — AWS
- Vast.ai Startup Program — Vast.ai
- Railway Free Trial Credits — Railway
