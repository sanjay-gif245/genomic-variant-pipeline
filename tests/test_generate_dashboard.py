"""Unit tests for scripts/3_generate_dashboard.py's variant-classification logic."""
from _modules import load_script_module

dashboard = load_script_module("3_generate_dashboard.py")


def test_analyze_variants_counts_snps_and_indels(tmp_path):
    vcf = tmp_path / "sample.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\n"
        "20\t100\t.\tA\tG\t50\n"    # SNP
        "20\t200\t.\tC\tT\t60\n"    # SNP
        "20\t300\t.\tA\tATG\t40\n"  # indel (insertion)
        "20\t400\t.\tGTT\tG\t40\n"  # indel (deletion)
    )
    snps, indels = dashboard.analyze_variants(str(vcf))
    assert snps == 2
    assert indels == 2


def test_analyze_variants_ignores_short_lines(tmp_path):
    vcf = tmp_path / "sample.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "20\t100\t.\tA\n"          # too few columns, should be skipped
        "20\t200\t.\tC\tT\t60\n"   # valid SNP
    )
    snps, indels = dashboard.analyze_variants(str(vcf))
    assert (snps, indels) == (1, 0)


def test_analyze_variants_missing_file_returns_zero(tmp_path):
    missing = tmp_path / "does_not_exist.vcf"
    snps, indels = dashboard.analyze_variants(str(missing))
    assert (snps, indels) == (0, 0)


def test_get_duplicates_parses_real_gatk_metrics_format(tmp_path):
    # Mirrors the actual MarkDuplicatesSpark metrics layout used in this
    # project (see data/output_bams/sample1_metrics.txt): the duplicate
    # count we want is READ_PAIR_DUPLICATES, column index 6.
    metrics = tmp_path / "metrics.txt"
    metrics.write_text(
        "## htsjdk.samtools.metrics.StringHeader\n"
        "# MarkDuplicatesSpark --output ...\n"
        "## METRICS CLASS\torg.broadinstitute.hellbender...\n"
        "LIBRARY\tUNPAIRED_READS_EXAMINED\tREAD_PAIRS_EXAMINED\t"
        "SECONDARY_OR_SUPPLEMENTARY_RDS\tUNMAPPED_READS\t"
        "UNPAIRED_READ_DUPLICATES\tREAD_PAIR_DUPLICATES\t"
        "READ_PAIR_OPTICAL_DUPLICATES\tPERCENT_DUPLICATION\t"
        "ESTIMATED_LIBRARY_SIZE\n"
        "Solexa-272222\t593\t66025\t0\t593\t111\t8613\t4545\t0.130704\t443848\n"
    )
    assert dashboard.get_duplicates(str(metrics)) == 8613


def test_get_duplicates_missing_file_returns_zero(tmp_path):
    assert dashboard.get_duplicates(str(tmp_path / "nope.txt")) == 0
