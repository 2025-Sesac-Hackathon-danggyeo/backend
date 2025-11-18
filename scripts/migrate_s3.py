"""
마이그레이션 스크립트: 기존 `db.json`의 루트 `s3_files` 리스트를 새 스키마로 변환합니다.

작업 내용:
- `db.json`을 백업(`db.json.bak.<timestamp>`)
- 기존 각 항목에 `id`, `object_key`, `visibility`, `created_at`, `updated_at`, `deleted` 필드를 추가
- 변경된 `s3_files` 리스트로 `db.json`을 갱신

사용법: 프로젝트 루트에서
    python3 scripts/migrate_s3.py

주의: 실행 전에 저장소/파일을 커밋하거나 백업을 확인하세요. 스크립트는 자동으로 백업을 생성합니다.
"""
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'db.json'


def make_object_key(file_info):
    key = file_info.get('user_id', '')
    script_name = file_info.get('script_name')
    if script_name:
        key += f'/{script_name}'
    key += f'/{file_info.get("file_name", "")}'
    return key


def main():
    if not DB_PATH.exists():
        print(f"DB file not found: {DB_PATH}")
        return
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    backup = DB_PATH.with_suffix(f'.bak.{ts}')
    shutil.copy(DB_PATH, backup)
    print(f"Backup created: {backup}")

    with open(DB_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    old_list = raw.get('s3_files', [])
    if not old_list:
        print("No s3_files found to migrate.")
        return

    new_list = []
    now = datetime.utcnow().isoformat() + 'Z'
    for item in old_list:
        new_item = {
            'id': str(uuid.uuid4()),
            'user_id': item.get('user_id'),
            'script_name': item.get('script_name', ''),
            'file_name': item.get('file_name'),
            'object_key': item.get('object_key') or make_object_key(item),
            'script': item.get('script'),
            'visibility': 'public' if item.get('user_id') == 'base_audio' else 'private',
            'size': item.get('size'),
            'content_hash': item.get('content_hash'),
            'created_at': item.get('created_at', now),
            'updated_at': item.get('updated_at', now),
            'deleted': item.get('deleted', False),
        }
        new_list.append(new_item)

    raw['s3_files'] = new_list

    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"Migration complete. {len(new_list)} records updated in {DB_PATH}")


if __name__ == '__main__':
    main()
