# xenoquant

**xenoquant** is a neural network training and analysis pipeline for nanopore sequencing of alternative base pairs (XNAs). It integrates Oxford Nanopore Technologies (ONT) workflows with Remora-based model training, reference-localized XNA detection, demultiplexing, signal-level visualization, and downstream analysis.

The software is organized around two layers:

- **`xenoquant.py`** — core engine for model training and XNA-aware basecalling
- **`xenoquant_pipe.py`** — master orchestration script for training, basecalling, demultiplexing, analysis, and visualization

This software has been tested on ONT **R9.4.1** and **R10.4.1** flow cells (**Flongle** and **MinION**) using **Remora 2.1.3**. This project is under active development.

---

## Overview

xenoquant supports:

- Training Remora-compatible RNN models for XNA detection
- Reference-localized XNA basecalling
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

1. A dataset containing the XNA substitution
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

xenoquant requires:

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

---

## Core CLI: `xenoquant.py`

### Training

The `train` command builds a model from two nanopore datasets:

1. Reads containing the XNA substitution
2. Reads containing the canonical DNA comparison

Each dataset requires a reference FASTA file that contains the XNA base abbreviation in the sequence so the model focus position can be defined.

#### Required inputs
- Desired output directory 
- FAST5 or POD5 directory containing XNA substitution 
- FAST5 or POD5 directory containing canonical DNA comparison 
- Reference file (`.fa`) for XNA dataset
- Reference file (`.fa`) for canonical DNA dataset

#### Training workflow

1. Convert FAST5 to POD5 or merge POD5 directory
2. Perform initial basecalling
3. Align reads to the reference
4. Convert FASTA to xFASTA
5. Generate BED files marking XNA positions
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
    -f [xna_pod5_directory] [dna_pod5_directory] \
    -r [xna_reference.fa] [dna_reference.fa]
```

---

### Basecalling

The `basecall` command applies a trained model to new reads.

#### Required inputs

- Desired output directory
- POD5 directory
- Reference FASTA containing XNA positions in the sequence
- Trained model (`.pt`)

#### Processing workflow

1. Convert FAST5 to POD5 or merge POD5 directory
2. Perform initial basecalling
3. Align reads to the reference
4. Convert FASTA to xFASTA
5. Generate BED files marking XNA positions
6. Generate Remora chunks
7. Model inference

#### Outputs

- Preprocessing files (`.pod5`, `.bam`, `.bed`)
- Full run summary
- Per-read TSV results

Per-read results include:

- `read_id`
- alignment position
- reference label (`1 = XNA`, `0 = DNA`)
- predicted class (`1 = XNA`, `0 = DNA`)
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

These modules operate on the working directory and require specification of the XNA base, retrieved from `xr_params.py`.

### Available visualizations

- Signal summary metrics
- Spaghetti plots
- Step-aligned signal plots
- Violin distributions
- Extracted quantitative metrics

---

## Model Characteristics and Limitations

Models are trained on **±50 signal datapoints** surrounding the XNA position defined in the BED file. This corresponds roughly to **±5 to 10 nucleotides** of sequence context, depending on pore chemistry.

Important considerations:

- Models are **sequence-context specific**
- Models do **not** generalize across flow cell chemistries
- Validation on new sequence contexts is recommended
- Remora compatibility enables conversion to other ONT basecallers

---

## xFASTA Format

xenoquant uses **xFASTA** to encode XNA positions in FASTA headers.

### Standard FASTA with XNA

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

- The **header** stores the XNA position
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

### Allowed XNA abbreviations (default)

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

xenoquant is under active development and intended for research use.
