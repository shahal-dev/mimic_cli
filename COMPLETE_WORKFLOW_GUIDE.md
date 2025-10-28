# ClusterPyXT Complete Workflow Guide

## Prerequisites

**⚠️ CRITICAL: You MUST have CIAO installed and activated before running any commands!**

```bash
# Activate CIAO environment
conda activate ciao
# OR
source /path/to/ciao/bin/ciao.bash

# Verify CIAO is working
python -c "import ciao_contrib; print('CIAO is ready!')"
```

## Complete Pipeline Workflow

### Step 0: Initialize Cluster Configuration

```bash
cd /home/mimic/ClusterPyXT_CLI

# Create a new cluster configuration
python clusterpyxt_cli.py init-cluster A2029

# This creates: A2029_cluster_config.ini
```

**Edit the configuration file** with your cluster's actual values:
```ini
[cluster_info]
name = A2029
observation_ids = 891, 4977, 16233, 16234, 16235  # Your actual ObsIDs
redshift = 0.0767                                  # Your cluster's redshift
hydrogen_column_density = 0.0348                  # nH value
abundance = 0.3                                    # Abundance ratio
signal_to_noise_threshold = 50

[processing]
last_step_completed = 0
parallel_processing = true
num_cpus = 0  # 0 = auto-detect
```

### Step 1: Process Existing Data
```bash
python clusterpyxt_cli.py process-data -c A2029_cluster_config.ini
```
**What it does:**
- Processes existing Chandra observations from the specified data path
- Performs initial data reprocessing
- Creates merged X-ray surface brightness maps
- **Time:** 10 minutes to several hours

### Step 2: Remove Sources
**Manual step required:** Create region files using DS9:
1. Open the merged surface brightness map in DS9
2. Create `sources.reg` - mark point sources to exclude
3. Create `exclude.reg` - mark regions to exclude from deflaring

```bash
python clusterpyxt_cli.py remove-sources -c A2029_cluster_config.ini
```
**What it does:**
- Removes point sources using your region files
- Filters background flares
- Creates clean X-ray maps

### Step 3: Generate Response Files
**Manual step required:** Create ACIS region files:
1. For each observation, open `acisI_clean.fits` in DS9
2. Draw small circular regions (~40 arc seconds) covering each CCD chip
3. Save as `acisI_region_0.reg` in each observation's analysis directory

```bash
python clusterpyxt_cli.py generate-responses -c A2029_cluster_config.ini
```
**What it does:**
- Creates RMF (Response Matrix Files)
- Creates ARF (Auxiliary Response Files)
- Essential for spectral calibration

### Step 4: Crop Data
**Manual step required:** Create master crop region:
1. Open the surface brightness map in DS9
2. Draw a box region covering your analysis area
3. Save as `master_crop-ciaowcs.reg`

```bash
python clusterpyxt_cli.py crop-data -c A2029_cluster_config.ini
```
**What it does:**
- Crops data to your analysis region
- Filters to 0.7-8.0 keV energy range

### Step 5: Create Adaptive Bins
```bash
python clusterpyxt_cli.py create-bins -c A2029_cluster_config.ini
```
**Options:**
- `--resolution 1` (low: 5x5 pixels)
- `--resolution 2` (medium: 3x3 pixels, default)
- `--resolution 3` (high: 1x1 pixels)
- `--num-cpus 4` (specify CPU cores)

**What it does:**
- Creates adaptive circular bins for target S/N ratio
- Generates scale map and region indices
- **Time:** 10+ hours for complex clusters

### Step 6: Fit Spectra
```bash
python clusterpyxt_cli.py fit-spectra -c A2029_cluster_config.ini
```
**Options:**
- `--continue` (resume interrupted fitting)
- `--resolution 2` (match Step 5 resolution)
- `--num-cpus 4` (parallel processing)

**What it does:**
- Performs X-ray spectral fitting on each bin
- Determines temperature and abundance
- **Time:** Many hours to days

### Step 7: Make Temperature Map
```bash
python clusterpyxt_cli.py make-temperature-map -c A2029_cluster_config.ini
```
**Options:**
- `--resolution 2` (match previous steps)
- `--average` (use averaged fits)

**What it does:**
- Creates temperature distribution map
- Generates error maps
- Saves as FITS files

### Step 8: Make Pressure Map
```bash
python clusterpyxt_cli.py make-pressure-map -c A2029_cluster_config.ini
```
**What it does:**
- Combines temperature and density data
- Creates pressure distribution map (P = n*T)

### Step 9: Make Entropy Map
```bash
python clusterpyxt_cli.py make-entropy-map -c A2029_cluster_config.ini
```
**What it does:**
- Creates entropy map (K = T * n^(-2/3))
- Shows thermodynamic state

## Quick Reference Commands

### Check what stage you're on:
```bash
# Look at your config file:
cat A2029_cluster_config.ini | grep last_step_completed
```

### Run with automatic yes to all prompts:
```bash
python clusterpyxt_cli.py process-data -c A2029_cluster_config.ini -y
```

### Get help for any command:
```bash
python clusterpyxt_cli.py process-data --help
```

## Typical Timeline

| Stage | Time Required | Manual Work |
|-------|---------------|-------------|
| Step 1 | 10min - 2hrs | None |
| Step 2 | 30min - 1hr | Create region files |
| Step 3 | 1-2 hrs | Create ACIS regions |
| Step 4 | 30min | Create crop region |
| Step 5 | 10-24 hrs | None |
| Step 6 | 1-7 days | None |
| Step 7-9 | 1-2 hrs each | None |

## Output Files

After completion, you'll have:
- Temperature maps (`*_temperature_map.fits`)
- Pressure maps (`*_pressure_map.fits`) 
- Entropy maps (`*_entropy_map.fits`)
- Error maps (`*_error_map.fits`)
- Spectral fitting results (`*_spec_fits.fits`)

## Troubleshooting

### "CIAO not found"
```bash
conda activate ciao
# or
source /path/to/ciao/bin/ciao.bash
```

### "Previous stages not completed"
The pipeline tracks progress automatically. Complete earlier stages first.

### "Region files not found"
Create the required `.reg` files using DS9 as described in each step.

### Resume interrupted processing
Most stages can be resumed by simply running the same command again. For spectral fitting, use `--continue`. 