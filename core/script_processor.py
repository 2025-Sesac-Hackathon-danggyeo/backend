"""
발표 대본 처리 유틸리티
- 마침표 기준 문장 분할
- 읽기에 적당한 길이로 청크화
- 예상 읽기 시간 계산
"""

import re
from typing import List, Tuple
from enum import Enum


class ChunkStrategy(Enum):
    """청크화 전략"""
    SENTENCE_COUNT = "sentence_count"  # N개의 문장으로 청크
    CHARACTER_COUNT = "character_count"  # 문자 개수 기준
    DURATION = "duration"  # 읽기 시간 기준


class ScriptProcessor:
    """발표 대본 처리 클래스"""
    
    # 한국어/영어 혼합 텍스트에서 문장 분리 정규식
    SENTENCE_PATTERN = r'(?<=[.!?。!？])\s+'
    
    # 기본 청크화 설정
    DEFAULT_CHUNK_WORDS = 12  # 한 청크당 약 50단어 (한국어 기준 150-200자)
    DEFAULT_CHUNK_CHARS = 70  # 한 청크당 약 200자
    
    # 평균 읽기 속도 (초/단어, 한국어 기준)
    AVG_KOREAN_SPEED = 0.4  # 약 150 단어/분
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """
        마침표, 물음표, 느낌표를 기준으로 문장 분할
        
        Args:
            text: 분할할 원본 텍스트
            
        Returns:
            문장 리스트
        """
        # 공백 정규화
        text = text.strip()
        
        # 마침표, 물음표, 느낌표를 기준으로 분할
        # 공백이 여러 개인 경우도 처리
        sentences = re.split(r'(?<=[.!?。!？])\s*', text)
        
        # 빈 문장 제거
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    @staticmethod
    def estimate_reading_duration(text: str, language: str = "korean") -> float:
        """
        텍스트의 예상 읽기 시간 계산
        
        Args:
            text: 읽을 텍스트
            language: 언어 ("korean", "english")
            
        Returns:
            예상 시간(초)
        """
        if language == "korean":
            # 한국어: 약 150 단어/분 (0.4초/단어)
            # 단어 단위: 공백 기준 + 글자 기준 하이브리드
            words = len(text.split())
            # 한글 문자 개수 / 3 (평균 3글자/단어)
            korean_chars = len([c for c in text if ord(c) >= 0xAC00])
            estimated_words = max(words, korean_chars // 3)
            return estimated_words * ScriptProcessor.AVG_KOREAN_SPEED
        else:
            # 영어: 약 150 단어/분 (0.4초/단어)
            words = len(text.split())
            return words * ScriptProcessor.AVG_KOREAN_SPEED
    
    @staticmethod
    def chunk_sentences(
        sentences: List[str],
        strategy: ChunkStrategy = ChunkStrategy.CHARACTER_COUNT,
        max_chars: int = DEFAULT_CHUNK_CHARS,
        max_sentences: int = 3
    ) -> List[Tuple[str, List[int]]]:
        """
        문장들을 읽기에 적당한 청크로 재배치
        
        Args:
            sentences: 분할된 문장 리스트
            strategy: 청크화 전략
            max_chars: 한 청크의 최대 문자 수
            max_sentences: 한 청크의 최대 문장 개수
            
        Returns:
            [(청크_텍스트, [원본_문장_인덱스]), ...] 리스트
        """
        chunks = []
        current_chunk = []
        current_indices = []
        current_length = 0
        
        for idx, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # 청크 크기 초과 여부 판단
            would_exceed_chars = (current_length + sentence_length) > max_chars
            would_exceed_sentences = len(current_chunk) >= max_sentences
            
            # 현재 청크가 비어있지 않고, 추가하면 한계 초과시
            if current_chunk and (would_exceed_chars or would_exceed_sentences):
                # 기존 청크 저장
                chunk_text = ' '.join(current_chunk)
                chunks.append((chunk_text, current_indices))
                current_chunk = []
                current_indices = []
                current_length = 0
            
            # 새 문장 추가
            current_chunk.append(sentence)
            current_indices.append(idx)
            current_length += sentence_length
        
        # 남은 청크 추가
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, current_indices))
        
        return chunks
    
    @staticmethod
    def process_slide_script(
        script_text: str,
        max_chars: int = DEFAULT_CHUNK_CHARS,
        max_sentences: int = 3
    ) -> List[Tuple[str, float, List[int]]]:
        """
        슬라이드 대본을 처리하여 청크와 메타데이터 반환
        
        Args:
            script_text: 슬라이드 대본 원문
            max_chars: 한 청크의 최대 문자 수
            max_sentences: 한 청크의 최대 문장 개수
            
        Returns:
            [(텍스트, 예상시간, 원본문장인덱스), ...] 리스트
        """
        # 1. 문장 분할
        sentences = ScriptProcessor.split_sentences(script_text)
        
        if not sentences:
            return []
        
        # 2. 청크화
        chunks = ScriptProcessor.chunk_sentences(
            sentences,
            strategy=ChunkStrategy.CHARACTER_COUNT,
            max_chars=max_chars,
            max_sentences=max_sentences
        )
        
        # 3. 각 청크의 읽기 시간 계산
        result = []
        for chunk_text, original_indices in chunks:
            duration = ScriptProcessor.estimate_reading_duration(chunk_text)
            result.append((chunk_text, duration, original_indices))
        
        return result


# ===== 테스트/예시 =====
if __name__ == "__main__":
    sample_text = """안녕하십니까. 지금부터 발표를 시작하겠습니다. 
    오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다. 
    먼저 팀 문화의 중요성을 살펴보겠습니다. 
    좋은 팀 문화는 조직의 생산성을 높입니다. 
    이번에는 구체적인 사례를 보여드리겠습니다."""
    
    processor = ScriptProcessor()
    
    # 문장 분할 테스트
    sentences = processor.split_sentences(sample_text)
    print(f"분할된 문장 수: {len(sentences)}")
    for i, s in enumerate(sentences):
        print(f"  [{i}] {s}")
    
    # 청크화 테스트
    chunks = processor.process_slide_script(sample_text)
    print(f"\n청크 개수: {len(chunks)}")
    for i, (text, duration, indices) in enumerate(chunks):
        print(f"  [{i}] 시간: {duration:.1f}초, 원본문장: {indices}")
        print(f"      텍스트: {text[:50]}...")
