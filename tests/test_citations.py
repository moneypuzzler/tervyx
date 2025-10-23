import unittest

from engine.citations import build_citations_payload, compute_manifest_hash, to_entry_references


class CitationNormalizationTests(unittest.TestCase):
    def test_duplicates_are_deduplicated_and_sorted(self):
        evidence_rows = [
            {
                "study_id": "StudyB",
                "year": 2022,
                "design": "randomized controlled trial",
                "journal_id": "ISSN:0161-8105",
                "outcome": "psqi_total",
                "population": "adults with insomnia",
                "adverse_events": "none",
                "doi": "10.2000/zzz",
                "pmid": None,
            },
            {
                "study_id": "StudyA",
                "year": 2021,
                "design": "randomized controlled trial",
                "journal_id": "ISSN:1389-9457",
                "outcome": "psqi_total",
                "population": "adults with insomnia",
                "adverse_events": "none",
                "doi": "https://doi.org/10.1000/xxx",
                "pmid": "12345678",
            },
            {
                "study_id": "StudyC",
                "year": 2023,
                "design": "randomized controlled trial",
                "journal_id": "ISSN:1389-9457",
                "outcome": "psqi_total",
                "population": "adults with insomnia",
                "adverse_events": "none",
                "doi": "10.1000/xxx",
                "pmid": None,
            },
        ]

        payload = build_citations_payload(
            evidence_rows,
            policy_fingerprint="0x1234567890abcdef",
            evidence_path="entries/example/evidence.csv",
            preferred_citation="Example",
        )

        # Studies should be sorted alphabetically by study_id
        self.assertEqual(
            [study["study_id"] for study in payload["studies"]],
            ["StudyA", "StudyB", "StudyC"],
        )

        # References should be deduplicated by identifier and sorted
        references = payload["references"]
        self.assertEqual(len(references), 3)
        self.assertEqual(references[0]["type"], "doi")
        self.assertEqual(references[0]["identifier"], "10.1000/xxx")
        self.assertEqual(references[0]["study_ids"], ["StudyA", "StudyC"])
        self.assertEqual(references[1]["identifier"], "10.2000/zzz")
        self.assertEqual(references[2]["type"], "pmid")
        self.assertEqual(references[2]["identifier"], "12345678")
        self.assertEqual(references[2]["study_ids"], ["StudyA"])

        # Manifest hash should validate against recomputation
        self.assertEqual(payload["manifest_hash"], compute_manifest_hash(payload))

        entry_references = to_entry_references(payload)
        self.assertEqual(entry_references[0]["studyIds"], ["StudyA", "StudyC"])
        self.assertTrue(entry_references[0]["@id"].startswith("doi:10.1000/xxx"))
        self.assertEqual(entry_references[1]["@id"], "doi:10.2000/zzz")
        self.assertEqual(entry_references[2]["@id"], "pmid:12345678")
        self.assertEqual(entry_references[2]["studyIds"], ["StudyA"])


if __name__ == "__main__":
    unittest.main()
