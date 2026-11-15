"""Dataset and response handling shared by the product-listing notebook."""

import base64
import json
from pathlib import Path


def prepare_products(records, images_dir="product_images"):
    """Normalize HuggingFace image rows or local image_path records."""
    products = []
    for source in records:
        product = dict(source)
        if product.get("id") is None:
            raise ValueError("Every product needs an id.")
        name = product.get("productDisplayName") or product.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every product needs a name or productDisplayName.")
        product["productDisplayName"] = name
        for field in ("masterCategory", "subCategory", "articleType",
                      "baseColour", "gender", "season", "usage"):
            product.setdefault(field, product.get("category", "Not specified")
                               if field == "masterCategory" else "Not specified")

        image = product.get("image")
        if image is not None:
            directory = Path(images_dir)
            directory.mkdir(parents=True, exist_ok=True)
            # Do not use externally supplied IDs as filesystem paths.
            path = directory / f"product_{len(products):05d}.jpg"
            image.convert("RGB").save(path)
        else:
            value = product.get("image_path")
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Every product needs an image or image_path.")
            path = Path(value)
            if not path.is_file():
                raise FileNotFoundError("A local product image does not exist.")
        product["image_path"] = str(path)
        products.append(product)
    if not products:
        raise ValueError("The product dataset is empty.")
    return products


def parse_listing(raw_text):
    """Reject empty responses and JSON that is not a usable listing."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("The API returned no listing text.")
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if (len(lines) < 3 or lines[0].strip().lower() not in ("```", "```json")
                or lines[-1].strip() != "```"):
            raise ValueError("The JSON code block is incomplete.")
        cleaned = "\n".join(lines[1:-1])
    listing = json.loads(cleaned)
    if not isinstance(listing, dict):
        raise ValueError("The listing must be a JSON object.")
    for field in ("title", "description", "keywords"):
        if not isinstance(listing.get(field), str) or not listing[field].strip():
            raise ValueError(f"The listing needs a non-empty {field}.")
    features = listing.get("features")
    if (not isinstance(features, list) or not features
            or any(not isinstance(x, str) or not x.strip() for x in features)):
        raise ValueError("The listing needs a list of non-empty features.")
    return listing


def generate_listing(client, prompt, image_path, model="gpt-4o"):
    """Return a listing, a JSON-error marker, or None for a failed request."""
    try:
        path = Path(image_path)
        mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png",
                ".webp": "webp", ".gif": "gif"}.get(path.suffix.lower())
        if mime is None:
            raise ValueError("Unsupported image format.")
        data = path.read_bytes()
        if not data:
            raise ValueError("The image file is empty.")
        encoded = base64.b64encode(data).decode("ascii")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/{mime};base64,{encoded}"}}
            ]}],
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
    except Exception as error:
        # Exception messages can contain provider or request details.
        print(f"Listing request failed ({type(error).__name__}).")
        return None

    choices = getattr(response, "choices", None)
    if not choices:
        print("The API returned no completion choices.")
        return None
    choice = choices[0]
    message = getattr(choice, "message", None)
    if getattr(message, "refusal", None):
        print("The API declined this request.")
        return None
    raw_text = getattr(message, "content", None)
    if getattr(choice, "finish_reason", None) == "length":
        print("The API response was truncated.")
        return {"raw_response": raw_text or ""}
    try:
        return parse_listing(raw_text)
    except (ValueError, TypeError):
        print("The API response was not a valid product listing.")
        return {"raw_response": raw_text or ""}
