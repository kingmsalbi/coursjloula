import os
import html
import docx

def render_docx(docx_path, file_display_name="Document"):
    """
    Renders a .docx file into clean, mobile-first responsive HTML.
    Optimized for smartphones:
      - Reading progress bar
      - Font size controls (A- / A+)
      - 3 Reading themes: Jour, Sépia, Nuit
      - Touch-scrollable tables with swipe hints
      - Responsive typography and touch ergonomics
    """
    try:
        doc = docx.Document(docx_path)
    except Exception as e:
        return render_error_page(f"Impossible de lire le document Word : {str(e)}", file_display_name)

    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="fr" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{html.escape(file_display_name)}</title>
    <style>
        :root {{
            --bg-body: #f1f5f9;
            --bg-card: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --heading-color: #0f172a;
            --border-color: #e2e8f0;
            --primary: #2563eb;
            --badge-bg: #eff6ff;
            --badge-text: #1d4ed8;
            --table-header: #f8fafc;
            --table-alt: #f8fafc;
            --table-border: #cbd5e1;
            --code-bg: #f1f5f9;
            --hint-bg: #e0e7ff;
            --hint-text: #3730a3;
            --font-size: 16px;
        }}

        [data-theme="sepia"] {{
            --bg-body: #f4ede1;
            --bg-card: #fbf7ee;
            --text-main: #433422;
            --text-muted: #79664f;
            --heading-color: #2b1d0c;
            --border-color: #e7dac2;
            --primary: #b45309;
            --badge-bg: #f3e5cb;
            --badge-text: #78350f;
            --table-header: #f3e7cf;
            --table-alt: #f7eed9;
            --table-border: #dccdb3;
            --code-bg: #ece0c8;
            --hint-bg: #ede0c6;
            --hint-text: #78350f;
        }}

        [data-theme="dark"] {{
            --bg-body: #090d16;
            --bg-card: #131c2e;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
            --heading-color: #f8fafc;
            --border-color: #223049;
            --primary: #3b82f6;
            --badge-bg: #1e293b;
            --badge-text: #93c5fd;
            --table-header: #19253d;
            --table-alt: #162035;
            --table-border: #2c3e5d;
            --code-bg: #19253d;
            --hint-bg: #1e293b;
            --hint-text: #93c5fd;
        }}

        * {{
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            margin: 0;
            padding: 8px 6px 40px 6px;
            font-size: var(--font-size);
            line-height: 1.75;
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: background-color 0.2s, color 0.2s;
            touch-action: manipulation;
        }}

        @media (min-width: 640px) {{
            body {{
                padding: 16px 12px 60px 12px;
            }}
        }}

        /* Reading Progress Bar (Fixed Top) */
        #progressBar {{
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            width: 0%;
            background: linear-gradient(90deg, #3b82f6, #6366f1);
            z-index: 1000;
            transition: width 0.1s;
        }}

        /* Mobile Sticky Toolbar */
        .mobile-toolbar {{
            position: sticky;
            top: 0;
            z-index: 900;
            width: 100%;
            max-width: 880px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 6px 10px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
            gap: 6px;
        }}

        .toolbar-group {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}

        .t-btn {{
            background: var(--bg-body);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 5px 9px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 32px;
            transition: all 0.15s;
        }}

        .t-btn:active {{
            transform: scale(0.96);
        }}

        .t-btn.active {{
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary);
        }}

        .document-wrapper {{
            background: var(--bg-card);
            width: 100%;
            max-width: 880px;
            min-height: 85vh;
            padding: 18px 14px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
            border-radius: 14px;
            border: 1px solid var(--border-color);
            transition: background-color 0.2s, border-color 0.2s;
        }}

        @media (min-width: 640px) {{
            .document-wrapper {{
                padding: 44px 38px;
                border-radius: 18px;
            }}
        }}

        .doc-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 12px;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .doc-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background-color: var(--badge-bg);
            color: var(--badge-text);
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
        }}

        h1, h2, h3, h4 {{
            color: var(--heading-color);
            font-weight: 700;
            margin-top: 1.4em;
            margin-bottom: 0.4em;
            line-height: 1.3;
        }}

        h1 {{ font-size: 1.45rem; }}
        h2 {{ font-size: 1.25rem; }}
        h3 {{ font-size: 1.1rem; }}

        @media (min-width: 640px) {{
            h1 {{ font-size: 1.8rem; }}
            h2 {{ font-size: 1.4rem; }}
            h3 {{ font-size: 1.2rem; }}
        }}

        p {{
            margin-top: 0;
            margin-bottom: 1.1em;
            line-height: 1.75;
            word-wrap: break-word;
        }}

        /* Touch-Scrollable Table Container */
        .table-scroll-wrapper {{
            margin: 1.5em 0;
            width: 100%;
        }}

        .table-scroll-hint {{
            font-size: 11px;
            color: var(--hint-text);
            background: var(--hint-bg);
            padding: 3px 8px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-bottom: 6px;
            font-weight: 600;
        }}

        @media (min-width: 768px) {{
            .table-scroll-hint {{ display: none; }}
        }}

        .table-scroll-inner {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border-radius: 10px;
            border: 1px solid var(--table-border);
        }}

        table {{
            width: 100%;
            min-width: 480px;
            border-collapse: collapse;
            font-size: 0.9em;
        }}

        th, td {{
            border: 1px solid var(--table-border);
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background-color: var(--table-header);
            font-weight: 700;
            color: var(--heading-color);
        }}

        tr:nth-child(even) {{
            background-color: var(--table-alt);
        }}

        ul, ol {{
            margin-bottom: 1.1em;
            padding-left: 20px;
        }}

        li {{
            margin-bottom: 0.35em;
        }}

        strong {{
            font-weight: 700;
            color: var(--heading-color);
        }}

        code {{
            background-color: var(--code-bg);
            padding: 2px 5px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div id="progressBar"></div>

    <!-- Mobile-First Reading Controls -->
    <div class="mobile-toolbar">
        <div class="toolbar-group">
            <button class="t-btn active" id="btnThemeLight" onclick="setTheme('light')" title="Mode Jour">☀️ <span style="display:none; @media(min-width:400px){{display:inline;}}">Jour</span></button>
            <button class="t-btn" id="btnThemeSepia" onclick="setTheme('sepia')" title="Mode Sépia (Confort des yeux)">📜 <span style="display:none; @media(min-width:400px){{display:inline;}}">Sépia</span></button>
            <button class="t-btn" id="btnThemeDark" onclick="setTheme('dark')" title="Mode Nuit (Sombre)">🌙 <span style="display:none; @media(min-width:400px){{display:inline;}}">Nuit</span></button>
        </div>
        <div class="toolbar-group">
            <button class="t-btn" onclick="changeFontSize(-1)" title="Diminuer texte">A-</button>
            <span id="fontIndicator" style="font-size: 11px; font-weight: 700; min-width: 32px; text-align: center; color: var(--text-muted);">100%</span>
            <button class="t-btn" onclick="changeFontSize(1)" title="Agrandir texte">A+</button>
        </div>
    </div>

    <div class="document-wrapper" id="contentArea">
        <div class="doc-header">
            <span class="doc-badge">📄 Document Word (.docx)</span>
            <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Adapté pour smartphone</span>
        </div>
""")

    for element in doc.element.body:
        if element.tag.endswith('p'):
            p = docx.text.paragraph.Paragraph(element, doc)
            text = p.text.strip()
            if not text:
                continue

            style_name = (p.style.name or '').lower() if p.style else ''

            p_html = ""
            for run in p.runs:
                r_text = html.escape(run.text)
                if run.bold and run.italic:
                    r_text = f"<strong><em>{r_text}</em></strong>"
                elif run.bold:
                    r_text = f"<strong>{r_text}</strong>"
                elif run.italic:
                    r_text = f"<em>{r_text}</em>"
                p_html += r_text

            if 'heading 1' in style_name or 'titre 1' in style_name:
                parts.append(f"<h1>{p_html}</h1>")
            elif 'heading 2' in style_name or 'titre 2' in style_name:
                parts.append(f"<h2>{p_html}</h2>")
            elif 'heading 3' in style_name or 'titre 3' in style_name:
                parts.append(f"<h3>{p_html}</h3>")
            else:
                parts.append(f"<p>{p_html}</p>")

        elif element.tag.endswith('tbl'):
            t = docx.table.Table(element, doc)
            parts.append("""
            <div class="table-scroll-wrapper">
                <div class="table-scroll-hint">↔ Faire glisser pour voir les colonnes</div>
                <div class="table-scroll-inner">
                    <table>
            """)
            for i, row in enumerate(t.rows):
                parts.append("<tr>")
                for cell in row.cells:
                    cell_text = html.escape(cell.text.strip()).replace('\n', '<br>')
                    tag = "th" if i == 0 else "td"
                    parts.append(f"<{tag}>{cell_text}</{tag}>")
                parts.append("</tr>")
            parts.append("""
                    </table>
                </div>
            </div>
            """)

    parts.append("""
    </div>

    <script>
        // Progress bar updates on scroll
        window.addEventListener('scroll', () => {
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? (window.scrollY / docHeight) * 100 : 0;
            document.getElementById('progressBar').style.width = Math.min(100, Math.max(0, progress)) + '%';
        }, { passive: true });

        // Themes
        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            ['Light', 'Sepia', 'Dark'].forEach(t => {
                const btn = document.getElementById('btnTheme' + t);
                if (btn) btn.classList.toggle('active', t.toLowerCase() === theme);
            });
            try { localStorage.setItem('pc_reader_theme', theme); } catch(e){}
        }

        // Restore saved theme
        try {
            const savedTheme = localStorage.getItem('pc_reader_theme');
            if (savedTheme) setTheme(savedTheme);
        } catch(e){}

        // Font scaling for mobile readability
        let currentSize = 16;
        function changeFontSize(delta) {
            currentSize = Math.max(13, Math.min(24, currentSize + (delta * 1.5)));
            document.documentElement.style.setProperty('--font-size', currentSize + 'px');
            const percent = Math.round((currentSize / 16) * 100);
            document.getElementById('fontIndicator').textContent = percent + '%';
        }
    </script>
</body>
</html>
""")
    return "\n".join(parts)

def render_pdf_viewer(raw_pdf_url, file_display_name="Document", download_url=""):
    """
    Renders PDF documents with Mozilla PDF.js for 100% mobile compatibility.
    Solves iOS Safari and Android Chrome blank/unscrollable iframe issues.
    Features:
      - Continuous vertical touch scroll
      - High-DPI canvas rendering for Retina/AMOLED phone screens
      - Touch zoom controls
      - Page indicator
    """
    escaped_title = html.escape(file_display_name)
    escaped_pdf_url = html.escape(raw_pdf_url)
    escaped_download = html.escape(download_url or raw_pdf_url)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{escaped_title}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        body {{
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        /* Sticky Mobile PDF Toolbar */
        .pdf-toolbar {{
            position: sticky;
            top: 0;
            z-index: 100;
            width: 100%;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #334155;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }}

        .toolbar-group {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .btn-tool {{
            background: #1e293b;
            color: #f1f5f9;
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 34px;
            transition: all 0.15s;
        }}

        .btn-tool:active {{ transform: scale(0.95); background: #334155; }}

        .page-badge {{
            font-size: 12px;
            font-weight: 600;
            color: #94a3b8;
            background: #1e293b;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid #334155;
        }}

        #pdfViewerContainer {{
            width: 100%;
            max-width: 900px;
            padding: 10px 6px 40px 6px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}

        .pdf-page-card {{
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            justify-content: center;
            width: 100%;
        }}

        canvas {{
            display: block;
            width: 100% !important;
            height: auto !important;
        }}

        #loadingSpinner {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 60px 20px;
            color: #94a3b8;
            font-size: 14px;
        }}

        .spinner {{
            width: 36px;
            height: 36px;
            border: 3px solid #334155;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .fallback-btn {{
            color: #38bdf8;
            text-decoration: underline;
            font-size: 12px;
            margin-top: 10px;
            background: none;
            border: none;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="pdf-toolbar">
        <div class="toolbar-group">
            <span class="page-badge">
                📄 <span id="curPageNum">1</span> / <span id="totalPageNum">-</span>
            </span>
        </div>
        <div class="toolbar-group">
            <button class="btn-tool" onclick="zoom(-0.15)" title="Dézoomer">➖</button>
            <button class="btn-tool" onclick="resetZoom()" title="Ajuster largeur mobile">📱</button>
            <button class="btn-tool" onclick="zoom(0.15)" title="Zoomer">➕</button>
            <a href="{escaped_download}" class="btn-tool" style="text-decoration: none;" title="Télécharger le fichier">⬇️</a>
        </div>
    </div>

    <div id="loadingSpinner">
        <div class="spinner"></div>
        <div>Chargement du document pour mobile...</div>
        <a href="{escaped_pdf_url}" class="fallback-btn">Ouvrir directement le PDF original</a>
    </div>

    <div id="pdfViewerContainer"></div>

    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        let pdfDoc = null;
        let scale = 1.0;
        const container = document.getElementById('pdfViewerContainer');
        const spinner = document.getElementById('loadingSpinner');

        async function initPDF() {{
            try {{
                const loadingTask = pdfjsLib.getDocument('{escaped_pdf_url}');
                pdfDoc = await loadingTask.promise;
                document.getElementById('totalPageNum').textContent = pdfDoc.numPages;
                spinner.style.display = 'none';
                renderAllPages();
            }} catch(err) {{
                console.error('PDF.js Error:', err);
                spinner.innerHTML = `
                    <div style="font-size:32px;">⚠️</div>
                    <div style="color:#f87171; font-weight:600;">Impossible d'afficher ce PDF dans la liseuse.</div>
                    <a href="{escaped_pdf_url}" class="btn-tool" style="margin-top:12px; text-decoration:none;">
                        ⬇️ Télécharger ou ouvrir le document PDF
                    </a>
                `;
            }}
        }}

        async function renderAllPages() {{
            container.innerHTML = '';
            for (let num = 1; num <= pdfDoc.numPages; num++) {{
                const pageCard = document.createElement('div');
                pageCard.className = 'pdf-page-card';
                pageCard.dataset.page = num;

                const canvas = document.createElement('canvas');
                pageCard.appendChild(canvas);
                container.appendChild(pageCard);

                await renderPage(num, canvas);
            }}
        }}

        async function renderPage(num, canvas) {{
            const page = await pdfDoc.getPage(num);
            const dpr = window.devicePixelRatio || 1;
            
            // Calculate scale to fit container width
            const containerWidth = Math.min(window.innerWidth - 12, 880);
            const unscaledViewport = page.getViewport({{ scale: 1.0 }});
            const autoScale = (containerWidth / unscaledViewport.width) * scale;
            
            const viewport = page.getViewport({{ scale: autoScale }});
            
            canvas.width = Math.floor(viewport.width * dpr);
            canvas.height = Math.floor(viewport.height * dpr);
            canvas.style.width = Math.floor(viewport.width) + 'px';
            canvas.style.height = Math.floor(viewport.height) + 'px';

            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);

            await page.render({{
                canvasContext: ctx,
                viewport: viewport
            }}).promise;
        }}

        function zoom(delta) {{
            scale = Math.max(0.6, Math.min(2.5, scale + delta));
            renderAllPages();
        }}

        function resetZoom() {{
            scale = 1.0;
            renderAllPages();
        }}

        // Track visible page on scroll
        window.addEventListener('scroll', () => {{
            const cards = document.querySelectorAll('.pdf-page-card');
            cards.forEach(card => {{
                const rect = card.getBoundingClientRect();
                if (rect.top <= window.innerHeight / 2 && rect.bottom >= window.innerHeight / 2) {{
                    document.getElementById('curPageNum').textContent = card.dataset.page;
                }}
            }});
        }}, {{ passive: true }});

        initPDF();
    </script>
</body>
</html>
"""

def render_error_page(message, file_name="Document"):
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erreur de lecture</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
            margin: 0;
            padding: 16px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 16px;
            padding: 28px 20px;
            max-width: 440px;
            text-align: center;
            border: 1px solid #334155;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.2);
        }}
        .icon {{ font-size: 36px; margin-bottom: 12px; }}
        h2 {{ color: #f8fafc; margin-top: 0; font-size: 1.15rem; }}
        p {{ color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">⚠️</div>
        <h2>{html.escape(file_name)}</h2>
        <p>{html.escape(message)}</p>
    </div>
</body>
</html>
"""

def render_office_fallback(file_name, download_url):
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{html.escape(file_name)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 85vh;
            margin: 0;
            padding: 16px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 18px;
            padding: 28px 20px;
            max-width: 460px;
            text-align: center;
            border: 1px solid #334155;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.3);
        }}
        .icon {{ font-size: 42px; margin-bottom: 12px; }}
        h2 {{ color: #f8fafc; margin: 0 0 8px 0; font-size: 1.2rem; }}
        p {{ color: #94a3b8; font-size: 0.9rem; line-height: 1.6; margin-bottom: 22px; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            padding: 14px 22px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.95rem;
            width: 100%;
            box-sizing: border-box;
            transition: background 0.2s;
            min-height: 48px;
        }}
        .btn:active {{ background: #1d4ed8; transform: scale(0.98); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">📊</div>
        <h2>{html.escape(file_name)}</h2>
        <p>Ce fichier bureautique (PowerPoint ou Excel) s'ouvre directement avec l'application de votre téléphone.</p>
        <a href="{html.escape(download_url)}" class="btn">
            <span>⬇️</span> Télécharger et ouvrir
        </a>
    </div>
</body>
</html>
"""
