#!/usr/bin/env python3
"""
ClusterPyXT CLI - Command Line Interface for X-ray Cluster Analysis
Version: 1.414.0a CLI

A streamlined command-line version of ClusterPyXT for automated X-ray cluster analysis.
"""

import sys
import argparse
import os
import configparser
from pathlib import Path

import pypeline_io as io
import cluster
import ciao
import acb
import spectral
from errors import ClusterPyError

# Check for CIAO availability
try:
    import ciao_contrib
except ImportError or ModuleNotFoundError:
    print("ERROR: Failed to import CIAO python scripts.")
    print("CIAO must be running prior to starting this script!")
    print("Please activate your CIAO environment and try again.")
    sys.exit(ClusterPyError.ciao_not_running)


def create_cluster_config_template(cluster_name: str, output_path: str = None):
    """Create a template cluster configuration INI file."""
    if output_path is None:
        output_path = f"{cluster_name}_cluster_config.ini"
    
    config = configparser.ConfigParser()
    config['cluster_info'] = {
        'name': cluster_name,
        'observation_ids': '# Comma-separated list of Chandra ObsIDs',
        'redshift': '# Cluster redshift (e.g., 0.055)',
        'hydrogen_column_density': '# nH in 10^22 cm^-2 (e.g., 0.0348)',
        'abundance': '# Solar abundance ratio (typically 0.3)',
        'signal_to_noise_threshold': '50'
    }
    
    config['processing'] = {
        'last_step_completed': '0',
        'parallel_processing': 'true',
        'num_cpus': '0  # 0 = auto-detect'
    }
    
    with open(output_path, 'w') as configfile:
        config.write(configfile)
    
    print(f"Created cluster configuration template: {output_path}")
    print("Please edit this file with your cluster's specific values before proceeding.")
    return output_path


def load_cluster_from_config(config_file: str) -> cluster.ClusterObj:
    """Load cluster configuration from INI file."""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    try:
        cluster_info = config['cluster_info']
        
        # Parse observation IDs
        obsids_str = cluster_info['observation_ids'].strip()
        if obsids_str.startswith('#'):
            raise ValueError("observation_ids must be filled out (remove # and add actual ObsIDs)")
        obsids = [id.strip() for id in obsids_str.split(',')]
        
        # Parse other required fields
        name = cluster_info['name'].strip()
        redshift = float(cluster_info['redshift'])
        nH = float(cluster_info['hydrogen_column_density'])
        abundance = float(cluster_info['abundance'])
        sn_threshold = int(cluster_info.get('signal_to_noise_threshold', '50'))
        
        # Get processing info
        processing = config['processing'] if 'processing' in config else {}
        last_step = int(processing.get('last_step_completed', '0'))
        
        print(f"Loading cluster: {name}")
        print(f"  ObsIDs: {', '.join(obsids)}")
        print(f"  Redshift: {redshift}")
        print(f"  nH: {nH} × 10²² cm⁻²")
        print(f"  Abundance: {abundance}")
        
        # Create cluster object
        cluster_obj = cluster.ClusterObj(
            name=name,
            observation_ids=obsids,
            hydrogen_column_density=nH,
            redshift=redshift,
            abundance=abundance,
            last_step_completed=last_step,
            signal_to_noise=sn_threshold
        )
        
        return cluster_obj
        
    except KeyError as e:
        raise ValueError(f"Missing required configuration key: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid configuration value: {e}")


def cmd_init_cluster(args):
    """Initialize a new cluster configuration."""
    print("Initializing new cluster configuration...")
    
    if args.config_file:
        config_path = args.config_file
    else:
        config_path = f"{args.name}_cluster_config.ini"
    
    # Create template
    template_path = create_cluster_config_template(args.name, config_path)
    
    print(f"\nNext steps:")
    print(f"1. Edit the configuration file: {template_path}")
    print(f"2. Fill in your cluster's observation IDs, redshift, nH, and abundance")
    print(f"3. Run: clusterpyxt_cli.py download-data -c {template_path}")


def cmd_download_data(args):
    """Download and perform initial processing of Chandra observations (Stage 1)."""
    print("=== ClusterPyXT Stage 1: Download and Initial Processing ===")
    
    # Load cluster configuration
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"\nStarting data download and initial processing for cluster: {cluster_obj.name}")
    print(f"This will download {len(cluster_obj.observation_ids)} Chandra observations and perform initial processing.")
    
    if not args.yes:
        response = input("Continue? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    # Run Stage 1
    try:
        print("\n--- Starting Stage 1 ---")
        ciao.run_stage_1(cluster_obj)
        ciao.finish_stage_1(cluster_obj)
        
        # Update configuration file
        cluster_obj.last_step_completed = 1
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Stage 1 completed successfully!")
        print(f"✓ Downloaded and processed {len(cluster_obj.observation_ids)} observations")
        print(f"✓ Created merged X-ray surface brightness map")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py remove-sources -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Stage 1 failed: {e}")
        sys.exit(1)


def cmd_remove_sources(args):
    """Remove point sources and filter background flares (Stage 2)."""
    print("=== ClusterPyXT Stage 2: Source Removal and Background Filtering ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"For Stage 2, you need to create region files:")
    print(f"1. sources.reg - regions around point sources to exclude")
    print(f"2. exclude.reg - regions to exclude from deflaring process")
    print(f"\nThese should be saved in: {cluster_obj.directory}")
    
    # Check for required files
    sources_file = os.path.join(cluster_obj.directory, "sources.reg")
    exclude_file = os.path.join(cluster_obj.directory, "exclude.reg")
    
    if not os.path.exists(sources_file):
        print(f"✗ Missing: {sources_file}")
        return
    if not os.path.exists(exclude_file):
        print(f"✗ Missing: {exclude_file}")
        return
    
    print("✓ Found required region files")
    
    if not args.yes:
        response = input("Continue with Stage 2? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Starting Stage 2 ---")
        ciao.run_stage_2(cluster_obj)
        ciao.finish_stage_2(cluster_obj)
        
        cluster_obj.last_step_completed = 2
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Stage 2 completed successfully!")
        print(f"✓ Removed point sources and filtered background flares")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py generate-responses -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Stage 2 failed: {e}")
        sys.exit(1)


def cmd_generate_responses(args):
    """Generate response matrix (RMF) and auxiliary response (ARF) files (Stage 3)."""
    print("=== ClusterPyXT Stage 3: Generate Response Files ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"For Stage 3, you need to create acisI_region_0.reg files for each observation.")
    print(f"These files should contain small circular regions covering each ACIS-I CCD chip.")
    print(f"Typical size: ~40 arc seconds (larger circles = longer runtime)")
    
    # Check for required files
    missing_files = []
    for obs in cluster_obj.observations:
        region_file = obs.acisI_region_0_filename
        if not os.path.exists(region_file):
            missing_files.append(f"ObsID {obs.id}: {region_file}")
    
    if missing_files:
        print(f"\n✗ Missing acisI_region_0.reg files:")
        for missing_file in missing_files:
            print(f"  {missing_file}")
        print(f"\nCreate these files by opening the respective acisI_clean.fits files in DS9:")
        for obs in cluster_obj.observations:
            print(f"  ds9 {obs.clean}")
        print(f"Draw small circular regions covering each CCD and save as acisI_region_0.reg")
        return
    
    print(f"✓ Found all required region files for {len(cluster_obj.observations)} observations")
    
    if not args.yes:
        response = input("Continue with Stage 3? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Starting Stage 3 ---")
        ciao.run_stage_3(cluster_obj, args)
        ciao.finish_stage_3(cluster_obj)
        
        cluster_obj.last_step_completed = 3
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Stage 3 completed successfully!")
        print(f"✓ Generated RMF and ARF files for spectral calibration")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py crop-data -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Stage 3 failed: {e}")
        sys.exit(1)


def cmd_crop_data(args):
    """Crop data to region of interest and filter energy range (Stage 4)."""
    print("=== ClusterPyXT Stage 4: Data Cropping and Energy Filtering ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"For Stage 4, you need to create a master_crop-ciaowcs.reg file.")
    print(f"This file should contain a box region defining the analysis area.")
    print(f"Open the surface brightness file and draw a box around your region of interest:")
    print(f"  ds9 {cluster_obj.xray_surface_brightness_nosrc_filename}")
    print(f"\nSave the region file as: {cluster_obj.master_crop_file}")
    
    # Check for required file
    if not os.path.exists(cluster_obj.master_crop_file):
        print(f"\n✗ Missing: {cluster_obj.master_crop_file}")
        print(f"Create this file using DS9 with a box region covering your analysis area.")
        return
    
    print(f"✓ Found master crop region file")
    
    if not args.yes:
        response = input("Continue with Stage 4? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Starting Stage 4 ---")
        print("Filtering data to 0.7-8.0 keV energy range and cropping to analysis region...")
        
        ciao.run_stage_4(cluster_obj, args)
        ciao.finish_stage_4(cluster_obj)
        
        cluster_obj.last_step_completed = 4
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Stage 4 completed successfully!")
        print(f"✓ Cropped data to analysis region")
        print(f"✓ Filtered data to 0.7-8.0 keV energy range")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py create-bins -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Stage 4 failed: {e}")
        print(f"Note: If you get dimension mismatch errors, try redrawing the crop region")
        print(f"to avoid splitting pixels between observations.")
        sys.exit(1)


def cmd_create_bins(args):
    """Create adaptive circular bins and scale map (Stage 5)."""
    print("=== ClusterPyXT Stage 5: Adaptive Circular Binning ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"Stage 5 creates adaptive circular bins to achieve target signal-to-noise ratio.")
    print(f"This stage calculates:")
    print(f"  - Scale map showing optimal bin sizes")
    print(f"  - Region index maps for spectral fitting")
    print(f"  - Exposure corrections for each region")
    print(f"  - Circular fitting regions")
    print(f"\nThis can take a long time (~10+ hours for complex clusters)")
    
    # Check if previous stages completed
    if cluster_obj.last_step_completed < 4:
        print(f"\n✗ Previous stages not completed. Current stage: {cluster_obj.last_step_completed}")
        print(f"Please complete Stages 1-4 before running Stage 5.")
        return
    
    print(f"✓ Previous stages completed (Stage {cluster_obj.last_step_completed})")
    
    if not args.yes:
        response = input("Continue with Stage 5 (this may take many hours)? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    # Set number of CPUs
    num_cpus = args.num_cpus if args.num_cpus > 0 else None
    if num_cpus:
        print(f"Using {num_cpus} CPU cores for parallel processing")
    else:
        print("Using all available CPU cores for parallel processing")
    
    try:
        print("\n--- Starting Stage 5: Adaptive Circular Binning ---")
        print("This stage includes multiple sub-processes:")
        print("  1. Creating scale map (adaptive bin sizing)")
        print("  2. Creating region index map")
        print("  3. Preparing high-energy images")
        print("  4. Calculating effective exposure times")
        print("  5. Creating circular fitting regions")
        print("  6. Preparing spectral fitting files")
        
        # Use args object to pass parameters
        if not hasattr(args, 'resolution'):
            args.resolution = 2  # Default medium resolution
        
        ciao.run_stage_5(cluster_obj, args, num_cpus=num_cpus)
        ciao.finish_stage_5(cluster_obj)
        
        cluster_obj.last_step_completed = 5
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Stage 5 completed successfully!")
        print(f"✓ Created adaptive circular bins with S/N = {cluster_obj.signal_to_noise}")
        print(f"✓ Generated scale map and region indices")
        print(f"✓ Calculated exposure corrections")
        print(f"✓ Prepared {cluster_obj.number_of_regions} regions for spectral fitting")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py fit-spectra -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Stage 5 failed: {e}")
        print(f"Note: Stage 5 is computationally intensive and may require significant time and memory.")
        sys.exit(1)


def cmd_fit_spectra(args):
    """Perform spectral fitting on adaptive circular bins (Stage 6)."""
    print("=== ClusterPyXT Stage 6: Spectral Fitting ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"Stage 6 performs X-ray spectral fitting on each adaptive circular bin.")
    print(f"This stage fits thermal plasma models to determine:")
    print(f"  - Temperature distribution across the cluster")
    print(f"  - Metal abundance patterns")
    print(f"  - Gas density normalization")
    print(f"  - Statistical uncertainties")
    print(f"\nThis can take many hours depending on number of regions and resolution")
    
    # Check if previous stages completed
    if cluster_obj.last_step_completed < 5:
        print(f"\n✗ Previous stages not completed. Current stage: {cluster_obj.last_step_completed}")
        print(f"Please complete Stages 1-5 before running spectral fitting.")
        return
    
    print(f"✓ Previous stages completed (Stage {cluster_obj.last_step_completed})")
    
    # Check for required files
    regions_to_fit = []
    try:
        if hasattr(cluster_obj, 'scale_map_regions_to_fit'):
            regions_to_fit = cluster_obj.scale_map_regions_to_fit(args.resolution)
        else:
            print(f"Warning: Cannot determine regions to fit")
    except Exception as e:
        print(f"Warning: Could not calculate regions to fit: {e}")
    
    if regions_to_fit:
        print(f"✓ Found {len(regions_to_fit)} regions to fit at resolution {args.resolution}")
    else:
        print(f"✓ Stage 5 completed - ready for spectral fitting")
    
    if not args.yes:
        estimated_hours = max(1, len(regions_to_fit) // 50) if regions_to_fit else "several"
        response = input(f"Continue with spectral fitting (estimated ~{estimated_hours} hours)? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    # Set number of CPUs
    num_cpus = args.num_cpus if args.num_cpus > 0 else None
    if num_cpus:
        print(f"Using {num_cpus} CPU cores for parallel fitting")
    else:
        print("Using all available CPU cores for parallel fitting")
    
    print(f"\nUsing resolution {args.resolution}:")
    if args.resolution == 1:
        print("  - Low resolution: 5x5 pixel binning")
    elif args.resolution == 2:
        print("  - Medium resolution: 3x3 pixel binning") 
    elif args.resolution == 3:
        print("  - High resolution: 1x1 pixel binning")
    
    try:
        print("\n--- Starting Stage 6: Spectral Fitting ---")
        print("This stage performs the following:")
        print("  1. Loads adaptive circular bin regions")
        print("  2. Extracts spectra for each region")
        print("  3. Fits thermal plasma models (APEC/MEKAL)")
        print("  4. Determines temperature, abundance, normalization")
        print("  5. Calculates statistical uncertainties")
        print("  6. Saves results for temperature map generation")
        
        if args.continue_fitting:
            print("  7. Continuing from previous incomplete run")
        
        # Import spectral fitting module
        try:
            import spectral
        except ImportError:
            print("✗ Cannot import spectral module")
            sys.exit(1)
        
        # Use the spectral.calculate_spectral_fits function
        spectral.calculate_spectral_fits(cluster_obj, num_cpus=num_cpus)
        
        # Update cluster status
        cluster_obj.last_step_completed = 6  # tmap stage
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Spectral fitting completed successfully!")
        print(f"✓ Fitted thermal plasma models to regions")
        print(f"✓ Determined temperature and abundance distributions") 
        print(f"✓ Generated best-fit parameters file")
        print(f"✓ Ready for temperature map generation")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py make-temperature-map -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Spectral fitting failed: {e}")
        print(f"Note: Spectral fitting requires completed Stage 5 and can take many hours.")
        print(f"Consider using --continue to resume interrupted fits.")
        sys.exit(1)


def cmd_make_temperature_map(args):
    """Create temperature map from spectral fitting results (Stage 7)."""
    print("=== ClusterPyXT Stage 7: Temperature Map Creation ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"Stage 7 creates temperature maps from spectral fitting results.")
    print(f"This stage generates:")
    print(f"  - Temperature distribution map across the cluster")
    print(f"  - Temperature error maps (statistical uncertainties)")
    print(f"  - Fractional error maps for quality assessment")
    print(f"\nMaps are created at the specified resolution")
    
    # Check if previous stages completed
    if cluster_obj.last_step_completed < 6:
        print(f"\n✗ Previous stages not completed. Current stage: {cluster_obj.last_step_completed}")
        print(f"Please complete spectral fitting (Stage 6) before creating temperature maps.")
        return
    
    print(f"✓ Spectral fitting completed (Stage {cluster_obj.last_step_completed})")
    
    # Check for spectral fitting results
    spec_fits_exists = False
    try:
        if hasattr(cluster_obj, 'spec_fits_file'):
            import pypeline_io as io
            spec_fits_exists = io.file_exists(cluster_obj.spec_fits_file)
        if spec_fits_exists:
            print(f"✓ Found spectral fitting results file")
        else:
            print(f"✗ Spectral fitting results not found")
            print(f"Please complete Stage 6 (fit-spectra) first")
            return
    except Exception as e:
        print(f"Warning: Could not verify spectral fitting results: {e}")
    
    print(f"\nUsing resolution {args.resolution}:")
    if args.resolution == 1:
        print("  - Low resolution: 5x5 pixel binning")
    elif args.resolution == 2:
        print("  - Medium resolution: 3x3 pixel binning") 
    elif args.resolution == 3:
        print("  - High resolution: 1x1 pixel binning")
    
    if args.average:
        print("  - Using averaged temperature fits")
    else:
        print("  - Using individual temperature fits")
    
    if not args.yes:
        response = input("Continue with temperature map creation? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Starting Stage 7: Temperature Map Creation ---")
        print("This stage performs the following:")
        print("  1. Loads spectral fitting results")
        print("  2. Maps temperature fits to spatial coordinates")
        print("  3. Creates temperature distribution map") 
        print("  4. Generates error and fractional error maps")
        print("  5. Saves FITS files for scientific analysis")
        
        # Import ACB module for map creation
        try:
            import acb
        except ImportError:
            print("✗ Cannot import acb module")
            sys.exit(1)
        
        # Create temperature map
        acb.make_temperature_map(cluster_obj, args.resolution, average=args.average)
        
        # Update cluster status
        cluster_obj.last_step_completed = 7
        cluster_obj.write_cluster_data()
        
        print(f"\n✓ Temperature map creation completed successfully!")
        print(f"✓ Created temperature distribution map")
        print(f"✓ Generated error and uncertainty maps") 
        print(f"✓ Saved maps as FITS files in output directory")
        print(f"✓ Maps ready for scientific analysis and visualization")
        
        print(f"\nOutput files:")
        print(f"  - Temperature map: {cluster_obj.temperature_map_filename}")
        print(f"  - Error map: {cluster_obj.temperature_error_map_filename}")
        print(f"  - Fractional error map: {cluster_obj.temperature_fractional_error_map_filename}")
        
        print(f"\nNext steps:")
        print(f"  clusterpyxt_cli.py make-pressure-map -c {args.config_file}")
        print(f"  clusterpyxt_cli.py make-entropy-map -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Temperature map creation failed: {e}")
        print(f"Note: Requires completed spectral fitting results.")
        sys.exit(1)


def cmd_make_pressure_map(args):
    """Create pressure map from temperature and density data."""
    print("=== ClusterPyXT Pressure Map Creation ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"Creating pressure maps from temperature and density data.")
    print(f"Pressure maps show:")
    print(f"  - Gas pressure distribution (P = n*T)")
    print(f"  - Thermodynamic state of cluster gas")
    print(f"  - Pressure gradients and substructure")
    print(f"  - Evidence for mergers and shocks")
    
    # Check if temperature map exists
    temp_map_exists = False
    try:
        if hasattr(cluster_obj, 'temperature_map_filename'):
            import pypeline_io as io
            temp_map_exists = io.file_exists(cluster_obj.temperature_map_filename)
        if temp_map_exists:
            print(f"✓ Found temperature map")
        else:
            print(f"✗ Temperature map not found")
            print(f"Please create temperature map first: make-temperature-map")
            return
    except Exception as e:
        print(f"Warning: Could not verify temperature map: {e}")
    
    if not args.yes:
        response = input("Continue with pressure map creation? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Creating Pressure Map ---")
        print("This process performs the following:")
        print("  1. Loads temperature map from spectral fitting")
        print("  2. Creates density map from X-ray surface brightness")
        print("  3. Matches coordinate systems and pixel scales")
        print("  4. Calculates pressure P = n*T")
        print("  5. Normalizes and saves pressure map")
        
        # Import ACB module
        try:
            import acb
        except ImportError:
            print("✗ Cannot import acb module")
            sys.exit(1)
        
        # Create pressure map
        acb.make_pressure_map(cluster_obj)
        
        print(f"\n✓ Pressure map creation completed successfully!")
        print(f"✓ Combined temperature and density data")
        print(f"✓ Generated normalized pressure distribution")
        print(f"✓ Saved pressure map as FITS file")
        
        print(f"\nOutput file:")
        print(f"  - Pressure map: {cluster_obj.pressure_map_filename}")
        
        print(f"\nNext step:")
        print(f"  clusterpyxt_cli.py make-entropy-map -c {args.config_file}")
        
    except Exception as e:
        print(f"\n✗ Pressure map creation failed: {e}")
        print(f"Note: Requires temperature map and X-ray surface brightness data.")
        sys.exit(1)


def cmd_make_entropy_map(args):
    """Create entropy map from temperature and density data."""
    print("=== ClusterPyXT Entropy Map Creation ===")
    
    cluster_obj = load_cluster_from_config(args.config_file)
    
    print(f"Creating entropy maps from temperature and density data.")
    print(f"Entropy maps show:")
    print(f"  - Gas entropy distribution (K = T * n^(-2/3))")
    print(f"  - Thermodynamic history of cluster gas")
    print(f"  - Evidence for heating and cooling processes")
    print(f"  - Signatures of AGN feedback and mergers")
    
    # Check if temperature map exists
    temp_map_exists = False
    try:
        if hasattr(cluster_obj, 'temperature_map_filename'):
            import pypeline_io as io
            temp_map_exists = io.file_exists(cluster_obj.temperature_map_filename)
        if temp_map_exists:
            print(f"✓ Found temperature map")
        else:
            print(f"✗ Temperature map not found")
            print(f"Please create temperature map first: make-temperature-map")
            return
    except Exception as e:
        print(f"Warning: Could not verify temperature map: {e}")
    
    if not args.yes:
        response = input("Continue with entropy map creation? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            return
    
    try:
        print("\n--- Creating Entropy Map ---")
        print("This process performs the following:")
        print("  1. Loads temperature map from spectral fitting")
        print("  2. Creates density map from X-ray surface brightness")
        print("  3. Matches coordinate systems and pixel scales")
        print("  4. Calculates entropy K = T * n^(-2/3)")
        print("  5. Normalizes and saves entropy map")
        
        # Import ACB module
        try:
            import acb
        except ImportError:
            print("✗ Cannot import acb module")
            sys.exit(1)
        
        # Create entropy map
        acb.make_entropy_map(cluster_obj)
        
        print(f"\n✓ Entropy map creation completed successfully!")
        print(f"✓ Combined temperature and density data")
        print(f"✓ Generated normalized entropy distribution")
        print(f"✓ Saved entropy map as FITS file")
        
        print(f"\nOutput file:")
        print(f"  - Entropy map: {cluster_obj.entropy_map_filename}")
        
        print(f"\n✓ ClusterPyXT analysis pipeline completed!")
        print(f"✓ All scientific maps generated")
        print(f"✓ Ready for astrophysical interpretation")
        
    except Exception as e:
        print(f"\n✗ Entropy map creation failed: {e}")
        print(f"Note: Requires temperature map and X-ray surface brightness data.")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ClusterPyXT CLI - X-ray Cluster Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize a new cluster
  clusterpyxt_cli.py init-cluster A2029
  
  # Download and process data (Stage 1)
  clusterpyxt_cli.py download-data -c A2029_cluster_config.ini
  
  # Remove sources (Stage 2, after creating region files)
  clusterpyxt_cli.py remove-sources -c A2029_cluster_config.ini
  
  # Generate response files (Stage 3, after creating ACIS region files)
  clusterpyxt_cli.py generate-responses -c A2029_cluster_config.ini
  
  # Crop data to analysis region (Stage 4, after creating crop region)
  clusterpyxt_cli.py crop-data -c A2029_cluster_config.ini
        """
    )
    
    parser.add_argument('--version', action='version', version='ClusterPyXT CLI 1.414.0a')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # init-cluster command
    init_parser = subparsers.add_parser('init-cluster', help='Initialize a new cluster configuration')
    init_parser.add_argument('name', help='Cluster name (e.g., A2029, Coma, Bullet)')
    init_parser.add_argument('-c', '--config-file', help='Output configuration file path')
    init_parser.set_defaults(func=cmd_init_cluster)
    
    # download-data command (Stage 1)
    download_parser = subparsers.add_parser('download-data', 
                                          help='Download Chandra data and perform initial processing (Stage 1)')
    download_parser.add_argument('-c', '--config-file', required=True, 
                               help='Cluster configuration file')
    download_parser.add_argument('-y', '--yes', action='store_true', 
                               help='Skip confirmation prompts')
    download_parser.set_defaults(func=cmd_download_data)
    
    # remove-sources command (Stage 2)  
    sources_parser = subparsers.add_parser('remove-sources',
                                         help='Remove point sources and filter background (Stage 2)')
    sources_parser.add_argument('-c', '--config-file', required=True,
                              help='Cluster configuration file')
    sources_parser.add_argument('-y', '--yes', action='store_true',
                              help='Skip confirmation prompts')
    sources_parser.set_defaults(func=cmd_remove_sources)
    
    # generate-responses command (Stage 3)
    responses_parser = subparsers.add_parser('generate-responses',
                                           help='Generate RMF and ARF response files (Stage 3)')
    responses_parser.add_argument('-c', '--config-file', required=True,
                                help='Cluster configuration file')
    responses_parser.add_argument('-y', '--yes', action='store_true',
                                help='Skip confirmation prompts')
    responses_parser.set_defaults(func=cmd_generate_responses)
    
    # crop-data command (Stage 4)
    crop_parser = subparsers.add_parser('crop-data',
                                      help='Crop data to analysis region and filter energy (Stage 4)')
    crop_parser.add_argument('-c', '--config-file', required=True,
                           help='Cluster configuration file')
    crop_parser.add_argument('-y', '--yes', action='store_true',
                           help='Skip confirmation prompts')
    crop_parser.set_defaults(func=cmd_crop_data)
    
    # create-bins command (Stage 5)
    bins_parser = subparsers.add_parser('create-bins',
                                      help='Create adaptive circular bins and scale map (Stage 5)')
    bins_parser.add_argument('-c', '--config-file', required=True,
                           help='Cluster configuration file')
    bins_parser.add_argument('-y', '--yes', action='store_true',
                           help='Skip confirmation prompts')
    bins_parser.add_argument('--num-cpus', type=int, default=0,
                           help='Number of CPU cores to use (0 = auto-detect)')
    bins_parser.add_argument('--resolution', type=int, choices=[1, 2, 3], default=2,
                           help='Resolution: 1=low (5x5), 2=medium (3x3), 3=high (1x1) pixels')
    bins_parser.set_defaults(func=cmd_create_bins)
    
    # fit-spectra command (Stage 6)
    spectra_parser = subparsers.add_parser('fit-spectra',
                                         help='Perform spectral fitting on adaptive bins (Stage 6)')
    spectra_parser.add_argument('-c', '--config-file', required=True,
                              help='Cluster configuration file')
    spectra_parser.add_argument('-y', '--yes', action='store_true',
                              help='Skip confirmation prompts')
    spectra_parser.add_argument('--num-cpus', type=int, default=0,
                              help='Number of CPU cores to use (0 = auto-detect)')
    spectra_parser.add_argument('--resolution', type=int, choices=[1, 2, 3], default=2,
                              help='Resolution: 1=low (5x5), 2=medium (3x3), 3=high (1x1) pixels')
    spectra_parser.add_argument('--continue', dest='continue_fitting', action='store_true',
                              help='Continue previous incomplete spectral fitting run')
    spectra_parser.set_defaults(func=cmd_fit_spectra)
    
    # make-temperature-map command (Stage 7)
    temp_map_parser = subparsers.add_parser('make-temperature-map',
                                          help='Create temperature map from spectral fits (Stage 7)')
    temp_map_parser.add_argument('-c', '--config-file', required=True,
                               help='Cluster configuration file')
    temp_map_parser.add_argument('-y', '--yes', action='store_true',
                               help='Skip confirmation prompts')
    temp_map_parser.add_argument('--resolution', type=int, choices=[1, 2, 3], default=2,
                               help='Resolution: 1=low (5x5), 2=medium (3x3), 3=high (1x1) pixels')
    temp_map_parser.add_argument('--average', action='store_true',
                               help='Use averaged temperature fits instead of individual fits')
    temp_map_parser.set_defaults(func=cmd_make_temperature_map)
    
    # make-pressure-map command
    pressure_map_parser = subparsers.add_parser('make-pressure-map',
                                              help='Create pressure map from temperature and density')
    pressure_map_parser.add_argument('-c', '--config-file', required=True,
                                   help='Cluster configuration file')
    pressure_map_parser.add_argument('-y', '--yes', action='store_true',
                                   help='Skip confirmation prompts')
    pressure_map_parser.set_defaults(func=cmd_make_pressure_map)
    
    # make-entropy-map command
    entropy_map_parser = subparsers.add_parser('make-entropy-map',
                                             help='Create entropy map from temperature and density')
    entropy_map_parser.add_argument('-c', '--config-file', required=True,
                                  help='Cluster configuration file')
    entropy_map_parser.add_argument('-y', '--yes', action='store_true',
                                  help='Skip confirmation prompts')
    entropy_map_parser.set_defaults(func=cmd_make_entropy_map)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute the command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 