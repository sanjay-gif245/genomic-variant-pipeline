"""
Step 4: extract the variants GATK actually called for each family sample into
one dashboard-friendly CSV. This is what connects the GATK variant-calling
pipeline (steps 1-2) to the Streamlit dashboard's "This Family's Variants"
section, instead of that section showing unrelated population data.

Input:  data/results/sample1.vcf, data/results/sample2.vcf
        (produced by scripts/2_variant_calling.py)
Output: family_variants.csv

sample1 = NA12878 ("Mother" in the Illumina Platinum Genomes / CEPH Utah
          Pedigree 1463 - also GIAB's primary reference genome, HG001).
sample2 = NA12877 ("Father" in the same pedigree, NA12878's husband).
(Confirmed from the @RG SM: tags in data/input_bams/*.bam.)
"""

import os
import csv

SAMPLE_ROLES = {
    "sample1": "Mother (NA12878 / GIAB HG001)",
    "sample2": "Father (NA12877)",
}


def parse_vcf(vcf_path):
    """Yields (chrom, pos, ref, alt, qual, sample_id) for each variant record in a VCF."""
    sample_id = "UNKNOWN"
    with open(vcf_path) as f:
        for line in f:
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                header = line.rstrip("\n").split("\t")
                if len(header) > 9:
                    sample_id = header[9]
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 6:
                continue
            chrom, pos, _id, ref, alt, qual = cols[0], cols[1], cols[2], cols[3], cols[4], cols[5]
            yield chrom, pos, ref, alt, qual, sample_id


def main():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    results_dir = os.path.join(project_dir, "data", "results")
    out_path = os.path.join(project_dir, "family_variants.csv")

    rows = []
    for sample_key, role in SAMPLE_ROLES.items():
        vcf_path = os.path.join(results_dir, f"{sample_key}.vcf")
        if not os.path.exists(vcf_path):
            print(f"[WARN] {vcf_path} not found, skipping.")
            continue
        count = 0
        for chrom, pos, ref, alt, qual, sample_id in parse_vcf(vcf_path):
            rows.append({
                "Family_Role": role,
                "Sample_ID": sample_id,
                "Chromosome": chrom,
                "Position": pos,
                "Original_DNA": ref,
                "Mutated_DNA": alt,
                "Quality": qual,
            })
            count += 1
        print(f"[OK] {sample_key} ({role}): {count} variants")

    if not rows:
        raise SystemExit(
            "No variants found - run scripts/1_preprocess.py and scripts/2_variant_calling.py first."
        )

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[SUCCESS] Wrote {len(rows)} variants for {len(SAMPLE_ROLES)} samples to {out_path}")


if __name__ == "__main__":
    main()
