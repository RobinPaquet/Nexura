# AI Scanner — Design Document
## Phase 2 : Layer 1 (Screener) + Layer 2 (News ESG)

**Date :** 1 avril 2026
**Contexte :** Phase 2 du Weefin Terminal. Layer 3 (WeefinScore quantitatif) est reporté en Phase 3 avec le Backtest.

---

## 1. Architecture globale

```
weefin-api (Railway)
├── FastAPI (existant)
│   ├── GET /scanner/alerts        — dernières alertes
│   ├── GET /scanner/screener      — résultats du screener
│   └── POST /scanner/config       — sauvegarder les filtres
│
├── Celery Beat (nouveau worker Railway)
│   ├── task: run_screener()       — toutes les 15 min
│   └── task: fetch_esg_news()     — toutes les heures
│
└── Redis (nouveau service Railway)
    └── broker Celery + cache résultats
```

**Infrastructure :**
- Redis ajouté sur Railway (free tier)
- Celery worker déployé comme second service Railway (même repo, commande différente)
- Notifications : in-app uniquement (badge + feed dans l'UI terminal)
- Frontend poll `/scanner/alerts` toutes les 60s

---

## 2. Base de données (PostgreSQL existant)

Deux nouvelles tables :

**`scanner_alerts`**
```
id          SERIAL PRIMARY KEY
isin        VARCHAR
company     VARCHAR
type        VARCHAR   -- 'screener' | 'news'
sentiment   VARCHAR   -- 'positive' | 'negative' | 'neutral'
headline    TEXT
source_url  TEXT
score       FLOAT
created_at  TIMESTAMP
```

**`scanner_config`**
```
id              SERIAL PRIMARY KEY
esg_min         FLOAT     -- score ESG minimum
sectors_exclude TEXT[]    -- secteurs exclus
countries       TEXT[]    -- pays filtrés
coverage_min    FLOAT     -- couverture données minimum
updated_at      TIMESTAMP
```

---

## 3. Layer 1 — Screener par règles

**Celery Beat :** `run_screener()` toutes les 15 minutes

**Scope :** entreprises de la watchlist uniquement (pas les 26k — trop lourd pour le free tier Railway).

**Filtres configurables dans l'UI :**
| Filtre | Type | Défaut |
|---|---|---|
| ESG score min | slider 0-100 | 0 |
| Secteur | multiselect exclusion | aucun |
| Exclusions | checkboxes | charbon, armes, tabac |
| Pays | multiselect | tous |
| Couverture min | slider 0-1 | 0 |

**Logique :**
- Pour chaque entreprise de la watchlist → applique les filtres sur `companies.json`
- Si une entreprise entre ou sort des critères → crée une alerte `type='screener'` en DB

---

## 4. Layer 2 — Signaux news ESG

**Celery Beat :** `fetch_esg_news()` toutes les heures

**Source :** GDELT Project (gratuit, API REST publique, 400M+ articles)

**Pipeline :**
```
GDELT API (articles ESG dernières 24h)
  → Filtre : garder entreprises de la watchlist
  → Matching entité : nom → ISIN via companies.json
  → Classification sentiment
  → Score pertinence > seuil → alerte DB
```

**Classification — deux modes :**

*Mode règles (actif par défaut, sans clé Anthropic) :*
- Positif : `"carbon neutral"`, `"ESG award"`, `"renewable"`, `"sustainability report"`, `"net zero"`
- Négatif : `"greenwashing"`, `"violation"`, `"fine"`, `"scandal"`, `"lawsuit"`, `"emissions fraud"`
- Score = somme pondérée des mots trouvés dans titre + premier paragraphe

*Mode Haiku (activé si `ANTHROPIC_API_KEY` présente) :*
```python
if os.getenv("ANTHROPIC_API_KEY"):
    sentiment = classify_with_haiku(article)
else:
    sentiment = classify_with_rules(article)
```

**Format alerte générée :**
```json
{
  "isin": "FR0000131104",
  "company": "BNP Paribas",
  "type": "news",
  "sentiment": "negative",
  "headline": "BNP Paribas sued over greenwashing claims",
  "source_url": "https://...",
  "score": -0.82,
  "created_at": "2026-04-01T14:23:00Z"
}
```

---

## 5. Frontend — Page /scanner

**Layout :**
- Panneau gauche : Screener (filtres configurables + liste entreprises matchées)
- Panneau droit : Feed alertes (news + screener, tri par date)
- Badge compteur sur l'icône scanner dans la navbar (alertes non lues)
- Poll automatique toutes les 60s sur `/scanner/alerts`

---

## 6. Ce qui est reporté (Phase 3)

- Layer 3 : WeefinScore quantitatif (nécessite données historiques prix du Backtest)
- Scan univers complet STOXX 600 (nécessite infra plus puissante)
- Notifications email/push
