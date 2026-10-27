"""Small dependency-free Unicode demo for a shared-checkout DeLM task."""
import sys
import unicodedata


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "-".join("".join(char if char.isalnum() else " " for char in normalized).split())


if __name__ == "__main__":
    print(slugify(" ".join(sys.argv[1:])))
