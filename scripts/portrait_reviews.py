"""Persistent AI assessments and append-only human reviews of exact output files.

Runtime SQLite/media are private and never belong in source control. Human feedback
is evaluation evidence, not automatic model training. HTTP callers supply only a
known row ID and the displayed output hash; they cannot choose filesystem paths.
"""
import hashlib
import json
import os
import sqlite3
import time
import uuid
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(os.environ.get('FPG_REVIEW_ROOT', '/workspace/fpg-validation'))


@contextmanager
def connect():
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'reviews.sqlite3', timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS human_reviews (
          id TEXT PRIMARY KEY, row_id TEXT NOT NULL, output_sha256 TEXT NOT NULL,
          score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10), notes TEXT NOT NULL,
          created_at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS human_output ON human_reviews(row_id, output_sha256, created_at);
        CREATE TABLE IF NOT EXISTS ai_reviews (
          row_id TEXT NOT NULL, output_sha256 TEXT NOT NULL, rubric TEXT NOT NULL,
          assessment TEXT NOT NULL, created_at REAL NOT NULL,
          PRIMARY KEY(row_id, output_sha256, rubric));
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


@lru_cache(maxsize=4096)
def _digest(path, mtime, size):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(path):
    stat = path.stat()
    return _digest(str(path), stat.st_mtime_ns, stat.st_size)


def output_hash(row):
    name = row.get('output')
    if not name or Path(name).name != name:
        return None
    try:
        return digest(ROOT / 'media' / name)
    except FileNotFoundError:
        return None


def attach(rows):
    with connect() as db:
        human = {}
        for item in db.execute('SELECT * FROM human_reviews ORDER BY created_at'):
            item = dict(item)
            human.setdefault((item['row_id'], item['output_sha256']), []).append(item)
        ai={};history={}
        for r in db.execute('SELECT * FROM ai_reviews ORDER BY created_at'):
            key=(r['row_id'],r['output_sha256']);assessment=json.loads(r['assessment'])
            ai[key]=assessment;history.setdefault(key,[]).append(assessment)
    for row in rows:
        sha = output_hash(row)
        if not sha:
            continue
        key = (row['id'], sha)
        row['output_sha256'] = sha
        row['human_reviews'] = [{k: h[k] for k in ('id', 'score', 'notes', 'created_at')}
                                for h in human.get(key, [])]
        row['human_review'] = row['human_reviews'][-1] if row['human_reviews'] else None
        row['ai_review'] = ai.get(key)
        row['ai_previous'] = [{k:a.get(k) for k in ('rubric','score','created_at')}
                              for a in history.get(key,[])[:-1]]
        try:row['ai_status']=json.loads((ROOT/'judge-status'/(row['id']+'.json')).read_text())['status']
        except (OSError,ValueError,KeyError):pass
    return rows


def save_human(payload, rows):
    if not isinstance(payload, dict):
        raise ValueError('A JSON object is required')
    row = next((r for r in rows if r['id'] == payload.get('row_id')), None)
    if not row or row.get('status') != 'Complete' or not output_hash(row):
        raise ValueError('Choose a finished output to review')
    sha = output_hash(row)
    if payload.get('output_sha256') != sha:
        raise ValueError('This output changed. Reload before submitting your review')
    score, notes = payload.get('score'), payload.get('notes', '')
    if type(score) is not int or not 1 <= score <= 10:
        raise ValueError('Choose a whole-number score from 1 to 10')
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError('Notes must be text, up to 2,000 characters')
    review_id = payload.get('submission_id')
    try:
        if str(uuid.UUID(review_id)) != review_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError('A valid submission ID is required') from None
    now = time.time()
    with connect() as db:
        old = db.execute('SELECT * FROM human_reviews WHERE id=?', (review_id,)).fetchone()
        if old:
            if (old['row_id'], old['output_sha256'], old['score'], old['notes']) != (row['id'], sha, score, notes.strip()):
                raise ValueError('Submission ID already used for a different review')
            return dict(old)
        db.execute('INSERT INTO human_reviews VALUES (?,?,?,?,?,?)',
                   (review_id, row['id'], sha, score, notes.strip(), now))
    return dict(id=review_id, score=score, notes=notes.strip(), created_at=now)


def save_ai(row, assessment):
    sha = output_hash(row)
    if not sha or assessment['output_sha256'] != sha:
        raise ValueError('Assessment does not match this output')
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO ai_reviews VALUES (?,?,?,?,?)',
                   (row['id'], sha, assessment['rubric'], json.dumps(assessment), time.time()))


def handle_post(handler, rows):
    """Same-origin JSON only; the bearer page URL determines the allowed rows."""
    try:
        if handler.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise ValueError('Submit from this review page')
        # Non-simple JSON requests require browser preflight; no CORS/OPTIONS is enabled.
        if handler.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise ValueError('JSON content type required')
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= 12000:
            raise ValueError('Invalid review size')
        result = save_human(json.loads(handler.rfile.read(size)), rows)
        status, body = 200, {'review': result}
    except (ValueError, UnicodeError) as error:
        status, body = 400, {'error': str(error)}
    data = json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)
