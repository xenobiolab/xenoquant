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

**Tested Hardware:**
- Nvidia RTX 3060 (12 GB)
- Intel I7-11700
- 32 GB DDR4 (3200 MHz)
---

## Reproducible Workflow: `xenoquant_pipe.py`

`xenoquant_pipe.py` is the recommended entry point for reproducing analyses.
It wraps training, basecalling, demultiplexing, raw basecall analysis, and
visualization behind a single configuration block and a set of Boolean switches.
After editing the paths and switches at the top of the file, run:

```bash
python xenoquant_pipe.py
```

The script prints each command before execution, making the workflow traceable
while avoiding the need to manually call each lower-level module.

### Included sample data

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

The sample data is intended as a minimal reproducible analysis and smoke test of
the full pipeline. It is smaller than the full datasets used for manuscript
model training.

### Environment and parameters

Before running `xenoquant_pipe.py`, create and activate the environment, then
verify that `lib/xr_params.py` points to your local Dorado binary and model:

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

For reproducibility, record any changes to these training parameters:

```python
mod_base = "B"
can_base = "N"
kmer_context = "4 4"
chunk_context = "50 50"
val_proportion = "0.2"
chunk_num = "500000"
balance_chunks = True
ml_model_path = "models/ConvLSTM_w_ref.py"
```

### Minimal analysis using `xenoquant_pipe.py`

Use the following examples by editing the configuration section at the top of
`xenoquant_pipe.py`, then running `python xenoquant_pipe.py`.

#### 1. Train a sample BS-vs-AT model

The `BS_Train_subset` directory contains reads with the `B` XNA context, and
`AT_Train_subset` is the matched canonical comparison set. Both use the same
reference because the `B` in the FASTA marks the position used for chunking and
model training.

```python
# --- Training paths ---
working_dir = "output/sample_training/BS_vs_AT"
xna_fast5_dir = "SAMPLE_DATA/Training_Testing/pod5/BS_Train_subset"
xna_ref_fasta = "SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta"
dna_fast5_dir = "SAMPLE_DATA/Training_Testing/pod5/AT_Train_subset"
dna_ref_fasta = "SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta"

# --- Master switches ---
train_model              = True
basecall_reads           = False
output_alignment_results = False
cutadapt_demux           = False
raw_basecall_analysis    = False

# --- Visualization switches ---
plot_signal_metrics    = False
plot_signal_spaghetti  = False
plot_signal_step       = False
plot_signal_violin     = False
extract_metrics        = False
```

The trained model is written to:

```text
output/sample_training/BS_vs_AT/model/model_best.pt
```

Training also writes preprocessing files, aligned BAMs, BED files, Remora
chunks, and `validation.log` under `output/sample_training/BS_vs_AT/`.

#### 2. Test the trained model on held-out subsets

Run the trained model against the held-out `BS` and `AT` subsets. This is a
quick functional test of model inference on data that was not used for training.

```python
# --- Basecall paths ---
bc_working_dir = "output/sample_testing/BS_Test_subset"
bc_fast5_dir = "SAMPLE_DATA/Training_Testing/pod5/BS_Test_subset"
bc_xna_ref_fasta = "SAMPLE_DATA/Training_Testing/references/90mer_train_test.fasta"
bc_model_file = "output/sample_training/BS_vs_AT/model/model_best.pt"

# --- Master switches ---
train_model              = False
basecall_reads           = True
output_alignment_results = False
cutadapt_demux           = False
raw_basecall_analysis    = False
```

To test the canonical held-out subset, change `bc_working_dir` to
`output/sample_testing/AT_Test_subset` and `bc_fast5_dir` to
`SAMPLE_DATA/Training_Testing/pod5/AT_Test_subset`, then rerun the pipe.

Per-read predictions are written under each testing output directory in
`remora_outputs/per-read_modifications.tsv`.

#### 3. Basecall, demultiplex, and summarize the PCR sample

After training a model, apply it to the PCR POD5 subset with the PCR reference:

```python
# --- Basecall paths ---
bc_working_dir = "output/sample_pcr/B24_B25"
bc_fast5_dir = "SAMPLE_DATA/PCR/pod5"
bc_xna_ref_fasta = "SAMPLE_DATA/PCR/references/REF_B24_B25.fasta"
barcode_pair_csv = "SAMPLE_DATA/PCR/references/DEMUX_B24_B25.csv"
bc_model_file = "output/sample_training/BS_vs_AT/model/model_best.pt"

# --- Master switches ---
train_model              = False
basecall_reads           = True
output_alignment_results = False
cutadapt_demux           = True
raw_basecall_analysis    = True
```

The PCR reference includes multiple B24/B25 amplicon sequences with the `B`
position marked for reference-localized basecalling. The barcode-pair CSV maps
PCR products to forward and reverse barcode names for cutadapt demultiplexing.

Demultiplexed per-read calls and summary tables are written under:

```text
output/sample_pcr/B24_B25/demux/
output/sample_pcr/B24_B25/raw_basecall_analysis/
```

### Reproducing trained models reported in the paper

The same `xenoquant_pipe.py` workflow is used to reproduce the trained models
reported in the paper. For each reported model or sequence context:

1. Set `working_dir` to a new output directory for that model.
2. Set `xna_fast5_dir` to the full POD5 or FAST5 directory containing the XNA
   training reads.
3. Set `dna_fast5_dir` to the matched canonical DNA training reads.
4. Set `xna_ref_fasta` and `dna_ref_fasta` to the reference FASTA files used for
   that model. The FASTA sequence must contain the XNA base abbreviation at the
   position used for training.
5. Confirm the XNA and canonical labels in `lib/xr_params.py`, especially
   `mod_base`, `can_base`, `confounding_pairs`, `kmer_context`,
   `chunk_context`, `chunk_num`, `val_proportion`, `balance_chunks`,
   `ml_model_path`, and `kmer_table_path`.
6. Set `train_model = True` and all unrelated downstream switches to `False`.
7. Run `python xenoquant_pipe.py`.

Each reproduced model is written to:

```text
[working_dir]/model/model_best.pt
[working_dir]/model/validation.log
```

To reproduce downstream basecalling or PCR analyses from a trained paper model,
set `bc_model_file` to the corresponding `model_best.pt`, set the basecalling
POD5 directory and reference FASTA, then enable `basecall_reads`. Enable
`cutadapt_demux` and `raw_basecall_analysis` when reproducing demultiplexed PCR
summary tables.

## Core CLI: `xenoquant.py`

The commands below expose the lower-level training and basecalling entry points
called by `xenoquant_pipe.py`. They are useful for debugging or running a single
stage manually, but the pipe file is the recommended reproducibility interface.

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
