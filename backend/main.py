from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os, pathlib, re, time, yaml, httpx, json
import urllib.parse

# ---------- Repo location helpers ----------
def _find_repo_root(start: pathlib.Path) -> pathlib.Path:
    for p in [start, *start.parents]:
        if (p / "apps").exists():
            return p
    return start

REPO_ROOT = _find_repo_root(pathlib.Path(__file__).resolve())
CASES_DIR = REPO_ROOT / "testcase-generator/apps"
ID_NUM_RE = re.compile(r".*-TC-(\d+)\.md$", re.IGNORECASE)

# ---------- Env / providers ----------
GITLAB_BASE = os.getenv("GITLAB_BASE_URL","").rstrip("/")
GITLAB_PROJ = os.getenv("GITLAB_PROJECT_ID","")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN","")
HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN} if GITLAB_TOKEN else {}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "stub").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

FM_RE = re.compile(r'^\s*---\s*\r?\n(.*?)\r?\n---\s*', re.DOTALL | re.MULTILINE)
FENCED_YAML_TOP_RE = re.compile(r'^\s*```(?:yaml)?\s*\r?\n(.*?)\r?\n```\s*', re.DOTALL | re.MULTILINE)

# Caps / safety
MAX_OUTPUT_TOKENS = 1200
MAX_NOTES_CHARS = 4000

# ---------- LLM (OpenAI) ----------
def _fmt_system_prompt() -> str:
    return (
        "You are a senior QA engineer. Generate ONE Markdown test case using this layout.\n"
        "The document MUST begin with YAML front-matter delimited by three dashes:\n"
        "---\n<yaml keys/values>\n---\n"
        "Front-matter keys: id, app, area, suite, type, priority, status, story_refs, bug_refs, owner, automation, links.\n"
        "Rules:\n"
        "- type: Functional by default\n"
        "- status: Draft unless implied otherwise\n"
        "- story_refs, bug_refs, links are YAML lists (can be [])\n"
        "- owner is a quoted string\n"
        "- automation.status: Planned | Automated | NotApplicable\n"
        "After the front-matter, include these sections in order:\n"
        "# <Title>\n## Preconditions\n## Steps & Expected\n## Negative / Edge\n## Notes\n"
        "Return ONLY Markdown."
    )

def _fmt_user_prompt(app: str, area: str, suite: str, priority: str, notes: str) -> str:
    return f"""
App: {app}
Area: {area}
Suite: {suite}
Priority: {priority}

Notes from QA (trimmed):
{(notes or '')[:MAX_NOTES_CHARS]}
"""

def generate_with_openai(app: str, area: str, suite: str, priority: str, notes: str) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail={"error":{"message":"OPENAI_API_KEY not set"}})
    try:
        # Lazy import to avoid dependency if not used
        from openai import OpenAI
        import openai
    except Exception:
        raise HTTPException(status_code=500, detail={"error":{"message":"openai SDK not installed"}})

    client = OpenAI(api_key=OPENAI_API_KEY)

    for attempt in range(3):
        try:
            msg = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=0.2,
                max_tokens=MAX_OUTPUT_TOKENS,
                messages=[
                    {"role":"system","content":_fmt_system_prompt()},
                    {"role":"user","content":_fmt_user_prompt(app, area, suite, priority, notes)},
                ],
            )
            return msg.choices[0].message.content.strip()
        except openai.RateLimitError as e:
            if attempt == 2:
                raise HTTPException(status_code=(getattr(e, "status_code", None) or 429),
                                    detail={"error":{"message":"Rate limited by model","code":"rate_limited"}})
            time.sleep(1.5 * (attempt + 1))
        except openai.APIError as e:
            # Bubble real status if possible
            status = getattr(e, "status_code", None) or 500
            msg = getattr(e, "message", "") or "OpenAI API error"
            raise HTTPException(status_code=status, detail={"error":{"message":msg}})
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error":{"message":f"OpenAI client error: {e}"}})

def stub_markdown(app: str, area: str, suite: str, priority: str, notes: str) -> str:
    return f"""---
id: {app}-TC-XXX
app: {app}
area: {area}
suite: {suite}
type: Functional
priority: {priority}
status: Draft
story_refs: []
bug_refs: []
owner: "@your-username"
automation:
  status: Planned
  mapping: ""
links: []
---

# {area}: baseline scenario from notes

## Preconditions
- From notes: {(notes or '')[:200]}...

## Steps & Expected
1. Describe the user action
   **Expected:** Describe the expected result

## Negative / Edge
- Describe unusual input and expected handling

## Notes
- Add any cleanup / data hints
"""

# ---------- Lint / normalize ----------
REQUIRED_KEYS = ["id","app","area","suite","type","priority","status","owner","automation"]

def ensure_front_matter(md: str) -> str:
    """
    If the document starts with ```yaml ...```, convert it to proper front-matter.
    If it already has front-matter, return as-is.
    Otherwise return unchanged (lint may complain).
    """
    if FM_RE.search(md):
        return md

    m = FENCED_YAML_TOP_RE.search(md)
    if not m:
        return md

    yaml_block = m.group(1).strip()
    # Remove the fenced block and leave the rest of the doc
    rest = md[m.end():].lstrip()
    normalized = f"---\n{yaml_block}\n---\n\n{rest}"
    return normalized

def lint_markdown(md: str) -> dict:
    m = re.search(r'^\s*---\s*\r?\n(.*?)\r?\n---\s*', md, re.DOTALL|re.MULTILINE)
    if not m:
        return {"ok": False, "errors": ["Missing YAML front-matter"]}
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        return {"ok": False, "errors": [f"YAML parse error: {e}"]}

    errors = []
    if isinstance(meta.get("owner"), str) and meta["owner"].startswith("@"):
        meta["owner"] = f"\"{meta['owner']}\""

    for k in ["story_refs","bug_refs","links"]:
        v = meta.get(k)
        if v is None: meta[k] = []
        elif not isinstance(v, list): errors.append(f"{k} must be a list")

    for k in REQUIRED_KEYS:
        if k not in meta: errors.append(f"Missing key: {k}")

    normalized = "---\n" + yaml.safe_dump(meta, sort_keys=False).strip() + "\n---"
    md_fixed = normalized + re.sub(r'^\s*---.*?---\s*', "", md, flags=re.DOTALL|re.MULTILINE)
    return {"ok": len(errors)==0, "errors": errors, "markdown": md_fixed}

# ---------- GitLab helpers ----------
FM_RE = re.compile(r'^\s*---\s*\r?\n(.*?)\r?\n---\s*', re.DOTALL | re.MULTILINE)

def parse_id_from_markdown(md: str) -> Optional[str]:
    """Read YAML front-matter and return 'id' if present."""
    m = FM_RE.search(md or "")
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        return None
    v = meta.get("id")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None

def set_id_in_markdown(md: str, new_id: str) -> str:
    """Rewrite YAML front-matter 'id' to new_id and return updated markdown."""
    m = FM_RE.search(md or "")
    if not m:
        return md  # nothing to rewrite
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    meta["id"] = new_id
    rebuilt = "---\n" + yaml.safe_dump(meta, sort_keys=False).strip() + "\n---"
    return rebuilt + re.sub(r'^\s*---.*?---\s*', "", md, flags=re.DOTALL|re.MULTILINE)

def file_exists_in_gitlab(file_path: str, ref: str = "main") -> bool:
    """True if a blob exists at file_path on ref."""
    url_path = urllib.parse.quote(file_path, safe="")
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/repository/files/{url_path}"
    params = {"ref": ref}
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, params=params, headers=HEADERS)
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        r.raise_for_status()
        return False

def next_free_id(app: str, area: str) -> str:
    """Return the next available <App>-TC-XXX that doesn't exist in the repo."""
    # Start from current max + 1
    candidate = next_id_from_gitlab(app, area)
    # Double-check existence of the file path (rare race).
    area_dir = area_to_repo_dir(area)
    while True:
        rel = f"testcase-generator/apps/{app.lower()}/areas/{area_dir}/{candidate}.md"
        if not file_exists_in_gitlab(rel, ref="main"):
            return candidate
        # bump
        m = re.match(rf"{re.escape(app)}-TC-(\d+)$", candidate, re.IGNORECASE)
        n = int(m.group(1)) if m else 1
        candidate = f"{app}-TC-{n+1:03d}"

def area_to_repo_dir(area: str) -> str:
    parts = [p.strip().lower().replace(" ", "-") for p in area.split(">")]
    return "/".join(parts)

def list_case_files_in_gitlab(app: str, area: str) -> list[str]:
    if not (GITLAB_BASE and GITLAB_PROJ and GITLAB_TOKEN):
        return []
    path = f"testcase-generator/apps/{app.lower()}/areas/{area_to_repo_dir(area)}"
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/repository/tree"
    params = {"path": path, "per_page": 100}
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, params=params, headers=HEADERS)
        if r.status_code == 404:
            return []
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return [item["name"] for item in r.json() if item.get("type")=="blob" and item["name"].endswith(".md")]

def next_id_from_gitlab(app: str, area: str) -> str:
    files = list_case_files_in_gitlab(app, area)
    max_n = 0
    for name in files:
        m = re.match(rf"{re.escape(app)}-TC-(\d+)\.md$", name, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            if n > max_n: max_n = n
    return f"{app}-TC-{max_n+1:03d}"

def create_branch(branch: str, ref: str="main"):
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/repository/branches"
    with httpx.Client(timeout=20.0) as c:
        r = c.post(url, headers=HEADERS, data={"branch": branch, "ref": ref})
        if r.status_code in (200,201,400):
            return
        raise HTTPException(status_code=r.status_code, detail=r.text)

def commit_file(branch: str, file_path: str, content: str, commit_msg: str):
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/repository/commits"
    def do(action: str):
        payload = {
            "branch": branch,
            "commit_message": commit_msg,
            "actions": [{
                "action": action,              # "create" or "update"
                "file_path": file_path,
                "content": content,
                "encoding": "text"
            }]
        }
        with httpx.Client(timeout=30.0) as c:
            rr = c.post(url, headers=HEADERS, json=payload)
            return rr
    # Try create; if already exists, update
    r = do("create")
    if r.status_code == 400:
        try:
            body = r.json()
        except Exception:
            body = {"message": r.text}
        msg = (body.get("message") or "").lower()
        if "already exists" in msg or "A file with this name already exists".lower() in msg:
            r2 = do("update")
            if r2.status_code not in (200, 201):
                raise HTTPException(status_code=r2.status_code, detail=r2.text)
            return
        # Other 400 → bubble with message
        raise HTTPException(status_code=400, detail=body)
    if r.status_code not in (200,201):
        raise HTTPException(status_code=r.status_code, detail=r.text)

def open_mr(branch: str, title: str, description: str=""):
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/merge_requests"
    data = {"source_branch": branch, "target_branch": "main", "title": title, "description": description}
    with httpx.Client(timeout=20.0) as c:
        r = c.post(url, headers=HEADERS, data=data)
        if r.status_code not in (200,201):
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()["web_url"]
        
def find_open_mr_for_branch(source_branch: str) -> Optional[str]:
    """Return web_url of an open MR for this source branch, or None."""
    if not (GITLAB_BASE and GITLAB_PROJ and GITLAB_TOKEN):
        return None
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/merge_requests"
    params = {"state": "opened", "source_branch": source_branch, "target_branch": "main"}
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, params=params, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        if data:
            return data[0].get("web_url")
        return None

def branch_exists(branch: str) -> bool:
    url = f"{GITLAB_BASE}/api/v4/projects/{GITLAB_PROJ}/repository/branches/{branch}"
    with httpx.Client(timeout=20.0) as c:
        r = c.get(url, headers=HEADERS)
        if r.status_code == 200: return True
        if r.status_code == 404: return False
        r.raise_for_status()
        return False

def unique_branch(base: str) -> str:
    """Return base, or base-v2/-v3… if branch or MR already exists."""
    # If there is already an open MR for base, bump suffix immediately
    if find_open_mr_for_branch(base) or branch_exists(base):
        i = 2
        while True:
            cand = f"{base}-v{i}"
            if not (branch_exists(cand) or find_open_mr_for_branch(cand)):
                return cand
            i += 1
    return base

# ---------- FastAPI app ----------
app = FastAPI(title="QA Testcase Assistant")
api = APIRouter(prefix="/api")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:****", "http://127.0.0.1:****"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class GenerateReq(BaseModel):
    app: str
    area: str
    suite: str
    priority: str
    notes: str
    ocr: bool = False
    image_base64: Optional[str] = None

class GenerateResp(BaseModel):
    markdown: str

class LintReq(BaseModel):
    markdown: str

class CreateMrReq(BaseModel):
    app: str
    area: str
    markdown: str
    preferred_id: Optional[str] = None
    story_refs: Optional[List[str]] = None

class CreateMrResp(BaseModel):
    branch: str
    mr_url: str

# ---------- Routes ----------
@api.get("/health")
def health():
    return {"ok": True, "provider": LLM_PROVIDER, "model": OPENAI_MODEL}

@api.get("/suggest-id")
def suggest_id(app: str = Query(...), area: str = Query(...)):
    return {"next_id": next_id_from_gitlab(app, area)}

@api.post("/lint")
def lint(req: LintReq):
    res = lint_markdown(req.markdown)
    if not res["ok"] and not res.get("markdown"):
        raise HTTPException(status_code=400, detail=res["errors"])
    return res

@api.post("/generate", response_model=GenerateResp)
def generate(req: GenerateReq, request: Request):
    try:
        # optional override via query: ?mode=ai | ?mode=stub
        mode = request.query_params.get("mode", "").lower().strip()
        use_ai = (mode == "ai") or (mode == "" and LLM_PROVIDER == "openai")
        if mode == "stub":
            use_ai = False

        if use_ai:
            md = generate_with_openai(req.app, req.area, req.suite, req.priority, req.notes)
        else:
            md = stub_markdown(req.app, req.area, req.suite, req.priority, req.notes)

        return {"markdown": md}

    except HTTPException as e:
        # preserve status code & detail for the frontend
        raise e
    except Exception as e:
        # ensure the UI gets a structured 500
        raise HTTPException(status_code=500, detail={"error": {"message": str(e)}})

@api.post("/create-mr", response_model=CreateMrResp)
def create_mr(req: CreateMrReq):
    if not (GITLAB_BASE and GITLAB_PROJ and GITLAB_TOKEN):
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "GitLab env vars not set (GITLAB_BASE_URL, GITLAB_PROJECT_ID, GITLAB_TOKEN)."}}
        )

    try:
        # 1) Choose the intended ID (Markdown > preferred_id > next free)
        md_id = parse_id_from_markdown(req.markdown or "")
        intended_id = (md_id or (req.preferred_id or "").strip()) or next_free_id(req.app, req.area)

        area_dir = area_to_repo_dir(req.area)
        file_rel = f"testcase-generator/apps/{req.app.lower()}/areas/{area_dir}/{intended_id}.md"

        # 2) If that file already exists, auto-bump and rewrite the Markdown's id
        if file_exists_in_gitlab(file_rel, ref="main"):
            bumped = next_free_id(req.app, req.area)
            req.markdown = set_id_in_markdown(req.markdown, bumped)
            intended_id = bumped
            file_rel = f"testcase-generator/apps/{req.app.lower()}/areas/{area_dir}/{intended_id}.md"

        # 3) Branch naming uses the final ID
        safe_area = area_dir.replace("/", "-")
        base_branch = f"feat/{req.app.lower()}-{safe_area}-{intended_id}".lower()
        branch = unique_branch(base_branch)

        # If open MR already exists for this branch, reuse it
        existing_mr = find_open_mr_for_branch(branch)

        # Ensure branch exists
        create_branch(branch, ref="main")

        # Commit (create action; GitLab will store new file)
        commit_msg = f"add/update test case {intended_id} for {req.app} / {req.area}"
        commit_file(branch, file_rel, req.markdown, commit_msg)

        if existing_mr:
            return {"branch": branch, "mr_url": existing_mr}

        # Open MR
        mr_title = f"[TC] {intended_id} - {req.app} / {req.area}"
        try:
            mr_url = open_mr(branch, mr_title, description="New test case generated by QA Assist")
            return {"branch": branch, "mr_url": mr_url}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                reuse = find_open_mr_for_branch(branch)
                if reuse:
                    return {"branch": branch, "mr_url": reuse}
            raise

    except httpx.HTTPStatusError as e:
        # preserve GitLab’s exact status/body
        body = e.response.text if hasattr(e, "response") and e.response is not None else str(e)
        raise HTTPException(status_code=e.response.status_code if hasattr(e, "response") and e.response is not None else 500,
                            detail=body)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": {"message": str(e)}})

app.include_router(api)
app.mount("/", StaticFiles(directory="/app/web", html=True), name="web")