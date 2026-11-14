from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class UserSession:
    user_id: int
    current_mode: str = "menu"  # "menu", "test_single", "test_batch", "ai_tutor"
    current_subject: Optional[str] = None
    current_topic: Optional[str] = None
    current_question: Optional[Dict[str, Any]] = None
    
    # Для пакетного теста (например, из 5 вопросов)
    batch_questions: List[Dict[str, Any]] = field(default_factory=list)
    batch_index: int = 0
    batch_correct: int = 0
    
    # Сохраненный пользователем файл
    saved_file_name: Optional[str] = None
    saved_file_text: Optional[str] = None
    saved_file_path: Optional[str] = None
    
    # Общая статистика пользователя
    total_answered: int = 0
    total_correct: int = 0
    stats_by_subject: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        "Русский язык": {"total": 0, "correct": 0},
        "Литература": {"total": 0, "correct": 0}
    })

class MemoryStorage:
    def __init__(self):
        self._sessions: Dict[int, UserSession] = {}

    def get_session(self, user_id: int) -> UserSession:
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession(user_id=user_id)
        return self._sessions[user_id]

    def record_answer(self, user_id: int, subject: str, is_correct: bool):
        session = self.get_session(user_id)
        session.total_answered += 1
        if is_correct:
            session.total_correct += 1
            
        subj_name = "Русский язык" if "рус" in subject.lower() else "Литература"
        if subj_name not in session.stats_by_subject:
            session.stats_by_subject[subj_name] = {"total": 0, "correct": 0}
            
        session.stats_by_subject[subj_name]["total"] += 1
        if is_correct:
            session.stats_by_subject[subj_name]["correct"] += 1

db = MemoryStorage()
