# API Calling to ChatGPT

**Track:** Module 1 — Generative AI & APIs · **When:** Week 2, Day 1 · **Status:** Required

This repository contains everything you need for this lab.

## Files

- [`instructions.md`](./instructions.md) — the lab instructions
- [`rubric.md`](./rubric.md) — how your submission is graded; this is what the AI reviewer checks your PR against

## How to complete this lab

1. **Fork** this repository.
2. Do the work described in `instructions.md`, committing to your fork.
3. Open a **pull request** back into this repository.
4. You'll receive **AI feedback** on your PR based on `rubric.md`. Address any blocking feedback and push updates to the same PR.

## Submission hygiene

- Keep this repository scoped to this lab only — no unrelated projects or personal files.
- Use clear, descriptive filenames.
- Remove secrets, API keys, and tokens before committing.

## Run the product-listing notebook

Requires Python 3.10 or newer. Run these commands from the repository root:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m jupyterlab lab_proof_Carolina.ipynb
```

Set `OPENAI_API_KEY` in your environment or in a local `.env` file. Never commit
that file. Running the API cells requires your own API access and may incur charges.
Run the notebook cells in order. Generated listings are written to `listings.json`;
images are saved under `product_images/`. These outputs are not currently included
in the repository. Historical evidence is in `lab_proof.md`.

If the dataset download is unavailable, create `products.json` in this directory:

```json
[
  {
    "id": 1,
    "name": "Your actual product name",
    "category": "Your actual product category",
    "image_path": "images/your-product.jpg"
  }
]
```

Replace the sample fields and image path with real local inputs. Add more records
as needed. Local records are normalized to the same columns as the dataset, so
subsequent prompt and batch cells work with either source.

Run regression checks without an API key or network requests:

```sh
python -m unittest discover -s tests -v
```
