from typing import Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["P0", "P1", "P2"]


class Intent(BaseModel):
    """需求分析：判断用户这句话是新产品想法 / 修改现有 PRD / 闲聊无关。"""

    kind: Literal["new_product", "modify_prd", "chitchat"]
    reason: str = ""


class ResearchPlan(BaseModel):
    """规划节点的结构化输出：决定是否需要工具、调用哪些工具。"""

    need_web_search: bool = Field(description="是否需要联网做竞品/市场调研")
    web_queries: list[str] = Field(default_factory=list, description="竞品搜索关键词，1-4 条")
    need_knowledge: bool = Field(description="是否需要查询 PRD 方法论/行业知识库")
    knowledge_queries: list[str] = Field(default_factory=list, description="知识库查询关键词")
    plan_summary: str = Field(description="用一句话概括本次任务步骤（给人看，不是思维链）")


class Persona(BaseModel):
    name: str = Field(description="画像名称，如：一线运营人员")
    description: str = Field(description="一句话描述")
    needs: list[str] = Field(default_factory=list, description="核心诉求")


class Feature(BaseModel):
    name: str
    description: str
    priority: Priority = "P1"
    rationale: str = Field(default="", description="为什么做/依据")


class Competitor(BaseModel):
    name: str
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None


class Metric(BaseModel):
    name: str
    target: str = ""
    how_to_measure: str = ""


class Milestone(BaseModel):
    phase: str
    timeline: str = ""
    deliverables: list[str] = Field(default_factory=list)


class PRD(BaseModel):
    product_name: str
    one_liner: str = Field(default="", description="一句话产品定位")
    background: str = ""
    goals: list[str] = Field(default_factory=list)
    target_users: list[Persona] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class RevisionResult(BaseModel):
    """多轮修改的结构化输出：新 PRD + 变更说明（对齐 section 级 patch）。"""

    prd: PRD
    change_summary: str = Field(description="本次修改做了什么，1-3 句")
    changed_sections: list[str] = Field(
        default_factory=list,
        description="被修改的 PRD 字段名，如 features / metrics / milestones",
    )


class PRDEnvelope(BaseModel):
    """对外返回的 PRD 包裹：数据 + 版本元信息。"""

    version: int
    data: PRD
    change_summary: str = ""
    changed_sections: list[str] = Field(default_factory=list)
    created_at: str = ""
