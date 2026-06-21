import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="Genomics Disease Predictor", layout="wide")

st.title("🧬 Pediatric Genomic Disease Predictor")
st.markdown("**Live Clinical Database Connection:** Ping `MyVariant.info` REST API")
st.divider()

# --- THE LIVE API FUNCTION ---
def fetch_disease_data(chrom, pos, ref, alt):
    """Pings the live medical database to find diseases linked to a mutation."""
    # Format the exact DNA change (HGVS standard format)
    hgvs_id = f"chr{chrom}:g.{pos}{ref}>{alt}"
    url = f"https://myvariant.info/v1/variant/{hgvs_id}?fields=clinvar"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # Dig into the clinical database response to find the disease name
            if 'clinvar' in data:
                rcv = data['clinvar'].get('rcv', {})
                # APIs can return lists or dictionaries, so we handle both safely
                if isinstance(rcv, list):
                    rcv = rcv[0]
                    
                disease = rcv.get('conditions', {}).get('name', 'No associated disease documented')
                risk = rcv.get('clinical_significance', 'Unknown')
                return disease, risk
    except Exception as e:
        pass
    
    return "Benign / No Disease Found", "Low Risk"

# --- MAIN DASHBOARD ---
try:
    # Load the raw mutation locations your Spark engine found
    location_data = pd.read_csv("mutation_locations.csv")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Child's Raw Genetic Anomalies")
        st.markdown("These are the exact chromosomal mutations extracted by the Spark Hadoop engine.")
        st.dataframe(location_data.head(15), use_container_width=True) # Show top 15 for speed
        
    with col2:
        st.subheader("🏥 Live Clinical Disease Scan")
        st.markdown("Cross-reference the child's mutations with global disease databases.")
        
        if st.button("Run Live API Disease Prediction"):
            # Create an empty box to show live progress
            progress_text = "Establishing secure connection to Clinical API..."
            my_bar = st.progress(0, text=progress_text)
            
            results = []
            
            # Scan the top 10 most critical mutations to keep the API fast
            top_mutations = location_data.head(10)
            total = len(top_mutations)
            
            for index, row in top_mutations.iterrows():
                # Update progress bar
                percent_complete = int(((index + 1) / total) * 100)
                my_bar.progress(percent_complete, text=f"Querying DNA Position: {row['Position']}...")
                
                # Hit the live API
                disease, risk = fetch_disease_data(row['Chromosome'], row['Position'], row['Original_DNA'], row['Mutated_DNA'])
                
                results.append({
                    "Chromosome": row['Chromosome'],
                    "Mutation Position": row['Position'],
                    "DNA Change": f"{row['Original_DNA']} ➔ {row['Mutated_DNA']}",
                    "Predicted Disease": disease,
                    "Clinical Risk": risk
                })
                
                time.sleep(0.5) # Slight delay so we don't crash the free medical API
                
            my_bar.empty() # Clear the loading bar when done
            
            # Display the final Medical Report
            st.success("✅ Clinical API Scan Complete.")
            
            # Convert to a clean table
            report_df = pd.DataFrame(results)
            
            # Highlight high-risk diseases in the table
            def highlight_risk(val):
                color = '#ff4b4b' if 'pathogenic' in str(val).lower() else ''
                return f'background-color: {color}'
                
            st.dataframe(report_df.style.applymap(highlight_risk, subset=['Clinical Risk']), use_container_width=True)

except FileNotFoundError:
    st.error("Spark data not found. Please run the Big Data engine first.")