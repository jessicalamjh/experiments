import glob
import json
from multiprocessing import Pool
from tqdm import tqdm

from s2ag.s2ag_parser.schemas import Paper
from s2ag.s2ag_parser.s2orc_parser import build_paper

def process(line: str):
    try:
        raw_paper = json.loads(line)
        paper = build_paper(raw_paper)
        Paper.model_validate(paper)
        return paper
    except:
        print(f"Something went wrong with processing corpusid={raw_paper["corpusid"]}")
        return None

if __name__ == "__main__":
    filepaths = sorted(list(glob.glob("data/raw/s2orc/*")))
    print(f"Total number of filepaths: {len(filepaths)}")

    out_path = "data/extracted/papers.jsonl"
    with open(out_path, "w") as f_out:
        for i, filepath in enumerate(filepaths):
            print(f"Filepath {i}: {filepath}")
            with open(filepath, "r") as f, Pool(10) as p:
                for paper in p.imap(process, tqdm(f.readlines())):
                    if paper is not None:
                        print(json.dumps(paper), file=f_out)