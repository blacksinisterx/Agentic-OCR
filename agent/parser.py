"""
agent/parser.py
Converts raw Markdown (from LLaVA) into a typed content tree
that the document generators traverse precisely.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto


class BT(Enum):
    H1 = auto(); H2 = auto(); H3 = auto(); H4 = auto()
    PARA     = auto()
    BULLETS  = auto()
    NUMBERED = auto()
    EQUATION = auto()
    DIAGRAM  = auto()
    TABLE    = auto()
    QUOTE    = auto()
    DIVIDER  = auto()


@dataclass
class Seg:
    """Inline text segment."""
    text:    str
    bold:    bool = False
    italic:  bool = False
    is_eq:   bool = False
    is_code: bool = False


@dataclass
class Block:
    btype:    BT
    raw:      str
    segs:     list[Seg]    = field(default_factory=list)
    children: list["Block"] = field(default_factory=list)
    ordered:  bool = False


@dataclass
class ParsedDoc:
    title:  str
    blocks: list[Block]
    stats:  dict = field(default_factory=dict)


class ContentParser:

    def parse(self, md: str, title: str = "Extracted Notes") -> ParsedDoc:
        lines  = md.splitlines()
        blocks = self._blocks(lines)
        stats  = self._stats(blocks)
        return ParsedDoc(title=title, blocks=blocks, stats=stats)

    # ── block level ──────────────────────────────────────────
    def _blocks(self, lines: list[str]) -> list[Block]:
        out: list[Block] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            s    = line.strip()

            if not s:
                i += 1; continue

            # Headings
            if s.startswith("#"):
                lvl  = min(len(s) - len(s.lstrip("#")), 4)
                text = s.lstrip("#").strip()
                bt   = (BT.H1, BT.H2, BT.H3, BT.H4)[lvl - 1]
                out.append(Block(bt, text, self._inline(text)))
                i += 1; continue

            # Blockquote
            if s.startswith(">"):
                text = s.lstrip(">").strip()
                out.append(Block(BT.QUOTE, text, self._inline(text)))
                i += 1; continue

            # Diagram tag
            m = re.match(r'\[DIAGRAM:(.*?)\]', s)
            if m:
                out.append(Block(BT.DIAGRAM, m.group(1).strip()))
                i += 1; continue

            # Horizontal rule
            if re.match(r'^[-*_]{3,}$', s):
                out.append(Block(BT.DIVIDER, ""))
                i += 1; continue

            # Table (requires separator on next line)
            if "|" in s and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if re.match(r'\|[-| :]+\|', nxt):
                    rows = []
                    while i < len(lines) and "|" in lines[i]:
                        rows.append(lines[i]); i += 1
                    out.append(Block(BT.TABLE, "\n".join(rows)))
                    continue

            # Bullet list
            if re.match(r'^\s*[-•*]\s', line):
                items, i = self._list(lines, i, False)
                out.append(Block(BT.BULLETS, "", children=items))
                continue

            # Numbered list
            if re.match(r'^\s*\d+[.)]\s', line):
                items, i = self._list(lines, i, True)
                out.append(Block(BT.NUMBERED, "", children=items, ordered=True))
                continue

            # Block equation $$...$$
            if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
                out.append(Block(BT.EQUATION, s[2:-2].strip()))
                i += 1; continue

            # Plain paragraph
            out.append(Block(BT.PARA, s, self._inline(s)))
            i += 1

        return out

    def _list(self, lines, start, ordered):
        items = []
        i     = start
        pat   = r'^\s*\d+[.)]\s' if ordered else r'^\s*[-•*]\s'
        while i < len(lines) and lines[i].strip():
            if not re.match(pat, lines[i]):
                break
            text = re.sub(pat, "", lines[i]).strip()
            items.append(Block(BT.PARA, text, self._inline(text)))
            i += 1
        return items, i

    # ── inline level ─────────────────────────────────────────
    def _inline(self, text: str) -> list[Seg]:
        segs: list[Seg] = []
        for part in re.split(r'(\$[^$]+\$|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)', text):
            if not part:
                continue
            if part.startswith("$") and part.endswith("$") and len(part) > 2:
                segs.append(Seg(part[1:-1], is_eq=True))
            elif part.startswith("**") and part.endswith("**"):
                segs.append(Seg(part[2:-2], bold=True))
            elif part.startswith("*") and part.endswith("*"):
                segs.append(Seg(part[1:-1], italic=True))
            elif part.startswith("`") and part.endswith("`"):
                segs.append(Seg(part[1:-1], is_code=True))
            else:
                segs.append(Seg(part))
        return segs or [Seg(text)]

    # ── stats ─────────────────────────────────────────────────
    def _stats(self, blocks: list[Block]) -> dict:
        full = " ".join(b.raw for b in blocks)
        eqs  = sum(
            1 for b in blocks
            if b.btype == BT.EQUATION or any(s.is_eq for s in b.segs)
        )
        return {
            "words":    len(full.split()),
            "headings": sum(1 for b in blocks if b.btype in (BT.H1,BT.H2,BT.H3,BT.H4)),
            "equations": eqs,
            "diagrams": sum(1 for b in blocks if b.btype == BT.DIAGRAM),
            "lists":    sum(1 for b in blocks if b.btype in (BT.BULLETS, BT.NUMBERED)),
        }
