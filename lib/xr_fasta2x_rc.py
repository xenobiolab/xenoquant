########################################################################
########################################################################
"""
xr_fasta2x_rc.py 

"""
########################################################################
########################################################################

import sys
from typing import List
from xr_params import *

########################################################################
print("Xenoquant [Status] - Initializing Xenoquant...")

########################################################################
# Helpers
########################################################################


def get_confounding_base(base: str, confounding_pairs: List[str]) -> str:
    """Return canonical confounding substitute for a given XNA base."""
    for pair in confounding_pairs:
        mod, can = pair[0], pair[1]
        if base == mod:
            return can
    return base


########################################################################
# Input / Output
########################################################################

if len(sys.argv) != 3:
    sys.exit("[xFASTA] Usage: python xr_fasta2x_rc.py <input.fasta> <output.fasta>")

input_fasta = sys.argv[1]
output_fasta = sys.argv[2]

detected_xfasta_header = False
detected_xna = False

########################################################################
# Conversion
########################################################################

with open(output_fasta, "w") as fout, open(input_fasta, "r") as fin:
    for line in fin:
        if line.startswith(">"):
            header = line.strip()
            if "XPOS[" in header:
                detected_xfasta_header = True
        else:
            seq = line.strip().upper()

            # Detect non-standard bases
            diff = list(set(seq) - set(standard_bases))
            if len(diff) > 0:
                # Handle each XNA type found in sequence
                for xna_base in diff:
                    x_locs = [i for i, c in enumerate(seq) if c == xna_base]

                    # Substitution with canonical base
                    substitution_base = get_confounding_base(xna_base, confounding_pairs)

                    # Prepare header
                    header_x = header + "+XPOS[" + "".join(f"{xna_base}:{pos}-" for pos in x_locs)
                    header_x = header_x[:-1] + "]\n"

                    # Prepare substituted sequence
                    clean_seq = seq.replace(xna_base, substitution_base)

                    fout.write(header_x)
                    fout.write(clean_seq + "\n")

                    if write_gaps:
                        gap_header = header + "+-+_GAP[]\n"
                        gap_seq = seq.replace(xna_base, "-").replace("-", "")
                        fout.write(gap_header)
                        fout.write(gap_seq + "\n")

                detected_xna = True

            elif len(diff) == 0 and write_no_xna_seq:
                fout.write(header + "\n")
                fout.write(seq + "\n")

########################################################################
# Sanity checks
########################################################################

if detected_xfasta_header:
    print("Xenoquant Status - [Error] Fasta input file already in xfasta format")
elif not detected_xna:
    print("Xenoquant Status - [Error] No XNAs detected in fasta input sequence.")
else:
    print("[xFASTA] Conversion complete.")
