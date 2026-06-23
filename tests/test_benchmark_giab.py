"""Unit tests for scripts/5_benchmark_giab.py's matching/scoring logic.

These use small synthetic VCF/BED fixtures instead of the real GIAB truth
set, so the precision/recall/F1 math itself is verified independently of
having the (large, separately-downloaded) GIAB files available. See
benchmark/README.md for how to run the script against the real truth set.
"""
import pytest

from _modules import load_script_module

benchmark = load_script_module("5_benchmark_giab.py")


def test_parse_region():
    chrom, start, end = benchmark.parse_region("20:10000000-10200000")
    assert (chrom, start, end) == ("20", 10000000, 10200000)


def test_load_confident_regions_filters_by_chrom_and_strips_chr_prefix(tmp_path):
    bed = tmp_path / "confident.bed"
    bed.write_text(
        "20\t100\t200\n"
        "21\t500\t600\n"      # different chrom, excluded
        "chr20\t300\t400\n"   # chr-prefixed, should still match
    )
    intervals = benchmark.load_confident_regions(str(bed), "20")
    assert intervals == [(100, 200), (300, 400)]


def test_load_confident_regions_missing_file_returns_empty(tmp_path):
    assert benchmark.load_confident_regions(str(tmp_path / "missing.bed"), "20") == []


def test_in_confident_regions_inside_and_outside():
    intervals = [(100, 200), (300, 400)]
    starts = [iv[0] for iv in intervals]
    assert benchmark.in_confident_regions(150, intervals, starts) is True
    assert benchmark.in_confident_regions(250, intervals, starts) is False
    # 1-based pos 201 -> 0-based 200, which is the (excluded) end of [100, 200)
    assert benchmark.in_confident_regions(201, intervals, starts) is False


def test_in_confident_regions_no_intervals_means_unrestricted():
    assert benchmark.in_confident_regions(999999, [], []) is True


def test_load_variants_filters_by_chrom_region_and_skips_no_calls(tmp_path):
    vcf = tmp_path / "q.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\n"
        "20\t150\t.\tA\tG\n"   # inside region
        "20\t999\t.\tC\tT\n"   # outside region
        "21\t150\t.\tA\tG\n"   # wrong chrom
        "20\t160\t.\tA\t.\n"   # no-call alt, skipped
    )
    variants = benchmark.load_variants(str(vcf), "20", 100, 200)
    assert variants == {(150, "A", "G")}


def test_precision_recall_f1_end_to_end(tmp_path):
    """Mirrors main()'s calculation with a hand-checkable synthetic example:
    1 true positive, 1 false positive, 1 false negative -> P=R=F1=0.5."""
    query_vcf = tmp_path / "query.vcf"
    truth_vcf = tmp_path / "truth.vcf"
    bed = tmp_path / "confident.bed"

    query_vcf.write_text(
        "#CHROM\tPOS\tID\tREF\tALT\n"
        "20\t100\t.\tA\tG\n"   # matches truth -> TP
        "20\t200\t.\tC\tT\n"   # not in truth -> FP
        "20\t999\t.\tA\tC\n"   # outside confident region -> excluded
    )
    truth_vcf.write_text(
        "#CHROM\tPOS\tID\tREF\tALT\n"
        "20\t100\t.\tA\tG\n"   # matched above
        "20\t300\t.\tG\tA\n"   # missed by query -> FN
    )
    bed.write_text("20\t0\t500\n")  # covers 100/200/300, not 999

    chrom, start, end = "20", 1, 1000
    intervals = benchmark.load_confident_regions(str(bed), chrom)
    starts = [iv[0] for iv in intervals]

    query = benchmark.load_variants(str(query_vcf), chrom, start, end)
    truth = benchmark.load_variants(str(truth_vcf), chrom, start, end)
    query = {v for v in query if benchmark.in_confident_regions(v[0], intervals, starts)}
    truth = {v for v in truth if benchmark.in_confident_regions(v[0], intervals, starts)}

    tp, fp, fn = query & truth, query - truth, truth - query
    assert (len(tp), len(fp), len(fn)) == (1, 1, 1)

    precision = len(tp) / len(query)
    recall = len(tp) / len(truth)
    f1 = 2 * precision * recall / (precision + recall)

    assert precision == pytest.approx(0.5)
    assert recall == pytest.approx(0.5)
    assert f1 == pytest.approx(0.5)
