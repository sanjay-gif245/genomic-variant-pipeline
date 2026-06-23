"""Unit tests for scripts/4_extract_family_variants.py's VCF parsing."""
from _modules import load_script_module

family = load_script_module("4_extract_family_variants.py")


def test_parse_vcf_extracts_records_and_sample_id(tmp_path):
    vcf = tmp_path / "sample1.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tNA12878\n"
        "20\t10000100\t.\tA\tG\t99.5\tPASS\t.\tGT\t0/1\n"
        "20\t10000200\t.\tC\tCT\t50.2\tPASS\t.\tGT\t1/1\n"
    )
    records = list(family.parse_vcf(str(vcf)))
    assert records == [
        ("20", "10000100", "A", "G", "99.5", "NA12878"),
        ("20", "10000200", "C", "CT", "50.2", "NA12878"),
    ]


def test_parse_vcf_unknown_sample_when_no_chrom_header(tmp_path):
    vcf = tmp_path / "no_header.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n20\t100\t.\tA\tG\t50\n")
    records = list(family.parse_vcf(str(vcf)))
    assert records[0][5] == "UNKNOWN"


def test_parse_vcf_skips_short_lines(tmp_path):
    vcf = tmp_path / "sample.vcf"
    vcf.write_text(
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tNA12877\n"
        "20\t100\t.\tA\n"  # too few columns
        "20\t200\t.\tC\tT\t60\tPASS\t.\tGT\t0/1\n"
    )
    records = list(family.parse_vcf(str(vcf)))
    assert len(records) == 1
    assert records[0][1] == "200"
