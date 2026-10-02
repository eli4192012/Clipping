"""Light blue visual shell for the local clipping studio."""
from pathlib import Path
import base64


def brand():
    mark=base64.b64encode((Path(__file__).parent/'assets/mark.svg').read_bytes()).decode()
    return f'<div class="studio-brand"><img alt="Clipping logo" src="data:image/svg+xml;base64,{mark}"><div>Clipping<span>YOUR LOCAL VIDEO STUDIO</span></div></div>'


def hero():
    return '''<section class="library-hero"><div class="hero-copy"><div class="eyebrow">YOUR WORKSPACE</div><h1>My projects</h1><p>Your imported videos, completed runs, clip edits and caption corrections stay saved on this Mac.</p></div><div class="hero-art" aria-hidden="true"><div class="wave wave-one"></div><div class="wave wave-two"></div><div class="glass-tile tile-back">▤</div><div class="glass-tile tile-main">[▷]</div><div class="glass-tile tile-play">▶</div></div></section>'''


def stat_card(label, value, detail, symbol, violet=False):
    import html
    return f'<div class="summary-card"><div class="summary-top"><div class="summary-icon {"violet" if violet else ""}" aria-hidden="true">{symbol}</div><div><div class="summary-label">{html.escape(label)}</div><div class="summary-value">{html.escape(str(value))}</div></div></div><div class="summary-detail">{html.escape(detail)}</div></div>'


def install(st):
    st.markdown('''<style>
:root {color-scheme:light}
.stApp {background:linear-gradient(125deg,#f5f9ff 0%,#f0f5fd 55%,#f9fbff 100%);color:#101737}
[data-testid="stAppDeployButton"] {display:none}
[data-testid="stHeader"] {background:rgba(246,249,255,.9)}
[data-testid="stSidebar"] {background:linear-gradient(155deg,#fff 0%,#f2f7ff 75%,#e8f2ff 100%);border-right:1px solid #e0e9f7;min-width:270px}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1rem}
.block-container {max-width:1450px;padding-top:3.7rem;padding-bottom:4rem}
h1 {font-size:2.8rem!important;letter-spacing:-1.7px;line-height:1.12!important;font-weight:750!important;color:#090f2a}
h2 {font-size:1.7rem!important;letter-spacing:-.6px;color:#101737}
h3 {font-size:1.1rem!important;letter-spacing:-.2px;line-height:1.5!important;color:#101737}
p {line-height:1.6}
[data-testid="stCaptionContainer"] {color:#647395}
.stButton button,.stDownloadButton button {border-radius:12px;min-height:44px;font-weight:600;border:1px solid #dce5f5;background:#fff;color:#24365c;transition:background .15s ease,box-shadow .15s ease}
.stButton button:hover,.stDownloadButton button:hover {border-color:#8cabff;background:#edf3ff;color:#234ef5;box-shadow:0 4px 12px #355ce012}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"] {background:linear-gradient(150deg,#548dff,#3d50ff);color:#fff;border-color:transparent;box-shadow:0 5px 13px #4166fa25}
button:focus-visible,a:focus-visible {outline:3px solid #315bdf!important;outline-offset:3px}
[data-testid="stSidebar"] .stButton button {text-align:left;justify-content:flex-start;padding:12px 18px;border-color:transparent;background:transparent;min-height:52px}
[data-testid="stSidebar"] .stButton button[kind="primary"] {background:#dfecff;color:#1647ed;box-shadow:none}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:20px}
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {border-color:#e1e9f6!important;border-radius:20px!important}
[data-testid="stMetric"] {background:#ffffffd9;border:1px solid #e0e8f6;padding:20px;border-radius:18px}
[data-testid="stExpander"] {border-color:#e0e8f6;border-radius:12px;background:#ffffff80}
[data-testid="stForm"] {border-color:#dce5f5;border-radius:12px}
[data-testid="stTextInput"] [data-baseweb="input"], [data-testid="stSelectbox"] [data-baseweb="select"]>div {border-radius:12px;background:#fff;border-color:#dde6f5}
[data-testid="stVideo"] {border-radius:14px;overflow:hidden;background:#080d0e;max-width:800px;margin:auto}
.studio-brand {display:flex;align-items:center;gap:14px;font-size:27px;font-weight:750;letter-spacing:-.8px;line-height:1.2;margin:5px 0 35px}
.studio-brand img {width:58px;height:58px;filter:drop-shadow(0 6px 9px #3866ef25)}
.studio-brand span {display:block;font-size:8px;letter-spacing:2px;color:#63749a;margin-top:8px;font-weight:650;white-space:nowrap}
.st-key-release-header {margin-bottom:4px}
.st-key-release-header [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;align-items:center}
.st-key-release-header [data-testid="stColumn"]:first-child {flex:1 1 auto!important;min-width:0!important;width:auto!important}
.st-key-release-header [data-testid="stColumn"]:last-child {flex:0 0 80px!important;min-width:80px!important;width:80px!important}
.st-key-release-header button {background:#e7edf9;color:#435477;border:0;min-height:36px}
.header-label {font-size:12px;color:#657493;letter-spacing:.3px}
.steps {display:flex;gap:8px;margin:20px 0 28px;flex-wrap:wrap}
.step {padding:8px 13px;border-radius:9px;font-size:12px;color:#677594;background:#eaf0fa;border:1px solid transparent}
.step.active {color:#244cf2;background:#dfebff;border-color:#bed0ff}
.eyebrow {font-size:11px;font-weight:700;letter-spacing:2.6px;color:#2458fa;margin:8px 0 14px}
[data-testid="stSidebar"] .eyebrow {color:#7181a3;font-size:10px}
.studio-note {padding:22px 0;color:#687999;font-size:12px;border-top:1px solid #dfe8f6;margin-top:26px}
.studio-note strong {color:#263758;font-weight:500}.local-dot {display:inline-block;width:9px;height:9px;background:#18ad88;border-radius:50%;margin-right:8px}
.library-hero {position:relative;overflow:hidden;isolation:isolate;min-height:270px;border-radius:24px;background:linear-gradient(120deg,#e5f0ff,#f3f7ff 53%,#dce9ff);padding:40px 32px;margin:0 0 8px}
.hero-copy {position:relative;z-index:2;max-width:56%}.hero-copy p {color:#63749a;font-size:16px;margin:16px 0 0}.hero-copy h1 {padding:0!important;margin:0}
.hero-art {position:absolute;inset:0 0 0 49%;pointer-events:none}.wave {position:absolute;width:650px;height:280px;border-radius:48%;transform:rotate(-22deg);background:linear-gradient(120deg,#a2d4ff77,#8b8aff33,#ffffffaa);border:1px solid #ffffff9e}.wave-one{top:18px;left:0}.wave-two{top:185px;left:-140px;transform:rotate(-12deg);z-index:4}
.glass-tile {position:absolute;display:grid;place-items:center;border-radius:28px;border:1px solid #fff9;box-shadow:14px 20px 28px #466bec25;transform:rotate(11deg) skewY(-8deg);font-weight:800;color:white}
.tile-main {width:155px;height:162px;top:33px;left:32%;font-size:64px;background:linear-gradient(140deg,#e1efff,#7d9bff 55%,#4644fd);z-index:3;text-shadow:0 5px 8px #243ce566}
.tile-back {width:115px;height:116px;top:102px;left:8%;background:linear-gradient(130deg,#ecf3ff,#9ea9ef88);color:#ffffffb5;font-size:78px;transform:rotate(15deg)}
.tile-play {width:112px;height:126px;top:103px;left:68%;font-size:63px;color:#4262f5;background:linear-gradient(130deg,#fff,#acc7ffbb);transform:rotate(10deg)}
.summary-card {padding:22px 24px;background:#ffffffed;border:1px solid #e3ebf8;border-radius:20px;box-shadow:0 10px 24px #384e7b05;min-height:164px;margin:4px 0 12px}.summary-top {display:flex;align-items:center;gap:18px}.summary-icon {width:62px;height:62px;flex-shrink:0;border-radius:17px;background:#e6f3ff;display:grid;place-items:center;color:#2460ff;font-size:32px}.summary-icon.violet{background:#f0eaff;color:#6a48ef}.summary-label{font-size:14px;color:#4f6083}.summary-value{font-size:clamp(20px,2vw,28px);font-weight:750;color:#101737;letter-spacing:-1px;line-height:1.3;margin-top:3px}.summary-detail{font-size:13px;color:#6c7c9c;margin-top:13px}
.st-key-project-search {margin:2px 0 10px}.st-key-project-search input{min-height:48px}
[class*="st-key-project-card-"] {background:#ffffffec;border:1px solid #e1e9f6;border-radius:20px;padding:20px;box-shadow:0 8px 22px #203d7405;margin-bottom:8px}
.project-cover {position:relative;border-radius:13px;overflow:hidden;aspect-ratio:16/9;background:#e8effb}.project-cover img{width:100%;height:100%;object-fit:cover;display:block}.cover-duration{position:absolute;bottom:8px;right:8px;background:#101737cc;color:white;font-size:12px;padding:2px 7px;border-radius:5px}.cover-placeholder{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:44px;color:#6a8bdd}.cover-placeholder span{font-size:11px;color:#586e99}
.project-title {font-size:17px;font-weight:700;line-height:1.5;color:#111936;margin:0 0 8px;overflow-wrap:anywhere}.project-runs{font-size:14px;color:#5b6c90;margin-bottom:12px}.project-meta{display:flex;gap:7px;flex-wrap:wrap}.project-meta span{font-size:11px;padding:6px 9px;border-radius:8px;background:#f0f4fb;color:#546582}
@media(min-width:900px){[class*="st-key-project-card-"] [data-testid="stHorizontalBlock"] {align-items:center}}
@media(max-width:900px){.hero-copy{max-width:70%}.hero-art{opacity:.48}.summary-card{padding:16px}.summary-top{gap:9px}.summary-icon{width:40px;height:44px;font-size:25px}.summary-value{font-size:24px}}
@media(max-width:700px){.block-container{padding:3.7rem 1rem 3rem}h1{font-size:2rem!important}.library-hero{padding:26px 22px;min-height:220px}.hero-copy{max-width:100%}.hero-art{opacity:.16;inset:0 0 0 25%}.hero-copy p{font-size:14px}.summary-card{min-height:130px}.step{padding:7px 9px;font-size:11px}}

.st-key-setup-preview,.st-key-setup-quality,.st-key-setup-auto,.st-key-setup-output,.st-key-job-progress {background:#ffffffdb;border:1px solid #e1e9f6;border-radius:20px;padding:22px;box-shadow:0 10px 26px #304d7c05}
.st-key-setup-preview {margin-top:10px}.st-key-setup-preview .project-title{font-size:17px;margin-top:6px}
.st-key-setup-quality,.st-key-setup-auto {min-height:260px;margin-top:12px}
.setup-card-heading{display:flex;gap:14px;align-items:flex-start;margin-bottom:20px}.setup-card-heading strong{font-size:15px;color:#111936}.setup-card-heading p{font-size:12px;color:#647395;line-height:1.5;margin:5px 0 0}.setup-card-heading .summary-icon{width:48px;height:48px;font-size:29px;border-radius:13px}
.st-key-setup-output {margin-top:14px}.st-key-setup-detection {margin-top:2px}
.st-key-job-progress {margin:10px 0 18px}.st-key-job-progress [data-testid="stProgress"] [role="progressbar"]{border-radius:15px;overflow:hidden}.st-key-job-progress [data-testid="stProgress"] [role="progressbar"]>div {background:linear-gradient(90deg,#3e8aff,#784bff)}
.steps{display:flex;align-items:center;gap:10px;margin:0 0 24px;flex-wrap:wrap}.step{display:flex;align-items:center;gap:12px;background:#f3f7ff;border:1px solid #dce7fa;border-radius:15px;padding:12px 16px;font-size:13px}.step.active{background:#ffffffb8;border:1px solid #7896ff;color:#2458fa;box-shadow:0 4px 15px #3758ed08}.step-number{display:inline-grid;place-items:center;width:29px;height:29px;border-radius:50%;background:#e9effa;color:#8190b1;font-size:12px}.step.active .step-number,.step.done .step-number{background:linear-gradient(150deg,#3599ff,#414aff);color:white}.step-connector{color:#a6b8de}
@media(max-width:1100px){.setup-card-heading{gap:8px;flex-wrap:wrap}.st-key-setup-quality,.st-key-setup-auto{padding:15px;min-height:290px}.steps{gap:6px}.step{padding:10px;font-size:12px}}
@media(max-width:700px){.st-key-setup-quality,.st-key-setup-auto{min-height:0}.st-key-setup-preview{margin-bottom:16px}.steps{gap:5px}.step{padding:7px;font-size:11px;gap:5px}.step-connector{display:none}.step-number{width:23px;height:23px}}

</style>''',unsafe_allow_html=True)


def setup_heading(title,detail,symbol,violet=False):
    import html
    return f'<div class="setup-card-heading"><span class="summary-icon {"violet" if violet else ""}" aria-hidden="true">{symbol}</span><div><strong>{html.escape(title)}</strong><p>{html.escape(detail)}</p></div></div>'
