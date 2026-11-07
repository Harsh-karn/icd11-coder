import os

bundle_path = "harsh.bundle"
output_dir = "bundle_parts"
chunk_size = 20 * 1024 * 1024  # 20 MB

os.makedirs(output_dir, exist_ok=True)

with open(bundle_path, "rb") as f:
    part_num = 0
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        part_name = f"harsh.bundle.part-{part_num:02d}"
        part_path = os.path.join(output_dir, part_name)
        with open(part_path, "wb") as out_f:
            out_f.write(chunk)
        print(f"Created {part_name} ({len(chunk)} bytes)")
        part_num += 1

print(f"Split complete: {part_num} parts created in {output_dir}/")

