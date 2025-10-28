# ClusterPyXT CLI - Command Line Interface

A streamlined, GUI-free version of ClusterPyXT for automated X-ray cluster analysis using Chandra observations.

## Prerequisites

1. **CIAO 4.14+** must be installed with full CALDB
2. **Python 3.8+** (included with CIAO)
3. Required Python packages (typically included with CIAO):
   - astropy
   - numpy  
   - matplotlib
   - configparser

## Setup

1. **Activate CIAO environment** (REQUIRED before running any commands):
   ```bash
   conda activate ciao
   ```

2. **Make the script executable**:
   ```bash
   chmod +x clusterpyxt_cli.py
   ```

## Usage Workflow

### Step 1: Initialize Cluster Configuration

Create a new cluster configuration template:

```bash
python clusterpyxt_cli.py init-cluster A2029
```

This creates `A2029_cluster_config.ini` with the following template:

```ini
[cluster_info]
name = A2029
observation_ids = # Comma-separated list of Chandra ObsIDs
redshift = # Cluster redshift (e.g., 0.055)
hydrogen_column_density = # nH in 10^22 cm^-2 (e.g., 0.0348)
abundance = # Solar abundance ratio (typically 0.3)
signal_to_noise_threshold = 50

[processing]
last_step_completed = 0
parallel_processing = true
num_cpus = 0  # 0 = auto-detect
```

### Step 2: Edit Configuration File

Fill in your cluster's information. Example:

```ini
[cluster_info]
name = A2029
observation_ids = 891, 4977, 16233, 16234, 16235
redshift = 0.0767
hydrogen_column_density = 0.0348
abundance = 0.3
signal_to_noise_threshold = 50

[processing]
last_step_completed = 0
parallel_processing = true
num_cpus = 0  # 0 = auto-detect
```

**Where to find values:**
- **observation_ids**: [Chandra Data Archive](https://cda.harvard.edu/chaser/)
- **redshift**: [NASA/IPAC Extragalactic Database (NED)](https://ned.ipac.caltech.edu)
- **hydrogen_column_density (nH)**: [NASA HEASARC nH Tool](https://heasarc.gsfc.nasa.gov/cgi-bin/Tools/w3nh/w3nh.pl)
- **abundance**: Usually 0.3 (check literature for specific clusters)

### Step 3: Download and Process Data (Stage 1)

```bash
python clusterpyxt_cli.py process-data -c A2029_cluster_config.ini
```

This will:
- Download all Chandra observations
- Perform initial data reprocessing  
- Create merged X-ray surface brightness maps
- Can take 10 minutes to several hours depending on data size

#### Technical Details - Stage 1 Functions:

**Main Functions:**
- `ciao.run_stage_1()` → calls `download_data()` + `merge_observations()`

**Download Process (`download_data()`):**
- `download_chandra_obsids()` **[CIAO]** - Downloads raw Chandra data from archive
- Uses parallel processing (multiprocessing.Pool) for multiple ObsIDs

**Data Processing (`merge_observations()`):**
- `chandra_repro()` **[CIAO]** - CIAO tool for data reprocessing and calibration
- `ccd_sort()` - Custom function to separate data by CCD chip
  - `dmcopy()` **[CIAO]** - CIAO tool for copying and filtering data
  - `dmkeypar()` **[CIAO]** - CIAO tool for reading FITS header keywords
- `ciao_back()` - Background processing
  - `acis_bkgrnd_lookup()` **[CIAO]** - CIAO tool to find appropriate background files  
  - `reproject_events()` **[CIAO]** - CIAO tool to reproject background data
  - `acis_process_events()` **[CIAO]** - CIAO tool for event processing
- `actually_merge_observations_from()` - Merges multiple observations
  - `merge_obs()` **[CIAO]** - CIAO tool for merging observations
  - `fluximage()` **[CIAO]** - CIAO tool for creating flux images

**Output:** Merged X-ray surface brightness map ready for source identification

### Step 4: Remove Sources (Stage 2)

Before running Stage 2, you need to manually create region files:

1. **Create sources.reg**: Open the merged surface brightness map and mark point sources to exclude
2. **Create exclude.reg**: Mark regions to exclude from background flare filtering

Then run:
```bash
python clusterpyxt_cli.py remove-sources -c A2029_cluster_config.ini
```

#### Technical Details - Stage 2 Functions:

**Main Functions:**
- `ciao.run_stage_2()` → calls `sources_and_light_curves()` + `make_nosrc_xray_sb()` + `lightcurves_with_exclusion()`

**Source Detection and Removal:**
- `find_sources()` - Automated source detection (if enabled)
  - `mkpsfmap()` **[CIAO]** - Creates point spread function map
  - `wavdetect()` **[CIAO]** - CIAO source detection algorithm
- `remove_sources_from_observation()` - Removes user-defined sources
  - Uses sources.reg file to exclude point sources
- `copy_image_excluding_region()` - Custom function using region masks

**Light Curve Generation and Filtering:**
- `generate_light_curve()` - Creates background light curves
  - `dmextract()` **[CIAO]** - CIAO tool for extracting spectra/light curves
  - `deflare()` **[CIAO]** - CIAO tool for filtering background flares
- `lightcurves_with_exclusion()` - Filters high-energy events using exclude.reg

**Background Processing:**
- Uses exclude.reg to preserve cluster emission during deflaring
- Parallel processing support for multiple observations

**Output:** Clean X-ray surface brightness map with sources removed and background flares filtered

### Step 5: Generate Response Files (Stage 3)

Before running Stage 3, create ACIS region files for each observation:

1. **Create acisI_region_0.reg for each observation**: Open each `acisI_clean.fits` file in DS9
2. **Draw small circular regions** covering each ACIS-I CCD chip (~40 arc seconds)
3. **Save as acisI_region_0.reg** in each observation's analysis directory

Then run:
```bash
python clusterpyxt_cli.py generate-responses -c A2029_cluster_config.ini
```

This generates RMF (Response Matrix Files) and ARF (Auxiliary Response Files) needed for spectral calibration.

#### Technical Details - Stage 3 Functions:

**Main Functions:**
- `ciao.run_stage_3()` → calls `make_response_files_in_parallel()`

**Response File Generation:**
- `create_global_response_file_for()` - Creates response files for each observation
  - `mkarf()` **[CIAO]** - Creates Auxiliary Response Files (ARF)
  - `mkrmf()` **[CIAO]** - Creates Response Matrix Files (RMF)
  - `mkgrmf()` **[CIAO]** - Alternative RMF creation for grating data
- `make_pcad_lis()` - Creates aspect solution file lists
- Requires acisI_region_0.reg files covering each CCD chip

**Calibration Process:**
- RMF files contain detector response as function of energy
- ARF files contain effective area and quantum efficiency
- Essential for converting observed counts to physical units
- Uses CALDB (Calibration Database) for instrument responses

**Parallel Processing:**
- `do_function_on_observations_in_parallel()` - Processes multiple observations simultaneously
- Significantly reduces processing time for multi-observation clusters

**Output:** Calibrated response files enabling accurate spectral analysis

### Step 6: Crop Data (Stage 4)

Before running Stage 4, create the master crop region:

1. **Open the surface brightness map**: `ds9 [cluster_dir]/main_output/[cluster]_xray_surface_brightness_nosrc.fits`
2. **Draw a box region** covering your analysis area
3. **Save as master_crop-ciaowcs.reg** in the combined directory

Then run:
```bash
python clusterpyxt_cli.py crop-data -c A2029_cluster_config.ini
```

This filters data to 0.7-8.0 keV energy range and crops to your analysis region.

#### Technical Details - Stage 4 Functions:

**Main Functions:**
- `ciao.run_stage_4()` → calls `stage_4()` function

**Data Cropping and Filtering:**
- `make_energy_filtered_image()` - Filters to 0.7-8.0 keV X-ray band
  - `dmcopy()` **[CIAO]** - CIAO tool with energy filtering: `[energy=700:8000]`
  - Optimal energy range for cluster thermal emission
- `make_energy_filtered_background()` - Applies same energy filter to backgrounds
- `copy_image_cropping_region()` - Crops images using master_crop-ciaowcs.reg
  - `dmcopy()` **[CIAO]** - CIAO tool with spatial filtering

**Image Processing:**
- `make_acisI_and_back()` - Creates final processed images for each observation
- `create_combined_images()` - Combines cropped observations
- `make_cumulative_mask()` - Creates analysis masks
- `reproject_image()` **[CIAO]** - Reprojects images to common coordinate system

**Quality Control:**
- Checks for dimension mismatches between observations
- Handles pixel boundary issues in region cropping
- Validates consistent image sizes across observations

**Output:** Energy-filtered, cropped data ready for adaptive binning and spectral analysis

### Step 7: Create Adaptive Bins (Stage 5)

```bash
python clusterpyxt_cli.py create-bins -c A2029_cluster_config.ini
```

Creates adaptive circular bins to achieve uniform signal-to-noise ratio across the cluster.

⚠️ **WARNING:** This stage is computationally intensive and can take 10+ hours for large clusters.

Optional parameters:
- `--num-cpus N` - Specify number of CPU cores (default: all available)
- `--resolution {1,2,3}` - Set resolution (1=low, 2=medium, 3=high, default: 2)
- `--yes` - Skip confirmation prompt

This stage produces the adaptive circular binning maps needed for spectral fitting.

#### Technical Details - Stage 5 Functions:

**Main Functions:**
- `ciao.run_stage_5()` → calls `acb.fitting_preparation()`

**Adaptive Circular Binning (`acb.fitting_preparation()`):**
- `fast_acb_creation_parallel()` - Creates scale map showing optimal bin sizes
  - `binary_search_radii()` - Custom algorithm to find radii achieving target S/N
  - `generate_acb_scale_map_for()` - Parallel generation of scale map
  - Target signal-to-noise ratio typically 40-80 counts per bin
- `create_scale_map_region_index()` - Creates region index map for fitting
- `prepare_efftime_circle_parallel()` - Prepares high-energy images
- `calculate_effective_times_in_parallel_map()` - Calculates exposure corrections
- `create_circle_regions_in_parallel()` - Creates DS9 regions for spectral extraction
- `prepare_for_spec()` - Finalizes preparation for spectral fitting

**Core Algorithm:**
- Adaptive binning ensures uniform statistical quality across cluster
- Smaller bins in high surface brightness regions (cluster center)
- Larger bins in low surface brightness regions (cluster outskirts)
- Uses binary search to optimize bin sizes for target S/N

**Scientific Purpose:**
- Enables spatially-resolved spectroscopy with uniform statistical errors
- Preserves spatial resolution where photon statistics allow
- Optimizes trade-off between spatial and spectral resolution

**Output:** Scale map, region indices, exposure corrections, and fitting regions ready for spectral analysis

### Step 8: Spectral Fitting (Stage 6)

```bash
python clusterpyxt_cli.py fit-spectra -c A2029_cluster_config.ini
```

Performs X-ray spectral fitting on each adaptive circular bin to determine physical properties.

⚠️ **WARNING:** This stage is extremely computationally intensive and can take many hours to days depending on the number of regions and resolution.

Optional parameters:
- `--num-cpus N` - Specify number of CPU cores (default: all available)
- `--resolution {1,2,3}` - Set resolution (1=low, 2=medium, 3=high, default: 2)
- `--continue` - Continue from previous incomplete run
- `--yes` - Skip confirmation prompt

This stage performs the actual scientific analysis, fitting thermal plasma models to determine temperature, abundance, and density.

#### Technical Details - Stage 6 Functions:

**Main Functions:**
- `ciao.run_stage_spectral_fits()` → calls `spectral.calculate_spectral_fits()`

**Spectral Fitting Process (`spectral.calculate_spectral_fits()`):**
- `cluster.scale_map_regions_to_fit()` - Identifies regions for spectral analysis
- `cluster.fit_region_number()` - Fits thermal plasma model to each region
  - Uses XSPEC **[XSPEC]** for spectral fitting (via CIAO)
  - `specextract()` **[CIAO]** - Extracts spectra from circular regions
  - `sherpa.fit()` **[SHERPA]** - Performs χ² minimization fitting
  - Models: APEC (thermal plasma), absorption (wabs/phabs)
- Parallel processing using multiprocessing.Process for efficiency
- `cluster.initialize_best_fits_file()` - Creates output files for results

**Scientific Models:**
- **Thermal Plasma Model**: APEC model for hot cluster gas
- **Photoelectric Absorption**: Galactic nH column density
- **Free Parameters**: Temperature (kT), abundance (Z), normalization
- **Fixed Parameters**: Redshift, hydrogen column density

**Quality Control:**
- Automatic bad fit detection and flagging
- Statistical uncertainty estimation using Sherpa
- Continue capability for interrupted long runs
- Fit quality assessment (χ²/dof, parameter uncertainties)

**Parallel Strategy:**
- Regions divided into batches for CPU cores
- Each process fits multiple regions independently
- Progress tracking with time estimates
- Memory management for large datasets

**Output:** Best-fit parameters for temperature map generation and physical analysis

### Step 9: Temperature Map Creation (Stage 7)

```bash
python clusterpyxt_cli.py make-temperature-map -c A2029_cluster_config.ini
```

Creates temperature distribution maps from spectral fitting results.

Optional parameters:
- `--resolution {1,2,3}` - Set resolution (1=low, 2=medium, 3=high, default: 2)
- `--average` - Use averaged temperature fits instead of individual fits
- `--yes` - Skip confirmation prompt

This stage converts the spectral fitting results into spatial temperature maps.

#### Technical Details - Stage 7 Functions:

**Main Functions:**
- `acb.make_temperature_map()` - Creates temperature distribution maps

**Temperature Map Creation Process:**
- Loads spectral fitting results from Stage 6
- Maps temperature fits to spatial coordinates using region indices
- Creates temperature distribution map with error propagation
- Generates three output maps:
  - **Temperature map**: Spatial distribution of gas temperature (keV)
  - **Error map**: Statistical uncertainties on temperature measurements
  - **Fractional error map**: Relative uncertainties for quality assessment

**Resolution Options:**
- **High (3)**: 1x1 pixel binning - highest spatial resolution
- **Medium (2)**: 3x3 pixel binning - good balance of resolution and S/N
- **Low (1)**: 5x5 pixel binning - smoothest maps with best statistics

**Scientific Products:**
- FITS files compatible with ds9, CASA, Python analysis
- World coordinate system (WCS) headers for proper astrometry  
- Ready for publication-quality figures and scientific analysis

**Output:** Temperature maps enabling cluster thermodynamics analysis

### Step 10: Pressure Map Creation

```bash
python clusterpyxt_cli.py make-pressure-map -c A2029_cluster_config.ini
```

Creates pressure distribution maps combining temperature and density information.

#### Technical Details - Pressure Map Functions:

**Main Functions:**
- `acb.make_pressure_map()` - Creates pressure distribution maps

**Pressure Map Creation Process:**
- `get_matching_density_and_temperature_maps()` - Loads and matches T and n maps
- `make_density_map()` - Creates density map from X-ray surface brightness (n ∝ √SB)
- `make_sizes_match()` - Ensures coordinate system compatibility
- Calculates pressure: **P = n × T** (proportional to gas pressure)
- `do.normalize_data()` - Normalizes pressure distribution

**Scientific Significance:**
- **Pressure gradients** reveal gravitational potential and gas dynamics
- **Pressure substructure** indicates mergers, shocks, and turbulence
- **Hydrostatic equilibrium** analysis for cluster mass determination
- **Shock detection** through pressure discontinuities

**Output:** Pressure maps for thermodynamic and dynamical analysis

### Step 11: Entropy Map Creation

```bash
python clusterpyxt_cli.py make-entropy-map -c A2029_cluster_config.ini
```

Creates entropy distribution maps showing thermodynamic history.

#### Technical Details - Entropy Map Functions:

**Main Functions:**
- `acb.make_entropy_map()` - Creates entropy distribution maps

**Entropy Map Creation Process:**
- Loads temperature and density maps
- Calculates entropy: **K = T × n^(-2/3)** (specific entropy)
- Handles zero-density regions with proper masking
- Normalizes entropy distribution for visualization

**Scientific Significance:**
- **Entropy profiles** reveal heating and cooling history
- **Low entropy** indicates condensed, recently shocked gas
- **High entropy** shows gas heated by AGN feedback or mergers
- **Entropy gradients** trace gas flows and mixing processes

**Astrophysical Applications:**
- AGN feedback signatures
- Merger shock identification  
- Cool core vs non-cool core classification
- Cluster formation history reconstruction

**Output:** Entropy maps for cluster evolution analysis

## Command Reference

### Available Commands

| Command | Description | Stage |
|---------|-------------|-------|
| `init-cluster <name>` | Create cluster configuration template | Setup |
| `process-data -c <config>` | Process existing Chandra data | 1 |
| `remove-sources -c <config>` | Remove point sources and filter flares | 2 |
| `generate-responses -c <config>` | Generate RMF and ARF response files | 3 |
| `crop-data -c <config>` | Crop to analysis region and filter energy | 4 |
| `create-bins -c <config>` | Create adaptive circular bins and scale map | 5 |
| `fit-spectra -c <config>` | Perform spectral fitting on adaptive bins | 6 |
| `make-temperature-map -c <config>` | Create temperature map from spectral fits | 7 |
| `make-pressure-map -c <config>` | Create pressure map from T and density | - |
| `make-entropy-map -c <config>` | Create entropy map from T and density | - |

### Common Options

- `-c, --config-file`: Path to cluster configuration file
- `-y, --yes`: Skip confirmation prompts (useful for automation)
- `--help`: Show help for any command

### Examples

```bash
# Get help
python clusterpyxt_cli.py --help
python clusterpyxt_cli.py process-data --help

# Initialize cluster
python clusterpyxt_cli.py init-cluster Coma

# Run stages with custom config path
python clusterpyxt_cli.py process-data -c /path/to/custom_config.ini

# Skip confirmation prompts
python clusterpyxt_cli.py process-data -c A2029_cluster_config.ini --yes

# Generate response files
python clusterpyxt_cli.py generate-responses -c A2029_cluster_config.ini

# Crop data to analysis region
python clusterpyxt_cli.py crop-data -c A2029_cluster_config.ini

# Create adaptive circular bins (Stage 5)
python clusterpyxt_cli.py create-bins -c A2029_cluster_config.ini --num-cpus 8

# Perform spectral fitting (Stage 6)
python clusterpyxt_cli.py fit-spectra -c A2029_cluster_config.ini --resolution 2 --num-cpus 8

# Continue interrupted spectral fitting
python clusterpyxt_cli.py fit-spectra -c A2029_cluster_config.ini --continue

# Create temperature map (Stage 7)
python clusterpyxt_cli.py make-temperature-map -c A2029_cluster_config.ini --resolution 2

# Create scientific maps
python clusterpyxt_cli.py make-pressure-map -c A2029_cluster_config.ini
python clusterpyxt_cli.py make-entropy-map -c A2029_cluster_config.ini
```

## File Structure

After initialization and Stage 1, your directory structure will look like:

```
ClusterPyXT_CLI/
├── clusterpyxt_cli.py           # Main CLI script
├── A2029_cluster_config.ini     # Your cluster config
├── [data_directory]/            # Set in pypeline_config.ini
│   └── A2029/                   # Cluster directory
│       ├── 891/                 # Individual observation dirs
│       ├── 4977/
│       ├── combined/            # Merged data products
│       ├── sources.reg          # You create this for Stage 2
│       └── exclude.reg          # You create this for Stage 2
```

## Environment Requirements

**Always run with CIAO activated:**
```bash
conda activate ciao
python clusterpyxt_cli.py <command>
```

**Check CIAO is working:**
```bash
conda activate ciao
python -c "import ciao_contrib; print('CIAO available')"
```

## Differences from GUI Version

1. **No PyQt5 dependency** - pure command line interface
2. **INI-based configuration** - no interactive cluster setup
3. **Explicit stage commands** - clear separation of pipeline stages  
4. **Meaningful command names** - `process-data` instead of generic "Stage 1"
5. **Better error handling** - clearer error messages and validation

## Complete Implementation Status

✅ **The CLI now implements the full ClusterPyXT scientific pipeline!**

**Core Pipeline (Stages 1-7):**
- ✅ Stage 1: Download and process Chandra data
- ✅ Stage 2: Remove point sources and filter background
- ✅ Stage 3: Generate RMF/ARF response files
- ✅ Stage 4: Crop data and filter energy  
- ✅ Stage 5: Create adaptive circular bins
- ✅ Stage 6: Perform spectral fitting
- ✅ Stage 7: Create temperature maps

**Scientific Map Generation:**
- ✅ Temperature distribution maps
- ✅ Pressure maps (P = n×T)
- ✅ Entropy maps (K = T×n^(-2/3))

**Advanced Features (Future):**
- `find-shocks -c <config>` (Shock detection and analysis)
- `profile-analysis -c <config>` (Radial profile fitting)
- `mass-estimation -c <config>` (Hydrostatic mass calculation)

## Troubleshooting

**Import errors**: Make sure CIAO environment is activated
```bash
conda activate ciao
```

**Permission errors**: Ensure you have write access to data directory (set in `pypeline_config.ini`)

**Missing observations**: Check ObsIDs are correct and publicly available

**Configuration errors**: Validate all required fields are filled in your config file 