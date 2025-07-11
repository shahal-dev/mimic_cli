#!/bin/bash

# ClusterPyXT CLI Demo Workflow
# This script demonstrates the complete workflow for analyzing a galaxy cluster

echo "=== ClusterPyXT CLI Demo Workflow ==="
echo ""

# Step 1: Ensure CIAO is activated
echo "Step 1: Checking CIAO environment..."
if [[ "$CONDA_DEFAULT_ENV" != "ciao" ]]; then
    echo "Error: CIAO environment not activated!"
    echo "Please run: conda activate ciao"
    exit 1
fi
echo "✓ CIAO environment is active"
echo ""

# Step 2: Initialize cluster
echo "Step 2: Initializing cluster configuration..."
python clusterpyxt_cli.py init-cluster A2029_demo
echo ""

# Step 3: Show what user needs to do
echo "Step 3: User manual configuration required"
echo "Edit A2029_demo_cluster_config.ini with:"
echo "  - Chandra observation IDs"
echo "  - Cluster redshift"  
echo "  - Hydrogen column density (nH)"
echo "  - Solar abundance ratio"
echo ""
echo "Example values for A2029:"
echo "  observation_ids = 891, 4977"
echo "  redshift = 0.0767"
echo "  hydrogen_column_density = 0.0348"
echo "  abundance = 0.3"
echo ""

# Step 4: Show data download (but don't actually run it)
echo "Step 4: Data download and processing (Stage 1)"
echo "Command: python clusterpyxt_cli.py download-data -c A2029_demo_cluster_config.ini"
echo "  - Downloads Chandra observations"
echo "  - Performs initial data reprocessing"
echo "  - Creates merged surface brightness maps"
echo "  - Duration: 10 minutes to several hours"
echo ""

# Step 5: Show source removal requirements
echo "Step 5: Source removal preparation (Stage 2)"  
echo "Before running Stage 2, create these files:"
echo "  - sources.reg: Mark point sources to exclude"
echo "  - exclude.reg: Mark regions to exclude from deflaring"
echo ""
echo "Command: python clusterpyxt_cli.py remove-sources -c A2029_demo_cluster_config.ini"
echo ""

# Step 6: Generate response files
echo "Step 6: Generate response files (Stage 3)"
echo "Before running Stage 3, create acisI_region_0.reg files:"
echo "  - Open each acisI_clean.fits file in DS9"
echo "  - Draw small circular regions covering each ACIS-I CCD chip"
echo "  - Save as acisI_region_0.reg in each observation's analysis directory"
echo ""
echo "Command: python clusterpyxt_cli.py generate-responses -c A2029_demo_cluster_config.ini"
echo ""

# Step 7: Crop data
echo "Step 7: Crop data (Stage 4)"
echo "Before running Stage 4, create master crop region:"
echo "  - Open surface brightness map in DS9"
echo "  - Draw box region covering analysis area"
echo "  - Save as master_crop-ciaowcs.reg in combined directory"
echo ""
echo "Command: python clusterpyxt_cli.py crop-data -c A2029_demo_cluster_config.ini"
echo ""

# Step 8: Future steps
echo "Future CLI commands (to be implemented):"
echo "  - python clusterpyxt_cli.py create-bins -c config.ini        (Stage 5)"
echo "  - python clusterpyxt_cli.py fit-spectra -c config.ini        (Spectral fitting)"
echo "  - python clusterpyxt_cli.py make-temperature-map -c config.ini"
echo "  - python clusterpyxt_cli.py make-pressure-map -c config.ini"
echo "  - python clusterpyxt_cli.py find-shocks -c config.ini"
echo ""

echo "=== Demo Complete ==="
echo "Check README_CLI.md for detailed usage instructions." 