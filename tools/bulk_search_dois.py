#!/usr/bin/env python3
"""Bulk search for DOIs using Crossref and PubMed APIs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

# Rate limiting
CROSSREF_DELAY = 0.1  # 10 req/sec (polite)
PUBMED_DELAY = 0.35   # ~3 req/sec
EUROPEPMC_DELAY = 0.2  # 5 req/sec


class DOISearcher:
    """Search for DOIs using multiple APIs."""

    def __init__(self, email: str = "research@example.com"):
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'TERVYXBot/1.0 (mailto:{email})'
        })

    def search_crossref(self, substance: str, outcome: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Crossref API for DOIs."""
        query = f"{substance} {outcome} randomized controlled trial"
        url = "https://api.crossref.org/works"

        params = {
            'query': query,
            'rows': limit,
            'filter': 'type:journal-article',
            'mailto': self.email
        }

        try:
            time.sleep(CROSSREF_DELAY)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get('message', {}).get('items', []):
                doi = item.get('DOI', '')
                if not doi:
                    continue

                title = ' '.join(item.get('title', [])) if item.get('title') else ''
                year = item.get('published-print', {}).get('date-parts', [[0]])[0][0]
                if not year:
                    year = item.get('published-online', {}).get('date-parts', [[0]])[0][0]

                cited_by = item.get('is-referenced-by-count', 0)

                results.append({
                    'doi': doi,
                    'title': title,
                    'year': year,
                    'cited_by': cited_by,
                    'source': 'crossref'
                })

            return results
        except Exception as e:
            print(f"  Crossref error: {str(e)[:100]}")
            return []

    def search_pubmed(self, substance: str, outcome: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search PubMed API for DOIs."""
        query = f"{substance} {outcome} randomized controlled trial"

        # Step 1: Search for PMIDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': limit,
            'retmode': 'json'
        }

        try:
            time.sleep(PUBMED_DELAY)
            search_response = self.session.get(search_url, params=search_params, timeout=30)
            search_response.raise_for_status()
            search_data = search_response.json()

            pmids = search_data.get('esearchresult', {}).get('idlist', [])
            if not pmids:
                return []

            # Step 2: Fetch details for PMIDs
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'json'
            }

            time.sleep(PUBMED_DELAY)
            fetch_response = self.session.get(fetch_url, params=fetch_params, timeout=30)
            fetch_response.raise_for_status()
            fetch_data = fetch_response.json()

            results = []
            for pmid in pmids:
                item = fetch_data.get('result', {}).get(pmid, {})
                if not item:
                    continue

                # Extract DOI from article IDs
                doi = None
                for article_id in item.get('articleids', []):
                    if article_id.get('idtype') == 'doi':
                        doi = article_id.get('value')
                        break

                if not doi:
                    continue

                title = item.get('title', '')
                year = int(item.get('pubdate', '2000')[:4]) if item.get('pubdate') else 2000

                results.append({
                    'doi': doi,
                    'title': title,
                    'year': year,
                    'pmid': pmid,
                    'cited_by': 0,  # PubMed doesn't provide citation counts
                    'source': 'pubmed'
                })

            return results
        except Exception as e:
            print(f"  PubMed error: {str(e)[:100]}")
            return []

    def search_europepmc(self, substance: str, outcome: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Europe PMC API for DOIs."""
        query = f"{substance} {outcome} randomized controlled trial"
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

        params = {
            'query': query,
            'format': 'json',
            'pageSize': limit
        }

        try:
            time.sleep(EUROPEPMC_DELAY)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get('resultList', {}).get('result', []):
                doi = item.get('doi', '')
                if not doi:
                    continue

                title = item.get('title', '')
                year = int(item.get('pubYear', 2000))
                cited_by = int(item.get('citedByCount', 0))
                pmid = item.get('pmid', '')

                results.append({
                    'doi': doi,
                    'title': title,
                    'year': year,
                    'cited_by': cited_by,
                    'pmid': pmid,
                    'source': 'europepmc'
                })

            return results
        except Exception as e:
            print(f"  EuropePMC error: {str(e)[:100]}")
            return []

    def rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank DOI results by quality score."""
        for result in results:
            score = 0
            title = result.get('title', '').lower()
            year = result.get('year', 0)
            cited_by = result.get('cited_by', 0)

            # Publication type scoring
            if 'meta-analysis' in title or 'meta analysis' in title:
                score += 50
            if 'systematic review' in title:
                score += 40
            if 'randomized controlled trial' in title or 'rct' in title:
                score += 30

            # Recency scoring
            if year >= 2020:
                score += 20
            elif year >= 2015:
                score += 10
            elif year >= 2010:
                score += 5

            # Citation scoring
            if cited_by > 100:
                score += 15
            elif cited_by > 50:
                score += 10
            elif cited_by > 20:
                score += 5

            result['score'] = score

        # Sort by score (descending) and remove duplicates
        seen_dois = set()
        ranked = []
        for result in sorted(results, key=lambda x: x['score'], reverse=True):
            doi = result['doi']
            if doi not in seen_dois:
                seen_dois.add(doi)
                ranked.append(result)

        return ranked


def search_entry_dois(searcher: DOISearcher, entry: Dict[str, str]) -> List[Dict[str, Any]]:
    """Search DOIs for a single entry using parallel API calls."""
    substance = entry.get('substance', '').replace('_', ' ')
    outcome = entry.get('primary_indication', '').replace('_', ' ')
    entry_id = entry.get('entry_id', 'unknown')

    print(f"🔍 {entry_id}: {substance} + {outcome}")

    # Search all APIs in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_crossref = executor.submit(searcher.search_crossref, substance, outcome, 10)
        future_pubmed = executor.submit(searcher.search_pubmed, substance, outcome, 10)
        future_pmc = executor.submit(searcher.search_europepmc, substance, outcome, 10)

        all_results = []
        all_results.extend(future_crossref.result())
        all_results.extend(future_pubmed.result())
        all_results.extend(future_pmc.result())

    # Rank and select top 3
    ranked = searcher.rank_results(all_results)
    top_3 = ranked[:3]

    print(f"   Found {len(all_results)} total, selected top {len(top_3)}")

    return top_3


def bulk_search_dois(
    entries_file: Path,
    output_csv: Path,
    max_workers: int = 5,
    limit: Optional[int] = None
) -> None:
    """Bulk search DOIs for multiple entries."""
    # Load entries
    with open(entries_file) as f:
        entries = json.load(f)

    if limit:
        entries = entries[:limit]

    print(f"📊 Searching DOIs for {len(entries)} entries...")
    print()

    searcher = DOISearcher()

    # Process entries with rate limiting
    results_map = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entry = {
            executor.submit(search_entry_dois, searcher, entry): entry
            for entry in entries
        }

        for future in as_completed(future_to_entry):
            entry = future_to_entry[future]
            entry_id = entry.get('entry_id', 'unknown')

            try:
                dois = future.result()
                results_map[entry_id] = {
                    'entry': entry,
                    'dois': dois
                }
            except Exception as e:
                print(f"❌ {entry_id}: {str(e)[:100]}")
                results_map[entry_id] = {
                    'entry': entry,
                    'dois': []
                }

    # Write results to CSV
    rows = []
    for entry_id, data in results_map.items():
        entry = data['entry']
        dois = data['dois']

        for i, doi_data in enumerate(dois, 1):
            rows.append({
                'entry_id': entry_id,
                'study_id': f"{entry_id}_{i:02d}",
                'substance': entry.get('substance', ''),
                'category': entry.get('category', ''),
                'indication': entry.get('primary_indication', ''),
                'doi': doi_data.get('doi', ''),
                'pmid': doi_data.get('pmid', ''),
                'year': doi_data.get('year', ''),
                'score': doi_data.get('score', 0),
                'source': doi_data.get('source', ''),
                'notes': doi_data.get('title', '')[:100]
            })

    # Write CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'entry_id', 'study_id', 'substance', 'category', 'indication',
            'doi', 'pmid', 'year', 'score', 'source', 'notes'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"✅ Saved {len(rows)} DOI mappings to {output_csv}")
    print()

    # Summary
    found_count = sum(1 for data in results_map.values() if len(data['dois']) > 0)
    complete_count = sum(1 for data in results_map.values() if len(data['dois']) >= 3)

    print(f"📈 Summary:")
    print(f"   Entries processed: {len(entries)}")
    print(f"   Entries with DOIs: {found_count}")
    print(f"   Entries with 3+ DOIs: {complete_count}")
    print(f"   Total DOIs found: {len(rows)}")


def main():
    parser = argparse.ArgumentParser(description="Bulk search for DOIs")
    parser.add_argument('--entries', type=Path, required=True, help='JSON file with entries')
    parser.add_argument('--output', type=Path, required=True, help='Output CSV file')
    parser.add_argument('--limit', type=int, help='Limit number of entries to process')
    parser.add_argument('--workers', type=int, default=5, help='Max parallel workers')

    args = parser.parse_args()

    bulk_search_dois(
        entries_file=args.entries,
        output_csv=args.output,
        max_workers=args.workers,
        limit=args.limit
    )


if __name__ == '__main__':
    main()
