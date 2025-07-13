# gitbook-worker

To install the helper utilities run:

```bash
pip install .
```

You can then call `gitbook-worker` to process a GitBook repository.
The optional flag `--verbose` prints progress messages to the console. A log
file `gitbook_worker_<timestamp>.log` is always written to the output directory.
The log now records the full pandoc command with start and finish times and the
resulting exit code.

Wide tables can be automatically rotated into landscape pages with
`--wrap-wide-tables`. The number of columns considered "wide" can be adjusted
via `--table-threshold`. Both pipe tables and HTML `<table>` blocks are
detected. When this option is enabled, the font size of these tables is reduced
depending on their column count so that the content fits without overlapping.
When using this option, ensure the LaTeX packages `pdflscape` and `ltablex`
are installed.

## 1. Upgrade notes

Version 2.0.0 of the `gitbook-worker` package consolidates the helper scripts into
an installable module. The command line interface remains compatible, but you
should reinstall the package to get the latest improvements:

```bash
pip install -U gitbook-worker
```
Pandoc is now called with `-t latex`. Should you need to avoid the built-in
`longtable` environment, provide a custom LaTeX header and a Lua filter as
shown below.

## 2. Dokumentation erzeugen

Um die technische Dokumentation zu erstellen, wechseln Sie in das `docs/`-Verzeichnis und rufen Sie anschließend `make html` auf:

```bash
cd tools/gitbook_worker/docs
make html
```

Die fertige HTML-Dokumentation finden Sie danach unter `tools/gitbook_worker/docs/_build/html`.

### Emoji-Schriftarten und Fallback mit Segoe UI Emoji

Bei der PDF-Erzeugung kann Pandoc Warnungen zu fehlenden Zeichen ausgeben,
wenn die verwendete LaTeX-Schriftart keine Emoji-Glyphen enthält. Ab
Pandoc 3.1.12 lässt sich dafür die Variable `mainfontfallback` nutzen. Ein
Aufruf mit farbiger Emoji-Schrift sieht beispielsweise so aus:

```bash
pandoc input.md -o output.pdf --pdf-engine=lualatex \
  -V mainfont="DejaVu Serif" \
  -V mainfontfallback="Segoe UI Emoji:mode=harf"
```

Die Angabe `:mode=harf` aktiviert den HarfBuzz-Renderer und ermöglicht farbige
Emoji-Darstellung. Ältere Pandoc-Versionen unterstützen `mainfontfallback`
noch nicht. `gitbook_worker` erzeugt in diesem Fall eine LaTeX-Präambel mit
`luaotfload`, um Segoe UI Emoji automatisch als Fallback einzurichten. Nutzen
Sie dazu den Schalter `--emoji-color` und passen Sie bei Bedarf `--main-font`
an.

`gitbook_worker` erkennt dabei die installierte Pandoc-Version und setzt
`mainfontfallback` nur ein, wenn es bereits unterstützt wird. Bei älteren
Versionen fügt das Programm stattdessen eine kurze LuaTeX-Anweisung ein, damit
Segoe UI Emoji als Fallback dient. Im Docker-Workflow kommen weiterhin die
OpenMoji-Schriftarten des Containers zum Einsatz. Bei Verwendung von
`--wrap-wide-tables` wird zudem das mitgelieferte `landscape.lua`
eingebunden, um breite Tabellen korrekt zu drehen.

## 3. Beispiele: PDF-Erzeugung mit gitbook_worker

Hier einige typische Workflows, wie Sie mit `gitbook_worker` ein PDF erzeugen:

### 1. ERDA Buch als PDF erzeugen (ohne Docker)

```bash
gitbook-worker -v \
  --clone-dir C:/RAMProjects/ERDA/repo/gitbook_repo \
  --temp-dir C:/RAMProjects/ERDA/repo/temp \
  --out-dir C:/RAMProjects/ERDA/repo \
  https://github.com/Rob9999/erda-book.git \
  --branch release_candidate \
  --wrap-wide-tables \
  --emoji-color \
  --main-font "Noto Serif" \
  --pdf "C:/RAMProjects/ERDA/repo/Erda Buch"
```

### 2. ERDA Buch als PDF mit Docker erzeugen

Auf Windows-Systemen startet `gitbook_worker` Docker Desktop automatisch,
falls es noch nicht ausgeführt wird.

```bash
gitbook-worker -v \
  --clone-dir C:/RAMProjects/ERDA/repo/gitbook_repo \
  --temp-dir C:/RAMProjects/ERDA/repo/temp \
  --out-dir C:/RAMProjects/ERDA/repo \
  https://github.com/Rob9999/erda-book.git \
  --branch release_candidate \
  --wrap-wide-tables \
  --emoji-color \
  --main-font "Noto Serif" \
  --use-docker \
  --pdf "C:/RAMProjects/ERDA/repo/Erda Buch"
```

### 3. Nur Markdown zusammenfassen und Quellen exportieren

```bash
gitbook-worker -v \
  --clone-dir C:/RAMProjects/ERDA/repo/gitbook_repo \
  --temp-dir C:/RAMProjects/ERDA/repo/temp \
  --out-dir C:/RAMProjects/ERDA/repo \
  https://github.com/Rob9999/erda-book.git \
  --branch release_candidate \
  --export-sources
```

Weitere Optionen und Beispiele finden Sie mit:

```bash
gitbook-worker --help
```

### 4. Longtable-Ausgabe verhindern

Erstellen Sie eine Datei `pandoc_header.tex` mit folgenden Befehlen und binden
Sie zusätzlich den Lua-Filter `no-longtable.lua` ein. Alternativ genügt der
neue Schalter `--disable-longtable`:

```latex
% pandoc_header.tex
\let\oldlongtable\longtable
\let\oldendlongtable\endlongtable
\renewenvironment{longtable}[1]{%
  \begin{tabular}{#1}%
}{%
  \end{tabular}%
}
```

```lua
-- no-longtable.lua
return {
  {
    RawBlock = function(el)
      if el.format == 'latex' then
        el.text = el.text
          :gsub('\\begin{longtable}', '\\begin{tabular}')
          :gsub('\\end{longtable}', '\\end{tabular}')
      end
      return el
    end
  }
}
```

Ein Beispielaufruf von Pandoc:

```bash
pandoc combined.md -o output.pdf \
  -t latex --pdf-engine=lualatex --toc -V geometry=a4paper \
  -H pandoc_header.tex --lua-filter=no-longtable.lua
```

In `gitbook-worker` können Sie die Option `--disable-longtable` verwenden, um
dieses Verhalten automatisch zu aktivieren. Der Lua-Filter und der Header werden
intern eingebunden:

```bash
gitbook-worker ... \
  --disable-longtable \
  --pdf "out.pdf"
```

### 5. `--disable-longtable` mit `--wrap-wide-tables`

Wenn Sie `--wrap-wide-tables` einsetzen, erzeugt Pandoc trotz der Rotation
teilweise eine `longtable`-Umgebung. In Verbindung mit bestimmten
LaTeX-Konfigurationen kann dies zusammen mit `ltablex` und `pdflscape`
zu Abstürzen führen. Aktivieren Sie daher zusätzlich
`--disable-longtable`, um `longtable` in ein einfaches `tabular`
zu verwandeln und solche Probleme zu vermeiden.
