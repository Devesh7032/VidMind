import pytest
from app.schemas import (
    FusedEvidence,
    VisualObservation,
    VisualContentType,
    ObservationType,
    SyntaxValidity,
    CodeRegion
)
from app.services.code_language_classifier import code_language_classifier
from app.services.code_reconstruction_service import code_reconstruction_service


def test_code_language_classifier_multi_signal_detection():
    """Requirement: Multi-signal heuristic language classification."""
    cpp_code = "#include <vector>\nusing namespace std;\nint main() { vector<int> v; v.push_back(1); }"
    lang, conf = code_language_classifier.classify_language(cpp_code)
    assert lang == "cpp"
    assert conf >= 0.80

    java_code = "public class Solution { public static void main(String[] args) { System.out.println(\"Hello\"); } }"
    lang, conf = code_language_classifier.classify_language(java_code)
    assert lang == "java"
    assert conf >= 0.80

    py_code = "def bfs(graph, start):\n    visited = set()\n    queue = [start]\n    print(queue)"
    lang, conf = code_language_classifier.classify_language(py_code)
    assert lang == "python"
    assert conf >= 0.70

    js_code = "const express = require('express');\nconst app = express();\nconsole.log(app);"
    lang, conf = code_language_classifier.classify_language(js_code)
    assert lang == "javascript"

    go_code = "package main\nimport \"fmt\"\nfunc main() {\n    fmt.Println(\"Hello Go\")\n}"
    lang, conf = code_language_classifier.classify_language(go_code)
    assert lang == "go"

    rust_code = "fn main() {\n    let mut vec = Vec::new();\n    println!(\"Hello Rust\");\n}"
    lang, conf = code_language_classifier.classify_language(rust_code)
    assert lang == "rust"

    uncertain_code = "foo bar baz 123 456"
    lang, conf = code_language_classifier.classify_language(uncertain_code)
    assert lang == "LANGUAGE_UNCERTAIN"


def test_multiple_code_regions_in_same_frame():
    """Requirement: Detect multiple distinct code panels (e.g. Java and C++) in the same frame."""
    frame_text = """
    // Java Implementation
    public class Solution {
        List<List<Integer>> res = new ArrayList<>();
    }

    // C++ Implementation
    #include <vector>
    using namespace std;
    vector<vector<int>> bridges;
    """
    regions = code_language_classifier.detect_code_regions(frame_text, timestamp=15.0)
    assert len(regions) >= 2
    languages = [r.language for r in regions]
    assert "java" in languages
    assert "cpp" in languages


def test_temporal_code_reconstruction_progressive_merging():
    """Requirement: Temporal reconstruction merges progressive typing frames into final complete state."""
    ev1 = FusedEvidence(
        evidence_id="ev1",
        video_id="vid123",
        start_seconds=10.0,
        end_seconds=20.0,
        transcript_text="Java implementation start",
        visual_observation=VisualObservation(
            frame_timestamp=15.0,
            content_type=VisualContentType.CODE,
            description="Java typing frame 1",
            visible_code_text="public class Solution {\n    List<List<Integer>> res = new ArrayList<>();"
        )
    )

    ev2 = FusedEvidence(
        evidence_id="ev2",
        video_id="vid123",
        start_seconds=21.0,
        end_seconds=30.0,
        transcript_text="Java implementation complete",
        visual_observation=VisualObservation(
            frame_timestamp=25.0,
            content_type=VisualContentType.CODE,
            description="Java typing frame 2 complete",
            visible_code_text="public class Solution {\n    List<List<Integer>> res = new ArrayList<>();\n    public void dfs() {\n        System.out.println(res);\n    }\n}"
        )
    )

    snippets = code_reconstruction_service.reconstruct_code_artifacts([ev1, ev2])
    assert len(snippets) == 1
    java_snippet = snippets[0]
    assert java_snippet.language == "java"
    assert java_snippet.filename == "Solution.java"
    assert "public void dfs()" in java_snippet.code_content
    assert java_snippet.reconstruction_status == ObservationType.RECONSTRUCTED
    assert java_snippet.syntax_validity == SyntaxValidity.VERIFIED


def test_ast_syntax_validation():
    """Requirement: AST/Braces syntax validation without executing code."""
    valid_py = "def add(a, b):\n    return a + b"
    assert code_reconstruction_service.validate_code_syntax(valid_py, "python") == SyntaxValidity.VERIFIED

    incomplete_py = "def add(a, b):\n    return a +"
    assert code_reconstruction_service.validate_code_syntax(incomplete_py, "python") == SyntaxValidity.UNVERIFIED_FRAGMENT

    valid_java = "class Solution { public void run() {} }"
    assert code_reconstruction_service.validate_code_syntax(valid_java, "java") == SyntaxValidity.VERIFIED

    incomplete_java = "class Solution { public void run() {"
    assert code_reconstruction_service.validate_code_syntax(incomplete_java, "java") == SyntaxValidity.UNVERIFIED_FRAGMENT


def test_language_specific_file_naming_and_unique_suffixes():
    """Requirement: Generate language-appropriate filenames and unique suffixes for multiple snippets."""
    ev1 = FusedEvidence(
        evidence_id="ev1",
        video_id="vid123",
        start_seconds=10.0,
        end_seconds=20.0,
        transcript_text="First C++ implementation",
        visual_observation=VisualObservation(
            frame_timestamp=15.0,
            content_type=VisualContentType.CODE,
            description="C++ 1",
            visible_code_text="#include <vector>\nusing namespace std;\nint main() { return 0; }"
        )
    )

    ev2 = FusedEvidence(
        evidence_id="ev2",
        video_id="vid123",
        start_seconds=300.0, # >2 mins later
        end_seconds=310.0,
        transcript_text="Second C++ implementation",
        visual_observation=VisualObservation(
            frame_timestamp=305.0,
            content_type=VisualContentType.CODE,
            description="C++ 2",
            visible_code_text="#include <iostream>\nusing namespace std;\nint main() { cout << 123; }"
        )
    )

    snippets = code_reconstruction_service.reconstruct_code_artifacts([ev1, ev2])
    assert len(snippets) == 2
    filenames = [s.filename for s in snippets]
    assert "Solution.cpp" in filenames
    assert "Solution_2.cpp" in filenames
