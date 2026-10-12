# Public deployment: 7 steps
1. Create a Public GitHub repository with main branch and upload AUREVIX_GAMES_PUBLIC.zip.
2. Create .github/workflows/unpack.yml in the repository using the supplied YAML. It must be outside the ZIP to run.
3. Settings -> Actions -> General -> Workflow permissions -> Read and write permissions. Run Unpack Aurevix project from Actions; source folders appear at repository root.
4. Create ONE Public Hugging Face Space: Gradio, Blank, CPU Basic. Upload backend contents into the Space root (app.py, requirements.txt, README.md, aurevix/, migrations/, alembic.ini). No local secret .env is included.
5. HF Settings: Secret OPENROUTER_API_KEY; Variable OPENROUTER_MODEL=inclusionai/ling-3.1-flash. Configure a private HF read-write storage volume and DATA_DIR/PERSISTENT_DIR for persistence. Check direct https://...hf.space/health.
6. Vercel -> Import GitHub repository -> Root Directory frontend -> Next.js -> NEXT_PUBLIC_API_URL=https://...hf.space (no /api) -> Deploy.
7. HF Variable FRONTEND_URL=https://...vercel.app (exact origin, no final slash); restart Space and check site.

The original PRIVATE ZIP contains a live key: NEVER upload it to a public repository. This PUBLIC archive contains no real key. GitHub Actions extracts source automatically; Vercel consumes the resulting frontend folder, not the ZIP itself. The Actions workflow is supplied in this archive for reference but must also be added as a top-level .github/workflows/unpack.yml. Local extraction validation was performed; actual GitHub Actions, HF and Vercel deployment were not performed in the owner's accounts.


## Server startup and required files
Upload backend contents into ONE Space root. app.py runs FastAPI/Uvicorn on port 7860, mounts Gradio, and applies Alembic migrations. requirements.txt installs all dependencies. Keep the backend README YAML intact. Upload aurevix/ and migrations/ too; two Python files alone are not sufficient.

## HF persistence
Create a private HF Storage Bucket and attach it read-write to the same Space at /mnt/aurevix. Set DATA_DIR=/tmp/aurevix-runtime and PERSISTENT_DIR=/mnt/aurevix. Live SQLite stays local, snapshots and objects live in the attached volume. Test restart/restore before APP_ENV=production and PERSISTENCE_CONFIRMED=yes. A normal Space disk is ephemeral. No third-party database or S3 is used.

## Local run
Backend: python -m venv .venv; activate environment; pip install -r requirements.txt; python app.py. Frontend: npm ci; npm run dev. Public artifact has no key file: add a local private .env if desired, or use HF Secrets. Test servers require LOAD_LOCAL_ENV=0 and no real OPENROUTER_API_KEY to avoid paid model calls.
