# Genomic Variant Analysis Pipeline (Spark + GATK + ClinVar)

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
pip install -r requirements.txt
```

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
- **No automated tests.** Coverage is manual (`py_compile`, a `streamlit
  run` smoke test, and a synthetic-truth-set dry run of the benchmark
  script — see git log for details).

## Possible extensions

- Run Spark across multiple worker processes/nodes and chart runtime vs.
  executor count — the single most convincing way to demonstrate actually
  understanding distributed computing, rather than just calling Spark's API.
- Deploy `app.py` (e.g., Streamlit Community Cloud) so it's a live link,
  not just code to read.
- Train a real classifier (e.g., on ClinVar-labeled variants) to predict
  pathogenicity — would justify a "predictor" framing for real.
- Re-run `scripts/5_benchmark_giab.py` with the actual GIAB truth set
  downloaded and report the real precision/recall numbers here.
