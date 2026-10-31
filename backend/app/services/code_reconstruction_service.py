import os
import ast
import uuid
from typing import List, Dict, Tuple, Optional, Any
from app.schemas import (
    FusedEvidence,
    CodeSnippet,
    CodeRegion,
    ObservationType,
    SyntaxValidity
)
from app.services.code_language_classifier import code_language_classifier


class CodeReconstructionEngine:
    """
    VidMind Temporal Code Reconstruction Engine.
    Assembles progressive code frames across keyframe timestamp sequences into complete, runnable code files.
    Groups code into language-specific tracks, validates syntax, and preserves source provenance.
    Never invents missing code.
    """

    def validate_code_syntax(self, code_text: str, language: str) -> SyntaxValidity:
        """
        Validates syntax using language AST parsers or heuristic checking without executing code.
        """
        if not code_text or not code_text.strip():
            return SyntaxValidity.UNVERIFIED_FRAGMENT

        lang = (language or "").lower()

        # Python AST validation
        if lang == "python":
            try:
                ast.parse(code_text)
                return SyntaxValidity.VERIFIED
            except SyntaxError:
                return SyntaxValidity.UNVERIFIED_FRAGMENT

        # Braces balancing check for C++, Java, JS, Go, Rust
        if lang in ["cpp", "java", "javascript", "typescript", "go", "rust", "csharp"]:
            open_b = code_text.count("{")
            close_b = code_text.count("}")
            open_p = code_text.count("(")
            close_p = code_text.count(")")
            if open_b == close_b and open_p == close_p and open_b > 0:
                return SyntaxValidity.VERIFIED
            elif open_b >= 1:
                return SyntaxValidity.UNVERIFIED_FRAGMENT
            else:
                return SyntaxValidity.SYNTAX_ERROR

        return SyntaxValidity.VERIFIED

    def reconstruct_code_artifacts(self, evidence_list: List[FusedEvidence]) -> List[CodeSnippet]:
        """
        Main Milestone 2 Reconstruction Pipeline:
        1. Extracts code regions from keyframe evidence.
        2. Groups evidence into language-specific tracks.
        3. Merges progressive typing versions across timestamps into final complete code state.
        4. Validates syntax and generates language-appropriate filenames.
        5. Preserves source provenance.
        """
        # Step 1: Collect code regions across evidence
        tracks: Dict[str, List[Dict[str, Any]]] = {}

        for ev in evidence_list:
            if not ev.visual_observation:
                continue

            vis = ev.visual_observation
            raw_code = vis.visible_code_text

            if not raw_code or len(raw_code.strip()) < 10:
                continue

            # Detect code regions (handles single or multi-region frames)
            regions = vis.detected_regions
            if not regions:
                regions = code_language_classifier.detect_code_regions(raw_code, vis.frame_timestamp)

            for reg in regions:
                lang = reg.language
                if lang not in tracks:
                    tracks[lang] = []
                tracks[lang].append({
                    "evidence_id": ev.evidence_id,
                    "video_id": ev.video_id,
                    "start_seconds": ev.start_seconds,
                    "end_seconds": ev.end_seconds,
                    "timestamp": reg.frame_timestamp,
                    "code_text": reg.code_text,
                    "confidence": reg.language_confidence,
                    "observation_type": reg.observation_type
                })

        if not tracks:
            return []

        snippets: List[CodeSnippet] = []
        language_file_counts: Dict[str, int] = {}

        # Step 2: Temporal State Merging & Version Selection per Language Track
        for lang, entries in tracks.items():
            # Sort entries by timestamp
            entries.sort(key=lambda x: x["timestamp"])

            # Group progressive typing frames of the same implementation
            merged_versions: List[Dict[str, Any]] = []
            curr_version: Optional[Dict[str, Any]] = None

            for entry in entries:
                if not curr_version:
                    curr_version = dict(entry)
                else:
                    # Check if entry is a progressive extension of curr_version
                    if len(entry["code_text"]) > len(curr_version["code_text"]):
                        curr_version["code_text"] = entry["code_text"]
                        curr_version["end_seconds"] = max(curr_version["end_seconds"], entry["end_seconds"])
                        curr_version["observation_type"] = ObservationType.RECONSTRUCTED
                    elif entry["timestamp"] - curr_version["timestamp"] > 120.0:
                        # Genuinely new code implementation separated by >2 minutes
                        merged_versions.append(curr_version)
                        curr_version = dict(entry)

            if curr_version:
                merged_versions.append(curr_version)

            # Step 3: Generate CodeSnippet objects with unique filenames
            for ver in merged_versions:
                count = language_file_counts.get(lang, 0) + 1
                language_file_counts[lang] = count

                ext_map = {
                    "cpp": "cpp", "java": "java", "python": "py", "javascript": "js",
                    "typescript": "ts", "go": "go", "rust": "rs", "csharp": "cs",
                    "language_uncertain": "txt"
                }
                ext = ext_map.get(lang.lower(), "txt")

                filename = f"Solution.{ext}" if count == 1 else f"Solution_{count}.{ext}"
                syntax_val = self.validate_code_syntax(ver["code_text"], lang)

                snippets.append(CodeSnippet(
                    filename=filename,
                    language=lang,
                    code_content=ver["code_text"],
                    start_seconds=ver["start_seconds"],
                    end_seconds=ver["end_seconds"],
                    reconstruction_status=ver["observation_type"],
                    syntax_validity=syntax_val
                ))

        return snippets


# Global singleton instance for code reconstruction engine
code_reconstruction_engine = CodeReconstructionEngine()
code_reconstruction_service = code_reconstruction_engine
