"""Build a portable HTML report from the completed seven studies (stdlib only)."""
from pathlib import Path
import base64
import html
import re

ROOT=Path(__file__).resolve().parent


def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    def link(match):
        title,url=match.groups()
        if url.startswith('http'):
            return f'<a href="{url}">{title}</a>'
        if 'REPORT.md' in url:
            folder=url.split('/')[-2]
            return f'<a href="#{folder}">{title}</a>'
        return title
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)


def markdown(text):
    """Render the small, controlled Markdown subset authored by study.py."""
    lines=text.splitlines(); out=[]; paragraph=[]; i=0
    def flush():
        if paragraph:
            out.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush(); block=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]);i+=1
            out.append('<pre>'+html.escape('\n'.join(block))+'</pre>')
        elif line.startswith('|'):
            flush(); rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[\s|:\-]+\|$',lines[i]):
                    rows.append([c.strip() for c in lines[i].strip('|').split('|')])
                i+=1
            out.append('<div class="table-wrap"><table>')
            for r,row in enumerate(rows):
                tag='th' if r==0 else 'td'
                out.append('<tr>'+''.join(f'<{tag}>{inline(c)}</{tag}>' for c in row)+'</tr>')
            out.append('</table></div>');continue
        elif line.startswith('#'):
            flush();level=len(line)-len(line.lstrip('#'))
            out.append(f'<h{min(level+1,6)}>'+inline(line[level:].strip())+f'</h{min(level+1,6)}>')
        elif not line.strip():flush()
        elif re.match(r'^\d+\. |^- ',line):
            flush();out.append('<p class="item">'+inline(line)+'</p>')
        else:paragraph.append(line)
        i+=1
    flush();return '\n'.join(out)


def main():
    folders=sorted(p for p in ROOT.iterdir() if p.is_dir() and re.match(r'^0[1-7]_',p.name))
    nav=''.join(f'<a href="#{p.name}">{p.name.replace("_"," ")}</a>' for p in folders)
    parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Initial PM2.5 study — 2025 Alabama data</title><style>',
        'body{margin:0;background:#f3f5f7;color:#203047;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:28px}',
        'h1,h2,h3{line-height:1.2;color:#133851}h1{font-size:36px}h2{margin-top:34px}h3{margin-top:28px}',
        'section,header{background:white;padding:30px;border-radius:12px;margin:22px 0;box-shadow:0 2px 8px #0000000b}',
        'nav{display:flex;flex-wrap:wrap;gap:8px}nav a{background:#e7eff5;padding:7px 12px;border-radius:5px;text-decoration:none}',
        'a{color:#175c87}table{border-collapse:collapse;font-size:14px;width:100%}th{background:#e8eff5;text-align:left}td,th{padding:8px 10px;border-bottom:1px solid #dae2e8;white-space:nowrap}',
        '.table-wrap{overflow-x:auto}tr:nth-child(even){background:#f8fafb}code{background:#edf1f5;padding:2px 4px;font-size:.9em}',
        'pre{background:#edf1f5;padding:16px;overflow:auto}figure{margin:28px 0}figure img{width:100%;height:auto;cursor:zoom-in}figcaption{font-size:14px;color:#526477}',
        'details{margin:20px 0}summary{cursor:pointer;font-weight:600}.item{margin:6px 0}footer{font-size:14px;color:#526477}',
        '@media print{body{background:white}section,header{box-shadow:none;padding:0}nav{display:none}section{break-before:page}table{font-size:10px}figure{break-inside:avoid}}',
        '</style></head><body><main><header><h1>Initial PM2.5 study</h1><p>Seven completed exploratory analyses of the supplied 2025 Alabama workbook.</p>',nav,'</header>',
        '<section id="overview">',markdown((ROOT/'README.md').read_text()),'</section>']
    for folder in folders:
        parts+=['<section id="'+folder.name+'">',markdown((folder/'REPORT.md').read_text())]
        for image in sorted(folder.glob('*.png')):
            data=base64.b64encode(image.read_bytes()).decode()
            label=image.stem.replace('_',' ').capitalize()
            parts.append(f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(label)}" onclick="this.requestFullscreen?.()"><figcaption>{html.escape(label)}. Click to view full screen; press Esc to return.</figcaption></figure>')
        parts.append('</section>')
    parts+=['<section id="methods">',markdown((ROOT/'METHODS.md').read_text()),'</section>',
            '<footer>Source workbook preserved. Exact inputs, code, tables, model artifacts and verification results accompany this report in the local study folder.</footer></main></body></html>']
    path=ROOT/'study_report.html'
    path.write_text('\n'.join(parts),encoding='utf-8')
    print(path)


if __name__=='__main__':main()
