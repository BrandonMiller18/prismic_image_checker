#!/usr/bin/env python3
"""
Prismic Image Alt Text Checker
Identifies all images in Prismic documents and exports them to CSV with their alt text.
Images without alt text will have a blank alt_text column.
"""

import requests
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
import argparse
import os
from urllib.parse import urljoin


class PrismicAltTextChecker:
    """Check Prismic documents for all images and their alt text."""
    
    def __init__(self, repository_name: str, access_token: str = None):
        """
        Initialize the Prismic alt text checker.
        
        Args:
            repository_name: Name of your Prismic repository (e.g., 'your-repo-name')
                            Can be just the name, or include .prismic.io, or full URL
            access_token: Optional access token for private repositories
        """
        # Extract clean repository name from various input formats
        self.repository_name = self._extract_repository_name(repository_name)
        self.access_token = access_token
        self.api_endpoint = f"https://{self.repository_name}.cdn.prismic.io/api/v2"
        self.session = requests.Session()
        
        if access_token:
            self.session.params = {'access_token': access_token}
    
    def _extract_repository_name(self, input_str: str) -> str:
        """
        Extract repository name from input string (handles various formats).
        
        Args:
            input_str: Repository name or URL (e.g., 'eisejewels', 'eisejewels.prismic.io', 
                      'https://eisejewels.prismic.io', 'https://eisejewels.cdn.prismic.io')
            
        Returns:
            Clean repository name (e.g., 'eisejewels')
        """
        # Remove protocol if present
        cleaned = input_str.replace('https://', '').replace('http://', '')
        
        # Remove trailing slash
        cleaned = cleaned.rstrip('/')
        
        # Extract just the repository name (the part before any domain)
        # Handle: eisejewels.prismic.io -> eisejewels
        # Handle: eisejewels.cdn.prismic.io -> eisejewels
        # Handle: eisejewels -> eisejewels
        if '.prismic.io' in cleaned:
            # Split on the first dot to get just the repository name
            cleaned = cleaned.split('.')[0]
        elif '.cdn.prismic.io' in cleaned:
            cleaned = cleaned.split('.')[0]
        
        return cleaned
    
    def get_api_ref(self) -> str:
        """
        Get the master ref for querying documents.
        
        Returns:
            The master ref string
        """
        try:
            response = self.session.get(self.api_endpoint)
            response.raise_for_status()
            data = response.json()
            
            # Find the master ref
            for ref in data.get('refs', []):
                if ref.get('isMasterRef'):
                    return ref.get('ref')
            
            raise ValueError("No master ref found in API response")
        except requests.RequestException as e:
            print(f"Error getting API ref: {e}")
            raise
    
    def fetch_all_documents(self, ref: str) -> List[Dict]:
        """
        Fetch all documents from Prismic repository with pagination.
        
        Args:
            ref: The ref to query against
            
        Returns:
            List of all documents
        """
        all_documents = []
        page = 1
        page_size = 100  # Maximum allowed by Prismic
        
        search_url = f"{self.api_endpoint}/documents/search"
        
        print(f"Fetching documents from Prismic repository: {self.repository_name}")
        
        while True:
            try:
                params = {
                    'ref': ref,
                    'pageSize': page_size,
                    'page': page
                }
                
                if self.access_token:
                    params['access_token'] = self.access_token
                
                response = self.session.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                if not results:
                    break
                
                all_documents.extend(results)
                print(f"  Fetched page {page}: {len(results)} documents (Total: {len(all_documents)})")
                
                # Check if there are more pages
                total_pages = data.get('total_pages', 1)
                if page >= total_pages:
                    break
                
                page += 1
                
            except requests.RequestException as e:
                print(f"Error fetching documents page {page}: {e}")
                break
        
        print(f"\nTotal documents fetched: {len(all_documents)}")
        return all_documents
    
    def check_image_field(self, field_value: Any, field_path: str) -> Dict:
        """
        Check if a field is an image and extract its information.
        
        Args:
            field_value: The field value to check
            field_path: The path to this field for reporting
            
        Returns:
            Dictionary with image info if this is an image field, None otherwise
        """
        # Check if this is an image field
        if isinstance(field_value, dict):
            # Single image field
            if 'url' in field_value and field_value.get('url', '').startswith('https://images.prismic.io'):
                alt_text = field_value.get('alt', '')
                # Return info for ALL images, not just those missing alt text
                return {
                    'field_path': field_path,
                    'image_url': field_value.get('url', ''),
                    'alt_text': alt_text if alt_text else '',  # Empty string if no alt text
                    'dimensions': f"{field_value.get('dimensions', {}).get('width', 'N/A')}x{field_value.get('dimensions', {}).get('height', 'N/A')}"
                }
        
        return None
    
    def traverse_document_data(self, data: Any, parent_path: str = "") -> List[Dict]:
        """
        Recursively traverse document data to find all images.
        
        Args:
            data: The data structure to traverse
            parent_path: The current path in the document structure
            
        Returns:
            List of all images found
        """
        all_images = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{parent_path}.{key}" if parent_path else key
                
                # Check if this field is an image
                image_info = self.check_image_field(value, current_path)
                if image_info:
                    all_images.append(image_info)
                
                # Recursively check nested structures
                all_images.extend(self.traverse_document_data(value, current_path))
        
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                current_path = f"{parent_path}[{idx}]"
                
                # Check if this item is an image
                image_info = self.check_image_field(item, current_path)
                if image_info:
                    all_images.append(image_info)
                
                # Recursively check nested structures
                all_images.extend(self.traverse_document_data(item, current_path))
        
        return all_images
    
    def analyze_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Analyze all documents for images.
        
        Args:
            documents: List of Prismic documents
            
        Returns:
            List of findings with document info and all images
        """
        findings = []
        
        print("\nAnalyzing documents for images...")
        
        for idx, doc in enumerate(documents, 1):
            doc_type = doc.get('type', 'unknown')
            doc_id = doc.get('id', 'unknown')
            doc_uid = doc.get('uid', '')
            
            # Try to get document title/name from common fields
            doc_data = doc.get('data', {})
            doc_title = (
                doc_data.get('title') or 
                doc_data.get('name') or 
                doc_data.get('page_title') or
                doc_uid or
                doc_id
            )
            
            # If title is a structured text field, extract the text
            if isinstance(doc_title, list) and len(doc_title) > 0:
                doc_title = doc_title[0].get('text', doc_uid or doc_id)
            elif isinstance(doc_title, dict):
                doc_title = doc_title.get('text', doc_uid or doc_id)
            
            # Find all images in this document
            all_images = self.traverse_document_data(doc_data)
            
            if all_images:
                # Construct Prismic edit URL
                prismic_url = f"https://{self.repository_name}.prismic.io/builder/pages/{doc_id}"
                
                for image in all_images:
                    findings.append({
                        'document_id': doc_id,
                        'document_type': doc_type,
                        'document_uid': doc_uid,
                        'document_title': str(doc_title),
                        'prismic_url': prismic_url,
                        'field_path': image['field_path'],
                        'image_url': image['image_url'],
                        'alt_text': image['alt_text'],
                        'image_dimensions': image['dimensions'],
                        'last_publication_date': doc.get('last_publication_date', '')
                    })
            
            if idx % 10 == 0:
                print(f"  Analyzed {idx}/{len(documents)} documents...")
        
        # Count images missing alt text
        missing_alt_count = sum(1 for f in findings if not f['alt_text'].strip())
        print(f"\nAnalysis complete. Found {len(findings)} total images ({missing_alt_count} missing alt text).")
        return findings
    
    def save_to_csv(self, findings: List[Dict], output_file: str):
        """
        Save findings to CSV file.
        
        Args:
            findings: List of findings
            output_file: Path to output CSV file
        """
        fieldnames = [
            'document_type',
            'document_title',
            'document_uid',
            'document_id',
            'prismic_url',
            'field_path',
            'image_url',
            'alt_text',
            'image_dimensions',
            'last_publication_date'
        ]
        
        if not findings:
            print("\n✓ No images found in repository.")
            # Still create an empty CSV with headers
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
            print(f"Empty report saved to: {output_file}")
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(findings)
        
        print(f"\n✓ Report saved to: {output_file}")
        
        # Print summary statistics
        total_images = len(findings)
        missing_alt_count = sum(1 for f in findings if not f['alt_text'].strip())
        has_alt_count = total_images - missing_alt_count
        
        # Count by document type
        type_counts = {}
        type_missing_counts = {}
        for finding in findings:
            doc_type = finding['document_type']
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            if not finding['alt_text'].strip():
                type_missing_counts[doc_type] = type_missing_counts.get(doc_type, 0) + 1
        
        print(f"\nSummary:")
        print(f"  Total images found: {total_images}")
        print(f"  Images with alt text: {has_alt_count} ({100*has_alt_count/total_images:.1f}%)")
        print(f"  Images missing alt text: {missing_alt_count} ({100*missing_alt_count/total_images:.1f}%)")
        print(f"\n  Images by document type:")
        for doc_type in sorted(type_counts.keys()):
            total = type_counts[doc_type]
            missing = type_missing_counts.get(doc_type, 0)
            print(f"    {doc_type}: {total} total ({missing} missing alt text)")
    
    def run(self, output_file: str):
        """
        Run the complete alt text check process.
        
        Args:
            output_file: Path to output CSV file
        """
        try:
            # Get API ref
            ref = self.get_api_ref()
            print(f"Using API ref: {ref}\n")
            
            # Fetch all documents
            documents = self.fetch_all_documents(ref)
            
            if not documents:
                print("No documents found in repository")
                return
            
            # Analyze documents
            findings = self.analyze_documents(documents)
            
            # Save results
            self.save_to_csv(findings, output_file)
            
        except Exception as e:
            print(f"\nError: {e}")
            raise


def main():
    """Main function to run the Prismic alt text checker."""
    parser = argparse.ArgumentParser(
        description='Export all images from Prismic documents with their alt text to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Public repository (any format works)
  python find_missing_alt_text.py eisejewels
  python find_missing_alt_text.py eisejewels.prismic.io
  python find_missing_alt_text.py https://eisejewels.prismic.io
  
  # Private repository with access token
  python find_missing_alt_text.py eisejewels --token YOUR_ACCESS_TOKEN
  
  # Use environment variable for token
  export PRISMIC_ACCESS_TOKEN=your_token
  python find_missing_alt_text.py eisejewels
  
  # Custom output file
  python find_missing_alt_text.py eisejewels -o my_report.csv
        """
    )
    parser.add_argument(
        'repository',
        help='Prismic repository (e.g., eisejewels OR eisejewels.prismic.io OR https://eisejewels.prismic.io)'
    )
    parser.add_argument(
        '-t', '--token',
        help='Access token for private repositories (or set PRISMIC_ACCESS_TOKEN env var)'
    )
    parser.add_argument(
        '-o', '--output',
        default=f'prismic_missing_alt_text_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        help='Output CSV file path (default: prismic_missing_alt_text_TIMESTAMP.csv)'
    )
    
    args = parser.parse_args()
    
    # Get access token from args or environment
    access_token = args.token or os.environ.get('PRISMIC_ACCESS_TOKEN')
    
    print("=" * 70)
    print("Prismic Image Alt Text Audit")
    print("=" * 70)
    print(f"Repository: {args.repository}")
    print(f"Access token: {'***' if access_token else 'None (public repository)'}")
    print(f"Output file: {args.output}")
    print("=" * 70)
    print()
    
    # Create checker and run
    checker = PrismicAltTextChecker(args.repository, access_token)
    checker.run(args.output)
    
    print("\n" + "=" * 70)
    print("Completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
