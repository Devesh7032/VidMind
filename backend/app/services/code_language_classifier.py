import re
import uuid
from typing import Tuple, List, Dict, Any
from app.schemas import CodeRegion, ObservationType


class CodeLanguageClassifier:
    """
    VidMind Multi-Signal Code Language Classifier.
    Analyzes code snippets and visual text using syntax patterns, keywords, standard library idioms,
    and region boundary detection.
    """

    def __init__(self):
        # Language Keyword & Syntax Patterns
        self.language_patterns: Dict[str, List[Tuple[str, float]]] = {
            "cpp": [
                (r"#include\s*<[a-zA-Z0-9_\.]+>", 0.95),
                (r"using\s+namespace\s+std\s*;", 0.95),
                (r"vector\s*<", 0.90),
                (r"push_back\s*\(", 0.85),
                (r"cout\s*<<", 0.85),
                (r"cin\s*>>", 0.85),
                (r"std::", 0.80),
                (r"int\s+main\s*\(\s*\)", 0.80)
            ],
            "java": [
                (r"public\s+class\s+[A-Za-z0-9_]+", 0.95),
                (r"System\.out\.print", 0.95),
                (r"List\s*<\s*List\s*<", 0.90),
                (r"ArrayList\s*<", 0.90),
                (r"public\s+static\s+void\s+main", 0.90),
                (r"@Override", 0.85),
                (r"new\s+[A-Z][a-zA-Z0-9_]*\s*\(", 0.70)
            ],
            "python": [
                (r"def\s+[a-zA-Z0-9_]+\s*\(.*?\)\s*:", 0.95),
                (r"self\.[a-zA-Z0-9_]+", 0.90),
                (r"import\s+[a-zA-Z0-9_]+", 0.80),
                (r"from\s+[a-zA-Z0-9_]+\s+import", 0.85),
                (r"if\s+__name__\s*==\s*['\"]__main__['\"]:", 0.95),
                (r"print\s*\(.*?\)", 0.75),
                (r"elif\s+.*?:", 0.85)
            ],
            "javascript": [
                (r"const\s+[a-zA-Z0-9_]+\s*=", 0.80),
                (r"let\s+[a-zA-Z0-9_]+\s*=", 0.80),
                (r"console\.log\s*\(", 0.90),
                (r"function\s+[a-zA-Z0-9_]+\s*\(", 0.85),
                (r"export\s+default", 0.90),
                (r"=>", 0.65)
            ],
            "typescript": [
                (r"interface\s+[A-Z][a-zA-Z0-9_]+", 0.90),
                (r"type\s+[A-Z][a-zA-Z0-9_]+\s*=", 0.90),
                (r":\s*(string|number|boolean|any|void)\b", 0.85),
                (r"as\s+[A-Z][a-zA-Z0-9_]+", 0.80)
            ],
            "go": [
                (r"func\s+[a-zA-Z0-9_]+\s*\(", 0.95),
                (r"package\s+[a-zA-Z0-9_]+", 0.95),
                (r"import\s*\(\s*\"[a-zA-Z0-9_/\.]+\"", 0.90),
                (r"fmt\.Print", 0.90),
                (r":=", 0.80)
            ],
            "rust": [
                (r"fn\s+[a-zA-Z0-9_]+\s*\(", 0.95),
                (r"let\s+mut\s+", 0.95),
                (r"println!\s*\(", 0.95),
                (r"impl\s+[A-Z]", 0.90),
                (r"match\s+[a-zA-Z0-9_]+", 0.80)
            ]
        }

    def classify_language(self, code_text: str) -> Tuple[str, float]:
        """
        Classifies programming language of a code block using multi-signal pattern matching.
        Returns (language_name, confidence_score).
        If unidentifiable, returns ("LANGUAGE_UNCERTAIN", 0.0).
        """
        if not code_text or len(code_text.strip()) < 5:
            return "LANGUAGE_UNCERTAIN", 0.0

        scores: Dict[str, float] = {}

        for lang, patterns in self.language_patterns.items():
            lang_score = 0.0
            matches_count = 0
            for pat, weight in patterns:
                if re.search(pat, code_text):
                    lang_score += weight
                    matches_count += 1
            if matches_count > 0:
                scores[lang] = round(min(0.99, lang_score / min(3, max(1, len(patterns) // 2))), 2)

        if not scores:
            return "LANGUAGE_UNCERTAIN", 0.0

        # Select highest confidence language
        best_lang = max(scores, key=scores.get)
        best_conf = scores[best_lang]

        if best_conf < 0.40:
            return "LANGUAGE_UNCERTAIN", best_conf

        return best_lang, best_conf

    def detect_code_regions(self, frame_text: str, timestamp: float) -> List[CodeRegion]:
        """
        Detects multiple distinct code regions in the same frame (e.g. Java panel on left, C++ panel on right).
        Separates text blocks and classifies language per region.
        """
        if not frame_text or not frame_text.strip():
            return []

        regions: List[CodeRegion] = []
        # Split by explicit multi-language section markers or headers if present
        blocks = re.split(r'\n(?=/\*|\/\/|#|\bJava\b|\bC\+\+\b|\bPython\b|\bGo\b|\bRust\b|\bJavaScript\b)', frame_text, flags=re.IGNORECASE)

        for idx, block in enumerate(blocks, start=1):
            cleaned_block = block.strip()
            if len(cleaned_block) < 10:
                continue

            lang, conf = self.classify_language(cleaned_block)
            reg_id = f"reg_{uuid.uuid4().hex[:8]}"

            regions.append(CodeRegion(
                region_id=reg_id,
                frame_timestamp=timestamp,
                language=lang,
                language_confidence=conf,
                code_text=cleaned_block,
                observation_type=ObservationType.DIRECTLY_OBSERVED
            ))

        # Fallback if no separate blocks were identified
        if not regions:
            lang, conf = self.classify_language(frame_text)
            regions.append(CodeRegion(
                region_id=f"reg_{uuid.uuid4().hex[:8]}",
                frame_timestamp=timestamp,
                language=lang,
                language_confidence=conf,
                code_text=frame_text.strip(),
                observation_type=ObservationType.DIRECTLY_OBSERVED
            ))

        return regions


# Global singleton instance for language classifier
code_language_classifier = CodeLanguageClassifier()
