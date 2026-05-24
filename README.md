# XenoCall

**XenoCall** is a neural network training and analysis pipeline for nanopore sequencing of unnatural base pairs (UBPs). It integrates Oxford Nanopore Technologies (ONT) workflows with Remora-based model training, reference-localized UBP detection, demultiplexing, signal-level visualization, and downstream analysis.

The software is organized around two layers:

- **`xenoquant.py`** — core engine for model training and UBP-aware basecalling
- **`xenoquant_pipe.py`** — master orchestration script for training, basecalling, demultiplexing, analysis, and visualization

This software has been tested on ONT **R9.4.1** and **R10.4.1** flow cells (**Flongle** and **MinION**) using **Remora 2.1.3**. This project is under active development.

---

## Overview

XenoCall supports:

- Training Remora-compatible RNN models for UBP detection
- Reference-localized UBP basecalling
- POD5-based nanopore preprocessing
- Alignment result extraction
- Barcode demultiplexing (cutadapt-based)
- Raw basecall class analysis
- Signal-level visualization, including:
  - signal metrics
  - spaghetti plots
  - step plots
  - violin plots
- Export of trained models for use with Dorado, Guppy, or Bonito through Remora compatibility

Models are trained on **defined sequence contexts**, not the full sequence space. For best performance, training should include:

1. A dataset containing the UBP substitution
2. A matched dataset containing the corresponding canonical DNA sequence

---

## Repository Structure

```text
xenoquant.py
    Command-line interface for model training and basecalling

xenoquant_pipe.py
    Master workflow controller with feature switches

lib/
├── xr_signal_metrics.py
├── xr_signal_plot_v2.py
├── xr_signal_plot_step.py
├── xr_violin.py
├── xr_extract_metrics.py
├── xr_results.py
├── xr_demux.py
├── xr_raw_basecall_analysis.py
├── xr_tools.py
└── xr_params.py
```

---

## Requirements

XenoCall requires:

- [Dorado Basecaller (ONT)](github.com/nanoporetech/dorado)
- ONT Tools (pod5-file-format, Remora)
- Bioinformatic Packages (Minimap2, Bioconda, Cutadapt, Samtools)
- Various standard Python packages

A full dependency list is provided in the environment file and can be installed using the following command.
```
conda env create -f xenoquant-re.yml
```

**Tested operating systems:**
- Ubuntu 18.04
- Ubuntu 20.04
- Ubuntu 22.04

**Tested Hardware:**
- Nvidia RTX 3060 (12 GB)
- Intel I7-11700
- 32 GB DDR4 (3200 MHz)
---

## Core CLI: `xenoquant.py`

### Sample Data Quickstart

This repository includes small POD5 subsets for exercising the training,
testing, and PCR basecalling workflows:

```text
SAMPLE_DATA/
├── Training_Testing/
│   ├── pod5/
│   │   ├── BS_Train_subset/
│   │   ├── AT_Train_subset/
│   │   ├── BS_Test_subset/
│   │   └── AT_Test_subset/
│   └── references/90mer_train_test.fasta
└── PCR/
    ├── pod5/
    └── references/
        ├── REF_B24_B25.fasta
        ├── DEMUX_B24_B25.csv
        └── EXPERIMENT_METADATA_B24_B25.csv
```

Before running the examples, create and activate the environment, then verify
that `lib/xr_params.py` points to your local Dorado binary and model:

```bash
conda env create -f xenoquant-re.yml
conda activate xenoquant-re
```

Check these parameters in `lib/xr_params.py`:

```python
dorado_path = "~/dorado-0.8.0-linux-x64/bin/dorado"
dorado_model = "~/dorado-0.8.0-linux-x64/models/dna_r10.4.1_e8.2_400bps_hac@v5.0.0"
mod_base = "B"
kmer_table_path = "models/remora/9mer_10-4-1.tsv"
```

#### Train on the sample training subset

The `BS_Train_subset` directory contains reads with the `B` UBP context, and
`AT_Train_subset` is the matched canonical comparison set. Both use the same
reference because the `B` in the FASTA marks the position used for chunking and
model training.

```bash
python xenoquant.py train \
    -w output/sample_training/BS_vs_AT \
    -f SAMPLE_DATA/Training_Testing/pod5/BS_Train_subset \
       SAMPLE_DATA/Training_Testing/pod5/AT_Train_subset \
    -r SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta \
       SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta
```

The trained model is written to:

```text
output/sample_training/BS_vs_AT/model/model_best.pt
```

#### Test on held-out subsets

Run the trained model against the held-out `BS` and `AT` subsets. This is a
quick functional test of model inference on data that was not used for training.

```bash
python xenoquant.py basecall \
    -w output/sample_testing/BS_Test_subset \
    -f SAMPLE_DATA/Training_Testing/pod5/BS_Test_subset \
    -r SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta \
    -m output/sample_training/BS_vs_AT/model/model_best.pt

python xenoquant.py basecall \
    -w output/sample_testing/AT_Test_subset \
    -f SAMPLE_DATA/Training_Testing/pod5/AT_Test_subset \
    -r SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta \
    -m output/sample_training/BS_vs_AT/model/model_best.pt
```

Per-read predictions are written under each testing output directory in
`remora_outputs/per-read_modifications.tsv`.

#### Basecall the PCR sample dataset

After training a model, apply it to the PCR POD5 subset with the PCR reference:

```bash
python xenoquant.py basecall \
    -w output/sample_pcr/B24_B25 \
    -f SAMPLE_DATA/PCR/pod5 \
    -r SAMPLE_DATA/PCR/references/REF_B24_B25.fasta \
    -m output/sample_training/BS_vs_AT/model/model_best.pt
```

The PCR reference includes multiple B24/B25 amplicon sequences with the `B`
position marked for reference-localized basecalling.

#### Optional PCR demultiplexing and analysis

The PCR sample includes barcode-pair metadata for cutadapt demultiplexing:

```bash
python lib/xr_demux.py \
    output/sample_pcr/B24_B25 \
    SAMPLE_DATA/PCR/references/DEMUX_B24_B25.csv
```

Then summarize raw basecall classes:

```bash
python lib/xr_raw_basecall_analysis.py output/sample_pcr/B24_B25 True
```

Demultiplexed per-read calls and summary tables are written under:

```text
output/sample_pcr/B24_B25/demux/
output/sample_pcr/B24_B25/raw_basecall_analysis/
```

### Training

The `train` command builds a model from two nanopore datasets:

1. Reads containing the UBP substitution
2. Reads containing the canonical DNA comparison

Each dataset requires a reference FASTA file that contains the UBP base abbreviation in the sequence so the model focus position can be defined.

#### Required inputs
- Desired output directory 
- FAST5 or POD5 directory containing UBP substitution
- FAST5 or POD5 directory containing canonical DNA comparison 
- Reference file (`.fa`) for UBP dataset
- Reference file (`.fa`) for canonical DNA dataset

#### Training workflow

1. Convert FAST5 to POD5 or merge POD5 directory
2. Perform initial basecalling
3. Align reads to the reference
4. Convert FASTA to xFASTA
5. Generate BED files marking UBP positions
6. Generate Remora chunks
7. Merge chunks
8. Train LSTM RNN model

#### Output

Model outputs are written to:

```text
[output_directory]/model/
```

Primary model file:

```text
model_best.pt
```

#### Command

```bash
python xenoquant.py train \
    -w [desired_output_directory] \
    -f [ubp_pod5_directory] [dna_pod5_directory] \
    -r [ubp_reference.fa] [dna_reference.fa]
```

---

### Basecalling

The `basecall` command applies a trained model to new reads.

#### Required inputs

- Desired output directory
- POD5 directory
- Reference FASTA containing UBP positions in the sequence
- Trained model (`.pt`)

#### Processing workflow

1. Convert FAST5 to POD5 or merge POD5 directory
2. Perform initial basecalling
3. Align reads to the reference
4. Convert FASTA to xFASTA
5. Generate BED files marking UBP positions
6. Generate Remora chunks
7. Model inference

#### Outputs

- Preprocessing files (`.pod5`, `.bam`, `.bed`)
- Full run summary
- Per-read TSV results

Per-read results include:

- `read_id`
- alignment position
- reference label (`1 = UBP`, `0 = DNA`)
- predicted class (`1 = UBP`, `0 = DNA`)
- class probabilities

#### Command

```bash
python xenoquant.py basecall \
    -w [output_directory] \
    -f [pod5_directory] \
    -r [reference.fa] \
    -m [model_best.pt]
```

---

## Master Pipeline: `xenoquant_pipe.py`

`xenoquant_pipe.py` provides switch-controlled orchestration of the full workflow.

### Feature switches

- `train_model`
- `basecall_reads`
- `output_alignment_results`
- `cutadapt_demux`
- `raw_basecall_analysis`

### Visualization switches

- `plot_signal_metrics`
- `plot_signal_spaghetti`
- `plot_signal_step`
- `plot_signal_violin`
- `extract_metrics`

Each stage is executed through subprocess calls to the appropriate module. This allows reproducible execution of full workflows without manually invoking each component.

---

## Demultiplexing

Barcode-based demultiplexing is supported using **cutadapt**.

### Inputs

- Working directory
- Barcode pair CSV

### Module

```text
lib/xr_demux.py
```

### Activation

```python
cutadapt_demux = True
```

---

## Raw Basecall Analysis

Performs class-based filtering and summary analysis of basecalling results.

### Module

```text
lib/xr_raw_basecall_analysis.py
```

### Activation

```python
raw_basecall_analysis = True
```

---

## Visualization Suite

Signal-level visualizations are supported for trained or basecalled datasets.

### Modules

- `xr_signal_metrics.py`
- `xr_signal_plot_v2.py`
- `xr_signal_plot_step.py`
- `xr_violin.py`
- `xr_extract_metrics.py`

These modules operate on the working directory and require specification of the UBP base, retrieved from `xr_params.py`.

### Available visualizations

- Signal summary metrics
- Spaghetti plots
- Step-aligned signal plots
- Violin distributions
- Extracted quantitative metrics

---

## Model Characteristics and Limitations

Models are trained on **±50 signal datapoints** surrounding the UBP position defined in the BED file. This corresponds roughly to **±5 to 10 nucleotides** of sequence context, depending on pore chemistry.

Important considerations:

- Models are **sequence-context specific**
- Models do **not** generalize across flow cell chemistries
- Validation on new sequence contexts is recommended
- Remora compatibility enables conversion to other ONT basecallers

---

## xFASTA Format

XenoCall uses **xFASTA** to encode UBP positions in FASTA headers.

### Standard FASTA with UBP

```fasta
>reference_header
ATGGCAACAGGATGABAAGGACGTA
```

### xFASTA format

```fasta
>reference_header+X_POS[B:18]
ATGGCAACAGGATGAGAAGGACGTA
```

In xFASTA:

- The **header** stores the UBP position
- The **sequence** contains the substituted canonical base

### Default substitutions

```text
B → A
S → T
P → G
Z → C
```

Substitution rules are configurable in:

```text
lib/xr_params.py
```

### Allowed UBP abbreviations (default)

```text
B, S, P, Z, D, X
```

### Default pairing rules

```text
B≡S
P≡Z
Ds:Px
```

---

## Parameter Customization

Workflow parameters, default paths, base substitutions, and model settings are configurable in:

```text
lib/xr_params.py
```

---

## Status

XenoCall is under active development and intended for research use.
