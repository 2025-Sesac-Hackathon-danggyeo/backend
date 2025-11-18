#!/usr/bin/env python3
"""
발표 대본 API 테스트 스크립트
로컬 개발 환경에서 API 동작 확인용
"""

import requests
import json
from typing import Dict, Any

# 테스트 설정
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_123"

# 테스트용 토큰 (실제 환경에서는 로그인해서 얻어야 함)
# 주의: 실제 테스트 시 유효한 토큰 필요
TEST_TOKEN = None  # 나중에 설정


def print_response(title: str, response: Dict[str, Any]):
    """응답을 보기 좋게 출력"""
    print(f"\n{'='*60}")
    print(f"[{title}]")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, ensure_ascii=False))


def test_create_script():
    """발표 대본 생성 테스트"""
    url = f"{BASE_URL}/api/v1/scripts"
    
    payload = {
        "script_name": "리더십 워크숍",
        "description": "팀 관리 효율화 전략",
        "total_slides": 3
    }
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("발표 대본 생성 성공", data)
        return data['script_id']
    else:
        print_response("발표 대본 생성 실패", response.json())
        return None


def test_upload_slide(script_id: str, slide_number: int, script_text: str):
    """슬라이드 업로드 테스트"""
    url = f"{BASE_URL}/api/v1/scripts/{script_id}/slide/{slide_number}"
    
    payload = {
        "script_text": script_text
    }
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.patch(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response(f"슬라이드 {slide_number} 업로드 성공", data)
        return data
    else:
        print_response(f"슬라이드 {slide_number} 업로드 실패", response.json())
        return None


def test_get_script_info(script_id: str):
    """스크립트 정보 조회 테스트"""
    url = f"{BASE_URL}/api/v1/scripts/{script_id}"
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("스크립트 정보 조회 성공", data)
        return data
    else:
        print_response("스크립트 정보 조회 실패", response.json())
        return None


def test_get_sentences(script_id: str):
    """문장 데이터 조회 테스트 (클론 준비)"""
    url = f"{BASE_URL}/api/v1/scripts/{script_id}/sentences"
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("문장 데이터 조회 성공", data)
        return data
    else:
        print_response("문장 데이터 조회 실패", response.json())
        return None


def test_submit_practice_score(sentence_id: str):
    """연습 점수 제출 테스트"""
    url = f"{BASE_URL}/api/v1/practice/scores/{sentence_id}"
    
    payload = {
        "accuracy": 85.5,
        "fluency": 90.0,
        "time_taken": 3.2
    }
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("연습 점수 제출 성공", data)
        return data
    else:
        print_response("연습 점수 제출 실패", response.json())
        return None


def test_get_practice_score(sentence_id: str):
    """연습 점수 조회 테스트"""
    url = f"{BASE_URL}/api/v1/practice/scores/{sentence_id}"
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("연습 점수 조회 성공", data)
        return data
    else:
        print_response("연습 점수 조회 실패", response.json())
        return None


def test_get_statistics(script_id: str):
    """연습 통계 조회 테스트"""
    url = f"{BASE_URL}/api/v1/practice/scripts/{script_id}/stats"
    
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_response("연습 통계 조회 성공", data)
        return data
    else:
        print_response("연습 통계 조회 실패", response.json())
        return None


def run_tests():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("발표 대본 API 테스트 시작")
    print("="*60)
    
    # 1. 발표 대본 생성
    script_id = test_create_script()
    if not script_id:
        print("테스트 중단: 발표 대본 생성 실패")
        return
    
    # 2. 슬라이드 1 업로드
    slide_text_1 = """안녕하십니까. 지금부터 리더십 워크숍을 시작하겠습니다. 
    오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다. 
    먼저 팀 문화의 중요성을 살펴보겠습니다."""
    
    slide_data_1 = test_upload_slide(script_id, 1, slide_text_1)
    
    if slide_data_1:
        sentence_id_1 = slide_data_1['sentences'][0]['sentence_id']
    else:
        print("테스트 중단: 슬라이드 1 업로드 실패")
        return
    
    # 3. 슬라이드 2 업로드
    slide_text_2 = """좋은 팀 문화는 조직의 생산성을 높입니다. 
    구체적인 사례를 보여드리겠습니다. 
    이것은 실제 프로젝트에서 적용한 사례입니다."""
    
    slide_data_2 = test_upload_slide(script_id, 2, slide_text_2)
    
    if slide_data_2:
        sentence_id_2 = slide_data_2['sentences'][0]['sentence_id']
    else:
        print("테스트 중단: 슬라이드 2 업로드 실패")
        return
    
    # 4. 스크립트 정보 조회
    test_get_script_info(script_id)
    
    # 5. 전체 문장 조회
    test_get_sentences(script_id)
    
    # 6. 연습 점수 제출
    test_submit_practice_score(sentence_id_1)
    
    # 7. 같은 문장에 다시 제출 (업데이트 테스트)
    print("\n[같은 문장에 더 높은 점수로 재제출]")
    test_submit_practice_score(sentence_id_1)
    
    # 8. 연습 점수 조회
    test_get_practice_score(sentence_id_1)
    
    # 9. 두 번째 문장에 점수 제출
    test_submit_practice_score(sentence_id_2)
    
    # 10. 통계 조회
    test_get_statistics(script_id)
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)


if __name__ == "__main__":
    print("""
    주의: 이 테스트를 실행하려면:
    
    1. 서버 시작: python3 -m uvicorn main:app --reload
    2. 유효한 인증 토큰 필요 (TEST_TOKEN 설정)
    
    임시로 로컬 테스트만 하려면, 스크립트 프로세서를 직접 테스트하세요:
    python3 -c "from core.script_processor import ScriptProcessor; 
                p = ScriptProcessor(); 
                text = '안녕하세요. 지금부터 시작합니다. 감사합니다.'; 
                result = p.process_slide_script(text); 
                print(result)"
    """)
    
    # TEST_TOKEN이 없으면 로컬 유틸리티 테스트만 수행
    if not TEST_TOKEN:
        print("\n로컬 유틸리티 테스트 수행 중...")
        from core.script_processor import ScriptProcessor
        
        processor = ScriptProcessor()
        
        # 문장 분할 테스트
        sample_text = """안녕하십니까. 지금부터 발표를 시작하겠습니다. 
        오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다. 
        먼저 팀 문화의 중요성을 살펴보겠습니다. 
        좋은 팀 문화는 조직의 생산성을 높입니다. 
        이번에는 구체적인 사례를 보여드리겠습니다."""
        
        print("\n" + "="*60)
        print("[로컬 테스트: 문장 분할 및 청크화]")
        print("="*60)
        
        result = processor.process_slide_script(sample_text)
        print(f"\n총 청크 개수: {len(result)}")
        
        for i, (text, duration, indices) in enumerate(result, 1):
            print(f"\n청크 [{i}]")
            print(f"  텍스트: {text}")
            print(f"  읽기시간: {duration:.1f}초")
            print(f"  원본문장인덱스: {indices}")
    else:
        run_tests()
