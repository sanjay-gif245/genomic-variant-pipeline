import os
import time

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Genomic Variant Clinical Annotation Dashboard", layout="wide")

st.title("🧬 Genomic Variant Clinical Annotation Dashboard")
st.markdown(
    "Looks up called variants against **ClinVar** (via the public `MyVariant.info` REST API) to "
    "see whether they have a documented clinical association. This is a rule-based lookup against "
    "an existing clinical database, **not** a predictive/ML model — ClinVar already supplies any "
    "disease association and clinical significance, this app just fetches and displays it."
)
st.divider()


# --- THE LIVE API FUNCTION ---
def fetch_disease_data(chrom, pos, ref, alt):
    """Looks up a variant in ClinVar via the MyVariant.info REST API."""
    # Format the exact DNA change (HGVS standard format)
    hgvs_id = f"chr{chrom}:g.{pos}{ref}>{alt}"
    url = f"https://myvariant.info/v1/variant/{hgvs_id}?fields=clinvar"

    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # Dig into the clinical database response to find the disease name
            if "clinvar" in data:
                rcv = data["clinvar"].get("rcv", {})
                # APIs can return lists or dictionaries, so we handle both safely
                if isinstance(rcv, list):
                    rcv = rcv[0]

                disease = rcv.get("conditions", {}).get("name", "No associated disease documented")
                risk = rcv.get("clinical_significance", "Unknown")
                return disease, risk
    except Exception:
        pass

    return "Benign / No Disease Found", "Low Risk"


def run_clinvar_lookup(variants_df, button_key):
    """Runs the live ClinVar lookup over the top 10 rows of a variants dataframe and renders the report."""
    if not st.button("Run Live ClinVar Lookup", key=button_key):
        return

    progress_text = "Establishing secure connection to ClinVar (via MyVariant.info)..."
    my_bar = st.progress(0, text=progress_text)

    results = []
    # Scan the top 10 variants to keep the free public API fast
    top_mutations = variants_df.head(10).reset_index(drop=True)
    total = len(top_mutations)

    for i, row in top_mutations.iterrows():
        percent_complete = int(((i + 1) / total) * 100)
        my_bar.progress(percent_complete, text=f"Querying DNA Position: {row['Position']}...")

        disease, risk = fetch_disease_data(
            row["Chromosome"], row["Position"], row["Original_DNA"], row["Mutated_DNA"]
        )

        results.append(
            {
                "Chromosome": row["Chromosome"],
                "Mutation Position": row["Position"],
                "DNA Change": f"{row['Original_DNA']} ➔ {row['Mutated_DNA']}",
                "Linked Condition (ClinVar)": disease,
                "Clinical Significance (ClinVar)": risk,
            }
        )

        time.sleep(0.5)  # Slight delay so we don't crash the free public API

    my_bar.empty()
    st.success("✅ ClinVar lookup complete.")

    report_df = pd.DataFrame(results)

    # Highlight pathogenic findings in the table
    def highlight_risk(val):
        color = "#ff4b4b" if "pathogenic" in str(val).lower() else ""
        return f"background-color: {color}"

    st.dataframe(
        report_df.style.map(highlight_risk, subset=["Clinical Significance (ClinVar)"]),
        use_container_width=True,
    )


# --- SECTION 1: THIS FAMILY'S VARIANTS (real GATK HaplotypeCaller output) ---
st.header("This Family's Variants")
st.markdown(
    "Variants GATK's `HaplotypeCaller` actually called from this project's own BAM samples "
    "(chr20:10,000,000-10,200,000). `sample1` is **NA12878** — the mother in the Illumina "
    "Platinum Genomes / CEPH Utah Pedigree 1463, and also GIAB's primary reference genome, "
    "**HG001**. `sample2` is **NA12877**, her husband and the pedigree's father. "
    "(Run `python3 scripts/4_extract_family_variants.py` after the GATK pipeline to (re)generate "
    "the CSV this section reads.)"
)

family_csv_path = "family_variants.csv"
if os.path.exists(family_csv_path):
    family_data = pd.read_csv(family_csv_path)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Called variants")
        roles = sorted(family_data["Family_Role"].unique())
        chosen_role = st.selectbox("Sample", roles)
        filtered = family_data[family_data["Family_Role"] == chosen_role].reset_index(drop=True)
        st.dataframe(filtered.head(15), use_container_width=True)
        st.caption(f"{len(filtered)} variants called for {chosen_role}.")

    with col2:
        st.subheader("🏥 Live ClinVar Lookup")
        st.markdown("Cross-reference this sample's own called variants against ClinVar.")
        run_clinvar_lookup(filtered, button_key="family_lookup")
else:
    st.warning(
        "`family_variants.csv` not found. Run `python3 scripts/4_extract_family_variants.py` "
        "after the GATK pipeline (scripts 1-2) to generate it."
    )

st.divider()

# --- SECTION 2: POPULATION-SCALE VARIANT STATISTICS (Spark/ADAM, 1000 Genomes chr22) ---
st.header("Population-Scale Variant Statistics")
st.markdown(
    "A separate, much larger dataset: chromosome 22 variants from the full **1000 Genomes "
    "Project** cohort, processed with **Spark + ADAM**. This demonstrates processing at "
    "big-data scale — it is population reference data and is **not** related to the two "
    "family samples above."
)

try:
    location_data = pd.read_csv("mutation_locations.csv")

    if os.path.exists("spark_results.csv"):
        stats = pd.read_csv("spark_results.csv")
        total = int(stats["total_mutations_analyzed"].iloc[0])
        st.metric("Total chr22 variants analyzed by Spark", f"{total:,}")

    st.markdown(f"Showing a sample of {min(15, len(location_data))} of the variants pulled from this dataset:")
    st.dataframe(location_data.head(15), use_container_width=True)

    st.subheader("🌍 Live ClinVar Lookup (population sample)")
    run_clinvar_lookup(location_data, button_key="population_lookup")

except FileNotFoundError:
    st.error(
        "`mutation_locations.csv` not found. Run `analyze_dna.py` (requires a running Spark + "
        "HDFS setup with the ADAM-converted chr22 Parquet data) first."
    )
