# Noto Color Emoji

`assets/NotoColorEmoji.ttf` is the unmodified standard color font from
`googlefonts/noto-emoji` release **v2.051**, matching the Unicode 17 catalogue.

Source: https://github.com/googlefonts/noto-emoji/blob/v2.051/fonts/NotoColorEmoji.ttf

SHA-256: `72a635cb3d2f3524c51620cdde406b217204e8a6a06c6a096ff8ed4b5fd6e27b`

The SIL Open Font License is preserved in `NOTO_EMOJI_LICENSE.txt`.

The browser uses the standard CBDT/CBLC font. The Windows-compatible variant
adds empty outline tables; in the verified Windows Firefox rendering path that
variant left smileys invisible and parts of gesture sequences missing.
Handler keeps its separately bundled native Qt variant;
both fonts use the same Noto artwork. The browser regression checks actual
painted pixels as well as category, search, scrolling and insertion behavior.
