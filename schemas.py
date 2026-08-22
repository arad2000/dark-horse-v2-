"""
Pydantic Schemas for Dark Horse V2
Request validation and response serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ============================================
# Micro Motive Schemas
# ============================================

class MicroMotiveBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="e.g., MED-001")
    description_fa: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    intensity_level: int = Field(default=1, ge=1, le=5)


class MicroMotiveCreate(MicroMotiveBase):
    pass


class MicroMotiveUpdate(BaseModel):
    description_fa: Optional[str] = None
    category: Optional[str] = None
    intensity_level: Optional[int] = None


class MicroMotiveResponse(MicroMotiveBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Value Pole Schemas
# ============================================

class ValuePoleBase(BaseModel):
    pole_code: str = Field(..., max_length=10, description="e.g., Q1A")
    question_num: int = Field(..., ge=1, le=15)
    option_letter: str = Field(..., regex="^[AB]$")
    description_fa: str = Field(..., max_length=300)


class ValuePoleCreate(ValuePoleBase):
    opposite_pole_id: Optional[int] = None


class ValuePoleResponse(ValuePoleBase):
    id: int
    opposite_pole_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Trait Option Schemas
# ============================================

class TraitOptionBase(BaseModel):
    question_code: str = Field(..., max_length=10, description="e.g., S01")
    option_index: int = Field(..., ge=0, le=4)
    traits: Optional[List[str]] = None
    description_fa: Optional[str] = None


class TraitOptionCreate(TraitOptionBase):
    pass


class TraitOptionResponse(TraitOptionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Major Schemas
# ============================================

class MajorBase(BaseModel):
    name: str = Field(..., max_length=200, description="e.g., پزشکی")
    group: str = Field(..., max_length=100)
    cluster: Optional[str] = Field(None, max_length=10)
    subgroup: Optional[str] = Field(None, max_length=50)
    exam_group: Optional[str] = Field(None, max_length=50)
    high_school_branch: Optional[str] = None
    archetype: Optional[str] = Field(None, max_length=200)
    fulfillment_source: Optional[str] = None
    prestige_level: Optional[int] = Field(None, ge=1, le=5)
    handcrafted: bool = True
    motive_driven: bool = True
    weights_version: Optional[str] = None


class MajorCreate(MajorBase):
    strategy_weights: List[List[float]] = Field(..., description="25x5 matrix")
    value_weights: Dict[str, float] = Field(...)
    micro_motive_codes: Optional[List[str]] = []


class MajorUpdate(BaseModel):
    name: Optional[str] = None
    group: Optional[str] = None
    archetype: Optional[str] = None
    fulfillment_source: Optional[str] = None
    prestige_level: Optional[int] = None


class MajorResponse(MajorBase):
    id: int
    strategy_weights: List[List[float]]
    value_weights: Dict[str, float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MajorListResponse(BaseModel):
    id: int
    name: str
    group: str
    cluster: Optional[str]
    archetype: Optional[str]

    class Config:
        from_attributes = True


# ============================================
# School Branch Schemas
# ============================================

class SchoolBranchBase(BaseModel):
    name: str = Field(..., max_length=100, description="e.g., علوم تجربی")
    group: str = Field(..., max_length=50)
    m_score_denom_limit: int = Field(default=30, ge=1)
    weights_version: Optional[str] = None
    source_majors_count: Optional[int] = None


class SchoolBranchCreate(SchoolBranchBase):
    strategy_weights: List[List[float]] = Field(..., description="25x5 matrix")
    value_weights: Dict[str, float] = Field(...)
    micro_motive_codes: List[str] = Field(...)


class SchoolBranchResponse(SchoolBranchBase):
    id: int
    strategy_weights: List[List[float]]
    value_weights: Dict[str, float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# User Session Schemas
# ============================================

class UserSessionCreate(BaseModel):
    micro_motives: List[str] = Field(...)
    sjt_answers: Dict[str, str] = Field(..., description='{"sjt_1": "A", ...}')
    conjoint_choices: Dict[str, str] = Field(..., description='{"conj_1": "Q1A", ...}')
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    language_preference: str = "fa"


class UserSessionResponse(BaseModel):
    id: int
    session_uuid: str
    micro_motives: List[str]
    sjt_answers: Dict[str, str]
    conjoint_choices: Dict[str, str]
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Discovery Result Schemas
# ============================================

class DiscoveryResultResponse(BaseModel):
    id: int
    major_id: int
    major_name: Optional[str] = None
    m_score: float
    s_score: float
    v_score: float
    total_score: float
    fit_level: Optional[str]
    matched_motives: Optional[List[Dict[str, str]]]
    strategy_highlights: Optional[List[str]]
    personalized_description: Optional[str]
    archetype_info: Optional[Dict[str, Any]]
    alternative_paths: Optional[List[Dict[str, Any]]]
    rank: Optional[int]

    class Config:
        from_attributes = True


# ============================================
# Branch Recommendation Schemas
# ============================================

class BranchRecommendationResponse(BaseModel):
    id: int
    branch_id: int
    branch_name: Optional[str] = None
    m_score: float
    s_score: float
    v_score: float
    average_score: float
    matched_motives: Optional[List[Dict[str, str]]]
    evidence: Optional[Dict[str, Any]]
    warning: Optional[str]
    alternative_paths: Optional[List[Dict[str, Any]]]
    rank: Optional[int]

    class Config:
        from_attributes = True


# ============================================
# User Feedback Schemas
# ============================================

class UserFeedbackCreate(BaseModel):
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5)
    accuracy_rating: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    recommended_major_id: Optional[int] = None
    would_recommend: Optional[bool] = None
    contact_for_research: bool = False
    email: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class UserFeedbackResponse(BaseModel):
    id: int
    session_id: int
    satisfaction_score: Optional[int]
    accuracy_rating: Optional[int]
    comments: Optional[str]
    would_recommend: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Discovery & Branch Discovery API Schemas
# ============================================

class DiscoveryRequest(BaseModel):
    micro_motives: List[str] = Field(..., min_items=1, description="List of selected micro motive codes")
    sjt_answers: Dict[str, str] = Field(..., description='SJT answers: {"sjt_1": "A", ...}')
    conjoint_choices: Dict[str, str] = Field(..., description='Value choices: {"conj_1": "Q1A", ...}')


class DiscoveryResponse(BaseModel):
    session_id: str
    discovery_result: Dict[str, Any] = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BranchDiscoveryResponse(BaseModel):
    session_id: str
    branch_discovery_result: Dict[str, Any] = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Statistics & Analytics Schemas
# ============================================

class DiscoveryStatistics(BaseModel):
    total_sessions: int
    completed_sessions: int
    average_satisfaction: Optional[float]
    total_majors_analyzed: int
    top_recommended_majors: List[Dict[str, Any]]
    created_at: datetime


class SessionAnalytics(BaseModel):
    session_id: str
    total_results: int
    high_fit_count: int
    medium_fit_count: int
    low_fit_count: int
    user_feedback: Optional[Dict[str, Any]]
