from __future__ import annotations
from pydantic import BaseModel, Field

class AnnotationSchema(BaseModel):
    start: int
    end: int
    text: str

    _config = {"extra": "allow"}

class ReferenceSchema(AnnotationSchema):
    ref_id: str | None
    ref_type: str
    relative_start: int
    relative_end: int

class ParagraphSchema(AnnotationSchema):
    refs: list[ReferenceSchema] = Field(default_factory=list)

class SectionSchema(BaseModel):
    n: str
    header: AnnotationSchema | None
    
    sections: list[SectionSchema] = Field(default_factory=list)
    paragraphs: list[ParagraphSchema] = Field(default_factory=list)

class PaperSchema(BaseModel):
    corpusid: int

    title: AnnotationSchema | None
    abstract: AnnotationSchema | None
    sections: list[SectionSchema] = Field(default_factory=list)

    bibliography: dict[str, AnnotationSchema] = Field(default_factory=list)
    figures: dict[str, AnnotationSchema] = Field(default_factory=list)
    tables: dict[str, AnnotationSchema] = Field(default_factory=list)
    formulas: dict[str, AnnotationSchema] = Field(default_factory=list)