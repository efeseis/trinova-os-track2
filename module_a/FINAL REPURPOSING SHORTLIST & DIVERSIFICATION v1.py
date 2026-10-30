
# -*- coding: utf-8 -*-

"""
==================================================================================
TRINOVA.OS — TRACK 2
FINAL REPURPOSING SHORTLIST & DIVERSIFICATION — v1
==================================================================================

OBJETIVO
--------
Construir la capa final de Drug Repurposing a partir de:

    BUB1B functional annotation
            ↓
    STOP_GAINED / MISSENSE
            ↓
    BUB1B loss-of-function hypothesis
            ↓
    mitotic checkpoint / chromosome segregation / mitosis
            ↓
    pharmacologically perturbable mechanisms
            ↓
    repurposing shortlist + mechanistic discovery set

IMPORTANTE
----------
Este módulo genera hipótesis de investigación.

NO afirma:
    - causalidad clínica
    - eficacia terapéutica
    - beneficio en pacientes
    - aprobación regulatoria actual
    - seguridad pediátrica
    - sinergia entre fármacos

"LAUNCHED" se conserva como estado del dataset Broad.
NO se convierte automáticamente en "FDA approved".

==================================================================================
"""

import os
import json
import math
import re
from itertools import combinations

import pandas as pd


# ==============================================================================
# CONFIGURACIÓN DE RUTAS
# ==============================================================================

# El script está dentro de module_a.
# REPO_DIR apunta a la raíz del repositorio.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)

# Todas las entradas se leen desde la carpeta data/

DATA_DIR = os.path.join(
    REPO_DIR,
    "data"
)

BUB1B_FUNCTIONAL_TSV = os.path.join(
    DATA_DIR,
    "bub1b_funcional_todas.tsv"
)

BUB1B_AUDIT_TSV = os.path.join(
    DATA_DIR,
    "bub1b_track1_audit.tsv"
)

CHR15_TSV = os.path.join(
    DATA_DIR,
    "chr15_barrido_trinova.tsv"
)

REPURPOSING_HUB = os.path.join(
    DATA_DIR,
    "Repurposing_Hub_export.txt"
)

CONSEQUENCE_QC = os.path.join(
    DATA_DIR,
    "submission_track2_qc.txt"
)

CONSEQUENCE_SUMMARY = os.path.join(
    DATA_DIR,
    "submission_track2_consequence_summary.txt"
)

CONSEQUENCE_RANKED = os.path.join(
    DATA_DIR,
    "submission_track2_drugs_consequence_aware_ranked.csv"
)

CONSEQUENCE_TOP20 = os.path.join(
    DATA_DIR,
    "submission_track2_drugs_consequence_aware_top20.csv"
)

CONSEQUENCE_TOP50 = os.path.join(
    DATA_DIR,
    "submission_track2_drugs_consequence_aware_top50.csv"
)

BUB1B_PROFILE_JSON = os.path.join(
    DATA_DIR,
    "submission_track2_bub1b_consequence_profile.json"
)


# ==============================================================================
# OUTPUT
# ==============================================================================

# Todos los resultados se guardan en output_final/ en la raíz del repositorio.

OUTPUT_DIR = os.path.join(
    REPO_DIR,
    "output_final"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

FINAL_RANKED = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_final_ranked.csv"
)

REPURPOSING_SHORTLIST = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_repurposing_shortlist.csv"
)

DISCOVERY_SET = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_mechanistic_discovery_set.csv"
)

COMBINATION_HYPOTHESES = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_combination_hypotheses.csv"
)

FINAL_PROFILE = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_final_profile.json"
)

FINAL_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_final_summary.txt"
)

FINAL_QC = os.path.join(
    OUTPUT_DIR,
    "trinova_track2_final_qc.txt"
)


# ==============================================================================
# UTILIDADES
# ==============================================================================

def print_header(title):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def normalize_text(value):
    if value is None:
        return ""

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_lower(value):
    return normalize_text(value).lower()


def normalize_upper(value):
    return normalize_text(value).upper()


def safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default

        text = str(value).strip()

        if text == "":
            return default

        return float(text)

    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or pd.isna(value):
            return default

        return int(float(value))

    except Exception:
        return default


def first_existing_column(df, candidates):

    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:

        key = candidate.strip().lower()

        if key in normalized:
            return normalized[key]

    return None


def contains_any(text, terms):

    text = normalize_lower(text)

    return any(term.lower() in text for term in terms)


def join_text(*values):

    parts = []

    for value in values:

        text = normalize_text(value)

        if text:
            parts.append(text)

    return " | ".join(parts)


# ==============================================================================
# VERIFICACIÓN DE INPUTS
# ==============================================================================

def verify_paths():

    print_header("TRINOVA.OS — VERIFICACIÓN DE INPUTS")

    print(f"[INFO] Repositorio: {REPO_DIR}")
    print(f"[INFO] Carpeta de datos: {DATA_DIR}")
    print(f"[INFO] Carpeta de resultados: {OUTPUT_DIR}")
    print()

    paths = {
        "BUB1B functional TSV": BUB1B_FUNCTIONAL_TSV,
        "BUB1B audit TSV": BUB1B_AUDIT_TSV,
        "Chr15 TSV": CHR15_TSV,
        "Repurposing Hub": REPURPOSING_HUB,
        "Consequence QC": CONSEQUENCE_QC,
        "Consequence summary": CONSEQUENCE_SUMMARY,
        "Consequence-aware ranked": CONSEQUENCE_RANKED,
        "Consequence-aware top20": CONSEQUENCE_TOP20,
        "Consequence-aware top50": CONSEQUENCE_TOP50,
        "BUB1B consequence profile": BUB1B_PROFILE_JSON,
    }

    found = 0

    for label, path in paths.items():

        if os.path.exists(path):

            print(f"[OK]      {label}")
            found += 1

        else:

            print(f"[MISSING] {label}")
            print(f"          {path}")

    print()
    print(f"[+] Encontrados: {found}/{len(paths)}")

    if found != len(paths):

        raise FileNotFoundError(
            "Faltan uno o más archivos de entrada. "
            "Verifica que todos estén dentro de la carpeta data."
        )

    print("[OK] Todas las rutas de entrada son válidas.")


# ==============================================================================
# CARGA DEL PERFIL BUB1B
# ==============================================================================

def load_bub1b_profile():

    print()
    print("[2/8] Cargando perfil molecular BUB1B...")

    with open(
        BUB1B_PROFILE_JSON,
        "r",
        encoding="utf-8"
    ) as f:

        profile = json.load(f)

    molecular = profile.get(
        "molecular_profile",
        {}
    )

    if not isinstance(molecular, dict):

        molecular = {}

    functional_variants = molecular.get(
        "functional_variants",
        []
    )

    if not isinstance(functional_variants, list):

        functional_variants = []

    stop_gained = []
    missense = []
    frameshift = []
    splice = []

    for variant in functional_variants:

        if not isinstance(variant, dict):
            continue

        consequence = normalize_upper(
            variant.get("consequence", "")
        )

        if consequence == "STOP_GAINED":

            stop_gained.append(variant)

        elif consequence == "MISSENSE":

            missense.append(variant)

        elif "FRAMESHIFT" in consequence:

            frameshift.append(variant)

        elif "SPLICE" in consequence:

            splice.append(variant)

    lof_hypothesis = bool(
        molecular.get(
            "loF_hypothesis",
            False
        )
    )

    mechanistic_axes = molecular.get(
        "mechanistic_axes",
        {}
    )

    if not isinstance(mechanistic_axes, dict):

        mechanistic_axes = {}

    axes = {
        str(key): safe_float(value)
        for key, value in mechanistic_axes.items()
    }

    phase = normalize_text(
        molecular.get(
            "phase",
            "INDETERMINATE"
        )
    )

    phase_supported = bool(
        molecular.get(
            "phase_supported",
            False
        )
    )

    print(
        f"[+] STOP_GAINED: {len(stop_gained)}"
    )

    print(
        f"[+] MISSENSE: {len(missense)}"
    )

    print(
        f"[+] FRAMESHIFT: {len(frameshift)}"
    )

    print(
        f"[+] SPLICE: {len(splice)}"
    )

    print(
        f"[+] LoF hypothesis: {lof_hypothesis}"
    )

    print(
        f"[+] Functional variants: {len(functional_variants)}"
    )

    print(
        f"[+] Phase: {phase}"
    )

    print(
        f"[+] Phase supported: {phase_supported}"
    )

    print()
    print("[+] Ejes mecanísticos:")

    for axis, value in sorted(
        axes.items(),
        key=lambda x: x[1],
        reverse=True
    ):

        print(
            f"    - {axis}: {value:.3f}"
        )

    return {
        "raw_profile": profile,
        "molecular": molecular,
        "functional_variants": functional_variants,
        "stop_gained": stop_gained,
        "missense": missense,
        "frameshift": frameshift,
        "splice": splice,
        "lof_hypothesis": lof_hypothesis,
        "axes": axes,
        "phase": phase,
        "phase_supported": phase_supported,
    }


# ==============================================================================
# CARGA CONSEQUENCE-AWARE RANKING
# ==============================================================================

def load_consequence_ranked():

    print()
    print("[3/8] Cargando ranking consequence-aware...")

    df = pd.read_csv(
        CONSEQUENCE_RANKED,
        sep=",",
        encoding="utf-8-sig",
        low_memory=False
    )

    print()
    print("[+] Columnas consequence-aware:")

    for col in df.columns:

        print(f"    - {col}")

    print()

    print(
        f"[+] Candidatos cargados: {len(df)}"
    )

    return df


# ==============================================================================
# NORMALIZACIÓN DEL RANKING
# ==============================================================================

def normalize_ranking_columns(df):

    rename_map = {}

    aliases = {

        "compound_id": [
            "compound_id",
            "compound",
            "id"
        ],

        "name": [
            "name",
            "Name",
            "drug",
            "Drug"
        ],

        "moa": [
            "moa",
            "MOA"
        ],

        "target": [
            "target",
            "Target"
        ],

        "phase": [
            "phase",
            "Phase"
        ],

        "primary_axis": [
            "primary_axis",
            "axis"
        ],

        "mechanism_score": [
            "mechanism_score"
        ],

        "axis_bonus": [
            "axis_bonus"
        ],

        "consequence_support": [
            "consequence_support"
        ],

        "phase_context_score": [
            "phase_context_score",
            "phase_score"
        ],

        "data_quality": [
            "data_quality"
        ],

        "sac_score": [
            "sac_score"
        ],

        "kinetochore_score": [
            "kinetochore_score"
        ],

        "microtubule_score": [
            "microtubule_score"
        ],

        "mitosis_score": [
            "mitosis_score"
        ],

        "cell_cycle_score": [
            "cell_cycle_score"
        ],

        "aurora_plk_score": [
            "aurora_plk_score"
        ],

        "mps1_score": [
            "mps1_score"
        ],

        "apoptosis_score": [
            "apoptosis_score"
        ],

        "evidence_terms": [
            "evidence_terms",
            "evidence"
        ],

        "final_score": [
            "final_score",
            "score"
        ],

        "mechanistic_rationale": [
            "mechanistic_rationale"
        ],

        "validation_hypothesis": [
            "validation_hypothesis"
        ],

        "research_status": [
            "research_status"
        ],

        "approval_context": [
            "approval_context"
        ],

        "approval_evidence_in_dataset": [
            "approval_evidence_in_dataset"
        ],
    }

    existing_lower = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for target_name, candidates in aliases.items():

        for candidate in candidates:

            key = candidate.strip().lower()

            if key in existing_lower:

                actual = existing_lower[key]

                if actual != target_name:

                    rename_map[actual] = target_name

                break

    if rename_map:

        df = df.rename(
            columns=rename_map
        )

    required_defaults = {

        "compound_id": "",
        "name": "",
        "moa": "",
        "target": "",
        "phase": "",
        "primary_axis": "",
        "mechanism_score": 0.0,
        "axis_bonus": 0.0,
        "consequence_support": 0.0,
        "phase_context_score": 0.0,
        "data_quality": 0.0,
        "sac_score": 0.0,
        "kinetochore_score": 0.0,
        "microtubule_score": 0.0,
        "mitosis_score": 0.0,
        "cell_cycle_score": 0.0,
        "aurora_plk_score": 0.0,
        "mps1_score": 0.0,
        "apoptosis_score": 0.0,
        "evidence_terms": "",
        "final_score": 0.0,
        "mechanistic_rationale": "",
        "validation_hypothesis": "",
        "research_status": "",
        "approval_context": "",
        "approval_evidence_in_dataset": "",
    }

    for column, default in required_defaults.items():

        if column not in df.columns:

            df[column] = default

    return df


# ==============================================================================
# STATUS
# ==============================================================================

def classify_status(phase):

    text = normalize_lower(phase)

    if "launched" in text:

        return "LAUNCHED_DATASET"

    if "approved" in text:

        return "APPROVAL_LABEL_IN_DATASET"

    if "phase 3" in text:

        return "PHASE_3"

    if "phase 2" in text:

        return "PHASE_2"

    if "phase 1" in text:

        return "PHASE_1"

    if "preclinical" in text:

        return "PRECLINICAL"

    if "clinical" in text:

        return "CLINICAL_UNSPECIFIED"

    return "OTHER"


# ==============================================================================
# MECANISMOS
# ==============================================================================

def infer_mechanism_family(row):

    axis = normalize_lower(
        row.get("primary_axis", "")
    )

    moa = normalize_lower(
        row.get("moa", "")
    )

    target = normalize_lower(
        row.get("target", "")
    )

    evidence = normalize_lower(
        row.get("evidence_terms", "")
    )

    combined = " ".join(
        [
            axis,
            moa,
            target,
            evidence,
        ]
    )

    if any(
        term in combined
        for term in [
            "mps1",
            "ttk",
            "spindle assembly checkpoint",
            "sac"
        ]
    ):

        return "MPS1_TTK_SAC"

    if any(
        term in combined
        for term in [
            "aurora",
            "aurora a",
            "aurora b",
            "plk",
            "polo-like"
        ]
    ):

        return "AURORA_PLK_MITOSIS"

    if any(
        term in combined
        for term in [
            "microtubule",
            "tubulin",
            "mitotic spindle",
            "spindle",
            "vinca",
            "taxane"
        ]
    ):

        return "MICROTUBULE_MITOSIS"

    if any(
        term in combined
        for term in [
            "kinetochore",
            "chromosome segregation",
            "chromosome",
            "centromere"
        ]
    ):

        return "CHROMOSOME_SEGREGATION"

    if any(
        term in combined
        for term in [
            "cell cycle",
            "cdk",
            "cyclin",
            "checkpoint"
        ]
    ):

        return "CELL_CYCLE"

    if any(
        term in combined
        for term in [
            "parp",
            "dna repair",
            "homologous recombination",
            "base excision",
            "repair"
        ]
    ):

        return "DNA_REPAIR"

    if any(
        term in combined
        for term in [
            "apoptosis",
            "bcl",
            "caspase",
            "cell death"
        ]
    ):

        return "APOPTOSIS"

    return "NO_DIRECT_MECHANISM"


# ==============================================================================
# RELACIÓN CON BUB1B
# ==============================================================================

def build_bub1b_relation(
    family,
    profile
):

    lof = profile["lof_hypothesis"]

    stop_count = len(
        profile["stop_gained"]
    )

    missense_count = len(
        profile["missense"]
    )

    axes = profile["axes"]

    mitotic_checkpoint = axes.get(
        "MITOTIC_CHECKPOINT",
        0.0
    )

    chromosome_segregation = axes.get(
        "CHROMOSOME_SEGREGATION",
        0.0
    )

    microtubule_mitosis = axes.get(
        "MICROTUBULE_MITOSIS",
        0.0
    )

    cell_cycle = axes.get(
        "CELL_CYCLE",
        0.0
    )

    if not lof:

        return (
            "BUB1B LoF hypothesis not activated; "
            "mechanistic interpretation remains exploratory."
        )

    if family == "MPS1_TTK_SAC":

        return (
            "High mechanistic compatibility with the BUB1B LoF hypothesis. "
            "BUB1B participates in spindle assembly checkpoint control; "
            "MPS1/TTK is a pharmacologically perturbable node within this "
            "mitotic checkpoint network."
        )

    if family == "AURORA_PLK_MITOSIS":

        return (
            "Strong mitotic-network compatibility with the BUB1B LoF "
            "hypothesis through chromosome segregation and mitotic control. "
            "Aurora/PLK perturbation represents a downstream mitotic "
            "mechanism for experimental validation."
        )

    if family == "MICROTUBULE_MITOSIS":

        return (
            "Mechanistic compatibility through mitotic spindle and "
            "chromosome-segregation biology. This is an indirect downstream "
            "vulnerability hypothesis rather than evidence of BUB1B-specific "
            "drug efficacy."
        )

    if family == "CHROMOSOME_SEGREGATION":

        return (
            "Directly relevant biological axis because BUB1B is involved "
            "in chromosome segregation and kinetochore-associated mitotic "
            "control."
        )

    if family == "CELL_CYCLE":

        return (
            "Moderate mechanistic compatibility through cell-cycle control. "
            "The relationship is broader than the primary SAC/mitotic axes "
            "and therefore requires experimental prioritization."
        )

    if family == "DNA_REPAIR":

        return (
            "Indirect hypothesis. DNA-repair dependence is not a primary "
            "BUB1B axis in this profile and should be considered lower "
            "priority unless additional molecular evidence supports it."
        )

    if family == "APOPTOSIS":

        return (
            "Indirect downstream hypothesis through cellular stress and "
            "cell-death responses. Not a direct BUB1B mechanism."
        )

    return (
        "No direct BUB1B mechanistic connection identified in the current "
        "mechanism vocabulary; retained only as a low-priority exploratory "
        "candidate."
    )


# ==============================================================================
# CONSEQUENCE SUPPORT
# ==============================================================================

def calculate_consequence_support(
    row,
    profile
):

    family = normalize_text(
        row.get(
            "mechanism_family",
            ""
        )
    )

    lof = profile["lof_hypothesis"]

    if not lof:

        return 0.0

    if family == "MPS1_TTK_SAC":

        return 5.0

    if family == "AURORA_PLK_MITOSIS":

        return 4.5

    if family == "CHROMOSOME_SEGREGATION":

        return 4.5

    if family == "MICROTUBULE_MITOSIS":

        return 4.0

    if family == "CELL_CYCLE":

        return 2.5

    if family == "APOPTOSIS":

        return 1.0

    if family == "DNA_REPAIR":

        return 0.75

    return 0.0


# ==============================================================================
# BUB1B AXIS COMPATIBILITY
# ==============================================================================

def calculate_axis_compatibility(
    row,
    profile
):

    family = normalize_text(
        row.get(
            "mechanism_family",
            ""
        )
    )

    axes = profile["axes"]

    axis_value = 0.0

    if family == "MPS1_TTK_SAC":

        axis_value = max(
            axes.get("MITOTIC_CHECKPOINT", 0.0),
            axes.get("CHROMOSOME_SEGREGATION", 0.0)
        )

        return axis_value * 0.35

    if family == "AURORA_PLK_MITOSIS":

        axis_value = max(
            axes.get("MICROTUBULE_MITOSIS", 0.0),
            axes.get("CHROMOSOME_SEGREGATION", 0.0),
            axes.get("MITOTIC_CHECKPOINT", 0.0)
        )

        return axis_value * 0.30

    if family == "MICROTUBULE_MITOSIS":

        axis_value = axes.get(
            "MICROTUBULE_MITOSIS",
            0.0
        )

        return axis_value * 0.30

    if family == "CHROMOSOME_SEGREGATION":

        axis_value = axes.get(
            "CHROMOSOME_SEGREGATION",
            0.0
        )

        return axis_value * 0.30

    if family == "CELL_CYCLE":

        axis_value = axes.get(
            "CELL_CYCLE",
            0.0
        )

        return axis_value * 0.25

    if family == "APOPTOSIS":

        axis_value = axes.get(
            "APOPTOSIS",
            0.0
        )

        return axis_value * 0.15

    if family == "DNA_REPAIR":

        axis_value = axes.get(
            "DNA_REPLICATION_STRESS",
            0.0
        )

        return axis_value * 0.15

    return 0.0


# ==============================================================================
# STATUS SCORE
# ==============================================================================

def status_score(status):

    scores = {

        "LAUNCHED_DATASET": 5.0,

        "APPROVAL_LABEL_IN_DATASET": 5.0,

        "PHASE_3": 4.0,

        "PHASE_2": 3.0,

        "PHASE_1": 2.0,

        "CLINICAL_UNSPECIFIED": 2.0,

        "PRECLINICAL": 0.5,

        "OTHER": 0.0,
    }

    return scores.get(
        status,
        0.0
    )


# ==============================================================================
# CALIFICACIÓN DE CADA CANDIDATO
# ==============================================================================

def score_candidate(
    row,
    profile
):

    family = row["mechanism_family"]

    mechanism_score = safe_float(
        row.get(
            "mechanism_score",
            0.0
        )
    )

    axis_bonus_original = safe_float(
        row.get(
            "axis_bonus",
            0.0
        )
    )

    consequence_support = calculate_consequence_support(
        row,
        profile
    )

    axis_compatibility = calculate_axis_compatibility(
        row,
        profile
    )

    status = row["status_category"]

    phase_score = status_score(
        status
    )

    data_quality = safe_float(
        row.get(
            "data_quality",
            0.0
        )
    )

    final_score = (

        mechanism_score * 0.55

        + axis_bonus_original * 0.15

        + consequence_support * 1.00

        + axis_compatibility * 0.55

        + phase_score * 0.50

        + data_quality * 0.10
    )

    return final_score


# ==============================================================================
# DIVERSIDAD
# ==============================================================================

def diverse_selection(
    df,
    n,
    max_per_family=2
):

    selected = []

    family_counts = {}

    for _, row in df.iterrows():

        family = normalize_text(
            row.get(
                "mechanism_family",
                "NO_DIRECT_MECHANISM"
            )
        )

        count = family_counts.get(
            family,
            0
        )

        if count >= max_per_family:

            continue

        selected.append(row)

        family_counts[family] = count + 1

        if len(selected) >= n:

            break

    return pd.DataFrame(
        selected
    )


# ==============================================================================
# CONSTRUCCIÓN DE CANDIDATOS
# ==============================================================================

def build_final_ranking(
    df,
    profile
):

    print()
    print("[4/8] Aplicando capa final BUB1B/status...")

    df = df.copy()

    df["status_category"] = df["phase"].apply(
        classify_status
    )

    df["mechanism_family"] = df.apply(
        infer_mechanism_family,
        axis=1
    )

    df["bub1b_relation"] = df.apply(
        lambda row: build_bub1b_relation(
            row["mechanism_family"],
            profile
        ),
        axis=1
    )

    df["bub1b_consequence_support"] = df.apply(
        lambda row: calculate_consequence_support(
            row,
            profile
        ),
        axis=1
    )

    df["bub1b_axis_compatibility"] = df.apply(
        lambda row: calculate_axis_compatibility(
            row,
            profile
        ),
        axis=1
    )

    df["trinova_final_score"] = df.apply(
        lambda row: score_candidate(
            row,
            profile
        ),
        axis=1
    )

    df["research_interpretation"] = df.apply(
        lambda row: build_research_interpretation(
            row,
            profile
        ),
        axis=1
    )

    df["trinova_validation_hypothesis"] = df.apply(
        lambda row: build_validation_hypothesis(
            row,
            profile
        ),
        axis=1
    )

    df["evidence_level"] = df.apply(
        lambda row: classify_evidence_level(
            row,
            profile
        ),
        axis=1
    )

    df = df.sort_values(
        by=[
            "trinova_final_score",
            "bub1b_consequence_support",
            "bub1b_axis_compatibility",
            "mechanism_score"
        ],
        ascending=[
            False,
            False,
            False,
            False
        ]
    ).reset_index(
        drop=True
    )

    df["trinova_rank"] = (
        df.index + 1
    )

    return df


# ==============================================================================
# INTERPRETACIÓN
# ==============================================================================

def build_research_interpretation(
    row,
    profile
):

    family = row["mechanism_family"]

    status = row["status_category"]

    if family == "MPS1_TTK_SAC":

        text = (
            "Priority hypothesis because MPS1/TTK is a mitotic "
            "checkpoint node compatible with the BUB1B LoF hypothesis."
        )

    elif family == "AURORA_PLK_MITOSIS":

        text = (
            "Mitotic-network hypothesis linked to chromosome segregation "
            "and mitotic progression downstream of BUB1B biology."
        )

    elif family == "MICROTUBULE_MITOSIS":

        text = (
            "Mitotic spindle hypothesis compatible with the "
            "chromosome-segregation vulnerability."
        )

    elif family == "CHROMOSOME_SEGREGATION":

        text = (
            "Direct biological-axis hypothesis involving chromosome "
            "segregation and kinetochore-associated processes."
        )

    elif family == "CELL_CYCLE":

        text = (
            "Broader cell-cycle hypothesis with indirect compatibility "
            "with BUB1B-associated mitotic dysfunction."
        )

    elif family == "DNA_REPAIR":

        text = (
            "Secondary exploratory hypothesis; not a primary BUB1B axis."
        )

    elif family == "APOPTOSIS":

        text = (
            "Indirect stress-response hypothesis; not a direct "
            "BUB1B mechanism."
        )

    else:

        text = (
            "Low-priority exploratory candidate without a direct "
            "BUB1B mechanistic relationship in the current vocabulary."
        )

    text += (
        f" Dataset status: {status}. "
        "This ranking represents a research hypothesis and not "
        "evidence of therapeutic efficacy."
    )

    return text


# ==============================================================================
# VALIDACIÓN EXPERIMENTAL
# ==============================================================================

def build_validation_hypothesis(
    row,
    profile
):

    family = row["mechanism_family"]

    name = normalize_text(
        row["name"]
    )

    if family == "MPS1_TTK_SAC":

        return (
            f"Test {name} in a BUB1B LoF-relevant cellular model and "
            "measure spindle assembly checkpoint integrity, mitotic "
            "duration, chromosome mis-segregation and cell viability."
        )

    if family == "AURORA_PLK_MITOSIS":

        return (
            f"Test {name} for differential sensitivity in a BUB1B "
            "LoF-relevant model, measuring mitotic progression, "
            "chromosome segregation and viability."
        )

    if family == "MICROTUBULE_MITOSIS":

        return (
            f"Test {name} for differential response in BUB1B LoF versus "
            "control cells, focusing on spindle integrity and "
            "chromosome-segregation phenotypes."
        )

    if family == "CHROMOSOME_SEGREGATION":

        return (
            f"Test {name} in a model with experimentally established "
            "BUB1B perturbation and quantify chromosome-segregation defects."
        )

    if family == "CELL_CYCLE":

        return (
            f"Evaluate {name} for differential cell-cycle response in "
            "BUB1B-perturbed versus control models."
        )

    if family == "DNA_REPAIR":

        return (
            f"Use {name} as a secondary hypothesis and test whether "
            "BUB1B perturbation creates measurable differential sensitivity."
        )

    if family == "APOPTOSIS":

        return (
            f"Evaluate whether {name} modifies stress-induced cell death "
            "in a BUB1B-perturbed experimental system."
        )

    return (
        f"Use {name} only as an exploratory comparator until a stronger "
        "BUB1B-specific mechanistic link is established."
    )


# ==============================================================================
# NIVEL DE EVIDENCIA
# ==============================================================================

def classify_evidence_level(
    row,
    profile
):

    family = row["mechanism_family"]

    if not profile["lof_hypothesis"]:

        return "EXPLORATORY"

    if family == "MPS1_TTK_SAC":

        return "HIGH_MECHANISTIC_COMPATIBILITY"

    if family in [
        "AURORA_PLK_MITOSIS",
        "CHROMOSOME_SEGREGATION"
    ]:

        return "MODERATE_HIGH_MECHANISTIC_COMPATIBILITY"

    if family == "MICROTUBULE_MITOSIS":

        return "MODERATE_MECHANISTIC_COMPATIBILITY"

    if family == "CELL_CYCLE":

        return "SECONDARY_MECHANISTIC_COMPATIBILITY"

    return "LOWER_PRIORITY_EXPLORATORY"


# ==============================================================================
# DEDUPLICACIÓN
# ==============================================================================

def deduplicate(df):

    print()
    print("[5/8] Deduplicando...")

    df = df.copy()

    df["_dedup_name"] = (
        df["name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["_dedup_target"] = (
        df["target"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df = df.sort_values(
        "trinova_final_score",
        ascending=False
    )

    df = df.drop_duplicates(
        subset=[
            "_dedup_name",
            "_dedup_target"
        ],
        keep="first"
    )

    df = df.drop(
        columns=[
            "_dedup_name",
            "_dedup_target"
        ]
    )

    df = df.reset_index(
        drop=True
    )

    df["trinova_rank"] = (
        df.index + 1
    )

    print(
        f"[+] Candidatos únicos: {len(df)}"
    )

    return df


# ==============================================================================
# REPURPOSING SHORTLIST
# ==============================================================================

def build_repurposing_shortlist(
    df
):

    repurposing_pool = df[
        df["status_category"].isin(
            [
                "LAUNCHED_DATASET",
                "APPROVAL_LABEL_IN_DATASET"
            ]
        )
    ].copy()

    repurposing_pool = repurposing_pool.sort_values(
        [
            "trinova_final_score",
            "bub1b_consequence_support",
            "bub1b_axis_compatibility"
        ],
        ascending=[
            False,
            False,
            False
        ]
    )

    shortlist = diverse_selection(
        repurposing_pool,
        n=8,
        max_per_family=2
    )

    return shortlist


# ==============================================================================
# DISCOVERY SET
# ==============================================================================

def build_discovery_set(
    df
):

    discovery_pool = df[
        ~df["status_category"].isin(
            [
                "LAUNCHED_DATASET",
                "APPROVAL_LABEL_IN_DATASET"
            ]
        )
    ].copy()

    discovery_pool = discovery_pool.sort_values(
        [
            "trinova_final_score",
            "bub1b_consequence_support",
            "bub1b_axis_compatibility"
        ],
        ascending=[
            False,
            False,
            False
        ]
    )

    discovery = diverse_selection(
        discovery_pool,
        n=12,
        max_per_family=3
    )

    return discovery


# ==============================================================================
# COMBINACIONES
# ==============================================================================

def generate_combination_hypotheses(
    shortlist,
    discovery
):

    print()
    print("[7/8] Generando hipótesis combinatorias...")

    all_candidates = pd.concat(
        [
            shortlist,
            discovery
        ],
        ignore_index=True
    )

    combinations_output = []

    for _, row_a in all_candidates.iterrows():

        for _, row_b in all_candidates.iterrows():

            name_a = normalize_lower(
                row_a["name"]
            )

            name_b = normalize_lower(
                row_b["name"]
            )

            if name_a >= name_b:
                continue

            family_a = row_a["mechanism_family"]

            family_b = row_b["mechanism_family"]

            if family_a == family_b:
                continue

            score = (
                safe_float(
                    row_a["trinova_final_score"]
                )
                +
                safe_float(
                    row_b["trinova_final_score"]
                )
            ) / 2.0

            combinations_output.append(
                {
                    "candidate_a": row_a["name"],
                    "candidate_b": row_b["name"],
                    "mechanism_a": family_a,
                    "mechanism_b": family_b,
                    "status_a": row_a["status_category"],
                    "status_b": row_b["status_category"],
                    "combined_priority_score": round(
                        score,
                        4
                    ),
                    "interpretation": (
                        "Potentially complementary mechanisms "
                        "within the BUB1B mitotic vulnerability "
                        "hypothesis. No synergy is assumed."
                    ),
                    "validation_hypothesis": (
                        "If experimentally justified, compare single-agent "
                        "effects with the combination while measuring "
                        "mitotic progression, chromosome segregation and "
                        "cell viability."
                    )
                }
            )

    combinations_df = pd.DataFrame(
        combinations_output
    )

    if len(combinations_df) > 0:

        combinations_df = combinations_df.sort_values(
            "combined_priority_score",
            ascending=False
        ).head(20)

    return combinations_df


# ==============================================================================
# PERFIL FINAL
# ==============================================================================

def build_final_profile(
    profile,
    ranked,
    shortlist,
    discovery
):

    top_candidates = []

    for _, row in shortlist.iterrows():

        top_candidates.append(
            {
                "name": row["name"],
                "mechanism_family": row["mechanism_family"],
                "status": row["status_category"],
                "score": round(
                    safe_float(
                        row["trinova_final_score"]
                    ),
                    4
                ),
                "bub1b_relation": row["bub1b_relation"],
                "evidence_level": row["evidence_level"]
            }
        )

    return {

        "framework": "TRINOVA.OS",

        "track": "TRACK_2",

        "module": (
            "FINAL_REPURPOSING_SHORTLIST_"
            "AND_DIVERSIFICATION"
        ),

        "status": (
            "RESEARCH_HYPOTHESIS_GENERATION"
        ),

        "gene": "BUB1B",

        "molecular_profile": {

            "loF_hypothesis": bool(
                profile["lof_hypothesis"]
            ),

            "stop_gained_count": len(
                profile["stop_gained"]
            ),

            "missense_count": len(
                profile["missense"]
            ),

            "frameshift_count": len(
                profile["frameshift"]
            ),

            "splice_count": len(
                profile["splice"]
            ),

            "phase": profile["phase"],

            "phase_supported": profile[
                "phase_supported"
            ],

            "mechanistic_axes": profile[
                "axes"
            ]
        },

        "dataset": {

            "total_ranked_candidates": int(
                len(ranked)
            ),

            "repurposing_shortlist": int(
                len(shortlist)
            ),

            "mechanistic_discovery_set": int(
                len(discovery)
            )
        },

        "top_repurposing_candidates": top_candidates,

        "interpretation": (
            "TriNova.OS prioritizes pharmacologically perturbable "
            "mechanisms compatible with a BUB1B loss-of-function "
            "hypothesis anchored by a FASTA-confirmed STOP_GAINED "
            "variant. Candidates are ranked for experimental "
            "validation and are not presented as evidence of efficacy."
        ),

        "limitations": [

            "The STOP_GAINED variant supports a BUB1B loss-of-function hypothesis but does not independently establish clinical causality.",

            "The missense variant is retained as secondary evidence and is not assumed pathogenic.",

            "Phase between coding variants is not assumed without explicit evidence.",

            "TriNova entropy is a prioritization/navigation heuristic.",

            "Mechanistic compatibility does not establish drug efficacy.",

            "LAUNCHED_DATASET reflects the Broad dataset status and is not by itself proof of current regulatory approval.",

            "No pediatric safety claim is made from this ranking.",

            "Combination hypotheses do not imply pharmacological synergy."
        ]
    }


# ==============================================================================
# ESCRITURA DE RESULTADOS
# ==============================================================================

def write_outputs(
    ranked,
    shortlist,
    discovery,
    combinations_df,
    final_profile,
    profile
):

    print()
    print("[8/8] Escribiendo resultados...")

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    ranked.to_csv(
        FINAL_RANKED,
        index=False,
        encoding="utf-8-sig"
    )

    shortlist.to_csv(
        REPURPOSING_SHORTLIST,
        index=False,
        encoding="utf-8-sig"
    )

    discovery.to_csv(
        DISCOVERY_SET,
        index=False,
        encoding="utf-8-sig"
    )

    combinations_df.to_csv(
        COMBINATION_HYPOTHESES,
        index=False,
        encoding="utf-8-sig"
    )

    with open(
        FINAL_PROFILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            final_profile,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------

    summary_lines = []

    summary_lines.append(
        "TRINOVA.OS — TRACK 2 — FINAL REPURPOSING"
    )

    summary_lines.append(
        "=" * 80
    )

    summary_lines.append("")

    summary_lines.append(
        "MOLECULAR HYPOTHESIS"
    )

    summary_lines.append(
        "-" * 80
    )

    summary_lines.append(
        f"BUB1B STOP_GAINED: "
        f"{len(profile['stop_gained'])}"
    )

    summary_lines.append(
        f"BUB1B MISSENSE: "
        f"{len(profile['missense'])}"
    )

    summary_lines.append(
        f"BUB1B FRAMESHIFT: "
        f"{len(profile['frameshift'])}"
    )

    summary_lines.append(
        f"BUB1B SPLICE: "
        f"{len(profile['splice'])}"
    )

    summary_lines.append(
        f"LoF hypothesis: "
        f"{profile['lof_hypothesis']}"
    )

    summary_lines.append(
        f"Phase: "
        f"{profile['phase']}"
    )

    summary_lines.append(
        f"Phase supported: "
        f"{profile['phase_supported']}"
    )

    summary_lines.append("")

    summary_lines.append(
        "MECHANISTIC AXES"
    )

    summary_lines.append(
        "-" * 80
    )

    for axis, value in sorted(
        profile["axes"].items(),
        key=lambda x: x[1],
        reverse=True
    ):

        summary_lines.append(
            f"{axis}: {value:.3f}"
        )

    summary_lines.append("")

    summary_lines.append(
        "FINAL REPURPOSING SHORTLIST"
    )

    summary_lines.append(
        "-" * 80
    )

    for i, (_, row) in enumerate(
        shortlist.iterrows(),
        start=1
    ):

        summary_lines.append(
            f"{i}. {row['name']}"
        )

        summary_lines.append(
            f"   Score: "
            f"{safe_float(row['trinova_final_score']):.2f}"
        )

        summary_lines.append(
            f"   Mechanism: "
            f"{row['mechanism_family']}"
        )

        summary_lines.append(
            f"   Status: "
            f"{row['status_category']}"
        )

        summary_lines.append(
            f"   Evidence: "
            f"{row['evidence_level']}"
        )

        summary_lines.append(
            f"   BUB1B relation: "
            f"{row['bub1b_relation']}"
        )

        summary_lines.append(
            f"   Validation: "
            f"{row['trinova_validation_hypothesis']}"
        )

        summary_lines.append("")

    summary_lines.append(
        "MECHANISTIC DISCOVERY SET"
    )

    summary_lines.append(
        "-" * 80
    )

    for i, (_, row) in enumerate(
        discovery.iterrows(),
        start=1
    ):

        summary_lines.append(
            f"{i}. "
            f"{row['name']} | "
            f"{row['mechanism_family']} | "
            f"{row['status_category']} | "
            f"{safe_float(row['trinova_final_score']):.2f}"
        )

    summary_lines.append("")

    summary_lines.append(
        "SCIENTIFIC INTERPRETATION"
    )

    summary_lines.append(
        "-" * 80
    )

    summary_lines.append(
        "TriNova.OS prioritizes pharmacologically perturbable "
        "mechanisms compatible with a BUB1B loss-of-function "
        "hypothesis. The STOP_GAINED variant is used as the primary "
        "molecular anchor; the missense variant is retained as "
        "secondary evidence."
    )

    summary_lines.append("")

    summary_lines.append(
        "IMPORTANT LIMITATIONS"
    )

    summary_lines.append(
        "-" * 80
    )

    summary_lines.append(
        "Drug ranking does not establish efficacy."
    )

    summary_lines.append(
        "LAUNCHED_DATASET is a Broad dataset status and does not "
        "automatically mean current FDA approval."
    )

    summary_lines.append(
        "No clinical causality is claimed."
    )

    summary_lines.append(
        "No compound heterozygosity is claimed without phase evidence."
    )

    summary_lines.append(
        "No pediatric safety claim is made."
    )

    summary_lines.append(
        "Combination hypotheses do not imply synergy."
    )

    with open(
        FINAL_SUMMARY,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(summary_lines)
        )

    # --------------------------------------------------------------------------
    # QC
    # --------------------------------------------------------------------------

    qc_lines = []

    qc_lines.append(
        "TRINOVA.OS — TRACK 2 — FINAL QC"
    )

    qc_lines.append(
        "=" * 80
    )

    qc_lines.append(
        f"BUB1B functional variants: "
        f"{len(profile['functional_variants'])}"
    )

    qc_lines.append(
        f"STOP_GAINED: "
        f"{len(profile['stop_gained'])}"
    )

    qc_lines.append(
        f"MISSENSE: "
        f"{len(profile['missense'])}"
    )

    qc_lines.append(
        f"LoF hypothesis: "
        f"{profile['lof_hypothesis']}"
    )

    qc_lines.append(
        f"Ranked candidates: "
        f"{len(ranked)}"
    )

    qc_lines.append(
        f"Repurposing shortlist: "
        f"{len(shortlist)}"
    )

    qc_lines.append(
        f"Discovery set: "
        f"{len(discovery)}"
    )

    qc_lines.append(
        f"Combination hypotheses: "
        f"{len(combinations_df)}"
    )

    qc_lines.append("")

    qc_lines.append(
        "Mechanism family distribution — repurposing:"
    )

    for family, count in (
        shortlist["mechanism_family"]
        .value_counts()
        .items()
    ):

        qc_lines.append(
            f"  {family}: {count}"
        )

    qc_lines.append("")

    qc_lines.append(
        "Mechanism family distribution — discovery:"
    )

    for family, count in (
        discovery["mechanism_family"]
        .value_counts()
        .items()
    ):

        qc_lines.append(
            f"  {family}: {count}"
        )

    qc_lines.append("")

    qc_lines.append(
        "STATUS INTERPRETATION:"
    )

    qc_lines.append(
        "LAUNCHED_DATASET is retained as a dataset status."
    )

    qc_lines.append(
        "Current regulatory approval must be independently verified "
        "before using the word 'approved' in the final submission."
    )

    with open(
        FINAL_QC,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(qc_lines)
        )


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print()
    print("=" * 90)

    print(
        "TRINOVA.OS — TRACK 2"
    )

    print(
        "FINAL REPURPOSING SHORTLIST & DIVERSIFICATION — v1"
    )

    print("=" * 90)

    print()
    print("[1/8] Verificando rutas...")

    verify_paths()

    profile = load_bub1b_profile()

    df = load_consequence_ranked()

    df = normalize_ranking_columns(
        df
    )

    df = build_final_ranking(
        df,
        profile
    )

    df = deduplicate(
        df
    )

    print()
    print(
        "[6/8] Construyendo repurposing shortlist..."
    )

    shortlist = build_repurposing_shortlist(
        df
    )

    discovery = build_discovery_set(
        df
    )

    print(
        f"[+] Repurposing shortlist: "
        f"{len(shortlist)}"
    )

    print(
        f"[+] Discovery set: "
        f"{len(discovery)}"
    )

    combinations_df = generate_combination_hypotheses(
        shortlist,
        discovery
    )

    final_profile = build_final_profile(
        profile,
        df,
        shortlist,
        discovery
    )

    write_outputs(
        df,
        shortlist,
        discovery,
        combinations_df,
        final_profile,
        profile
    )

    # ==========================================================================
    # RESULTADO
    # ==========================================================================

    print()
    print("=" * 90)

    print(
        "RESULTADO FINAL — TRINOVA.OS TRACK 2"
    )

    print("=" * 90)

    print()

    print(
        "HIPÓTESIS MOLECULAR"
    )

    print("-" * 80)

    print(
        f"  BUB1B STOP_GAINED: "
        f"{len(profile['stop_gained'])}"
    )

    print(
        f"  BUB1B MISSENSE: "
        f"{len(profile['missense'])}"
    )

    print(
        f"  BUB1B FRAMESHIFT: "
        f"{len(profile['frameshift'])}"
    )

    print(
        f"  BUB1B SPLICE: "
        f"{len(profile['splice'])}"
    )

    print(
        f"  LoF hypothesis: "
        f"{profile['lof_hypothesis']}"
    )

    print()

    print(
        "FINAL REPURPOSING SHORTLIST"
    )

    print("-" * 80)

    for i, (_, row) in enumerate(
        shortlist.iterrows(),
        start=1
    ):

        print(
            f"{i}. {row['name']}"
        )

        print(
            f"   Score: "
            f"{safe_float(row['trinova_final_score']):.2f}"
        )

        print(
            f"   Mechanism: "
            f"{row['mechanism_family']}"
        )

        print(
            f"   Status: "
            f"{row['status_category']}"
        )

        print(
            f"   Evidence: "
            f"{row['evidence_level']}"
        )

        print(
            f"   BUB1B relation: "
            f"{row['bub1b_relation']}"
        )

        print()

    print(
        "DISCOVERY SET"
    )

    print("-" * 80)

    for i, (_, row) in enumerate(
        discovery.iterrows(),
        start=1
    ):

        print(
            f"{i}. "
            f"{row['name']} | "
            f"{row['mechanism_family']} | "
            f"{row['status_category']} | "
            f"{safe_float(row['trinova_final_score']):.2f}"
        )

    print()

    print(
        "ARCHIVOS GENERADOS"
    )

    print(
        f"  [1] {FINAL_RANKED}"
    )

    print(
        f"  [2] {REPURPOSING_SHORTLIST}"
    )

    print(
        f"  [3] {DISCOVERY_SET}"
    )

    print(
        f"  [4] {COMBINATION_HYPOTHESES}"
    )

    print(
        f"  [5] {FINAL_PROFILE}"
    )

    print(
        f"  [6] {FINAL_SUMMARY}"
    )

    print(
        f"  [7] {FINAL_QC}"
    )

    print()
    print("=" * 90)

    print(
        "TRINOVA.OS — FINAL REPURPOSING MODULE v1 COMPLETADO"
    )

    print("=" * 90)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":

    main()
