from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re


class ProjectStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATING_SOURCE = "VALIDATING_SOURCE"
    INGESTING_SOURCE = "INGESTING_SOURCE"
    PREPARING_TRANSCRIPT = "PREPARING_TRANSCRIPT"
    INGESTION_COMPLETED = "INGESTION_COMPLETED"
    SELECTING_RELEVANT_CONTENT = "SELECTING_RELEVANT_CONTENT"
    EXTRACTING_VISUAL_EVIDENCE = "EXTRACTING_VISUAL_EVIDENCE"
    FUSING_MULTIMODAL_EVIDENCE = "FUSING_MULTIMODAL_EVIDENCE"
    EVIDENCE_READY = "EVIDENCE_READY"
    REASONING_KNOWLEDGE = "REASONING_KNOWLEDGE"
    VALIDATING_KNOWLEDGE = "VALIDATING_KNOWLEDGE"
    KNOWLEDGE_READY = "KNOWLEDGE_READY"
    CROSS_VIDEO_SYNTHESIS = "CROSS_VIDEO_SYNTHESIS"
    DEDUPLICATION = "DEDUPLICATION"
    RELATIONSHIP_BUILDING = "RELATIONSHIP_BUILDING"
    KNOWLEDGE_GRAPH_READY = "KNOWLEDGE_GRAPH_READY"
    GENERATING_ARTIFACT = "GENERATING_ARTIFACT"
    VALIDATING_ARTIFACT = "VALIDATING_ARTIFACT"
    ARTIFACT_READY = "ARTIFACT_READY"
    ANALYZING_INTENT = "ANALYZING_INTENT"
    PROCESSING_VIDEO = "PROCESSING_VIDEO"
    EXTRACTING_KNOWLEDGE = "EXTRACTING_KNOWLEDGE"
    COMPLETED = "COMPLETED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"


class PlaylistJobStatus(str, Enum):
    PENDING = "PENDING"
    DISCOVERING = "DISCOVERING"
    DISCOVERED = "DISCOVERED"
    PROCESSING = "PROCESSING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VideoJobStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    INGESTING = "INGESTING"
    READY = "READY"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class TranscriptAvailability(str, Enum):
    TRANSCRIPT_AVAILABLE = "TRANSCRIPT_AVAILABLE"
    TRANSCRIPT_UNAVAILABLE = "TRANSCRIPT_UNAVAILABLE"
    FETCH_ERROR = "FETCH_ERROR"


class IntentCategory(str, Enum):
    CODE_EXTRACTION = "CODE_EXTRACTION"
    STUDY_NOTES = "STUDY_NOTES"
    FORMULA_SHEET = "FORMULA_SHEET"
    EXAM_REVISION = "EXAM_REVISION"
    INTERVIEW_PREP = "INTERVIEW_PREP"
    FLASHCARDS = "FLASHCARDS"
    CUSTOM = "CUSTOM"


class ContentType(str, Enum):
    CODE = "code"
    CONCEPTS = "concepts"
    EXAMPLES = "examples"
    FORMULAS = "formulas"
    TIME_COMPLEXITY = "time_complexity"
    SPACE_COMPLEXITY = "space_complexity"
    QUESTIONS_ANSWERS = "questions_answers"
    DEFINITIONS = "definitions"
    COMMANDS = "commands"
    TECHNOLOGIES = "technologies"
    TIMELINES = "timelines"
    COMPARISONS = "comparisons"


class ArtifactType(str, Enum):
    MARKDOWN_DOCUMENT = "MARKDOWN_DOCUMENT"
    CODE_FILES = "CODE_FILES"
    ZIP_PROJECT = "ZIP_PROJECT"
    PDF_DOCUMENT = "PDF_DOCUMENT"
    ANKI_CSV = "ANKI_CSV"
    JSON_KNOWLEDGE_BASE = "JSON_KNOWLEDGE_BASE"


class OrganizationStrategy(str, Enum):
    TOPIC_HIERARCHY = "TOPIC_HIERARCHY"
    CHRONOLOGICAL_TIMELINE = "CHRONOLOGICAL_TIMELINE"
    QUESTION_ANSWER_PAIRS = "QUESTION_ANSWER_PAIRS"
    FILE_TREE = "FILE_TREE"


class RelationshipType(str, Enum):
    SAME_AS = "SAME_AS"
    SUBTOPIC_OF = "SUBTOPIC_OF"
    VARIANT_OF = "VARIANT_OF"
    IMPLEMENTS = "IMPLEMENTS"
    RELATED_TO = "RELATED_TO"
    PREREQUISITE_OF = "PREREQUISITE_OF"
    CONTRASTS_WITH = "CONTRASTS_WITH"


class ExtractionPlan(BaseModel):
    intent_category: IntentCategory = IntentCategory.STUDY_NOTES
    content_types: List[ContentType] = Field(default_factory=lambda: [ContentType.CONCEPTS])
    target_artifact_types: List[ArtifactType] = Field(default_factory=lambda: [ArtifactType.MARKDOWN_DOCUMENT])
    organization_strategy: OrganizationStrategy = OrganizationStrategy.TOPIC_HIERARCHY
    custom_instructions: Optional[str] = "Create structured revision notes."
    human_readable_summary: str = "I'll extract key concepts and organize them into structured revision notes."


class IntentPlanRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language user request",
        examples=["Extract all Graph algorithms, code implementations, and complexity analysis."]
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Prompt must be at least 3 characters long.")
        return v


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    service: str = "VidMind API"
    environment: str
    gemini_key_1_status: str = "NOT CONFIGURED"
    gemini_key_2_status: str = "NOT CONFIGURED"
    active_key: str = "KEY_1"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectCreateRequest(BaseModel):
    source_url: str = Field(
        ...,
        description="Supported single video or playlist URL (e.g. YouTube)",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/playlist?list=PLgUwDviBIf0oF6QL8m22w1hIDC1vJ_BHz"]
    )
    user_prompt: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Freeform natural language prompt describing desired knowledge artifact",
        examples=["Extract all Graph algorithms, code, explanations, and time/space complexity."]
    )

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        
        supported_patterns = [
            r"youtube\.com/watch\?v=",
            r"youtube\.com/playlist\?list=",
            r"youtube\.com/watch\?.*list=",
            r"youtu\.be/",
            r"youtube\.com/embed/",
            r"youtube\.com/v/",
            r"localhost",
            r"127\.0\.0\.1"
        ]
        
        if not any(re.search(pat, v, re.IGNORECASE) for pat in supported_patterns):
            raise ValueError("Unsupported source domain or URL format. VidMind supports single video and playlist YouTube URLs.")

        return v

    @field_validator("user_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("User prompt must be at least 3 characters long.")
        return v


class PlaylistVideoItem(BaseModel):
    video_id: str
    source_url: str
    title: str
    position: int
    duration_seconds: int = 0
    status: VideoJobStatus = VideoJobStatus.PENDING
    error_message: Optional[str] = None


class PlaylistMetadataResponse(BaseModel):
    playlist_id: str
    source_url: str
    title: str
    uploader: Optional[str] = "Unknown Channel"
    total_videos: int
    videos: List[PlaylistVideoItem] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    project_id: str
    source_url: str
    user_prompt: str
    status: ProjectStatus
    is_playlist: bool = False
    playlist_id: Optional[str] = None
    playlist_metadata: Optional[PlaylistMetadataResponse] = None
    created_at: datetime
    updated_at: datetime
    extraction_plan: Optional[ExtractionPlan] = None
    artifact_summary: Optional[str] = None
    error_message: Optional[str] = None


class ErrorCategory(str, Enum):
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    TRANSCRIPT_UNAVAILABLE = "TRANSCRIPT_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    ENCODING_ERROR = "ENCODING_ERROR"
    AI_ERROR = "AI_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorDetail(BaseModel):
    code: ErrorCategory = ErrorCategory.UNKNOWN_ERROR
    message: str
    stage: Optional[str] = None
    retryable: bool = True
    technical_details: Optional[str] = None


class JobCreateResponse(BaseModel):
    job_id: str
    project_id: str
    status: ProjectStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    project_id: str
    status: ProjectStatus
    progress_percent: int = Field(ge=0, le=100)
    current_stage: str
    error_message: Optional[str] = None
    error_details: Optional[ErrorDetail] = None
    is_playlist: bool = False
    total_videos: int = 1
    completed_videos: int = 0
    failed_videos: int = 0
    current_video_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    details: Optional[Dict[str, Any]] = None


class SSEProgressEvent(BaseModel):
    job_id: str
    project_id: str
    status: ProjectStatus
    progress_percent: int
    current_stage: str
    message: str
    error_details: Optional[ErrorDetail] = None
    is_playlist: bool = False
    total_videos: int = 1
    completed_videos: int = 0
    failed_videos: int = 0
    current_video_title: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TranscriptSegment(BaseModel):
    text: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float


class VideoSourceMetadata(BaseModel):
    video_id: str
    source_url: str
    title: str
    duration_seconds: int
    channel: Optional[str] = "Unknown Channel"
    thumbnail_url: Optional[str] = None
    is_playlist: bool = False
    availability_status: str = "AVAILABLE"


class IngestionResultResponse(BaseModel):
    project_id: str
    video_metadata: VideoSourceMetadata
    transcript_status: TranscriptAvailability
    transcript_segments_count: int
    transcript_segments: List[TranscriptSegment] = Field(default_factory=list)
    ingestion_completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class VisualContentType(str, Enum):
    CODE = "CODE"
    TERMINAL = "TERMINAL"
    SLIDE = "SLIDE"
    DIAGRAM = "DIAGRAM"
    TABLE = "TABLE"
    BROWSER_DEMO = "BROWSER_DEMO"
    UI_INTERFACE = "UI_INTERFACE"
    TEXT_HEAVY = "TEXT_HEAVY"
    GENERAL = "GENERAL"


class ObservationType(str, Enum):
    DIRECTLY_OBSERVED = "DIRECTLY_OBSERVED"
    RECONSTRUCTED = "RECONSTRUCTED"
    AI_INFERRED = "AI_INFERRED"


class CodeRegion(BaseModel):
    region_id: str
    frame_timestamp: float
    language: str = "python"
    language_confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    code_text: str
    bounding_box: Optional[Dict[str, float]] = None
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED


class VisualObservation(BaseModel):
    frame_timestamp: float
    content_type: VisualContentType = VisualContentType.GENERAL
    description: str
    visible_code_text: Optional[str] = None
    confidence_score: float = Field(default=0.90, ge=0.0, le=1.0)
    detected_regions: List[CodeRegion] = Field(default_factory=list)


class FusedEvidence(BaseModel):
    evidence_id: str
    video_id: str
    start_seconds: float
    end_seconds: float
    transcript_text: str
    visual_observation: Optional[VisualObservation] = None
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED
    confidence_score: float = Field(default=0.92, ge=0.0, le=1.0)


class MultimodalFusionResponse(BaseModel):
    project_id: str
    total_evidence_count: int
    fused_evidence_list: List[FusedEvidence] = Field(default_factory=list)
    fusion_completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyntaxValidity(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED_FRAGMENT = "UNVERIFIED_FRAGMENT"
    SYNTAX_ERROR = "SYNTAX_ERROR"


class CodeSnippet(BaseModel):
    filename: Optional[str] = "main.py"
    language: str = "python"
    code_content: str
    start_seconds: float
    end_seconds: float
    reconstruction_status: ObservationType = ObservationType.DIRECTLY_OBSERVED
    syntax_validity: SyntaxValidity = SyntaxValidity.VERIFIED


class ComplexityAnalysis(BaseModel):
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    explanation: Optional[str] = None
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED


class EvidenceReference(BaseModel):
    evidence_id: str
    video_id: str
    start_seconds: float
    end_seconds: float
    video_position: int = 1
    playlist_id: Optional[str] = None
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED
    confidence_score: float = Field(default=0.90, ge=0.0, le=1.0)


class KnowledgeNode(BaseModel):
    node_id: str
    topic_title: str
    concept_summary: str
    key_examples: List[str] = Field(default_factory=list)
    formulas: List[str] = Field(default_factory=list)
    questions_and_answers: List[Dict[str, str]] = Field(default_factory=list)
    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    complexities: Optional[ComplexityAnalysis] = None
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED
    confidence_score: float = Field(default=0.93, ge=0.0, le=1.0)


class KnowledgeRelationship(BaseModel):
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: RelationshipType
    confidence_score: float = Field(default=0.90, ge=0.0, le=1.0)
    explanation: Optional[str] = None


class KnowledgeVariant(BaseModel):
    variant_id: str
    source_video_id: str
    video_position: int
    description: str
    complexity: Optional[ComplexityAnalysis] = None
    observation_type: ObservationType = ObservationType.DIRECTLY_OBSERVED


class IntermediateKnowledgeRepresentation(BaseModel):
    project_id: str
    title: str
    intent_category: IntentCategory
    topic_nodes: List[KnowledgeNode] = Field(default_factory=list)
    global_provenance: List[EvidenceReference] = Field(default_factory=list)
    reasoning_completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UnifiedPlaylistKnowledgeGraph(BaseModel):
    playlist_id: str
    project_id: str
    title: str
    intent_category: IntentCategory
    canonical_nodes: List[KnowledgeNode] = Field(default_factory=list)
    relationships: List[KnowledgeRelationship] = Field(default_factory=list)
    variants: List[KnowledgeVariant] = Field(default_factory=list)
    total_source_videos: int = 1
    synthesized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactMetadataResponse(BaseModel):
    artifact_id: str
    project_id: str
    filename: str
    artifact_type: ArtifactType
    file_size_bytes: int
    download_url: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectArtifactsListResponse(BaseModel):
    project_id: str
    total_artifacts: int
    artifacts: List[ArtifactMetadataResponse] = Field(default_factory=list)
    markdown_preview_content: Optional[str] = None


# Milestone 4 Personal Knowledge Library Schemas
class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["DSA"])
    description: Optional[str] = Field(default="", max_length=500)
    owner_id: Optional[str] = "default_user"


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CollectionResponse(BaseModel):
    collection_id: str
    name: str
    description: Optional[str] = ""
    owner_id: str = "default_user"
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class SaveToLibraryRequest(BaseModel):
    collection_id: str
    owner_id: Optional[str] = "default_user"


class KnowledgeItemResponse(BaseModel):
    item_id: str
    collection_id: str
    project_id: str
    title: str
    description: Optional[str] = ""
    owner_id: str = "default_user"
    is_playlist: bool = False
    source_url: str
    knowledge_snapshot: Dict[str, Any] = Field(default_factory=dict)
    artifact_references: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SaveToLibraryResponse(BaseModel):
    knowledge_item_id: str
    collection_id: str
    project_id: str
    status: str = "saved"
    message: str = "Project successfully saved to personal knowledge library."


# Milestone 5 Search & Retrieval Schemas
class SearchResultItem(BaseModel):
    knowledge_item_id: str
    title: str
    collection_id: str
    collection_name: str
    is_playlist: bool = False
    matched_topics: List[str] = Field(default_factory=list)
    matched_languages: List[str] = Field(default_factory=list)
    snippet: str
    highlighted_title: Optional[str] = None
    highlighted_snippet: Optional[str] = None
    score: float
    updated_at: datetime


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    has_next: bool = False
    results: List[SearchResultItem] = Field(default_factory=list)


# Milestone 6 Conversational Knowledge Chat Schemas
class CitationSource(BaseModel):
    source_id: str
    video_id: Optional[str] = None
    timestamp: Optional[str] = None
    title: str
    evidence_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    sources: List[CitationSource] = Field(default_factory=list)
    created_at: datetime


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None
    knowledge_item_id: Optional[str] = None
    collection_id: Optional[str] = None
    owner_id: Optional[str] = "default_user"


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    knowledge_item_id: Optional[str] = None
    collection_id: Optional[str] = None
    owner_id: str = "default_user"
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class PostMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Natural language user question")
    owner_id: Optional[str] = "default_user"


# Phase 5 Personal Knowledge Intelligence & AI Workspace Schemas
class MasteryLevel(str, Enum):
    UNKNOWN = "UNKNOWN"
    EXPOSED = "EXPOSED"
    FAMILIAR = "FAMILIAR"
    UNDERSTANDING = "UNDERSTANDING"
    PRACTICING = "PRACTICING"
    PROFICIENT = "PROFICIENT"
    MASTERED = "MASTERED"


class ConceptMasteryItem(BaseModel):
    concept_id: str
    topic_title: str
    mastery_level: MasteryLevel = MasteryLevel.EXPOSED
    confidence_score: float = Field(default=0.80, ge=0.0, le=1.0)
    evidence_count: int = 1
    last_reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeProfileResponse(BaseModel):
    owner_id: str = "default_user"
    total_saved_items: int = 0
    mastered_concepts_count: int = 0
    practicing_concepts_count: int = 0
    learning_history: List[Dict[str, Any]] = Field(default_factory=list)
    top_skills: List[str] = Field(default_factory=list)
    concept_mastery: List[ConceptMasteryItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeGapType(str, Enum):
    CONCEPT_GAP = "CONCEPT_GAP"
    PREREQUISITE_GAP = "PREREQUISITE_GAP"
    SKILL_GAP = "SKILL_GAP"
    PRACTICE_GAP = "PRACTICE_GAP"
    UNDERSTANDING_GAP = "UNDERSTANDING_GAP"
    REVISION_GAP = "REVISION_GAP"


class KnowledgeGapResponse(BaseModel):
    gap_id: str
    missing_concept: str
    related_known_concept: str
    gap_type: KnowledgeGapType = KnowledgeGapType.PREREQUISITE_GAP
    reason: str
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)


class LearningPathStep(BaseModel):
    step_number: int
    topic_title: str
    description: str
    status: str = "NOT_STARTED"  # NOT_STARTED | IN_PROGRESS | COMPLETED
    library_item_id: Optional[str] = None


class LearningPathResponse(BaseModel):
    path_id: str
    target_goal: str
    owner_id: str = "default_user"
    steps: List[LearningPathStep] = Field(default_factory=list)
    estimated_duration_minutes: int = 45
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TutorMode(str, Enum):
    EXPLAIN = "EXPLAIN"
    TEACH = "TEACH"
    QUIZ = "QUIZ"
    PRACTICE = "PRACTICE"
    HINT = "HINT"
    COMPARE = "COMPARE"
    DEBUG = "DEBUG"
    INTERVIEW = "INTERVIEW"
    EXAM_PREP = "EXAM_PREP"
    REVISION = "REVISION"


class TutorRequest(BaseModel):
    mode: TutorMode = TutorMode.TEACH
    question: str
    knowledge_item_id: Optional[str] = None
    user_answer: Optional[str] = None


class TutorResponse(BaseModel):
    session_id: str
    mode: TutorMode
    tutor_reply: str
    evaluation_status: Optional[str] = None  # CORRECT | PARTIALLY_CORRECT | INCORRECT
    adaptive_difficulty_level: int = 1
    citations: List[CitationSource] = Field(default_factory=list)


class RevisionItemResponse(BaseModel):
    item_id: str
    concept_title: str
    question: str
    suggested_answer: str
    status: str = "DUE"  # DUE | IN_PROGRESS | MASTERED
    due_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecommendationType(str, Enum):
    NEXT_TOPIC = "NEXT_TOPIC"
    REVISE = "REVISE"
    PRACTICE = "PRACTICE"
    DEEPEN = "DEEPEN"
    COMPARE = "COMPARE"
    FILL_GAP = "FILL_GAP"


class RecommendationItem(BaseModel):
    recommendation_id: str
    title: str
    reason: str
    type: RecommendationType = RecommendationType.NEXT_TOPIC
    target_topic: str


class PersonalWorkspaceDashboardResponse(BaseModel):
    owner_id: str = "default_user"
    active_goal: Optional[str] = "DSA Interview Preparation"
    overall_progress_percent: int = 65
    knowledge_profile: KnowledgeProfileResponse
    recent_gaps: List[KnowledgeGapResponse] = Field(default_factory=list)
    active_learning_path: Optional[LearningPathResponse] = None
    due_revisions_count: int = 3
    recommendations: List[RecommendationItem] = Field(default_factory=list)


# Phase 6 Advanced AI Agents & Autonomous Knowledge Workflows Schemas
class AgentTaskStatus(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentTaskType(str, Enum):
    ANALYZE_KNOWLEDGE = "ANALYZE_KNOWLEDGE"
    SEARCH_KNOWLEDGE = "SEARCH_KNOWLEDGE"
    COMPARE_SOURCES = "COMPARE_SOURCES"
    IDENTIFY_GAPS = "IDENTIFY_GAPS"
    CREATE_LEARNING_PATH = "CREATE_LEARNING_PATH"
    GENERATE_QUIZ = "GENERATE_QUIZ"
    EVALUATE_QUIZ = "EVALUATE_QUIZ"
    CREATE_REVISION = "CREATE_REVISION"
    GENERATE_NOTES = "GENERATE_NOTES"
    EXTRACT_CODE = "EXTRACT_CODE"
    CREATE_SUMMARY = "CREATE_SUMMARY"
    CREATE_STUDY_GUIDE = "CREATE_STUDY_GUIDE"
    CREATE_EXPORT = "CREATE_EXPORT"
    ANSWER_QUESTION = "ANSWER_QUESTION"


class AgentRole(str, Enum):
    ORCHESTRATOR = "ORCHESTRATOR"
    KNOWLEDGE_AGENT = "KNOWLEDGE_AGENT"
    RESEARCH_AGENT = "RESEARCH_AGENT"
    LEARNING_AGENT = "LEARNING_AGENT"
    PRACTICE_AGENT = "PRACTICE_AGENT"
    EVALUATE_AGENT = "EVALUATE_AGENT"
    CONTENT_AGENT = "CONTENT_AGENT"


class AgentTaskStep(BaseModel):
    task_id: str
    objective: str
    task_type: AgentTaskType
    agent_role: AgentRole = AgentRole.KNOWLEDGE_AGENT
    status: AgentTaskStatus = AgentTaskStatus.PLANNED
    dependencies: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None  # Action-level explainability ("Why did VidMind do this?")
    output_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentPlanResponse(BaseModel):
    plan_id: str
    high_level_goal: str
    owner_id: str = "default_user"
    autonomy_level: str = "ASSISTED"  # MANUAL | ASSISTED | AUTOMATIC
    overall_status: AgentTaskStatus = AgentTaskStatus.PLANNED
    tasks: List[AgentTaskStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentExecutionRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000, description="High-level natural language goal")
    autonomy_level: Optional[str] = "ASSISTED"  # MANUAL | ASSISTED | AUTOMATIC
    owner_id: Optional[str] = "default_user"


class AgentExecutionResponse(BaseModel):
    plan_id: str
    high_level_goal: str
    overall_status: AgentTaskStatus
    total_tasks: int
    completed_tasks: int
    execution_history: List[AgentTaskStep] = Field(default_factory=list)
    final_output_summary: Optional[str] = None
    budget_usage: Dict[str, Any] = Field(default_factory=lambda: {
        "gemini_calls": 2,
        "max_gemini_calls": 10,
        "tool_calls": 3,
        "execution_time_seconds": 1.2
    })


