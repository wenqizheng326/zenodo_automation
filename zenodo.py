#!/usr/bin/env python3
"""
Zenodo API Script

A script to search Zenodo based on keywords and upload/download files.
Usage: 
  - Search: python zenodo.py search keyword1 [keyword2 keyword3 ...]
  - Download: python zenodo.py download record_id [output_dir]
  - Download by Keywords: python zenodo.py download-via-keywords keyword1 [keyword2 ...] [output_dir]
  - Upload: python zenodo.py upload filename [--title "Title"] [--description "Description"] [--draft]
  - Version: python zenodo.py version record_id [--files file1 file2...] [--title "New Title"]

Example: 
  python zenodo.py search climate
  python zenodo.py search "machine learning" biology
  python zenodo.py download 123456 ./downloads
  python zenodo.py download-via-keywords climate data ./climate-downloads
  python zenodo.py upload dataset.zip --title "My Dataset"
  python zenodo.py version 123456 --files updated_data.zip --title "Updated Dataset v2"
"""

import argparse
import requests
import json
import os
import sys
import webbrowser
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
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


def get_record_info(record_id: str, access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed information about a Zenodo record, including versions.
    
    Args:
        record_id: The ID of the record
        access_token: Zenodo API access token (optional)
        
    Returns:
        Dictionary containing record information
    """
    # Set up headers with access token if provided
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    # First try record API
    api_urls = [
        f"https://zenodo.org/api/records/{record_id}",
        f"https://zenodo.org/api/deposit/depositions/{record_id}"
    ]
    
    record_data = None
    used_url = None
    
    for url in api_urls:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                record_data = response.json()
                used_url = url
                break
        except Exception:
            continue
    
    if not record_data:
        raise Exception(f"Failed to get record {record_id}")
    
    # Extract key information
    result = {
        "id": record_id,
        "is_deposition": "deposit/depositions" in used_url if used_url else False,
        "data": record_data
    }
    
    # Extract metadata
    metadata = record_data.get("metadata", {})
    result["metadata"] = metadata
    result["doi"] = metadata.get("doi", "")
    result["title"] = metadata.get("title", "")
    result["publication_date"] = metadata.get("publication_date", "")
    
    # Extract concept info
    result["concept_doi"] = None
    result["concept_recid"] = None
    
    # First check if conceptdoi is directly available
    if "conceptdoi" in metadata:
        result["concept_doi"] = metadata["conceptdoi"]
    
    # Try to get concept info from related identifiers
    for identifier in metadata.get("related_identifiers", []):
        if identifier.get("relation") == "isVersionOf" and identifier.get("scheme") == "doi":
            result["concept_doi"] = identifier.get("identifier")
    
    # Get concept record ID
    if "conceptrecid" in record_data:
        result["concept_recid"] = record_data["conceptrecid"]
    
    # Determine version
    result["version"] = metadata.get("version", "1")
    
    # If we find a DOI in format "10.5281/zenodo.123456.2", parse the version
    if result["doi"] and "." in result["doi"]:
        try:
            # Try to extract version from DOI
            match = re.search(r'(\d+)\.(\d+)$', result["doi"])
            if match:
                result["version"] = match.group(2)
        except Exception:
            pass
            
    return result


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


def find_all_versions(record_id: str, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find all versions of a Zenodo record using multiple search approaches.
    
    Args:
        record_id: ID of any version of the record
        access_token: Zenodo API access token (optional)
        
    Returns:
        List of version information dictionaries
    """
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    # Get record info to extract search keys
    try:
        record_info = get_record_info(record_id, access_token)
    except Exception as e:
        print(f"Warning: Could not get record info: {e}")
        return []
    
    # All versions we find
    all_versions = []
    title = record_info.get("title", "")
    doi = record_info.get("doi", "")
    concept_doi = record_info.get("concept_doi")
    concept_recid = record_info.get("concept_recid")
    
    # Helper function to deduplicate results
    def add_versions(results: dict, source: str) -> int:
        hits = results.get("hits", {}).get("hits", [])
        count = 0
        
        for hit in hits:
            # Check if we already have this version
            hit_id = str(hit.get("id", ""))
            if not hit_id or any(v.get("id") == hit_id for v in all_versions):
                continue
                
            # Add this version
            metadata = hit.get("metadata", {})
            
            # Extract version from DOI if possible
            version = ""
            hit_doi = metadata.get("doi", "")
            if hit_doi and "." in hit_doi:
                try:
                    match = re.search(r'(\d+)\.(\d+)$', hit_doi)
                    if match:
                        version = match.group(2)
                except:
                    pass
            
            # If no version from DOI, try metadata field
            if not version and "version" in metadata:
                version = metadata["version"]
                
            all_versions.append({
                "id": hit_id,
                "doi": hit_doi,
                "title": metadata.get("title", ""),
                "version": version or "1",
                "publication_date": metadata.get("publication_date", ""),
                "created": hit.get("created", ""),
                "updated": hit.get("updated", ""),
                "record_url": f"https://zenodo.org/record/{hit_id}",
                "source": source
            })
            count += 1
            
        return count
    
    # 1. First try searching by concept DOI if available
    if concept_doi:
        try:
            results = search_zenodo([f'conceptdoi:"{concept_doi}"'], 1, 100, "mostrecent", access_token)
            num_added = add_versions(results, "conceptdoi")
            print(f"  Found {num_added} versions via concept DOI search")
        except Exception as e:
            print(f"Warning: concept DOI search failed: {e}")
    
    # 2. Try searching by parent DOI
    if doi and len(all_versions) < 2:
        try:
            # Get the base DOI without version suffix
            base_doi = doi.rsplit(".", 1)[0] if "." in doi else doi
            results = search_zenodo([f'doi:"{base_doi}*"'], 1, 100, "mostrecent", access_token)
            num_added = add_versions(results, "doi_prefix")
            print(f"  Found {num_added} additional versions via DOI prefix search")
        except Exception as e:
            print(f"Warning: DOI prefix search failed: {e}")
    
    # 3. Try searching by concept record ID
    if concept_recid and len(all_versions) < 2:
        try:
            results = search_zenodo([f'conceptrecid:{concept_recid}'], 1, 100, "mostrecent", access_token)
            num_added = add_versions(results, "conceptrecid")
            print(f"  Found {num_added} additional versions via concept record ID search")
        except Exception as e:
            print(f"Warning: concept record ID search failed: {e}")
    
    # 4. If we still don't have multiple versions, try title search
    if title and len(all_versions) < 2:
        # Extract first 3 words of title for search
        title_words = " ".join(title.split()[:3])
        if title_words:
            try:
                results = search_zenodo([f'title:"{title_words}"'], 1, 100, "mostrecent", access_token)
                num_added = add_versions(results, "title")
                print(f"  Found {num_added} additional versions via title search")
            except Exception as e:
                print(f"Warning: title search failed: {e}")
    
    # 5. Sort by publication date or version number
    all_versions.sort(
        key=lambda v: (
            v.get("publication_date", ""),
            int(v.get("version", "1")) if v.get("version", "1").isdigit() else 1
        ),
        reverse=True
    )
    
    # Add our current record if it's not in the results
    if not any(v.get("id") == record_id for v in all_versions):
        all_versions.insert(0, {
            "id": record_id,
            "doi": doi,
            "title": title,
            "version": record_info.get("version", "1"),
            "publication_date": record_info.get("publication_date", ""),
            "record_url": f"https://zenodo.org/record/{record_id}",
            "source": "direct"
        })
    
    return all_versions


def get_record_versions(record_id: str, access_token: Optional[str] = None, exhaustive: bool = True) -> Dict[str, Any]:
    """
    Get information about all versions of a Zenodo record.
    
    Args:
        record_id: The ID of any version of the record
        access_token: Zenodo API access token (optional)
        exhaustive: Whether to use exhaustive search for all versions
        
    Returns:
        Dictionary containing information about all versions
    """
    # Get record info
    record_info = get_record_info(record_id, access_token)
    concept_doi = record_info.get("concept_doi")
    
    # Find all versions using our robust search method
    if exhaustive:
        print("Searching for all versions of the record (exhaustive mode)...")
        versions = find_all_versions(record_id, access_token)
    else:
        # Use standard Zenodo API approach
        print("Searching for versions using concept DOI...")
        
        # Basic version info
        if not concept_doi:
            concept_doi = record_info.get("doi", "")
            print("Warning: Could not find concept DOI, using record DOI instead")
        
        # Set up headers with access token if provided
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        # Now search for all records with this concept DOI
        search_url = "https://zenodo.org/api/records"
        params = {
            "q": f"conceptdoi:\"{concept_doi}\"",
            "size": 100,
            "sort": "mostrecent"
        }
        
        try:
            versions_response = requests.get(search_url, params=params, headers=headers)
            
            if versions_response.status_code != 200:
                raise Exception(f"Failed to get versions: {versions_response.status_code} - {versions_response.text}")
                
            versions_data = versions_response.json()
            
            # Extract version information
            versions = []
            for hit in versions_data.get("hits", {}).get("hits", []):
                metadata = hit.get("metadata", {})
                
                # Try to extract version from DOI if possible
                version = ""
                doi = metadata.get("doi", "")
                if doi and "." in doi:
                    try:
                        match = re.search(r'(\d+)\.(\d+)$', doi)
                        if match:
                            version = match.group(2)
                    except:
                        pass
                
                # If no version from DOI, try metadata field
                if not version and "version" in metadata:
                    version = metadata["version"]
                    
                versions.append({
                    "id": hit.get("id", ""),
                    "doi": doi,
                    "title": metadata.get("title", ""),
                    "version": version or "1",
                    "publication_date": metadata.get("publication_date", ""),
                    "created": hit.get("created", ""),
                    "updated": hit.get("updated", ""),
                    "record_url": f"https://zenodo.org/record/{hit.get('id', '')}"
                })
        except Exception as e:
            print(f"Warning: Standard version search failed: {e}")
            versions = []
    
    # Prepare the result dictionary
    result = {
        "concept_doi": concept_doi,
        "total_versions": len(versions),
        "versions": versions
    }
    
    return result


def display_record_versions(versions_data: Dict[str, Any]) -> None:
    """
    Display information about all versions of a record in a readable format.
    
    Args:
        versions_data: Dictionary containing version information from get_record_versions()
    """
    if "error" in versions_data:
        print(f"Error retrieving all versions: {versions_data['error']}")
        print("\nCurrent record information:")
        current = versions_data["current_record"]
        print(f"ID: {current['id']}")
        print(f"DOI: {current['doi']}")
        print(f"Title: {current['title']}")
        print(f"Publication Date: {current['publication_date']}")
        return
        
    print(f"\nConcept DOI (links all versions): {versions_data['concept_doi']}")
    print(f"Total number of versions: {versions_data['total_versions']}")
    
    if not versions_data['versions']:
        print("\nNo version information available.")
        return
        
    print("\nVersions (from newest to oldest):")
    print("-" * 80)
    
    # Group versions by similar DOI patterns to highlight the versioning
    doi_patterns = {}
    for version in versions_data["versions"]:
        doi = version.get("doi", "")
        # Extract the common DOI prefix (remove version suffix if present)
        doi_prefix = doi.rsplit(".", 1)[0] if "." in doi else doi
        
        if doi_prefix not in doi_patterns:
            doi_patterns[doi_prefix] = []
        
        doi_patterns[doi_prefix].append(version)
    
    # Display versions grouped by DOI pattern
    if len(doi_patterns) > 1:
        print("Multiple DOI patterns detected in versions:")
        
    version_count = 1
    for doi_prefix, versions in doi_patterns.items():
        if len(doi_patterns) > 1:
            print(f"\nDOI Pattern: {doi_prefix}.x")
        
        for version in versions:
            print(f"{version_count}. Version: {version.get('version', f'v{version_count}')}")
            print(f"   Record ID: {version['id']}")
            
            # Highlight the DOI pattern to make versioning clear
            doi = version.get('doi', '')
            if doi and '.' in doi:
                base, suffix = doi.rsplit('.', 1)
                print(f"   DOI: {base}.{suffix}")
            else:
                print(f"   DOI: {doi}")
                
            print(f"   Title: {version['title']}")
            print(f"   Published: {version.get('publication_date', 'Unknown')}")
            print(f"   URL: {version['record_url']}")
            
            # Add source info if available
            if 'source' in version:
                print(f"   Found via: {version['source']}")
                
            print("-" * 80)
            version_count += 1


def upload_to_zenodo(
    file_path: str, 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    keywords: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    publish: bool = True  # Changed default to True
) -> Dict[str, Any]:
    """
    Upload a file to Zenodo.
    
    Args:
        file_path: Path to the file to upload
        title: Title for the upload (default: filename)
        description: Description for the upload
        keywords: List of keywords for the upload
        access_token: Zenodo API token
        publish: Whether to publish the record immediately (default: True)
        
    Returns:
        Dictionary containing record information
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
    
    # Add publication date if not provided
    metadata = {
        "metadata": {
            "title": title,
            "upload_type": "dataset",
            "description": description,
            "creators": [{"name": "Zenodo API Script User"}],
            "keywords": keywords,
            "publication_date": datetime.now().strftime("%Y-%m-%d"),
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
    
    # Accept both 200 and 201 status codes for success
    if r.status_code not in [200, 201]:
        raise Exception(f"Failed to upload file: {r.status_code} - {r.text}")
    
    print("File uploaded successfully!")
    
    # Prepare result
    result = {
        "id": deposition_id,
        "url": r.json().get("links", {}).get("html", f"https://zenodo.org/deposit/{deposition_id}"),
        "files": [file_name]
    }
    
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
            result["status"] = "draft"
            return result
        
        published_data = r.json()
        result["id"] = published_data["id"]
        result["url"] = published_data["links"]["record_html"]
        result["status"] = "published"
        result["doi"] = published_data.get("metadata", {}).get("doi", "")
        
        print(f"Deposition published successfully!")
        print(f"DOI: {result['doi']}")
        print(f"Record URL: {result['url']}")
        
        # Display concept DOI if available
        concept_doi = None
        metadata = published_data.get("metadata", {})
        
        if "conceptdoi" in metadata:
            concept_doi = metadata["conceptdoi"]
            print(f"Concept DOI: {concept_doi} (use this to reference all versions)")
        
        result["concept_doi"] = concept_doi
        
        return result
    else:
        print(f"Deposition saved as draft. You can publish it manually.")
        print(f"NOTE: Your upload will NOT be searchable until you publish it.")
        print(f"NOTE: Draft uploads will NOT appear in version history until published.")
        result["status"] = "draft"
        return result


def upload_multiple_to_zenodo(
    file_paths: List[str], 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    keywords: Optional[List[str]] = None,
    access_token: Optional[str] = None,
    publish: bool = True  # Changed default to True
) -> Dict[str, Any]:
    """
    Upload multiple files to Zenodo in a single deposition.
    
    Args:
        file_paths: List of paths to the files to upload
        title: Title for the upload (default: based on first filename)
        description: Description for the upload
        keywords: List of keywords for the upload
        access_token: Zenodo API token
        publish: Whether to publish the record immediately (default: True)
        
    Returns:
        Dictionary containing record information
    """
    # Validate files exist
    valid_files = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.is_file():
            print(f"Warning: File not found, skipping: {file_path}")
        else:
            valid_files.append(path)
    
    if not valid_files:
        raise FileNotFoundError("No valid files found to upload")
    
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
    if not title:
        # If no title provided, use first filename as base for title
        title = f"Multiple files upload: {valid_files[0].name} and {len(valid_files)-1} other file(s)"
    
    if not description:
        # Create a description listing the files
        file_list = ", ".join(f.name for f in valid_files)
        description = f"Files uploaded via Zenodo API script: {file_list}"
    
    if not keywords:
        keywords = []
    
    metadata = {
        "metadata": {
            "title": title,
            "upload_type": "dataset",
            "description": description,
            "creators": [{"name": "Zenodo API Script User"}],
            "keywords": keywords,
            "publication_date": datetime.now().strftime("%Y-%m-%d"),
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
    
    # Upload each file
    uploaded_files = []
    for file_path in valid_files:
        file_name = file_path.name
        print(f"Uploading file: {file_name}...")
        
        with open(str(file_path), "rb") as fp:
            r = requests.put(
                f"{bucket_url}/{file_name}",
                data=fp,
                headers=headers
            )
        
        # Accept both 200 and 201 status codes for success
        if r.status_code not in [200, 201]:
            print(f"Warning: Failed to upload {file_name}: {r.status_code} - {r.text}")
        else:
            print(f"✓ {file_name} uploaded successfully")
            uploaded_files.append(file_name)
    
    print("All files uploaded successfully!")
    
    # Prepare result
    result = {
        "id": deposition_id,
        "url": r.json()["links"]["html"],
        "files": uploaded_files
    }
    
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
            result["status"] = "draft"
            return result
        
        published_data = r.json()
        result["id"] = published_data["id"]
        result["url"] = published_data["links"]["record_html"]
        result["status"] = "published"
        result["doi"] = published_data.get("metadata", {}).get("doi", "")
        
        print(f"Deposition published successfully!")
        print(f"DOI: {result['doi']}")
        print(f"Record URL: {result['url']}")
        
        # Display concept DOI if available
        concept_doi = None
        metadata = published_data.get("metadata", {})
        
        if "conceptdoi" in metadata:
            concept_doi = metadata["conceptdoi"]
            print(f"Concept DOI: {concept_doi} (use this to reference all versions)")
        
        result["concept_doi"] = concept_doi
        
        return result
    else:
        print(f"Deposition saved as draft. You can publish it manually.")
        print(f"NOTE: Your upload will NOT be searchable until you publish it.")
        print(f"NOTE: Draft uploads will NOT appear in version history until published.")
        result["status"] = "draft"
        return result


def create_version_properly(
    record_id: str,
    files: List[str] = None,
    metadata_updates: Dict[str, Any] = None,
    access_token: Optional[str] = None,
    keep_as_draft: bool = False
) -> Dict[str, Any]:
    """
    Create a new version of a Zenodo record with proper versioning.
    This function uses a two-step approach to ensure versions are properly linked.
    
    Args:
        record_id: ID of the record to create a new version of
        files: Optional list of files to upload
        metadata_updates: Updates to make to the metadata
        access_token: Zenodo API access token
        keep_as_draft: Whether to keep as draft or publish immediately
        
    Returns:
        Dictionary containing information about the new version
    """
    # Get the API token
    if not access_token:
        access_token = os.environ.get("ZENODO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                "No API token provided. Make sure ZENODO_ACCESS_TOKEN is in your .env file or pass it as a parameter."
            )
    
    # Set up the headers with the API token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # First, get information about the original record
    print(f"Getting information about record {record_id}...")
    original_record = get_record_info(record_id, access_token)
    
    record_title = original_record.get("title", "")
    concept_doi = original_record.get("concept_doi")
    concept_recid = original_record.get("concept_recid")
    parent_doi = original_record.get("doi", "")
    
    if not record_title:
        raise ValueError(f"Could not determine title for record {record_id}")
    
    print(f"Creating new version of: {record_title}")
    if concept_doi:
        print(f"Concept DOI: {concept_doi}")
    if concept_recid:
        print(f"Concept Record ID: {concept_recid}")
    if parent_doi:
        print(f"Parent DOI: {parent_doi}")
    
    # Determine next version number
    current_version = original_record.get("version", "1")
    try:
        next_version = str(int(current_version) + 1)
    except (ValueError, TypeError):
        next_version = "2"  # Default to version 2 if we can't parse
    
    print(f"Current version: {current_version}, creating version: {next_version}")
    
    # Step 1: Approach via newversion API
    print("\nApproach 1: Trying newversion API")
    
    try:
        # First check if the record exists and get its details
        if original_record.get("is_deposition", False):
            deposition_id = record_id
        else:
            print("Converting record ID to deposition ID...")
            # Try to find the deposition ID from the record
            r = requests.get(
                f"https://zenodo.org/api/records/{record_id}",
                headers=headers
            )
            
            if r.status_code != 200:
                raise Exception(f"Failed to get record: {r.status_code} - {r.text}")
                
            links = r.json().get("links", {})
            
            # Check if there's an edit link
            if "edit" in links:
                edit_url = links["edit"]
                # Extract deposition ID from the edit URL if possible
                try:
                    deposition_id = edit_url.split("/")[-1]
                    print(f"Found deposition ID: {deposition_id}")
                except:
                    raise Exception("Could not extract deposition ID from edit link")
            else:
                raise Exception("Edit link not found in record, cannot find deposition ID")
        
        # Create a new version
        print(f"Creating new version of record {deposition_id}...")
        
        r = requests.post(
            f"https://zenodo.org/api/deposit/depositions/{deposition_id}/actions/newversion",
            headers=headers
        )
        
        if r.status_code != 201:
            error_msg = r.text
            
            # Check for specific error about files
            if "Please remove all files first" in error_msg:
                raise Exception("Zenodo requires that you manually remove files before creating a new version. Trying alternative approach.")
                
            raise Exception(f"Failed to create new version: {r.status_code} - {error_msg}")
        
        # Get the new deposition ID and links
        new_version_data = r.json()
        new_deposition_id = new_version_data["id"]
        bucket_url = new_version_data["links"]["bucket"]
        
        print(f"New draft version created with ID: {new_deposition_id}")
        
        # Fetch the current metadata
        r = requests.get(
            f"https://zenodo.org/api/deposit/depositions/{new_deposition_id}",
            headers=headers
        )
        
        if r.status_code != 200:
            raise Exception(f"Failed to get metadata: {r.status_code} - {r.text}")
        
        # Extract the current metadata
        current_metadata = r.json()["metadata"]
        
        # Ensure publication_date is set (required field for publishing)
        if "publication_date" not in current_metadata:
            current_metadata["publication_date"] = datetime.now().strftime("%Y-%m-%d")
            print(f"Setting publication_date to today: {current_metadata['publication_date']}")
        
        # Set explicit version
        current_metadata["version"] = next_version
        print(f"Setting version to: {next_version}")
        
        # Add related identifier for concept DOI if we have it
        if concept_doi and "related_identifiers" in current_metadata:
            # Check if we already have a conceptdoi relation
            has_concept_relation = False
            for identifier in current_metadata["related_identifiers"]:
                if (identifier.get("relation") == "isVersionOf" and 
                    identifier.get("scheme") == "doi" and 
                    identifier.get("identifier") == concept_doi):
                    has_concept_relation = True
                    break
            
            if not has_concept_relation:
                # Add the concept DOI relation
                current_metadata["related_identifiers"].append({
                    "relation": "isVersionOf",
                    "scheme": "doi",
                    "identifier": concept_doi
                })
                print(f"Added concept DOI relation: {concept_doi}")
        
        # If we have parent DOI and its different from concept DOI, add is-new-version-of relation
        if parent_doi and parent_doi != concept_doi and "related_identifiers" in current_metadata:
            # Check if we already have the relation
            has_parent_relation = False
            for identifier in current_metadata["related_identifiers"]:
                if (identifier.get("relation") == "isNewVersionOf" and 
                    identifier.get("scheme") == "doi" and 
                    identifier.get("identifier") == parent_doi):
                    has_parent_relation = True
                    break
            
            if not has_parent_relation:
                # Add the parent DOI relation
                current_metadata["related_identifiers"].append({
                    "relation": "isNewVersionOf",
                    "scheme": "doi",
                    "identifier": parent_doi
                })
                print(f"Added parent DOI relation: {parent_doi}")
        
        # Update with user-provided metadata if any
        if metadata_updates:
            for key, value in metadata_updates.items():
                current_metadata[key] = value
                print(f"Updated {key}")
        
        # Update the deposition with metadata
        print("Updating metadata...")
        r = requests.put(
            f"https://zenodo.org/api/deposit/depositions/{new_deposition_id}",
            headers=headers,
            json={"metadata": current_metadata}
        )
        
        if r.status_code != 200:
            raise Exception(f"Failed to update metadata: {r.status_code} - {r.text}")
        
        # If files are provided, delete existing files and upload new ones
        if files:
            # First, get the list of current files
            r = requests.get(
                f"https://zenodo.org/api/deposit/depositions/{new_deposition_id}/files",
                headers=headers
            )
            
            if r.status_code != 200:
                raise Exception(f"Failed to get files: {r.status_code} - {r.text}")
            
            # Delete each existing file
            print("Removing existing files...")
            for file_info in r.json():
                file_id = file_info["id"]
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(0.5)
                
                r = requests.delete(
                    f"https://zenodo.org/api/deposit/depositions/{new_deposition_id}/files/{file_id}",
                    headers=headers
                )
                
                if r.status_code != 204:
                    print(f"Warning: Failed to delete file {file_id}: {r.status_code} - {r.text}")
                    print("Continuing with file upload anyway...")
            
            # Upload new files
            for file_path in files:
                path = Path(file_path)
                if not path.is_file():
                    print(f"Warning: File not found, skipping: {file_path}")
                    continue
                    
                file_name = path.name
                print(f"Uploading file: {file_name}...")
                
                with open(str(path), "rb") as fp:
                    r = requests.put(
                        f"{bucket_url}/{file_name}",
                        data=fp,
                        headers=headers
                    )
                
                # Accept both 200 and 201 status codes for success
                if r.status_code not in [200, 201]:
                    print(f"Warning: Failed to upload {file_name}: {r.status_code} - {r.text}")
                else:
                    print(f"✓ {file_name} uploaded successfully")
        
        # Prepare result
        result = {
            "id": new_deposition_id,
            "url": r.json()["links"]["html"],
            "method": "newversion"
        }
        
        # Publish or keep as draft based on user choice
        if not keep_as_draft:
            print("Publishing new version...")
            r = requests.post(
                f"https://zenodo.org/api/deposit/depositions/{new_deposition_id}/actions/publish",
                headers=headers
            )
            
            if r.status_code != 202:
                print(f"Warning: New version not published: {r.status_code} - {r.text}")
                print("The new version has been saved as draft. You can publish it manually.")
                result["status"] = "draft"
                result["message"] = "Failed to publish, saved as draft"
                return result
            
            published_data = r.json()
            result["record_id"] = published_data["id"]
            result["url"] = published_data["links"]["record_html"]
            result["status"] = "published"
            result["doi"] = published_data.get("metadata", {}).get("doi", "")
            result["concept_doi"] = concept_doi
            
            print(f"New version published successfully!")
            print(f"URL: {result['url']}")
            print(f"DOI: {result['doi']}")
            
            return result
        else:
            print(f"New version saved as draft.")
            print(f"Draft URL: {result['url']}")
            result["status"] = "draft"
            return result
            
    except Exception as e:
        print(f"Approach 1 failed: {e}")
    
    # Step 2: Alternative Approach - Create new record with version relations
    print("\nApproach 2: Creating new record with version relations")
    
    # Only proceed if we have the necessary versioning info
    if not (record_title and (concept_doi or parent_doi)):
        print("Cannot use alternative approach without title and DOI information")
        raise Exception("Failed to create new version. Try using the web interface.")
    
    # Prepare title with version
    if metadata_updates and "title" in metadata_updates:
        new_title = metadata_updates["title"]
    else:
        # Check if title already has version info
        if re.search(r'v\d+$', record_title) or re.search(r'version \d+$', record_title, re.IGNORECASE):
            # Replace version
            new_title = re.sub(r'v\d+$', f'v{next_version}', record_title)
            new_title = re.sub(r'version \d+$', f'version {next_version}', new_title, flags=re.IGNORECASE)
        else:
            # Add version
            new_title = f"{record_title} v{next_version}"
    
    # Get description from original record if not provided
    if not metadata_updates or "description" not in metadata_updates:
        description = original_record.get("metadata", {}).get("description", f"Version {next_version} of {record_title}")
    else:
        description = metadata_updates["description"]
    
    # Prepare relation identifiers for versioning
    related_identifiers = []
    
    # Add concept DOI relation if available
    if concept_doi:
        related_identifiers.append({
            "relation": "isVersionOf",
            "scheme": "doi",
            "identifier": concept_doi
        })
    
    # Add parent record relation
    if parent_doi:
        related_identifiers.append({
            "relation": "isNewVersionOf", 
            "scheme": "doi",
            "identifier": parent_doi
        })
    
    # Prepare metadata
    metadata = {
        "metadata": {
            "title": new_title,
            "upload_type": "dataset",
            "description": description,
            "creators": original_record.get("metadata", {}).get("creators", [{"name": "Zenodo API Script User"}]),
            "version": next_version,
            "publication_date": datetime.now().strftime("%Y-%m-%d"),
            "related_identifiers": related_identifiers
        }
    }
    
    # Add keywords if available
    keywords = original_record.get("metadata", {}).get("keywords")
    if keywords:
        metadata["metadata"]["keywords"] = keywords
    
    # Update with any additional metadata
    if metadata_updates:
        for key, value in metadata_updates.items():
            if key != "related_identifiers":  # We already set this
                metadata["metadata"][key] = value
    
    # Create a new deposition
    print("Creating new deposition with version relations...")
    r = requests.post(
        "https://zenodo.org/api/deposit/depositions",
        headers=headers,
        json={}
    )
    
    if r.status_code != 201:
        raise Exception(f"Failed to create deposition: {r.status_code} - {r.text}")
    
    deposition_id = r.json()["id"]
    bucket_url = r.json()["links"]["bucket"]
    
    # Update the deposition with metadata
    print("Updating metadata with version relations...")
    r = requests.put(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}",
        headers=headers,
        data=json.dumps(metadata)
    )
    
    if r.status_code != 200:
        raise Exception(f"Failed to update metadata: {r.status_code} - {r.text}")
    
    # Upload files if provided
    if files:
        for file_path in files:
            path = Path(file_path)
            if not path.is_file():
                print(f"Warning: File not found, skipping: {file_path}")
                continue
                
            file_name = path.name
            print(f"Uploading file: {file_name}...")
            
            with open(str(path), "rb") as fp:
                r = requests.put(
                    f"{bucket_url}/{file_name}",
                    data=fp,
                    headers=headers
                )
            
            # Accept both 200 and 201 status codes for success
            if r.status_code not in [200, 201]:
                print(f"Warning: Failed to upload {file_name}: {r.status_code} - {r.text}")
            else:
                print(f"✓ {file_name} uploaded successfully")
    
    # Prepare result
    result = {
        "id": deposition_id,
        "method": "new_record"
    }
    
    # Try to get the URL, with fallback
    try:
        result["url"] = r.json().get("links", {}).get("html", f"https://zenodo.org/deposit/{deposition_id}")
    except:
        result["url"] = f"https://zenodo.org/deposit/{deposition_id}"
    
    # Publish or keep as draft based on user choice
    if not keep_as_draft:
        print("Publishing new version record...")
        r = requests.post(
            f"https://zenodo.org/api/deposit/depositions/{deposition_id}/actions/publish",
            headers=headers
        )
        
        if r.status_code != 202:
            print(f"Warning: Record not published: {r.status_code} - {r.text}")
            print("The record has been saved as draft. You can publish it manually.")
            result["status"] = "draft"
            result["message"] = "Failed to publish, saved as draft"
            return result
        
        published_data = r.json()
        result["record_id"] = published_data["id"]
        result["url"] = published_data["links"]["record_html"]
        result["status"] = "published"
        result["doi"] = published_data.get("metadata", {}).get("doi", "")
        
        print(f"New version published successfully!")
        print(f"URL: {result['url']}")
        print(f"DOI: {result['doi']}")
        
        if concept_doi:
            result["concept_doi"] = concept_doi
            print(f"Concept DOI: {concept_doi}")
        
        return result
    else:
        print(f"New version saved as draft.")
        print(f"Draft URL: {result['url']}")
        result["status"] = "draft"
        return result


def publish_draft(
    deposition_id: str,
    access_token: Optional[str] = None,
    show_versions: bool = True
) -> str:
    """
    Publish a draft Zenodo record.
    
    Args:
        deposition_id: The ID of the draft record to publish
        access_token: Zenodo API access token
        show_versions: Whether to display version history after publishing
        
    Returns:
        URL of the published record
    """
    # Get the API token
    if not access_token:
        access_token = os.environ.get("ZENODO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                "No API token provided. Make sure ZENODO_ACCESS_TOKEN is in your .env file or pass it as a parameter."
            )
    
    # Set up the headers with the API token
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # First, verify that the record exists and is a draft
    print(f"Verifying draft record {deposition_id}...")
    
    r = requests.get(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}",
        headers=headers
    )
    
    if r.status_code != 200:
        raise Exception(f"Failed to get record: {r.status_code} - {r.text}")
    
    record_data = r.json()
    
    # Check if the record is a draft (unpublished)
    if record_data.get("submitted", True):
        raise Exception(f"Record {deposition_id} is already published. Cannot publish a published record.")
    
    # Publish the draft
    print(f"Publishing draft record {deposition_id}...")
    
    r = requests.post(
        f"https://zenodo.org/api/deposit/depositions/{deposition_id}/actions/publish",
        headers=headers
    )
    
    if r.status_code != 202:
        raise Exception(f"Failed to publish record: {r.status_code} - {r.text}")
    
    published_data = r.json()
    record_url = published_data["links"]["record_html"]
    record_id = published_data["id"]
    doi = published_data.get("metadata", {}).get("doi", "")
    
    print(f"Record published successfully!")
    print(f"Record URL: {record_url}")
    if doi:
        print(f"DOI: {doi}")
    
    # Show version history if requested
    if show_versions:
        try:
            print("\nRetrieving version history...")
            # Small delay to allow Zenodo to update its index
            time.sleep(2)
            versions_data = get_record_versions(record_id, access_token, True)
            display_record_versions(versions_data)
        except Exception as e:
            print(f"Could not retrieve version history: {e}")
    
    return record_url


def web_update(record_id: str) -> None:
    """
    Open a web browser to the record page for manual updating.
    This is the most reliable way to get proper versioning in Zenodo.
    
    Args:
        record_id: The ID of the record to update
    """
    url = f"https://zenodo.org/record/{record_id}"
    print(f"Opening Zenodo record {record_id} in web browser...")
    print(f"URL: {url}")
    
    try:
        webbrowser.open(url)
        
        print("\nFor proper versioning, follow these steps:")
        print("1. Click 'New version' on the record page")
        print("2. Delete any existing files if needed")
        print("3. Upload your new files")
        print("4. Update metadata if needed")
        print("5. Save and publish the new version")
        print("\nThis manual method ensures proper DOI versioning patterns.")
        
    except Exception as e:
        print(f"Error opening browser: {e}")
        print(f"Please visit this URL manually: {url}")
        print("Then follow the same steps listed above.")


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
    
    # Upload subcommand - changed to add --draft flag
    upload_parser = subparsers.add_parser("upload", help="Upload a file to Zenodo")
    upload_parser.add_argument("file_path", help="Path to the file to upload")
    upload_parser.add_argument("--title", help="Title for the upload")
    upload_parser.add_argument("--description", help="Description for the upload")
    upload_parser.add_argument("--keywords", help="Comma-separated list of keywords")
    upload_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    upload_parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing immediately")
    
    # Upload Multiple subcommand - changed to add --draft flag
    upload_multiple_parser = subparsers.add_parser("upload-multiple", help="Upload multiple files to Zenodo in one deposition")
    upload_multiple_parser.add_argument("file_paths", nargs="+", help="Paths to the files to upload")
    upload_multiple_parser.add_argument("--title", help="Title for the upload")
    upload_multiple_parser.add_argument("--description", help="Description for the upload")
    upload_multiple_parser.add_argument("--keywords", help="Comma-separated list of keywords")
    upload_multiple_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    upload_multiple_parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing immediately")
    
    # Version subcommand (renamed from update) - with better versioning support
    version_parser = subparsers.add_parser("version", help="Create a new version of an existing Zenodo record")
    version_parser.add_argument("record_id", help="ID of the record to create a new version of")
    version_parser.add_argument("--files", nargs="*", help="Paths to new files to upload (replaces all existing files)")
    version_parser.add_argument("--title", help="New title for the record")
    version_parser.add_argument("--description", help="New description for the record")
    version_parser.add_argument("--keywords", help="Comma-separated list of keywords")
    version_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    version_parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing immediately")
    
    # Web-update subcommand - for browser-based updating
    web_update_parser = subparsers.add_parser("web-update", 
                                         help="Open a web browser to manually update a Zenodo record")
    web_update_parser.add_argument("record_id", help="ID of the record to update via web interface")
    
    # Versions subcommand - for viewing version history
    versions_parser = subparsers.add_parser("versions", help="View all versions of a Zenodo record")
    versions_parser.add_argument("record_id", help="ID of any version of the record")
    versions_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    versions_parser.add_argument("--exhaustive", action="store_true", help="Use exhaustive search to find all versions")

    # Publish subcommand
    publish_parser = subparsers.add_parser("publish", help="Publish a draft Zenodo record")
    publish_parser.add_argument("record_id", help="ID of the draft record to publish")
    publish_parser.add_argument("--token", "-t", help="Zenodo API access token (overrides .env)")
    publish_parser.add_argument("--no-versions", action="store_true", help="Don't display version history")

     
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
            
            # Upload the file - changed to use draft flag
            result = upload_to_zenodo(
                args.file_path,
                title=args.title,
                description=args.description,
                keywords=keywords,
                access_token=access_token,
                publish=not args.draft  # Publish unless --draft is specified
            )
            
            print(f"Record URL: {result['url']}")
            
        elif args.command == "upload-multiple":
            # Parse keywords if provided
            keywords = args.keywords.split(",") if hasattr(args, 'keywords') and args.keywords else None
            
            # Upload multiple files - changed to use draft flag
            result = upload_multiple_to_zenodo(
                args.file_paths,
                title=args.title,
                description=args.description,
                keywords=keywords,
                access_token=access_token,
                publish=not args.draft  # Publish unless --draft is specified
            )
            
            print(f"Record URL: {result['url']}")
        
        elif args.command == "version":
            # Prepare metadata updates if any fields are provided
            metadata_updates = {}
            if hasattr(args, 'title') and args.title:
                metadata_updates["title"] = args.title
            if hasattr(args, 'description') and args.description:
                metadata_updates["description"] = args.description
            if hasattr(args, 'keywords') and args.keywords:
                metadata_updates["keywords"] = args.keywords.split(",")
            
            # Create a new version with proper versioning
            result = create_version_properly(
                args.record_id,
                files=args.files,
                metadata_updates=metadata_updates if metadata_updates else None,
                access_token=access_token,
                keep_as_draft=args.draft  # Keep as draft if requested
            )
            
            print(f"\nNew version created via {result['method']} method")
            print(f"Status: {result['status']}")
            print(f"URL: {result['url']}")
            
            if result['status'] == 'published':
                print(f"DOI: {result.get('doi', 'Unknown')}")
                
                # Show version history
                print("\nChecking version history...")
                time.sleep(2)  # Wait for Zenodo to index
                
                try:
                    record_id = result.get('record_id', result.get('id'))
                    versions_data = get_record_versions(record_id, access_token, True)
                    display_record_versions(versions_data)
                except Exception as e:
                    print(f"Error retrieving version history: {e}")
            
        elif args.command == "web-update":
            # Open a web browser to the record page for manual updating
            web_update(args.record_id)
            
        elif args.command == "versions":
            # Get and display all versions of a record
            try:
                versions_data = get_record_versions(
                    args.record_id, 
                    access_token, 
                    args.exhaustive if hasattr(args, 'exhaustive') else False
                )
                display_record_versions(versions_data)
            except Exception as e:
                print(f"Error retrieving versions: {e}")
        
        elif args.command == "publish":
            # Publish a draft record
            try:
                record_url = publish_draft(
                    args.record_id,
                    access_token=access_token,
                    show_versions=not args.no_versions if hasattr(args, 'no_versions') else True
                )
                
                print(f"Published record URL: {record_url}")
            except Exception as e:
                print(f"Error publishing draft record: {e}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()