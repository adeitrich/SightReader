import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from sightreader.corrections import _apply_mxl_corrections


class CorrectionTests(unittest.TestCase):
    def test_apply_mxl_pitch_and_tie_corrections(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise>
  <part>
    <measure number="25">
      <note default-x="92">
        <pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>2</duration><type>quarter</type>
      </note>
      <note default-x="134">
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>1</duration><type>eighth</type><accidental>natural</accidental>
      </note>
    </measure>
  </part>
</score-partwise>
"""
        corrections = {
            "operations": [
                {
                    "action": "add_tie",
                    "match": {
                        "measure": 25,
                        "default_x": 92,
                        "step": "B",
                        "alter": "-1",
                        "octave": 4,
                    },
                    "type": "start",
                },
                {
                    "action": "set_pitch",
                    "match": {
                        "measure": 25,
                        "default_x": 134,
                        "step": "B",
                        "octave": 4,
                    },
                    "step": "B",
                    "alter": -1,
                    "octave": 4,
                    "accidental": "flat",
                },
                {
                    "action": "add_tie",
                    "match": {
                        "measure": 25,
                        "default_x": 134,
                        "step": "B",
                        "alter": "-1",
                        "octave": 4,
                    },
                    "type": "stop",
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            mxl_path = Path(tmp) / "score.mxl"
            with ZipFile(mxl_path, "w") as archive:
                archive.writestr("score.xml", xml)

            applied = _apply_mxl_corrections(mxl_path, corrections)

            self.assertEqual(len(applied), 3)
            with ZipFile(mxl_path) as archive:
                root = ET.fromstring(archive.read("score.xml"))
            notes = root.findall(".//note")
            corrected = notes[1]
            self.assertEqual(corrected.find("pitch/alter").text, "-1")
            self.assertEqual(corrected.find("accidental").text, "flat")
            self.assertEqual(corrected.find("tie").attrib["type"], "stop")
            self.assertEqual(notes[0].find("tie").attrib["type"], "start")


if __name__ == "__main__":
    unittest.main()
