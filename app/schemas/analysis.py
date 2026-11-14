from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.enums import Category

Explanation = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Team = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class AnalysisSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    suggested_priority: Literal["low", "medium", "high", "critical"]
    suggested_team: Team
    rationale: Explanation
    recommendation: Explanation


class AIAnalysis(AnalysisSuggestion):
    is_simulation: bool
