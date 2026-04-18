def parse_response(raw: str, output_format: str) -> str:
    if output_format == "manuscript":
        return raw.strip()

    raise ValueError(f"Unknown output_format: '{output_format}'")
