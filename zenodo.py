#!/usr/bin/env python3
"""
Zenodo Keyword Search Script

A simple script to search Zenodo based on keywords.

You can set your Zenodo API token via an .env file
    -   look at .env.example for example

"""

import argparse
import requests
import json
import os
from typing import List, Optional


def search_zenodo(keywords: List[str], page: int = 1, page_size: int = 20, sort: str = "bestmatch", access_token: Optional[str] = None) -> dict:
    """
    Search Zenodo using keywords.
    
    Args:
        keywords: List of keywords to search for
        page: Page number to retrieve
        page_size: Number of results per page
        sort: Sorting method (bestmatch, mostrecent)
        
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
    
    # Handle newer Zenodo API format
    if isinstance(total, dict):  
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


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Search Zenodo based on keywords")
    parser.add_argument("keywords", nargs="+", help="One or more keywords to search for")
    parser.add_argument("--results", "-r", type=int, default=20, help="Number of results per page")
    parser.add_argument("--page", "-p", type=int, default=1, help="Page number to retrieve")
    parser.add_argument("--sort", "-s", choices=["bestmatch", "mostrecent"], default="bestmatch", 
                        help="Sort order: 'bestmatch' or 'mostrecent'")
    parser.add_argument("--save", action="store_true", help="Save results to a JSON file")
    parser.add_argument("--output", "-o", default="zenodo_results.json", help="Output filename for saved results")
    parser.add_argument("--token", "-t", help="Zenodo API access token")
    
    args = parser.parse_args()
    
    try:
        # Get access token from command line or environment variable
        access_token = args.token
        if not access_token:
            access_token = os.environ.get("ZENODO_ACCESS_TOKEN")
        
        if access_token:
            print("Using Zenodo API access token")
        
        # Display the search query
        print(f"Searching Zenodo for: {' AND '.join(args.keywords)}")
        
        # Perform the search
        results = search_zenodo(args.keywords, args.page, args.results, args.sort, access_token)
        
        # Display the results
        display_results(results)
        
        # Save results if requested
        if args.save:
            save_results(results, args.output)
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()