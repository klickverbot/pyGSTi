import tableformat as _tf

class ReportTable(object):
    def __init__(self, colHeadings, formatters, customHeader=None):
        self._headings = colHeadings
        self._headingFormatters = formatters
        self._customHeadings = customHeader
        self._rows = []

        if self._headingFormatters is not None:
            self._columnNames = self._headings
        else: #headingFormatters is None => headings is dict w/formats
            self._columnNames = self._headings['py'] #use python heading


    def addrow(self, rowData, formatters):
        self._rows.append( (rowData, formatters) )

    def finish(self):
        pass #nothing to do currently

    def render(self, fmt, longtables=False, tableclass='pygstiTbl',
               scratchDir=None):


        if fmt == "latex":

            _tf.SCRATCHDIR = scratchDir #Dangerous global     
            table = "longtable" if longtables else "tabular"
            if self._customHeadings is not None \
                    and "latex" in self._customHeadings:
                latex = self._customHeadings['latex']
            else:
                if self._headingFormatters is not None:
                    colHeadings_formatted = \
                        _tf.formatList(self._headings,
                                       self._headingFormatters, "latex")
                else: #headingFormatters is None => headings is dict w/formats
                    colHeadings_formatted = self._headings['latex']
                
                latex  = "\\begin{%s}[l]{%s}\n\hline\n" % \
                    (table, "|c" * len(colHeadings_formatted) + "|")
                latex += "%s \\\\ \hline\n" % \
                    (" & ".join(colHeadings_formatted))

            for rowData,formatters in self._rows:
                formatted_rowData = _tf.formatList(rowData, formatters, "latex")
                if len(formatted_rowData) > 0:
                    latex += " & ".join(formatted_rowData) + " \\\\ \hline\n"

            latex += "\end{%s}\n" % table
            _tf.SCRATCHDIR = None #Dangerous global     
            return latex

    
        elif fmt == "html":

            _tf.SCRATCHDIR = scratchDir #Dangerous global     
            if self._customHeadings is not None \
                    and "html" in self._customHeadings:
                html = self._customHeadings['html']
            else:
                if self._headingFormatters is not None:
                    colHeadings_formatted = \
                        _tf.formatList(self._headings,
                                       self._headingFormatters, "html")
                else: #headingFormatters is None => headings is dict w/formats
                    colHeadings_formatted = self._headings['html']

                html  = "<table class=%s><thead>" % tableclass
                html += "<tr><th> %s </th></tr>" % \
                    (" </th><th> ".join(colHeadings_formatted))
                html += "</thead><tbody>"

            for rowData,formatters in self._rows:
                formatted_rowData = _tf.formatList(rowData, formatters, "html")
                if len(formatted_rowData) > 0:
                    html += "<tr><td>" + \
                        "</td><td>".join(formatted_rowData) + "</td></tr>\n"

            html += "</tbody></table>"
            _tf.SCRATCHDIR = None #Dangerous global     
            return html
            

        elif fmt == "py":
    
            if self._customHeadings is not None \
                    and "py" in self._customHeadings:
                raise ValueError("custom headers unsupported for python format")

            if self._headingFormatters is not None:
                colHeadings_formatted = \
                    _tf.formatList(self._headings,
                                   self._headingFormatters, "py")
            else: #headingFormatters is None => headings is dict w/formats
                colHeadings_formatted = self._headings['py']
    
            py = { 'column names': colHeadings_formatted,
                   'row data': [] }

            for rowData,formatters in self._rows:
                formatted_rowData = _tf.formatList(rowData, formatters, "py")
                if len(formatted_rowData) > 0:
                    py['row data'].append( formatted_rowData )

            return py

    
        elif fmt == "ppt":

            if self._customHeadings is not None \
                    and "ppt" in self._customHeadings:
                raise ValueError("custom headers unsupported for " +
                                 "powerpoint format")

            if self._headingFormatters is not None:
                colHeadings_formatted = \
                    _tf.formatList(self._headings,
                                   self._headingFormatters, "ppt")
            else: #headingFormatters is None => headings is dict w/formats
                colHeadings_formatted = self._headings['ppt']
    
            ppt = { 'column names': colHeadings_formatted,
                    'row data' : [] }

            for rowData,formatters in self._rows:
                formatted_rowData = _tf.formatList(rowData, formatters, "ppt")
                if len(formatted_rowData) > 0:
                    ppt['row data'].append( formatted_rowData )

            return ppt

        else:
            raise ValueError("Unknown format: %s" % fmt)
    

    def __str__(self):

        def strlen(x):
            return max([len(p) for p in str(x).split('\n')])
        def nlines(x):
            return len(str(x).split('\n'))
        def getline(x,i):
            lines = str(x).split('\n')
            return lines[i] if i < len(lines) else ""
        
        data = self.render('py')
        col_widths = [0]*len(self._columnNames)
        row_lines = [0]*len(self._rows)
        header_lines = 0

        for i,nm in enumerate(self._columnNames):
            col_widths[i] = max( strlen(nm), col_widths[i] )
            header_lines = max(header_lines, nlines(nm))
        for k,(d,f) in enumerate(self._rows):
            for i,el in enumerate(d):
                col_widths[i] = max( strlen(el), col_widths[i] )
                row_lines[k] = max(row_lines[k], nlines(el))

        row_separator = "|" + '-'*(sum([w+5 for w in col_widths])-1) + "|\n"
          # +5 for pipe & spaces, -1 b/c don't count first pipe

        s  = "*** ReportTable object ***\n"
        s += row_separator

        for k in range(header_lines):
            for i,nm in enumerate(self._columnNames):
                s += "|  %*s  " % (col_widths[i],getline(nm,k))
            s += "|\n"
        s += row_separator

        for rowIndex,(rowEls,rowFormatters) in enumerate(self._rows):
            for k in range(row_lines[rowIndex]):
                for i,el in enumerate(rowEls):
                    s += "|  %*s  " % (col_widths[i],getline(el,k))
                s += "|\n"
            s += row_separator
            
        s += "\n"
        s += "Access row and column data by indexing into this object\n"
        s += " as a dictionary using the column header followed by the\n"
        s += " value of the first element of each row, i.e.,\n"
        s += " tableObj[<column header>][<first row element>].\n"

        return s


    def __getitem__(self, key):
        """Indexes the first column rowdata"""
        for row_data,formatters in self._rows:
            if len(row_data) > 0 and row_data[0] == key:
                return { key:val for key,val in \
                             zip(self._columnNames,row_data) }
        raise KeyError("%s not found as a first-column value" % key)

    def __len__(self):
        return len(self._rows)

    def __contains__(self, key):
        return key in self.keys()

    def keys(self):
        """ 
        Return a list of the first element of each row, which can be
        used for indexing.
        """
        return [ d[0] for (d,f) in self._rows if len(d) > 0 ]

    def has_key(self, key):
        return key in self.keys()

    def row(self, key=None, index=None):
        if key is not None:
            if index is not None:
                raise ValueError("Cannot specify *both* key and index")
            for row_data,formatters in self._rows:
                if len(row_data) > 0 and row_data[0] == key:
                    return row_data
            raise KeyError("%s not found as a first-column value" % key)
        
        elif index is not None:
            if 0 <= index < len(self):
                return self._rows[index][0]
            else:
                raise ValueError("Index %d is out of bounds" % index)

        else:
            raise ValueError("Must specify either key or index")


    def col(self, key=None, index=None):
        if key is not None:
            if index is not None:
                raise ValueError("Cannot specify *both* key and index")
            if key in self._columnNames:
                iCol = self._columnNames.index(key)
                return [ d[iCol] for (d,f) in self._rows ] #if len(d)>iCol
            raise KeyError("%s is not a column name." % key)
        
        elif index is not None:
            if 0 <= index < len(self._columnNames):
                return [ d[index] for (d,f) in self._rows ] #if len(d)>iCol
            else:
                raise ValueError("Index %d is out of bounds" % index)

        else:
            raise ValueError("Must specify either key or index")


    @property
    def num_rows(self):
        return len(self._rows)
    
    @property
    def num_cols(self):
        return len(self._columnNames)

    @property
    def row_names(self):
        return self.keys()

    @property
    def col_names(self):
        return self._columnNames
        
    
