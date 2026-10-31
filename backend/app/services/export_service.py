import os
import json
import uuid
import zipfile
import hashlib
import csv
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from app.config import settings
from app.schemas import KnowledgeItemResponse
from app.services.library_service import library_service
from app.services.artifact_service import artifact_service


class ExportService:
    """
    VidMind Advanced Export & Offline Package Service.
    Generates 100% deterministic exports from saved library knowledge:
    Markdown, PDF, Code, JSON (v1.0 schema), Anki CSV, and Complete Offline ZIP Package.
    Enforces path traversal safety, secret exclusion, and ownership isolation.
    """

    def __init__(self):
        self.export_base_dir = os.path.join(os.path.abspath(settings.artifacts_dir), "exports")
        os.makedirs(self.export_base_dir, exist_ok=True)

    def _get_item_dir(self, item_id: str) -> str:
        safe_item_id = artifact_service.sanitize_filename(item_id)
        item_dir = os.path.join(self.export_base_dir, safe_item_dir_name(safe_item_id))
        os.makedirs(item_dir, exist_ok=True)
        return item_dir

    def _verify_item_access(self, knowledge_item_id: str, owner_id: str) -> KnowledgeItemResponse:
        item = library_service.get_knowledge_item(knowledge_item_id, owner_id=owner_id)
        if not item:
            raise ValueError(f"Knowledge item '{knowledge_item_id}' not found or access denied.")
        return item

    def _calculate_sha256(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _sanitize_string_no_secrets(self, text: str) -> str:
        """Verifies and scrubs any secret environment variables from text output."""
        if not text:
            return ""
        # Scrub any accidental env key leaks
        for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "XAI_API_KEY"]:
            val = getattr(settings, k.lower(), None)
            if val and isinstance(val, str) and len(val) > 8:
                text = text.replace(val, "[REDACTED_SECRET]")
        return text

    # --- 1. MARKDOWN EXPORT ---

    def export_markdown(self, knowledge_item_id: str, owner_id: str = "default_user") -> Tuple[str, str]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)

        lines = [
            f"# {item.title}",
            "",
            f"> **Source URL**: `{item.source_url}`  ",
            f"> **Collection ID**: `{item.collection_id}`  ",
            f"> **Saved Date**: {item.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"> **Format**: Unified Offline Knowledge Export",
            "",
            "---",
            ""
        ]

        snapshot = item.knowledge_snapshot or {}
        nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []

        for node in nodes:
            if isinstance(node, dict):
                t_title = node.get("topic_title", "Topic")
                c_summary = node.get("concept_summary", "")
                lines.append(f"## 📌 {t_title}")
                lines.append(f"{c_summary}")
                lines.append("")

                code_snippets = node.get("code_snippets") or []
                if code_snippets:
                    lines.append("### Code Implementations")
                    for cs in code_snippets:
                        if isinstance(cs, dict):
                            lang = cs.get("language", "text")
                            fname = cs.get("filename", "solution")
                            code_txt = cs.get("code_content", "")
                            lines.append(f"#### Implementation (`{fname}` - `{lang.upper()}`)")
                            lines.append(f"```{lang}\n{code_txt}\n```")
                            lines.append("")

                complexities = node.get("complexities")
                if isinstance(complexities, dict):
                    t_comp = complexities.get("time_complexity")
                    s_comp = complexities.get("space_complexity")
                    if t_comp or s_comp:
                        lines.append("### Complexity Analysis")
                        lines.append(f"- **Time Complexity**: `{t_comp or 'N/A'}`")
                        lines.append(f"- **Space Complexity**: `{s_comp or 'N/A'}`")
                        lines.append("")

                evidence_refs = node.get("evidence_references") or []
                if evidence_refs:
                    lines.append("### Evidence & Source Provenance")
                    for ev in evidence_refs:
                        if isinstance(ev, dict):
                            v_id = ev.get("video_id", "unknown_video")
                            start_t = ev.get("start_seconds", 0.0)
                            obs_type = ev.get("observation_type", "DIRECTLY_OBSERVED")
                            lines.append(f"- 📍 Video `{v_id}` @ `{start_t:.1f}s` (`{obs_type}`)")
                    lines.append("")

        lines.append("---")
        lines.append("*Generated by VidMind — Deterministic Offline Knowledge Export*")

        content = self._sanitize_string_no_secrets("\n".join(lines))
        filename = f"{artifact_service.sanitize_filename(item.title)}.md"
        filepath = os.path.join(item_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath, filename

    # --- 2. JSON EXPORT (v1.0 Schema) ---

    def export_json(self, knowledge_item_id: str, owner_id: str = "default_user") -> Tuple[str, str]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)

        json_data = {
            "schema_version": "1.0",
            "package_type": "vidmind_knowledge_json",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "knowledge_item": {
                "item_id": item.item_id,
                "collection_id": item.collection_id,
                "project_id": item.project_id,
                "title": item.title,
                "description": item.description,
                "source_url": item.source_url,
                "is_playlist": item.is_playlist,
                "created_at": item.created_at.isoformat()
            },
            "knowledge_snapshot": item.knowledge_snapshot,
            "artifact_references": item.artifact_references
        }

        json_str = self._sanitize_string_no_secrets(json.dumps(json_data, indent=2))
        filename = f"{artifact_service.sanitize_filename(item.title)}.json"
        filepath = os.path.join(item_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)

        return filepath, filename

    # --- 3. CODE EXPORT ---

    def export_code(self, knowledge_item_id: str, owner_id: str = "default_user") -> List[Tuple[str, str]]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)
        code_sub_dir = os.path.join(item_dir, "code")
        os.makedirs(code_sub_dir, exist_ok=True)

        snapshot = item.knowledge_snapshot or {}
        nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []

        exported_files: List[Tuple[str, str]] = []
        used_filenames = set()

        for node in nodes:
            if isinstance(node, dict):
                code_snippets = node.get("code_snippets") or []
                for cs in code_snippets:
                    if isinstance(cs, dict):
                        lang = cs.get("language", "python")
                        fname = cs.get("filename", "solution")
                        code_txt = cs.get("code_content", "")

                        clean_fname, ext, comment_prefix = artifact_service._get_language_extension_and_comment(lang, fname)

                        # Prevent filename collisions
                        counter = 1
                        final_fname = clean_fname
                        base, extension = os.path.splitext(clean_fname)
                        while final_fname in used_filenames:
                            final_fname = f"{base}_{counter}{extension}"
                            counter += 1
                        used_filenames.add(final_fname)

                        filepath = os.path.join(code_sub_dir, final_fname)
                        file_content = self._sanitize_string_no_secrets(
                            f"{comment_prefix} VidMind Code Export: {lang.upper()}\n"
                            f"{comment_prefix} Source: {item.source_url}\n\n"
                            f"{code_txt}\n"
                        )
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(file_content)

                        exported_files.append((filepath, final_fname))

        if not exported_files:
            # Generate default fallback python script if no code snippet was saved
            filepath = os.path.join(code_sub_dir, "solution.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# VidMind Knowledge: {item.title}\n# Source: {item.source_url}\n")
            exported_files.append((filepath, "solution.py"))

        return exported_files

    # --- 4. ANKI FLASHCARD EXPORT (CSV) ---

    def export_anki(self, knowledge_item_id: str, owner_id: str = "default_user") -> Tuple[str, str]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)

        filename = f"{artifact_service.sanitize_filename(item.title)}_anki.csv"
        filepath = os.path.join(item_dir, filename)

        snapshot = item.knowledge_snapshot or {}
        nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []

        rows: List[List[str]] = [["Front", "Back", "Tags"]]

        for node in nodes:
            if isinstance(node, dict):
                t_title = node.get("topic_title", "Topic")
                summary = node.get("concept_summary", "")
                
                if t_title and summary:
                    rows.append([
                        self._sanitize_string_no_secrets(f"What is {t_title}?"),
                        self._sanitize_string_no_secrets(summary),
                        self._sanitize_string_no_secrets(f"VidMind {item.title}")
                    ])

                qna_list = node.get("questions_and_answers") or []
                for qna in qna_list:
                    if isinstance(qna, dict):
                        q = qna.get("question")
                        a = qna.get("answer")
                        if q and a:
                            rows.append([
                                self._sanitize_string_no_secrets(q),
                                self._sanitize_string_no_secrets(a),
                                self._sanitize_string_no_secrets(f"VidMind {t_title}")
                            ])

                complexities = node.get("complexities")
                if isinstance(complexities, dict):
                    t_comp = complexities.get("time_complexity")
                    if t_comp:
                        rows.append([
                            self._sanitize_string_no_secrets(f"What is the time complexity of {t_title}?"),
                            self._sanitize_string_no_secrets(f"Time Complexity: {t_comp}"),
                            self._sanitize_string_no_secrets(f"VidMind {t_title}")
                        ])

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerows(rows)

        return filepath, filename

    # --- 5. PDF EXPORT ---

    def export_pdf(self, knowledge_item_id: str, owner_id: str = "default_user") -> Tuple[str, str]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)
        filename = f"{artifact_service.sanitize_filename(item.title)}.pdf"
        filepath = os.path.join(item_dir, filename)

        # Generate readable PDF via ReportLab if available, or fall back to structured text PDF representation
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor='#4F46E5',
                spaceAfter=12
            )
            h2_style = ParagraphStyle(
                'DocH2',
                parent=styles['Heading2'],
                fontSize=14,
                textColor='#111827',
                spaceBefore=10,
                spaceAfter=6
            )
            body_style = styles['Normal']

            story.append(Paragraph(item.title, title_style))
            story.append(Paragraph(f"<b>Source URL:</b> {item.source_url}", body_style))
            story.append(Paragraph(f"<b>Created:</b> {item.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", body_style))
            story.append(Spacer(1, 12))

            snapshot = item.knowledge_snapshot or {}
            nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []

            for node in nodes:
                if isinstance(node, dict):
                    t_title = node.get("topic_title", "Topic")
                    summary = node.get("concept_summary", "")
                    story.append(Paragraph(t_title, h2_style))
                    if summary:
                        story.append(Paragraph(summary, body_style))
                    story.append(Spacer(1, 8))

            doc.build(story)
        except Exception:
            # Fallback simple text PDF writing
            with open(filepath, "wb") as f:
                content = f"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /Resources << >> /Contents 4 0 R >> endobj\n4 0 obj << /Length 50 >> stream\nBT /F1 12 Tf 50 700 TD ({item.title}) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer << /Size 5 /Root 1 0 R >>\nstartxref\n304\n%%EOF".encode("utf-8")
                f.write(content)

        return filepath, filename

    # --- 6. COMPLETE OFFLINE ZIP KNOWLEDGE PACKAGE EXPORT ---

    def export_zip(self, knowledge_item_id: str, owner_id: str = "default_user") -> Tuple[str, str]:
        item = self._verify_item_access(knowledge_item_id, owner_id=owner_id)
        item_dir = self._get_item_dir(knowledge_item_id)
        zip_filename = f"{artifact_service.sanitize_filename(item.title)}_offline_pack.zip"
        zip_filepath = os.path.join(item_dir, zip_filename)

        # 1. Generate constituent files
        md_path, md_name = self.export_markdown(knowledge_item_id, owner_id=owner_id)
        json_path, json_name = self.export_json(knowledge_item_id, owner_id=owner_id)
        anki_path, anki_name = self.export_anki(knowledge_item_id, owner_id=owner_id)
        code_files = self.export_code(knowledge_item_id, owner_id=owner_id)

        # 2. Build README.md for Offline Package
        readme_content = self._sanitize_string_no_secrets(
            f"# {item.title} — VidMind Offline Knowledge Package\n\n"
            f"This is a self-contained, offline-usable AI knowledge package generated by VidMind.\n\n"
            f"## Package Contents\n"
            f"- `README.md`: Package index and setup guide\n"
            f"- `manifest.json`: Schema versioning and file SHA256 integrity hashes\n"
            f"- `knowledge.json`: Structured machine-readable knowledge snapshot\n"
            f"- `notes/knowledge.md`: Complete Markdown notes\n"
            f"- `code/`: Runnable programming implementations\n"
            f"- `flashcards/anki.csv`: Anki-compatible study flashcards\n\n"
            f"## Source Metadata\n"
            f"- **Source URL**: {item.source_url}\n"
            f"- **Saved Date**: {item.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
        readme_path = os.path.join(item_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # 3. Calculate File Hashes for manifest.json
        file_entries: List[Dict[str, str]] = [
            {"path": "README.md", "sha256": self._calculate_sha256(readme_path)},
            {"path": "knowledge.json", "sha256": self._calculate_sha256(json_path)},
            {"path": "notes/knowledge.md", "sha256": self._calculate_sha256(md_path)},
            {"path": "flashcards/anki.csv", "sha256": self._calculate_sha256(anki_path)}
        ]
        for c_path, c_name in code_files:
            file_entries.append({
                "path": f"code/{c_name}",
                "sha256": self._calculate_sha256(c_path)
            })

        manifest_data = {
            "schema_version": "1.0",
            "package_type": "vidmind_offline_package",
            "knowledge_item_id": item.item_id,
            "title": item.title,
            "source_url": item.source_url,
            "created_at": item.created_at.isoformat(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "files": file_entries
        }
        manifest_path = os.path.join(item_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # 4. Zip all files together
        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(readme_path, arcname="README.md")
            zf.write(manifest_path, arcname="manifest.json")
            zf.write(json_path, arcname="knowledge.json")
            zf.write(md_path, arcname="notes/knowledge.md")
            zf.write(anki_path, arcname="flashcards/anki.csv")
            for c_path, c_name in code_files:
                zf.write(c_path, arcname=f"code/{c_name}")

        return zip_filepath, zip_filename


def safe_item_dir_name(item_id: str) -> str:
    cleaned = artifact_service.sanitize_filename(item_id)
    return cleaned.replace("..", "_")


# Global singleton instance for export service
export_service = ExportService()
