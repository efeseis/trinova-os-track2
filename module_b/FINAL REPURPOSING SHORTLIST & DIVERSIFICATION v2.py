
# -*- coding: utf-8 -*-
"""
TRINOVA.OS — TRACK 2 — FINAL CANDIDATE (pipeline2)
BUB1B → MOLECULAR VULNERABILITY → DRUG REPURPOSING

Research hypothesis-generation pipeline.

Preserved components:
- BUB1B molecular-profile loading and consequence summary
- Seven mechanistic clusters and configurable axis weights
- Broad Repurposing Hub ingestion and normalization
- Mechanistic classification with matched-term provenance
- Molecular relevance and development-context scores
- Full ranking, cluster summary, repurposing shortlist, discovery set
- Complementary mechanistic-coverage hypotheses
- CSV, JSON, summary TXT, and QC TXT outputs

Important:
- Scores are heuristic prioritization aids, not validated probabilities.
- Mechanistic association does not establish therapeutic benefit.
- Broad "Launched" labels are not treated as proof of current approval.
- Combination hypotheses do not establish drug synergy.
- This script does not establish clinical causality or patient suitability.

Paths:
- Inputs: root/data/
- Outputs: root/output_final/
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

# The script is located in module_b, so its parent directory is the project root.
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTDIR = BASE_DIR / "output_final"

# Create the shared output directory if it does not exist.
OUTDIR.mkdir(parents=True, exist_ok=True)

# All input files are read from the shared root data folder.
TRACK2_ROOT = DATA_DIR

BROAD_HUB = DATA_DIR / "Repurposing_Hub_export.txt"

# Prefer the consequence-aware profile. Use the v3 profile as a fallback.
PROFILE_CANDIDATES = [
    DATA_DIR / "submission_track2_bub1b_consequence_profile.json",
    DATA_DIR / "trinova_track2_v3_final_profile.json",
]


# These weights are explicit heuristic parameters, not empirically calibrated
# estimates of treatment response.
AXIS_WEIGHTS = {
    "MITOTIC_CHECKPOINT": 1.00,
    "CHROMOSOME_SEGREGATION": 0.90,
    "MICROTUBULE_MITOSIS": 0.85,
    "CELL_CYCLE": 0.60,
    "APOPTOSIS": 0.20,
    "DNA_REPLICATION_STRESS": 0.10,
}

DEVELOPMENT_SCORE = {
    "APPROVAL_CONTEXT": 1.00,
    "LAUNCHED_DATASET": 0.95,
    "PHASE_4": 0.90,
    "PHASE_3": 0.80,
    "PHASE_2": 0.65,
    "PHASE_1": 0.45,
    "PRECLINICAL": 0.20,
    "DISCOVERY": 0.10,
    "UNRESOLVED": 0.00,
}


# =============================================================================
# UTILITIES
# =============================================================================

def norm_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).replace("\ufeff", "").strip()


def norm_upper(value: Any) -> str:
    return norm_text(value).upper()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert numeric scalar to float; non-numeric values use default."""
    if isinstance(value, bool):
        return float(value)
    try:
        if value is None or pd.isna(value):
            return default
        if isinstance(value, dict):
            for key in ("score", "value", "weight", "support", "normalized_score"):
                if key in value:
                    return safe_float(value[key], default)
            return default
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError, OverflowError):
        return default


def clean_colname(column: Any) -> str:
    text = norm_text(column).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def first_existing(
    df: pd.DataFrame,
    candidates: list[str],
    default: str = "",
) -> pd.Series:
    for candidate in candidates:
        if candidate in df.columns:
            return df[candidate]
    return pd.Series([default] * len(df), index=df.index, dtype=object)


def minmax(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if numeric.empty:
        return pd.Series(index=numeric.index, dtype=float)

    minimum = float(numeric.min())
    maximum = float(numeric.max())

    if abs(maximum - minimum) < 1e-12:
        return pd.Series([0.0] * len(numeric), index=numeric.index, dtype=float)

    return (numeric - minimum) / (maximum - minimum)


def normalize_phase(phase: Any) -> str:
    """Normalize common Broad phase/status spellings to stable categories."""
    p = norm_upper(phase)
    p = p.replace("-", " ").replace("/", " ")
    p = re.sub(r"[\s]+", " ", p).strip()

    if not p:
        return "UNRESOLVED"

    if "LAUNCHED" in p:
        return "LAUNCHED_DATASET"
    if "APPROVED" in p or "FDA APPROVAL" in p:
        return "APPROVAL_CONTEXT"

    if re.search(r"\b(PHASE\s*4|PHASE IV|PHASE4|PHASE_4)\b", p):
        return "PHASE_4"
    if re.search(r"\b(PHASE\s*3|PHASE III|PHASE3|PHASE_3)\b", p):
        return "PHASE_3"
    if re.search(r"\b(PHASE\s*2|PHASE II|PHASE2|PHASE_2)\b", p):
        return "PHASE_2"
    if re.search(r"\b(PHASE\s*1|PHASE I|PHASE1|PHASE_1)\b", p):
        return "PHASE_1"
    if "PRECLINICAL" in p or "PRE CLINICAL" in p:
        return "PRECLINICAL"
    if "DISCOVERY" in p:
        return "DISCOVERY"

    return "UNRESOLVED"


def get_molecular_axes(
    molecular_profile: dict[str, Any],
) -> dict[str, float]:
    raw_axes = molecular_profile.get("mechanistic_axes", {})
    if not isinstance(raw_axes, dict):
        return {}
    return {
        str(axis): safe_float(value, 0.0)
        for axis, value in raw_axes.items()
    }


# =============================================================================
# PROFILE DISCOVERY AND VALIDATION
# =============================================================================

def profile_quality(data: Any) -> tuple[int, str]:
    """
    Return a conservative schema score and reason.
    Does not treat a high heuristic score as biological validation.
    """
    if not isinstance(data, dict):
        return 0, "root_not_object"

    molecular = data.get("molecular_profile")
    if not isinstance(molecular, dict):
        return 0, "missing_molecular_profile_object"

    gene = norm_upper(
        molecular.get(
            "gene_symbol",
            molecular.get("gene", data.get("gene", "")),
        )
    )

    if gene and gene != "BUB1B":
        return 0, f"unexpected_gene:{gene}"

    functional = molecular.get("functional_variants", [])
    axes = molecular.get("mechanistic_axes", {})

    functional_ok = isinstance(functional, list)
    axes_ok = isinstance(axes, dict)

    score = 10

    if gene == "BUB1B":
        score += 20

    if functional_ok:
        score += 10
        if functional:
            score += 15

    if axes_ok:
        score += 10
        if axes:
            score += 15

    if not functional_ok:
        return score, "functional_variants_not_list"

    if not axes_ok:
        return score, "mechanistic_axes_not_object"

    return score, "schema_compatible"


def load_profile() -> tuple[dict[str, Any], Path]:
    print("\n[1] Buscando perfil molecular BUB1B...")

    checked: list[str] = []
    candidates: list[tuple[int, Path, dict[str, Any], str]] = []

    # Check explicit paths first and preserve their priority when quality ties.
    for path in PROFILE_CANDIDATES:
        checked.append(str(path))

        if not path.exists():
            continue

        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                data = json.load(handle)

            score, reason = profile_quality(data)

            if score > 0 and reason == "schema_compatible":
                candidates.append(
                    (
                        score + max(0, 10 - len(candidates)),
                        path,
                        data,
                        reason,
                    )
                )
            else:
                print(f"  [WARN] Perfil no compatible: {path} ({reason})")

        except Exception as exc:
            print(f"  [WARN] No se pudo leer {path}: {exc}")

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        score, path, data, _ = candidates[0]

        print(f"  Perfil seleccionado: {path}")
        print(f"  Puntaje interno de compatibilidad de esquema: {score}")

        return data, path

    print("  No se encontró un perfil compatible en las rutas principales.")
    print(f"  Buscando JSON adicionales en: {TRACK2_ROOT}")

    if TRACK2_ROOT.exists():
        for path in TRACK2_ROOT.rglob("*.json"):
            if path in PROFILE_CANDIDATES:
                continue

            checked.append(str(path))

            try:
                with path.open("r", encoding="utf-8-sig") as handle:
                    data = json.load(handle)

                score, reason = profile_quality(data)

                if score > 0 and reason == "schema_compatible":
                    candidates.append((score, path, data, reason))

            except Exception:
                continue

    if candidates:
        candidates.sort(
            key=lambda item: (
                -item[0],
                len(str(item[1])),
                str(item[1]).lower(),
            )
        )

        score, path, data, _ = candidates[0]

        print(f"  Perfil seleccionado automáticamente: {path}")
        print(f"  Puntaje interno de compatibilidad de esquema: {score}")

        return data, path

    raise FileNotFoundError(
        "No fue posible localizar un perfil molecular BUB1B compatible.\n"
        "Verifique que el JSON contenga un objeto 'molecular_profile', "
        "una lista 'functional_variants' y un objeto 'mechanistic_axes'.\n"
        "Rutas revisadas:\n"
        + "\n".join(f"  - {path}" for path in checked)
    )


profile, PROFILE_USED = load_profile()
molecular = profile["molecular_profile"]

gene = norm_text(
    molecular.get(
        "gene_symbol",
        molecular.get("gene", profile.get("gene", "BUB1B")),
    )
) or "BUB1B"

lof_hypothesis = bool(molecular.get("loF_hypothesis", False))

functional_variants_raw = molecular.get("functional_variants", [])
functional_variants = (
    functional_variants_raw
    if isinstance(functional_variants_raw, list)
    else []
)

axes = get_molecular_axes(molecular)

phase_status = (
    norm_text(molecular.get("phase", "INDETERMINATE"))
    or "INDETERMINATE"
)

phase_supported = bool(molecular.get("phase_supported", False))

print(f"\n  Gen: {gene}")
print(f"  Hipótesis LoF declarada en el perfil: {lof_hypothesis}")
print(f"  Variantes funcionales registradas: {len(functional_variants)}")
print(f"  Fase: {phase_status}")
print(f"  Fase respaldada: {phase_supported}")


# =============================================================================
# CONSEQUENCE SUMMARY
# =============================================================================

stop_gained = missense = frameshift = splice = 0

for variant in functional_variants:
    if not isinstance(variant, dict):
        continue

    consequence = norm_upper(variant.get("consequence", ""))

    if "STOP_GAINED" in consequence:
        stop_gained += 1

    if "MISSENSE" in consequence:
        missense += 1

    if "FRAMESHIFT" in consequence:
        frameshift += 1

    if "SPLICE" in consequence:
        splice += 1


print("\n[2] Resumen de consecuencias moleculares")
print(f"  STOP_GAINED : {stop_gained}")
print(f"  MISSENSE    : {missense}")
print(f"  FRAMESHIFT  : {frameshift}")
print(f"  SPLICE      : {splice}")

print("\n  Ejes mecanísticos:")

if axes:
    for axis, value in axes.items():
        print(f"    {axis:<30} {value:8.3f}")
else:
    print("    [WARN] No se encontraron ejes mecanísticos numéricos.")


# This index is a transparent heuristic, not a pathogenicity score.
molecular_support = 0.0

if lof_hypothesis:
    molecular_support += 1.0

if stop_gained > 0:
    molecular_support += 1.0

if frameshift > 0:
    molecular_support += 0.8

if splice > 0:
    molecular_support += 0.8

if missense > 0:
    molecular_support += 0.25

molecular_support = min(molecular_support / 2.0, 1.0)

phase_uncertainty_factor = 1.0 if phase_supported else 0.90

print(f"\n  Índice heurístico de soporte molecular: {molecular_support:.3f}")

if not phase_supported:
    print(
        "  [WARN] Fase no respaldada: "
        "no se infiere heterocigosis compuesta en trans."
    )


# =============================================================================
# MECHANISM CLUSTERS
# =============================================================================

MECHANISM_CLUSTERS = {
    "MPS1_TTK_SAC": {
        "label": "MPS1/TTK spindle assembly checkpoint",
        "axis": "MITOTIC_CHECKPOINT",
        "target_terms": [
            "MPS1/TTK",
            "SPINDLE ASSEMBLY CHECKPOINT",
            "MPS1",
            "TTK",
            "SAC",
        ],
        "moa_terms": [
            "MPS1 INHIBITOR",
            "TTK INHIBITOR",
            "MPS1/TTK INHIBITOR",
            "SPINDLE CHECKPOINT INHIBITOR",
        ],
    },
    "AURORA_PLK_MITOSIS": {
        "label": "Aurora/PLK mitotic regulation",
        "axis": "MITOTIC_CHECKPOINT",
        "target_terms": [
            "POLO-LIKE KINASE",
            "POLO LIKE KINASE",
            "AURORA A",
            "AURORA B",
            "AURKA",
            "AURKB",
            "PLK1",
            "AURORA",
        ],
        "moa_terms": [
            "AURORA KINASE INHIBITOR",
            "AURORA INHIBITOR",
            "PLK1 INHIBITOR",
            "PLK INHIBITOR",
            "MITOTIC KINASE INHIBITOR",
        ],
    },
    "CHROMOSOME_SEGREGATION": {
        "label": "Chromosome segregation / kinetochore",
        "axis": "CHROMOSOME_SEGREGATION",
        "target_terms": [
            "CHROMOSOME SEGREGATION",
            "SPINDLE",
            "KINETOCHORE",
            "CENTROMERE",
            "CENP",
            "KINESIN",
            "KIF",
        ],
        "moa_terms": [
            "CHROMOSOME SEGREGATION",
            "KINETOCHORE",
            "SPINDLE INHIBITOR",
            "KINESIN INHIBITOR",
            "KIF INHIBITOR",
        ],
    },
    "MICROTUBULE_MITOSIS": {
        "label": "Microtubule / mitotic spindle",
        "axis": "MICROTUBULE_MITOSIS",
        "target_terms": [
            "BETA-TUBULIN",
            "TUBULIN BETA",
            "TUBULIN ALPHA",
            "MICROTUBULE",
            "TUBULIN",
        ],
        "moa_terms": [
            "MICROTUBULE DESTABILIZER",
            "MICROTUBULE STABILIZER",
            "MICROTUBULE DISRUPTOR",
            "MICROTUBULE INHIBITOR",
            "TUBULIN INHIBITOR",
            "TUBULIN BINDING",
        ],
    },
    "CELL_CYCLE": {
        "label": "Cell-cycle regulation",
        "axis": "CELL_CYCLE",
        "target_terms": [
            "CDK4",
            "CDK6",
            "CDK2",
            "CDK1",
            "CYCLIN",
            "CDK",
            "CELL CYCLE",
        ],
        "moa_terms": [
            "CDK INHIBITOR",
            "CELL CYCLE INHIBITOR",
            "CELL CYCLE ARREST",
        ],
    },
    "APOPTOSIS": {
        "label": "Apoptosis / programmed cell death",
        "axis": "APOPTOSIS",
        "target_terms": [
            "BCL-2",
            "BCL2",
            "CASPASE",
            "APOPTOSIS",
            "BAX",
        ],
        "moa_terms": [
            "APOPTOSIS INDUCER",
            "BCL2 INHIBITOR",
            "CASPASE ACTIVATOR",
            "PRO-APOPTOTIC",
        ],
    },
    "DNA_REPLICATION_STRESS": {
        "label": "DNA replication / replication stress",
        "axis": "DNA_REPLICATION_STRESS",
        "target_terms": [
            "DNA REPLICATION",
            "REPLICATION STRESS",
            "DNA DAMAGE",
            "CHK1",
            "WEE1",
            "ATR",
        ],
        "moa_terms": [
            "DNA DAMAGE RESPONSE",
            "REPLICATION STRESS",
            "ATR INHIBITOR",
            "CHK1 INHIBITOR",
            "WEE1 INHIBITOR",
        ],
    },
}


def contains_term(text: str, term: str) -> bool:
    """Use boundary-aware matching for short symbols to reduce false positives."""
    text = norm_upper(text)
    term = norm_upper(term)

    if not text or not term:
        return False

    if re.fullmatch(r"[A-Z0-9]+", term) and len(term) <= 4:
        return (
            re.search(
                rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])",
                text,
            )
            is not None
        )

    return term in text


def classify_mechanism(target: Any, moa: Any) -> dict[str, str]:
    target_u = norm_upper(target)
    moa_u = norm_upper(moa)

    # Prefer explicit target matches, then mechanism-of-action descriptions.
    for cluster, spec in MECHANISM_CLUSTERS.items():
        for term in spec["target_terms"]:
            if contains_term(target_u, term):
                return {
                    "cluster": cluster,
                    "label": spec["label"],
                    "axis": spec["axis"],
                    "source": "TARGET",
                    "confidence": "RULE_MATCH_HIGH",
                    "matched_term": term,
                }

    for cluster, spec in MECHANISM_CLUSTERS.items():
        for term in spec["moa_terms"]:
            if contains_term(moa_u, term):
                return {
                    "cluster": cluster,
                    "label": spec["label"],
                    "axis": spec["axis"],
                    "source": "MOA",
                    "confidence": "RULE_MATCH_MODERATE",
                    "matched_term": term,
                }

    return {
        "cluster": "UNRESOLVED",
        "label": "Mechanism unresolved",
        "axis": "UNRESOLVED",
        "source": "NONE",
        "confidence": "UNRESOLVED",
        "matched_term": "",
    }


# =============================================================================
# LOAD AND NORMALIZE BROAD REPURPOSING HUB
# =============================================================================

print("\n[3] Cargando Broad Repurposing Hub...")

if not BROAD_HUB.exists():
    raise FileNotFoundError(
        f"No existe el archivo Broad Repurposing Hub:\n{BROAD_HUB}\n"
        "Verifique que Repurposing_Hub_export.txt esté dentro de la carpeta data."
    )

broad = pd.read_csv(
    BROAD_HUB,
    sep="\t",
    dtype=str,
    low_memory=False,
    encoding="utf-8-sig",
)

broad.columns = [clean_colname(column) for column in broad.columns]

if len(set(broad.columns)) != len(broad.columns):
    duplicates = sorted({
        column
        for column in broad.columns
        if broad.columns.tolist().count(column) > 1
    })
    raise ValueError(
        f"Hay encabezados duplicados después de normalizar: {duplicates}"
    )

print(f"  Registros originales: {len(broad):,}")
print("  Columnas: " + ", ".join(broad.columns))

broad["name_norm"] = first_existing(
    broad,
    ["name", "drug", "compound", "compound_name"],
    "",
).map(norm_text)

broad["target_norm"] = first_existing(
    broad,
    ["target", "targets", "gene_target"],
    "",
).map(norm_text)

broad["moa_norm"] = first_existing(
    broad,
    ["moa", "mechanism_of_action", "mechanism"],
    "",
).map(norm_text)

broad["phase_norm"] = first_existing(
    broad,
    ["phase", "clinical_phase", "development_phase"],
    "",
).map(norm_text)

broad = broad[broad["name_norm"] != ""].copy()

broad = broad.drop_duplicates(
    subset=["name_norm", "target_norm", "moa_norm"]
).reset_index(drop=True)

print(f"  Registros válidos/deduplicados: {len(broad):,}")


# Apply classification with a stable schema even for an empty input.
CLASSIFICATION_COLUMNS = [
    "cluster",
    "label",
    "axis",
    "source",
    "confidence",
    "matched_term",
]

if broad.empty:
    for column in CLASSIFICATION_COLUMNS:
        broad[column] = pd.Series(dtype=object)
else:
    classified = broad.apply(
        lambda row: classify_mechanism(
            row["target_norm"],
            row["moa_norm"],
        ),
        axis=1,
        result_type="expand",
    )

    for column in CLASSIFICATION_COLUMNS:
        if column not in classified.columns:
            classified[column] = ""

    broad = pd.concat(
        [broad, classified[CLASSIFICATION_COLUMNS]],
        axis=1,
    )

broad["development_context"] = broad["phase_norm"].map(normalize_phase)

broad["development_score"] = (
    broad["development_context"]
    .map(DEVELOPMENT_SCORE)
    .fillna(0.0)
    .astype(float)
)


# =============================================================================
# MOLECULAR RELEVANCE AND PRIORITY
# =============================================================================

def molecular_relevance(row: pd.Series) -> float:
    if row.get("cluster", "UNRESOLVED") == "UNRESOLVED":
        return 0.0

    axis = norm_text(row.get("axis", "UNRESOLVED"))

    axis_value = safe_float(axes.get(axis, 0.0))
    axis_weight = AXIS_WEIGHTS.get(axis, 0.0)

    source_score = {
        "TARGET": 1.00,
        "MOA": 0.82,
        "NONE": 0.00,
    }.get(norm_text(row.get("source", "NONE")), 0.0)

    rule_score = {
        "RULE_MATCH_HIGH": 1.00,
        "RULE_MATCH_MODERATE": 0.85,
        "UNRESOLVED": 0.00,
    }.get(norm_text(row.get("confidence", "UNRESOLVED")), 0.0)

    consequence_factor = 0.65 + 0.35 * molecular_support

    return (
        axis_value
        * axis_weight
        * source_score
        * rule_score
        * consequence_factor
        * phase_uncertainty_factor
    )


if broad.empty:
    broad["molecular_relevance"] = pd.Series(dtype=float)
else:
    broad["molecular_relevance"] = broad.apply(
        molecular_relevance,
        axis=1,
    )

broad["molecular_relevance_norm"] = minmax(
    broad["molecular_relevance"]
)

# Min-max normalization is relative to the current Broad catalogue,
# not an absolute biological or clinical evidence scale.
broad["priority_score"] = (
    0.70 * broad["molecular_relevance_norm"]
    + 0.30 * broad["development_score"]
)

broad.loc[
    broad["cluster"] == "UNRESOLVED",
    "priority_score",
] *= 0.25


def priority_class(row: pd.Series) -> str:
    molecular_score = safe_float(
        row.get("molecular_relevance_norm", 0.0)
    )

    development_score = safe_float(
        row.get("development_score", 0.0)
    )

    cluster = norm_text(row.get("cluster", "UNRESOLVED"))

    if cluster == "UNRESOLVED":
        return "LOW_MECHANISTIC_SUPPORT"

    if molecular_score >= 0.75 and development_score >= 0.70:
        return "HIGH_REPURPOSING_RELEVANCE"

    if molecular_score >= 0.75:
        return "HIGH_MECHANISTIC_RELEVANCE"

    if molecular_score >= 0.45 and development_score >= 0.60:
        return "MODERATE_REPURPOSING_RELEVANCE"

    if molecular_score >= 0.45:
        return "MODERATE_MECHANISTIC_RELEVANCE"

    return "LOWER_PRIORITY"


broad["priority_class"] = (
    broad.apply(priority_class, axis=1)
    if not broad.empty
    else pd.Series(dtype=object)
)


# =============================================================================
# MECHANISTIC CLUSTER SUMMARY
# =============================================================================

resolved = (
    broad[broad["cluster"] != "UNRESOLVED"].copy()
    if not broad.empty
    else broad.copy()
)

CLUSTER_COLUMNS = [
    "cluster",
    "label",
    "axis",
    "compounds",
    "max_molecular_relevance",
    "mean_molecular_relevance",
    "max_development_score",
    "mean_development_score",
    "cluster_score",
    "mechanistic_rank",
]

if resolved.empty:
    cluster_df = pd.DataFrame(columns=CLUSTER_COLUMNS)
else:
    cluster_df = (
        resolved.groupby(
            ["cluster", "label", "axis"],
            dropna=False,
        )
        .agg(
            compounds=("name_norm", "nunique"),
            max_molecular_relevance=("molecular_relevance", "max"),
            mean_molecular_relevance=("molecular_relevance", "mean"),
            max_development_score=("development_score", "max"),
            mean_development_score=("development_score", "mean"),
        )
        .reset_index()
    )

    cluster_df["cluster_score"] = (
        0.70 * minmax(cluster_df["max_molecular_relevance"])
        + 0.30 * cluster_df["max_development_score"]
    )

    cluster_df = cluster_df.sort_values(
        ["cluster_score", "max_molecular_relevance"],
        ascending=False,
    ).reset_index(drop=True)

    cluster_df["mechanistic_rank"] = range(
        1,
        len(cluster_df) + 1,
    )


broad["compound_rank_within_cluster"] = pd.Series(
    0,
    index=broad.index,
    dtype=int,
)

if not broad.empty:
    mask = broad["cluster"] != "UNRESOLVED"

    if mask.any():
        ranks = (
            broad.loc[mask]
            .groupby("cluster")["priority_score"]
            .rank(method="first", ascending=False)
            .astype(int)
        )

        broad.loc[
            mask,
            "compound_rank_within_cluster",
        ] = ranks


# =============================================================================
# FINAL COLUMNS
# =============================================================================

FINAL_COLUMNS = [
    "name_norm",
    "target_norm",
    "moa_norm",
    "phase_norm",
    "development_context",
    "development_score",
    "cluster",
    "label",
    "axis",
    "source",
    "confidence",
    "matched_term",
    "molecular_relevance",
    "molecular_relevance_norm",
    "priority_score",
    "priority_class",
    "compound_rank_within_cluster",
]


def empty_like_broad() -> pd.DataFrame:
    return broad.iloc[0:0].copy()


# =============================================================================
# REPURPOSING SHORTLIST WITH CLUSTER DIVERSIFICATION
# =============================================================================

repurposing = broad[
    broad["cluster"] != "UNRESOLVED"
].copy()

repurposing = repurposing[
    repurposing["development_context"].isin(
        ["APPROVAL_CONTEXT", "LAUNCHED_DATASET", "PHASE_4"]
    )
].copy()

repurposing = repurposing[
    repurposing["molecular_relevance_norm"] >= 0.15
].copy()

if not repurposing.empty:
    repurposing = repurposing.sort_values(
        [
            "priority_score",
            "molecular_relevance_norm",
            "development_score",
        ],
        ascending=False,
    ).reset_index(drop=True)

selected_rows: list[dict[str, Any]] = []
cluster_counts: dict[str, int] = {}

for _, row in repurposing.iterrows():
    cluster = row["cluster"]

    if cluster_counts.get(cluster, 0) >= 3:
        continue

    selected_rows.append(row.to_dict())

    cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

    if len(selected_rows) >= 12:
        break

repurposing_shortlist = (
    pd.DataFrame(selected_rows)
    if selected_rows
    else empty_like_broad()
)


# =============================================================================
# DISCOVERY SET WITH CLUSTER DIVERSIFICATION
# =============================================================================

discovery = broad[
    broad["cluster"] != "UNRESOLVED"
].copy()

discovery = discovery[
    discovery["development_context"].isin(
        [
            "PRECLINICAL",
            "DISCOVERY",
            "PHASE_1",
            "PHASE_2",
            "PHASE_3",
        ]
    )
].copy()

discovery = discovery[
    discovery["molecular_relevance_norm"] >= 0.20
].copy()

if not discovery.empty:
    discovery = discovery.sort_values(
        [
            "molecular_relevance_norm",
            "priority_score",
        ],
        ascending=False,
    ).reset_index(drop=True)

selected_discovery: list[dict[str, Any]] = []
discovery_cluster_counts: dict[str, int] = {}

for _, row in discovery.iterrows():
    cluster = row["cluster"]

    if discovery_cluster_counts.get(cluster, 0) >= 4:
        continue

    selected_discovery.append(row.to_dict())

    discovery_cluster_counts[cluster] = (
        discovery_cluster_counts.get(cluster, 0) + 1
    )

    if len(selected_discovery) >= 20:
        break

discovery_set = (
    pd.DataFrame(selected_discovery)
    if selected_discovery
    else empty_like_broad()
)


# =============================================================================
# COMPLEMENTARY MECHANISTIC-COVERAGE HYPOTHESES
# =============================================================================

combination_candidates: list[dict[str, Any]] = []

ordered_clusters = (
    cluster_df["cluster"].tolist()
    if not cluster_df.empty
    else []
)

for i, cluster_a in enumerate(ordered_clusters):
    spec_a = MECHANISM_CLUSTERS.get(cluster_a)

    if not spec_a:
        continue

    for cluster_b in ordered_clusters[i + 1:]:
        spec_b = MECHANISM_CLUSTERS.get(cluster_b)

        if not spec_b:
            continue

        axis_a = spec_a["axis"]
        axis_b = spec_b["axis"]

        if axis_a == axis_b:
            continue

        axis_a_value = safe_float(axes.get(axis_a, 0.0))
        axis_b_value = safe_float(axes.get(axis_b, 0.0))

        coverage = (
            axis_a_value * AXIS_WEIGHTS.get(axis_a, 0.0)
            + axis_b_value * AXIS_WEIGHTS.get(axis_b, 0.0)
        )

        combination_candidates.append({
            "cluster_a": cluster_a,
            "cluster_b": cluster_b,
            "axis_a": axis_a,
            "axis_b": axis_b,
            "mechanistic_coverage": coverage,
            "hypothesis_type": "COMPLEMENTARY_MECHANISTIC_COVERAGE",
            "interpretation": (
                "Mechanistic coverage hypothesis for experimental evaluation. "
                "This is not a drug-pair recommendation and does not establish "
                "synergy, efficacy, safety, or clinical suitability."
            ),
        })

if combination_candidates:
    combination_df = (
        pd.DataFrame(combination_candidates)
        .sort_values("mechanistic_coverage", ascending=False)
        .head(20)
        .reset_index(drop=True)
    )
else:
    combination_df = pd.DataFrame(
        columns=[
            "cluster_a",
            "cluster_b",
            "axis_a",
            "axis_b",
            "mechanistic_coverage",
            "hypothesis_type",
            "interpretation",
        ]
    )


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def ensure_final_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    for column in FINAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.Series(
                index=result.index,
                dtype=object,
            )

    return result[FINAL_COLUMNS]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


# =============================================================================
# SAVE FULL RANKING
# =============================================================================

full_ranked = ensure_final_columns(broad)

if not full_ranked.empty:
    full_ranked = full_ranked.sort_values(
        "priority_score",
        ascending=False,
    ).reset_index(drop=True)

full_ranked.insert(
    0,
    "rank",
    range(1, len(full_ranked) + 1),
)

full_path = OUTDIR / "trinova_track2_final_full_ranked.csv"
cluster_path = OUTDIR / "trinova_track2_final_mechanistic_clusters.csv"
repurposing_path = OUTDIR / "trinova_track2_final_repurposing_shortlist.csv"
discovery_path = OUTDIR / "trinova_track2_final_discovery_set.csv"
combination_path = OUTDIR / "trinova_track2_final_combination_hypotheses.csv"

full_ranked.to_csv(
    full_path,
    index=False,
    encoding="utf-8-sig",
)

cluster_df.to_csv(
    cluster_path,
    index=False,
    encoding="utf-8-sig",
)

ensure_final_columns(repurposing_shortlist).to_csv(
    repurposing_path,
    index=False,
    encoding="utf-8-sig",
)

ensure_final_columns(discovery_set).to_csv(
    discovery_path,
    index=False,
    encoding="utf-8-sig",
)

combination_df.to_csv(
    combination_path,
    index=False,
    encoding="utf-8-sig",
)


# =============================================================================
# FINAL PROFILE JSON
# =============================================================================

cluster_profile_columns = [
    "mechanistic_rank",
    "cluster",
    "label",
    "axis",
    "compounds",
    "max_molecular_relevance",
    "max_development_score",
    "cluster_score",
]

cluster_records = (
    cluster_df[cluster_profile_columns].to_dict(orient="records")
    if not cluster_df.empty
    else []
)


def selected_records(
    frame: pd.DataFrame,
    columns: list[str],
) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    available = [
        column
        for column in columns
        if column in frame.columns
    ]

    return frame[available].to_dict(orient="records")


final_profile = {
    "framework": "TRINOVA.OS",
    "track": "TRACK_2",
    "module": "MOLECULAR_VULNERABILITY_AND_DRUG_REPURPOSING",
    "version": "FINAL_CANDIDATE_1.0",
    "status": "RESEARCH_HYPOTHESIS_GENERATION",
    "profile_source": str(PROFILE_USED),
    "gene": gene,
    "molecular_profile": {
        "loF_hypothesis": lof_hypothesis,
        "functional_variants_count": len(functional_variants),
        "stop_gained_count": stop_gained,
        "missense_count": missense,
        "frameshift_count": frameshift,
        "splice_count": splice,
        "heuristic_molecular_support_index": molecular_support,
        "phase": phase_status,
        "phase_supported": phase_supported,
        "phase_uncertainty_factor": phase_uncertainty_factor,
    },
    "mechanistic_axes": axes,
    "scoring": {
        "priority_score_formula": (
            "0.70 * molecular_relevance_norm + 0.30 * development_score"
        ),
        "molecular_relevance_normalization": (
            "min-max relative to the loaded Broad catalogue"
        ),
        "axis_weights": AXIS_WEIGHTS,
        "development_scores": DEVELOPMENT_SCORE,
        "note": (
            "Weights and thresholds are heuristic and not clinically calibrated."
        ),
    },
    "mechanistic_clusters": cluster_records,
    "repurposing_shortlist": selected_records(
        repurposing_shortlist,
        [
            "name_norm",
            "cluster",
            "axis",
            "molecular_relevance",
            "development_context",
            "priority_score",
            "priority_class",
        ],
    ),
    "discovery_set": selected_records(
        discovery_set,
        [
            "name_norm",
            "cluster",
            "axis",
            "molecular_relevance",
            "development_context",
            "priority_score",
            "priority_class",
        ],
    ),
    "combination_hypotheses": (
        combination_df.to_dict(orient="records")
        if not combination_df.empty
        else []
    ),
    "limitations": [
        "The molecular-support index is a transparent prioritization heuristic, not a pathogenicity score.",
        "A STOP_GAINED annotation alone does not prove clinical causality.",
        "A missense annotation is not assumed pathogenic.",
        "No compound heterozygosity in trans is inferred without adequate phase evidence.",
        "Mechanistic relevance does not establish therapeutic efficacy or patient benefit.",
        "Broad LAUNCHED labels are dataset context, not proof of current regulatory approval.",
        "Min-max molecular relevance is relative to the loaded catalogue and may change with dataset composition.",
        "Rule-match labels describe text matching, not experimentally validated confidence.",
        "Discovery and repurposing candidates are separated by dataset development-context labels, which require source verification.",
        "Complementary-coverage hypotheses do not identify validated drug combinations or establish synergy.",
        "Potential inhibition of mitotic pathways could be ineffective or harmful; experimental evidence and safety must be assessed independently.",
        "All outputs are research hypotheses requiring orthogonal biological, pharmacological, and regulatory validation.",
    ],
}

profile_path = OUTDIR / "trinova_track2_final_profile.json"

write_json(
    profile_path,
    final_profile,
)


# =============================================================================
# HUMAN-READABLE SUMMARY
# =============================================================================

summary_path = OUTDIR / "trinova_track2_final_summary.txt"

with summary_path.open("w", encoding="utf-8") as handle:
    handle.write("TRINOVA.OS — TRACK 2 — FINAL CANDIDATE 1.0\n")
    handle.write("BUB1B → MOLECULAR VULNERABILITY → DRUG REPURPOSING\n")
    handle.write("=" * 84 + "\n\n")

    handle.write(f"Profile source: {PROFILE_USED}\n")
    handle.write(f"Gene: {gene}\n")
    handle.write(f"Declared LoF hypothesis: {lof_hypothesis}\n")
    handle.write(
        f"Functional variants recorded: {len(functional_variants)}\n"
    )

    handle.write(
        f"STOP_GAINED: {stop_gained}\n"
        f"MISSENSE: {missense}\n"
        f"FRAMESHIFT: {frameshift}\n"
        f"SPLICE: {splice}\n"
    )

    handle.write(f"Phase: {phase_status}\n")
    handle.write(f"Phase supported: {phase_supported}\n")
    handle.write(
        f"Heuristic molecular-support index: {molecular_support:.3f}\n"
    )
    handle.write(
        f"Phase uncertainty factor: {phase_uncertainty_factor:.2f}\n\n"
    )

    handle.write("INTERPRETATION LIMIT\n")
    handle.write("-" * 84 + "\n")

    handle.write(
        "Scores prioritize research hypotheses. They do not estimate probability "
        "of clinical benefit, demonstrate drug efficacy, establish causal disease "
        "mechanism, or determine patient suitability.\n\n"
    )

    handle.write(
        "MECHANISTIC CLUSTERS\n"
        + "-" * 84
        + "\n"
    )

    if cluster_df.empty:
        handle.write("No clusters resolved from the loaded catalogue.\n")
    else:
        for _, row in cluster_df.iterrows():
            handle.write(
                f"{int(row['mechanistic_rank']):2d}. "
                f"{row['cluster']} | {row['label']} | "
                f"axis={row['axis']} | "
                f"compounds={int(row['compounds'])} | "
                f"score={safe_float(row['cluster_score']):.4f}\n"
            )

    handle.write(
        "\nREPURPOSING SHORTLIST\n"
        + "-" * 84
        + "\n"
    )

    if repurposing_shortlist.empty:
        handle.write(
            "No candidates passed the current filters. "
            "This is not evidence that no candidate exists.\n"
        )
    else:
        for i, (_, row) in enumerate(
            repurposing_shortlist.iterrows(),
            start=1,
        ):
            handle.write(
                f"{i:2d}. {row['name_norm']} | "
                f"{row['cluster']} | {row['axis']} | "
                f"molecular={safe_float(row['molecular_relevance']):.3f} | "
                f"context={row['development_context']} | "
                f"priority={safe_float(row['priority_score']):.4f}\n"
            )

    handle.write(
        "\nDISCOVERY SET\n"
        + "-" * 84
        + "\n"
    )

    if discovery_set.empty:
        handle.write("No discovery candidates passed the current filters.\n")
    else:
        for i, (_, row) in enumerate(
            discovery_set.iterrows(),
            start=1,
        ):
            handle.write(
                f"{i:2d}. {row['name_norm']} | "
                f"{row['cluster']} | {row['axis']} | "
                f"context={row['development_context']} | "
                f"molecular={safe_float(row['molecular_relevance']):.3f}\n"
            )

    handle.write(
        "\nCOMPLEMENTARY-COVERAGE HYPOTHESES\n"
        + "-" * 84
        + "\n"
    )

    if combination_df.empty:
        handle.write("No complementary axis pairs were generated.\n")
    else:
        for _, row in combination_df.iterrows():
            handle.write(
                f"{row['cluster_a']} + {row['cluster_b']} | "
                f"coverage={safe_float(row['mechanistic_coverage']):.3f} | "
                "not evidence of synergy\n"
            )

    handle.write(
        "\nSCORING\n"
        + "-" * 84
        + "\n"
    )

    handle.write(
        "priority_score = "
        "0.70 * molecular_relevance_norm + 0.30 * development_score\n"
    )
    handle.write(
        "Molecular relevance is min-max normalized within the loaded Broad catalogue.\n"
    )
    handle.write(
        "A rule match is a text-based association, not a validated biological mechanism.\n"
    )


# =============================================================================
# QUALITY CONTROL
# =============================================================================

qc_path = OUTDIR / "trinova_track2_final_qc.txt"

axis_values_all_equal = (
    not broad.empty
    and broad["molecular_relevance"].nunique(dropna=False) <= 1
)

with qc_path.open("w", encoding="utf-8") as handle:
    handle.write("TRINOVA.OS TRACK 2 — FINAL CANDIDATE QC\n")
    handle.write("=" * 84 + "\n")

    handle.write(f"Profile used: {PROFILE_USED}\n")
    handle.write(
        f"Broad records after filtering/deduplication: {len(broad):,}\n"
    )

    resolved_count = (
        int((broad["cluster"] != "UNRESOLVED").sum())
        if not broad.empty
        else 0
    )

    unresolved_count = (
        int((broad["cluster"] == "UNRESOLVED").sum())
        if not broad.empty
        else 0
    )

    handle.write(
        f"Mechanism resolved by text rules: {resolved_count:,}\n"
    )
    handle.write(
        f"Mechanism unresolved: {unresolved_count:,}\n"
    )
    handle.write(
        f"Repurposing shortlist size: {len(repurposing_shortlist)}\n"
    )
    handle.write(
        f"Discovery set size: {len(discovery_set)}\n"
    )
    handle.write(
        f"Mechanistic clusters: {len(cluster_df)}\n"
    )
    handle.write(
        f"Complementary-coverage hypotheses: {len(combination_df)}\n"
    )
    handle.write(
        "All molecular relevance values identical/undiscriminating: "
        f"{axis_values_all_equal}\n"
    )

    handle.write("\nMechanism counts:\n")

    if broad.empty:
        handle.write("  No catalogue records available.\n")
    else:
        for cluster, count in broad["cluster"].value_counts().items():
            handle.write(f"  {cluster}: {count}\n")

    handle.write("\nDevelopment contexts:\n")

    if broad.empty:
        handle.write("  No catalogue records available.\n")
    else:
        for context, count in broad["development_context"].value_counts().items():
            handle.write(f"  {context}: {count}\n")

    handle.write("\nQC cautions:\n")
    handle.write(
        "- Text matching may miss synonyms and may produce ambiguous matches.\n"
    )
    handle.write(
        "- Rule-match confidence is not experimental evidence.\n"
    )
    handle.write(
        "- Development context is inherited from the input catalogue "
        "and was not independently verified.\n"
    )
    handle.write(
        "- Min-max scores depend on catalogue composition.\n"
    )
    handle.write(
        "- No efficacy, causality, safety, or synergy claims are generated.\n"
    )
    handle.write(
        "- No current approval is inferred from Broad 'Launched' labels.\n"
    )


# =============================================================================
# CONSOLE SUMMARY
# =============================================================================

print("\n" + "=" * 84)
print("TRINOVA.OS — TRACK 2 — FINAL CANDIDATE")
print("=" * 84)

print(f"Profile used: {PROFILE_USED}")
print(f"Broad compounds after deduplication: {len(broad):,}")
print(f"Mechanism resolved by rules: {resolved_count:,}")
print(f"Mechanism unresolved: {unresolved_count:,}")

print("\nTOP MECHANISTIC CLUSTERS")
print("-" * 84)

if cluster_df.empty:
    print("No mechanistic clusters.")
else:
    for _, row in cluster_df.head(10).iterrows():
        print(
            f"{int(row['mechanistic_rank']):2d}. "
            f"{row['cluster']:<28} "
            f"axis={row['axis']:<25} "
            f"compounds={int(row['compounds']):4d} "
            f"score={safe_float(row['cluster_score']):.4f}"
        )

print("\nREPURPOSING SHORTLIST")
print("-" * 84)

if repurposing_shortlist.empty:
    print("No candidates passed the current filters.")
else:
    for i, (_, row) in enumerate(
        repurposing_shortlist.iterrows(),
        start=1,
    ):
        print(
            f"{i:2d}. {row['name_norm']:<24} | "
            f"{row['cluster']:<24} | "
            f"molecular={safe_float(row['molecular_relevance']):.3f} | "
            f"context={row['development_context']:<18} | "
            f"priority={safe_float(row['priority_score']):.4f}"
        )

print("\nDISCOVERY SET")
print("-" * 84)

if discovery_set.empty:
    print("No discovery candidates passed the current filters.")
else:
    for i, (_, row) in enumerate(
        discovery_set.head(15).iterrows(),
        start=1,
    ):
        print(
            f"{i:2d}. {row['name_norm']:<24} | "
            f"{row['cluster']:<24} | "
            f"context={row['development_context']:<14} | "
            f"molecular={safe_float(row['molecular_relevance']):.3f}"
        )

print("\nOUTPUT FILES")
print("-" * 84)

for path in [
    full_path,
    cluster_path,
    repurposing_path,
    discovery_path,
    combination_path,
    profile_path,
    summary_path,
    qc_path,
]:
    print(path)

print("\nCOMPLETED")
print(
    "Interpret outputs as research hypotheses, "
    "not evidence of clinical efficacy."
)
print(
    "Review QC warnings and validate candidate identity, biology, "
    "pharmacology, and regulatory status independently."
)
