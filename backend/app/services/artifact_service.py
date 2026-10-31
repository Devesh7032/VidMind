import os
import json
import uuid
import zipfile
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from app.config import settings
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    ExtractionPlan,
    IntentCategory,
    ContentType,
    ArtifactType,
    ArtifactMetadataResponse,
    ProjectArtifactsListResponse,
    CodeSnippet
)
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.project_service import project_service


class ArtifactService:
    def __init__(self):
        # Base directory for persistent offline artifact storage
        self.artifacts_base_dir = os.path.abspath(settings.artifacts_dir)
        os.makedirs(self.artifacts_base_dir, exist_ok=True)
        # Store in-memory metadata index: artifact_id -> file_path
        self._artifacts_index: Dict[str, Dict] = {}

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes filename against path traversal and unsafe characters."""
        if not filename:
            return "code_snippet.txt"
        base_name = os.path.basename(filename)
        # Keep alphanumeric, dots, underscores, dashes
        cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base_name)
        return cleaned or "code_snippet.txt"

    def get_project_artifact_dir(self, project_id: str) -> str:
        safe_pid = self.sanitize_filename(project_id)
        proj_dir = os.path.join(self.artifacts_base_dir, "projects", safe_pid)
        os.makedirs(proj_dir, exist_ok=True)
        return proj_dir

    def _get_enum_val(self, enum_or_str: Any, default: str = "UNKNOWN") -> str:
        """Safely extracts string representation from Enum or string value."""
        if enum_or_str is None:
            return default
        return getattr(enum_or_str, "value", str(enum_or_str))

    def _get_language_extension_and_comment(self, language: str, filename: str) -> Tuple[str, str, str]:
        """
        Determines target file extension, comment prefix, and filename for code snippets.
        Supports multi-language extraction and LANGUAGE_UNCERTAIN labeling.
        """
        lang = (language or "").lower().strip()
        ext = os.path.splitext(filename)[1].lower() if filename else ""

        if lang in ["cpp", "c++", "c"] or ext in [".cpp", ".hpp", ".c", ".h", ".cc"]:
            target_ext = ".cpp"
            comment_prefix = "//"
        elif lang in ["java"] or ext in [".java"]:
            target_ext = ".java"
            comment_prefix = "//"
        elif lang in ["javascript", "js", "typescript", "ts"] or ext in [".js", ".ts", ".jsx", ".tsx"]:
            target_ext = ".js" if "javascript" in lang or ext == ".js" else ".ts"
            comment_prefix = "//"
        elif lang in ["python", "py"] or ext in [".py"]:
            target_ext = ".py"
            comment_prefix = "#"
        elif lang in ["html", "xml"]:
            target_ext = ".html"
            comment_prefix = "<!--"
        elif lang == "language_uncertain" or lang == "uncertain":
            target_ext = ext or ".txt"
            comment_prefix = "#"
        else:
            target_ext = ext or ".txt"
            comment_prefix = "#"

        base_clean = self.sanitize_filename(filename or f"code_snippet{target_ext}")
        if not base_clean.endswith(target_ext):
            base_clean = f"{os.path.splitext(base_clean)[0]}{target_ext}"

        return base_clean, target_ext, comment_prefix

    def generate_markdown_content(
        self,
        ikr: IntermediateKnowledgeRepresentation,
        plan: ExtractionPlan
    ) -> str:
        """
        Deterministic Markdown Generator.
        Renders structured Markdown strictly formatted according to user ExtractionPlan.
        Clearly labels multi-language code implementations.
        """
        lines = []
        intent_cat = self._get_enum_val(ikr.intent_category, "STUDY_NOTES")

        # Document Header
        lines.append(f"# {ikr.title or 'VidMind Knowledge Pack'}")
        lines.append("")
        lines.append(f"> **Intent Category**: `{intent_cat}`  ")
        lines.append(f"> **Generated**: {ikr.reasoning_completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
        lines.append(f"> **Status**: Usable completely offline without YouTube or server dependency.")
        lines.append("")
        lines.append("---")
        lines.append("")

        content_types_str = [self._get_enum_val(ct) for ct in (plan.content_types or [])]

        # 1. CODE_EXTRACTION Intent Document Layout
        if intent_cat == IntentCategory.CODE_EXTRACTION.value or ContentType.CODE.value in content_types_str:
            lines.append("## Code Implementations & Technical Analysis")
            lines.append("")

            for node in ikr.topic_nodes:
                lines.append(f"### {node.topic_title or 'Code Analysis'}")
                lines.append("")
                lines.append(f"{node.concept_summary or 'Extract code and algorithm analysis.'}")
                lines.append("")

                if node.code_snippets:
                    for snippet in node.code_snippets:
                        clean_fname, _, _ = self._get_language_extension_and_comment(
                            snippet.language or "python",
                            snippet.filename or "code.py"
                        )
                        lang_display = (snippet.language or "LANGUAGE_UNCERTAIN").upper()
                        lines.append(f"#### Implementation ({lang_display}: `{clean_fname}`)")
                        lines.append(f"```{snippet.language or ''}")
                        lines.append((snippet.code_content or "").strip())
                        lines.append("```")
                        
                        syn_val = self._get_enum_val(snippet.syntax_validity, "VERIFIED")
                        rec_val = self._get_enum_val(snippet.reconstruction_status, "DIRECTLY_OBSERVED")
                        lines.append(f"*Language*: `{lang_display}` | *Syntax Status*: `{syn_val}` | *Reconstruction*: `{rec_val}`")
                        lines.append("")

                if node.complexities:
                    lines.append("#### Complexity Analysis")
                    lines.append(f"- **Time Complexity**: `{node.complexities.time_complexity or 'N/A'}`")
                    lines.append(f"- **Space Complexity**: `{node.complexities.space_complexity or 'N/A'}`")
                    if node.complexities.explanation:
                        lines.append(f"- *Explanation*: {node.complexities.explanation}")
                    lines.append("")

                if node.evidence_references:
                    ev = node.evidence_references[0]
                    start_t = ev.start_seconds if ev.start_seconds is not None else 0.0
                    end_t = ev.end_seconds if ev.end_seconds is not None else start_t + 10.0
                    obs_val = self._get_enum_val(ev.observation_type, "DIRECTLY_OBSERVED")
                    lines.append(f"📍 *Source Timestamp*: Video `{ev.video_id or 'source'}` @ `{start_t:.1f}s - {end_t:.1f}s` (`{obs_val}`)")
                    lines.append("")

        # 2. FORMULA_SHEET Intent Document Layout
        elif intent_cat == IntentCategory.FORMULA_SHEET.value or ContentType.FORMULAS.value in content_types_str:
            lines.append("## Mathematical Formulas & Equation Reference")
            lines.append("")

            for node in ikr.topic_nodes:
                lines.append(f"### {node.topic_title or 'Formula Reference'}")
                lines.append(f"{node.concept_summary or 'Mathematical formulation'}")
                lines.append("")

                if node.formulas:
                    lines.append("#### Equations")
                    for formula in node.formulas:
                        lines.append(f"$$\n{formula}\n$$")
                        lines.append("")

                if node.key_examples:
                    lines.append("#### Examples & Variable Definitions")
                    for ex in node.key_examples:
                        lines.append(f"- {ex}")
                    lines.append("")

                if node.evidence_references:
                    ev = node.evidence_references[0]
                    start_t = ev.start_seconds if ev.start_seconds is not None else 0.0
                    end_t = ev.end_seconds if ev.end_seconds is not None else start_t + 10.0
                    obs_val = self._get_enum_val(ev.observation_type, "DIRECTLY_OBSERVED")
                    lines.append(f"📍 *Source Timestamp*: Video `{ev.video_id or 'source'}` @ `{start_t:.1f}s - {end_t:.1f}s` (`{obs_val}`)")
                    lines.append("")

        # 3. INTERVIEW_PREP Intent Document Layout
        elif intent_cat == IntentCategory.INTERVIEW_PREP.value or ContentType.QUESTIONS_ANSWERS.value in content_types_str:
            lines.append("## Technical Interview Preparation Q&A")
            lines.append("")

            for node in ikr.topic_nodes:
                lines.append(f"### Topic: {node.topic_title or 'Interview Topic'}")
                lines.append("")

                if node.questions_and_answers:
                    for idx, qna in enumerate(node.questions_and_answers, start=1):
                        lines.append(f"#### Q{idx}: {qna.get('question', '')}")
                        lines.append(f"**Answer**: {qna.get('answer', '')}")
                        lines.append("")

                if node.evidence_references:
                    ev = node.evidence_references[0]
                    start_t = ev.start_seconds if ev.start_seconds is not None else 0.0
                    end_t = ev.end_seconds if ev.end_seconds is not None else start_t + 10.0
                    obs_val = self._get_enum_val(ev.observation_type, "DIRECTLY_OBSERVED")
                    lines.append(f"📍 *Source Timestamp*: Video `{ev.video_id or 'source'}` @ `{start_t:.1f}s - {end_t:.1f}s` (`{obs_val}`)")
                    lines.append("")

        # 4. STUDY_NOTES / EXAM_REVISION Intent Document Layout
        else:
            lines.append("## Core Lecture Concepts & Revision Notes")
            lines.append("")

            for node in ikr.topic_nodes:
                lines.append(f"### 📌 {node.topic_title or 'Core Topic'}")
                lines.append(f"{node.concept_summary or ''}")
                lines.append("")

                if node.key_examples:
                    lines.append("#### Key Examples")
                    for ex in node.key_examples:
                        lines.append(f"- {ex}")
                    lines.append("")

                if node.complexities:
                    obs_val = self._get_enum_val(node.complexities.observation_type, "DIRECTLY_OBSERVED")
                    lines.append("#### Algorithm Complexity")
                    lines.append(f"| Time Complexity | Space Complexity | Observation Type |")
                    lines.append(f"| :--- | :--- | :--- |")
                    lines.append(f"| `{node.complexities.time_complexity or 'N/A'}` | `{node.complexities.space_complexity or 'N/A'}` | `{obs_val}` |")
                    lines.append("")

                if node.evidence_references:
                    ev = node.evidence_references[0]
                    start_t = ev.start_seconds if ev.start_seconds is not None else 0.0
                    end_t = ev.end_seconds if ev.end_seconds is not None else start_t + 10.0
                    obs_val = self._get_enum_val(ev.observation_type, "DIRECTLY_OBSERVED")
                    lines.append(f"📍 *Source Timestamp*: Video `{ev.video_id or 'source'}` @ `{start_t:.1f}s - {end_t:.1f}s` (`{obs_val}`)")
                    lines.append("")

        lines.append("---")
        lines.append("*Generated by VidMind — Personalized Offline AI Knowledge Package*")

        return "\n".join(lines)

    def _normalize_playlist_language_info(self, raw_lang: str) -> Tuple[str, str, str, str]:
        """
        Normalizes raw language name to (lang_key, display_name, file_name, code_tag).
        e.g. ("java", "Java", "playlist_java.md", "java")
             ("cpp", "C++", "playlist_cpp.md", "cpp")
             ("py", "Python", "playlist_py.md", "python")
        """
        l = (raw_lang or "python").lower().strip()
        if l in ["java"]:
            return "java", "Java", "playlist_java.md", "java"
        elif l in ["cpp", "c++", "c"]:
            return "cpp", "C++", "playlist_cpp.md", "cpp"
        elif l in ["python", "py"]:
            return "py", "Python", "playlist_py.md", "python"
        elif l in ["javascript", "js"]:
            return "js", "JavaScript", "playlist_js.md", "javascript"
        elif l in ["typescript", "ts"]:
            return "ts", "TypeScript", "playlist_ts.md", "typescript"
        else:
            clean = self.sanitize_filename(l).replace(".", "_")
            return clean, l.capitalize(), f"playlist_{clean}.md", l

    def _generate_playlist_code_files(
        self,
        project: Any,
        ikr: IntermediateKnowledgeRepresentation,
        proj_dir: str,
        code_dir: str,
        artifact_records: List[ArtifactMetadataResponse]
    ) -> List[str]:
        """
        Playlist Code Consolidation Engine:
        Consolidates all extracted code from the entire playlist by language into ONE markdown file per language:
        code/playlist_java.md
        code/playlist_cpp.md
        code/playlist_py.md
        Grouped strictly by VIDEO.
        Does NOT create empty language files.
        """
        generated_code_files: List[str] = []
        
        # Structure: lang_key -> v_key -> { position, title, source_url, snippets }
        language_data: Dict[str, Dict[str, Dict[str, Any]]] = {}

        pl_meta = project.playlist_metadata
        videos_list = pl_meta.videos if (pl_meta and pl_meta.videos) else []

        video_map: Dict[str, Dict[str, Any]] = {}
        for idx, v_item in enumerate(videos_list, start=1):
            v_key = v_item.video_id or f"vid_{idx}"
            v_info = {
                "position": idx,
                "title": v_item.title or f"Video #{idx}",
                "source_url": v_item.source_url or project.source_url
            }
            video_map[v_key] = v_info
            video_map[f"v{idx}"] = v_info
            video_map[f"pos_{idx}"] = v_info

        # 1. Collect snippets from per-video child IKRs
        for idx, v_item in enumerate(videos_list, start=1):
            child_pid = f"{project.project_id}_v{idx}"
            child_ikr = knowledge_reasoning_service.get_knowledge_representation(child_pid)
            if child_ikr and child_ikr.topic_nodes:
                for node in child_ikr.topic_nodes:
                    for snippet in node.code_snippets:
                        if not snippet.code_content or not snippet.code_content.strip():
                            continue
                        lang_key, display_name, file_name, code_tag = self._normalize_playlist_language_info(snippet.language)
                        v_key = f"v{idx}"

                        if lang_key not in language_data:
                            language_data[lang_key] = {}

                        if v_key not in language_data[lang_key]:
                            language_data[lang_key][v_key] = {
                                "position": idx,
                                "title": v_item.title or f"Video #{idx}",
                                "source_url": v_item.source_url or project.source_url,
                                "snippets": []
                            }

                        # Deduplicate identical code snippets under same video
                        existing_texts = [s.code_content.strip() for s in language_data[lang_key][v_key]["snippets"]]
                        if snippet.code_content.strip() not in existing_texts:
                            language_data[lang_key][v_key]["snippets"].append(snippet)

        # 2. Collect snippets from main project IKR (or unified playlist graph)
        for node in ikr.topic_nodes:
            for snippet in node.code_snippets:
                if not snippet.code_content or not snippet.code_content.strip():
                    continue
                lang_key, display_name, file_name, code_tag = self._normalize_playlist_language_info(snippet.language)

                v_idx = 1
                v_title = "Video #1"
                v_url = project.source_url
                if node.evidence_references:
                    ev = node.evidence_references[0]
                    if getattr(ev, "video_position", None):
                        v_idx = ev.video_position
                    v_title = f"Video #{v_idx}"
                    if getattr(ev, "video_id", None) and ev.video_id in video_map:
                        v_title = video_map[ev.video_id]["title"]
                        v_url = video_map[ev.video_id]["source_url"]

                v_key = f"v{v_idx}"
                if lang_key not in language_data:
                    language_data[lang_key] = {}

                if v_key not in language_data[lang_key]:
                    language_data[lang_key][v_key] = {
                        "position": v_idx,
                        "title": v_title,
                        "source_url": v_url,
                        "snippets": []
                    }

                existing_texts = [s.code_content.strip() for s in language_data[lang_key][v_key]["snippets"]]
                if snippet.code_content.strip() not in existing_texts:
                    language_data[lang_key][v_key]["snippets"].append(snippet)

        # 3. Generate ONE markdown file per language (e.g. code/playlist_java.md, code/playlist_cpp.md)
        for lang_key, v_map in language_data.items():
            if not v_map:
                continue

            _, display_name, file_name, code_tag = self._normalize_playlist_language_info(lang_key)
            total_snips = sum(len(d["snippets"]) for d in v_map.values())
            if total_snips == 0:
                continue

            lines = [
                f"# {display_name} Code — Playlist",
                ""
            ]

            sorted_vids = sorted(v_map.values(), key=lambda x: x["position"])

            for v_data in sorted_vids:
                if not v_data["snippets"]:
                    continue

                pos = v_data["position"]
                v_title = v_data["title"]
                v_url = v_data["source_url"]

                lines.append(f"## Video {pos} — {v_title}")
                lines.append("")
                lines.append(f"Source: {v_url}")

                for snippet in v_data["snippets"]:
                    start_t = snippet.start_seconds if snippet.start_seconds is not None else 0.0
                    end_t = snippet.end_seconds if snippet.end_seconds is not None else start_t + 10.0
                    
                    if end_t > start_t:
                        ts_str = f"{start_t:.1f}s - {end_t:.1f}s"
                    else:
                        ts_str = f"{start_t:.1f}s"

                    lines.append(f"Timestamp: {ts_str}")
                    lines.append("")
                    lines.append(f"### {display_name} Code")
                    lines.append("")
                    lines.append(f"```{code_tag}")
                    lines.append(snippet.code_content.strip())
                    lines.append("```")
                    lines.append("")

            code_file_path = os.path.join(code_dir, file_name)
            with open(code_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines).strip() + "\n")

            code_art_id = f"art_{uuid.uuid4().hex[:8]}"
            self._artifacts_index[code_art_id] = {
                "project_id": project.project_id,
                "filename": f"code/{file_name}",
                "filepath": code_file_path,
                "artifact_type": ArtifactType.CODE_FILES
            }
            generated_code_files.append(file_name)
            artifact_records.append(ArtifactMetadataResponse(
                artifact_id=code_art_id,
                project_id=project.project_id,
                filename=f"code/{file_name}",
                artifact_type=ArtifactType.CODE_FILES,
                file_size_bytes=os.path.getsize(code_file_path),
                download_url=f"/api/artifacts/{code_art_id}/download"
            ))

        return generated_code_files

    def validate_artifacts(self, project_id: str, proj_dir: str, artifact_records: List[ArtifactMetadataResponse]) -> bool:
        """
        Validates artifact package integrity before marking ready:
        1. Verifies all files exist on disk.
        2. Verifies path safety (no path traversal outside proj_dir).
        3. Verifies manifest.json is valid JSON.
        4. Verifies export_package.zip is a valid zip archive.
        """
        safe_proj_dir = os.path.abspath(proj_dir)

        # 1. Check File Existence & Path Bounds
        for art in artifact_records:
            art_file_path = self._artifacts_index[art.artifact_id]["filepath"]
            abs_path = os.path.abspath(art_file_path)

            if not abs_path.startswith(safe_proj_dir):
                raise SecurityError(f"[Artifact Validation] Path traversal detected: '{abs_path}' outside project boundary.")

            if not os.path.exists(abs_path) or os.path.getsize(abs_path) == 0:
                raise FileNotFoundError(f"[Artifact Validation] Artifact file '{art.filename}' missing or empty on disk.")

        # 2. Check manifest.json validity
        manifest_path = os.path.join(proj_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError("[Artifact Validation] manifest.json missing.")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_json = json.load(f)
            if "project_id" not in manifest_json or "generated_files" not in manifest_json:
                raise ValueError("[Artifact Validation] manifest.json missing required fields.")

        # 3. Check ZIP integrity
        zip_path = os.path.join(proj_dir, "export_package.zip")
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            raise ValueError("[Artifact Validation] export_package.zip is missing or corrupted.")

        return True

    def generate_project_artifacts(self, project_id: str) -> ProjectArtifactsListResponse:
        """
        Main Milestone 7 Artifact Packaging Engine:
        1. Fetches project IKR and ExtractionPlan.
        2. Renders Markdown `knowledge_pack.md`.
        3. Generates code files:
           - For SINGLE VIDEO: generates separate runnable source files (Solution.java, Solution.cpp, etc.).
           - For PLAYLIST: consolidates all code per language into ONE file (code/playlist_java.md, code/playlist_cpp.md, etc.) grouped by Video.
        4. Generates `manifest.json`.
        5. Compiles `export_package.zip`.
        6. Validates artifact package integrity.
        7. Stores metadata index and returns ProjectArtifactsListResponse.
        """
        stage = "INIT"
        try:
            stage = "FETCH_PROJECT"
            project = project_service.get_project(project_id)
            if not project:
                raise ValueError(f"Project '{project_id}' not found.")

            stage = "FETCH_IKR"
            ikr = knowledge_reasoning_service.get_knowledge_representation(project_id)
            if not ikr:
                ikr = knowledge_reasoning_service.construct_intermediate_knowledge_representation(project_id)

            plan = project.extraction_plan or ExtractionPlan()
            proj_dir = self.get_project_artifact_dir(project_id)
            code_dir = os.path.join(proj_dir, "code")
            os.makedirs(code_dir, exist_ok=True)

            artifact_records: List[ArtifactMetadataResponse] = []

            # 1. Generate knowledge_pack.md
            stage = "MARKDOWN_GENERATION"
            md_content = self.generate_markdown_content(ikr, plan)
            md_filename = "knowledge_pack.md"
            md_path = os.path.join(proj_dir, md_filename)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            md_art_id = f"art_{uuid.uuid4().hex[:8]}"
            self._artifacts_index[md_art_id] = {
                "project_id": project_id,
                "filename": md_filename,
                "filepath": md_path,
                "artifact_type": ArtifactType.MARKDOWN_DOCUMENT
            }
            artifact_records.append(ArtifactMetadataResponse(
                artifact_id=md_art_id,
                project_id=project_id,
                filename=md_filename,
                artifact_type=ArtifactType.MARKDOWN_DOCUMENT,
                file_size_bytes=os.path.getsize(md_path),
                download_url=f"/api/artifacts/{md_art_id}/download"
            ))

            # 2. Generate Code Files in code/ directory
            stage = "CODE_FILE_GENERATION"
            generated_code_files: List[str] = []

            if project.is_playlist:
                # PLAYLIST MODE: Consolidate code per language into code/playlist_{lang}.md
                generated_code_files = self._generate_playlist_code_files(
                    project=project,
                    ikr=ikr,
                    proj_dir=proj_dir,
                    code_dir=code_dir,
                    artifact_records=artifact_records
                )
            else:
                # SINGLE VIDEO MODE: Keep current behavior (Solution.java, Solution_1.java, Solution.cpp, etc.)
                used_filenames = set()
                for node in ikr.topic_nodes:
                    for snippet in node.code_snippets:
                        clean_fname, ext, comment_prefix = self._get_language_extension_and_comment(
                            snippet.language or "python",
                            snippet.filename or f"snippet{ext}"
                        )
                        
                        final_fname = clean_fname
                        counter = 1
                        base, extension = os.path.splitext(clean_fname)
                        while final_fname in used_filenames:
                            final_fname = f"{base}_{counter}{extension}"
                            counter += 1
                        used_filenames.add(final_fname)

                        code_file_path = os.path.join(code_dir, final_fname)

                        start_t = snippet.start_seconds if snippet.start_seconds is not None else 0.0
                        end_t = snippet.end_seconds if snippet.end_seconds is not None else start_t + 10.0
                        syn_val = self._get_enum_val(snippet.syntax_validity, "VERIFIED")
                        lang_lbl = (snippet.language or "LANGUAGE_UNCERTAIN").upper()

                        with open(code_file_path, "w", encoding="utf-8") as f:
                            if comment_prefix == "<!--":
                                f.write(f"<!-- Source: Video @ {start_t:.1f}s - {end_t:.1f}s | Language: {lang_lbl} | Syntax: {syn_val} -->\n\n")
                            else:
                                f.write(f"{comment_prefix} Language: {lang_lbl}\n")
                                f.write(f"{comment_prefix} Source: Video @ {start_t:.1f}s - {end_t:.1f}s\n")
                                f.write(f"{comment_prefix} Syntax Validity: {syn_val}\n\n")
                            f.write((snippet.code_content or "").strip())
                            f.write("\n")

                        code_art_id = f"art_{uuid.uuid4().hex[:8]}"
                        self._artifacts_index[code_art_id] = {
                            "project_id": project_id,
                            "filename": f"code/{final_fname}",
                            "filepath": code_file_path,
                            "artifact_type": ArtifactType.CODE_FILES
                        }
                        generated_code_files.append(final_fname)
                        artifact_records.append(ArtifactMetadataResponse(
                            artifact_id=code_art_id,
                            project_id=project_id,
                            filename=f"code/{final_fname}",
                            artifact_type=ArtifactType.CODE_FILES,
                            file_size_bytes=os.path.getsize(code_file_path),
                            download_url=f"/api/artifacts/{code_art_id}/download"
                        ))

            # 3. Generate manifest.json
            stage = "MANIFEST_GENERATION"
            intent_cat_str = self._get_enum_val(ikr.intent_category, "STUDY_NOTES")
            manifest_data = {
                "schema_version": "1.0",
                "project_id": project_id,
                "source_url": project.source_url,
                "user_prompt": project.user_prompt,
                "intent_category": intent_cat_str,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generated_files": [md_filename] + [f"code/{cf}" for cf in generated_code_files],
                "topic_nodes_count": len(ikr.topic_nodes)
            }
            manifest_path = os.path.join(proj_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            # 4. Compile export_package.zip
            stage = "ZIP_PACKAGING"
            zip_filename = "export_package.zip"
            zip_path = os.path.join(proj_dir, zip_filename)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(md_path, arcname=md_filename)
                zf.write(manifest_path, arcname="manifest.json")
                for cf in generated_code_files:
                    c_path = os.path.join(code_dir, cf)
                    zf.write(c_path, arcname=f"code/{cf}")

            zip_art_id = f"art_{uuid.uuid4().hex[:8]}"
            self._artifacts_index[zip_art_id] = {
                "project_id": project_id,
                "filename": zip_filename,
                "filepath": zip_path,
                "artifact_type": ArtifactType.ZIP_PROJECT
            }
            artifact_records.append(ArtifactMetadataResponse(
                artifact_id=zip_art_id,
                project_id=project_id,
                filename=zip_filename,
                artifact_type=ArtifactType.ZIP_PROJECT,
                file_size_bytes=os.path.getsize(zip_path),
                download_url=f"/api/artifacts/{zip_art_id}/download"
            ))

            # 5. Artifact Package Validation
            stage = "ARTIFACT_VALIDATION"
            self.validate_artifacts(project_id, proj_dir, artifact_records)

            return ProjectArtifactsListResponse(
                project_id=project_id,
                total_artifacts=len(artifact_records),
                artifacts=artifact_records,
                markdown_preview_content=md_content
            )

        except Exception as e:
            print(f"[ARTIFACT DEBUG] Stage: {stage} | Project ID: {project_id} | Error: {type(e).__name__}: {str(e)}")
            raise e

    def get_artifact_file_path(self, artifact_id: str) -> Optional[Tuple[str, str]]:
        """Returns (filepath, filename) for an artifact_id."""
        art = self._artifacts_index.get(artifact_id)
        if not art:
            return None
        return art["filepath"], art["filename"]


class SecurityError(Exception):
    pass


# Global singleton instance for artifact service
artifact_service = ArtifactService()
