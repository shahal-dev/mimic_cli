# ClusterPyXT CLI Setup Instructions

## Current Setup

The ClusterPyXT CLI has been successfully organized with the following structure:

```
ClusterPyXT_CLI/
├── clusterpyxt_cli.py          # Main wrapper script (executable)
├── finder/                     # Core CLI application code
│   ├── clusterpyxt_cli.py     # Actual CLI implementation
│   ├── ciao.py                # CIAO interface functions
│   ├── cluster.py             # Cluster object definitions
│   ├── acb.py                 # Analysis and calibration functions
│   ├── config.py              # Configuration management
│   ├── pypeline_config.ini    # System configuration
│   └── [other Python modules]
├── A2029_cluster_config.ini    # Example cluster configuration
├── A2029_demo_cluster_config.ini
└── A2029_example_config.ini
```

## Prerequisites

Before using ClusterPyXT CLI, you need:

1. **CIAO 4.14+** with full CALDB installation
2. **Python 3.8+** (included with CIAO)
3. Active CIAO environment

## Setup Steps

### 1. Activate CIAO Environment

Before running any ClusterPyXT commands, you must activate CIAO:

```bash
# If CIAO is installed via conda:
conda activate ciao

# Or if CIAO is installed traditionally:
source /path/to/ciao/bin/ciao.bash
```

### 2. Verify CIAO is Working

Test that CIAO is properly activated:

```bash
python -c "import ciao_contrib; print('CIAO is ready')"
```

### 3. Run ClusterPyXT CLI

You can now run the CLI from the main directory:

```bash
cd /home/mimic/ClusterPyXT_CLI
python clusterpyxt_cli.py --help
```

Or directly from the finder directory:

```bash
cd /home/mimic/ClusterPyXT_CLI/finder
python clusterpyxt_cli.py --help
```

## Usage Examples

### Initialize a new cluster:
```bash
python clusterpyxt_cli.py init-cluster A2029
```

### Download and process data (after editing config file):
```bash
python clusterpyxt_cli.py download-data -c A2029_cluster_config.ini
```

### Continue with other pipeline stages:
```bash
python clusterpyxt_cli.py remove-sources -c A2029_cluster_config.ini
python clusterpyxt_cli.py generate-responses -c A2029_cluster_config.ini
# ... and so on
```

## Configuration Files

- **Cluster config files** (*.ini): Located in both main directory and finder/ (linked)
- **System config** (pypeline_config.ini): Located in finder/ directory
- **Configuration files are automatically accessible from both locations**

## Troubleshooting

### "ModuleNotFoundError: No module named 'ciao_contrib'"
- Solution: Activate your CIAO environment first
- Check: `conda activate ciao` or source the CIAO setup script

### "Unable to load CIAO. Fitting calls will fail"
- This warning appears when CIAO is not activated
- The CLI will not function without CIAO

### Import or path issues
- The wrapper script handles path management automatically
- Run from either the main directory or finder/ directory

## Files Modified/Created

1. **Created**: `ClusterPyXT_CLI/clusterpyxt_cli.py` - Main wrapper script
2. **Made executable**: Both wrapper and finder CLI scripts
3. **Created symlinks**: Cluster config files accessible from finder directory
4. **Created**: This setup documentation

The CLI is now properly organized and ready to use once CIAO is activated! 