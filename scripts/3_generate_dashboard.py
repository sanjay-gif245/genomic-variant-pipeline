import os

def analyze_variants(vcf_path):
    """Reads the VCF file and categorizes mutations into SNPs and Indels"""
    snps = 0
    indels = 0
    try:
        with open(vcf_path, 'r') as f:
            for line in f:
                if not line.startswith('#'):
                    # Split the line into columns (tab-separated)
                    columns = line.strip().split('\t')
                    if len(columns) > 4:
                        ref_dna = columns[3]
                        alt_dna = columns[4]
                        
                        # If both are 1 letter long, it's a simple swap (SNP)
                        if len(ref_dna) == 1 and len(alt_dna) == 1:
                            snps += 1
                        else:
                            # Otherwise, letters were added or removed (Indel)
                            indels += 1
    except FileNotFoundError:
        print(f"Warning: Could not find {vcf_path}")
    return snps, indels

def get_duplicates(metrics_path):
    try:
        with open(metrics_path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith("LIBRARY"):
                    return int(lines[i+1].split('\t')[6])
    except Exception:
        return 0
    return 0

def main():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("Analyzing Genomic Variants...")
    
    # 1. Extract and Categorize Data
    snp1, indel1 = analyze_variants(os.path.join(project_dir, "data", "results", "sample1.vcf"))
    snp2, indel2 = analyze_variants(os.path.join(project_dir, "data", "results", "sample2.vcf"))
    dup1 = get_duplicates(os.path.join(project_dir, "data", "output_bams", "sample1_metrics.txt"))
    dup2 = get_duplicates(os.path.join(project_dir, "data", "output_bams", "sample2_metrics.txt"))
    
    print(f"Mother -> SNPs: {snp1}, Indels: {indel1}")
    print(f"Father -> SNPs: {snp2}, Indels: {indel2}")
    
    # 2. Generate the Upgraded HTML Dashboard
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Genomic Variant Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #fff; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; margin-bottom: 30px; padding-bottom: 20px; }}
        h1 {{ color: #4CAF50; margin: 0; }}
        .container {{ display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; }}
        .card {{ background: #1e1e1e; padding: 20px; border-radius: 10px; width: 45%; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }}
        h3 {{ text-align: center; color: #e0e0e0; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .spark-stats {{ background-color: #2c3e50; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 30px; }}
        .spark-stats span {{ font-weight: bold; color: #f39c12; font-size: 1.2em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Genomic Variant Analysis</h1>
        <p>Distributed Bio-Informatics Pipeline</p>
    </div>
    
    <div class="spark-stats">
        <h2>Biological Target: Human Chromosome 20 (GRCh37)</h2>
        <p>Total Variants Discovered: <span>Sample 1: {snp1 + indel1}</span> | <span>Sample 2: {snp2 + indel2}</span></p>
    </div>

    <div class="container">
        <div class="card">
            <h3>Variant Classification: SNPs vs Indels</h3>
            <p style="text-align:center; font-size:0.9em; color:#aaa;">Displays the specific types of genetic mutations found in the DNA.</p>
            <canvas id="typeChart"></canvas>
        </div>

        <div class="card">
            <h3>Spark Preprocessing: Duplicates Filtered</h3>
            <p style="text-align:center; font-size:0.9em; color:#aaa;">Shows the volume of sequencing errors removed by the distributed cluster.</p>
            <canvas id="dupChart"></canvas>
        </div>
    </div>

    <script>
        // Chart 1: The Biological Data (Stacked Bar)
        new Chart(document.getElementById('typeChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: ['Sample 1 (Mother)', 'Sample 2 (Father)'],
                datasets: [
                    {{ label: 'SNPs (Single Letter Change)', data: [{snp1}, {snp2}], backgroundColor: '#4CAF50' }},
                    {{ label: 'Indels (Insertions/Deletions)', data: [{indel1}, {indel2}], backgroundColor: '#FFC107' }}
                ]
            }},
            options: {{ scales: {{ x: {{ stacked: true }}, y: {{ stacked: true }} }} }}
        }});

        // Chart 2: The IT/Big Data Metrics
        new Chart(document.getElementById('dupChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: ['Sample 1 (Mother)', 'Sample 2 (Father)'],
                datasets: [{{ label: 'Duplicate Reads Removed', data: [{dup1}, {dup2}], backgroundColor: '#36a2eb' }}]
            }}
        }});
    </script>
</body>
</html>"""

    # 3. Save the file
    dashboard_path = os.path.join(project_dir, "dashboard", "index.html")
    with open(dashboard_path, "w") as f:
        f.write(html_content)
    print(f"[SUCCESS] Biological Dashboard generated at {dashboard_path}")

if __name__ == "__main__":
    main()
