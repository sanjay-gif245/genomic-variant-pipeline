"""
Step 1 of the pipeline: mark duplicate reads in each raw BAM file.

Input:  data/input_bams/*.bam        (raw aligned reads, one per sample)
Output: data/output_bams/*_dedup.bam (deduplicated reads)
        data/output_bams/*_metrics.txt (duplicate metrics report)

Uses GATK's MarkDuplicatesSpark, which runs as a local Spark job under the
hood (local[*]) — this is a single-machine run, not a multi-node cluster.
"""

import os
import subprocess
import time
import glob


def main():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    input_dir = os.path.join(project_dir, "data", "input_bams")
    output_dir = os.path.join(project_dir, "data", "output_bams")

    os.makedirs(output_dir, exist_ok=True)

    # Find the GATK jar directly instead of using the wrapper script
    jar_matches = glob.glob(os.path.join(project_dir, "tools", "gatk-4.5.0.0", "gatk-package-*.jar"))
    if not jar_matches:
        raise FileNotFoundError(
            "Could not find a gatk-package-*.jar under tools/gatk-4.5.0.0/. "
            "Download GATK 4.5.0.0 and unzip it there — see README 'Setup'."
        )
    gatk_jar = jar_matches[0]
    print(f"Using GATK jar {gatk_jar}")

    bam_files = [f for f in os.listdir(input_dir) if f.endswith(".bam")]
    print(f"\nFound {len(bam_files)} samples to process.")

    for bam in bam_files:
        sample_name = bam.split(".")[0]
        input_path = os.path.join(input_dir, bam)
        output_path = os.path.join(output_dir, f"{sample_name}_dedup.bam")
        metrics_path = os.path.join(output_dir, f"{sample_name}_metrics.txt")

        print(f"\n--- Starting Preprocessing for {sample_name} ---")
        start_time = time.time()

        # Call Java directly — subprocess list handles spaces in paths safely
        cmd = [
            "java",
            "-Dsamjdk.use_async_io_read_samtools=false",
            "-Dsamjdk.use_async_io_write_samtools=true",
            "-Dsamjdk.use_async_io_write_tribble=false",
            "-Dsamjdk.compression_level=2",
            "-jar", gatk_jar,
            "MarkDuplicatesSpark",
            "-I", input_path,
            "-O", output_path,
            "-M", metrics_path,
            "--conf", "spark.executor.cores=4",
        ]

        try:
            subprocess.run(cmd, check=True)
            elapsed = time.time() - start_time
            print(f"[SUCCESS] {sample_name} preprocessed in {elapsed:.2f} seconds.")
        except subprocess.CalledProcessError:
            print(f"[ERROR] Failed to process {sample_name}. Check the logs.")


if __name__ == "__main__":
    main()
