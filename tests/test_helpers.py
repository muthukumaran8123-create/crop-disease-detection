import unittest

from disease_guide import get_disease_guide, readable_label
from train_model import discover_class_directory
from pathlib import Path
import tempfile


class DiseaseGuideTests(unittest.TestCase):
    def test_readable_label(self):
        self.assertEqual(readable_label("Apple___Apple_scab"), ("Apple", "Scab"))
        self.assertEqual(readable_label("Tomato___Tomato_Yellow_Leaf_Curl_Virus"), ("Tomato", "Yellow Leaf Curl Virus"))
        self.assertEqual(readable_label("Tomato___healthy"), ("Tomato", "Appears Healthy"))

    def test_healthy_guide(self):
        guide = get_disease_guide("Tomato___healthy")
        self.assertIn("Healthy", guide["category"])

    def test_discovers_nested_class_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "color"
            for class_name in ("Crop___disease", "Crop___healthy"):
                folder = root / class_name
                folder.mkdir(parents=True)
                (folder / "leaf.jpg").write_bytes(b"placeholder")
            self.assertEqual(discover_class_directory(Path(temp_dir)), root)


if __name__ == "__main__":
    unittest.main()
