import sys
import yaml

def validate_metadata(markdown_path):
    """Check if YAML metadata in Markdown file is valid."""
    try:
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract YAML front matter (between --- delimiters)
        if not content.startswith("---"):
            print(f"No metadata block found at start of {markdown_path}")
            return

        end_idx = content.find("\n---")
        if end_idx == -1:
            print(f"Missing closing '---' for metadata in {markdown_path}")
            return

        # Extract YAML content
        yaml_block = content[3:end_idx].strip()
        
        try:
            # Attempt to parse YAML (raises error on invalid syntax)
            yaml.safe_load(yaml_block)
            print(f"Valid YAML metadata in {markdown_path}")
        except yaml.YAMLError as e:
            print(f"Invalid YAML syntax in {markdown_path}:")
            print(f"  Error: {e}")

    except Exception as e:
        print(f"Unexpected error processing {markdown_path}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_metadata.py <path_to_markdown_file.md>")
        sys.exit(1)

    markdown_path = sys.argv[1]
    validate_metadata(markdown_path)
