// SDRE Typst macros (stable).

// Basic helpers
#let sdre_color(hex) = rgb(hex)

#let sdre_document(meta, theme, body) = {
  // Page shell
  set page(
    paper: if theme.page.size == "A4" { "a4" } else { "us-letter" },
    margin: (
      top: theme.page.margin_mm.top * 1mm,
      right: theme.page.margin_mm.right * 1mm,
      bottom: theme.page.margin_mm.bottom * 1mm,
      left: theme.page.margin_mm.left * 1mm,
    ),
  )

  // Text defaults
  set text(
    font: theme.fonts.base,
    size: if theme.text != none { theme.text.base_size_px * 1pt } else { 11pt },
    fill: sdre_color(theme.colors.text),
    lang: meta.language,
    dir: if meta.direction == "rtl" { rtl } else { ltr },
  )

  // Background (light touch)
  set page(fill: sdre_color(theme.colors.background))

  body
}

// Headings / structure
#let sdre_section(title) = heading(level: 1)[title]
#let sdre_subsection(title) = heading(level: 2)[title]

// Paragraph: accept content
#let sdre_paragraph(content) = content

// Central LTR inline macro (RTL docs still need LTR terms)
#let sdre_ltr(value, style: "plain", theme: none) = {
  let mono_font = if theme != none { theme.fonts.mono } else { none }
  if style == "mono" {
    if mono_font != none { text(font: mono_font, dir: ltr)[value] } else { text(dir: ltr)[value] }
  } else if style == "boxed" {
    box(
      inset: (x: 4pt, y: 2pt),
      stroke: 1pt + sdre_color(if theme != none { theme.colors.border } else { "#AAAAAA" }),
      radius: 2pt,
    )[text(dir: ltr)[value]]
  } else {
    text(dir: ltr)[value]
  }
}

// Inline code / math
#let sdre_inline_code(value, lang: none) = raw(value, lang: lang, block: false)
#let sdre_inline_math(value) = value

// Blocks: code/math
#let sdre_code_block(value, lang: none) = raw(value, lang: lang, block: true)
#let sdre_math_block(value) = value

// Horizontal rule / page break
#let sdre_horizontal_rule(theme: none) = line(
  length: 100%,
  stroke: 1pt + sdre_color(if theme != none { theme.colors.border } else { "#DDDDDD" })
)
#let sdre_page_break() = pagebreak()

// Notes / warnings
#let sdre_note(content, theme: none) = block(
  fill: sdre_color(if theme != none { theme.colors.code_bg } else { "#F6F8FA" }),
  inset: 8pt,
  radius: 3pt,
  stroke: 1pt + sdre_color(if theme != none { theme.colors.border } else { "#DDDDDD" }),
)[content]

#let sdre_warning(content, theme: none) = block(
  fill: luma(95%),
  inset: 8pt,
  radius: 3pt,
  stroke: 1pt + sdre_color(if theme != none { theme.colors.accent } else { "#CC5500" }),
)[content]

// Lists
#let sdre_bullet_list(items) = list(..items)
#let sdre_numbered_list(items) = enum(..items)

// Images
#let sdre_image(src, alt: none, caption: none) = {
  image(src, alt: alt)
  if caption != none { caption }
}

// Image placeholder: reserved box + optional label/caption.
#let sdre_image_placeholder(theme: none, reserve_height: none, aspect_ratio: none, border: true, label: none, caption: none) = {
  let h = if reserve_height != none { reserve_height } else { 50mm }
  let stroke_val = if border {
    1pt + sdre_color(if theme != none { theme.colors.border } else { "#DDDDDD" })
  } else { none }

  rect(
    width: 100%,
    height: h,
    stroke: stroke_val,
    radius: 3pt,
    inset: 8pt,
    fill: none,
  )[
    if label != none { strong(label) }
    if aspect_ratio != none { text(fill: sdre_color(theme.colors.muted))[ " (" + str(aspect_ratio) + ")" ] }
  ]

  if caption != none {
    caption
  }
}

// Tables: rows is an array of arrays of cell content blocks.
#let sdre_table(rows, caption: none) = {
  if caption != none { caption }

  let cols = rows.at(0).len()
  table(
    columns: cols,
    ..rows.flatten(),
  )
}
