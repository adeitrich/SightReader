import unittest
from pathlib import Path

from sightreader.pdf import format_pdf_inspection, PdfInspection


class PdfInspectionTests(unittest.TestCase):
    def test_format_includes_source_references(self):
        report = format_pdf_inspection(
            PdfInspection(
                path=Path("/tmp/score.pdf"),
                pages="1",
                title="Score",
                creator="LilyPond",
                source_files=("/tmp/score.ly",),
            )
        )

        self.assertIn("Score", report)
        self.assertIn("/tmp/score.ly", report)


if __name__ == "__main__":
    unittest.main()
