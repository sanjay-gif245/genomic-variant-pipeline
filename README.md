# Genomic Variant Analysis Pipeline (Spark + GATK + ClinVar)

**Repo:** [github.com/sanjay-gif245/genomic-variant-pipeline](https://github.com/sanjay-gif245/genomic-variant-pipeline)
**Live demo:** [genomic-variant-pipeline.streamlit.app](https://genomic-variant-pipeline.streamlit.app/) (free tier — first load may take ~20-30s to wake up)

Two linked pieces of work on real public genomic data:

1. **Family variant calling** — GATK4 deduplicates and calls variants from
   two real BAM samples, then a Streamlit dashboard cross-references those
   calls against ClinVar.
2. **Population-scale analysis** — Apache Spark + ADAM process ~1.1M
   variants from the full 1000 Genomes chromosome 22 cohort.

Both pipelines feed one Streamlit app (`app.py`), kept in clearly separated
sections so it's obvious which numbers come from which dataset.

## Datasets

| Sample | Real identity | Role |
|---|---|---|
| `sample1` | **NA12878** | Mother in the Illumina Platinum Genomes / CEPH Utah Pedigree 1463. Also GIAB's primary reference genome, **HG001** — the most heavily benchmarked human genome in the field, with a published high-confidence truth set. |
| `sample2` | **NA12877** | Father in the same pedigree (NA12878's husband). No published GIAB truth set exists for this sample. |

(Confirmed from the `@RG SM:` tag in each BAM header, not assumed.)

- Chromosome 22 cohort VCF: [1000 Genomes Project, phase 3](https://www.internationalgenome.org/) (AWS Open Data), reference build GRCh37.
- BAM samples + reference (`data/reference/20.fa`): [NIST Genome in a Bottle (GIAB)](https://www.nist.gov/programs-projects/genome-bottle) / Illumina Platinum Genomes, GRCh37.

## Pipeline A — family variant calling (GATK)

```
data/input_bams/*.bam
  └─ scripts/1_preprocess.py        GATK MarkDuplicatesSpark (dedup)
       └─ data/output_bams/*_dedup.bam, *_metrics.txt
            └─ scripts/2_variant_calling.py   GATK HaplotypeCaller, region chr20:10,000,000-10,200,000
                 └─ data/results/sample1.vcf, sample2.vcf
                      ├─ scripts/3_generate_dashboard.py  → dashboard/index.html (static Chart.js: SNP/indel + dedup counts)
                      ├─ scripts/4_extract_family_variants.py → family_variants.csv → app.py "This Family's Variants"
                      └─ scripts/5_benchmark_giab.py (sample1/NA12878 only) → precision/recall vs GIAB truth set
```

`MarkDuplicatesSpark` and the Spark session created in step 1 run in
**local mode** (`local[*]`) — single machine, not a multi-node cluster.
HaplotypeCaller itself doesn't use Spark at all.

## Benchmark results (sample1 / NA12878 vs. GIAB truth set)

`scripts/5_benchmark_giab.py` scores GATK's calls for sample1 against
NIST/GIAB's published high-confidence truth set (v4.2.1, GRCh37),
restricted to the 200kb region this project actually calls variants in
(`chr20:10,000,000-10,200,000`):

| Metric | Value |
|---|---|
| Truth variants in region | 355 |
| Called variants in region | 353 |
| True positives | 352 |
| False positives | 1 |
| False negatives | 3 |
| **Precision** | **0.9972** |
| **Recall** | **0.9915** |
| **F1** | **0.9944** |

See `benchmark/README.md` to reproduce this and for the exact-match
(non-normalized) caveat that most likely explains the handful of
false positives/negatives.

## Pipeline B — population-scale analysis (Spark + ADAM)

```
ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz  (1000 Genomes, full chr22, ~1.1M variants)
  └─ ADAM TransformVariants CLI (manual step, not scripted - see below)
       └─ HDFS: hdfs://localhost:9000/genomics_project/parquet_data/chr22.adam
            └─ analyze_dna.py     Spark job: groupBy/count + sample extraction
                 ├─ spark_results.csv        (top reference alleles, total variant count)
                 └─ mutation_locations.csv   (sample of 100 variants)
                      └─ app.py "Population-Scale Variant Statistics"
```

The VCF → Parquet conversion isn't scripted in this repo. It was run by
hand via ADAM's CLI:

```bash
hdfs dfs -put ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz /genomics_project/raw/
./adam-distribution-spark3_2.12-0.36.0/bin/adam-submit -- transformVariants \
    /genomics_project/raw/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz \
    /genomics_project/parquet_data/chr22.adam
```

This Spark job also runs in **local mode**, reading from a single-node
HDFS instance — not a distributed cluster.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt              # streamlit + app.py's runtime deps
pip install -r requirements-pipeline-b.txt    # pyspark, only needed for analyze_dna.py (Pipeline B)
```

`requirements.txt` is scoped to what the deployed dashboard (`app.py`)
actually imports — it never starts a Spark session, it just reads
pre-computed CSVs. PySpark is split into its own file since it's a large
dependency only `analyze_dna.py` needs.

You'll also need, downloaded separately (not in git — see `.gitignore`):

- **Spark 3.3.2** (`spark-3.3.2-bin-hadoop3`) — [downloads page](https://spark.apache.org/downloads.html)
- **ADAM 0.36.0** (`adam-distribution-spark3_2.12-0.36.0`) — [GitHub releases](https://github.com/bigdatagenomics/adam/releases)
- **GATK 4.5.0.0** (`tools/gatk-4.5.0.0`) — [GitHub releases](https://github.com/broadinstitute/gatk/releases)
- A local single-node HDFS instance for Pipeline B (or point `analyze_dna.py` at a local file path instead of `hdfs://...`)

## Running it

```bash
# Pipeline A
python3 scripts/1_preprocess.py
python3 scripts/2_variant_calling.py
python3 scripts/3_generate_dashboard.py
python3 scripts/4_extract_family_variants.py
python3 scripts/5_benchmark_giab.py        # optional, needs the GIAB truth set - see benchmark/README.md

# Pipeline B (needs Spark + HDFS + the ADAM conversion above)
python3 analyze_dna.py

# Dashboard
streamlit run app.py
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/
```

15 unit tests cover the pure data-processing logic in `scripts/3-5`
(SNP/indel classification, VCF parsing, GIAB region/BED matching, and the
precision/recall/F1 calculation) against small synthetic fixtures — no
GATK, Spark, or network access needed, so the suite runs in well under a
second. GitHub Actions (`.github/workflows/tests.yml`) runs it on every
push across Python 3.10 and 3.11.

Scope is deliberately narrow: these tests don't cover `app.py` (a
Streamlit script — not idiomatic to unit test) or the GATK/Spark pipeline
steps themselves, which are checked manually by running the pipeline
end-to-end and diffing the outputs.

## Known limitations

Documented here on purpose, instead of glossed over — these are the
things worth being upfront about if this comes up in an interview.

- **Not actually distributed.** Both Spark jobs run `local[*]` on one
  machine. There's no multi-node cluster, no custom partitioning, no
  executor tuning to speak of.
- **Small called region.** GATK only calls variants in a 200kb window of
  chr20, not the whole genome — large enough to be a believable demo,
  not large enough to actually need Spark/cluster-scale compute on its own.
- **The ClinVar lookup is not a predictive model.** It's a REST call
  against an existing clinical database (ClinVar via MyVariant.info).
- **GIAB benchmarking does exact match, not normalized match.** Tools
  like `hap.py`/`vcfeval` normalize indel representation before comparing;
  `scripts/5_benchmark_giab.py` does plain `(pos, ref, alt)` matching, so
  it will under-count some true positives where GATK and GIAB represent
  the same variant differently.
- **Automated tests cover data-processing logic, not the full pipeline.**
  See "Testing" above — `app.py` and the GATK/Spark steps are still
  checked manually, not via CI.

## Possible extensions

- Run Spark across multiple worker processes/nodes and chart runtime vs.
  executor count — the single most convincing way to demonstrate actually
  understanding distributed computing, rather than just calling Spark's API.
- Deploy `app.py` (e.g., Streamlit Community Cloud) so it's a live link,
  not just code to read.
- Train a real classifier (e.g., on ClinVar-labeled variants) to predict
  pathogenicity — would justify a "predictor" framing for real.
