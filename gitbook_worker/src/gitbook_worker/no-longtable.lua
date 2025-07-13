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
