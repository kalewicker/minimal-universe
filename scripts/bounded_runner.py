"""Bounded independent process supervision, with immutable attempt directories."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def supervise(command, per_job_seconds, global_deadline, byte_limit):
    start=time.monotonic()
    deadline=min(start+per_job_seconds,global_deadline)
    cap_status='global_wall_cap' if global_deadline<=start+per_job_seconds else 'job_wall_cap'
    if start>=deadline:
        return {'status':cap_status,'elapsed_seconds':0,'captured_bytes':0}
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    selector=selectors.DefaultSelector()
    chunks={'stdout':bytearray(),'stderr':bytearray()}
    for name,pipe in [('stdout',process.stdout),('stderr',process.stderr)]:
        os.set_blocking(pipe.fileno(),False)
        selector.register(pipe,selectors.EVENT_READ,name)
    status=None;captured=0
    try:
        while selector.get_map() or process.poll() is None:
            remaining=deadline-time.monotonic()
            if remaining<=0:
                status=cap_status;break
            for key,_ in selector.select(min(.02,remaining)):
                data=os.read(key.fd,8192)
                if not data:
                    selector.unregister(key.fileobj);continue
                allowed=max(0,byte_limit-captured)
                chunks[key.data].extend(data[:allowed])
                captured+=min(len(data),allowed)
                if len(data)>allowed:
                    status='output_cap';break
            if status:
                break
        if status:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        process.wait()
    finally:
        if process.poll() is None:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
        selector.close();process.stdout.close();process.stderr.close()
    result={'status':status or ('complete' if process.returncode==0 else 'worker_error'),
            'elapsed_seconds':time.monotonic()-start,'captured_bytes':captured,
            'stdout_sha256':sha256(chunks['stdout']).hexdigest(),
            'stderr_sha256':sha256(chunks['stderr']).hexdigest()}
    if result['status']=='complete':
        try: result['result']=json.loads(chunks['stdout'])
        except (ValueError,UnicodeError): result['status']='invalid_worker_json'
    if result['status']!='complete':
        result['returncode']=process.returncode
        result['stderr_prefix']=bytes(chunks['stderr'][:128]).decode('utf-8',errors='replace')
    return result


def summary_reservation(count):
    # Full status vector plus generous fixed envelope. Avoid an unbounded suffix log.
    return len(encoded(['not_started_global_wall_cap']*count))+8192


def run_batch(jobs,command_factory,limits,directory):
    """Jobs must already be validated by the caller. Reserved entries never launch."""
    for name in ('workers','global_output_bytes','per_job_output_bytes'):
        if type(limits[name]) is not int or limits[name]<=0:
            raise ValueError('invalid integer budget')
    for name in ('per_job_wall_seconds','global_wall_seconds'):
        if not math.isfinite(limits[name]) or limits[name]<=0:
            raise ValueError('invalid deadline')
    if limits['workers']>4 or limits['per_job_output_bytes']<1024:
        raise ValueError('unsupported supervisor budget')
    reserve=summary_reservation(len(jobs))
    if limits['global_output_bytes']<reserve:
        raise ValueError('budget cannot hold mandatory accounting')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();deadline=start+limits['global_wall_seconds']
    statuses=['reserved' if j.get('reserved',False) else 'not_started' for j in jobs]
    used=0;cursor=0;active={};stop=None
    with (directory/'events.jsonl').open('xb') as ledger, ThreadPoolExecutor(max_workers=limits['workers']) as pool:
        while cursor<len(jobs) or active:
            while not stop and cursor<len(jobs) and len(active)<limits['workers']:
                if statuses[cursor]=='reserved':
                    cursor+=1;continue
                if time.monotonic()>=deadline:
                    stop='global_wall_cap';break
                if used+reserve+(len(active)+1)*limits['per_job_output_bytes']>limits['global_output_bytes']:
                    if active: break
                    stop='global_output_cap';break
                index=cursor;cursor+=1
                # Failure to construct a command is also an attempted job, not a retry.
                try:
                    command=command_factory(jobs[index])
                    future=pool.submit(supervise,command,limits['per_job_wall_seconds'],deadline,
                                       limits['per_job_output_bytes'])
                    active[future]=index
                except Exception as error:
                    row={'index':index,'status':'dispatch_error','error_type':type(error).__name__}
                    data=encoded(row);ledger.write(data);ledger.flush();used+=len(data)
                    statuses[index]='dispatch_error'
            if not active:
                if stop or cursor==len(jobs): break
                continue
            done,_=wait(active,timeout=.02,return_when=FIRST_COMPLETED)
            for future in sorted(done,key=lambda f:active[f]):
                index=active.pop(future)
                try: row=future.result() | {'index':index}
                except Exception as error: row={'index':index,'status':'supervisor_error','error_type':type(error).__name__}
                data=encoded(row)
                if len(data)>limits['per_job_output_bytes']:
                    row={'index':index,'status':'record_output_cap','discarded_record_sha256':sha256(data).hexdigest()}
                    data=encoded(row)
                if len(data)>limits['per_job_output_bytes']:
                    raise RuntimeError('error envelope exceeds reservation')
                ledger.write(data);ledger.flush();used+=len(data)
                statuses[index]=row['status']
                if row['status']=='global_wall_cap': stop='global_wall_cap'
        for index,status in enumerate(statuses):
            if status=='not_started':
                statuses[index]='not_started_'+(stop or 'unknown')
    result={'statuses':statuses,'elapsed_seconds':time.monotonic()-start,
            'limits':limits,'stop_reason':stop,'ledger_bytes':used,
            'ledger_sha256':sha256((directory/'events.jsonl').read_bytes()).hexdigest(),
            'plan_sha256':sha256(encoded(jobs)).hexdigest(),'stored_bytes':0}
    for _ in range(10):
        total=used+len(encoded(result))
        if result['stored_bytes']==total: break
        result['stored_bytes']=total
    data=encoded(result)
    if len(data)>reserve or used+len(data)>limits['global_output_bytes']:
        raise RuntimeError('mandatory accounting exceeded reservation')
    with (directory/'summary.json').open('xb') as stream: stream.write(data)
    return result
