import os
import runpy
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from zipfile import ZipFile

import httpx

MAX_BYTES = 40 * 1024 * 1024


def main():
    url = os.environ.get("PROJECT_ZIP_URL", "")
    local_test = os.environ.get("PROJECT_ZIP_FILE", "")
    if not local_test and (
        urlparse(url).scheme != "https"
        or urlparse(url).hostname != "raw.githubusercontent.com"
    ):
        raise RuntimeError("Set PROJECT_ZIP_URL to your public GitHub raw ZIP URL")

    with tempfile.TemporaryDirectory(prefix="aurevix-") as work:
        work = Path(work)
        archive_path = work / "project.zip"
        if local_test:
            archive_path.write_bytes(Path(local_test).read_bytes())
        else:
            with httpx.stream("GET", url, timeout=60, follow_redirects=False) as response:
                response.raise_for_status()
                with archive_path.open("wb") as output:
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise RuntimeError("Project ZIP is too large")
                        output.write(chunk)

        backend = work / "backend"
        backend.mkdir()
        expanded = 0
        with ZipFile(archive_path) as archive:
            if len(archive.infolist()) > 1000:
                raise RuntimeError("Too many project files")
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                path = PurePosixPath(entry.filename)
                if path.parts[:2] != ("aurevix-games", "backend"):
                    continue
                parts = path.parts[2:]
                if not parts or ".." in parts or "\\" in entry.filename:
                    raise RuntimeError("Unsafe ZIP path")
                destination = backend.joinpath(*parts).resolve()
                if not destination.is_relative_to(backend.resolve()):
                    raise RuntimeError("Unsafe ZIP destination")
                expanded += entry.file_size
                if expanded > MAX_BYTES:
                    raise RuntimeError("Backend is too large")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(entry))

        # The real key is written only to an untracked runtime file in the Space.
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if key:
            env = backend / ".env"
            model = os.environ.get("OPENROUTER_MODEL", "inclusionai/ling-3.1-flash")
            env.write_text(f"OPENROUTER_API_KEY={key}\nOPENROUTER_MODEL={model}\n")
            env.chmod(0o600)

        os.chdir(backend)
        sys.path.insert(0, str(backend))
        runpy.run_path(str(backend / "app.py"), run_name="__main__")


if __name__ == "__main__":
    main()
