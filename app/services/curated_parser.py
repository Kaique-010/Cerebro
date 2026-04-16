import re
import ast
from pathlib import Path


class CuratedParserService:
    def parse_file(self, file_path: Path) -> dict:
        raw = file_path.read_text(encoding="utf-8").strip()

        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
        if not frontmatter_match:
            return {
                "metadata": {},
                "body": raw,
            }

        frontmatter_text = frontmatter_match.group(1).strip()
        body = frontmatter_match.group(2).strip()

        metadata = self.parse_frontmatter(frontmatter_text)

        return {
            "metadata": metadata,
            "body": body,
        }

    def parse_frontmatter(self, text: str) -> dict:
        data = {}

        for line in text.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value.startswith("[") and value.endswith("]"):
                try:
                    data[key] = ast.literal_eval(value)
                except Exception:
                    data[key] = value
            elif value.lower() in {"true", "false"}:
                data[key] = value.lower() == "true"
            elif value.isdigit():
                data[key] = int(value)
            else:
                data[key] = value.strip('"').strip("'")

        return data