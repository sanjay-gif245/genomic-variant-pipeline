from pyspark.sql import SparkSession
import pyspark.sql.functions as F
import pandas as pd

print("🚀 Booting up Spark Engine for Deep Analysis...")

spark = SparkSession.builder \
    .appName("Genomes_Analytics") \
    .master("local[*]") \
    .getOrCreate()

print("📖 Reading Parquet data from HDFS...")
df = spark.read.parquet("hdfs://localhost:9000/genomics_project/parquet_data/chr22.adam")

print("⚙️ Crunching advanced genomic data...")

# 1. Total Count & Basic Stats (Keep this for the top of the dashboard)
total_mutations = df.count()
common_variants = df.groupBy("referenceAllele").count().orderBy(F.desc("count")).limit(5).toPandas()
common_variants['total_mutations_analyzed'] = total_mutations
common_variants.to_csv("spark_results.csv", index=False)

# 2. NEW: Extract exact mutation locations and DNA swaps
# We pull the Chromosome (contigName), the exact position (start), and what the DNA mutated into
print("🧬 Extracting specific chromosomal anomaly locations...")
locations_df = df.select(
    F.col("referenceName").alias("Chromosome"),
    F.col("start").alias("Position"),
    F.col("referenceAllele").alias("Original_DNA"),
    F.col("alternateAllele").alias("Mutated_DNA")
).limit(100) # Grabbing a sample of 100 specific anomalies

# Save this detailed location data for the web dashboard
locations_df.toPandas().to_csv("mutation_locations.csv", index=False)

print("✅ SUCCESS! Advanced data extracted.")
spark.stop()