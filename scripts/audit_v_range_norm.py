"""Offline reproducible audit; no user data, network, runtime logging or DB.
Run from repository root: python scripts/audit_v_range_norm.py > report.json
"""
import ast
import hashlib
import json
import random
import statistics
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dark_horse_engine_v2 import DarkHorseEngineV2

BASE = '45e61bc5ed0f83a69ec36aff9de7a24a1ce45b90'


def shadow_s(answers, weights):
    terms = [(row[a] - min(row)) / (max(row) - min(row))
             for a, row in zip(answers, weights)
             if 0 <= a < len(row) and max(row) > min(row)]
    return statistics.mean(terms) if terms else None


def main():
    module = types.ModuleType('baseline_engine')
    exec(compile(subprocess.check_output(['git', 'show', BASE + ':dark_horse_engine_v2.py'], text=True), 'baseline_engine', 'exec'), module.__dict__)
    old, new = module.DarkHorseEngineV2(), DarkHorseEngineV2()
    old_source = subprocess.check_output(['git','show',BASE+':dark_horse_engine_v2.py'], text=True)
    new_source = (ROOT/'dark_horse_engine_v2.py').read_text()
    def implementation(source, name):
        return next(ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(source))
                    if isinstance(n, ast.FunctionDef) and n.name == name)

    # S remains an exact AST match to the pinned BASE implementation.
    assert implementation(old_source, '_compute_s_score') == implementation(new_source, '_compute_s_score'), '_compute_s_score changed'

    # Branch M is intentionally changed: lock its approved fixed-30 expression.
    branch_m = next(n for n in ast.walk(ast.parse(new_source))
                    if isinstance(n, ast.FunctionDef) and n.name == '_compute_branch_m_score')
    score_values = [ast.dump(n.value, include_attributes=False)
                    for n in ast.walk(branch_m)
                    if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'score' for t in n.targets)]
    expected_score = ast.dump(ast.parse('len(matched) / 30.0', mode='eval').body,
                              include_attributes=False)
    expected_return = ast.dump(ast.parse('min(1.0, score)', mode='eval').body,
                               include_attributes=False)
    branch_returns = [ast.dump(n.value, include_attributes=False)
                      for n in ast.walk(branch_m) if isinstance(n, ast.Return)]
    assert score_values == [expected_score] and expected_return in branch_returns, (
        '_compute_branch_m_score must use min(1, k / 30)'
    )

    profiles = [(str(k), m) for k, m in new.majors_db.items() if m.get('motive_driven') is not False]
    profiles += [('branch:' + k, m) for k, m in new.school_branches.items()]
    rng = random.Random(420)
    report = {'baseline_sha': BASE, 'version': new._v_method(), 'profiles': [], 'fixtures': [], 'ms_parity': True, 'database_identity': []}
    for filename in ('majors_database_v2.json', 'school_branches_v2.json'):
        current = (ROOT / filename).read_bytes()
        base = subprocess.check_output(['git', 'show', BASE + ':' + filename])
        payload = json.loads(current)
        report['database_identity'].append({'file': filename, 'length': len(payload),
            'md5_current': hashlib.md5(current).hexdigest(), 'md5_baseline': hashlib.md5(base).hexdigest(),
            'sha256_current': hashlib.sha256(current).hexdigest(), 'sha256_baseline': hashlib.sha256(base).hexdigest(),
            'byte_identical': current == base})
    report['major_counts'] = {'catalog': len(new.majors_db), 'active': len(profiles)-4,
        'excluded': sum(m.get('motive_driven') is False for m in new.majors_db.values()),
        'active_161_230': sum(int(k)>=161 and m.get('motive_driven') is not False for k,m in new.majors_db.items())}
    old_ms, new_ms = [], []
    for key, m in profiles:
        w = m['value_weights']
        draws = [[f'Q{i}{rng.choice("AB")}' for i in range(1, 16)] for _ in range(200)]
        before = [old._compute_v_score(c, w)[0] for c in draws]
        after = [new._compute_v_score(c, w)[0] for c in draws]
        # Exact Bernoulli expectation/std (fixed answered set; independent fair choices).
        spans = [round(abs(w[f'Q{i}A']-w[f'Q{i}B']), 12) for i in range(1,16)]
        spans = [d for d in spans if d >= new.V_EPSILON]
        report['profiles'].append({'id': key, 'name': m['name'],
            'before_mean': statistics.mean(before), 'after_mean': statistics.mean(after),
            'after_std_sample': statistics.pstdev(after), 'after_exact_mean': .5,
            'after_exact_std': (.25*sum(d*d for d in spans))**.5/sum(spans),
            'after_min': 0, 'after_max': 1,
            'all_a': new._compute_v_score([f'Q{i}A' for i in range(1,16)],w)[0],
            'all_b': new._compute_v_score([f'Q{i}B' for i in range(1,16)],w)[0]})
    active = [m for m in new.majors_db.values() if m.get('motive_driven') is not False]
    fixtures = [(seed, label, 'random', None) for seed, label in enumerate(
        ('sara_synthetic','ali_synthetic','hossein_synthetic','zahra_synthetic','random_1','random_2'))]
    fixtures += [(101, 'pole_a_biotech', 'A', 34), (102, 'pole_b_biotech', 'B', 93),
        (103, 'pole_a_computer', 'A', 42), (104, 'pole_b_software', 'B', 44),
        (105, 'balanced_it', 'balanced', 43), (106, 'balanced_computer_science', 'balanced', 45),
        (107, 'balanced_biotech', 'balanced', 169), (108, 'balanced_graphic', 'balanced', 140),
        (109, 'sensitive_biotech', 'random', 34), (110, 'sensitive_software', 'random', 44),
        (111, 'sensitive_it', 'random', 43), (112, 'unanswered_v', 'empty', 140)]
    for seed, label, mode, target_id in fixtures:
        r = random.Random(seed)
        target = next((m for m in active if m['id'] == target_id), active[(seed*37) % len(active)])
        motives = list(target['micro_motive_codes'])
        motives += [c for m in r.sample(active, 3) for c in m['micro_motive_codes'][:2]]
        answers = [r.randrange(5) for _ in range(25)]
        choices = [f'Q{i}{r.choice("AB")}' for i in range(1,16)]
        if mode in ('A', 'B'):
            choices = [f'Q{i}{mode}' for i in range(1,16)]
        elif mode == 'balanced':
            choices = [f'Q{i}' + ('A' if (i + seed) % 2 else 'B') for i in range(1,16)]
        elif mode == 'empty':
            choices = []
        rows = []
        shadow = []
        for key,m in profiles:
            mf = '_compute_branch_m_score' if key.startswith('branch:') else '_compute_m_score'
            bm = getattr(old,mf)(motives,m)[0]; nm = getattr(new,mf)(motives,m)[0]
            bs = old._compute_s_score(answers,m['strategy_weights'])[0]
            ns = new._compute_s_score(answers,m['strategy_weights'])[0]
            old_ms.append((key,bm,bs)); new_ms.append((key,nm,ns))
            if key.startswith('branch:'):
                continue
            bv=old._compute_v_score(choices,m['value_weights'])[0]
            nv=new._compute_v_score(choices,m['value_weights'])[0]
            before=round(100*(.55*bm+.15*bs+.30*bv),1)
            after=round(100*(.55*nm+.15*ns+.30*nv),1) if nv is not None else None
            rows.append({'id':key,'name':m['name'],'m':nm,'s':ns,'m_before':bm,'m_after':nm,'s_before':bs,'s_after':ns,'v_before':bv,'v_after':nv,
                'v_coverage':new._compute_v_result(choices,m['value_weights'])['coverage'],
                'before':before,'after':after,
                'cross_down': after is not None and before >= 30 and after < 30,
                'cross_up': after is not None and before < 30 and after >= 30,
                'null': nv is None})
            shadow.append({'id':key,'s_live':ns,'s_range_shadow':shadow_s(answers,m['strategy_weights'])})
        selected=lambda field: sorted([x for x in rows if x['m']>=.15 and x[field] is not None and x[field]>=30],key=lambda x:x[field],reverse=True)
        br,ar=selected('before'),selected('after')
        old_ids={x['id'] for x in br}; new_ids={x['id'] for x in ar}
        report['fixtures'].append({'label':label,'seed':seed,'synthetic':True, 'mode':mode,
            'focus_major_id': '140' if label == 'zahra_synthetic' else str(target['id']),
            'inputs': {'motives':motives,'strategy_answers':answers,'value_choices':choices},
            'all_major_rows': rows,
            'counts': {'delta_v_gt20':sum(x['v_after'] is not None and abs(x['v_after']-x['v_before'])>.20 for x in rows),
                       'cross_down':sum(x['cross_down'] for x in rows), 'cross_up':sum(x['cross_up'] for x in rows),
                       'eligible_cross_down':sum(x['cross_down'] and x['m']>=.15 for x in rows),
                       'eligible_cross_up':sum(x['cross_up'] and x['m']>=.15 for x in rows),
                       'null':sum(x['null'] for x in rows)},
            'before_top5':br[:5],'after_top5':ar[:5],
            'removed':sorted(old_ids-new_ids),'added':sorted(new_ids-old_ids),
            'removed_details':[x for x in rows if x['id'] in old_ids-new_ids],
            'threshold_counts': {str(t): {'before':sum(x['before']>=t and x['m']>=.15 for x in rows),
                                        'after':sum(x['after'] is not None and x['after']>=t and x['m']>=.15 for x in rows)} for t in (30,40,60,80)},
            's_shadow':shadow})
    rows = [x for f in report['fixtures'] for x in f['all_major_rows']]
    report['aggregate_counts'] = {k: sum(f['counts'][k] for f in report['fixtures']) for k in report['fixtures'][0]['counts']}
    report['unique_majors_delta_v_gt20'] = len({x['id'] for x in rows if x['v_after'] is not None and abs(x['v_after']-x['v_before'])>.20})
    report['fixture_count'] = len(report['fixtures'])
    digest=lambda x: hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
    report['ms_before_sha256']=digest(old_ms)
    report['ms_after_sha256']=digest(new_ms)
    report['ms_parity']=old_ms==new_ms
    assert report['ms_parity'], 'M/S parity failed'
    report['reference_weights_unchanged'] = not subprocess.check_output(['git','diff',BASE,'--','majors_database_v2.json','school_branches_v2.json']).strip()
    assert report['reference_weights_unchanged']
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
