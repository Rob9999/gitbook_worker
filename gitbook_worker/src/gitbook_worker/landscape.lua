function Div(el)
  if FORMAT:match('latex') and el.classes:includes('landscape') then
    local cols = tonumber(el.attributes['cols']) or 0
    -- Schriftgröße wählen
    local size = ''
    if cols >= 13 then
      size = '\\tiny'
    elseif cols >= 10 then
      size = '\\scriptsize'
    elseif cols >= 7 then
      size = '\\footnotesize'
    end

    local blocks = {}

    -- Hilfsfunktion für die Spaltenspezifikation
    local function to_X_spec(spec)
      -- p{..}, m{..}, b{..} und >{..}lcr entfernen
      spec = spec:gsub('>[^{}]+%b{}[lcr]', 'X')
      spec = spec:gsub('[pmbx]%b{}', 'X')
      spec = spec:gsub('[lcr]', 'X')
      return spec
    end

    -- 1) Landscape-Umgebung
    table.insert(blocks, pandoc.RawBlock('latex', '\\begin{landscape}'))
    -- 2) Schmalere Ränder
    table.insert(blocks, pandoc.RawBlock('latex', '\\newgeometry{margin=1cm,landscape}'))

    if size ~= '' then
      table.insert(blocks, pandoc.RawBlock('latex', '\\begingroup' .. size))
    end

    local doc = pandoc.Pandoc(el.content)
    local latex = pandoc.write(doc, 'latex')

    -- longtable oder tabular durch ltablex ersetzen
    latex = latex:gsub('\\begin{longtable}(%b[])?%s*{([^}]+)}', function(opt, spec)
      opt = opt or ''
      return '\\begin{ltablex' .. opt .. '{\\linewidth}{' .. to_X_spec(spec) .. '}'
    end)
    latex = latex:gsub('\\begin{tabular}(%b[])?%s*{([^}]+)}', function(opt, spec)
      opt = opt or ''
      return '\\begin{ltablex' .. opt .. '{\\linewidth}{' .. to_X_spec(spec) .. '}'
    end)

    latex = latex:gsub('\\end{longtable}', '\\end{ltablex}')
    latex = latex:gsub('\\end{tabular}', '\\end{ltablex}')

    table.insert(blocks, pandoc.RawBlock('latex', latex))

    if size ~= '' then
      table.insert(blocks, pandoc.RawBlock('latex', '\\endgroup'))
    end

    -- 3) Ränder wiederherstellen
    table.insert(blocks, pandoc.RawBlock('latex', '\\restoregeometry'))
    -- 4) Landscape beenden
    table.insert(blocks, pandoc.RawBlock('latex', '\\end{landscape}'))

    return blocks
  end
  return nil
end

