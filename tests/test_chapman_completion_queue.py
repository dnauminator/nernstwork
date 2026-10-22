"""Failure and resume boundaries for the finite local completion queue."""
import importlib.util
from pathlib import Path
import sys
import pytest

pytest.importorskip('fcntl')  # the queue script locks with fcntl.flock (POSIX only); skip on Windows instead of failing collection

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('chapman_completion_queue',ROOT/'scripts/complete_chapman_li_campaign.py')
queue=importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)

CAPTURED={'InvocationID':'abc','CollectMode':'inactive'}
MARKER={'terminal_marker_verified':True}


def test_running_success_property_is_not_completion():
    assert queue.dependency_classification({'ActiveState':'active','Result':'success','InvocationID':'abc'},CAPTURED,MARKER)=='waiting'


def test_unknown_unit_default_success_cannot_release_queue():
    unknown={'LoadState':'not-found','ActiveState':'inactive','Result':'success','ExecMainStatus':'0'}
    assert queue.dependency_classification(unknown,{},MARKER)=='unknown_unit'
    assert queue.dependency_classification(unknown,CAPTURED,MARKER)=='missing_completion_evidence'
    assert queue.dependency_classification(unknown,CAPTURED,MARKER,{'accounting_after_capture':True,'failure_messages':[]})=='success_collected_with_evidence'
    assert queue.dependency_classification(unknown,CAPTURED,MARKER,{'accounting_after_capture':True,'failure_messages':['failed']})=='missing_completion_evidence'


def test_restarted_and_failed_dependencies_stop():
    assert queue.dependency_classification({'ActiveState':'active','InvocationID':'other'},CAPTURED,MARKER)=='changed_invocation'
    assert queue.dependency_classification({'ActiveState':'inactive','InvocationID':'other'},CAPTURED,MARKER)=='changed_invocation'
    assert queue.dependency_classification({'ActiveState':'failed','Result':'exit-code','ExecMainStatus':'1'},CAPTURED,MARKER)=='failed'
    assert queue.dependency_classification({'LoadState':'loaded','ActiveState':'inactive','Result':'success','ExecMainStatus':'0'},CAPTURED,None)=='missing_completion_evidence'


def test_success_marker_must_follow_current_start_and_capture(tmp_path):
    path=tmp_path/'job.log'
    path.write_text('{"started":"2","jobs":2,"scenario":"fig2_lower"}\n{"finished":"1","counts":{"fitted":2}}\n')
    captured={'log_path':str(path),'log_bytes_at_capture':0}
    assert queue.completion_marker('lower',captured) is None
    path.write_text('{"started":"2","jobs":2,"scenario":"fig2_lower"}\n{"finished":"3","counts":{"fitted":1,"nonconvergence":1}}\n')
    assert queue.completion_marker('lower',captured)['terminal_marker_verified']
    captured['log_bytes_at_capture']=path.stat().st_size
    assert queue.completion_marker('lower',captured) is None


def test_immutable_outputs_and_protected_primary_hashes(tmp_path,monkeypatch):
    monkeypatch.setattr(queue,'ROOT',tmp_path)
    path=tmp_path/'result.json'
    queue.immutable(path,{'status':'nonconvergence'})
    original=path.read_bytes()
    queue.immutable(path,{'status':'nonconvergence'})
    assert path.read_bytes()==original
    with pytest.raises(ValueError): queue.immutable(path,{'status':'fitted'})
    hashes={'result.json':queue.digest(path)}
    queue.verify_preserved(hashes)
    path.write_text('{}')
    with pytest.raises(ValueError): queue.verify_preserved(hashes)


def test_resume_keeps_recorded_failures_and_only_schedules_missing(tmp_path,monkeypatch):
    monkeypatch.setattr(queue,'CAMPAIGN',tmp_path)
    records=[{'dynamics_hash':'a'},{'dynamics_hash':'b'}]
    path=tmp_path/'results/fig2_lower__fixed/a.json';path.parent.mkdir(parents=True)
    path.write_text('{"status":"execution_error"}')
    assert queue.pending_records(records,'fig2_lower','fixed')==[records[1]]


def test_frozen_plan_is_not_rebuilt_on_resume(tmp_path,monkeypatch):
    lists={'initial_amount_shortlist':[{'dynamics_hash':'frozen'}]}
    saved={'plan':{},'plan_sha256':queue.sha256_json({}),'lists':lists,'lists_sha256':{k:queue.sha256_json(v) for k,v in lists.items()}}
    queue.immutable(tmp_path/'plans/after_primary.json',saved)
    def forbidden(*args): raise AssertionError('An extra replan would expand the finite scope')
    monkeypatch.setattr(queue,'build',forbidden)
    assert queue.plan_snapshot(tmp_path,'after_primary')==saved


def test_recorded_success_can_be_retried_for_missing_busy_outputs(tmp_path,monkeypatch):
    monkeypatch.setattr(queue,'ROOT',tmp_path)
    monkeypatch.setattr(queue,'result_hashes',lambda:{})
    monkeypatch.setattr(queue,'protected_remote',lambda:{})
    monkeypatch.setattr(queue,'cost',lambda:{'estimated_usd':0})
    q=queue.Queue(tmp_path/'queue',{},1)
    monkeypatch.setattr(q,'check',lambda:None)
    class Child:
        pid=123
        def wait(self): return 0
    calls=[]
    monkeypatch.setattr(queue.subprocess,'Popen',lambda *a,**k:(calls.append(a) or Child()))
    q.state['completed_stages']=['fit_same_missing_set']
    q.command('fit_same_missing_set',['python','missing.py'],skip_completed=False)
    assert len(calls)==1
    q.command('fit_same_missing_set',['python','missing.py'])
    assert len(calls)==1


def test_completion_receipt_recovers_crash_before_final_state(tmp_path,monkeypatch):
    monkeypatch.setattr(queue,'ROOT',tmp_path)
    manifest={}
    queue.immutable(tmp_path/'manifest.json',manifest)
    queue.immutable(tmp_path/'completion.json',{'queue_manifest_sha256':queue.digest(tmp_path/'manifest.json')})
    q=queue.Queue(tmp_path,manifest,1)
    monkeypatch.setattr(q,'wait_dependencies',lambda _:None)
    monkeypatch.setattr(q,'command',lambda *a,**k:pytest.fail('Completed receipt must not rerun work'))
    q.execute(5)
    assert q.state['phase']=='complete'


def test_preparation_does_not_capture_service_invocations(tmp_path,monkeypatch):
    monkeypatch.setattr(queue,'PINNED',[])
    monkeypatch.setattr(queue,'cost',lambda:{'estimated_usd':0})
    monkeypatch.setattr(queue,'code_identity',lambda:{'sha256':'engine'})
    actual_read=queue.read
    monkeypatch.setattr(queue,'read',lambda p: {'inputs':{}} if Path(p).name=='input_manifest.json' else actual_read(p))
    monkeypatch.setattr(queue,'service',lambda _:pytest.fail('Dependency identities must be captured at execution'))
    manifest=queue.prepare(tmp_path,1)
    assert manifest['services']==queue.SERVICES
    assert 'dependencies' not in manifest
