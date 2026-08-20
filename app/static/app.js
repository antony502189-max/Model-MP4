let currentJob = null;
let poller = null;
const jobStorageKey = 'conveyor-bag-counter.current-job-id';
const $ = (id) => document.getElementById(id);

function setCurrentJob(job){
  currentJob = job;
  globalThis.localStorage?.setItem(jobStorageKey, job.id);
}

$('uploadBtn').onclick = async () => {
  const file = $('video').files[0];
  if (!file) return alert('Choose a video first.');
  const form = new FormData(); form.append('file', file);
  $('uploadBtn').disabled = true;
  let res;
  try { res = await fetch('/api/videos', { method:'POST', body:form }); }
  catch { $('uploadBtn').disabled = false; return alert('Upload connection failed.'); }
  $('uploadBtn').disabled = false;
  if (!res.ok) return alert((await res.json()).detail || 'Upload failed');
  setCurrentJob(await res.json());
  $('jobCard').classList.remove('hidden');
  $('jobId').textContent = currentJob.id;
  render(currentJob);
};

$('startBtn').onclick = async () => {
  if (!currentJob) return;
  let res;
  try { res = await fetch(`/api/jobs/${currentJob.id}/start`, { method:'POST' }); }
  catch { return alert('Could not contact the processing service.'); }
  if (!res.ok) return alert((await res.json()).detail || 'Could not start job');
  setCurrentJob(await res.json()); render(currentJob);
  loadAnomalies();
  $('startBtn').disabled = true;
  clearInterval(poller); poller = setInterval(refresh, 1500); refresh();
};

async function refresh(){
  const res = await fetch(`/api/jobs/${currentJob.id}`);
  if(!res.ok) return;
  setCurrentJob(await res.json()); render(currentJob);
  loadAnomalies();
  if(['completed','failed'].includes(currentJob.status)){ clearInterval(poller); $('startBtn').disabled = false; }
}

async function loadAnomalies(){
  if (!currentJob) return;
  const res = await fetch(`/api/jobs/${currentJob.id}/anomalies`);
  if (!res.ok) return;
  const items = await res.json();
  $('anomalyHint').textContent = items.length ? `${items.length} recorded` : 'No anomalies recorded.';
  $('anomalyList').replaceChildren(...items.slice(-12).reverse().map((item) => {
    const row = document.createElement('li');
    const id = item.track_id == null ? '' : ` · track #${item.track_id}`;
    row.textContent = `[${item.severity}] ${item.type}${id} — ${item.description}`;
    return row;
  }));
}

function render(job){
  $('status').textContent = job.status;
  $('progress').textContent = `${job.progress.toFixed(1)}%`;
  $('bar').style.width = `${job.progress}%`;
  $('count').textContent = job.bag_count;
  $('anomalies').textContent = job.anomaly_count;
  $('fps').textContent = job.processing_fps == null ? '—' : job.processing_fps.toFixed(1);
  $('startBtn').disabled = ['queued', 'processing'].includes(job.status);
  if(job.status === 'completed'){
    $('downloadBtn').href = `/api/jobs/${job.id}/result`;
    $('downloadBtn').classList.remove('disabled');
  }
  if(job.error){ $('error').textContent = job.error; $('error').classList.remove('hidden'); }
  else $('error').classList.add('hidden');
}

(async function restoreLatestJob(){
  const requestedJobId = new URLSearchParams(window.location.search).get('job');
  const jobId = requestedJobId || globalThis.localStorage?.getItem(jobStorageKey);
  if (!jobId) return;
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) { globalThis.localStorage?.removeItem(jobStorageKey); return; }
  setCurrentJob(await res.json());
  $('jobCard').classList.remove('hidden');
  $('jobId').textContent = currentJob.id;
  render(currentJob);
  loadAnomalies();
  if (!['completed', 'failed'].includes(currentJob.status)) {
    clearInterval(poller); poller = setInterval(refresh, 1500);
  }
})();
