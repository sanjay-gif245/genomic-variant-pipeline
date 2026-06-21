import os
import subprocess
import time

def main():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ref_path = os.path.join(project_dir, "data", "reference", "20.fa")
    input_dir = os.path.join(project_dir, "data", "output_bams")
    output_dir = os.path.join(project_dir, "data", "results")
    gatk_path = os.path.join(project_dir, "tools", "gatk-4.5.0.0", "gatk")

    # Create results folder if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Find the cleaned BAM files
    dedup_files = [f for f in os.listdir(input_dir) if f.endswith("_dedup.bam")]
    
    print(f"Starting Variant Calling for {len(dedup_files)} samples...")

    for bam in dedup_files:
        sample_name = bam.replace("_dedup.bam", "")
        input_path = os.path.join(input_dir, bam)
        output_vcf = os.path.join(output_dir, f"{sample_name}.vcf")
        
        print(f"\n>>> Calling variants for: {sample_name}")
        start_time = time.time()

        # GATK command for HaplotypeCaller
        cmd = [
            "python3", gatk_path, "HaplotypeCaller",
            "-R", ref_path,
            "-I", input_path,
            "-O", output_vcf,
            "-L", "20:10000000-10200000"  # Focus on the region we downloaded
        ]

        try:
            subprocess.run(cmd, check=True)
            elapsed = time.time() - start_time
            print(f"[SUCCESS] Created {sample_name}.vcf in {elapsed:.2f} seconds.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Variant calling failed for {sample_name}.")

if __name__ == "__main__":
    main()
