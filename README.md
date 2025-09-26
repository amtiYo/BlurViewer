<h1 align="center">FreshViewer</h1>

<p align="center">
  <a href="https://github.com/amtiYo/FreshViewer"><img alt="License" src="https://img.shields.io/github/license/amtiYo/FreshViewer?label=license"></a>
  <a href="https://github.com/amtiYo/FreshViewer/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/amtiYo/FreshViewer?display_name=tag&sort=semver"></a>
  <img alt="Conventional Commits" src="https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg">
</p>

A modern, distraction‑free image viewer for Windows built with .NET 8 and Avalonia. FreshViewer features a crisp Liquid Glass interface, smooth navigation, rich format support, and a handy info overlay — all optimized for everyday use.

## Highlights
- Liquid Glass UI: translucent cards, soft shadows, and subtle motion for a premium feel
- Smooth navigation: kinetic panning, focus‑aware zoom, rotate, and fit‑to‑view
- Info at a glance: compact summary card + detailed metadata panel (EXIF/XMP)
- Powerful formats: stills, animations, modern codecs, and DSLR RAW families
- Personalization: themes, language (ru/en/uk/de), and keyboard‑shortcut profiles

## Liquid Glass design
FreshViewer embraces a lightweight “Liquid Glass” aesthetic:
- Top app bar with rounded glass buttons (Back, Next, Fit, Rotate, Open, Info, Settings, Fullscreen)
- Left summary card (file name, resolution, position in folder)
- Slide‑in information panel (I) with fluid enter/exit animation
- Compact status pill at the bottom with action hints

The result is a calm, legible interface that stays out of the way while keeping essential controls at your fingertips.

## Supported formats
- Common: PNG, JPEG, BMP, TIFF, ICO, SVG
- Modern: WEBP, HEIC/HEIF, AVIF, JXL
- Pro: PSD, HDR, EXR
- DSLR RAW: CR2/CR3, NEF, ARW, DNG, RAF, ORF, RW2, PEF, SRW, MRW, X3F, DCR, KDC, ERF, MEF, MOS, PTX, R3D, FFF, IIQ
- Animation: GIF/APNG (with loop handling)

## Keyboard & mouse (default)
- Navigate: A/← and D/→
- Fit to view: Space / F
- Rotate: R / L
- Zoom: mouse wheel, + / −
- Info panel: I
- Settings: P
- Fullscreen: F11
- Copy current frame: Ctrl+C

## Requirements
- Windows 10 1809 or newer (x64)
- .NET 8 SDK

## Build & run
```bash
dotnet restore FreshViewer.sln
dotnet build FreshViewer.sln -c Release
dotnet run --project FreshViewer/FreshViewer.csproj -- <optional-image-path>
```

Publish (Windows x64, single file):
```bash
dotnet publish FreshViewer/FreshViewer.csproj -c Release -r win-x64 \
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true --self-contained=false
```

## Settings
- Themes: switch between pre‑tuned Liquid Glass palettes
- Language: ru / en / uk / de
- Shortcuts: select a profile (Standard, Photoshop, Lightroom) or export/import your own mapping (JSON)

## Contributing
Contributions are welcome. Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for a short guide.

## License
MIT — see [LICENSE](./LICENSE).

## Credits
Avalonia, SkiaSharp, ImageSharp, Magick.NET, and MetadataExtractor.
