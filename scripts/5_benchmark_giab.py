"""
Step 5 (optional): benchmark GATK's variant calls for sample1 (NA12878 /
GIAB HG001) against the NIST/GIAB high-confidence truth set.

This is a deliberately simple, dependency-free stand-in for tools like
hap.py/vcfeval: it does exact (chrom, pos, ref, alt) matching rather than
allele normalization, and only counts a variant if it falls inside both
the region this project actually called variants in AND GIAB's confident
regions. See benchmark/README.md for where to download the truth set and
for the normalization caveat.

Usage:
    python3 scripts/5_benchmark_giab.py
    python3 scripts/5_benchmark_giab.py --truth-vcf path/to/truth.vcf.gz \\
        --confident-bed path/to/confident.bed --query-vcf data/results/sample1.vcf
"""

import argparse
import bisect
import gzip
import os


def open_maybe_gzip(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "r")


def parse_region(region_str):
    """Parses 'chrom:start-end' (1-based, inclusive) into (chrom, start, end)."""
    chrom, span = region_str.split(":")
    start, end = span.split("-")
    return chrom, int(start), int(end)


def load_confident_regions(bed_path, chrom):
    """Returns a sorted list of (start, end) 0-based half-open intervals for one chromosome."""
    intervals = []
    if not bed_path or not os.path.exists(bed_path):
        return intervals
    with open_maybe_gzip(bed_path) as f:
        for line in f:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            cols = line.rstrip("\n").split("\t")
            bed_chrom = cols[0].lstrip("chr")
            if bed_chrom != chrom.lstrip("chr"):
                continue
            intervals.append((int(cols[1]), int(cols[2])))
    intervals.sort()
    return intervals


def in_confident_regions(pos, intervals, starts):
    """1-based pos falls inside a 0-based half-open [start, end) interval."""
    if not intervals:
        # No BED supplied - don't restrict (caller should be aware of this).
        return True
    i = bisect.bisect_right(starts, pos - 1) - 1
    if i < 0:
        return False
    start, end = intervals[i]
    return start <= pos - 1 < end


def load_variants(vcf_path, chrom, region_start, region_end):
    """Returns a set of (pos, ref, alt) tuples for variants inside [region_start, region_end]."""
    variants = set()
    with open_maybe_gzip(vcf_path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            vcf_chrom = cols[0].lstrip("chr")
            if vcf_chrom != chrom.lstrip("chr"):
                continue
            pos = int(cols[1])
            if not (region_start <= pos <= region_end):
                continue
            ref, alt_field = cols[3], cols[4]
            for alt in alt_field.split(","):
                if alt in (".", "<NON_REF>"):
                    continue
                variants.add((pos, ref, alt))
    return variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-vcf", default="data/results/sample1.vcf",
                         help="GATK output to score (default: data/results/sample1.vcf, NA12878).")
    parser.add_argument("--truth-vcf", default="benchmark/giab_truth/HG001_GRCh37_1_22_v4.2.1_benchmark.vcf.gz",
                         help="GIAB high-confidence truth VCF for the same sample.")
    parser.add_argument("--confident-bed", default="benchmark/giab_truth/HG001_GRCh37_1_22_v4.2.1_benchmark_noinconsistent.bed",
                         help="GIAB high-confidence regions BED file.")
    parser.add_argument("--region", default="20:10000000-10200000",
                         help="Region this project actually called variants in (chrom:start-end, 1-based).")
    args = parser.parse_args()

    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_dir)

    if not os.path.exists(args.truth_vcf):
        print(f"[MISSING] {args.truth_vcf} not found.")
        print("Download the GIAB truth set first - see benchmark/README.md for exact URLs.")
        return
    if not os.path.exists(args.query_vcf):
        print(f"[MISSING] {args.query_vcf} not found. Run scripts/1-2 first.")
        return

    chrom, start, end = parse_region(args.region)

    confident_intervals = load_confident_regions(args.confident_bed, chrom)
    confident_starts = [iv[0] for iv in confident_intervals]
    if not confident_intervals:
        print(f"[WARN] No confident-regions BED found at {args.confident_bed} - "
              f"comparing without restricting to GIAB's high-confidence regions. "
              f"Results will be less reliable; see benchmark/README.md.")

    query = load_variants(args.query_vcf, chrom, start, end)
    truth = load_variants(args.truth_vcf, chrom, start, end)

    query = {v for v in query if in_confident_regions(v[0], confident_intervals, confident_starts)}
    truth = {v for v in truth if in_confident_regions(v[0], confident_intervals, confident_starts)}

    tp = query & truth
    fp = query - truth
    fn = truth - query

    precision = len(tp) / len(query) if query else 0.0
    recall = len(tp) / len(truth) if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"Region: chr{chrom}:{start:,}-{end:,}  (sample: {args.query_vcf})")
    print(f"Truth variants in region (confident only): {len(truth)}")
    print(f"Called variants in region (confident only): {len(query)}")
    print(f"True Positives:  {len(tp)}")
    print(f"False Positives: {len(fp)}")
    print(f"False Negatives: {len(fn)}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")


if __name__ == "__main__":
    main()
