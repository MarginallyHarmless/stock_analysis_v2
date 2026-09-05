"""Two reading levels share one immutable financial evidence ledger."""
from html import escape

def validate_audience(data):
    if 'audience' not in data:return []
    errors=[];a=data['audience']
    if not isinstance(a,dict):return ['audience must be an object']
    if a.get('default') not in ('beginner','experienced'):errors.append('Invalid audience.default')
    versions=a.get('versions',{})
    if set(versions)!= {'en','ro'}:return errors+['Audience guides require reviewed en and ro versions']
    eids={e['id'] for e in data['evidence']}
    records={e['id']:e for e in data['evidence']}
    first=[records.get(s.get('results',[None])[0],{}) for s in data['scenarios']]
    if len({tuple(e.get(k) for k in ('label','period','unit')) for e in first})!=1:
        errors.append('Audience scenario cards need comparable first results with matching measure, period and unit')
    checks={c['id'] for s in data['sections'] for c in s['checks']}|{c['id'] for c in data['optional']}
    sections={s['id'] for s in data['sections']}
    for lang,g in versions.items():
        if not isinstance(g,dict):errors.append(lang+': invalid audience guide');continue
        if set(g.get('sections',{}))!=sections:errors.append(lang+': guide needs all sections')
        if set(g.get('checks',{}))!=checks:errors.append(lang+': guide needs all checklist items')
        if set(g.get('scenarios',{}))!={'bear','base','bull'}:errors.append(lang+': guide needs all scenarios')
        for field in ('orientation','summary','peers','glossary','highlights'):
            if not isinstance(g.get(field),list) or not g[field]:errors.append(lang+': missing '+field)
        for eid in g.get('highlights',[]):
            if eid not in eids or eid not in g.get('metrics',{}):errors.append(lang+': invalid explained highlight '+str(eid))
        def walk(obj):
            if isinstance(obj,dict):
                if 'text' in obj and not obj['text']:errors.append(lang+': empty guide text')
                if 'text' in obj and 'evidence_ids' not in obj:errors.append(lang+': guide clauses require evidence_ids (empty for instruction/definition)')
                for eid in obj.get('evidence_ids',[]):
                    if eid not in eids:errors.append(lang+': unknown guide evidence '+str(eid))
                for v in obj.values():walk(v)
            elif isinstance(obj,list):
                for v in obj:walk(v)
        walk(g)
    # Same semantic items and layout must survive either independent switch.
    left,right=versions['en'],versions['ro']
    for key in ('orientation','summary','peers','glossary'):
        if len(left.get(key,[]))!=len(right.get(key,[])):errors.append('Audience language structure differs: '+key)
    if left.get('highlights')!=right.get('highlights'):errors.append('Audience highlights must match across languages')
    for group in ('checks','sections','scenarios','metrics'):
        if set(left.get(group,{}))!=set(right.get(group,{})):errors.append('Audience language keys differ: '+group)
        for k in set(left.get(group,{}))&set(right.get(group,{})):
            if left[group][k].get('evidence_ids',[])!=right[group][k].get('evidence_ids',[]):errors.append('Audience references differ across languages: '+k)
    return errors

class Presentation:
    def __init__(self,data,lang,clause,refs):
        self.guide=data.get('audience',{}).get('versions',{}).get(lang)
        self.default=data.get('audience',{}).get('default','beginner')
        self.lang=lang;self.clause=clause;self.refs=refs
    def pair(self,beginner,experienced,inline=False):
        if not self.guide:return experienced
        tag='span' if inline else 'div'
        return f'<{tag} class="audience-beginner">{beginner}</{tag}><{tag} class="audience-experienced">{experienced}</{tag}>'
    def controls(self):
        if not self.guide:return ''
        en=self.lang=='en'
        return '<div class="audience-switch" role="group" aria-label="'+('Reading level' if en else 'Nivel de lectură')+'" data-default="'+self.default+'" hidden><button type="button" data-audience-choice="beginner">'+('Beginner' if en else 'Începător')+'</button><button type="button" data-audience-choice="experienced">'+('Experienced' if en else 'Experimentat')+'</button></div>'
    def orientation(self):
        if not self.guide:return ''
        title='How to use this report' if self.lang=='en' else 'Cum folosești acest raport'
        glossary='Terms explained' if self.lang=='en' else 'Termeni explicați'
        content='<aside class="reader-guide"><h2>'+title+'</h2>'+''.join(self.clause(c) for c in self.guide['orientation'])+'</aside>'
        content+='<details class="reader-glossary"><summary>'+glossary+'</summary><dl>'+''.join('<div><dt>'+escape(c['label'])+'</dt><dd>'+self.clause(c)+'</dd></div>' for c in self.guide['glossary'])+'</dl></details>'
        return self.pair(content,'')
