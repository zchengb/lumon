import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "lib" / "templates" / "delivery-docs" / "templates"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "technical_plan"


def words(markdown: str) -> int:
    """Count the Latin words used by the profile size guidance."""

    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", markdown))


def headings(markdown: str) -> list[str]:
    return re.findall(r"^#{1,6} .+$", markdown, flags=re.MULTILINE)


class TechnicalPlanContractTest(unittest.TestCase):
    profiles = {
        "light": (300, 700),
        "standard": (700, 1500),
        "complex": (1200, 2500),
    }

    def read_template(self, name: str) -> str:
        return (TEMPLATE_DIR / name).read_text(encoding="utf-8")

    def read_fixture(self, name: str) -> str:
        return (FIXTURE_DIR / name).read_text(encoding="utf-8")

    def assert_no_contract_heading(self, markdown: str, *titles: str) -> None:
        for title in titles:
            self.assertNotRegex(
                markdown,
                rf"^#{1,6} {re.escape(title)}\s*$",
                msg=f"unexpected contract heading: {title}",
            )

    def test_all_profile_templates_exist_and_share_core_contract(self) -> None:
        for profile in self.profiles:
            template_name = f"technical-plan-{profile}.md"
            markdown = self.read_template(template_name)
            self.assertIn("story.md", markdown)
            self.assertIn("primary language", markdown)
            self.assertIn("**What is the problem?**", markdown)
            self.assertIn("**Decision content**", markdown)
            self.assertIn("**Decision conclusion**", markdown)
            self.assertNotIn("## Approval", markdown)
            self.assertNotIn("## Technical Plan Approval", markdown)
            self.assert_no_contract_heading(
                markdown,
                "Repository Evidence",
                "Rollback",
                "Verification Matrix",
            )

    def test_compatibility_template_is_standard(self) -> None:
        markdown = self.read_template("technical-plan.md")
        self.assertIn("Default profile: Standard", markdown)
        for section in (
            "## Goal & Scope",
            "## Technical Decisions",
            "## API & Data Design (only when applicable)",
            "## Implementation Plan",
            "## Verification",
        ):
            self.assertIn(section, markdown)
        self.assert_no_contract_heading(markdown, "Architecture", "Identifier Contract")

    def test_light_template_stays_small_and_local(self) -> None:
        markdown = self.read_template("technical-plan-light.md")
        self.assertIn("Profile: Light", markdown)
        for section in ("## Goal & Scope", "## Implementation Plan", "## Verification"):
            self.assertIn(section, markdown)
        self.assertNotIn("```mermaid", markdown)
        self.assert_no_contract_heading(
            markdown,
            "API & Data Design",
            "Database Design",
            "Architecture",
            "Performance",
        )

    def test_standard_template_contains_contract_and_grounded_schema_shapes(self) -> None:
        markdown = self.read_template("technical-plan-standard.md")
        self.assertIn("Profile: Standard", markdown)
        self.assertRegex(markdown, r"```(?:text|json)\n")
        self.assertIn("#### New table:", markdown)
        self.assertIn("#### Modified table:", markdown)
        self.assertIn(
            "| Field | Type | Length / precision | Null | Default | Key / index | Explanation |",
            markdown,
        )
        self.assertIn("CREATE/ALTER/rename migrations", markdown)

    def test_complex_template_expands_boundaries_without_mandatory_class_diagram(self) -> None:
        markdown = self.read_template("technical-plan-complex.md")
        for section in (
            "## Goal & Scope",
            "## Technical Decisions",
            "## Architecture (usually one main diagram)",
            "## API & Data Design",
            "## Implementation Plan",
            "## Verification",
        ):
            self.assertIn(section, markdown)
        self.assertIn("zero or one", markdown)
        self.assertIn("only when the class/component relationship itself is the design problem", markdown)
        self.assertIn("#### New table:", markdown)
        self.assertIn("#### Modified table:", markdown)
        self.assertNotIn("classDiagram", markdown)
        self.assert_not_contains_legacy_boilerplate(markdown)

    def test_golden_fixtures_match_profile_density(self) -> None:
        counts = {}
        for profile, (minimum, maximum) in self.profiles.items():
            markdown = self.read_fixture(f"{profile}.md")
            counts[profile] = words(markdown)
            self.assertGreaterEqual(counts[profile], minimum)
            self.assertLessEqual(counts[profile], maximum)
            self.assert_no_contract_heading(
                markdown,
                "Repository Evidence",
                "Rollback",
                "Verification Matrix",
            )
            self.assertNotIn("## Approval", markdown)
            self.assertNotIn("Technical Plan Approval", markdown)

        self.assertLess(counts["light"], counts["standard"])
        self.assertLess(counts["standard"], counts["complex"])

    def test_golden_light_fixture_has_no_heavy_design_sections(self) -> None:
        markdown = self.read_fixture("light.md")
        self.assertIn("## Goal & Scope", markdown)
        self.assertIn("## Implementation Plan", markdown)
        self.assertIn("## Verification", markdown)
        self.assertNotIn("```mermaid", markdown)
        self.assertNotIn("| Field |", markdown)
        self.assert_not_contains_legacy_boilerplate(markdown)

    def test_golden_standard_fixture_has_decision_code_and_table_contracts(self) -> None:
        markdown = self.read_fixture("standard.md")
        self.assertEqual(len(re.findall(r"^### Decision \d+:", markdown, re.MULTILINE)), 2)
        self.assertEqual(markdown.count("**Decision conclusion**"), 2)
        self.assertIn("```json", markdown)
        self.assertIn("### New table: delivery_job", markdown)
        self.assertIn("### Modified table: delivery_event", markdown)
        self.assertIn(
            "| Field | Type | Length / precision | Null | Default | Key / index | Explanation |",
            markdown,
        )

    def test_golden_complex_fixture_has_one_flow_and_schema_grounding(self) -> None:
        markdown = self.read_fixture("complex.md")
        self.assertEqual(markdown.count("```mermaid"), 1)
        self.assertIn("flowchart TB", markdown)
        self.assertNotIn("classDiagram", markdown)
        self.assertIn("### New table: delivery_job", markdown)
        self.assertIn("### Modified table: delivery_event", markdown)
        self.assertGreaterEqual(markdown.count("| Field | Type | Length / precision | Null | Default | Key / index | Explanation |"), 2)
        self.assertIn("technicalStatus", markdown)
        self.assertIn("idempotency", markdown)

    def test_decisions_define_problem_content_and_one_conclusion(self) -> None:
        for profile in self.profiles:
            markdown = self.read_fixture(f"{profile}.md")
            decision_blocks = re.split(r"(?=^### Decision \d+:)", markdown, flags=re.MULTILINE)
            for block in decision_blocks:
                if not block.startswith("### Decision"):
                    continue
                self.assertEqual(block.count("**What is the problem?**"), 1)
                self.assertEqual(block.count("**Decision content**"), 1)
                self.assertEqual(block.count("**Decision conclusion**"), 1)

    @staticmethod
    def assert_not_contains_legacy_boilerplate(markdown: str) -> None:
        for phrase in (
            "Acceptance Criteria Mapping table",
            "full identifier inventory",
            "Performance Assessment",
            "Release order",
        ):
            assert phrase not in markdown, phrase


if __name__ == "__main__":
    unittest.main()
