"""Timezone-aware post dates and durable local Instagram schedules."""
import argparse
import fcntl
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import social_store as store

POLL_SECONDS = 15
MAX_LATENESS = 3600


def local_zone():
    name=os.environ.get('TZ') or str(Path('/etc/localtime').resolve()).partition('/zoneinfo/')[2]
    try:
        ZoneInfo(name)
        return name
    except (ValueError,ZoneInfoNotFoundError):return 'UTC'


def parse_time(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:raise ValueError()
        return result.astimezone(timezone.utc)
    except (AttributeError,TypeError,ValueError):raise ValueError('Choose a valid posting date, time and timezone.') from None


def future_time(value, now=None):
    result=parse_time(value)
    now=datetime.now(timezone.utc) if now is None else datetime.fromtimestamp(now,timezone.utc)
    if result <= now:raise ValueError('Choose a posting time in the future.')
    return result.isoformat(timespec='seconds').replace('+00:00','Z')


def posting_time(day, clock, zone):
    try:zone=ZoneInfo(zone)
    except (ValueError,ZoneInfoNotFoundError):raise ValueError('Choose a valid timezone.') from None
    naive=datetime.combine(day,clock).replace(tzinfo=None)
    first=naive.replace(tzinfo=zone,fold=0);second=naive.replace(tzinfo=zone,fold=1)
    if first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=naive:
        raise ValueError('That time is skipped by the daylight-saving change. Choose another time.')
    if first.utcoffset()!=second.utcoffset():
        raise ValueError('That time occurs twice during the daylight-saving change. Choose another time.')
    return future_time(first.isoformat())


def display_time(draft):
    value=parse_time(draft['publish_at'])
    name=draft.get('schedule_timezone') or local_zone()
    try:value=value.astimezone(ZoneInfo(name))
    except (ValueError,ZoneInfoNotFoundError):name='UTC'
    return value.strftime('%b %d, %Y at %I:%M %p')+' · '+name


def cancel_local(draft_id, expected_updated):
    from social_publish import upload_lock
    with upload_lock():
        draft=store.get(draft_id)
        if not draft or draft['updated']!=expected_updated:raise ValueError('This schedule changed. Refresh before cancelling it.')
        if draft.get('schedule_provider')!='local' or draft['status'] not in ('Scheduled','Schedule failed'):
            raise ValueError('This post has already started. Check its upload status.')
        fresh={k:v for k,v in draft.items() if k not in ('publish_at','schedule_timezone','schedule_provider','schedule_next_check','error')}
        return store.save(dict(fresh,status='Draft'))


def local_jobs():
    return [d for d in store.drafts() if d.get('schedule_provider')=='local' and '-attempt-' not in d['id']
            and d['status'] in ('Scheduled','Starting','Uploading','Processing','Ready','Publishing')]


def tick(now=None):
    from social_publish import publish,check,upload_lock,UploadBusy
    from app_logging import log_exception
    now=time.time() if now is None else now
    for snapshot in local_jobs():
        if snapshot.get('schedule_next_check',0)>now:continue
        try:
            due=parse_time(snapshot['publish_at']).timestamp()
            if due>now:continue
            if snapshot['status']=='Scheduled':
                if now-due>MAX_LATENESS:
                    with upload_lock():
                        current=store.get(snapshot['id'])
                        if current['status']=='Scheduled' and current['updated']==snapshot['updated']:
                            store.save(dict(current,status='Schedule failed',error='This post is more than an hour late. Cancel the schedule and choose a new time.'))
                    continue
                publish(snapshot['id'],expected_updated=snapshot['updated'],prevent_duplicate=True,scheduled_due=True)
            else:
                # A crash before a receipt is never permission to start another upload.
                if not snapshot.get('container_id'):
                    with upload_lock():
                        current=store.get(snapshot['id'])
                        if current['updated']==snapshot['updated']:
                            store.save(dict(current,status='Needs check',error='The scheduled upload was interrupted before its receipt was saved. Check Instagram before posting again.'))
                    continue
                current=check(snapshot['id'])
                if current['status']=='Ready' and not current.get('publish_requested'):
                    publish(current['id'],expected_updated=store.get(current['id'])['updated'],prevent_duplicate=True)
        except UploadBusy:continue
        except Exception:
            log_exception('Scheduled publishing needs attention')
            # Change state only under the same lock as cancellation and publication.
            try:
                with upload_lock():
                    current=store.get(snapshot['id'])
                    if current and current['status']=='Scheduled' and current['updated']==snapshot['updated']:
                        store.save(dict(current,status='Schedule failed',error='Posting could not start. Check the account, video and posting text, then cancel and schedule it again.'))
                    elif current and current['status'] in ('Processing','Ready'):
                        store.save(dict(current,schedule_next_check=now+60))
            except UploadBusy:pass


def runner_alive(root):
    path=Path(root)/'work/social-schedule.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
    return False


def ensure_scheduler(root):
    root=Path(root).resolve()
    if not store.DB.exists() or not local_jobs() or runner_alive(root):return
    with (root/'work/social-schedule.log').open('a') as log:
        subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--root',str(root)],cwd=root,
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)


def run(root):
    root=Path(root).resolve();store.DB=root/'data/social.sqlite3'
    path=root/'work/social-schedule.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        while local_jobs():
            tick();time.sleep(POLL_SECONDS)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=store.ROOT)
    run(parser.parse_args().root)
