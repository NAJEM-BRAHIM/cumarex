# Localisation Maroc - Paie (l10n_ma_hr_payroll)

Module Odoo 19 pour la paie marocaine conforme à la **Loi de Finances 2025-2026**.

## Installation

1. Copier le dossier `l10n_ma_hr_payroll` dans votre répertoire `addons`
2. Activer le mode développeur
3. **Apps** → *Update Apps List*
4. Rechercher "Maroc - Paie" et installer
5. Le module installera automatiquement les dépendances : `hr_payroll`, `hr_contract`, `l10n_ma`

## Configuration

### 1. Société
- Le pays de la société doit être **Maroc (MA)**

### 2. Contrat de travail
Pour chaque salarié, dans l'onglet **Paie Maroc** du contrat :
- **Date d'ancienneté** : pour le calcul automatique de la prime
- **Personnes à charge** : 0 à 6 (50 DH/personne/mois)
- **Taux frais professionnels** : 35% (par défaut) ou 25%
- **Indemnité de transport** : montant mensuel (exonérée jusqu'à 500 DH)
- **Indemnité de panier** : montant mensuel (exonérée jusqu'à 30 DH/jour, max 20% du brut)
- **Avantages en nature** : logement, voiture
- **CIMR** : si affilié, indiquer les taux salariaux et patronaux
- **Mutuelle** : montants fixes mensuels

### 3. Structure salariale
Sur la fiche contrat → **Salary Information** → sélectionner :
- **Structure salariale** : *Maroc - Salarié Standard*

## Règles salariales incluses

### Salaire Brut
| Code | Libellé | Description |
|------|---------|-------------|
| `BASIC` | Salaire de Base | Salaire contractuel |
| `ANCIENNETE` | Prime d'ancienneté | 5%/10%/15%/20%/25% selon ancienneté |
| `HS25` / `HS50` / `HS100` | Heures supplémentaires | Selon Art. 196 Code du Travail |
| `PRIME_REND` | Prime de rendement | Saisie manuelle |
| `PRIME_BILAN` | 13ème mois / Bilan | Saisie manuelle |
| `PRIME_EXC` | Prime exceptionnelle | Saisie manuelle |
| `IND_TRANSPORT` | Indemnité transport | Exonérée jusqu'à 500 DH |
| `IND_PANIER` | Indemnité panier | Exonérée 30 DH/jour, max 20% brut |
| `IND_REPR` | Indemnité représentation | Exonérée à 10% du base |
| `AVN_LOGEMENT` | Avantage logement | Imposable |
| `AVN_VOITURE` | Avantage voiture | Imposable |
| `SBG` | **Salaire Brut Global** | Total brut |
| `SBI` | **Salaire Brut Imposable** | SBG - exonérations |
| `SBC` | Salaire Brut Cotisable | Base CNSS/AMO |

### Cotisations Sociales (Part Salariale)
| Code | Libellé | Taux | Plafond |
|------|---------|------|---------|
| `CNSS_SAL` | CNSS salariale | **4,48%** | 6 000 DH |
| `AMO_SAL` | AMO salariale | **2,26%** | Déplafonné |
| `CIMR_SAL` | CIMR salariale | Variable | Selon contrat |
| `MUTUELLE_SAL` | Mutuelle | Fixe | Selon contrat |

### Charges Patronales
| Code | Libellé | Taux | Plafond |
|------|---------|------|---------|
| `CNSS_PAT` | CNSS patronale | **8,98%** | 6 000 DH |
| `ALLOC_FAM` | Allocations familiales | **6,40%** | Déplafonné |
| `TFP` | Taxe Formation Pro | **1,60%** | Déplafonné |
| `AMO_PAT` | AMO patronale | **4,11%** | Déplafonné |
| `CIMR_PAT` | CIMR patronale | Variable | - |
| `MUTUELLE_PAT` | Mutuelle patronale | Fixe | - |

**Total charges patronales standard : ~21,09%** (hors CIMR/mutuelle)

### Impôt sur le Revenu (Barème 2026)

#### Frais professionnels
- **35%** si salaire ≤ 78 000 DH/an
- **25%** au-delà
- Plafond : **35 000 DH/an** (~2 916,67 DH/mois)

#### Barème mensuel IR 2026
| Tranche RNI mensuel (DH) | Taux | Somme à déduire (DH) |
|--------------------------|------|----------------------|
| 0 - 3 333,33 | **0%** | 0 |
| 3 333,34 - 5 000 | **10%** | 333,33 |
| 5 000,01 - 6 666,67 | **20%** | 833,33 |
| 6 666,68 - 8 333,33 | **30%** | 1 500,00 |
| 8 333,34 - 15 000 | **34%** | 1 833,33 |
| > 15 000 | **37%** | 2 283,33 |

#### Charges de famille (LF 2026)
- **50 DH/personne/mois** (600 DH/an)
- Maximum **6 personnes** à charge

### Retenues
- `AVANCE` : Avance sur salaire
- `ACOMPTE` : Acompte
- `PRET` : Remboursement prêt
- `SAISIE` : Saisie-arrêt
- `ABS_NP` : Absences non payées

## Exemple de calcul

**Salarié célibataire, 10 000 DH brut, sans personnes à charge, ancienneté 3 ans**

```
Salaire de base                  10 000,00
Prime d'ancienneté (5%)             500,00
SBG (Salaire Brut Global)        10 500,00
SBC (= SBG, pas d'exo)           10 500,00

Cotisations salariales :
  CNSS (4,48% × 6 000)              -268,80
  AMO (2,26% × 10 500)              -237,30

Frais professionnels (35% × 10 500 plafonné)  : 2 916,67
SNI = 10 500 - 2 916,67 - 268,80 - 237,30 = 7 077,23

IR brut = (7 077,23 × 30%) - 1 500 = 623,17
IR net = 623,17 (pas de charges famille)

Salaire net = 10 500 - 268,80 - 237,30 - 623,17 ≈ 9 370,73 DH
```

## Sources légales

- Code Général des Impôts (CGI) : Articles 56-60 (assiette), Article 73 (barème)
- Code du Travail Marocain : Articles 196 (HS), 350-356 (ancienneté)
- Loi de Finances 2025 (réforme barème IR)
- Loi de Finances 2026 (revalorisation charges famille à 600 DH/an)
- Décrets CNSS 2026 (plafond maintenu à 6 000 DH)

## Limitations connues

Ce module est une **base de référence**. À adapter selon :
- Conventions collectives spécifiques (banque, BTP, etc.)
- Cas particuliers : exportateurs, zones franches, expatriés
- Bulletin de paie graphique (rapport QWeb à personnaliser)
- Déclarations Damancom (intégration export à développer)

## Licence

LGPL-3
