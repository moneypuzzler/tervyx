"""
Complete Real-Data TERVYX Pipeline
===============================

Integrated pipeline that combines all components:
1. PubMed paper search and metadata extraction
2. AI-powered abstract analysis and gate evaluation
3. Journal quality assessment
4. Real meta-analysis with REML + Monte Carlo
5. TEL-5 classification and TERVYX entry generation

Production-ready system for generating actual TERVYX entries using real scientific literature.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import system components
from .pubmed_integration import PubMedAPI, PubMedPaper
from .cost_optimized_analyzer import CostOptimizedAnalyzer  # NEW: Cost-optimized AI analysis
from .journal_quality_db import JournalQualityDatabase
from .real_meta_analysis import RealMetaAnalyzer, generate_real_tervyx_entry


class RealTERVYXPipeline:
    """Complete pipeline for generating TERVYX entries using real literature data."""

    def __init__(self, email: str, gemini_api_key: str, ncbi_api_key: Optional[str] = None) -> None:
        """Initialize pipeline with required API keys and configuration."""

        self.email = email
        self.gemini_api_key = gemini_api_key
        self.ncbi_api_key = ncbi_api_key

        # Initialize components
        self.pubmed_api = PubMedAPI(email, api_key=ncbi_api_key)
        self.ai_analyzer = CostOptimizedAnalyzer(gemini_api_key)  # NEW: Cost-optimized analyzer
        self.journal_db = JournalQualityDatabase()
        self.meta_analyzer = RealMetaAnalyzer()

        # Configuration (tuned for real-data production runs)
        self.config: Dict[str, Any] = {
            "max_papers_search": 100,
            "max_papers_analyze": 30,
            "min_papers_meta_analysis": 3,
            "analysis_timeout_minutes": 30,
            "relevance_threshold": 0.6,
            "confidence_threshold": 0.7,
            "batch_delay_seconds": 30,
        }

    async def generate_entry(self, substance: str, outcome_category: str) -> Dict[str, Any]:
        """Generate complete TERVYX entry using real literature data."""

        start_time = datetime.now()

        try:
            print(f"\n🚀 Starting Real TERVYX Analysis: {substance} + {outcome_category}")
            print(f"⏰ Started at: {start_time.isoformat()}")

            # Step 1: Search PubMed for relevant papers
            print("\n📚 Step 1: Searching PubMed...")

            pmids = await self.pubmed_api.search_papers(
                substance=substance,
                outcome=outcome_category,
                max_results=self.config["max_papers_search"],
            )

            if not pmids:
                return {
                    "error": "No papers found in PubMed search",
                    "substance": substance,
                    "outcome_category": outcome_category,
                    "search_results": 0,
                }

            print(f"✅ Found {len(pmids)} papers")

            # Step 2: Fetch detailed paper metadata
            print("\n📄 Step 2: Fetching paper metadata...")

            papers = await self.pubmed_api.fetch_detailed_metadata(
                pmids[: self.config["max_papers_analyze"]],
                substance=substance,
                outcome=outcome_category,
            )

            if len(papers) < 2:
                return {
                    "error": "Insufficient papers with complete metadata",
                    "substance": substance,
                    "outcome_category": outcome_category,
                    "papers_found": len(pmids),
                    "papers_with_metadata": len(papers),
                }

            print(f"✅ Retrieved metadata for {len(papers)} papers")

            # Step 3: AI analysis of abstracts (tiered cost optimized)
            print("\n🤖 Step 3: AI analysis of abstracts...")

            analyses = await self.ai_analyzer.process_batch_optimized(
                papers=papers,
                substance=substance,
                outcome_category=outcome_category,
                relevance_threshold=self.config["relevance_threshold"],
                confidence_threshold=self.config["confidence_threshold"],
            )

            if len(analyses) < self.config["min_papers_meta_analysis"]:
                return {
                    "error": "Insufficient successful AI analyses for meta-analysis",
                    "substance": substance,
                    "outcome_category": outcome_category,
                    "papers_analyzed": len(papers),
                    "successful_analyses": len(analyses),
                    "required_minimum": self.config["min_papers_meta_analysis"],
                }

            included_analyses = [analysis for analysis in analyses if analysis.inclusion_recommendation]

            if len(included_analyses) < self.meta_analyzer.min_studies:
                return {
                    "error": "Not enough includable studies after AI review",
                    "substance": substance,
                    "outcome_category": outcome_category,
                    "successful_analyses": len(analyses),
                    "included_analyses": len(included_analyses),
                    "required_minimum": self.meta_analyzer.min_studies,
                }

            print(
                f"✅ Successfully analyzed {len(analyses)} abstracts "
                f"({len(included_analyses)} includable)"
            )

            # Step 4: Journal quality assessment (only includable PMIDs)
            print("\n🏛️ Step 4: Assessing journal quality...")

            includable_pmids = {analysis.paper_pmid for analysis in included_analyses}
            journal_assessments: Dict[str, Any] = {}

            for paper in papers:
                if paper.pmid not in includable_pmids:
                    continue
                if not paper.journal_issn:
                    continue

                assessment = await self.journal_db.assess_journal(
                    issn=paper.journal_issn,
                    title=paper.journal,
                )

                if assessment is not None:
                    journal_assessments[paper.pmid] = assessment

            print(f"✅ Assessed {len(journal_assessments)} journals")

            # Step 5: Meta-analysis and entry generation
            print("\n📊 Step 5: Performing meta-analysis...")

            entry = await generate_real_tervyx_entry(
                substance=substance,
                outcome_category=outcome_category,
                analyses=included_analyses,
                journal_assessments=journal_assessments,
            )

            if "error" in entry:
                return {
                    **entry,
                    "pipeline_step": "meta_analysis",
                    "analyses_input": len(analyses),
                    "included_ai_analyses": len(included_analyses),
                    "journal_assessments_input": len(journal_assessments),
                }

            # Step 6: Add pipeline metadata
            processing_time = (datetime.now() - start_time).total_seconds()

            entry["pipeline_metadata"] = {
                "processing_time_seconds": processing_time,
                "pubmed_search_results": len(pmids),
                "papers_with_metadata": len(papers),
                "successful_ai_analyses": len(analyses),
                "included_ai_analyses": len(included_analyses),
                "journal_assessments": len(journal_assessments),
                "pipeline_version": "v1.1-real-data",
                "components_used": {
                    "pubmed_api": True,
                    "gemini_ai": True,
                    "journal_quality_db": True,
                    "reml_monte_carlo": True,
                },
                "data_sources": {
                    "literature_search": "PubMed E-utilities",
                    "ai_analysis": "Gemini Tiered (Flash-Lite + Flash + Pro)",
                    "journal_quality": "Multi-source aggregated",
                    "meta_analysis": "TERVYX REML+MC Engine",
                },
            }

            print(
                f"\n🎉 SUCCESS: Generated TEL-{entry['tier']} entry ({entry['label']})"
            )
            print(
                "📊 Evidence: "
                f"{entry['evidence_summary']['n_studies']} studies, "
                f"{entry['evidence_summary']['total_n']} participants"
            )
            print(f"⏱️ Total processing time: {processing_time:.1f} seconds")

            return entry

        except Exception as exc:  # pragma: no cover - defensive logging path
            error_info = {
                "error": f"Pipeline failed: {exc}",
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
                "substance": substance,
                "outcome_category": outcome_category,
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }

            print(f"\n💥 PIPELINE FAILED: {exc}")

            return error_info

    async def generate_multiple_entries(
        self,
        substance_outcome_pairs: List[Tuple[str, str]],
        output_dir: str = "/home/user/webapp/entries_real",
    ) -> Dict[str, Any]:
        """Generate multiple TERVYX entries in batch."""

        print(f"\n🚀 Batch Generation: {len(substance_outcome_pairs)} entries")

        results: Dict[str, Any] = {
            "successful_entries": [],
            "failed_entries": [],
            "summary": {},
        }

        os.makedirs(output_dir, exist_ok=True)
        delay_seconds = self.config.get("batch_delay_seconds", 30)

        for index, (substance, outcome_category) in enumerate(substance_outcome_pairs):
            print("\n" + "=" * 60)
            print(
                f"Processing {index + 1}/{len(substance_outcome_pairs)}: "
                f"{substance} + {outcome_category}"
            )
            print("=" * 60)

            try:
                entry = await self.generate_entry(substance, outcome_category)

                if "error" in entry:
                    results["failed_entries"].append(
                        {
                            "substance": substance,
                            "outcome_category": outcome_category,
                            "error": entry["error"],
                        }
                    )
                else:
                    entry_dir = os.path.join(
                        output_dir, f"nutrient/{substance}/{outcome_category}/v1"
                    )
                    os.makedirs(entry_dir, exist_ok=True)

                    # Save entry files (exclude heavy metadata for entry.jsonld)
                    clean_entry = {
                        key: value
                        for key, value in entry.items()
                        if key not in {"real_studies", "pipeline_metadata"}
                    }

                    with open(os.path.join(entry_dir, "entry.jsonld"), "w", encoding="utf-8") as file:
                        json.dump(clean_entry, file, indent=2, ensure_ascii=False)

                    with open(
                        os.path.join(entry_dir, "analysis_detailed.json"),
                        "w",
                        encoding="utf-8",
                    ) as file:
                        json.dump(entry, file, indent=2, default=str, ensure_ascii=False)

                    results["successful_entries"].append(
                        {
                            "substance": substance,
                            "outcome_category": outcome_category,
                            "tier": entry["tier"],
                            "label": entry["label"],
                            "n_studies": entry["evidence_summary"]["n_studies"],
                        }
                    )

                    print(f"✅ Saved to {entry_dir}")

            except Exception as exc:  # pragma: no cover - defensive logging path
                print(
                    f"💥 Failed to process {substance} + {outcome_category}: {exc}"
                )
                results["failed_entries"].append(
                    {
                        "substance": substance,
                        "outcome_category": outcome_category,
                        "error": str(exc),
                    }
                )

            # Rate limiting between entries
            if index < len(substance_outcome_pairs) - 1:
                print(f"⏳ Waiting {delay_seconds} seconds before next entry...")
                await asyncio.sleep(delay_seconds)

        # Generate summary
        successful = len(results["successful_entries"])
        failed = len(results["failed_entries"])

        results["summary"] = {
            "total_attempted": len(substance_outcome_pairs),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(substance_outcome_pairs)) * 100
            if substance_outcome_pairs
            else 0.0,
            "tier_distribution": {},
            "label_distribution": {},
        }

        for entry in results["successful_entries"]:
            tier = entry["tier"]
            label = entry["label"]
            results["summary"]["tier_distribution"][tier] = (
                results["summary"]["tier_distribution"].get(tier, 0) + 1
            )
            results["summary"]["label_distribution"][label] = (
                results["summary"]["label_distribution"].get(label, 0) + 1
            )

        with open(os.path.join(output_dir, "batch_results.json"), "w", encoding="utf-8") as file:
            json.dump(results, file, indent=2, ensure_ascii=False)

        print("\n📊 BATCH COMPLETE:")
        print(
            f"   Successful: {successful}/{len(substance_outcome_pairs)} "
            f"({results['summary']['success_rate']:.1f}%)"
        )
        print(f"   Results saved to: {output_dir}")

        return results

    def validate_configuration(self) -> Dict[str, bool]:
        """Validate that all required components are properly configured."""

        validation = {
            "pubmed_api": False,
            "gemini_api": False,
            "journal_db": False,
            "meta_analyzer": False,
            "overall": False,
        }

        try:
            validation["pubmed_api"] = bool(self.email and "@" in self.email)
            validation["gemini_api"] = bool(
                self.gemini_api_key and len(self.gemini_api_key) > 10
            )
            validation["journal_db"] = os.path.exists(
                os.path.dirname(getattr(self.journal_db, "db_path", "")) or "/"
            )
            validation["meta_analyzer"] = hasattr(
                self.meta_analyzer, "perform_full_analysis"
            )
            validation["overall"] = all(
                [
                    validation["pubmed_api"],
                    validation["gemini_api"],
                    validation["journal_db"],
                    validation["meta_analyzer"],
                ]
            )

        except Exception as exc:  # pragma: no cover - defensive logging path
            print(f"⚠️ Validation error: {exc}")

        return validation


# ============================================================================
# Production Usage Examples
# ============================================================================


async def run_priority_substances() -> Dict[str, Any]:
    """Generate entries for high-priority substances with substantial literature."""

    # Check environment variables
    email = os.getenv("TERVYX_EMAIL", "your-email@domain.com")
    gemini_key = os.getenv("GEMINI_API_KEY")
    ncbi_key = os.getenv("NCBI_API_KEY")  # Optional

    if not gemini_key or gemini_key == "your-api-key-here":
        print("❌ Missing GEMINI_API_KEY environment variable")
        print("   Set with: export GEMINI_API_KEY='your-actual-api-key'")
        return {}

    if email == "your-email@domain.com":
        print("❌ Update TERVYX_EMAIL environment variable with your real email")
        return {}

    # Initialize pipeline
    pipeline = RealTERVYXPipeline(
        email=email,
        gemini_api_key=gemini_key,
        ncbi_api_key=ncbi_key,
    )

    # Validate configuration
    validation = pipeline.validate_configuration()
    if not validation["overall"]:
        print(f"❌ Configuration validation failed: {validation}")
        return {}

    print("✅ Pipeline configuration validated")

    # Priority substances with strong literature base
    priority_pairs = [
        # Sleep category - well-researched substances
        ("melatonin", "sleep"),
        ("magnesium", "sleep"),
        ("valerian", "sleep"),
        # Cognition category - nootropics with RCT evidence
        ("omega-3", "cognition"),
        ("ginkgo", "cognition"),
        ("bacopa", "cognition"),
        # Mental health - supplements with psychiatric research
        ("st-john-wort", "mental_health"),
        ("omega-3", "mental_health"),
        ("saffron", "mental_health"),
        # Cardiovascular - heart health supplements
        ("omega-3", "cardiovascular"),
        ("coq10", "cardiovascular"),
        ("garlic", "cardiovascular"),
        # Renal safety - known nephrotoxic substances
        ("aristolochic-acid", "renal_safety"),
        ("nsaids", "renal_safety"),
    ]

    print(f"\n🎯 Generating {len(priority_pairs)} high-priority TERVYX entries...")

    # Run batch generation
    results = await pipeline.generate_multiple_entries(priority_pairs)

    print("\n🏁 FINAL RESULTS:")
    print(f"   ✅ Successful: {results['summary']['successful']}")
    print(f"   ❌ Failed: {results['summary']['failed']}")
    print(f"   📊 Success Rate: {results['summary']['success_rate']:.1f}%")

    if results["summary"]["tier_distribution"]:
        print("   🏆 Tier Distribution:")
        for tier, count in results["summary"]["tier_distribution"].items():
            print(f"      {tier}: {count}")

    return results


async def test_single_entry() -> Dict[str, Any]:
    """Test pipeline with a single well-studied substance."""

    email = os.getenv("TERVYX_EMAIL", "test@example.com")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not gemini_key:
        print("⚠️ No Gemini API key found - running validation test only")

        pipeline = RealTERVYXPipeline(
            email=email,
            gemini_api_key="test-key",
            ncbi_api_key=None,
        )

        validation = pipeline.validate_configuration()
        print(f"Pipeline validation: {validation}")
        return {}

    pipeline = RealTERVYXPipeline(
        email=email,
        gemini_api_key=gemini_key,
    )

    print("🧪 Testing with melatonin + sleep (well-studied combination)")

    entry = await pipeline.generate_entry("melatonin", "sleep")

    if "error" not in entry:
        print(f"\n✅ SUCCESS: Generated TEL-{entry['tier']} entry")
        print(f"   Label: {entry['label']}")
        print(f"   Studies: {entry['evidence_summary']['n_studies']}")
        print(f"   Participants: {entry['evidence_summary']['total_n']}")
        print(
            "   Processing time: "
            f"{entry['pipeline_metadata']['processing_time_seconds']:.1f}s"
        )

        with open(
            "/home/user/webapp/system/test_real_entry.json", "w", encoding="utf-8"
        ) as file:
            json.dump(entry, file, indent=2, default=str, ensure_ascii=False)

        print("   Saved to: test_real_entry.json")
    else:
        print(f"\n❌ FAILED: {entry['error']}")

    return entry


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "full":
        asyncio.run(run_priority_substances())
    else:
        asyncio.run(test_single_entry())
