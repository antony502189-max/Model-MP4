let currentJob = null;
let poller = null;
const $ = (id) => document.getElementById(id);

$('uploadBtn').onclick = async () => {
  const file = $('video').files[0];
  if (!file) return alert('Choose a video first.');
  const form = new FormData(); form.append('file', file);
  $('uploadBtn').disabled = true;
  const res = await fetch('/api/videos', { method:'POST', body:form });
  $('uploadBtn').disabled = false;
  if (!res.ok) return alert((await res.json()).detail || 'Upload failed');
  currentJob = await res.json();
  $('jobCard').classList.remove('hidden');
  $('jobId').textContent = currentJob.id;
  render(currentJob);
};

$('startBtn').onclick = async () => {
  if (!currentJob) return;
  const res = await fetch(`/api/jobs/${currentJob.id}/start`, { method:'POST' });
  if (!res.ok) return alert((await res.json()).detail || 'Could not start job');
  currentJob = await res.json(); render(currentJob);
  $('startBtn').disabled = true;
  clearInterval(poller); poller = setInterval(refresh, 1500); refresh();
};

async function refresh(){
  const res = await fetch(`/api/jobs/${currentJob.id}`);
  if(!res.ok) return;
  currentJob = await res.json(); render(currentJob);
  if(['completed','failed'].includes(currentJob.status)){ clearInterval(poller); $('startBtn').disabled = false; }
}

function render(job){
  $('status').textContent = job.status;
  $('progress').textContent = `${job.progress.toFixed(1)}%`;
  $('bar').style.width = `${job.progress}%`;
  $('count').textContent = job.bag_count;
  $('anomalies').textContent = job.anomaly_count;
  $('fps').textContent = job.processing_fps == null ? '—' : job.processing_fps.toFixed(1);
  if(job.status === 'completed'){
    $('downloadBtn').href = `/api/jobs/${job.id}/result`;
    $('downloadBtn').classList.remove('disabled');
  }
  if(job.error){ $('error').textContent = job.error; $('error').classList.remove('hidden'); }
  else $('error').classList.add('hidden');
}
