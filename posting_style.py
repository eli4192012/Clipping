"""Local, bounded examples for posting-copy personalization; no weight training."""
import collections
import hashlib
import json
import math
import re
from pathlib import Path

from engine import ROOT
from project_store import read, write

VERSION = 'posting-style-1'
PROFILE = ROOT/'data/posting-style/profile.json'
TAG = re.compile(r'(?<!\w)#[\w]+', re.UNICODE)
IGNORED_TAGS = {'fyp', 'fpy', 'viral', 'trending', 'pushed', 'different', 'team', 'win'}
COMMON = set('the a an and or but is are was were it this that to of for on in at as with from by be have has had their our your its he she they his her how why what who can could will would should more about colts nfl football indianapolis interview clip video says said'.split())
COMMON.update('you we me my them us not no do don doesn did didn t really know get got going want wants need needs sort feel like guys guy actually much things games game now anymore even terms areas where these those way ways'.split())
TOPICS = {
    '#OffensiveLine': ('offensive line', 'o line', 'o-line'),
    '#BallSecurity': ('ball security', 'two hands on the ball', 'two hands in the pocket', 'protect the ball'),
    '#RunningBack': ('running back', 'running backs', 'rb', 'rbs'),
    '#Quarterback': ('quarterback', 'quarterbacks', 'qb'),
    '#Defense': ('defense', 'defensive'), '#Touchdown': ('touchdown', 'touchdowns'),
    '#InjuryUpdate': ('injury', 'injured', 'injuries'), '#Turnovers': ('turnover', 'turnovers'),
    '#PassProtection': ('pass protection', 'pass blocking'), '#ThirdDown': ('third down', '3rd down'),
    '#London': ('london',), '#Momentum': ('momentum',), '#Speed': ('speed',),
    '#Signature': ('signature',), '#BestCut': ('best cut',),
}


def words(text):
    return re.findall(r"[\w]+", str(text).casefold())


def plain(text):
    return ' '.join(str(text).split())


def supported_tag(tag, text):
    if not isinstance(tag, str) or not re.fullmatch(r'#[\w]+', tag):return False
    body=tag[1:].replace('_','').casefold()
    if len(body)<3 or body in IGNORED_TAGS:return False
    source=words(text)
    # Require whole adjacent words, not a substring of an unrelated word.
    if any(''.join(source[i:i+n])==body for i in range(len(source)) for n in range(1,6)):
        return True
    phrases=next((v for k,v in TOPICS.items() if k.casefold()==tag.casefold()), ())
    heard=' '+' '.join(source)+' '
    return any(' '+' '.join(words(p))+' ' in heard for p in phrases)


def description_reference(text):
    # Learn the actual description, excluding copied speech, tag lists and footers.
    paragraphs=[]
    for part in re.split(r'\n\s*\n', str(text)):
        part=plain(TAG.sub('', part)).strip()
        if not part or part.casefold().startswith('subscribe to '):continue
        paragraphs.append(part)
    return ' '.join(paragraphs)


def build_profile(corpus):
    if not isinstance(corpus, dict) or not isinstance(corpus.get('records'), list):
        raise ValueError('Posting examples must contain a records list.')
    channel=plain(corpus.get('channel',''))
    if not channel or len(channel)>100:raise ValueError('A channel name is required.')
    records=corpus['records']
    if not 1<=len(records)<=10000:raise ValueError('Import between 1 and 10,000 posts.')
    examples=[];audit=[];tags=collections.Counter();seen=set();ids=set()
    for row in records:
        if not isinstance(row,dict) or type(row.get('id')) is not int or row['id'] in ids:
            raise ValueError('Each imported post needs a unique integer id.')
        ids.add(row['id'])
        if not all(isinstance(row.get(k),str) and row[k].strip() for k in ('title','description')):
            raise ValueError('Each imported post needs a title and description.')
        title=plain(row['title']);desc=description_reference(row['description'])
        if len(title)>2000 or len(row['description'])>20000:raise ValueError('An example is too large.')
        headline=plain(TAG.sub('',title)).strip(' #')
        reasons=[]
        if re.match(r'^["“]',desc) and len(words(desc))>45:reasons.append('copied_speech_description')
        if re.match(r'(?i)^(?:the clip discusses|the speaker|latest from)',desc):reasons.append('generic_description')
        title_years=set(re.findall(r'\b20\d{2}\b',headline))
        desc_years=set(re.findall(r'\b20\d{2}\b',desc))
        if title_years and desc_years and title_years.isdisjoint(desc_years):reasons.append('inconsistent_year')
        if 'overtime win' in headline.casefold() and 'decide to tie' in desc.casefold():reasons.append('inconsistent_outcome')
        if len(words(desc))<5:reasons.append('insufficient_description')
        if len(desc)>450:reasons.append('long_description')
        if len(headline)>140:reasons.append('long_headline')
        key=(headline.casefold(),desc.casefold())
        if key in seen:reasons.append('duplicate_example')
        seen.add(key)
        audit.append(dict(id=row['id'],excluded_reasons=reasons))
        if reasons:continue
        clean_tags=[]
        for tag in TAG.findall(title):
            body=tag[1:].casefold()
            if body not in IGNORED_TAGS and body not in {t[1:].casefold() for t in clean_tags}:
                clean_tags.append(tag);tags[body]+=1
        examples.append(dict(id=row['id'],headline=headline,description=desc,hashtags=clean_tags[:8]))
    if not examples:raise ValueError('No usable title/description references were found.')
    body=dict(version=VERSION,channel=channel,total_posts=len(records),examples=examples,audit=audit,
              hashtag_counts=dict(tags.most_common()),source_name=plain(corpus.get('source_name','')),
              source_sha256=corpus.get('source_sha256',''),source_date=corpus.get('source_date',''),
              corpus_sha256=hashlib.sha256(json.dumps(corpus,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
              method='Local example retrieval. No model weight changes or performance-based training.')
    body['fingerprint']=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    return body


def import_corpus(corpus, path=PROFILE):
    profile=build_profile(corpus)
    path=Path(path)
    # Archive every original pair, even excluded/duplicate entries, without replacement.
    archive=path.parent/('corpus-'+profile['fingerprint']+'.json')
    if not archive.exists():write(archive,corpus)
    write(path,profile)
    return profile


def load(path=PROFILE):
    path=Path(path)
    try:
        if path.stat().st_size>8*1024*1024:return {}
    except OSError:return {}
    data=read(path,{})
    if (not isinstance(data,dict) or data.get('version')!=VERSION or
            not isinstance(data.get('examples'),list) or not data.get('fingerprint')):return {}
    # Verify content provenance and bounded fields before supplying any examples.
    try:
        body={k:v for k,v in data.items() if k!='fingerprint'}
        expected=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        if data['fingerprint']!=expected:return {}
        if not isinstance(data['channel'],str) or not 1<=len(data['channel'])<=100:return {}
        if type(data['total_posts']) is not int or not 1<=data['total_posts']<=10000:return {}
        if not 1<=len(data['examples'])<=data['total_posts']:return {}
        ids=set()
        for example in data['examples']:
            if type(example['id']) is not int or example['id'] in ids:return {}
            ids.add(example['id'])
            for name,limit in (('headline',140),('description',450)):
                if not isinstance(example[name],str) or not 1<=len(example[name])<=limit:return {}
            if not isinstance(example['hashtags'],list) or len(example['hashtags'])>8:return {}
            if any(not isinstance(t,str) or not re.fullmatch(r'#[\w]+',t) for t in example['hashtags']):return {}
    except (KeyError,TypeError,ValueError):return {}
    return data


def context(text, profile=None):
    profile=load() if profile is None else profile
    if not profile:return {}
    examples=profile['examples']
    query=set(words(text))-COMMON
    frequency=collections.Counter(t for e in examples for t in set(words(e['headline']+' '+e['description']))-COMMON)
    def score(example):
        terms=set(words(example['headline']+' '+example['description']))-COMMON
        return sum(math.log(1+len(examples)/(1+frequency[t])) for t in query & terms)
    ranked=sorted(examples,key=lambda e:(-score(e),e['id']))
    best=score(ranked[0])
    selected=[];seen=set()
    for example in ranked:
        shared=query & (set(words(example['headline']+' '+example['description']))-COMMON)
        if score(example)<=0 or score(example)<.6*best or len(shared)<2:continue
        headline=example['headline'].casefold()
        if headline in seen:continue
        seen.add(headline)
        # Prompt examples show good tag placement using only relevant historical tags.
        tags=[t for t in example['hashtags'] if supported_tag(t,example['headline']+' '+example['description'])]
        selected.append(dict(id=example['id'],headline=example['headline'],description=example['description'],hashtags=tags[:2]))
        if len(selected)==3:break
    return dict(channel=profile['channel'],fingerprint=profile['fingerprint'],total_posts=profile['total_posts'],
                eligible_examples=len(examples),examples=selected)


def suggested_tags(text, style):
    tags=[]
    for example in style.get('examples',[]):
        for tag in example.get('hashtags',[]):
            if supported_tag(tag,text) and tag.casefold() not in {t.casefold() for t in tags}:tags.append(tag)
    for tag in TOPICS:
        if supported_tag(tag,text) and tag.casefold() not in {t.casefold() for t in tags}:tags.append(tag)
    return tags


def provenance(style):
    if not style:return {}
    return dict(channel=style['channel'],fingerprint=style['fingerprint'],total_posts=style['total_posts'],
                example_ids=[e['id'] for e in style['examples']])
