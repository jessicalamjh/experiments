from s2ag_parser.schemas import ParagraphSchema, SectionSchema, PaperSchema

def get_sections_flat(x: PaperSchema | SectionSchema) -> list[SectionSchema]:
    sections = []
    try:
        SectionSchema.model_validate(x)
        sections.append(x)
    except:
        pass

    for section in x.get("sections", []):
        sections += get_sections_flat(section)
    return sections

def get_paragraphs_flat(x: PaperSchema | SectionSchema) -> list[ParagraphSchema]:
    paragraphs = []
    for section in get_sections_flat(x):
        paragraphs += section["paragraphs"]
    return paragraphs
