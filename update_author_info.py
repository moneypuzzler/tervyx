#!/usr/bin/env python3
"""
Author Information Update Script
==============================

Script to update author metadata when DOI, ORCID, or other publication info becomes available.
This ensures all future TERVYX entries include the latest attribution information.
"""

import os
import sys
sys.path.append('/home/user/webapp')

from system.author_metadata import AUTHOR_METADATA
import json

def update_publication_info():
    """
    Update author metadata with publication information
    """
    print("📝 TERVYX Author Information Update")
    print("=" * 50)
    
    # Current info
    print("Current Author Information:")
    print(f"  Name (EN): {AUTHOR_METADATA.author_info['name_english']}")
    print(f"  Name (KR): {AUTHOR_METADATA.author_info['name_korean']}")
    print(f"  Email: {AUTHOR_METADATA.author_info['email']}")
    print(f"  Website: {AUTHOR_METADATA.author_info['website']}")
    print(f"  ORCID: {AUTHOR_METADATA.author_info['orcid'] or 'Not set'}")
    
    print(f"\nCurrent Publication Information:")
    print(f"  DOI: {AUTHOR_METADATA.publication_info['doi'] or 'Not published yet'}")
    print(f"  Preprint DOI: {AUTHOR_METADATA.publication_info['preprint_doi'] or 'Not available'}")
    print(f"  Zenodo DOI: {AUTHOR_METADATA.publication_info['zenodo_doi'] or 'Not available'}")
    
    print("\n" + "=" * 50)
    print("🎯 UPDATE OPTIONS:")
    print("1. Add ORCID ID")
    print("2. Add Published Paper DOI")
    print("3. Add Preprint DOI (ArXiv/bioRxiv)")
    print("4. Add Zenodo Dataset DOI")
    print("5. Update all information")
    print("6. Show current citation format")
    print("0. Exit")
    
    while True:
        choice = input("\nEnter choice (0-6): ").strip()
        
        if choice == "0":
            print("👋 Exiting...")
            break
            
        elif choice == "1":
            orcid = input("Enter ORCID ID (format: 0000-0000-0000-0000): ").strip()
            if orcid and len(orcid) == 19:
                AUTHOR_METADATA.update_publication_info(orcid=orcid)
                print(f"✅ ORCID updated: https://orcid.org/{orcid}")
            else:
                print("❌ Invalid ORCID format")
        
        elif choice == "2":
            doi = input("Enter published paper DOI: ").strip()
            if doi:
                AUTHOR_METADATA.update_publication_info(doi=doi)
                print(f"✅ DOI updated: {doi}")
            else:
                print("❌ Empty DOI")
        
        elif choice == "3":
            preprint_doi = input("Enter preprint DOI (ArXiv/bioRxiv): ").strip()
            if preprint_doi:
                AUTHOR_METADATA.update_publication_info(preprint_doi=preprint_doi)
                print(f"✅ Preprint DOI updated: {preprint_doi}")
            else:
                print("❌ Empty preprint DOI")
        
        elif choice == "4":
            zenodo_doi = input("Enter Zenodo dataset DOI: ").strip()
            if zenodo_doi:
                AUTHOR_METADATA.update_publication_info(zenodo_doi=zenodo_doi)
                print(f"✅ Zenodo DOI updated: {zenodo_doi}")
            else:
                print("❌ Empty Zenodo DOI")
        
        elif choice == "5":
            print("\n📝 Comprehensive Update:")
            
            # ORCID
            orcid = input("ORCID ID (0000-0000-0000-0000) [current: {}]: ".format(
                AUTHOR_METADATA.author_info['orcid'] or 'None'
            )).strip()
            
            # DOI
            doi = input("Published paper DOI [current: {}]: ".format(
                AUTHOR_METADATA.publication_info['doi'] or 'None'
            )).strip()
            
            # Preprint
            preprint = input("Preprint DOI [current: {}]: ".format(
                AUTHOR_METADATA.publication_info['preprint_doi'] or 'None'
            )).strip()
            
            # Zenodo
            zenodo = input("Zenodo DOI [current: {}]: ".format(
                AUTHOR_METADATA.publication_info['zenodo_doi'] or 'None'
            )).strip()
            
            # Update all
            AUTHOR_METADATA.update_publication_info(
                doi=doi if doi else None,
                preprint_doi=preprint if preprint else None,
                zenodo_doi=zenodo if zenodo else None,
                orcid=orcid if orcid else None
            )
            
            print("✅ All information updated!")
        
        elif choice == "6":
            print("\n📄 Current Citation Format:")
            print(f"Citation: {AUTHOR_METADATA._generate_citation()}")
            
            metadata = AUTHOR_METADATA.get_citation_metadata()
            print(f"\nFull Attribution:")
            print(f"  Author: {metadata['author']['name']} ({metadata['author']['alternateName']})")
            print(f"  Email: {metadata['author']['email']}")
            print(f"  Website: {metadata['author']['url']}")
            print(f"  ORCID: {metadata['author']['identifier'] or 'Not set'}")
            
        else:
            print("❌ Invalid choice")
        
        # Show updated info
        if choice in ["1", "2", "3", "4", "5"]:
            print(f"\n📊 Updated Citation: {AUTHOR_METADATA._generate_citation()}")

def create_attribution_template():
    """
    Create a template file for easy attribution copying
    """
    template = f"""
# TERVYX Protocol Attribution Template

## Author Information
- **Name**: {AUTHOR_METADATA.author_info['name_english']} ({AUTHOR_METADATA.author_info['name_korean']})
- **Email**: {AUTHOR_METADATA.author_info['email']}
- **Website**: https://{AUTHOR_METADATA.author_info['website']}
- **ORCID**: {AUTHOR_METADATA.author_info['orcid'] or 'To be added'}

## Citation Format
```
{AUTHOR_METADATA._generate_citation()}
```

## For Papers/Publications
When citing the TERVYX methodology, use:
```
The analysis was conducted using the TERVYX Protocol ({AUTHOR_METADATA._generate_citation()}).
```

## For Code/Software Attribution
```
Analysis performed using TERVYX System v{AUTHOR_METADATA.system_info['tervyx_version']} 
by {AUTHOR_METADATA.author_info['name_english']} ({AUTHOR_METADATA.author_info['name_korean']}).
Contact: {AUTHOR_METADATA.author_info['email']}
```

## Loop Reinforcement Strategy
1. Each TERVYX entry includes full attribution
2. Website traffic directed to moneypuzzler.com
3. Professional recognition through methodology citation
4. Contact information ensures collaboration opportunities
5. Bilingual name ensures recognition in both Korean and international contexts

## Update Instructions
To update author information when DOI/ORCID becomes available:
```bash
cd /home/user/webapp
python update_author_info.py
```
"""
    
    with open('/home/user/webapp/ATTRIBUTION_TEMPLATE.md', 'w', encoding='utf-8') as f:
        f.write(template)
    
    print("✅ Attribution template created: ATTRIBUTION_TEMPLATE.md")

def show_loop_reinforcement_strategy():
    """
    Display the complete loop reinforcement strategy
    """
    print("\n🔄 LOOP REINFORCEMENT STRATEGY")
    print("=" * 50)
    
    print("1️⃣ TERVYX Entry Generation:")
    print(f"   → Every entry includes: {AUTHOR_METADATA.author_info['name_english']} ({AUTHOR_METADATA.author_info['name_korean']})")
    print(f"   → Contact email: {AUTHOR_METADATA.author_info['email']}")
    print(f"   → Website: https://{AUTHOR_METADATA.author_info['website']}")
    
    print("\n2️⃣ Professional Recognition:")
    print("   → Methodology citations in academic papers")
    print("   → Software attribution in research code")
    print("   → Contact requests for collaboration")
    
    print("\n3️⃣ Website Traffic Generation:")
    print(f"   → Direct links to moneypuzzler.com in every entry")
    print("   → SEO boost from academic citations")
    print("   → Portfolio demonstration of expertise")
    
    print("\n4️⃣ Identity Reinforcement:")
    print("   → Bilingual name recognition (김건엽 / KIMGEONYEOB)")
    print("   → Consistent email across all platforms")
    print("   → Professional expertise establishment")
    
    print("\n5️⃣ Loop Completion:")
    print("   → Recognition → Opportunities → More Projects → More Recognition")
    print("   → Each TERVYX entry strengthens professional reputation")
    print("   → Systematic approach to building authority in the field")

if __name__ == "__main__":
    print("🎯 TERVYX Author Information Management")
    print("📧 Contact: moneypuzzler@gmail.com")
    print("🌐 Website: moneypuzzler.com")
    print("👤 Author: KIMGEONYEOB (김건엽)")
    print()
    
    # Show current status
    print("📋 CURRENT STATUS:")
    print(f"  DOI: {AUTHOR_METADATA.publication_info['doi'] or '❌ Not published yet'}")
    print(f"  ORCID: {AUTHOR_METADATA.author_info['orcid'] or '❌ Not set'}")
    print(f"  Zenodo: {AUTHOR_METADATA.publication_info['zenodo_doi'] or '❌ Dataset not uploaded'}")
    
    print("\n🎯 RECOMMENDATIONS:")
    if not AUTHOR_METADATA.author_info['orcid']:
        print("  1. Get ORCID ID: https://orcid.org/register")
    
    if not AUTHOR_METADATA.publication_info['zenodo_doi']:
        print("  2. Upload TERVYX dataset to Zenodo for DOI")
    
    if not AUTHOR_METADATA.publication_info['doi']:
        print("  3. Submit TERVYX methodology paper to journal")
    
    print("\n" + "=" * 50)
    
    # Main menu
    print("OPTIONS:")
    print("1. Update author information")
    print("2. Create attribution template")
    print("3. Show loop reinforcement strategy")
    print("4. Test current metadata")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        update_publication_info()
    elif choice == "2":
        create_attribution_template()
    elif choice == "3":
        show_loop_reinforcement_strategy()
    elif choice == "4":
        from system.author_metadata import get_standardized_metadata
        metadata = get_standardized_metadata()
        print("\n📊 Current Metadata:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
    else:
        print("❌ Invalid choice")
    
    print(f"\n✅ Complete! All future TERVYX entries will include proper attribution.")
    print(f"🔄 Loop reinforcement active: moneypuzzler.com ← TERVYX ← Citations ← Recognition")