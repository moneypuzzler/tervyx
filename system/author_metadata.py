"""
Author and Publication Metadata for TERVYX Entries
===============================================

Standardized author information and publication details for automatic inclusion
in all TERVYX entries to ensure proper attribution and reproducibility.
"""

from datetime import datetime
from typing import Dict, Any

class AuthorMetadata:
    """
    Standardized author metadata for TERVYX system
    """
    
    def __init__(self):
        # Author Information
        self.author_info = {
            "name_korean": "김건엽",
            "name_english": "KIMGEONYEOB", 
            "email": "moneypuzzler@gmail.com",
            "website": "moneypuzzler.com",
            "orcid": None,  # Add when available
            "affiliation": {
                "name": "Independent Research",
                "type": "individual_researcher"
            }
        }
        
        # Publication Information (to be updated when paper is published)
        self.publication_info = {
            "doi": None,  # To be added when published
            "preprint_doi": None,  # ArXiv/bioRxiv DOI if available
            "zenodo_doi": None,  # Zenodo dataset DOI if available
            "title": "TERVYX Protocol: Tiered Evidence Review for Yielding eXpert Classifications",
            "version": "1.0",
            "publication_date": None,  # Will be set when published
            "methodology_paper": True
        }
        
        # System Information
        self.system_info = {
            "tervyx_version": "1.0",
            "protocol_version": "TEL-5",
            "implementation": "Real-Data TERVYX System v2.0",
            "code_repository": "https://github.com/your-repo/tervyx-system",  # Update when available
            "documentation_url": "moneypuzzler.com/tervyx"
        }
    
    def get_citation_metadata(self) -> Dict[str, Any]:
        """
        Get standardized citation metadata for TERVYX entries
        """
        return {
            "@context": [
                "https://schema.org/",
                "https://w3id.org/codemeta/3.0"
            ],
            "@type": "ScholarlyArticle",
            "author": {
                "@type": "Person",
                "name": self.author_info["name_english"],
                "alternateName": self.author_info["name_korean"],
                "email": self.author_info["email"],
                "url": f"https://{self.author_info['website']}",
                "identifier": self.author_info["orcid"],  # Will be populated when available
                "affiliation": self.author_info["affiliation"]["name"]
            },
            "creator": {
                "@type": "Person", 
                "name": f"{self.author_info['name_english']} ({self.author_info['name_korean']})",
                "email": self.author_info["email"],
                "url": f"https://{self.author_info['website']}"
            },
            "citation": self._generate_citation(),
            "methodology": {
                "name": "TERVYX Protocol",
                "version": self.publication_info["version"],
                "description": "Tiered Evidence Review for Yielding eXpert Classifications",
                "implementation": self.system_info["implementation"]
            },
            "software": {
                "@type": "SoftwareApplication",
                "name": "TERVYX System",
                "version": self.system_info["tervyx_version"],
                "codeRepository": self.system_info["code_repository"],
                "author": self.author_info["name_english"],
                "programmingLanguage": "Python"
            },
            "dateCreated": datetime.now().isoformat(),
            "license": "CC-BY-4.0",  # Adjust as needed
            "reproducibility": {
                "methodology_paper_doi": self.publication_info["doi"],
                "preprint_doi": self.publication_info["preprint_doi"],
                "dataset_doi": self.publication_info["zenodo_doi"],
                "code_availability": "Open source",
                "data_availability": "Available upon request"
            }
        }
    
    def _generate_citation(self) -> str:
        """
        Generate standardized citation text
        """
        if self.publication_info["doi"]:
            return f"{self.author_info['name_english']} ({self.author_info['name_korean']}). {self.publication_info['title']}. doi: {self.publication_info['doi']}"
        else:
            return f"{self.author_info['name_english']} ({self.author_info['name_korean']}). {self.publication_info['title']}. TERVYX Protocol v{self.publication_info['version']} (In preparation)."
    
    def get_provenance_metadata(self) -> Dict[str, Any]:
        """
        Get detailed provenance information for reproducibility
        """
        return {
            "provenance": {
                "methodology": {
                    "name": "TERVYX Protocol",
                    "version": self.system_info["protocol_version"],
                    "author": f"{self.author_info['name_english']} ({self.author_info['name_korean']})",
                    "contact": self.author_info["email"],
                    "website": f"https://{self.author_info['website']}"
                },
                "implementation": {
                    "system": self.system_info["implementation"],
                    "version": self.system_info["tervyx_version"],
                    "code_repository": self.system_info["code_repository"],
                    "documentation": self.system_info["documentation_url"]
                },
                "data_sources": {
                    "literature_search": "PubMed E-utilities API",
                    "journal_quality": "Multi-source aggregated database",
                    "ai_analysis": "Gemini API (cost-optimized tiered approach)",
                    "meta_analysis": "Custom REML + Monte Carlo implementation"
                },
                "reproducibility": {
                    "seed_data_available": True,
                    "code_available": True,
                    "methodology_documented": True,
                    "api_versions_recorded": True
                }
            }
        }
    
    def update_publication_info(self, doi: str = None, preprint_doi: str = None, 
                              zenodo_doi: str = None, orcid: str = None):
        """
        Update publication information when paper is published or preprint is available
        """
        if doi:
            self.publication_info["doi"] = doi
            self.publication_info["publication_date"] = datetime.now().isoformat()
        
        if preprint_doi:
            self.publication_info["preprint_doi"] = preprint_doi
        
        if zenodo_doi:
            self.publication_info["zenodo_doi"] = zenodo_doi
            
        if orcid:
            self.author_info["orcid"] = f"https://orcid.org/{orcid}"

# Global instance for consistent metadata across all entries
AUTHOR_METADATA = AuthorMetadata()

def get_standardized_metadata() -> Dict[str, Any]:
    """
    Get complete standardized metadata for TERVYX entries
    """
    citation_meta = AUTHOR_METADATA.get_citation_metadata()
    provenance_meta = AUTHOR_METADATA.get_provenance_metadata()
    
    # Combine both metadata sets
    return {
        **citation_meta,
        **provenance_meta,
        "attribution": {
            "primary_author": f"{AUTHOR_METADATA.author_info['name_english']} ({AUTHOR_METADATA.author_info['name_korean']})",
            "contact_email": AUTHOR_METADATA.author_info["email"],
            "website": f"https://{AUTHOR_METADATA.author_info['website']}",
            "methodology_citation": AUTHOR_METADATA._generate_citation(),
            "system_version": AUTHOR_METADATA.system_info["tervyx_version"],
            "loop_reinforcement": "moneypuzzler.com → TERVYX → Publications → Citations → Recognition"
        }
    }

# Example usage and testing
if __name__ == "__main__":
    
    print("🔬 TERVYX Author Metadata System")
    print("=" * 50)
    
    # Get metadata
    metadata = get_standardized_metadata()
    
    print(f"Author: {metadata['author']['name']} ({metadata['author']['alternateName']})")
    print(f"Email: {metadata['author']['email']}")
    print(f"Website: {metadata['author']['url']}")
    print(f"Citation: {metadata['citation']}")
    print(f"System Version: {metadata['attribution']['system_version']}")
    
    print("\n📊 Provenance Information:")
    prov = metadata['provenance']
    print(f"Methodology: {prov['methodology']['name']} v{prov['methodology']['version']}")
    print(f"Implementation: {prov['implementation']['system']}")
    print(f"Contact: {prov['methodology']['contact']}")
    
    print("\n🔄 Loop Reinforcement Strategy:")
    print(metadata['attribution']['loop_reinforcement'])
    
    # Example of updating when paper is published
    print("\n🚀 Example: Updating with publication info...")
    
    # AUTHOR_METADATA.update_publication_info(
    #     doi="10.1000/example-doi",
    #     orcid="0000-0000-0000-0000",
    #     zenodo_doi="10.5281/zenodo.17364486"
    # )
    
    print("✅ Metadata system ready for integration!")
