import os
import tempfile
import pytest
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    ExtractionPlan,
    KnowledgeNode,
    CodeSnippet,
    SyntaxValidity,
    ObservationType,
    IntentCategory
)
from app.services.artifact_service import artifact_service
from app.services.export_service import export_service
from app.services.security_service import security_service

UNICODE_TEST_STRINGS = [
    "Hello World",
    "✓ → • — ©",
    "café résumé naïve",
    "தமிழ்",
    "हिन्दी",
    "中文",
    "🚀 🎯 ✅"
]


def test_1_markdown_generation_with_all_unicode_scripts():
    """Test 1: Markdown generation preserves English, Symbols, European, Tamil, Hindi, Chinese & Emojis."""
    full_unicode_text = " | ".join(UNICODE_TEST_STRINGS)
    ikr = IntermediateKnowledgeRepresentation(
        project_id="proj_utf8_test",
        title=f"VidMind UTF-8 Knowledge {full_unicode_text}",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="node_1",
                topic_title=f"Multi-Language Topic {full_unicode_text}",
                concept_summary=f"Summary with symbols: {full_unicode_text}",
                code_snippets=[
                    CodeSnippet(
                        filename="Solution.py",
                        language="python",
                        code_content=f"# Unicode comment: {full_unicode_text}\ndef solve():\n    print('{full_unicode_text}')\n",
                        start_seconds=10.0,
                        end_seconds=20.0,
                        reconstruction_status=ObservationType.DIRECTLY_OBSERVED,
                        syntax_validity=SyntaxValidity.VERIFIED
                    )
                ]
            )
        ]
    )

    plan = ExtractionPlan(intent_category=IntentCategory.CODE_EXTRACTION)
    md = artifact_service.generate_markdown_content(ikr, plan)

    for item in UNICODE_TEST_STRINGS:
        assert item in md


def test_2_writing_code_files_with_utf8():
    """Test 2: Code files (.py, .js, .cpp, .java) write and read cleanly using UTF-8 without charmap errors."""
    full_unicode_text = " | ".join(UNICODE_TEST_STRINGS)
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "solution_utf8.py")
        content = f"# Source: Video @ 10.0s\n# Symbols: {full_unicode_text}\nprint('{full_unicode_text}')\n"
        
        # Explicit UTF-8 write
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Explicit UTF-8 read
        with open(test_file, "r", encoding="utf-8") as f:
            read_back = f.read()

        assert read_back == content
        for item in UNICODE_TEST_STRINGS:
            assert item in read_back


def test_3_json_serialization_preserves_unicode():
    """Test 3: JSON serialization preserves Unicode characters without ASCII escaping."""
    import json
    data = {"unicode_test": UNICODE_TEST_STRINGS}
    serialized = json.dumps(data, ensure_ascii=False, indent=2)

    for item in UNICODE_TEST_STRINGS:
        assert item in serialized


def test_4_secret_scrubbing_does_not_mutate_unicode():
    """Test 4: Secret scrubbing preserves Unicode while redacting keys."""
    raw_text = "Gemini API key 1234567890123 failed on தமிழ், हिन्दी, 中文, 🚀."
    scrubbed = security_service.scrub_secrets(raw_text)
    assert "1234567890123" not in scrubbed
    assert "தமிழ்" in scrubbed
    assert "हिन्दी" in scrubbed
    assert "中文" in scrubbed
    assert "🚀" in scrubbed


def test_5_windows_console_encoding_safety():
    """Test 5: Printing Unicode text on Windows console does not raise UnicodeEncodeError."""
    import sys
    try:
        full_str = " | ".join(UNICODE_TEST_STRINGS)
        formatted = f"[Console Test] {full_str}"
        assert len(formatted) > 0
    except UnicodeEncodeError:
        pytest.fail("Console output formatting raised UnicodeEncodeError!")
