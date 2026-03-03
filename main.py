"""
Content Builder v1 — Main Entry Point

Usage:
    python main.py
    python main.py --input src/inputs/sample_batch.json
    python main.py --input src/inputs/sample_batch.json --output outputs/
"""

import argparse
import sys
import os

# Ensure the project root is in the path so `src.` imports work
sys.path.insert(0, os.path.dirname(__file__))

from src.core.builder import build_from_json


def main():
    parser = argparse.ArgumentParser(
        description="📸 Content Builder v1 — Generate social media images from JSON"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="src/inputs/sample_batch.json",
        help="Path to JSON batch file (default: src/inputs/sample_batch.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs",
        help="Output directory (default: outputs/)",
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)

    from datetime import datetime
    timestamp = datetime.now().strftime("%d %B %Y %H:%M:%S")
    final_output = os.path.join(args.output, timestamp)

    print("=" * 50)
    print("  📸 CONTENT BUILDER v1")
    print("=" * 50)
    print(f"  Input:  {args.input}")
    print(f"  Output: {final_output}")
    print("=" * 50)
    print()

    build_from_json(args.input, final_output)


if __name__ == "__main__":
    main()
