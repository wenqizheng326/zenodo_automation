# Zenodo API Script

A Python utility for interacting with the Zenodo repository API. This script allows you to search for datasets, download files, upload your own data to Zenodo, and manage versioning of records.

## Features

- **Search**: Find records on Zenodo using keywords
- **Download**: Retrieve files from specific Zenodo records
- **Bulk Download**: Search for and download files matching specific keywords
- **Upload**: Publish your own datasets to Zenodo (single or multiple files)
- **Versioning**: Create and manage new versions of existing records
- **Publishing**: Publish draft records
- **Version History**: View all versions of a record

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/zenodo-api-script.git
   cd zenodo-api-script
   ```

2. Install the required dependencies:
   ```bash
   pip install requests python-dotenv
   ```

3. Create a `.env` file in the project directory with your Zenodo API token (optional, but required for uploads and versioning):
   ```
   ZENODO_ACCESS_TOKEN=your_zenodo_api_token_here
   ```
   You can obtain a Zenodo API token by:
   - Creating a Zenodo account at [zenodo.org](https://zenodo.org)
   - Going to your [Applications settings](https://zenodo.org/account/settings/applications/)
   - Creating a new personal access token

## Usage

### Searching Zenodo

Search for records using keywords:
```bash
python zenodo.py search climate
python zenodo.py search "machine learning" biology
```

Options:
- `--results` or `-r`: Number of results per page (default: 20)
- `--page` or `-p`: Page number to retrieve (default: 1)
- `--sort` or `-s`: Sort order, either "bestmatch" or "mostrecent" (default: "bestmatch")
- `--save`: Save results to a JSON file
- `--output` or `-o`: Output filename for saved results (default: "zenodo_results.json")
- `--token` or `-t`: Zenodo API access token (overrides .env file)

### Downloading Files

Download all files from a specific record:
```bash
python zenodo.py download 123456
python zenodo.py download 123456 ./downloads
```

The first argument is the record ID, and the optional second argument is the directory where files should be saved.

### Downloading Files by Keywords

Search for records matching keywords and download their files:
```bash
python zenodo.py download-via-keywords climate data
python zenodo.py download-via-keywords "machine learning" biology ./ml-bio-data
```

Options:
- `--max-records`: Maximum number of records to download (default: 10)
- `--sort` or `-s`: Sort order, either "bestmatch" or "mostrecent" (default: "bestmatch")
- `--token` or `-t`: Zenodo API access token (overrides .env file)

### Uploading Files

Upload a file to Zenodo:
```bash
python zenodo.py upload dataset.zip --title "My Dataset" --description "Description of my dataset"
```

By default, files are published immediately. Use the `--draft` flag to save as a draft instead.

Options:
- `--title`: Title for the upload (default: filename)
- `--description`: Description for the upload
- `--keywords`: Comma-separated list of keywords
- `--token` or `-t`: Zenodo API access token (overrides .env file)
- `--draft`: Save as draft instead of publishing immediately

### Uploading Multiple Files

Upload multiple files in a single Zenodo deposition:
```bash
python zenodo.py upload-multiple data1.csv data2.json metadata.txt --title "Complete Dataset"
```

Options:
- Same options as the `upload` command

### Creating New Versions

Create a new version of an existing Zenodo record:
```bash
python zenodo.py version 123456 --files updated_data.csv --title "Updated Dataset v2"
```

Options:
- `--files`: Space-separated list of new files to upload (replaces all existing files)
- `--title`: New title for the record
- `--description`: New description for the record
- `--keywords`: Comma-separated list of keywords
- `--token` or `-t`: Zenodo API access token (overrides .env file)
- `--draft`: Save as draft instead of publishing immediately

### Web-Based Updating

Open a web browser to manually update a record in the Zenodo interface:
```bash
python zenodo.py web-update 123456
```

This is the most reliable way to ensure proper versioning in Zenodo.

### Viewing Version History

View all versions of a record:
```bash
python zenodo.py versions 123456
```

Options:
- `--token` or `-t`: Zenodo API access token (overrides .env file)
- `--exhaustive`: Use exhaustive search to find all versions

### Publishing Draft Records

Publish a draft record:
```bash
python zenodo.py publish 123456
```

Options:
- `--token` or `-t`: Zenodo API access token (overrides .env file)
- `--no-versions`: Don't display version history after publishing

## Examples

### Search for climate data and save the results
```bash
python zenodo.py search climate --save --output climate_results.json
```

### Download all files from the first 5 records matching "genomics data"
```bash
python zenodo.py download-via-keywords "genomics data" ./genomics-downloads --max-records 5
```

### Upload a dataset and publish immediately
```bash
python zenodo.py upload experiment_results.csv --title "Experiment Results" --description "Data from my experiment" --keywords "experiment,science,data"
```

### Upload multiple files as a draft
```bash
python zenodo.py upload-multiple data.csv metadata.txt --title "Research Data" --draft
```

### Create a new version of an existing record
```bash
python zenodo.py version 123456 --files updated_data.csv new_analysis.txt --title "Dataset v2"
```

### Publish a draft record
```bash
python zenodo.py publish 123456
```
