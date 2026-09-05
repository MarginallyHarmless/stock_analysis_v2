"""Compile reviewed translations into a standalone, state-preserving report switch."""
import copy,html,json,re
from html.parser import HTMLParser

FIELDS={'label','text','explanation','note','basis','period','unit','formula','result','description','financial_period','horizon','subtitle','industry','share_class','currency','session'}
PROTECTED={'translations','sources','library','raw_value','id','source_ids','evidence_ids','inputs','operation','key','url','file','observed_at','prepared_at','as_of','freshness_checked_at','checked_at','topic','status','kind','quote_evidence_id','exchange','ticker','related_section','section_id'}

def required_strings(data):
    values=set()
    def walk(obj,key=''):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k not in PROTECTED:walk(v,k)
        elif isinstance(obj,list):
            for v in obj:walk(v,key)
        elif isinstance(obj,str) and key in FIELDS:values.add(obj)
    walk(data)
    for e in data['evidence']:
        if e.get('raw_value') is None:values.add(e['display'])
    for c in data.get('charts',[]):values.add(c['title'])
    for s in data['scenarios']:values.add(s['name'])
    return {value for value in values if value.strip() and not re.fullmatch(r'[\d\s.,%+−–-]+',value)}

def localized(data,language):
    default=data['report']['language']
    if language==default:return data
    translations=data.get('translations',{})
    if not isinstance(translations,dict) or not isinstance(translations.get(language,{}),dict):
        raise ValueError('Translations must contain language objects')
    strings=translations.get(language,{}).get('strings',{})
    if not isinstance(strings,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in strings.items()):
        raise ValueError('Translation strings must map text to text')
    missing=required_strings(data)-strings.keys()
    if missing:raise ValueError(f'{language}: {len(missing)} translations missing; first: '+sorted(missing)[0])
    def walk(obj,key=''):
        if key in PROTECTED:return copy.deepcopy(obj)
        if isinstance(obj,dict):return {k:walk(v,k) for k,v in obj.items()}
        if isinstance(obj,list):return [walk(v,key) for v in obj]
        return strings.get(obj,obj) if isinstance(obj,str) else obj
    result=walk(data);result['report']['language']=language
    return result

class Tokens(HTMLParser):
    def __init__(self,markup):
        super().__init__(convert_charrefs=True);self.tokens=[];self.feed(markup)
    def handle_starttag(self,t,a):self.tokens.append(('start',t,a))
    def handle_startendtag(self,t,a):self.tokens.append(('void',t,a))
    def handle_endtag(self,t):self.tokens.append(('end',t))
    def handle_data(self,s):self.tokens.append(('data',s))
    def handle_comment(self,s):self.tokens.append(('comment',s))
    def handle_decl(self,s):self.tokens.append(('decl',s))

def bilingual(pages,default,script,css):
    parsed={lang:Tokens(page).tokens for lang,page in pages.items()}
    en,ro=parsed['en'],parsed['ro']
    if len(en)!=len(ro):raise ValueError('Language versions have different document structures')
    dictionaries={'en':{},'ro':{}};keys={}
    def key(a,b):
        pair=(a,b)
        if pair not in keys:
            k='t'+str(len(keys));keys[pair]=k;dictionaries['en'][k]=a;dictionaries['ro'][k]=b
        return keys[pair]
    output=[];stack=[]
    for index,(a,b) in enumerate(zip(en,ro)):
        if a[0]!=b[0] or (a[0] in ('start','end','void') and a[1]!=b[1]):raise ValueError('Language token mismatch')
        current=a if default=='en' else b
        if a[0] in ('start','void'):
            tag=a[1];attrs=dict(current[2]);left,right=dict(a[2]),dict(b[2]);translated={}
            for attr in left.keys()|right.keys():
                if left.get(attr)!=right.get(attr) and attr!='lang':
                    if attr not in {'aria-label','title','placeholder','data-preview','data-open-label','data-close-label'}:raise ValueError('Translation changed protected HTML attribute: '+attr)
                    translated[attr]=key(left.get(attr,''),right.get(attr,''))
            if translated:attrs['data-i18n-attrs']=json.dumps(translated,separators=(',',':'))
            if tag in {'option','title','text'} and index+1<len(en) and en[index+1][0]=='data' and en[index+1]!=ro[index+1]:
                attrs['data-i18n']=key(en[index+1][1],ro[index+1][1])
            output.append('<'+tag+''.join(' '+k+('="'+html.escape(v,quote=True)+'"' if v is not None else '') for k,v in attrs.items())+('/>' if a[0]=='void' else '>'))
            if a[0]=='start' and tag not in {'meta','link','input','br','hr','img','wbr','source'}:stack.append(tag)
        elif a[0]=='end':
            output.append('</'+a[1]+'>')
            if stack and stack[-1]==a[1]:stack.pop()
        elif a[0]=='data':
            if stack and stack[-1] in {'script','style'}:
                if a!=b:raise ValueError('Executable/style content differs across languages')
                output.append(current[1])
            elif a!=b and (not stack or stack[-1] not in {'option','title','text'}):
                output.append('<span data-i18n="'+key(a[1],b[1])+'">'+html.escape(current[1])+'</span>')
            else:output.append(html.escape(current[1]))
        elif a[0]=='comment':output.append('<!--'+current[1]+'-->')
        elif a[0]=='decl':output.append('<!'+current[1]+'>')
    result=''.join(output)
    switch='<div class="language-switch" role="group" aria-label="Language / Limbă" hidden><button type="button" data-language="en" lang="en" aria-label="English">EN</button><button type="button" data-language="ro" lang="ro" aria-label="Română">RO</button></div>'
    result=result.replace('<div class="topbar">','<div class="topbar">'+switch,1)
    payload=json.dumps(dictionaries,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    # Controller runs after existing report initialization and never replaces the document.
    return result.replace('</style>','\n'+css+'</style>',1).replace('</body>','<script id="report-translations" type="application/json">'+payload+'</script><script>'+script+'</script></body>',1)
