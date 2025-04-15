# Zenodo API Script

A Python utility for interacting with the Zenodo repository API. This script allows you to search for datasets, download files, and upload your own data to Zenodo.

## Features

- **Search**: Find records on Zenodo using keywords
- **Download**: Retrieve files from specific Zenodo records
- **Bulk Download**: Search for and download files matching specific keywords
- **Upload**: Publish your own datasets to Zenodo

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

3. Create a `.env` file in the project directory with your Zenodo API token (optional, but required for uploads):
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

Options:
- `--title`: Title for the upload (default: filename)
- `--description`: Description for the upload
- `--keywords`: Comma-separated list of keywords
- `--token` or `-t`: Zenodo API access token (overrides .env file)
- `--publish`: Publish the record immediately (default: save as draft)

## Examples

### Search for climate data and save the results

```bash
python zenodo.py search climate --save --output climate_results.json
```

### Download all files from the first 5 records matching "genomics data"

```bash
python zenodo.py download-via-keywords "genomics data" ./genomics-downloads --max-records 5
```

### Upload a dataset with keywords and publish immediately

```bash
python zenodo.py upload experiment_results.csv --title "Experiment Results" --description "Data from my experiment" --keywords "experiment,science,data" --publish
```
