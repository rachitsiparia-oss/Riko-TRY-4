import json
import mimetypes
import os

import db


BASE_DIR = os.path.dirname(__file__)
SEED_PATH = os.path.join(BASE_DIR, "menu_items_seed_updated.json")


def load_dotenv():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


def main():
    load_dotenv()
    if not db.use_supabase():
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")

    if not os.path.exists(SEED_PATH):
        raise SystemExit(f"Seed file not found: {SEED_PATH}")

    with open(SEED_PATH, "r", encoding="utf-8") as seed_file:
        items = json.load(seed_file)

    uploaded = 0
    skipped = 0

    for item in items:
        slug = item.get("slug")
        image_url = item.get("image_url", "")
        if not slug or not image_url.startswith("assets/"):
            skipped += 1
            continue

        local_path = os.path.join(BASE_DIR, image_url.replace("/", os.sep))
        if not os.path.exists(local_path):
            print(f"Missing local file for {slug}: {image_url}")
            skipped += 1
            continue

        ext = os.path.splitext(local_path)[1].lower() or ".png"
        content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
        storage_path = f"dishes/{slug}{ext}"

        with open(local_path, "rb") as image_file:
            result = db.upload_menu_image(image_file.read(), storage_path, content_type)

        existing = db.get_by_slug("menu_items", slug)
        if not existing:
            print(f"No menu row found for slug {slug}; uploaded image but did not update database row.")
            skipped += 1
            continue

        ok, err = db.update_item("menu_items", existing["id"], {
            "image_url": result["image_url"],
            "image_path": result["image_path"],
        })
        if not ok:
            print(f"Database update failed for {slug}: {err}")
            skipped += 1
            continue

        uploaded += 1
        print(f"Uploaded {slug} -> {result['image_path']}")

    print(f"Done. Uploaded and linked {uploaded} images. Skipped {skipped}.")


if __name__ == "__main__":
    main()
