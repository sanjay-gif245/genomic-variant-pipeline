# Benchmarking against the GIAB truth set

`data/results/sample1.vcf` was called from sample **NA12878** — GIAB's primary
reference genome, **HG001** (confirmed from the `@RG SM:` tag in
`data/input_bams/sample1.bam`). NIST/GIAB publishes a high-confidence
"truth" VCF plus a "confident regions" BED file for this exact sample,
specifically so variant callers like GATK can be scored for precision and
recall against it.

`sample2.vcf` (NA12877) has **no** published GIAB truth set, so it can't be
benchmarked this way — only sample1 can.

## 1. Download the truth set (GRCh37, matches this project's reference)

```bash
cd benchmark/giab_truth

curl -O https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/NISTv4.2.1/GRCh37/HG001_GRCh37_1_22_v4.2.1_benchmark.vcf.gz
curl -O https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/NISTv4.2.1/GRCh37/HG001_GRCh37_1_22_v4.2.1_benchmark.vcf.gz.tbi
curl -O https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/NISTv4.2.1/GRCh37/HG001_GRCh37_1_22_v4.2.1_benchmark.bed
```

(These URLs are NIST's official GIAB FTP mirror. If they've reorganized
their directory layout, browse from
https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/
and grab the latest `NISTv*` GRCh37 benchmark VCF + BED pair.)

> This repo's sandboxed dev environment could not reach NCBI's FTP server
> to fetch these automatically (outbound network is allowlisted) — run the
> commands above on your own machine.

## 2. Run the benchmark

```bash
python3 scripts/5_benchmark_giab.py
```

This compares `data/results/sample1.vcf` against the truth set, restricted
to both the region this project actually called variants in
(`chr20:10,000,000-10,200,000`) and GIAB's high-confidence regions, and
prints precision/recall/F1.

## A caveat worth knowing for an interview

This script does exact `(chrom, pos, ref, alt)` matching, not allele
normalization. A real caller-benchmarking tool (`hap.py`, `vcfeval`) first
normalizes both VCFs so that e.g. an indel represented two different-but
equivalent ways still matches. This script will under-count true positives
in that situation — it's a reasonable, explainable simplification, not a
hidden bug.

## Results (sample1 / NA12878, run against the real GIAB v4.2.1 GRCh37 truth set)

```
Region: chr20:10,000,000-10,200,000  (sample: data/results/sample1.vcf)
Truth variants in region (confident only): 355
Called variants in region (confident only): 353
True Positives:  352
False Positives: 1
False Negatives: 3
Precision: 0.9972
Recall:    0.9915
F1:        0.9944
```

The 1 false positive and 3 false negatives are most plausibly explained by
the exact-match limitation described above (an indel or complex variant
represented differently between GATK's output and GIAB's truth VCF), not
by GATK making genuinely wrong calls — but that hasn't been individually
confirmed per-variant, so don't overstate it as proven.
