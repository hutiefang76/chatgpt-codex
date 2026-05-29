import unittest

from chatgpt_codex.openapi import make_openapi_document


class OpenApiTests(unittest.TestCase):
    def test_openapi_has_explicit_object_schemas_for_action_responses(self):
        document = make_openapi_document("https://actions.example.com")

        self.assertEqual(document["servers"][0]["url"], "https://actions.example.com")
        for path in ["/list_files", "/read_file", "/search_text", "/write_file", "/apply_patch", "/exec_command"]:
            with self.subTest(path=path):
                response = document["paths"][path]["post"]["responses"]["200"]
                schema = response["content"]["application/json"]["schema"]
                self.assertIn("$ref", schema)

        components = document["components"]["schemas"]
        for schema_name in ["FileListingResult", "ReadFileResult", "SearchResult", "WriteFileResult", "PatchResult", "CommandResult"]:
            with self.subTest(schema_name=schema_name):
                self.assertEqual(components[schema_name]["type"], "object")
                self.assertIn("properties", components[schema_name])
                self.assertTrue(components[schema_name]["properties"])

    def test_openapi_declares_bearer_auth_for_mutating_and_read_actions(self):
        document = make_openapi_document("https://actions.example.com")

        self.assertIn("bearerAuth", document["components"]["securitySchemes"])
        for path, methods in document["paths"].items():
            if path in ["/health", "/openapi.json", "/privacy"]:
                continue
            self.assertEqual(methods["post"]["security"], [{"bearerAuth": []}])


if __name__ == "__main__":
    unittest.main()

