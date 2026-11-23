# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Fill the 7.1 report template from docs/final-report.md.

    python3 docs/final-presentation/build_report.py

Each "## N." section of the markdown replaces the Nth "Click or tap here" field after the title,
so edit the markdown and rerun. Handles paragraphs, bullet and numbered lists, tables, code
blocks, ![images](path), "> " notes (highlighted), **bold** and `code`. Standard library only.
"""

import re
import struct
import zipfile
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = HERE / "Self-study Capstone Checkpoint Activity 7.1_Final Capstone Report Planning Template.docx"
SOURCE = HERE.parent / "final-report.md"
OUT = HERE / "FrontLine Final Capstone Report.docx"

FONT = "Open Sans"
MONO = "Consolas"
INDENT = 720  # template's list text indent, so answers line up under each prompt
TEXT_WIDTH = 11906 - 2 * 1080 - INDENT  # A4 minus template margins minus indent
BULLET_NUM, ABSTRACT_BULLET, ABSTRACT_DECIMAL = 90, 90, 91  # ids well clear of the template's


def run(text: str, bold=False, mono=False, size=22, highlight=False) -> str:
    font = MONO if mono else FONT
    props = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    props += "<w:b/>" if bold else '<w:b w:val="0"/>'  # explicit: table cells otherwise inherit bold
    props += '<w:highlight w:val="yellow"/>' if highlight else ""
    props += f'<w:color w:val="000000"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text, quote=False)}</w:t></w:r>'


def inline(text: str, size=22, highlight=False, bold=False) -> str:
    """**bold** and `code` spans to runs."""
    out = []
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(inline(part[2:-2], size, highlight, bold=True))
        elif part.startswith("`"):
            out.append(run(part[1:-1], bold, mono=True, size=size - 2, highlight=highlight))
        else:
            out.append(run(part, bold, size=size, highlight=highlight))
    return "".join(out)


def para(runs: str, ind=INDENT, before=0, after=120, num: int | None = None, keep_next=False, shade=None) -> str:
    # Child order is fixed by the schema: pStyle, keepNext, numPr, shd, spacing, ind
    ppr = '<w:pStyle w:val="NormalWeb"/>'
    ppr += "<w:keepNext/>" if keep_next else ""
    if num is not None:
        ppr += f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num}"/></w:numPr>'
    if shade:
        ppr += f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>'
    ppr += f'<w:spacing w:before="{before}" w:beforeAutospacing="0" w:after="{after}" w:afterAutospacing="0"/>'
    ppr += f'<w:ind w:left="{ind + (360 if num is not None else 0)}"' + (' w:hanging="360"/>' if num is not None else "/>")
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def table(rows: list[list[str]]) -> str:
    ncol = len(rows[0])
    # Column widths follow the longest cell in each column, with a floor so short columns stay readable
    lens = [max(min(len(r[c]), 90) for r in rows) + 8 for c in range(ncol)]
    # ...but never narrower than the longest single word, so headers like "Games" don't break mid-word
    lens = [max(l, 2 * max(len(w) for r in rows for w in r[c].replace('**', '').split() or ['']) + 4)
            for c, l in enumerate(lens)]
    widths = [int(TEXT_WIDTH * l / sum(lens)) for l in lens]
    widths[-1] += TEXT_WIDTH - sum(widths)
    border = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
                     for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_WIDTH}" w:type="dxa"/><w:tblInd w:w="{INDENT}" w:type="dxa"/>'
           f'<w:tblBorders>{border}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
           f'<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>',
           "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"]
    for i, r in enumerate(rows):
        head = i == 0
        trpr = "<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>" if head else "<w:trPr><w:cantSplit/></w:trPr>"
        cells = []
        for w, text in zip(widths, r):
            shd = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if head else ""
            body = inline(text, size=18, bold=head)
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}</w:tcPr>'
                         f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{body}</w:p></w:tc>')
        out.append(f"<w:tr>{trpr}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    # A spacer paragraph so the next block doesn't touch the table
    return "".join(out) + para("", after=60)


def image(path: Path, alt: str, images: list[tuple[str, str, bytes]]) -> str:
    """An inline picture as wide as the text column. Records (rel id, media name, bytes) in `images`."""
    data = path.read_bytes()
    w_px, h_px = struct.unpack(">II", data[16:24])  # PNG IHDR
    cx = TEXT_WIDTH * 635  # DXA to EMU
    cy = cx * h_px // w_px
    n = len(images) + 1
    rid, name = f"rId{900 + n}", f"report-{n}.png"
    images.append((rid, name, data))
    pid = 9000 + n
    drawing = (
        f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{pid}" name="Picture {n}" descr="{escape(alt)}"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{pid}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        "</wp:inline></w:drawing>")
    return para(f"<w:r>{drawing}</w:r>", before=60, after=120)


def blocks(md: str, numbering: list[str], images: list[tuple[str, str, bytes]]) -> str:
    """Markdown section body to WordprocessingML. Appends a <w:num> per numbered list to `numbering`
    and each picture to `images`."""
    lines, out, i = md.strip("\n").split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif m := re.match(r"!\[(.*)\]\((.+)\)$", line.strip()):
            out.append(image(SOURCE.parent / m.group(2), m.group(1), images))
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            code = lines[i + 1:j]
            for k, c in enumerate(code):
                out.append(para(run(c, mono=True, size=15) if c else "", before=60 if k == 0 else 0,
                                after=60 if k == len(code) - 1 else 0, keep_next=k < len(code) - 1, shade="F7F7F7"))
            i = j + 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(table(rows))
        elif line.startswith("> "):
            out.append(para(inline(line[2:].strip(), highlight=True)))
            i += 1
        elif line.startswith("- "):
            while i < len(lines) and lines[i].startswith("- "):
                out.append(para(inline(lines[i][2:]), num=BULLET_NUM, after=60))
                i += 1
            out[-1] = out[-1].replace('w:after="60"', 'w:after="120"', 1)
        elif re.match(r"\d+\. ", line):
            num = BULLET_NUM + 1 + len(numbering)
            numbering.append(f'<w:num w:numId="{num}"><w:abstractNumId w:val="{ABSTRACT_DECIMAL}"/>'
                             f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>')
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                out.append(para(inline(lines[i].split(". ", 1)[1]), num=num, after=60))
                i += 1
            out[-1] = out[-1].replace('w:after="60"', 'w:after="120"', 1)
        else:
            text = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(```|\||> |- |\d+\. )", lines[i]):
                text.append(lines[i].strip())
                i += 1
            out.append(para(inline(" ".join(text))))
    return "".join(out)


def abstract_nums() -> str:
    lvl = '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/><w:lvlText w:val="{txt}"/>' \
          '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{ind}" w:hanging="360"/></w:pPr>{rpr}</w:lvl>'
    bullet = lvl.format(fmt="bullet", txt="•", ind=INDENT + 360,
                        rpr='<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>')
    bullet = bullet.replace("•", "")
    decimal = lvl.format(fmt="decimal", txt="%1.", ind=INDENT + 360, rpr="")
    return (f'<w:abstractNum w:abstractNumId="{ABSTRACT_BULLET}"><w:multiLevelType w:val="singleLevel"/>{bullet}'
            f'</w:abstractNum><w:abstractNum w:abstractNumId="{ABSTRACT_DECIMAL}">'
            f'<w:multiLevelType w:val="singleLevel"/>{decimal}</w:abstractNum>')


def main():
    md = SOURCE.read_text()
    title = re.search(r"^# (.+)$", md, re.M).group(1)
    byline = md.split("\n## ")[0].split("\n", 1)[1].strip().split("\n")[0]
    sections = re.split(r"^## \d+\. .*$", md, flags=re.M)[1:]

    with zipfile.ZipFile(TEMPLATE) as z:
        files = {n: z.read(n) for n in z.namelist()}
    doc = files["word/document.xml"].decode()
    numbering_xml = files["word/numbering.xml"].decode()

    sdts = list(re.finditer(r"<w:sdt>.*?</w:sdt>", doc, re.S))
    if len(sdts) != len(sections) + 1:
        raise SystemExit(f"template has {len(sdts)} fields, markdown has {len(sections)} sections + title")

    nums: list[str] = []
    images: list[tuple[str, str, bytes]] = []
    bodies = [para(inline(title, size=28, bold=True), before=120, after=60) + para(inline(byline), after=120)]
    bodies += [blocks(s, nums, images) for s in sections]

    # Work from the last field back so earlier offsets stay valid
    for m, body in reversed(list(zip(sdts, bodies))):
        if "<w:p " in m.group(0) or "<w:p>" in m.group(0):  # block-level field (the title): swap it out whole
            doc = doc[:m.start()] + body + doc[m.end():]
            continue
        # Inline field at the end of a prompt paragraph: drop it and the two line breaks before it,
        # then put the answer after that paragraph
        end = doc.index("</w:p>", m.end()) + len("</w:p>")
        head = re.sub(r"(?:<w:r(?: [^>]*)?>(?:<w:rPr>(?:(?!</w:rPr>).)*</w:rPr>)?<w:br/></w:r>)+$", "",
                      doc[:m.start()], flags=re.S)
        doc = head + doc[m.end():end] + body + doc[end:]

    numbering_xml = re.sub(r"(<w:abstractNum )", abstract_nums() + r"\1", numbering_xml, count=1)
    numbering_xml = numbering_xml.replace("</w:numbering>", f'<w:num w:numId="{BULLET_NUM}"><w:abstractNumId '
                                          f'w:val="{ABSTRACT_BULLET}"/></w:num>' + "".join(nums) + "</w:numbering>")
    files["word/document.xml"] = doc.encode()
    files["word/numbering.xml"] = numbering_xml.encode()
    rels = files["word/_rels/document.xml.rels"].decode()
    for rid, name, data in images:  # png is already a registered content type in the template
        files[f"word/media/{name}"] = data
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                            f'officeDocument/2006/relationships/image" Target="media/{name}"/></Relationships>')
    files["word/_rels/document.xml.rels"] = rels.encode()

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            if not name.endswith("/"):
                z.writestr(name, data)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
