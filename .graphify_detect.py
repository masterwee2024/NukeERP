import json
from pathlib import Path

from graphify.detect import detect

result = detect(Path("."))
with open(".graphify_detect.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
print(
    json.dumps(
        {
            "total_files": result["total_files"],
            "total_words": result["total_words"],
            "files": {k: len(v) for k, v in result.get("files", {}).items() if v},
            "skipped_sensitive": result.get("skipped_sensitive", []),
        }
    )
)
