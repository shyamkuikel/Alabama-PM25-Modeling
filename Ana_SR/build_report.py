"""Build the county ranking PDF from published_results (requires reportlab)."""
from pathlib import Path
import csv
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'published_results'
OUT = ROOT / 'output' / 'pdf' / 'county_pca_variable_rankings.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
meta = json.loads((RESULTS / 'run_summary.json').read_text())
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='SmallNote', fontSize=9, leading=13, textColor=colors.HexColor('#475569')))
styles['Title'].textColor = colors.HexColor('#16324f')
styles['Heading1'].textColor = colors.HexColor('#16324f')
styles['BodyText'].leading = 15
story = []
def p(text, style='BodyText'):
    return Paragraph(text, styles[style])
def table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#16324f')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),9),
        ('LEADING',(0,0),(-1,-1),12),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef3f7'),colors.white]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    return t

def rows_for(county):
    with (RESULTS / county / 'variable_ranking.csv').open() as f:
        return list(csv.DictReader(f))

story += [p('County-wise weather variable rankings','Title'),
          p('Alabama PM2.5 Study | Local workbook analysis','Heading2'),
          p('Ten county worksheets; 365 input records per county. Each county was analyzed independently using the existing Python PCA workflow.'),Spacer(1,12),
          p('Main findings','Heading2'),
          p('Dew point ranks first in eight counties. Precipitation ranks first in Jefferson, and wind speed ranks first in Sumter. Sumter precipitation is constant and is excluded from scaled PCA.'),
          p('Temperature and dew point exceed the absolute-correlation redundancy threshold of 0.90 in every county. No analyzed variable has retained communality below 0.50. These results do not justify declaring a weather variable irrelevant to PM2.5.'),Spacer(1,12)]
rows=[['County','First-ranked variable','Rows used','PCs','Variance']]
for c in meta['counties']:
    rows.append([c['county'], rows_for(c['county'])[0]['variable'], str(c['complete_rows']),str(c['retained_components']),f"{c['retained_variance']:.2%}"])
story += [table(rows,[95,155,75,50,65]),Spacer(1,12),
          p('How to read the rankings','Heading2'),
          p('Importance is the percentage share of retained PCA variance contributed by a variable. Variables are standardized, and enough PCs are retained to explain at least 80% of weather variance. Scores are ordered within each county, not compared as absolute effects across counties.'),
          p('PCA contribution is not a p-value, statistical significance, or predictive importance for PM2.5. Small rank differences can be unstable. PM2.5 values are not used in this ranking.','SmallNote')]
for c in meta['counties']:
    county=c['county']; data=rows_for(county)
    story += [PageBreak(),p(county,'Title'),
              p(f"Worksheet: {escape(c['sheet'])} | {c['complete_rows']} of {c['input_rows']} rows used | {c['dropped_rows']} rows omitted",'SmallNote'),
              p(f"{c['retained_components']} retained PCs explain {c['retained_variance']:.2%} of standardized weather variance."),Spacer(1,12)]
    rows=[['Rank','Variable','Importance (%)','Communality','Screening flag']]
    for r in data:
        included=bool(r['importance_percent'])
        rows.append([str(int(float(r['rank']))) if included else '-',r['variable'],
                     f"{float(r['importance_percent']):.4f}" if included else '-',
                     f"{float(r['communality']):.4f}" if included else '-',
                     {'high_redundancy':'Redundancy','retained':'None','constant':'Constant / excluded'}.get(r['status'],r['status'])])
    story += [table(rows,[35,120,95,80,110]),Spacer(1,10),
              Image(str(RESULTS/county/'variable_ranking.png'),width=440,height=247.5),Spacer(1,8)]
    dew=next(r for r in data if r['variable']=='Dew Point')
    story += [p(f"Temperature / dew point correlation: {float(dew['strongest_correlation']):.4f}. Both are flagged for redundancy; neither was removed for this analysis."),
              p('Communality is the fraction of a variable\'s standardized variance represented by the retained PCs. The low-representation flag applies below 0.50. An absent flag does not establish relevance to PM2.5.','SmallNote')]
    if county=='Sumter':
        story.append(p('Precipitation has no variation in this workbook and is unranked. It is not assigned a zero importance score.','SmallNote'))
    if county in ('Mobile','Montgomery'):
        story.append(p('Some neighboring scores are extremely close. The numerical order is preserved, but this is not evidence of a meaningful difference in importance.','SmallNote'))
story += [PageBreak(),p('Method and reproducibility','Title'),
          p('Input','Heading2'),p('Source workbook: Ana_SK/Meterological_data_ALAbama.xlsx. All ten worksheets were matched to the county names used in the original R code. Dekalb, Etohaw and Jefferson_NB are displayed as DeKalb, Etowah and Jefferson.'),
          p('Procedure','Heading2'),p('All six meteorological variables were considered in each county. All-missing and constant columns were excluded before complete-case deletion. Remaining observations were centered and scaled with sample standard deviations. Singular value decomposition produced the PCA eigenvalues and eigenvectors.'),
          p('The smallest number of PCs reaching 80% cumulative variance was retained. For each variable j, communality equals the sum of eigenvalue(k) times eigenvector(j,k) squared across retained components. Importance equals 100 times that communality divided by the sum of all included variable communalities.'),
          p('Flags and interpretation','Heading2'),p('Low representation: communality below 0.50. Redundancy: absolute pairwise correlation at least 0.90 on the PCA complete-case rows. Thresholds are exploratory choices. Rankings depend on the retained components and do not provide uncertainty intervals. Variables are not automatically deleted based on rank.'),
          p('The existing R analysis used fixed county-specific removals. This run intentionally starts with all six weather variables, so its PCA results need not match the R benchmarks. No PM2.5 association or prediction model is fitted.'),
          p('Reproduction','Heading2'),p('From the repository root, run:<br/><font face="Courier" size="8">python Ana_SR/pca_variable_ranking.py<br/>"Ana_SK/Meterological_data_ALAbama.xlsx"<br/>--output Ana_SR/published_results</font><br/>Join these three lines into one shell command.'),
          p('Run metadata, full-precision CSV tables, loadings, correlation matrices and charts accompany this PDF in Ana_SR/published_results. The PDF builder is Ana_SR/build_report.py and requires reportlab.'),
          p(f"Analysis environment: Python {meta['python']}; NumPy {meta['numpy']}; pandas {meta['pandas']}.",'SmallNote')]
def footer(canvas, doc):
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(colors.HexColor('#64748b'))
    canvas.drawString(42,25,'Ana_SR | County-wise weather variable screening')
    canvas.drawRightString(570,25,str(doc.page))
SimpleDocTemplate(str(OUT),pagesize=(612,792),rightMargin=42,leftMargin=42,
                  topMargin=38,bottomMargin=42,title='County-wise PCA weather variable rankings').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
