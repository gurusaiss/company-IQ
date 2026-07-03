/* ═══════════════════════════════════════════
   CompanyIQ v3 — Frontend Application
   Auth (JWT) · Quota · Account · Share · Compare · Salary · Tracker
═══════════════════════════════════════════ */

const API      = '';
const POLL_MS  = 2500;
const TOKEN_LS = 'ciq_token';
const UPI_ID   = 'your-upi@bank';   // ← change to your real UPI id

// ── State ──
var token        = localStorage.getItem(TOKEN_LS) || '';
var currentUser  = null;
var currentJobId = null;
var pollTimer    = null;
var pptText      = '';
var clLetterText = '';
var authMode     = 'login';   // 'login' | 'signup'
var fcCards = [], fcIndex = 0, fcFlipped = false;

var $ = function(id) { return document.getElementById(id); };

// ══════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════
var toastEl = $('toast'), toastTimer = null;
function showToast(msg, type) {
  toastEl.textContent = msg;
  toastEl.className = 'toast show' + (type && type !== 'info' ? ' ' + type : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function() { toastEl.className = 'toast'; }, 3600);
}

// ══════════════════════════════════════════
//  FETCH WRAPPER (adds Bearer token, handles 401/402)
// ══════════════════════════════════════════
function authedFetch(url, opts) {
  opts = opts || {};
  opts.headers = opts.headers || {};
  if (token) opts.headers['Authorization'] = 'Bearer ' + token;
  return fetch(API + url, opts).then(function(res) {
    if (res.status === 401) { handleLogout(true); throw { handled: true, status: 401 }; }
    return res;
  });
}

function handle402(res) {
  return res.json().catch(function() { return {}; }).then(function(d) {
    openUpgrade(d.detail || "You've reached your free limit. Upgrade for unlimited access.");
    throw { handled: true, status: 402 };
  });
}

// ══════════════════════════════════════════
//  AUTH
// ══════════════════════════════════════════
var authOverlay = $('authOverlay');
var authForm = $('authForm'), authEmail = $('authEmail'), authPassword = $('authPassword');
var authName = $('authName'), authRef = $('authRef');
var authNameField = $('authNameField'), authRefField = $('authRefField');
var authTitle = $('authTitle'), authSubtitle = $('authSubtitle'), authSubmitBtn = $('authSubmitBtn');
var authToggleBtn = $('authToggleBtn'), authToggleText = $('authToggleText');

function showAuth() { authOverlay.classList.remove('hidden'); authEmail.focus(); }
function hideAuth() { authOverlay.classList.add('hidden'); }

function setAuthMode(mode) {
  authMode = mode;
  if (mode === 'signup') {
    authTitle.textContent = 'Create your account';
    authSubtitle.textContent = 'Start free — 3 reports a month, no card needed';
    authSubmitBtn.textContent = 'Sign Up';
    authNameField.classList.remove('hidden');
    authRefField.classList.remove('hidden');
    authToggleText.textContent = 'Already have an account?';
    authToggleBtn.textContent = 'Sign in';
    authPassword.setAttribute('autocomplete', 'new-password');
  } else {
    authTitle.textContent = 'Welcome back';
    authSubtitle.textContent = 'Sign in to continue to CompanyIQ';
    authSubmitBtn.textContent = 'Sign In';
    authNameField.classList.add('hidden');
    authRefField.classList.add('hidden');
    authToggleText.textContent = 'New here?';
    authToggleBtn.textContent = 'Create an account';
    authPassword.setAttribute('autocomplete', 'current-password');
  }
}
authToggleBtn.addEventListener('click', function() { setAuthMode(authMode === 'login' ? 'signup' : 'login'); });

authForm.addEventListener('submit', function(e) {
  e.preventDefault();
  var email = authEmail.value.trim(), pw = authPassword.value;
  if (!email || !pw) { showToast('Enter email and password.', 'error'); return; }
  if (authMode === 'signup' && pw.length < 6) { showToast('Password must be at least 6 characters.', 'error'); return; }

  authSubmitBtn.disabled = true;
  authSubmitBtn.textContent = 'Please wait...';

  var path = authMode === 'signup' ? '/api/auth/register' : '/api/auth/login';
  var body = { email: email, password: pw };
  if (authMode === 'signup') {
    body.name = authName.value.trim();
    if (authRef.value.trim()) body.referral_code = authRef.value.trim();
  }

  fetch(API + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  })
    .then(function(res) { return res.json().then(function(d) { return { ok: res.ok, status: res.status, d: d }; }); })
    .then(function(r) {
      authSubmitBtn.disabled = false;
      setAuthMode(authMode);
      if (!r.ok) { showToast(r.d.detail || 'Authentication failed.', 'error'); return; }
      token = r.d.token;
      localStorage.setItem(TOKEN_LS, token);
      currentUser = r.d.user;
      hideAuth();
      onAuthed();
      showToast(authMode === 'signup' ? 'Welcome to CompanyIQ! 🎉' : 'Signed in!', 'success');
    })
    .catch(function() { authSubmitBtn.disabled = false; setAuthMode(authMode); showToast('Could not reach server.', 'error'); });
});

function handleLogout(expired) {
  token = ''; currentUser = null;
  localStorage.removeItem(TOKEN_LS);
  accountPanel.classList.add('hidden');
  if (expired) showToast('Session expired. Please sign in again.', 'error');
  setAuthMode('login');
  showAuth();
}
$('logoutBtn').addEventListener('click', function() { handleLogout(false); });

function onAuthed() {
  refreshAccount();
}

// ══════════════════════════════════════════
//  ACCOUNT PANEL
// ══════════════════════════════════════════
var accountPanel = $('accountPanel');
$('accountToggle').addEventListener('click', function() {
  accountPanel.classList.toggle('hidden');
  if (!accountPanel.classList.contains('hidden')) refreshAccount();
});
$('accountClose').addEventListener('click', function() { accountPanel.classList.add('hidden'); });

function planLabel(p) { return p ? p.charAt(0).toUpperCase() + p.slice(1) : 'Free'; }

function refreshAccount() {
  authedFetch('/api/auth/me').then(function(res) {
    if (!res.ok) return;
    return res.json();
  }).then(function(data) {
    if (!data) return;
    currentUser = data.user;
    renderAccount(data);
  }).catch(function() {});
}

function renderAccount(data) {
  var u = data.user;
  var plan = u.plan || 'free';
  $('accountAvatar').textContent = (u.email || '?').charAt(0).toUpperCase();
  $('accountPlanPill').textContent = planLabel(plan);
  $('accountPlanPill').className = 'account-plan-pill plan-' + plan;
  $('accountEmail').textContent = u.email;
  $('accountPlanBadge').textContent = planLabel(plan);
  $('accountPlanBadge').className = 'plan-badge plan-' + plan;
  $('accountRefCode').value = u.referral_code || '';

  var upgradeBtn = $('accountUpgradeBtn');
  var usageBox = $('accountUsage');
  if (plan === 'pro' || plan === 'lifetime') {
    upgradeBtn.classList.add('hidden');
    usageBox.innerHTML = '<div class="usage-unlimited">✨ Unlimited usage on ' + planLabel(plan) + '</div>';
  } else {
    upgradeBtn.classList.remove('hidden');
    var usage = data.usage || {}, limits = data.limits || {}, labels = data.labels || {};
    var rows = Object.keys(limits).map(function(action) {
      var used = usage[action] || 0, lim = limits[action];
      var pct = lim > 0 ? Math.min(100, Math.round(used / lim * 100)) : 0;
      var label = labels[action] || action;
      var over = used >= lim;
      return '<div class="usage-row">'
        + '<div class="usage-top"><span>' + escHtml(label) + '</span><span class="' + (over ? "usage-over" : "") + '">' + used + ' / ' + lim + '</span></div>'
        + '<div class="usage-track"><div class="usage-fill" style="width:' + pct + '%"></div></div></div>';
    }).join('');
    usageBox.innerHTML = '<div class="usage-title">This month</div>' + rows;
  }
}

$('accountUpgradeBtn').addEventListener('click', function() { openUpgrade(); });
$('accountRefCopy').addEventListener('click', function() {
  navigator.clipboard.writeText($('accountRefCode').value).then(function() { showToast('Referral code copied!', 'success'); });
});

function doRedeem(inputEl, btnEl) {
  var code = inputEl.value.trim();
  if (!code) { showToast('Enter a redemption code.', 'error'); return; }
  btnEl.disabled = true;
  authedFetch('/api/auth/redeem', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code })
  }).then(function(res) { return res.json().then(function(d) { return { ok: res.ok, d: d }; }); })
    .then(function(r) {
      btnEl.disabled = false;
      if (!r.ok) { showToast(r.d.detail || 'Invalid code.', 'error'); return; }
      inputEl.value = '';
      showToast(r.d.message || 'Upgraded!', 'success');
      closeUpgrade();
      refreshAccount();
    }).catch(function(e) { btnEl.disabled = false; if (!(e && e.handled)) showToast('Redeem failed.', 'error'); });
}
$('accountRedeemBtn').addEventListener('click', function() { doRedeem($('accountRedeemInput'), this); });
$('upgradeRedeemBtn').addEventListener('click', function() { doRedeem($('upgradeRedeemInput'), this); });

// ══════════════════════════════════════════
//  UPGRADE MODAL
// ══════════════════════════════════════════
var upgradeOverlay = $('upgradeOverlay');
function openUpgrade(msg) {
  if (msg) $('upgradeMsg').textContent = msg;
  $('upiId').textContent = UPI_ID;
  upgradeOverlay.classList.remove('hidden');
}
function closeUpgrade() { upgradeOverlay.classList.add('hidden'); }
$('upgradeClose').addEventListener('click', closeUpgrade);

// ══════════════════════════════════════════
//  TABS
// ══════════════════════════════════════════
var tabBtns = document.querySelectorAll('.tool-tab');
var tabPanes = document.querySelectorAll('.tab-pane');
tabBtns.forEach(function(btn) {
  btn.addEventListener('click', function() {
    tabBtns.forEach(function(b) { b.classList.remove('active'); });
    tabPanes.forEach(function(p) { p.classList.add('hidden'); });
    btn.classList.add('active');
    var pane = $('tab' + cap(btn.dataset.tab));
    if (pane) pane.classList.remove('hidden');
    if (btn.dataset.tab === 'tracker') loadTracker();
  });
});
function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function showInTab(list, active) {
  list.forEach(function(s) { s.classList.add('hidden'); });
  active.classList.remove('hidden');
}

// ══════════════════════════════════════════
//  UPLOAD ZONES
// ══════════════════════════════════════════
function wireUpload(zone, input, idle, done, nameEl, rmBtn) {
  function handleFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) { showToast('Only PDF files are accepted.', 'error'); return; }
    if (file.size > 10 * 1024 * 1024) { showToast('File exceeds 10 MB limit.', 'error'); return; }
    try { var dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; } catch(_) {}
    nameEl.textContent = file.name;
    idle.classList.add('hidden'); done.classList.remove('hidden');
  }
  zone.addEventListener('click', function(e) { if (rmBtn && (e.target === rmBtn || rmBtn.contains(e.target))) return; input.click(); });
  input.addEventListener('change', function() { if (input.files && input.files[0]) handleFile(input.files[0]); });
  if (rmBtn) rmBtn.addEventListener('click', function(e) { e.stopPropagation(); input.value=''; idle.classList.remove('hidden'); done.classList.add('hidden'); });
  zone.addEventListener('dragover', function(e) { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', function() { zone.classList.remove('drag-over'); });
  zone.addEventListener('drop', function(e) { e.preventDefault(); zone.classList.remove('drag-over'); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
}
wireUpload($('uploadZone'),   $('resumeFile'),   $('uploadIdle'),   $('uploadDone'),   $('fileName'),   $('fileRm'));
wireUpload($('clUploadZone'), $('clResumeFile'), $('clUploadIdle'), $('clUploadDone'), $('clFileName'), $('clFileRm'));
wireUpload($('jdUploadZone'), $('jdResumeFile'), $('jdUploadIdle'), $('jdUploadDone'), $('jdFileName'), $('jdFileRm'));
wireUpload($('cmpUploadZone'),$('cmpResumeFile'),$('cmpUploadIdle'),$('cmpUploadDone'),$('cmpFileName'),$('cmpFileRm'));
wireUpload($('salUploadZone'),$('salResumeFile'),$('salUploadIdle'),$('salUploadDone'),$('salFileName'),$('salFileRm'));

// ══════════════════════════════════════════
//  BLOB DOWNLOAD (authenticated)
// ══════════════════════════════════════════
function downloadAuthed(path, filename) {
  showToast('Preparing download...');
  authedFetch(path).then(function(res) {
    if (!res.ok) throw new Error('Download failed');
    return res.blob();
  }).then(function(blob) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }).catch(function(e) { if (!(e && e.handled)) showToast('Download failed.', 'error'); });
}

// ══════════════════════════════════════════
//  REPORT FLOW
// ══════════════════════════════════════════
var companyInput = $('companyName'), resumeInput = $('resumeFile'), generateBtn = $('generateBtn');
var sectionForm = $('sectionForm'), sectionProgress = $('sectionProgress'), sectionResults = $('sectionResults'), sectionError = $('sectionError');
var reportSections = [sectionForm, sectionProgress, sectionResults, sectionError];

$('analyzeForm').addEventListener('submit', function(e) {
  e.preventDefault();
  var company = companyInput.value.trim();
  if (!company) { showToast('Enter a company name.', 'error'); return; }
  if (!resumeInput.files || !resumeInput.files[0]) { showToast('Upload your resume PDF.', 'error'); return; }

  generateBtn.disabled = true; generateBtn.innerHTML = '<span>⏳</span> Starting...';
  var fd = new FormData();
  fd.append('company_name', company);
  fd.append('resume', resumeInput.files[0]);

  authedFetch('/api/analyze', { method: 'POST', body: fd })
    .then(function(res) {
      if (res.status === 402) return handle402(res);
      if (res.status === 429) { showToast('Rate limit reached. Please wait.', 'error'); throw { handled: true }; }
      if (!res.ok) return res.json().then(function(d) { throw new Error(d.detail || 'Server error'); });
      return res.json();
    })
    .then(function(data) {
      currentJobId = data.job_id; pptText = '';
      $('progressCompany').textContent = company;
      $('progFill').style.width = '0%'; $('progMsg').textContent = 'Initializing...'; $('progPct').textContent = '0%';
      resetSteps();
      hideShareResult();
      showInTab(reportSections, sectionProgress);
      startPolling(company);
    })
    .catch(function(err) { if (!(err && err.handled)) showToast(err.message || 'Failed to start.', 'error'); resetGenBtn(); });
});
function resetGenBtn() { generateBtn.disabled = false; generateBtn.innerHTML = '<span>⚡</span> Generate Intelligence Report'; }

var STATUS_ORDER = ['pending','parsing','researching','analyzing','generating','complete','failed'];
var STEPS = [{id:'stepParsing',s:['parsing']},{id:'stepResearching',s:['researching']},{id:'stepAnalyzing',s:['analyzing']},{id:'stepGenerating',s:['generating','complete']}];
function resetSteps() { STEPS.forEach(function(st){var el=$(st.id);el.classList.remove('active','done');el.querySelector('.step-tick').textContent='';}); }
function updateSteps(status) {
  var cur = STATUS_ORDER.indexOf(status);
  STEPS.forEach(function(step){var el=$(step.id);var idx=STATUS_ORDER.indexOf(step.s[0]);el.classList.remove('active','done');el.querySelector('.step-tick').textContent='';
    if(cur>idx){el.classList.add('done');el.querySelector('.step-tick').textContent='✓';}else if(step.s.indexOf(status)!==-1){el.classList.add('active');}});
}
function startPolling(company){ stopPolling(); pollTimer=setInterval(function(){pollStatus(company);},POLL_MS); pollStatus(company); }
function stopPolling(){ if(pollTimer){clearInterval(pollTimer);pollTimer=null;} }
function pollStatus(company){
  if(!currentJobId){stopPolling();return;}
  authedFetch('/api/status/'+currentJobId).then(function(res){if(res.ok)return res.json();})
    .then(function(data){
      if(!data)return;
      var pct=data.progress||0;
      $('progFill').style.width=pct+'%'; $('progMsg').textContent=data.message||''; $('progPct').textContent=pct+'%';
      updateSteps(data.status);
      if(data.status==='complete'){stopPolling();handleComplete(company);}
      else if(data.status==='failed'){stopPolling();handleErr(data.error||'Analysis failed.');}
    }).catch(function(){});
}
function handleComplete(company){
  var slug = slugify(company);
  $('dlPdf').onclick = function(){ downloadAuthed('/api/download/'+currentJobId+'/pdf', slug+'_report.pdf'); };
  $('dlMd').onclick  = function(){ downloadAuthed('/api/download/'+currentJobId+'/md',  slug+'_report.md'); };
  $('dlPpt').onclick = function(){ downloadAuthed('/api/download/'+currentJobId+'/ppt', slug+'_ppt_prompt.txt'); };
  authedFetch('/api/download/'+currentJobId+'/ppt').then(function(r){if(r.ok)return r.text();}).then(function(t){if(t)pptText=t;}).catch(function(){});
  $('resultsCo').textContent = company;
  resetGenBtn();
  showInTab(reportSections, sectionResults);
  showToast('Your report is ready! 🎉', 'success');
  refreshAccount();
}
function handleErr(msg){ $('errMsg').textContent=msg; resetGenBtn(); showInTab(reportSections, sectionError); }

$('copyPpt').addEventListener('click', function(){
  if(!pptText){showToast('PPT prompt not available.','error');return;}
  navigator.clipboard.writeText(pptText).then(function(){showToast('PPT prompt copied.','success');});
});
[$('resetBtn'),$('errResetBtn')].forEach(function(b){b.addEventListener('click',function(){
  stopPolling(); currentJobId=null; companyInput.value=''; resumeInput.value='';
  $('uploadIdle').classList.remove('hidden'); $('uploadDone').classList.add('hidden');
  hideShareResult();
  showInTab(reportSections, sectionForm);
});});

// ── Share ──
function hideShareResult(){ $('shareResult').classList.add('hidden'); }
$('shareBtn').addEventListener('click', function(){
  if(!currentJobId){showToast('Generate a report first.','error');return;}
  var btn=this; btn.disabled=true;
  authedFetch('/api/share/'+currentJobId,{method:'POST'})
    .then(function(res){ if(res.status===402)return handle402(res); return res.json().then(function(d){return {ok:res.ok,d:d};}); })
    .then(function(r){ btn.disabled=false; if(!r.ok){showToast(r.d.detail||'Could not create link.','error');return;}
      var full = window.location.origin + r.d.share_path;
      $('shareUrl').value = full; $('shareResult').classList.remove('hidden');
      showToast('Shareable link created!','success');
    }).catch(function(e){ btn.disabled=false; if(!(e&&e.handled))showToast('Could not create link.','error'); });
});
$('shareCopyBtn').addEventListener('click', function(){ navigator.clipboard.writeText($('shareUrl').value).then(function(){showToast('Link copied!','success');}); });

// ── Flashcards ──
$('flashcardBtn').addEventListener('click', function(){
  if(!currentJobId){showToast('Generate a report first.','error');return;}
  var btn=this; btn.disabled=true; btn.textContent='Loading...';
  authedFetch('/api/flashcards/'+currentJobId).then(function(res){if(res.ok)return res.json();throw new Error();})
    .then(function(data){ btn.disabled=false; btn.textContent='Study Now →';
      if(!data.cards||!data.cards.length){showToast('No flashcards in this report.','error');return;}
      openFlashcards(data.cards,data.company||'');
    }).catch(function(e){ btn.disabled=false; btn.textContent='Study Now →'; if(!(e&&e.handled))showToast('Could not load flashcards.','error'); });
});
var flashcardModal=$('flashcardModal'), fcInner=$('fcInner');
function openFlashcards(cards,company){ fcCards=cards; fcIndex=0; fcFlipped=false; $('fcCompany').textContent=company; renderCard(); flashcardModal.classList.remove('hidden'); }
function renderCard(){ if(!fcCards.length)return; var c=fcCards[fcIndex];
  $('fcCategory').textContent=c.category||'General'; $('fcQuestion').textContent=c.question||''; $('fcTip').textContent=c.tip||'';
  $('fcProgress').textContent=(fcIndex+1)+' / '+fcCards.length; fcFlipped=false; fcInner.classList.remove('flipped');
  $('fcPrev').disabled=(fcIndex===0); $('fcNext').disabled=(fcIndex===fcCards.length-1);
}
window.flipCard=function(){ fcFlipped=!fcFlipped; fcInner.classList.toggle('flipped',fcFlipped); };
$('fcFlipBtn').addEventListener('click',window.flipCard);
$('fcPrev').addEventListener('click',function(){if(fcIndex>0){fcIndex--;renderCard();}});
$('fcNext').addEventListener('click',function(){if(fcIndex<fcCards.length-1){fcIndex++;renderCard();}});
$('fcShuffle').addEventListener('click',function(){for(var i=fcCards.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=fcCards[i];fcCards[i]=fcCards[j];fcCards[j]=t;}fcIndex=0;renderCard();showToast('Shuffled!');});
function closeFC(){ flashcardModal.classList.add('hidden'); }
$('fcClose').addEventListener('click',closeFC); $('fcBackdrop').addEventListener('click',closeFC);
document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeFC();closeUpgrade();}});

// ══════════════════════════════════════════
//  COVER LETTER
// ══════════════════════════════════════════
var clSections=[$('sectionCL'),$('sectionCLResult')];
$('clForm').addEventListener('submit',function(e){
  e.preventDefault();
  var company=$('clCompany').value.trim(), role=$('clRole').value.trim();
  if(!company||!role){showToast('Enter company and role.','error');return;}
  if(!$('clResumeFile').files[0]){showToast('Upload your resume PDF.','error');return;}
  var btn=$('clGenerateBtn'); btn.disabled=true; btn.innerHTML='<span>⏳</span> Generating...';
  var fd=new FormData();
  fd.append('company_name',company); fd.append('job_role',role);
  fd.append('job_description',$('clJd').value); fd.append('resume',$('clResumeFile').files[0]);
  if(currentJobId) fd.append('job_id',currentJobId);
  authedFetch('/api/cover-letter',{method:'POST',body:fd})
    .then(function(res){ if(res.status===402)return handle402(res); if(!res.ok)return res.json().then(function(d){throw new Error(d.detail||'Error');}); return res.json(); })
    .then(function(data){ clLetterText=data.cover_letter||''; $('clOutput').textContent=clLetterText;
      $('clResultMeta').textContent=company+' — '+role; showInTab(clSections,$('sectionCLResult')); showToast('Cover letter ready!','success'); refreshAccount();
    })
    .catch(function(err){ if(!(err&&err.handled))showToast(err.message||'Failed.','error'); })
    .finally(function(){ btn.disabled=false; btn.innerHTML='<span>✉️</span> Generate Cover Letter'; });
});
$('clCopyBtn').addEventListener('click',function(){ if(clLetterText)navigator.clipboard.writeText(clLetterText).then(function(){showToast('Copied!','success');}); });
$('clDownloadBtn').addEventListener('click',function(){ if(!clLetterText)return;
  var blob=new Blob([clLetterText],{type:'text/plain'}); var url=URL.createObjectURL(blob);
  var a=document.createElement('a'); a.href=url; a.download=slugify($('clCompany').value||'company')+'_cover_letter.txt'; a.click(); URL.revokeObjectURL(url);
});
$('clResetBtn').addEventListener('click',function(){ clLetterText=''; $('clForm').reset(); $('clResumeFile').value='';
  $('clUploadIdle').classList.remove('hidden'); $('clUploadDone').classList.add('hidden'); showInTab(clSections,$('sectionCL')); });

// ══════════════════════════════════════════
//  JD ANALYSER
// ══════════════════════════════════════════
var jdSections=[$('sectionJD'),$('sectionJDResult')];
$('jdForm').addEventListener('submit',function(e){
  e.preventDefault();
  var jd=$('jdText').value.trim();
  if(jd.length<50){showToast('Paste a full job description (50+ chars).','error');return;}
  if(!$('jdResumeFile').files[0]){showToast('Upload your resume PDF.','error');return;}
  var btn=$('jdAnalyzeBtn'); btn.disabled=true; btn.innerHTML='<span>⏳</span> Analysing...';
  var fd=new FormData();
  fd.append('job_description',jd); fd.append('company_name',$('jdCompany').value.trim()); fd.append('resume',$('jdResumeFile').files[0]);
  authedFetch('/api/analyze-jd',{method:'POST',body:fd})
    .then(function(res){ if(res.status===402)return handle402(res); if(!res.ok)return res.json().then(function(d){throw new Error(d.detail||'Error');}); return res.json(); })
    .then(function(data){ renderJd(data); showInTab(jdSections,$('sectionJDResult')); showToast('Analysis complete!','success'); refreshAccount(); })
    .catch(function(err){ if(!(err&&err.handled))showToast(err.message||'Failed.','error'); })
    .finally(function(){ btn.disabled=false; btn.innerHTML='<span>📋</span> Analyse My Fit'; });
});
function renderJd(data){
  var score=data.fit_score||0, ats=data.ats_score||0, circ=251.2;
  var ring=$('jdRingFill'); ring.style.strokeDashoffset=circ; setTimeout(function(){ring.style.strokeDashoffset=circ-(circ*score/100);},80);
  $('jdScore').textContent=score; $('jdVerdict').textContent=data.fit_verdict||'—'; $('jdSummary').textContent=data.match_summary||'';
  var co=$('jdCompany').value.trim(); $('jdCompanyDisplay').textContent=(co?co+' · ':'')+'ATS + Fit Analysis';
  $('jdAtsFill').style.width='0%'; setTimeout(function(){$('jdAtsFill').style.width=ats+'%';},80); $('jdAtsPct').textContent=ats+'%';
  pills('jdMatchedSkills',data.matched_skills,'matched'); pills('jdMissingSkills',data.missing_skills,'missing'); pills('jdKeywords',data.keywords_to_add,'keyword');
  bullets('jdSelling',data.top_selling_points); bullets('jdInterviewFocus',data.interview_focus);
  $('jdPitch').textContent=data.tailored_pitch||''; $('jdAdvice').textContent=data.resume_advice||'';
  $('jdPitchCopy').onclick=function(){var t=data.tailored_pitch||'';if(t)navigator.clipboard.writeText(t).then(function(){showToast('Pitch copied!','success');});};
}
function pills(id,items,cls){var el=$(id);items=items||[];el.innerHTML=items.length?items.map(function(s){return '<span class="skill-pill '+cls+'">'+escHtml(s)+'</span>';}).join(''):'<span style="font-size:12px;color:var(--gray-600)">None detected</span>';}
function bullets(id,items){var el=$(id);items=items||[];el.innerHTML=items.map(function(s){return '<li>'+escHtml(s)+'</li>';}).join('');}
$('jdResetBtn').addEventListener('click',function(){$('jdForm').reset();$('jdResumeFile').value='';$('jdUploadIdle').classList.remove('hidden');$('jdUploadDone').classList.add('hidden');showInTab(jdSections,$('sectionJD'));});

// ══════════════════════════════════════════
//  COMPARE
// ══════════════════════════════════════════
var cmpSections=[$('sectionCompare'),$('sectionCmpResult')];
$('cmpForm').addEventListener('submit',function(e){
  e.preventDefault();
  var a=$('cmpA').value.trim(), b=$('cmpB').value.trim();
  if(!a||!b){showToast('Enter both companies.','error');return;}
  if(!$('cmpResumeFile').files[0]){showToast('Upload your resume PDF.','error');return;}
  var btn=$('cmpBtn'); btn.disabled=true; btn.innerHTML='<span>⏳</span> Comparing...';
  var fd=new FormData(); fd.append('company_a',a); fd.append('company_b',b); fd.append('resume',$('cmpResumeFile').files[0]);
  authedFetch('/api/compare',{method:'POST',body:fd})
    .then(function(res){ if(res.status===402)return handle402(res); if(!res.ok)return res.json().then(function(d){throw new Error(d.detail||'Error');}); return res.json(); })
    .then(function(data){ renderCompare(data); showInTab(cmpSections,$('sectionCmpResult')); showToast('Comparison ready!','success'); refreshAccount(); })
    .catch(function(err){ if(!(err&&err.handled))showToast(err.message||'Failed.','error'); })
    .finally(function(){ btn.disabled=false; btn.innerHTML='<span>⚖️</span> Compare Companies'; });
});
function compCard(c,isWinner){
  c=c||{};
  var pros=(c.pros||[]).map(function(p){return '<li class="cmp-pro">'+escHtml(p)+'</li>';}).join('');
  var cons=(c.cons||[]).map(function(p){return '<li class="cmp-con">'+escHtml(p)+'</li>';}).join('');
  return '<div class="cmp-card'+(isWinner?' cmp-winner':'')+'">'
    +(isWinner?'<div class="cmp-win-badge">★ Better Fit</div>':'')
    +'<div class="cmp-name">'+escHtml(c.name||'')+'</div>'
    +'<div class="cmp-score">'+(c.fit_score||0)+'<span>/100</span></div>'
    +'<div class="cmp-meta">'+escHtml(c.comp_estimate||'')+'</div>'
    +'<div class="cmp-culture">'+escHtml(c.culture||'')+'</div>'
    +'<ul class="cmp-list">'+pros+cons+'</ul>'
    +'<div class="cmp-growth">📈 '+escHtml(c.growth||'')+'</div></div>';
}
function renderCompare(data){
  var a=data.company_a||{}, b=data.company_b||{}, winner=data.winner||'';
  $('cmpGrid').innerHTML=compCard(a,winner&&winner===a.name)+compCard(b,winner&&winner===b.name);
  $('cmpWinner').textContent=winner?('Winner: '+winner):'';
  $('cmpVerdict').textContent=data.verdict||'';
  bullets('cmpFactors',data.decision_factors);
}
$('cmpResetBtn').addEventListener('click',function(){$('cmpForm').reset();$('cmpResumeFile').value='';$('cmpUploadIdle').classList.remove('hidden');$('cmpUploadDone').classList.add('hidden');showInTab(cmpSections,$('sectionCompare'));});

// ══════════════════════════════════════════
//  SALARY
// ══════════════════════════════════════════
var salSections=[$('sectionSalary'),$('sectionSalResult')];
$('salForm').addEventListener('submit',function(e){
  e.preventDefault();
  var c=$('salCompany').value.trim(), r=$('salRole').value.trim();
  if(!c||!r){showToast('Enter company and role.','error');return;}
  if(!$('salResumeFile').files[0]){showToast('Upload your resume PDF.','error');return;}
  var btn=$('salBtn'); btn.disabled=true; btn.innerHTML='<span>⏳</span> Estimating...';
  var fd=new FormData(); fd.append('company_name',c); fd.append('job_role',r); fd.append('location',$('salLocation').value.trim()); fd.append('resume',$('salResumeFile').files[0]);
  authedFetch('/api/salary',{method:'POST',body:fd})
    .then(function(res){ if(res.status===402)return handle402(res); if(!res.ok)return res.json().then(function(d){throw new Error(d.detail||'Error');}); return res.json(); })
    .then(function(data){ renderSalary(data); showInTab(salSections,$('sectionSalResult')); showToast('Estimate ready!','success'); })
    .catch(function(err){ if(!(err&&err.handled))showToast(err.message||'Failed.','error'); })
    .finally(function(){ btn.disabled=false; btn.innerHTML='<span>💰</span> Estimate Salary'; });
});
function fmtMoney(n,cur){ if(!n)return '—'; var s=Number(n).toLocaleString('en-IN'); return (cur==='USD'?'$':'₹')+s; }
function renderSalary(d){
  var cur=d.currency||'INR';
  $('salTitle').textContent=(d.level_guess?d.level_guess+' · ':'')+'Salary Estimate';
  $('salMeta').textContent=d.role+' @ '+d.company+(d.location?' · '+d.location:'');
  $('salBands').innerHTML=
    '<div class="sal-band"><div class="sal-band-label">Base Salary</div><div class="sal-band-val">'+fmtMoney(d.base_low,cur)+' – '+fmtMoney(d.base_high,cur)+'</div></div>'
   +'<div class="sal-band sal-band-total"><div class="sal-band-label">Total Comp</div><div class="sal-band-val">'+fmtMoney(d.total_low,cur)+' – '+fmtMoney(d.total_high,cur)+'</div></div>'
   +'<div class="sal-band"><div class="sal-band-label">Confidence</div><div class="sal-band-val">'+escHtml(d.data_confidence||'—')+'</div></div>';
  $('salBreakdown').textContent=d.breakdown||''; bullets('salTips',d.negotiation_tips); $('salNote').textContent=d.notes||'';
}
$('salResetBtn').addEventListener('click',function(){$('salForm').reset();$('salResumeFile').value='';$('salUploadIdle').classList.remove('hidden');$('salUploadDone').classList.add('hidden');showInTab(salSections,$('sectionSalary'));});

// ══════════════════════════════════════════
//  TRACKER
// ══════════════════════════════════════════
var STATUS_COLS=[['saved','Saved'],['applied','Applied'],['interviewing','Interviewing'],['offer','Offer'],['rejected','Rejected']];
$('trackerAddBtn').addEventListener('click',function(){ $('trackerForm').classList.toggle('hidden'); });
$('trCancelBtn').addEventListener('click',function(){ $('trackerForm').classList.add('hidden'); $('trackerForm').reset(); });
$('trackerForm').addEventListener('submit',function(e){
  e.preventDefault();
  var company=$('trCompany').value.trim();
  if(!company){showToast('Enter a company.','error');return;}
  var body={company:company,role:$('trRole').value.trim(),status:$('trStatus').value,notes:$('trNotes').value.trim()};
  authedFetch('/api/applications',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(res){if(!res.ok)throw new Error();return res.json();})
    .then(function(){ $('trackerForm').reset(); $('trackerForm').classList.add('hidden'); showToast('Application added!','success'); loadTracker(); })
    .catch(function(e){ if(!(e&&e.handled))showToast('Could not add.','error'); });
});
function loadTracker(){
  var board=$('trackerBoard'); board.innerHTML='<div class="history-loading">Loading...</div>';
  authedFetch('/api/applications').then(function(res){if(res.ok)return res.json();}).then(function(apps){
    if(!apps)return;
    if(!apps.length){board.innerHTML='<div class="history-empty">No applications yet.<br>Click "+ Add Application" to start tracking.</div>';return;}
    board.innerHTML=STATUS_COLS.map(function(col){
      var items=apps.filter(function(a){return a.status===col[0];});
      var cards=items.map(function(a){
        return '<div class="tr-card" data-id="'+a.id+'">'
          +'<div class="tr-card-company">'+escHtml(a.company)+'</div>'
          +(a.role?'<div class="tr-card-role">'+escHtml(a.role)+'</div>':'')
          +(a.notes?'<div class="tr-card-notes">'+escHtml(a.notes)+'</div>':'')
          +'<div class="tr-card-actions">'
          +'<select class="tr-move" onchange="moveApp(\''+a.id+'\',this.value)">'+STATUS_COLS.map(function(c){return '<option value="'+c[0]+'"'+(c[0]===a.status?' selected':'')+'>'+c[1]+'</option>';}).join('')+'</select>'
          +'<button class="tr-del" onclick="delApp(\''+a.id+'\')">✕</button>'
          +'</div></div>';
      }).join('');
      return '<div class="tr-col"><div class="tr-col-head">'+col[1]+' <span class="tr-count">'+items.length+'</span></div>'+(cards||'<div class="tr-col-empty">—</div>')+'</div>';
    }).join('');
  }).catch(function(){});
}
window.moveApp=function(id,status){
  authedFetch('/api/applications/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:status})})
    .then(function(res){if(res.ok){showToast('Moved to '+status+'.','success');loadTracker();}}).catch(function(){});
};
window.delApp=function(id){
  authedFetch('/api/applications/'+id,{method:'DELETE'}).then(function(res){if(res.ok){showToast('Removed.');loadTracker();}}).catch(function(){});
};

// ══════════════════════════════════════════
//  HISTORY
// ══════════════════════════════════════════
var historyPanel=$('historyPanel');
$('historyToggle').addEventListener('click',function(){ historyPanel.classList.toggle('hidden'); if(!historyPanel.classList.contains('hidden'))loadHistory(); });
$('historyClose').addEventListener('click',function(){historyPanel.classList.add('hidden');});
function loadHistory(){
  var list=$('historyList'); list.innerHTML='<div class="history-loading">Loading...</div>';
  authedFetch('/api/history?limit=30').then(function(res){if(res.ok)return res.json();}).then(function(items){
    if(!items)return;
    if(!items.length){list.innerHTML='<div class="history-empty">No past reports yet.<br>Generate your first report!</div>';return;}
    list.innerHTML=items.map(function(it){
      var date=fmtDate(it.created_at);
      var dl=it.status==='complete'
        ? '<button class="hi-btn" onclick="dlHist(\''+it.job_id+'\',\'pdf\',\''+slugify(it.company_name)+'\')">PDF</button>'
        + '<button class="hi-btn" onclick="dlHist(\''+it.job_id+'\',\'md\',\''+slugify(it.company_name)+'\')">MD</button>'
        + '<button class="hi-btn" onclick="dlHist(\''+it.job_id+'\',\'ppt\',\''+slugify(it.company_name)+'\')">PPT</button>'
        : '';
      return '<div class="history-item '+it.status+'"><div class="hi-top"><span class="hi-company">'+escHtml(it.company_name)+'</span><span class="hi-date">'+date+'</span></div>'
        +'<span class="hi-status '+it.status+'">'+it.status+'</span>'
        +'<div class="hi-actions">'+dl+'<button class="hi-btn hi-btn-del" onclick="delHist(this,\''+it.job_id+'\')">Delete</button></div></div>';
    }).join('');
  }).catch(function(){ list.innerHTML='<div class="history-empty">Could not load history.</div>'; });
}
window.dlHist=function(jobId,type,slug){ var ext=type==='ppt'?'_ppt_prompt.txt':(type==='md'?'_report.md':'_report.pdf'); downloadAuthed('/api/download/'+jobId+'/'+type,slug+ext); };
window.delHist=function(btn,jobId){
  btn.disabled=true; btn.textContent='...';
  authedFetch('/api/jobs/'+jobId,{method:'DELETE'}).then(function(res){if(!res.ok)throw new Error();
    var el=btn.closest('.history-item'); el.style.opacity='0'; el.style.transition='opacity .25s'; setTimeout(function(){el.remove();showToast('Deleted.');},250);
  }).catch(function(e){ btn.disabled=false; btn.textContent='Delete'; if(!(e&&e.handled))showToast('Could not delete.','error'); });
};

// ══════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════
function slugify(s){ return String(s||'').toLowerCase().replace(/\s+/g,'_').replace(/[^a-z0-9_]/g,'').slice(0,30)||'report'; }
function escHtml(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmtDate(iso){ if(!iso)return ''; try{var d=new Date(iso.endsWith('Z')?iso:iso+'Z');return d.toLocaleDateString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}catch(_){return iso.slice(0,16).replace('T',' ');} }

// ══════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════
(function init(){
  setAuthMode('login');
  // Prefill referral code from URL (?ref=CODE)
  var params = new URLSearchParams(window.location.search);
  var ref = params.get('ref');
  if (ref) { setAuthMode('signup'); authRef.value = ref; }

  if (!token) { showAuth(); return; }
  // Validate token
  authedFetch('/api/auth/me').then(function(res){
    if (!res.ok) { handleLogout(false); return; }
    return res.json();
  }).then(function(data){ if(data){ currentUser=data.user; renderAccount(data); } })
    .catch(function(){});
})();
