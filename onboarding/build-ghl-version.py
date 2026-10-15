import re, sys
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
src = open('pocket-ceo-deck.html').read()

# ---- split pieces
css = re.search(r'<style>(.*?)</style>', src, re.S).group(1)
js = re.search(r'<script>(.*?)</script>', src, re.S).group(1)
body = src[src.index('</style>')+len('</style>'):src.index('<script>')]
fontlink = re.search(r'<link rel="stylesheet"[^>]+>', src).group(0)

# move nav + dots inside the scaled stage so they scale with it
navs = re.search(r'<nav class="dots".*?</nav>\s*<div class="nav">.*?</div>', body, re.S).group(0)
body = body.replace(navs, '')
body = body.replace('</main>', navs + '\n</main>')
# ---- prefix ids
ids = sorted(set(re.findall(r'\bid="([^"]+)"', body)), key=len, reverse=True)
for i in ids:
    body = body.replace(f'id="{i}"', f'id="pc-{i}"').replace(f'for="{i}"', f'for="pc-{i}"')

# ---- css: scope everything under #pceo
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
css = css.replace('html,body{margin:0;height:100%;overflow:hidden;background:var(--canvas);color:var(--ink)}', '')
css = css.replace('body{font-family:var(--display)', '#pceo{font-family:var(--display)')
css = re.sub(r'body\[data-c=(\w+)\]', r'#pceo[data-c=\1]', css)
css = css.replace('.atmos{position:fixed', '.atmos{position:absolute')
css = css.replace('.nav{position:fixed', '.nav{position:absolute')
css = css.replace('.dots{position:fixed', '.dots{position:absolute')

def prefix_block(block):
    out = []; i = 0
    while i < len(block):
        if block[i].isspace(): out.append(block[i]); i += 1; continue
        j = block.find('{', i)
        if j == -1: out.append(block[i:]); break
        sel = block[i:j].strip()
        # find matching brace
        depth = 0; k = j
        while True:
            if block[k] == '{': depth += 1
            elif block[k] == '}':
                depth -= 1
                if depth == 0: break
            k += 1
        inner = block[j+1:k]
        if sel.startswith('@keyframes') or sel.startswith('@property'):
            out.append(f'{sel}{{{inner}}}')
        elif sel.startswith('@media'):
            out.append(f'{sel}{{{prefix_block(inner)}}}')
        else:
            parts = []
            for s in sel.split(','):
                s = s.strip()
                if s == ':root': parts.append('#pceo')
                elif s.startswith('#pceo'): parts.append(s)
                elif s == '*': parts.append('#pceo *')
                else: parts.append('#pceo ' + s)
            out.append(f'{",".join(parts)}{{{inner}}}')
        i = k + 1
    return ''.join(out)
css = prefix_block(css)
# @property can't live on #pceo scope issue: keep as-is (global, harmless)

wrapper_css = '''
#pceo{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;background:var(--canvas);color:var(--ink);border-radius:18px;isolation:isolate;line-height:normal;text-align:left}
#pceo *,#pceo *::before,#pceo *::after{box-sizing:border-box}
#pceo h1,#pceo h2,#pceo h3,#pceo h4,#pceo h5,#pceo h6,#pceo p,#pceo ol,#pceo ul,#pceo li,#pceo form,#pceo fieldset,#pceo pre{margin:0;padding:0;border:0;text-transform:none;letter-spacing:normal;background:none}
#pceo button,#pceo input,#pceo select,#pceo textarea{font-family:inherit;letter-spacing:normal;text-transform:none;margin:0;line-height:1.2;min-height:0;height:auto;width:auto}
#pceo a{text-decoration:none}
#pceo .deck{left:50%;top:50%}
#pceo-wrap .pc-phone-note{display:none;margin:0 0 12px;padding:14px 16px;border-radius:14px;background:#0E1524;color:#EEF3FF;font:600 16px/1.4 Arial,sans-serif;text-align:center}
@media (max-width:820px){#pceo-wrap .pc-phone-note{display:block}}
'''
# re-add list/fieldset paddings the deck relies on
fix_css = """
#pceo .nav{right:40px;bottom:30px;gap:16px}
#pceo .dots{bottom:44px}
#pceo button{width:auto!important;height:auto!important;min-height:0!important;margin:0!important;box-shadow:none;text-transform:none!important;letter-spacing:normal!important;float:none!important}
#pceo .nav button{font:800 26px/1 var(--display)!important;color:var(--ink)!important;background:rgba(14,21,36,.9)!important;border:2px solid var(--hair)!important;border-radius:999px!important;padding:18px 28px!important}
#pceo .nav button.next{background:var(--field)!important;color:#04120B!important;border-color:transparent!important}
#pceo .dots button{width:34px!important;height:28px!important;padding:0!important;border:0!important;background:transparent!important;border-radius:0!important}
#pceo .bigbtn{background:var(--field)!important;color:#04120B!important;border:0!important;border-radius:24px!important;padding:20px 40px!important;min-height:90px!important;font:900 34px/1 var(--display)!important;box-shadow:0 18px 60px -18px var(--field)!important}
#pceo .bigbtn.ghost{background:transparent!important;color:var(--ink)!important;border:2px solid var(--field)!important;box-shadow:none!important}
#pceo input[type=text],#pceo select,#pceo textarea{height:auto!important;font:500 26px/1.3 var(--display)!important;color:var(--ink)!important;background:var(--panel2)!important;border:2px solid var(--hair)!important}
#pceo .pills input,#pceo .check input{width:22px!important;height:22px!important}
#pceo .check input{width:38px!important;height:38px!important}
#pceo .steps,#pceo .abc{margin:12px 0 0!important}
#pceo .abc{padding:0!important}
#pceo h1,#pceo h2,#pceo h3,#pceo h4,#pceo h5,#pceo h6{color:inherit!important;font-family:var(--display)!important;text-transform:none!important}
#pceo p,#pceo li,#pceo label,#pceo span,#pceo legend{font-family:inherit}
#pceo a.bigbtn{color:#04120B!important;text-decoration:none!important}
""" + '#pceo .steps{padding-left:34px}#pceo fieldset{display:flex}#pceo input[type=text],#pceo select,#pceo textarea{width:100%;padding:16px 20px;border-radius:16px}'

# ---- js: scope
js = js.replace('const $ = id => document.getElementById(id);', 'const ROOT = document.getElementById("pceo");\nconst $ = id => document.getElementById("pc-" + id);')
js = js.replace('const slides = [...document.querySelectorAll(".slide")];', 'const slides = [...ROOT.querySelectorAll(".slide")];')
js = js.replace('function fit(){ const s = Math.min(innerWidth/1920, innerHeight/1080); document.documentElement.style.setProperty("--s", s); $("deck").style.setProperty("--s", s); }\naddEventListener("resize", fit); fit();',
 'function fit(){ const s = ROOT.clientWidth/1920; $("deck").style.setProperty("--s", s); }\ntry { new ResizeObserver(fit).observe(ROOT); } catch(e) { addEventListener("resize", fit); } fit();')
js = js.replace('document.querySelector(`input[name="${n}"]:checked`)', 'ROOT.querySelector(`input[name="${n}"]:checked`)')
js = js.replace('document.querySelector(`input[name="${n}"][value="${CSS.escape(saved[n])}"]`)', 'ROOT.querySelector(`input[name="${n}"][value="${CSS.escape(saved[n])}"]`)')
js = js.replace('document.body.dataset.c = slides[i].dataset.c;', 'ROOT.dataset.c = slides[i].dataset.c;')
js = js.replace('  try { history.replaceState(null, "", "#s" + (i+1)); } catch(e) {}\n', '')
js = js.replace('addEventListener("keydown", e => {\n  if (e.target.closest("input,textarea,select")) return;',
 'addEventListener("keydown", e => {\n  if (e.target.closest && e.target.closest("input,textarea,select")) return;\n  const r = ROOT.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) return;')
js = js.replace('document.addEventListener("input", save); document.addEventListener("change", save);', 'ROOT.addEventListener("input", save); ROOT.addEventListener("change", save);')
js = js.replace('const start = parseInt((location.hash.match(/^#s(\\d+)$/) || [])[1] || "1", 10) - 1;\ngo(isNaN(start) ? 0 : start);', 'go(0);')
js = js.replace('const s = getSelection()', 'const s = window.getSelection()')
js = '(function(){\n' + js + '\nwindow.PCEO_go = go;\n})();'
assert 'location.hash' not in js and 'document.body' not in js, 'leftover global refs'

out = f'''<!-- Pocket CEO deck: paste this whole block into a GoHighLevel Custom HTML/JS element. -->
{fontlink}
<style>{css}
{wrapper_css}
{fix_css}</style>
<div id="pceo-wrap">
<p class="pc-phone-note">To set up Pocket CEO, open this page on your computer. You can still flip through the slides here.</p>
<div id="pceo" data-c="blue">
{body.strip()}
</div>
</div>
<script>{js}</script>
'''
open('pocket-ceo-deck-ghl.html','w').write(out)
print(len(out), 'ids prefixed:', len(ids))

# ---- make the file pure ASCII so no paste box can garble special characters
def ascii_html(t):
    return ''.join(c if ord(c) < 128 else f'&#{ord(c)};' for c in t)
def ascii_js(t):
    out = []
    for c in t:
        o = ord(c)
        if o < 128: out.append(c)
        elif o <= 0xFFFF: out.append('\\u%04x' % o)
        else:
            o -= 0x10000; out.append('\\u%04x\\u%04x' % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
    return ''.join(out)
def ascii_css(t):
    return ''.join(c if ord(c) < 128 else '\\%x ' % ord(c) for c in t)
o = open('pocket-ceo-deck-ghl.html').read()
pre, rest = o.split('<style>', 1); style, rest = rest.split('</style>', 1)
mid, rest = rest.split('<script>', 1); script, post = rest.split('</script>', 1)
o = ascii_html(pre) + '<style>' + ascii_css(style) + '</style>' + ascii_html(mid) + '<script>' + ascii_js(script) + '</script>' + ascii_html(post)
assert all(ord(c) < 128 for c in o)
open('pocket-ceo-deck-ghl.html', 'w').write(o)
print('ascii-only:', len(o))
