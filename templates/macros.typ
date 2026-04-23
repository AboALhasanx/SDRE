// SDRE Typst macros (stable).

// --------------------------------------
// Basic helpers
// --------------------------------------
#let sdre_color(hex) = rgb(hex)

#let sdre_text_size(theme) = if theme != none and theme.text != none {
  theme.text.base_size_px * 1pt
} else {
  11pt
}

#let sdre_border_color(theme) = sdre_color(
  if theme != none { theme.colors.border } else { "#DDDDDD" }
)

#let sdre_muted_color(theme) = sdre_color(
  if theme != none { theme.colors.muted } else { "#666666" }
)

#let sdre_accent_color(theme) = sdre_color(
  if theme != none { theme.colors.accent } else { "#0B5FFF" }
)

#let sdre_code_bg(theme) = sdre_color(
  if theme != none { theme.colors.code_bg } else { "#F6F8FA" }
)

#let sdre_base_font(theme) = if theme != none {
  theme.fonts.base
} else {
  "Arial"
}

#let sdre_mono_font(theme) = if theme != none and theme.fonts.mono != none {
  theme.fonts.mono
} else {
  "Courier New"
}

// --------------------------------------
// Document shell
// --------------------------------------
#let sdre_document(meta, theme, body) = {
  set page(
    paper: if theme.page.size == "A4" { "a4" } else { "us-letter" },
    margin: (
      top: theme.page.margin_mm.top * 1mm,
      right: theme.page.margin_mm.right * 1mm,
      bottom: theme.page.margin_mm.bottom * 1mm,
      left: theme.page.margin_mm.left * 1mm,
    ),
    fill: sdre_color(theme.colors.background),
  )

  set text(
    font: sdre_base_font(theme),
    size: sdre_text_size(theme),
    fill: sdre_color(theme.colors.text),
    lang: meta.language,
    dir: if meta.direction == "rtl" { rtl } else { ltr },
  )

  body
}

// --------------------------------------
// Headings / structure
// --------------------------------------
#let sdre_section(title) = heading(level: 1)[#title]
#let sdre_subsection(title) = heading(level: 2)[#title]

// --------------------------------------
// Paragraph
// --------------------------------------
#let sdre_paragraph(content) = content

// --------------------------------------
// Inline RTL/LTR helpers
// --------------------------------------
#let sdre_ltr(value, style: "plain", theme: none) = {
  let mono_font = sdre_mono_font(theme)

  if style == "mono" {
    text(font: mono_font, dir: ltr)[#value]
  } else if style == "boxed" {
    box(
      inset: (x: 4pt, y: 2pt),
      stroke: 1pt + sdre_border_color(theme),
      radius: 2pt,
      fill: none,
    )[
      #text(dir: ltr)[#value]
    ]
  } else {
    text(dir: ltr)[#value]
  }
}

// --------------------------------------
// Inline code / math
// --------------------------------------
#let sdre_inline_code(value, lang: none, theme: none) = box(
  inset: (x: 4pt, y: 2pt),
  radius: 2pt,
  fill: sdre_code_bg(theme),
  stroke: 0.6pt + sdre_border_color(theme),
)[
  #text(font: sdre_mono_font(theme), dir: ltr)[#value]
]

#let sdre_inline_math(value) = value

// --------------------------------------
// Code block
// --------------------------------------
#let sdre_code_block(value, lang: none, theme: none) = {
  let lines = value.split("\n")
  let mono = sdre_mono_font(theme)

  block(spacing: 0.45em)[
    #box(
      width: 100%,
      inset: 10pt,
      radius: 4pt,
      fill: sdre_code_bg(theme),
      stroke: 1pt + sdre_border_color(theme),
    )[
      #align(left)[
        #set text(font: mono, dir: ltr)
        #set par(justify: false)

        #if lang != none [
          #text(size: 9pt, fill: sdre_muted_color(theme), dir: ltr)[#lang]
          #v(6pt)
        ]

        #for line in lines [
          #text(dir: ltr)[#line]
          #linebreak()
        ]
      ]
    ]
  ]
}

// --------------------------------------
// Math block
// --------------------------------------
#let sdre_math_block(value) = value

// --------------------------------------
// Horizontal rule / page break
// --------------------------------------
#let sdre_horizontal_rule(theme: none) = line(
  length: 100%,
  stroke: 1pt + sdre_border_color(theme),
)

#let sdre_page_break() = pagebreak()

// --------------------------------------
// Notes / warnings
// --------------------------------------
#let sdre_note(content, theme: none) = block(
  fill: sdre_code_bg(theme),
  inset: 8pt,
  radius: 3pt,
  stroke: 1pt + sdre_border_color(theme),
)[#content]

#let sdre_warning(content, theme: none) = block(
  fill: luma(95%),
  inset: 8pt,
  radius: 3pt,
  stroke: 1pt + sdre_accent_color(theme),
)[#content]

// --------------------------------------
// Lists
// --------------------------------------
#let sdre_bullet_list(items) = list(..items)
#let sdre_numbered_list(items) = enum(..items)

// --------------------------------------
// Images
// --------------------------------------
#let sdre_image(src, alt: none, caption: none) = block(spacing: 0.35em)[
  #image(src, alt: alt)
  #if caption != none [
    #caption
  ]
]

// --------------------------------------
// Image placeholder
// --------------------------------------
#let sdre_image_placeholder(
  theme: none,
  reserve_height: none,
  aspect_ratio: none,
  border: true,
  label: none,
  caption: none,
) = {
  let h = if reserve_height != none { reserve_height } else { 50mm }
  let stroke_val = if border {
    1pt + sdre_border_color(theme)
  } else {
    none
  }

  block(spacing: 0.35em)[
    #rect(
      width: 100%,
      height: h,
      stroke: stroke_val,
      radius: 3pt,
      inset: 8pt,
      fill: none,
    )[
      #align(center + horizon)[
        #if label != none [
          #strong[#label]
          #v(4pt)
        ]
        #if aspect_ratio != none [
          #text(fill: sdre_muted_color(theme))[ratio: #aspect_ratio]
        ]
      ]
    ]

    #if caption != none [
      #caption
    ]
  ]
}

// --------------------------------------
// Tables
// --------------------------------------
#let sdre_table(rows, caption: none, theme: none) = {
  block(spacing: 0.35em)[
    #if caption != none [
      #caption
    ]

    #let cols = rows.at(0).len()

    #table(
      columns: cols,
      ..rows.flatten(),
    )
  ]
}