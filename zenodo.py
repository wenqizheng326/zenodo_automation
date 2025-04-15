#!/usr/bin/env python3
"""
Zenodo API Script

A script to search Zenodo based on keywords and upload/download files.
Usage: 
  - Search: python zenodo.py search keyword1 [keyword2 keyword3 ...]
  - Download: python zenodo.py download record_id [output_dir]
  - Download by Keywords: python zenodo.py download-via-keywords keyword1 [keyword2 ...] [output_dir]
  - Upload: python zenodo.py upload filename [--title "Title"] [--description "Description"]

Example: 
  python zenodo.py search climate
  python zenodo.py search "machine learning" biology
  python zenodo.py download 123456 ./downloads
  python zenodo.py download-via-keywords climate data ./climate-downloads
  python zenodo.py upload dataset.zip --title "My Dataset"
"""

import argparse
import requests
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import time
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def search_zenodo(keywords: List[str], page: int = 1, page_size: int = 20, sort: str = "bestmatch", access_token: Optional[str] = None) -> dict:
    """
    Search Zenodo using keywords.
    
    Args:
        keywords: List of keywords to search for
        page: Page number to retrieve
        page_size: Number of results per page
        sort: Sorting method (bestmatch, mostrecent)
        access_token: Optional Zenodo API access token
        
    Returns:
        Dictionary containing the search results
    """
    # Zenodo API endpoint for searching
    zenodo_api_url = "https://zenodo.org/api/records"
    
    # Combine multiple keywords with AND operators
    if len(keywords) > 1:
        query = " AND ".join(keywords)
    else:
        query = keywords[0]
    
    # Set up the parameters for the API request
    params = {
        "q": query,
        "size": page_size,
        "page": page,
        "sort": sort
    }
    
    # Set up headers with access token if provided
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    # Make the API request
    response = requests.get(zenodo_api_url, params=params, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")


def display_results(results: dict) -> None:
    """
    Display the search results in a readable format.
    
    Args:
        results: Dictionary containing the search results
    """
    hits = results.get("hits", {}).get("hits", [])
    total = results.get("hits", {}).get("total", 0)
    
    if isinstance(total, dict):  # Handle newer Zenodo API format
        total = total.get("value", 0)
    
    print(f"\nFound {total} results\n")
    print("-" * 80)
    
    if not hits:
        print("No results found for your search query.")
        return
    
    for i, hit in enumerate(hits, 1):
        metadata = hit.get("metadata", {})
        
        title = metadata.get("title", "No title")
        creators = metadata.get("creators", [])
        creator_names = ", ".join([creator.get("name", "Unknown") for creator in creators])
        publication_date = metadata.get("publication_date", "Unknown date")
        description = metadata.get("description", "No description")
        
        # Truncate long descriptions
        if len(description) > 200:
            description = description[:200] + "..."
        
        # Get DOI and URL
        doi = metadata.get("doi", "No DOI")
        record_url = f"https://zenodo.org/record/{hit.get('id', '')}"
        
        print(f"{i}. {title}")
        print(f"   Authors: {creator_names}")
        print(f"   Published: {publication_date}")
        print(f"   DOI: {doi}")
        print(f"   URL: {record_url}")
        
        # Print keywords if available
        if "keywords" in metadata and metadata["keywords"]:
            print(f"   Keywords: {', '.join(metadata['keywords'])}")
            
        print(f"   Description: {description}")
        print("-" * 80)


def save_results(results: dict, filename: str = "zenodo_results.json") -> None:
    """
    Save the search results to a JSON file.
    
    Args:
        results: Dictionary containing the search results
        filename: Name of the file to save the results to
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {filename}")


def download_zenodo_record(record_id: str, output_dir: Optional[str] = None, access_token: Optional[str] = None) -> None:
    """
    Download all files associated with a Zenodo record.
    
    Args:
        record_id: The ID of the record to download files from
        output_dir: Directory to save files to (default: current directory)
        access_token: Zenodo API access token
    """
    # Set up the output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()
    
    # Set up headers with access token if provided
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    # Get record metadata
    api_url = f"https://zenodo.org/api/records/{record_id}"
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get record {record_id}: {response.status_code} - {response.text}")
    
    record_data = response.json()
    title = record_data.get("metadata", {}).get("title", "Unknown Title")
    print(f"Downloading files for record: {title}")
    
    # Extract file information
    files = record_data.get("files", [])
    if not files:
        print("No files found in this record.")
        return
    
    print(f"Found {len(files)} file(s).")
    
    # Download each file
    for file_info in files:
        file_url = file_info.get("links", {}).get("self", "")
        filename = file_info.get("key", "unknown_file")
        size = file_info.get("size", 0)
        
        # Format the file size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        
        print(f"Downloading: {filename} ({size_str})")
        
        # Download the file with the same headers
        file_response = requests.get(file_url, headers=headers, stream=True)
        if file_response.status_code != 200:
            print(f"Failed to download {filename}: {file_response.status_code}")
            continue
        
        # Sanitize filename to remove path separators
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        
        # Save the file
        output_file = output_path / safe_filename
        with open(output_file, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Saved to: {output_file}")


def download_via_keywords(
    keywords: List[str], 
    output_dir: Optional[str] = None, 
    access_token: Optional[str] = None,
    max_records: int = 10,
    page_size: int = 20,
    sort: str = "bestmatch"
) -> None:
    """
    Search for records matching keywords and download all files from those records.
    
    Args:
        keywords: List of keywords to search for
        output_dir: Directory to save files to (default: current directory)
        access_token: Zenodo API access token
        max_records: Maximum number of records to download
        page_size: Number of results per page
        sort: Sorting method (bestmatch, mostrecent)
    """
    # Set up the output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()
    
    print(f"Searching Zenodo for: {' AND '.join(keywords)}")
    
    # Perform the search
    results = search_zenodo(keywords, 1, page_size, sort, access_token)
    
    hits = results.get("hits", {}).get("hits", [])
    total = results.get("hits", {}).get("total", 0)
    
    if isinstance(total, dict):  # Handle newer Zenodo API format
        total = total.get("value", 0)
    
    if not hits:
        print("No results found for your search query.")
        return
    
    print(f"\nFound {total} results. Will download files from up to {max_records} records.\n")
    
    # Limit the number of records to download
    records_to_download = min(len(hits), max_records)
    
    # Create a subdirectory for each record
    for i, hit in enumerate(hits[:records_to_download], 1):
        record_id = hit.get("id", "")
        if not record_id:
            continue
        
        # Create a directory for this record
        record_title = hit.get("metadata", {}).get("title", f"record_{record_id}")
        safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in record_title)
        safe_title = safe_title[:50]  # Limit directory name length
        
        record_dir = output_path / f"{i}_{safe_title}"
        record_dir.mkdir(exist_ok=True)
        
        # Save record metadata
        with open(record_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(hit, f, indent=2, ensure_ascii=False)
        
        # Download all files for this record
        try:
            print(f"\nDownloading record {i}/{records_to_download}: {record_title}")
            download_zenodo_record(record_id, str(record_dir), access_token)
        except Exception as e:
            print(f"Error downloading record {record_id}: {e}")
    
    print(f"\nDownload complete. Files saved to {output_path}")


def upload_to_zenodo(
    file_path: str, 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    keywords: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    publish: bool = False
) -> str:
    """
    Upload a file to Zenodo.
    
    Args:
        file_path: Path to the file to upload
        title: Title for the upload (default: filename)
        description: Description for the upload
        keywords: List of keywords for the upload
        access_token: Zenodo API token
        publish: Whether to publish the record immediately
        
    Returns:
        URL of the created record
    """
    # Check if the file exists
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get the API token
    if not access_token:
        access_token = os.environ.get("ZENODO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                "No API token provided. Make sure ZENODO_ACCESS_TOKEN is in your .env file or pass it as a parameter."
            )
    
    # Set up the headers with the API token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create a new deposition
    print("Creating new deposition...")
    r = requests.post(
        "https://zenodo.org/api/deposit/depositions",
        headers=headers,
        json={}
    )
    
    if r.status_code != 201:
        raise Exception(f"Failed to create deposition: {r.status_code} - {r.text}")
    
    deposition_id = r.json()["id"]
    bucket_url = r.json()["links"]["bucket"]
    
    # Set metadata
    file_name = file_path.name
    if not title:
        title = file_name
    
    if not description:
        description = f"File uploaded via Zenodo API script: {file_name}"
    
    if not keywords:
        keywords = []
    
    metadata = {
        "metadata": {
            "title": title,
            "upload_type": "dataset",
            "description": description,
            "creators": [{"name": "Zenodo API Script User"}],
            "keywords": keywords,
        }
    }
    
    # Update the deposition with metadata
    print("Updating metadata...")
    r = requests.put(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}",
        headers=headers,
        data=json.dumps(metadata)
    )
    
    if r.status_code != 200:
        raise Exception(f"Failed to update metadata: {r.status_code} - {r.text}")
    
    # Upload the file
    print(f"Uploading file: {file_name}...")
    with open(str(file_path), "rb") as fp:
        r = requests.put(
            f"{bucket_url}/{file_name}",
            data=fp,
            headers=headers
        )
    
    if r.status_code != 200:
        raise Exception(f"Failed to upload file: {r.status_code} - {r.text}")
    
    print("File uploaded successfully!")
    
    # Publish the deposition if requested
    if publish:
        print("Publishing deposition...")
        r = requests.post(
            f"https://zenodo.org/api/deposit/depositions/{deposition_id}/actions/publish",
            headers=headers
        )
        
        if r.status_code != 202:
            print(f"Warning: Deposition not published: {r.status_code} - {r.text}")
            print("The deposition has been saved as draft. You can publish it manually.")
            return r.json()["links"]["html"]
        
        record_url = r.json()["links"]["record_html"]
        print(f"Deposition published successfully!")
        return record_url
    else:
        draft_url = r.json()["links"]["html"]
        print(f"Deposition saved as draft. You can publish it manually.")
        return draft_url


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Zenodo API Interactions")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Search subcommand
    search_parser = subparsers.add_parser("search", help="Search Zenodo records")
    search_parser.add_argument("keywords", nargs="+", help="One or more keywords to search for")
    search_parser.add_argument("--results", "-r", type=int, default=20, help="Number of results per page")
    search_parser.add_argument("--page", "-p", type=int, default=1, help="Page number to retrieve")
    search_parser.add_argument("--sort", "-s", choices=["bestmatch", "mostrecent"], default="bestmatch", 
                        help="Sort order: 'bestmatch' or 'mostrecent'")
    search_parser.add_argument("--save", action="store_true", help="Save results to a JSON file")
    search_parser.add_argument("--output", "-o", default="zenodo_results.json", help="Output filename for saved results")
    search_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    
    # Download subcommand
    download_parser = subparsers.add_parser("download", help="Download files from a Zenodo record")
    download_parser.add_argument("record_id", help="ID of the record to download")
    download_parser.add_argument("output_dir", nargs="?", help="Directory to save files to")
    download_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    
    # Download by keywords subcommand
    download_keywords_parser = subparsers.add_parser("download-via-keywords", 
                                                   help="Download files from records matching keywords")
    download_keywords_parser.add_argument("keywords", nargs="+", help="One or more keywords to search for")
    download_keywords_parser.add_argument("output_dir", nargs="?", help="Directory to save files to")
    download_keywords_parser.add_argument("--max-records", type=int, default=10, 
                                        help="Maximum number of records to download (default: 10)")
    download_keywords_parser.add_argument("--sort", "-s", choices=["bestmatch", "mostrecent"], default="bestmatch", 
                                        help="Sort order: 'bestmatch' or 'mostrecent'")
    download_keywords_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    
    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Upload a file to Zenodo")
    upload_parser.add_argument("file_path", help="Path to the file to upload")
    upload_parser.add_argument("--title", help="Title for the upload")
    upload_parser.add_argument("--description", help="Description for the upload")
    upload_parser.add_argument("--keywords", help="Comma-separated list of keywords")
    upload_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    upload_parser.add_argument("--publish", action="store_true", help="Publish the record immediately")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Get access token from command line or environment variable
        access_token = args.token if hasattr(args, 'token') else None
        if not access_token:
            access_token = os.environ.get("ZENODO_ACCESS_TOKEN")
            if access_token:
                print("Using Zenodo API token from .env file")
            
        if args.command == "search":
            # Display the search query
            print(f"Searching Zenodo for: {' AND '.join(args.keywords)}")
            
            # Perform the search
            results = search_zenodo(args.keywords, args.page, args.results, args.sort, access_token)
            
            # Display the results
            display_results(results)
            
            # Save results if requested
            if args.save:
                save_results(results, args.output)
                
        elif args.command == "download":
            # Download files from the record
            download_zenodo_record(args.record_id, args.output_dir, access_token)
            
        elif args.command == "download-via-keywords":
            # Download files from records matching keywords
            download_via_keywords(
                args.keywords, 
                args.output_dir, 
                access_token,
                args.max_records,
                20,  # page_size
                args.sort
            )
            
        elif args.command == "upload":
            # Parse keywords if provided
            keywords = args.keywords.split(",") if hasattr(args, 'keywords') and args.keywords else None
            
            # Upload the file
            record_url = upload_to_zenodo(
                args.file_path,
                title=args.title,
                description=args.description,
                keywords=keywords,
                access_token=access_token,
                publish=args.publish
            )
            
            print(f"Record URL: {record_url}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()