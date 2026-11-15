import ast
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from product_listing_helpers import generate_listing, parse_listing, prepare_products


LISTING = {"title": "Navy shirt", "description": "A navy shirt with a check pattern.",
           "features": ["Navy blue", "Check pattern"], "keywords": "navy, shirt"}


def client_for(content, finish_reason="stop", refusal=None, choices=True):
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content, refusal=refusal),
        finish_reason=finish_reason)] if choices else [])
    create = Mock(return_value=response)
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "product.jpg"
        self.image.write_bytes(b"test image bytes")

    def call(self, client, image=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return generate_listing(client, "Describe this image.", image or self.image)

    def test_local_fallback_has_columns_used_by_later_cells(self):
        rows = prepare_products([{"id": 1, "name": "Local shirt", "category": "Apparel",
                                  "image_path": str(self.image)}])
        self.assertEqual(rows[0]["productDisplayName"], "Local shirt")
        self.assertEqual(rows[0]["masterCategory"], "Apparel")
        self.assertEqual(rows[0]["baseColour"], "Not specified")
        self.assertEqual(rows[0]["image_path"], str(self.image))

    def test_embedded_image_ids_cannot_escape_output_directory(self):
        class Image:
            def convert(self, mode):
                return self

            def save(self, path):
                Path(path).write_bytes(b"image")

        directory = Path(self.temp.name) / "output"
        rows = prepare_products([{"id": "../outside", "name": "Image", "image": Image()}], directory)
        self.assertEqual(Path(rows[0]["image_path"]).parent, directory)
        self.assertFalse((Path(self.temp.name) / "outside.jpg").exists())

    def test_missing_local_image_fails_before_api_work(self):
        with self.assertRaises(FileNotFoundError):
            prepare_products([{"id": 1, "name": "Missing", "image_path": "missing.jpg"}])

    def test_empty_dataset_is_explicit(self):
        with self.assertRaises(ValueError):
            prepare_products([])

    def test_valid_json_and_code_fence(self):
        text = json.dumps(LISTING)
        self.assertEqual(parse_listing(text), LISTING)
        self.assertEqual(parse_listing("```json\n" + text + "\n```"), LISTING)

    def test_wrong_json_shapes_are_not_successes(self):
        for value in ("null", "[]", "{}", "not JSON", None,
                      json.dumps({**LISTING, "features": "not a list"})):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_listing(value)

    def test_success_sends_image_and_prompt(self):
        client = client_for(json.dumps(LISTING))
        self.assertEqual(self.call(client), LISTING)
        request = client.chat.completions.create.call_args.kwargs
        parts = request["messages"][0]["content"]
        self.assertEqual(parts[0]["text"], "Describe this image.")
        self.assertTrue(parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

    def test_missing_image_does_not_abort_batch_or_call_api(self):
        client = client_for(json.dumps(LISTING))
        self.assertIsNone(self.call(client, Path(self.temp.name) / "missing.jpg"))
        client.chat.completions.create.assert_not_called()
        self.assertEqual(self.call(client), LISTING)

    def test_empty_and_refused_responses_do_not_raise(self):
        self.assertIsNone(self.call(client_for(None, choices=False)))
        self.assertIsNone(self.call(client_for(None, refusal="declined")))
        self.assertIn("raw_response", self.call(client_for(None)))

    def test_truncated_json_is_not_counted_as_success(self):
        result = self.call(client_for(json.dumps(LISTING), finish_reason="length"))
        self.assertIn("raw_response", result)

    def test_api_error_does_not_print_request_details(self):
        client = client_for(None)
        client.chat.completions.create.side_effect = RuntimeError("sensitive-request-detail")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertIsNone(generate_listing(client, "prompt", self.image))
        self.assertNotIn("sensitive-request-detail", output.getvalue())

    def test_every_notebook_code_cell_compiles(self):
        path = Path(__file__).resolve().parents[1] / "lab_proof_Carolina.ipynb"
        notebook = json.loads(path.read_text())
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell-{index}")


if __name__ == "__main__":
    unittest.main()
