import json
import re


def parse_response(raw: str, output_format: str) -> str | dict:
    if output_format == "manuscript":
        return raw

    if output_format in ("structured_feedback", "skill_updates"):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(
                f"No JSON block found in LLM response for output_format='{output_format}'"
            )
        data = json.loads(match.group())

        if output_format == "skill_updates":
            if "new_rules" not in data or "failures" not in data:
                raise ValueError(
                    "skill_updates response missing required keys: 'new_rules' or 'failures'"
                )

        return data

    raise ValueError(f"Unknown output_format: '{output_format}'")
