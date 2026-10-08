"""Local export layouts and burned word-highlight captions."""
import re
import textwrap

LAYOUTS=['Original','Portrait · full picture','Portrait · speaker crop','Portrait · two speakers','Portrait · automatic']


def normalize_layout(layout):
    return LAYOUTS[4] if layout=='Portrait · automatic interview' else layout


def default_layout(vertical):
    return LAYOUTS[4] if vertical else LAYOUTS[0]


def ass_time(t):
    ticks=round(max(0,t)*100);h,ticks=divmod(ticks,360000);m,ticks=divmod(ticks,6000);s,c=divmod(ticks,100)
    return f'{h}:{m:02}:{s:02}.{c:02}'


def safe_text(text):
    return re.sub(r'[\x00-\x1f]', ' ',str(text)).replace('\\','').replace('{','').replace('}','')


def write_ass(path,words,start,end,width,height,burn,title,emphasis=None,emphasis_style='Bold'):
    size=38 if height>width else max(22,round(height*.048))
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,{round(height*.16)},1
Style: Title,Arial,{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,3,8,0,8,50,50,{round(height*.07)},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    if burn:
        emphasized=set((emphasis or {}).get('indices',[]))
        selected=[dict(w,emphasized=i in emphasized) for i,w in enumerate(words) if w['end']>start and w['start']<end]
        groups=[];group=[]
        for w in selected:
            if group and (len(group)>=5 or w.get('segment_id')!=group[-1].get('segment_id') or w['start']-group[-1]['end']>.6 or len(' '.join(x['text'] for x in group))+len(w['text'])>40):groups.append(group);group=[]
            group.append(w)
        if group:groups.append(group)
        for group in groups:
            for i,w in enumerate(group):
                a=max(start,w['start'])-start;b=min(end,w['end'],group[i+1]['start'] if i+1<len(group) else end)-start
                if b<=a:continue
                parts=[]
                for j,x in enumerate(group):
                    word=safe_text(x['text'])
                    if j==i and x.get('emphasized'):
                        # Inline sizing keeps caption placement stable. Only semantic words animate.
                        tags=f'\\b1\\fs{round(size*1.14)}\\c&H70FF80&'
                        if emphasis_style=='Gentle pop':
                            milliseconds=min(160,max(40,round((b-a)*1000*.7)))
                            tags+=f'\\fscx108\\fscy108\\t(0,{milliseconds},\\fscx100\\fscy100)'
                        word='{'+tags+'}'+word+'{\\rCaption}'
                    elif j==i:word='{\\c&H70FF80&}'+word+'{\\rCaption}'
                    parts.append(word)
                text=' '.join(parts)
                events.append(f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Caption,,0,0,0,,{text}')
    if title.strip():
        text=r'\N'.join(textwrap.wrap(safe_text(title)[:100],30 if height>width else 55))
        events.append(f'Dialogue: 1,0:00:00.00,{ass_time(min(3,end-start))},Title,,0,0,0,,{text}')
    path.write_text(header+'\n'.join(events)+'\n',encoding='utf-8')


def layout_filter(layout,position=.5,second=.75):
    layout=normalize_layout(layout)
    position=max(0,min(1,float(position)));second=max(0,min(1,float(second)))
    if layout in (LAYOUTS[1],LAYOUTS[4]):
        from framing import blur_filter
        return blur_filter()
    if layout==LAYOUTS[2]:return f'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280:(iw-720)*{position}:(ih-1280)/2,setsar=1'
    if layout==LAYOUTS[3]:return f'split=2[top][bottom];[top]scale=720:640:force_original_aspect_ratio=increase,crop=720:640:(iw-720)*{position}:(ih-640)/2[t];[bottom]scale=720:640:force_original_aspect_ratio=increase,crop=720:640:(iw-720)*{second}:(ih-640)/2[b];[t][b]vstack,setsar=1'
    return 'scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1'
