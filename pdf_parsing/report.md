## 2026-01-14

### Setup

I ran into significant trouble with creating a venv that would work with this model, even when I followed/varied on NVIDIA's instructions [here](https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-v1.1). The solution that ultimately worked was to use their custom Docker image *nvcr.io/nvidia/pytorch:25.03-py3*.

### Input

The model description is somewhat contradictory - on one hand, it claims [here](https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-v1.1#use-case) that it accepts PDFs as input, but on the other hand, PDF is not listed as an accepted input [here](https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-v1.1#input) and there are no code snippets to instruct the user on how to pass PDFs. 

A possible workaround is to use something like [pdf2image](https://pypi.org/project/pdf2image/) to programmatically convert each PDF into a list of images, probably with each image representing one page. I did not have the time to test this out, so for now, I took screenshots manually. 

### Output

The script `run.py` reads in each input file, generates an "intermediate" version of its textual content, then outputs a "final" version of the textual content according to the user's specifications. For this test, I output the intermediate representations and set the final versions to be markdown-compatible.

In the final markdown file, each new line roughly corresponds to a new "element" (e.g. text, section header, picture). Nested elements like pictures that contain text appear to be multi-line.

### Observations

#### Runtime

Each file took ~2s to run. However, the implementation for this quick test is not optimised at all (e.g., I did not do batch inference), so it's hard to tell whether this scales well for now. 

#### Case 1

Input: [Screenshot_20260114_143603.png](data/Screenshot_20260114_143603.png)

- Single column
- Two figures, each with textual labels and captions
- Section header
- Some text

Output: [Screenshot_20260114_143603.md](output/markdown/Screenshot_20260114_143603.md)

- Figure captions are correctly identified (instead of being assigned as e.g. text)
- Textual labels in figures are extracted as well. That might be annoying
- The two figures and two captions are ordered in a potentially troublesome manner in the output:
    - Content of first figure
    - Content of second figure
    - Caption of first figure
    - Caption of second figure
- Header and footer text are separated nicely

#### Case 2

Input: [Screenshot_20260114_150559.png](data/Screenshot_20260114_150559.png)

- Two columns
- Three tables
- Footnote
- Subsection, section headers
- Formulas
- Header and footer text are separated nicely

Output: [Screenshot_20260114_150559.md](output/markdown/Screenshot_20260114_150559.md)

- Tables look generally correct
    - Table 4 contains wrong data (99.2 instead of 59.2)
- Similar potential issue with table and caption ordering as in Case 1
- Footnote is correctly identified as footnote, but it'd be difficult to trace where the footnote was made
- Section 5 is correctly identified as being on a higher section level than Sections 4.3 and 4.4
- Formulas have some issues, but are good considering the screenshot resolution 
    - $s_\text{null} = S \cdot C + E \cdot C$ became _s_<sub>max11</sub>=_S-C+E-C_
    - $s_{\hat{i},j} = \max_{j \geq i} S \cdot T_i + E \cdot T_j$ became \(s_{i,j}=\text{max}_{j\ge 1}S-T_l+E-T_j\)

#### Case 3

Input: [Screenshot_20260114_182127.png](data/Screenshot_20260114_182127.png)

- Two columns
- One wide table
- One figure with four subfigures and long caption
- Section header

Output: [Screenshot_20260114_182127.md](output/markdown/Screenshot_20260114_182127.md)

- Table looks good
- Struggles with the subfigure labels
- In this output, the table appears before the figure, but the table caption appears after the figure caption
- Section and text look good
- Header and footer text are separated nicely

#### Case 4

Input: [Screenshot_20260114_182142.png](data/Screenshot_20260114_182142.png)

- Two columns
- Lots of citation markers
- Section and subsection headers

Output: [Screenshot_20260114_182142.md](output/markdown/Screenshot_20260114_182142.md)

- Header and footer text are separated nicely
- Section heading and text look good
    - "Subjects and song recordings" is not recognised as subsection of "Methods", but that might be forgiveable, given that the heading is inline with the text
- Many citation markers are extracted correctly (e.g., instead of as footnotes)
    - The marker text itself is sometimes wrong, but that may again be a resolution issue

#### Case 5

Input: [Screenshot_20260114_182151.png](data/Screenshot_20260114_182151.png)

- Similar to Case 4
- Formulas

Output: [Screenshot_20260114_182151.md](output/markdown/Screenshot_20260114_182151.md)

- Same "issue" with the subsections not being recognised as subsections
- Formulas look pretty nice

#### Case 6

Input: [Screenshot_20260114_182210.png](data/Screenshot_20260114_182210.png)

- Similar to Case 4
- Start of References

Output: [Screenshot_20260114_182210.md](output/Screenshot_20260114_182210.md)

- The work "Bibliography" is not in the input file, yet the output file correctly applies that category to each line in the References section. Nice!
- Multiline Reference entries wrongly get split over two lines, but that looks like an issue that can be easily solved with custom post processing.

