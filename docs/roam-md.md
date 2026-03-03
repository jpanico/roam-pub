Here's the compiled list:

---

## Roam Markdown vs. CommonMark: Key Differences

### 1. Document Model
CommonMark is **document-oriented** — a flat sequence of block elements (paragraphs, headings, lists). Roam is **block-oriented** — every line is an atomic block node in an outliner tree. The fundamental unit is the indented bullet, not the page.

### 2. Italics — Breaking Difference
| | Syntax |
|---|---|
| CommonMark | `*italic*` or `_italic_` |
| Roam | `__double underscores__` only |

Roam's single underscore/asterisk does nothing. This is the most impactful incompatibility — copy-pasted content between Roam and other Markdown tools will silently mangle italic text.

### 3. Roam-Only Constructs (no CommonMark equivalent)

| Construct | Syntax | Purpose |
|---|---|---|
| Page links | `[[Page Name]]` | Wiki-style internal link |
| Nested page links | `[[nested [[pages]]]]` | Pages whose names contain brackets |
| Block references | `((block-uid))` | Inline reference to another block |
| Block embeds | `{{embed: ((block-uid))}}` | Transclude another block's content |
| Tags | `#tag` or `#[[multi-word tag]]` | Shorthand page link |
| Attributes | `Attribute Name::` | Key-value metadata on a block |
| Highlight | `^^highlighted text^^` | Background highlight |
| LaTeX (inline) | `$$latex$$` | Inline math (double-dollar inline, vs. CommonMark convention of `$...$`) |
| Roam components | `{{TODO}}`, `{{DONE}}`, `{{slider}}`, `{{query: ...}}`, `{{pdf: url}}`, `{{youtube: url}}`, `{{calc: expr}}` | Interactive widgets |
| Aliases to page links | `[display text]([[Page Name]])` | Labelled internal link |
| Aliases to block refs | `[display text]((block-uid))` | Labelled block reference |

### 4. TODO / Task Lists
CommonMark (and GFM) uses `- [ ] task` / `- [x] done`. Roam uses `{{[[TODO]]}}` and `{{[[DONE]]}}` as inline components within a block string — not list syntax at all. They are not interchangeable.

### 5. Strikethrough
Both Roam and GFM use `~~strikethrough~~`, but this is a GFM extension — it is **not** in CommonMark proper.

### 6. Headings
CommonMark headings are `# H1`, `## H2`, etc. Roam has no first-class heading syntax in the block string — headings are a **block-level property** (an integer `1–3` stored separately from the string). Some Roam exporters emit `#` prefixes, but that's an artifact of export, not native Roam syntax.

### 7. Automatic URL Linking
Roam auto-links bare URLs (`www.example.com`, `https://...`) inline. CommonMark does not — bare URLs require `<url>` angle-bracket syntax to be treated as links.

### 8. Unsupported CommonMark Constructs
Roam ignores or doesn't render several CommonMark features:
- Setext-style headings (`===` / `---` underlines)
- Reference-style links (`[text][ref]` + `[ref]: url`)
- HTML blocks and inline HTML
- Thematic breaks rendered as document structure (Roam may render `---` but it's not a structural separator in the outliner sense)

---

The net verdict: Roam's syntax is a **strict superset in extensions** (adds many constructs CommonMark lacks) but a **subset in standard support** (drops or alters several CommonMark conventions, most critically italics). It is not compatible with CommonMark parsers in either direction without transformation.

Sources:
- [roam-parser (LuisThiamNye)](https://github.com/LuisThiamNye/roam-parser)
- [Roam-Research/issues #340 — Roam should support standard Markdown](https://github.com/Roam-Research/issues/issues/340)
- [Roam-Research/issues #667 — Copy/paste TODO lists to/from markdown](https://github.com/Roam-Research/issues/issues/667)