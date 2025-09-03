import ast

from s2ag.s2ag_parser.schemas import AnnotationSchema, ParagraphSchema, SectionSchema, PaperSchema

NONSECTION_KEYS = [
    "title", "abstract",
    "publisher", "venue",
    "author", "authoraffiliation", "authorfirstname", "authorlastname",
    "bibauthor", "bibauthorfirstname", "bibauthorlastname", "bibentry", "bibtitle", "bibvenue",
    "figure", "figurecaption",
    "table",
]
REF_TYPES = ["bibref", "figureref", "tableref", "formula"]

def sanitize_annotations(annotations: dict[str, list[AnnotationSchema]], text_len: int) -> dict[str, list[AnnotationSchema]]:
    out = {}
    for key, _annotations in annotations.items():
        # ensure annotations is always a list
        if _annotations is None:
            out[key] = []
            continue
        
        out[key] = _annotations
        
        try:
            # literal eval all annotations for easier access later on
            _annotations_new = ast.literal_eval(_annotations)
            assert isinstance(_annotations_new, list)
            out[key] = _annotations_new
            
            if isinstance(_annotations_new, dict):
                    _annotations_new["start"] = int(_annotations_new["start"])
                    _annotations_new["end"] = int(_annotations_new["end"])
            elif isinstance(_annotations_new, list):
                for _ in _annotations_new:
                    _["start"], _["end"] = int(_["start"]), int(_["end"])
            out[key] = _annotations_new
        except:
            print(f"Unable to literal eval {key=} annotations")

        try:
            # deduplicate and keep valid annotations only, i.e. where 0 <= start < end <= len(text)
            # TODO: ensure author, bib information still matches up (so we don't acidentally put names together wrongly)
            _annotations_new = []
            seen_idxs = set()
            for ann in out[key]:
                idxs = (ann["start"], ann["end"])
                if idxs not in seen_idxs and 0 <= idxs[0] < idxs[1] <= text_len:
                    _annotations_new.append(ann)
                    seen_idxs.add(idxs)

            _annotations_new.sort(key=lambda _: _["start"])
            out[key] = _annotations_new
        except:
            print(f"Unable to deduplicate {key=} annotations")
        
        try:
            # merge overlapping annotations
            if len(out[key]) > 1:
                _annotations_new = [out[key][0]]
                for curr in out[key][1:]:
                    prev = _annotations_new[-1]
                    if curr["start"] < prev["end"]:
                        prev["end"] = max(prev["end"], curr["end"])
                        
                        for k, v in curr.get("attributes", {}).items():
                            if k not in prev:
                                prev[k] = v
                    else:
                        _annotations_new.append(curr)
                out[key] = _annotations_new
        except:
            print(f"Unable to merge overlapping {key=} annotations")

    return out

def build_referenced_items(paper: dict) -> dict[str, dict[str, AnnotationSchema]]:
    unref_count = 0

    # bibliography is easy
    bibliography = {}
    for ann in paper["annotations"]["bibentry"]:
        # determine reference id
        ref_id = ann.get("attributes", {}).get("id")
        if not ref_id:
            ref_id = f"unref_{unref_count}"
            unref_count += 1
            
        # in case of collision, prioritise whatever came first
        if ref_id not in bibliography:
            bibliography[ref_id] = {
                "ref_id": ref_id,
                "text": paper["text"][ann["start"]:ann["end"]],
                "start": ann["start"],
                "end": ann["end"],

                "corpusid": ann.get("attributes", {}).get("matched_paper_id"),
                "externalids": {
                    k:v for k,v in ann.get("attributes", {}).items() 
                    if k not in ["id", "matched_paper_id"]
                },
            }

    # formulas are also easy
    formulas = {}
    for ann in paper["annotations"]["formula"]:
        ref_id = ann.get("attributes", {}).get("id")
        if not ref_id:
            ref_id = f"unref_{unref_count}"
            unref_count += 1
            
        if ref_id not in formulas:
            formulas[ref_id] = {
                "ref_id": ref_id,
                "text": paper["text"][ann["start"]:ann["end"]],
                "start": ann["start"],
                "end": ann["end"],
            }

    # table annotations are actually also under figure annotations. ignore table annotations; they have less info!
    # TODO: figure spans currently include more text than the captions. explore whether this extra info is useful
    tables = {}
    figures = {}
    for ann in paper["annotations"]["figure"]:
        # ensure EVERYTHING has a ref_id, even if it was never referenced
        ref_id = ann.get("attributes", {}).get("id")
        if not ref_id: 
            ref_id = f"unref_{unref_count}"
            unref_count += 1

        temp = {
            "ref_id": ref_id,
            "text": paper["text"][ann["start"]:ann["end"]],
            "start": ann["start"],
            "end": ann["end"],
        }
        if ann.get("attributes", {}).get("type") == "table":
            if temp["ref_id"] not in tables:
                tables[temp["ref_id"]] = temp
        else:
            if temp["ref_id"] not in figures:
                figures[temp["ref_id"]] = temp

    return {
        "bibliography": bibliography, 
        "formulas": formulas, 
        "tables": tables, 
        "figures": figures,
    }

def build_paragraphs(paper: dict) -> list[ParagraphSchema]:
    # get list of references 
    refs = [
        {
            "ref_id": ann.get("attributes", {}).get("ref_id"),
            "ref_type": ref_type,
            "text": paper["text"][ann["start"]:ann["end"]],
            "start": ann["start"],
            "end": ann["end"],
        }
        for ref_type in REF_TYPES
        for ann in paper["annotations"][ref_type]
    ]
    refs.sort(key=lambda _: _["start"])

    # prepare list of paragraphs
    paragraphs = []
    for ann in paper["annotations"]["paragraph"]:
        paragraph = ann.copy()
        paragraph["text"] = paper["text"][ann["start"]:ann["end"]]

        # identify the bibliography, table, figure, formula references that belong to this paragraph
        paragraph["refs"] = []
        for ref in refs:
            if (paragraph["start"] <= ref["start"] and ref["end"] <= paragraph["end"]):
                ref["relative_start"] = ref["start"] - paragraph["start"]
                ref["relative_end"] = ref["end"] - paragraph["start"]
                
                paragraph["refs"].append(ref)

        paragraphs.append(paragraph)

    # deduplicate consecutive paragraphs
    if len(paragraphs) > 1:
        temp = [paragraphs[0]]
        for prev, curr in zip(paragraphs, paragraphs[1:]):
            if curr["text"].startswith(prev["text"]) or \
                (curr["text"] == prev["text"] and len(curr["refs"]) > len(prev["refs"])):
                temp[-1] = curr
            else:
                temp.append(curr)
        paragraphs = temp
        
    return paragraphs

def assign_paragraphs_to_sections(paper: dict, paragraphs: list[ParagraphSchema]) -> list[SectionSchema]:
    # get important annotations for determining sectioning
    sectionheader_annotations = paper["annotations"]["sectionheader"]

    # prepare list of sections based on sectionheaders
    sections = []
    for ann in sectionheader_annotations:
        temp = {
            "n": ann.get("attributes", {}).get("n", ""),
            "header": {
                "start": ann["start"],
                "end": ann["end"],
                "text": paper["text"][ann["start"]:ann["end"]],
            },
            "sections": [],
            "paragraphs": [],
        }

        # if previous section has exact same header text, ignore
        if not sections or temp["header"]["text"] != sections[-1]["header"]["text"]:
            sections.append(temp)

    # assign paragraphs to sections
    dummy_section = {
        "n": "",
        "header": None,
        "sections": [],
        "paragraphs": [],
    }
    for paragraph in paragraphs:
        # add paragraphs that end before first section header should to new dummy first section
        if not sections or paragraph["end"] < sections[0]["header"]["start"]:
            dummy_section["paragraphs"].append(paragraph)

        # add paragraph to most recent section
        else:
            parent_section = None
            for section in sections:
                if section["header"]["end"] < paragraph["start"]:
                    parent_section = section
                else:
                    break
            if parent_section:
                parent_section["paragraphs"].append(paragraph)
    
    # establish dummy section as new first section, if it has paragraphs
    if dummy_section["paragraphs"]:
        sections.insert(0, dummy_section)

    return sections

def remove_nonsection_sections(annotations, sections: list[SectionSchema]) -> list[SectionSchema]:
    # collect all "non-section" ranges
    nonsection_ranges = []
    for key in NONSECTION_KEYS:
        nonsection_ranges += annotations[key]
    nonsection_ranges.sort(key=lambda _: _["start"])

    # merge overlapping ranges for efficiency
    if len(nonsection_ranges) > 1:
        temp = [nonsection_ranges[0]]
        for current in nonsection_ranges[1:]:
            prev = temp[-1]
            if current["start"] <= prev["end"]:  # overlap or adjacency
                prev["end"] = max(prev["end"], current["end"])
            else:
                temp.append(current)
        nonsection_ranges = temp

    # filter out sections that overlap with any "non-section" range
    section_sections = []
    for section in sections:
        if section["header"]:
            start = section["header"]["start"]
        elif section["paragraphs"]:
            start = section["paragraphs"][0]["start"]
        else:
            raise
        
        if section["paragraphs"]:
            end = section["paragraphs"][-1]["end"]
        elif section["header"]:
            end = section["header"]["end"]
        else:
            raise
        
        if any(_["start"] < end and _["end"] > start for _ in nonsection_ranges):
            continue
        section_sections.append(section)

    return section_sections

def nest_sections(sections: list[SectionSchema]) -> list[SectionSchema]:
    nested_sections = []

    # reset section nesting
    for section in sections:
        section["sections"] = []

    # use section numbering 
    if any(section["n"] for section in sections):
        # keep track of current section nesting in stack
        stack = []
        for section in sections:

            try:
                current_n = [_ for _ in section["n"].split(".") if _]

                # pop from stack until we find a parent whose n is a prefix
                while stack:
                    parent_n = [_ for _ in stack[-1]["n"].split(".") if _]
                    if parent_n and current_n[:-1] == parent_n:
                        break
                    stack.pop()
            except:
                pass

            if stack:
                # current section is child of previous section in stack
                stack[-1]["sections"].append(section)
            else:
                # current section is new top-level section
                nested_sections.append(section)

            # add current section to stack
            stack.append(section)

    # FUTUREWORK: nest based on IMRAD heuristics instead # FUTUREWORK: use LLM to perform nesting instead
    else:
        nested_sections = sections
        
    return nested_sections

def build_title(paper: dict) -> AnnotationSchema:
    if paper["annotations"]["title"]:
        ann = paper["annotations"]["title"][0]
        return {
            "start": ann["start"],
            "end": ann["end"],
            "text": paper["text"][ann["start"]: ann["end"]],
    }
    else:
        return None

def build_abstract(paper: dict) -> AnnotationSchema:
    if paper["annotations"]["abstract"]:
        ann = paper["annotations"]["abstract"][0]
        return {
            "start": ann["start"],
            "end": ann["end"],
            "text": paper["text"][ann["start"]: ann["end"]],
    }
    else:
        return None

def build_paper(raw_paper: dict) -> PaperSchema:
    paper = {
        "corpusid": raw_paper["corpusid"],
        "externalids": raw_paper["externalids"],
        "text": raw_paper["content"]["text"],
        "annotations": raw_paper["content"]["annotations"],
    }
    if paper["text"] is None:
        paper["text"] = ""
    
    paper["annotations"] = sanitize_annotations(paper["annotations"], len(paper["text"]))

    for ref_type, referenced_items in build_referenced_items(paper).items():
        paper[ref_type] = referenced_items

    paragraphs = build_paragraphs(paper)
    sections = assign_paragraphs_to_sections(paper, paragraphs)
    sections = remove_nonsection_sections(paper["annotations"], sections)
    sections = nest_sections(sections)
    paper["sections"] = sections

    paper["abstract"] = build_abstract(paper)
    paper["title"] = build_title(paper)

    # save space
    del paper["text"], paper["annotations"]

    return paper