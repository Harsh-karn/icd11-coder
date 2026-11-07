#!/usr/bin/env python3
"""Main CLI entrypoint for ICD-11 coding system."""
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline import ICD11Pipeline

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m src.main <input_notes.jsonl> <output_predictions.jsonl>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Resolve paths to project root if running locally
    pipeline = ICD11Pipeline(
        enriched_path=os.path.join(os.path.dirname(__file__), "..", "data", "enriched_mms.json"),
        emb_path=os.path.join(os.path.dirname(__file__), "..", "data", "icd11_embeddings.npy"),
        model_path=os.path.join(os.path.dirname(__file__), "..", "data", "minilm_model")
    )
    pipeline.process_file(input_path, output_path)

if __name__ == "__main__":
    main()

