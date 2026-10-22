#!/usr/bin/env python3
"""Durable finite completion queue. Default is read-only dry-run; --prepare never runs jobs.

Review the prepared manifest before --execute. No API, SSH, publication, service
control, conditional per-temperature fits, profiles, or rescue fits are performed.
An exclusive lock and immutable plan snapshots make interrupted execution resumable.
"""
from __future__ import annotations
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from nernstwork.data import sha256_json
from nernstwork.evaluate import code_identity
from nernstwork.store import FitCache, atomic_write_json, now
from plan_chapman_li_followups import build, coverage
from summarize_chapman_li_sensitivity import collect

CAMPAIGN = ROOT/'data/derived/chapman_li_sensitivity'
RUN = ROOT/'investigations/runs/chapman-li-oct22-opus1'
SERVICES = {
    'lower': 'nernstwork-li-lower-oct22.service',
    'lower_boost': 'nernstwork-li-lower-boost-oct22.service',
    'fresh_final': 'nernstwork-li-fresh-final-oct22.service',
    'extraction': 'nernstwork-li-extraction-local-oct22.service',
    's1_sync': 'nernstwork-li-s1-sync-oct22.service',
}
PINNED = [Path(__file__), ROOT/'scripts/run_chapman_li_sensitivity.py',
          ROOT/'scripts/plan_chapman_li_followups.py', ROOT/'scripts/export_chapman_fresh_candidates.py',
          ROOT/'scripts/check_chapman_sensitivity_numerics.py', ROOT/'scripts/chapman_initial_amount_adapter.py',
          ROOT/'scripts/summarize_chapman_li_sensitivity.py', ROOT/'scripts/audit_chapman_physics.py',
          ROOT/'src/nernstwork/investigation.py',
          ROOT/'configs/protocols/synthesis-mle-v1.json', CAMPAIGN/'input_manifest.json',
          CAMPAIGN/'repaired_records.json', CAMPAIGN/'comparable_records.json',
          ROOT/'investigations/runs/chapman750-propose_space-opus1/final/chapman2023_fig2_750C/predictions.json']
PROPERTIES = ['Id','LoadState','ActiveState','SubState','Result','ExecMainCode','ExecMainStatus',
              'MainPID','InvocationID','CollectMode','ExecStart','ExecMainStartTimestamp']


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def immutable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read(path) != body:
            raise ValueError(f'Immutable queue artifact differs: {path}')
        return
    # Atomic create-only, including a crash between write and publication.
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    atomic_write_json(temporary, body)
    try:
        os.link(temporary, path)
    except FileExistsError:
        if read(path) != body:
            raise ValueError(f'Concurrent immutable artifact differs: {path}')
    finally:
        temporary.unlink(missing_ok=True)


def service(name):
    raw = subprocess.check_output(['systemctl','--user','show',name,*[f'--property={p}' for p in PROPERTIES]], text=True)
    result = dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
    pid = result.get('MainPID','0')
    if pid != '0':
        try:
            result['log_path'] = str(Path(f'/proc/{pid}/fd/1').resolve(strict=True))
            result['log_bytes_at_capture'] = Path(result['log_path']).stat().st_size
        except FileNotFoundError:
            pass
    return result


def cost():
    path = RUN/'pi/usage.json'
    body = read(path)
    value = body['cost_usd']
    if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError(f'API cost estimate is outside the authorized $10 envelope: {value}')
    return {'estimated_usd':value,'authorized_usd':10,'new_api_calls_by_queue':0,
            'source':relative(path),'sha256':digest(path),'cost_note':body.get('cost_note')}


def result_hashes():
    return {relative(p):digest(p) for p in sorted((CAMPAIGN/'results').glob('*/*.json'))}


def verify_preserved(hashes):
    for name, expected in hashes.items():
        if not (ROOT/name).is_file() or digest(ROOT/name) != expected:
            raise ValueError(f'Protected primary/imported artifact changed: {name}')


def protected_remote():
    hashes = {}
    for path in sorted((CAMPAIGN/'remote').glob('*/imports/*/remote_snapshot.json')):
        snapshot = read(path)
        for name, info in snapshot['files'].items():
            local = ROOT/name
            if local.is_file():
                value = digest(local)
                if value != info['sha256']:
                    raise ValueError(f'Imported artifact differs from remote snapshot: {name}')
                hashes[name] = value
    return hashes


def log_objects(path):
    # Runner lines are compact JSON; other pretty-printed summaries are ignored.
    lines = Path(path).read_text(errors='replace').splitlines()
    objects = []
    for line in lines:
        try:
            value = json.loads(line)
            if isinstance(value,dict): objects.append(value)
        except json.JSONDecodeError:
            continue
    return lines, objects


def completion_marker(label, captured):
    path = captured.get('log_path')
    if not path or not Path(path).is_file():
        return None
    if Path(path).stat().st_size <= captured.get('log_bytes_at_capture', -1):
        return None
    lines, objects = log_objects(path)
    if label == 'fresh_final':
        valid = bool(lines and lines[-1].startswith('Fresh standard final evaluation and campaign materialization finished.'))
    elif label == 's1_sync':
        manifests = sorted((CAMPAIGN/'remote').glob('*/launch_manifest.json'))
        valid = False
        for manifest_path in manifests:
            manifest = read(manifest_path)
            imports = sorted(manifest_path.parent.glob('imports/*/import.json'))
            for imported in reversed(imports):
                row = read(imported)
                if row['manifest_sha256'] == digest(manifest_path):
                    valid = row['result_records'] == 2*len(manifest['remote_dynamics']) and all(
                        (CAMPAIGN/'results'/f'{scenario}__fixed'/f'{dh}.json').is_file()
                        for scenario in ('s1_nominal','s1_lower') for dh in manifest['remote_dynamics'])
                    break
            if valid: break
    else:
        starts = [r for r in objects if 'started' in r and 'jobs' in r]
        finishes = [r for r in objects if 'finished' in r and 'counts' in r]
        scenario = 's1_lower' if label == 'extraction' else 'fig2_lower'
        valid = bool(starts and finishes and starts[-1]['scenario'] == scenario
                     and sum(finishes[-1]['counts'].values()) == starts[-1]['jobs']
                     and finishes[-1]['finished'] >= starts[-1]['started'])
    return {'path':path,'sha256':digest(path),'terminal_marker_verified':True} if valid else None


def dependency_classification(current, captured, marker, journal=None):
    """Pure decision logic. Unknown units never pass on default Result=success."""
    if current.get('InvocationID') and current['InvocationID'] != captured.get('InvocationID'):
        return 'changed_invocation'
    if current.get('ActiveState') in ('active','activating','deactivating','reloading'):
        if current.get('InvocationID') != captured.get('InvocationID'):
            return 'changed_invocation'
        return 'waiting'
    if current.get('ActiveState') == 'failed' or current.get('Result','success') != 'success' or current.get('ExecMainStatus','0') != '0':
        return 'failed'
    if not marker:
        return 'missing_completion_evidence'
    if current.get('LoadState') == 'loaded' and current.get('ActiveState') == 'inactive':
        return 'success_loaded'
    if current.get('LoadState') == 'not-found':
        # CollectMode=inactive retains failed units. Require a captured real
        # invocation, terminal work evidence, and its later accounting record.
        if not captured.get('InvocationID') or captured.get('CollectMode') != 'inactive':
            return 'unknown_unit'
        if journal and journal.get('accounting_after_capture') and not journal.get('failure_messages'):
            return 'success_collected_with_evidence'
    return 'missing_completion_evidence'


def journal_evidence(name, prepared_at):
    since = datetime.fromisoformat(prepared_at.replace('Z','+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC')
    raw = subprocess.check_output(['journalctl','--user','-u',name,'--since',since,'-o','json','--no-pager'],text=True)
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    failures = [r.get('MESSAGE','') for r in rows if 'Failed with result' in r.get('MESSAGE','')
                or 'Main process exited, code=' in r.get('MESSAGE','')]
    return {'sha256':hashlib.sha256(raw.encode()).hexdigest(),'rows':rows,
            'accounting_after_capture':any(r.get('MESSAGE_ID')=='ae8f7b866b0347b9af31fe1c80b127c0' for r in rows),
            'failure_messages':failures}


def active_cache_owners():
    found = []
    cache = FitCache(ROOT/'investigations')
    for directory in cache.root.iterdir():
        if directory.is_dir():
            live = cache.live_attempt(directory.name)
            if live: found.append({'fit_key':directory.name,'attempt':live['attempt_id'],'pid':live['pid']})
    return found


def pending_records(targets, scenario, mode):
    return [r for r in targets if not (CAMPAIGN/'results'/f'{scenario}__{mode}'/f"{r['dynamics_hash']}.json").exists()]


def plan_snapshot(queue, name):
    path = queue/'plans'/f'{name}.json'
    if path.exists():
        saved=read(path)
        if saved['plan_sha256'] != sha256_json(saved['plan']) or saved['lists_sha256'] != {k:sha256_json(v) for k,v in saved['lists'].items()}:
            raise ValueError(f'Frozen plan failed its content-hash check: {path}')
        return saved
    plan, lists = build(CAMPAIGN,CAMPAIGN)
    if plan['audit_problems'] or plan['warnings'] or plan['fresh']['provisional']:
        raise ValueError('Planner requires reconciliation before scheduling: '+json.dumps({
            'warnings':plan['warnings'],'audit_problems':plan['audit_problems'],'fresh':plan['fresh']}))
    if not plan['primary_coverage']['fig2_nominal__fixed']['all_outcomes_recorded']:
        raise ValueError('Historical nominal coverage unexpectedly incomplete; scientist review required')
    body = {'created_at':now(),'plan':plan,'lists':lists,'plan_sha256':sha256_json(plan),
            'lists_sha256':{k:sha256_json(v) for k,v in lists.items()}}
    immutable(path,body)
    return body


class Queue:
    def __init__(self, directory, manifest, workers):
        self.directory,self.manifest,self.workers = directory,manifest,workers
        self.path = directory/'state.json'
        self.state = read(self.path) if self.path.exists() else {'created_at':now(),'phase':'waiting','attempts':[], 'completed_stages':[]}

    def save(self, **changes):
        self.state.update(changes,updated_at=now())
        atomic_write_json(self.path,self.state)

    def check(self):
        verify_preserved(self.manifest['pinned_sources'])
        if code_identity()['sha256'] != self.manifest['engine_sha256']:
            raise ValueError('Numerical engine changed since queue preparation')
        verify_preserved(self.state.get('protected_artifacts',{}))
        return cost()

    def wait_dependencies(self, poll):
        if not self.state.get('dependency_capture'):
            captured={label:service(name) for label,name in self.manifest['services'].items()}
            if any(not d.get('InvocationID') or not d.get('log_path') for d in captured.values()):
                raise ValueError('Launch needs identifiable dependency invocations/logs; an already unloaded unit requires explicit completion evidence and review')
            self.save(dependency_capture=captured,dependency_capture_at=now())
        while True:
            estimate=self.check(); observations={}; waiting=False
            for label,captured in self.state['dependency_capture'].items():
                previous=self.state.get('dependencies',{}).get(label,{})
                if previous.get('status','').startswith('success_'):
                    observations[label]=previous; continue
                current=service(captured['Id'])
                marker=completion_marker(label,captured) if current.get('ActiveState') not in ('active','activating','deactivating','reloading') else None
                journal=journal_evidence(captured['Id'],self.state['dependency_capture_at']) if current.get('LoadState')=='not-found' else None
                status=dependency_classification(current,captured,marker,journal)
                observations[label]={'status':status,'observed_at':now(),'service':current,'marker':marker,'journal':journal}
                waiting |= status=='waiting'
            self.save(dependencies=observations,api_cost=estimate)
            errors={k:v['status'] for k,v in observations.items() if v['status']!='waiting' and not v['status'].startswith('success_')}
            if errors: raise ValueError('Dependency requires review: '+json.dumps(errors))
            if not waiting: break
            print(json.dumps({'waiting_for':[k for k,v in observations.items() if v['status']=='waiting'],'at':now(),'api_cost':estimate['estimated_usd']}),flush=True)
            time.sleep(poll)
        if active_cache_owners(): raise ValueError('An untracked live cache owner remains after dependency completion')
        if not self.state.get('protected_artifacts'):
            self.save(protected_artifacts=result_hashes()|protected_remote())

    def command(self, label, arguments, skip_completed=True):
        if skip_completed and label in self.state['completed_stages']: return
        self.check()
        before=result_hashes()|protected_remote()
        self.state.setdefault('protected_artifacts',{}).update(before)
        attempt={'stage':label,'started_at':now(),'argv':[str(x) for x in arguments],
                 'source_sha256':{relative(p):digest(p) for p in [Path(arguments[1])] if p.is_file()}}
        number=len(self.state['attempts'])+1
        log=self.directory/'logs'/f'{number:03d}_{label}.log';log.parent.mkdir(parents=True,exist_ok=True)
        attempt['log']=relative(log);self.state['attempts'].append(attempt);self.save(phase=label)
        with log.open('xb') as output:
            child=subprocess.Popen([str(x) for x in arguments],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
            attempt['pid']=child.pid;self.save()
            code=child.wait()
        attempt.update(finished_at=now(),returncode=code,log_sha256=digest(log))
        verify_preserved(before)
        self.save(api_cost=cost())
        if code: raise RuntimeError(f'{label} exited {code}; see {log}')
        if label not in self.state['completed_stages']:
            self.state['completed_stages'].append(label)
        self.save()

    def fits(self,label,targets,scenario,mode):
        self.check()
        if active_cache_owners(): raise ValueError('Another cache owner is active; refusing concurrent completion work')
        missing=pending_records(targets,scenario,mode)
        if missing:
            # Attempt-specific subset; a restart may need only some old entries.
            path=self.directory/'records'/f'{label}_{sha256_json(missing)[:16]}.json'
            immutable(path,missing)
            invocation=f'{label}_{sha256_json(missing)[:16]}'
            self.command(invocation,[ROOT/'.venv/bin/python',ROOT/'scripts/run_chapman_li_sensitivity.py',
                '--records',path,'--scenario',scenario,'--mode',mode,'--workers',str(self.workers)],skip_completed=False)
        if pending_records(targets,scenario,mode):
            raise RuntimeError(f'{label} still has missing outcomes; rerun resumes only missing work')
        rows,problems,_,_,_=collect(CAMPAIGN)
        report=coverage(rows,{r['dynamics_hash'] for r in targets},scenario,mode)
        if not report['all_outcomes_recorded']:
            raise ValueError(f'{label} has invalid identities: {report}')
        self.state.setdefault('stage_coverage',{})[label]=report
        self.state['protected_artifacts'].update(result_hashes());self.save()

    def execute(self,poll):
        self.wait_dependencies(poll)
        if self.state.get('phase')=='complete': return
        if (self.directory/'completion.json').exists():
            saved=read(self.directory/'completion.json')
            if saved['queue_manifest_sha256'] != digest(self.directory/'manifest.json'):
                raise ValueError('Completion receipt belongs to another queue manifest')
            self.save(phase='complete',completion_sha256=digest(self.directory/'completion.json'))
            return
        python=ROOT/'.venv/bin/python'
        self.command('refresh_fresh_export',[python,ROOT/'scripts/export_chapman_fresh_candidates.py'])
        before=plan_snapshot(self.directory,'before_primary')
        self.state['protected_artifacts'][relative(self.directory/'plans/before_primary.json')]=digest(self.directory/'plans/before_primary.json')
        self.save(before_primary_sha256=digest(self.directory/'plans/before_primary.json'))
        self.fits('primary_lower',before['lists']['primary_lower_union_records'],'fig2_lower','fixed')
        self.command('score_closed_primary',[python,ROOT/'scripts/check_chapman_sensitivity_numerics.py'])
        # Exactly one replan after primary closure. Its lists never expand again.
        after=plan_snapshot(self.directory,'after_primary')
        if not after['plan']['primary_coverage']['fig2_lower__fixed']['all_outcomes_recorded']:
            raise ValueError('Primary lower union did not close before the final scheduling snapshot')
        self.state['protected_artifacts'][relative(self.directory/'plans/after_primary.json')]=digest(self.directory/'plans/after_primary.json')
        self.save(after_primary_sha256=digest(self.directory/'plans/after_primary.json'))
        for label,stem,scenario,mode in [
            ('fresh_nominal','fresh_selected_nominal_shortlist','fig2_nominal','fixed'),
            ('shared','initial_amount_shortlist','fig2_lower','shared'),
            ('s1_nominal','extraction_shortlist','s1_nominal','fixed'),
            ('s1_lower','extraction_shortlist','s1_lower','fixed')]:
            self.fits(label,after['lists'][stem],scenario,mode)
        self.command('score_final',[python,ROOT/'scripts/check_chapman_sensitivity_numerics.py'])
        self.command('physics_final',[python,ROOT/'scripts/audit_chapman_physics.py','--report',self.directory/'physics_report.md'])
        self.command('summary_final',[python,ROOT/'scripts/summarize_chapman_li_sensitivity.py',
            '--report',self.directory/'results_report.md','--figures',self.directory/'figures'])
        rows,problems,hashes,_,_=collect(CAMPAIGN)
        final_coverage={}
        for label,stem,scenario,mode in [
            ('primary_lower','primary_lower_union_records','fig2_lower','fixed'),
            ('fresh_nominal','fresh_selected_nominal_shortlist','fig2_nominal','fixed'),
            ('shared','initial_amount_shortlist','fig2_lower','shared'),
            ('s1_nominal','extraction_shortlist','s1_nominal','fixed'),
            ('s1_lower','extraction_shortlist','s1_lower','fixed')]:
            final_coverage[label]=coverage(rows,{r['dynamics_hash'] for r in after['lists'][stem]},scenario,mode)
        final_coverage['historical_nominal']=coverage(rows,{r['dynamics_hash'] for r in read(CAMPAIGN/'repaired_records.json')},'fig2_nominal','fixed')
        if not all(r['all_outcomes_recorded'] for r in final_coverage.values()):
            raise ValueError('Final coverage contains missing or invalid outcomes')
        report={'completed_at':now(),'queue_manifest_sha256':digest(self.directory/'manifest.json'),
                'plan_sha256':self.state['after_primary_sha256'],'api_cost':cost(),'coverage':final_coverage,
                'audit_problems':problems,'result_source_sha256':hashes,'dependency_evidence':self.state['dependencies'],
                'remaining_decisions':after['plan']['pending_interpretation_decisions']+[
                    'Per-temperature additions and likelihood profiles require scientist review; none were launched by this queue.',
                    'Numerical rescues remain separate decisions; recorded failures and optimizer warnings were not refitted.',
                    'Review physical and prediction audit exceptions before scientific interpretation or sharing.'],
                'rescue_triage_at_primary_closure':after['plan']['numerical_rescue_priorities'],
                'conditional_per_temperature_targets':after['plan']['planned_lists']['per_temperature_shortlist'],
                'conditional_per_temperature_coverage':coverage(rows,
                    {r['dynamics_hash'] for r in after['lists']['per_temperature_shortlist']},'fig2_lower','per_temperature'),
                'audit_artifacts':{relative(p):digest(p) for p in [
                    CAMPAIGN/'physics_audit/summary.json',CAMPAIGN/'summary/campaign_summary.json',
                    CAMPAIGN/'summary/profile_summary.json',self.directory/'physics_report.md',
                    self.directory/'results_report.md']},
                'completion_meaning':'All frozen prescribed condition outcomes are recorded, including bounded failures. This is not a claim that all fits/predictions succeeded or that the chemistry is validated.'}
        verify_preserved(self.state['protected_artifacts'])
        immutable(self.directory/'completion.json',report)
        lines=['# Chapman finite campaign completion', '', report['completion_meaning'], '',
               '| Condition | Required | Recorded | Fitted | Audited predictions |',
               '|---|---:|---:|---:|---:|']
        for name,row in final_coverage.items():
            lines.append(f"| {name} | {row['target_count']} | {row['result_files']} | {row['valid_fitted_results']} | {row['audited_predictions']} |")
        lines += ['',f"API cost estimate: ${report['api_cost']['estimated_usd']:.4f} of $10 authorized; this queue made no API calls.",
                  '', 'The exact target lists were frozen once after primary coverage closed. Recorded failures remain visible.',
                  'Separate-temperature additions, parameter profiles and optimizer rescues remain scientific review decisions.',
                  '', '[Completion receipt and source hashes](completion.json) · [Scientific results](results_report.md) · [Physics audit](physics_report.md)',
                  '', 'The completion receipt is the authority for the final expanded target coverage; legacy v1 follow-up tables in the scientific summary describe their original lists.']
        receipt=self.directory/'completion.md'
        if not receipt.exists():
            with receipt.open('x') as handle: handle.write('\n'.join(lines)+'\n')
        self.save(phase='complete',completion_sha256=digest(self.directory/'completion.json'),api_cost=report['api_cost'])


def prepare(directory,workers):
    if (directory/'manifest.json').exists():
        body=read(directory/'manifest.json');verify_preserved(body['pinned_sources']);return body
    pinned={relative(p):digest(p) for p in PINNED}
    for paths in read(CAMPAIGN/'input_manifest.json')['inputs'].values():
        for name in paths:pinned[name]=digest(ROOT/name)
    body={'prepared_at':now(),'queue_version':1,'workers':workers,'max_workers':12,'services':SERVICES,
          'dependency_capture_policy':'Capture invocation IDs and logs only when --execute first starts; dry-run/preparation status is informational.',
          'pinned_sources':pinned,'engine_sha256':code_identity()['sha256'],'api_cost':cost(),
          'scope':'Wait, close primary lower, replan exactly once, run frozen nominal/shared/extraction followups and audits; no conditional fitting or API calls.'}
    immutable(directory/'manifest.json',body)
    return body


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue-dir',type=Path,default=CAMPAIGN/'completion_queue/v2')
    parser.add_argument('--workers',type=int,default=12)
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--prepare',action='store_true',help='Write reviewable manifest only; starts no work')
    action.add_argument('--execute',action='store_true',help='Run an already prepared/reviewed queue')
    action.add_argument('--dry-run',action='store_true',help='Read-only state and proposed coverage; default')
    parser.add_argument('--poll-seconds',type=int,default=30)
    args=parser.parse_args()
    if not 1<=args.workers<=12:parser.error('--workers must be between 1 and 12')
    if not 5<=args.poll_seconds<=60:parser.error('--poll-seconds must be between 5 and 60')
    directory=args.queue_dir.resolve();directory.relative_to(CAMPAIGN.resolve())
    if args.prepare:
        manifest=prepare(directory,args.workers)
        print(json.dumps({'prepared':relative(directory/'manifest.json'),'sha256':digest(directory/'manifest.json'),'jobs_started':0,
                         'dependency_status_informational':{k:service(v) for k,v in manifest['services'].items()},'api_cost':manifest['api_cost']},indent=2));return
    if not args.execute:
        plan,lists=build(CAMPAIGN,CAMPAIGN)
        print(json.dumps({'dry_run':True,'jobs_started':0,'queue_prepared':(directory/'manifest.json').exists(),
            'active_services':{k:service(v) for k,v in SERVICES.items()},'api_cost':cost(),
            'inventory':plan['inventory_counts'],'fresh':plan['fresh'],
            'primary_missing':{k:v['missing_count'] for k,v in plan['primary_coverage'].items()},
            'future_targets_provisional_until_primary_closed':{k:len(v) for k,v in lists.items()},
            'pending_scientist_decisions':['per-temperature additions','profiles','rescues'],
            'audit_problems':len(plan['audit_problems']),'warnings':plan['warnings']},indent=2));return
    if not (directory/'manifest.json').exists():parser.error('--execute requires --prepare and review first')
    manifest=read(directory/'manifest.json')
    if args.workers!=manifest['workers']:parser.error('Worker count must match reviewed manifest')
    with (CAMPAIGN/'completion_queue.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        queue=Queue(directory,manifest,args.workers)
        try: queue.execute(args.poll_seconds)
        except BaseException as error:
            queue.save(last_error={'at':now(),'type':type(error).__name__,'message':str(error)})
            raise
        print(json.dumps({'phase':queue.state['phase'],'completion':relative(directory/'completion.json')}))


if __name__=='__main__':
    main()
