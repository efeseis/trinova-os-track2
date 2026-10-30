# TriNova.OS | MVA Hackathon 2026
## Track 2: Drug Repurposing

**Project:** BUB1B Molecular Vulnerability and Drug Repurposing  
**Framework:** TriNova.OS  
**Track:** MVA Hackathon 2026 · Track 2  
**Purpose:** Computational hypothesis generation for drug repurposing research  
**Author:** Erick Fernando Rojas Rojas

---

## 1. Project Overview

Track 2 explores whether existing medications and investigational compounds have biological mechanisms that may be relevant to molecular vulnerabilities associated with the BUB1B molecular profile.

The project uses computational analysis to connect molecular evidence, biological pathways, drug-target annotations, and drug-development information.

The objective is to identify and organize candidates that may warrant further biological and pharmacological investigation.

The implementation contains two complementary but independent computational pipelines.

Each pipeline has its own input requirements, classification strategy, scoring model, selection criteria, and output files.

They address the same research objective from different computational perspectives and are intentionally preserved as separate implementations.

**All results are research hypotheses for follow-up. They are not evidence that a medication works, clinical recommendations, prescriptions, or treatment guidance.**

---

## 2. Scientific Context

BUB1B is associated with the mitotic spindle assembly checkpoint and chromosome segregation.

The molecular context used in Track 2 includes functional variant consequences, a potential loss-of-function hypothesis, and mechanistic axes derived from upstream molecular analysis.

The project explores several biological areas:

- Mitotic checkpoint regulation.
- MPS1 / TTK signaling.
- Aurora and PLK mitotic regulation.
- Chromosome segregation and kinetochore function.
- Microtubule dynamics.
- Cell-cycle regulation.
- Apoptosis.
- DNA replication stress.

These mechanisms provide a framework for computational candidate prioritization.

A relationship between a drug target and a biological pathway does not demonstrate that the compound can correct the molecular alteration or provide therapeutic benefit.

---

## 3. Computational Architecture

Track 2 contains two independent analytical modules.

### Module A: Final Repurposing Shortlist and Diversification

**Python implementation:** First Track 2 script.

This module uses an upstream consequence-aware candidate ranking and BUB1B molecular profile to produce a final prioritized candidate collection.

Its principal operations include:

- Loading the molecular profile.
- Integrating consequence-aware candidate information.
- Classifying drug-associated mechanisms.
- Calculating composite prioritization scores.
- Separating a repurposing shortlist from a mechanistic discovery set.
- Diversifying candidates across mechanism families.
- Generating exploratory candidate-pair hypotheses.
- Exporting ranking tables, profiles, summaries, and QC reports.

Its combination hypotheses are generated from candidate pairs belonging to different mechanistic families.

See the dedicated README for the complete methodology, scoring formula, input requirements, outputs, and limitations.

### Module B: Molecular Vulnerability and Drug Repurposing

**Python implementation:** Second Track 2 script, `FINAL CANDIDATE (pipeline2)`.

This module independently loads a compatible BUB1B molecular profile and the Broad Repurposing Hub dataset.

Its principal operations include:

- Discovering and validating the molecular profile.
- Summarizing functional variant consequences.
- Calculating a heuristic molecular-support index.
- Classifying compounds into seven mechanistic clusters.
- Recording matched-term provenance.
- Calculating molecular relevance and development-context scores.
- Ranking the loaded compound catalogue.
- Generating a repurposing shortlist and discovery set.
- Ranking mechanistic clusters.
- Generating complementary mechanistic-coverage hypotheses.
- Exporting CSV, JSON, summary, and QC files.

Its combination-related output represents complementary coverage between molecular axes, not specific drug-pair recommendations.

See the dedicated README for the complete methodology, scoring formula, input requirements, outputs, and limitations.

---

## 4. Relationship Between the Two Modules

The two implementations share a common scientific objective but do not form a mandatory sequential pipeline.

They are not interchangeable and their scores should not be directly compared.

| Dimension | Module A | Module B |
|---|---|---|
| Main approach | Consequence-aware candidate prioritization | Molecular-axis and catalogue-based prioritization |
| Molecular context | Upstream BUB1B profile | Compatible BUB1B profile |
| Drug information | Upstream ranked candidate dataset and associated inputs | Broad Repurposing Hub |
| Mechanistic analysis | Mechanism-family classification and compatibility | Seven rule-based mechanistic clusters |
| Scoring | Composite candidate score | Molecular relevance and development-context score |
| Candidate selection | Shortlist and discovery set | Shortlist and discovery set |
| Combination output | Candidate-pair hypotheses across mechanism families | Complementary coverage between molecular axes |
| Main purpose | Final candidate prioritization and diversification | Independent molecular vulnerability analysis |

The modules provide complementary analytical views.

Module A emphasizes consequence-aware candidate ranking and candidate diversification.

Module B emphasizes direct catalogue analysis, molecular-axis compatibility, and mechanistic cluster coverage.

Their independent outputs can be reviewed together as separate computational perspectives.

A shared biological rationale does not make their scoring systems equivalent.

---

## 5. Execution and Input Requirements

Each module has its own execution requirements.

### Module A

Requires the upstream molecular profile, consequence-aware ranking information, and the additional input files validated by its implementation.

Its output directory is configured within the script.

Refer to the Module A README for the complete list of expected inputs and execution instructions.

### Module B

Requires:

1. A compatible BUB1B molecular profile JSON.
2. The Broad Repurposing Hub tab-separated export.

It supports the following environment variables:

- `TRINOVA_BASE`
- `TRINOVA_TRACK2_ROOT`
- `TRINOVA_BROAD_HUB`

Its output directory is created alongside the Python script.

Refer to the Module B README for profile discovery, configuration, and execution instructions.

### Execution Independence

Neither module is defined as an obligatory predecessor of the other.

Each should be executed and evaluated according to its own input requirements and configuration.

The results should retain their original provenance and should not be merged into a single numerical ranking without an independently justified integration method.

---

## 6. Outputs and Interpretation

Both modules generate structured outputs intended for research review.

Depending on the module, these include:

- Ranked candidate tables.
- Repurposing shortlists.
- Mechanistic discovery sets.
- Mechanistic cluster summaries.
- Combination or coverage hypotheses.
- Structured JSON profiles.
- Human-readable summary reports.
- Quality-control reports.

The outputs should be interpreted within the methodology of the script that generated them.

In particular:

- A higher computational score does not represent a higher probability of clinical response.
- Mechanistic compatibility does not establish therapeutic efficacy.
- A development-status label does not independently establish regulatory approval.
- Candidate inclusion does not establish clinical availability or patient suitability.
- Combination hypotheses do not establish pharmacological synergy.

The two modules are intended to support hypothesis generation and structured research prioritization.

---

## 7. General Scientific and Clinical Limitations

The project does not independently establish:

- Clinical causality of the BUB1B findings.
- Pathogenicity of every identified variant.
- Therapeutic efficacy of any candidate.
- Drug safety or tolerability.
- Appropriate dosing.
- Pediatric authorization or suitability.
- Clinical benefit for the individual represented by the molecular profile.
- Synergy or safety of proposed drug combinations.

Variant interpretation, biological mechanisms, compound identity, pharmacology, and regulatory status require independent validation.

Potential interference with mitotic pathways may be ineffective or harmful. Mechanistic relevance alone is insufficient to establish a favorable therapeutic effect.

All outputs must be treated as research hypotheses requiring orthogonal biological, pharmacological, and regulatory evaluation.

### Exploratory Nature of Results and Professional Review

All results generated by TriNova.OS Track 2 are exploratory computational findings intended to support research hypothesis generation and candidate prioritization.

The identified compounds, molecular associations, mechanistic classifications, scores, and proposed hypotheses have not been clinically validated through this project. They must not be interpreted as established therapeutic conclusions, evidence of clinical efficacy, or medical recommendations.

The computational outputs require independent review, critical assessment, and, where appropriate, correction or refinement by qualified biomedical, pharmacological, and clinical professionals. Further experimental, pharmacological, and regulatory validation is necessary before any candidate can be considered for subsequent research or clinical evaluation.

The project addresses the hackathon challenge by applying computational methods to identify existing drug candidates whose known or annotated mechanisms may be relevant to the biological vulnerabilities explored in this case. Meeting this computational objective does not establish that any candidate is effective, safe, approved for a particular indication, or suitable for any individual.

**All findings should therefore be treated as preliminary research hypotheses, subject to professional review and further validation, rather than definitive conclusions.**

---

## 8. Reproducibility and Data Provenance

The results depend on the input datasets, molecular profile, annotations, scoring parameters, classification rules, and filtering thresholds used by each module.

For reproducibility:

- Document the source and version of each input dataset.
- Record the molecular profile provenance, subject to applicable privacy restrictions.
- Document the Broad Repurposing Hub export version.
- Preserve code, configuration, and methodological documentation where permitted.
- Maintain execution records and QC evidence only within the retention period and conditions authorized by the Hackathon Rules.
- Avoid comparing scores generated by different scoring systems as if they shared a common scale.

Changes in source data or algorithmic parameters may change candidate rankings.

Each output should remain traceable to the specific implementation and input files that generated it, subject to applicable data-retention and deletion requirements.

---

## 9. Data Governance, Temporary Availability, and Deletion Commitment

The `data/` directory contains input and supporting files required to document and reproduce the computational analyses, while `output_final/` contains the generated results and final computational deliverables produced by the respective pipelines.

These materials are included to provide reviewers with sufficient evidence to inspect the analytical workflow, verify computational execution, understand candidate prioritization, and evaluate the resulting research hypotheses developed for MVA Hackathon 2026 Track 2.

The repository is designed to avoid direct patient identifiers and to preserve participant anonymity. Nevertheless, all files remain subject to the Hackathon's privacy, data-use, and retention requirements. The absence of direct identifiers does not remove the obligation to comply with applicable restrictions on original, intermediate, or derived data.

Their publication and availability are strictly subject to the official Hackathon Rules and applicable data-use and privacy restrictions.

**All hackathon-related original data, intermediate data, and derived datasets included in or associated with this repository will be deleted from GitHub and all other environments immediately after the evaluation and review process is completed, or earlier if required, and in all cases no later than 30 days after the Hackathon closes, in accordance with the official rules.**

This deletion commitment includes applicable files stored in public or private repositories, local environments, cloud storage, and computational workspaces.

The repository's files are provided for evaluation and research documentation purposes only. Their temporary availability does not grant permission to redistribute the original hackathon data or disclose restricted or identifiable participant information.

The required data deletion and confirmation procedures established by the Hackathon organizers will be followed, including any required deletion confirmation.

Code, methodological documentation, and Markdown files may remain available only to the extent permitted by the official rules and applicable third-party licenses and restrictions.

---

## 10. Repository Organization

The repository is organized to separate the two computational modules, their supporting inputs, and their generated results.

A representative structure is:

```text
trinova-os-track2/
│
├── README.md
├── LICENSE
│
├── data/
│   └── Input and supporting files required by the pipelines
│
├── output_final/
│   └── Generated computational results and final deliverables
│
├── module_a/
│   ├── README.md
│   └── FINAL REPURPOSING SHORTLIST & DIVERSIFICATION v1.py
│
└── module_b/
    ├── README.md
    └── FINAL REPURPOSING SHORTLIST & DIVERSIFICATION v2.py
```

The actual repository may use different filenames or directory names.

The `data/` and `output_final/` directories are included for reproducibility and evaluation purposes, subject to the temporary availability and deletion commitments described in Section 9.

"The data/ directory contains only permitted non-restricted resources, functional annotations of BUB1B, and public third-party drug datasets (Broad Repurposing Hub). Raw genomic VCF/BAM files are strictly excluded."

The main README provides the shared project context and explains the relationship between the modules.

Each module README documents its own implementation without duplicating the full project-level description.

---

## 11. Research Scope and Intended Use

Track 2 is a computational drug-repurposing hypothesis-generation project.

Its purpose is to organize molecular and pharmacological information into structured candidate-prioritization outputs.

The two implementations provide independent analytical perspectives that can support further investigation.

They do not identify a treatment, establish a therapeutic recommendation, or demonstrate that any medication is effective.

**The central research principle is that mechanistic plausibility can guide investigation, but it cannot substitute for experimental and clinical evidence.**

---

## 12. License and Attribution

The hackathon deliverables are distributed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license, subject to the applicable hackathon requirements.

Third-party datasets and resources retain their respective licenses, terms of use, and attribution requirements.

Users are responsible for respecting the original data-source conditions.

The CC BY 4.0 license does not override privacy restrictions, third-party data licenses, or the Hackathon's data-retention and deletion requirements.

---
---
## 13. Acknowledgments

We express our profound gratitude to the child and their family, who generously chose to share their genomic data openly with the research community. This hackathon would not exist without their remarkable generosity, trust, and bravery in advancing research into this rare disease.

I personally want to express my deepest gratitude for the opportunity to participate in this noble mission alongside so many individuals who focus science and data analysis toward the greater good. I sincerely hope that some of the tools and computational frameworks developed here can help bring us closer to a solution.

This work was made possible through the Rare Disease Hackathon (MVA Hackathon 2026), organized by Sage Bionetworks in partnership with the MVA Society, Hugging Face, and BEACON (The Benchmarking, Evaluation, and Assessment Consortium for Science), with prize sponsorship from AWS and Anthropic. We also extend our sincere thanks to the Wilhelm Foundation for their invaluable guidance, clinical perspective, and insight throughout this project.
---

**TriNova.OS | MVA Hackathon 2026 | Track 2: Drug Repurposing**

*Two independent computational approaches. One shared research objective. Hypotheses for further investigation.*