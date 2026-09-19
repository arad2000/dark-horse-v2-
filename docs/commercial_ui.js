/* commercial_ui.js — server-authoritative auth + OTP + credit gate + payment UI + admin feedback */
(function (global) {
  'use strict';
  var USER_KEY='dh_local_user_v1',QUOTA_KEY='dh_local_quota_v1',BUSY=false;
  function el(id){return document.getElementById(id);} function text(v){return String(v==null?'':v);} function digits(v){return text(v).replace(/[۰-۹]/g,function(d){return String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d));});} function escapeHtml(v){return text(v).replace(/&/g,'&').replace(/</g,'<').replace(/>/g,'>').replace(/"/g,'"');}
  function saveLocalUser(u){try{localStorage.setItem(USER_KEY,JSON.stringify(u||null));}catch(_){}} function clearLocalUser(){try{localStorage.removeItem(USER_KEY);}catch(_){}} function setLocalQuota(q){try{localStorage.setItem(QUOTA_KEY,JSON.stringify(q||{}));}catch(_){} }
  function setBusy(b,t,n,x){if(!b)return;b.disabled=!!x;b.textContent=x?t:n;b.style.opacity=x?'.72':'';}
  function addStyles(){if(el('dh-commercial-styles'))return;var s=document.createElement('style');s.id='dh-commercial-styles';s.textContent='.dh-commercial-overlay{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.78);display:flex;align-items:center;justify-content:center;padding:16px;backdrop-filter:blur(9px)}.dh-commercial-modal{width:100%;max-width:440px;background:#161622;border:1px solid rgba(212,175,55,.45);border-radius:22px;padding:22px;box-shadow:0 25px 80px rgba(0,0,0,.62);color:#eee;max-height:92vh;overflow:auto}.dh-commercial-title{color:#f0c040;text-align:center;margin:0 0 8px;font-size:1.4rem;font-weight:850}.dh-commercial-sub{color:#b7ad98;text-align:center;font-size:.88rem;line-height:1.9;margin:0 0 14px}.dh-commercial-label{display:block;color:#d7caa9;font-size:.82rem;margin:10px 2px 5px;text-align:right}.dh-commercial-field{position:relative}.dh-commercial-input{width:100%;box-sizing:border-box;padding:13px 14px;border-radius:12px;border:1px solid #353545;background:#0f0f18;color:#fff;font:inherit;outline:none}.dh-commercial-input:focus{border-color:rgba(240,192,64,.78);box-shadow:0 0 0 3px rgba(240,192,64,.1)}.dh-commercial-input.has-toggle{padding-left:48px}.dh-commercial-toggle{position:absolute;left:8px;top:50%;transform:translateY(-50%);width:34px;height:34px;border:0;border-radius:9px;background:transparent;color:#b8ad94;cursor:pointer}.dh-commercial-actions{display:flex;gap:9px;margin-top:16px}.dh-commercial-actions .btn{flex:1;margin:0;min-height:48px}.dh-commercial-error{color:#ff8787;min-height:1.45em;font-size:.83rem;line-height:1.7;margin-top:8px;text-align:right}.dh-commercial-note{color:#8f845f;font-size:.77rem;line-height:1.8;margin-top:11px;text-align:center}.dh-commercial-price{font-size:2rem;color:#f0c040;font-weight:850;text-align:center;margin:6px 0}.dh-commercial-pack{background:#10101a;border:1px solid rgba(212,175,55,.22);border-radius:14px;padding:14px;margin:12px 0;color:#cbb98a;line-height:2.05;text-align:center}.dh-commercial-pack .badge{display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.22);font-size:.72rem;color:#e0c876;margin-bottom:5px}.dh-commercial-link{background:none;border:0;color:#d4af37;text-decoration:underline;cursor:pointer;font:inherit;padding:6px}.dh-commercial-divider{height:1px;background:rgba(255,255,255,.07);margin:14px 0 10px}.dh-commercial-status{display:flex;align-items:center;justify-content:center;gap:8px;font-size:.8rem;color:#9f957f;margin-top:10px}.dh-commercial-spinner{width:14px;height:14px;border:2px solid rgba(240,192,64,.2);border-top-color:#f0c040;border-radius:50%;animation:dhspin .8s linear infinite}.dh-otp-box{display:flex;gap:8px;justify-content:center;direction:ltr;margin:14px 0}.dh-otp-box input{width:46px;height:54px;text-align:center;font-size:1.35rem;font-weight:800;border-radius:12px}@keyframes dhspin{to{transform:rotate(360deg)}}';document.head.appendChild(s);}
  function closeModal(){var o=el('dh-commercial-overlay');if(o)o.remove();} function showModal(html){addStyles();closeModal();var o=document.createElement('div');o.id='dh-commercial-overlay';o.className='dh-commercial-overlay';o.innerHTML='<div class="dh-commercial-modal">'+html+'</div>';o.addEventListener('click',function(e){if(e.target===o&&!BUSY)closeModal();});document.body.appendChild(o);return o;}
  function addPasswordToggle(i,b){var input=el(i),btn=el(b);if(!input||!btn)return;btn.onclick=function(){var v=input.type==='text';input.type=v?'password':'text';btn.textContent=v?'◉':'◉̸';};}
  function showOtpModal(reg){var o=showModal('<h2 class="dh-commercial-title">تأیید شماره موبایل</h2><p class="dh-commercial-sub">کد ۶ رقمی ارسال‌شده به شماره <strong dir="ltr">'+escapeHtml(reg.phone)+'</strong> را وارد کنید.</p><div class="dh-otp-box">'+[1,2,3,4,5,6].map(function(i){return '<input id="dh-otp-'+i+'" class="dh-commercial-input" inputmode="numeric" maxlength="1" autocomplete="one-time-code">';}).join('')+'</div><div id="dh-otp-err" class="dh-commercial-error"></div><div id="dh-otp-timer" class="dh-otp-timer">اعتبار کد: ۵:۰۰</div><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-otp-submit">تأیید و ساخت حساب</button><button type="button" class="btn" id="dh-otp-cancel">انصراف</button></div><p class="dh-commercial-note">کد یک‌بارمصرف ۵ دقیقه معتبر است و تلاش‌های ناموفق محدود هستند.</p>');var fs=[1,2,3,4,5,6].map(function(i){return el('dh-otp-'+i);});fs.forEach(function(f,i){f.addEventListener('input',function(){f.value=digits(f.value).replace(/\D/g,'').slice(0,1);if(f.value&&fs[i+1])fs[i+1].focus();});f.addEventListener('keydown',function(e){if(e.key==='Backspace'&&!f.value&&fs[i-1])fs[i-1].focus();});});fs[0].focus();var n=Number(reg.expires_in||300),tm=el('dh-otp-timer'),iv=setInterval(function(){n--;if(n<=0){clearInterval(iv);if(tm)tm.textContent='کد منقضی شده است.';}else if(tm)tm.textContent='اعتبار کد: '+Math.floor(n/60)+':'+String(n%60).padStart(2,'0');},1000);el('dh-otp-cancel').onclick=function(){clearInterval(iv);closeModal();};el('dh-otp-submit').onclick=async function(){if(BUSY)return;BUSY=true;var b=el('dh-otp-submit'),err=el('dh-otp-err');setBusy(b,'در حال تأیید…','تأیید و ساخت حساب',true);var code=fs.map(function(f){return f.value;}).join('');if(code.length!==6){if(err)err.textContent='کد ۶ رقمی را کامل وارد کنید.';BUSY=false;setBusy(b,'','تأیید و ساخت حساب',false);return;}try{var d=await global.DHAuth.verifyRegistration(reg.challenge_id,code);if(d&&d.user)saveLocalUser(d.user);if(d&&typeof d.quota==='number')setLocalQuota({remaining:d.quota});clearInterval(iv);closeModal();await continueAfterAuth();}catch(e){if(err)err.textContent=text(e&&e.message?e.message:e)||'تأیید کد ناموفق بود.';BUSY=false;setBusy(b,'','تأیید و ساخت حساب',false);}};}
  function showAuthModal(initial){var mode=initial==='login'?'login':'register',o=showModal('');function paint(){var title=mode==='login'?'ورود به حساب':'ساخت حساب',action=mode==='login'?'ورود':'ثبت‌نام';o.querySelector('.dh-commercial-modal').innerHTML='<h2 class="dh-commercial-title">'+title+'</h2><p class="dh-commercial-sub">'+(mode==='login'?'با شماره موبایل و رمز عبور وارد حساب خود شوید.':'برای ساخت حساب، شماره موبایل خود را با کد پیامکی تأیید کنید.')+'</p>'+(mode==='register'?'<label class="dh-commercial-label" for="dh-c-name">نام و نام خانوادگی</label><input id="dh-c-name" class="dh-commercial-input" autocomplete="name" placeholder="نام و نام خانوادگی">':'')+'<label class="dh-commercial-label" for="dh-c-phone">شماره موبایل</label><input id="dh-c-phone" class="dh-commercial-input" type="tel" inputmode="numeric" dir="ltr" placeholder="09xxxxxxxxx" autocomplete="tel"><label class="dh-commercial-label" for="dh-c-pass">رمز عبور</label><div class="dh-commercial-field"><input id="dh-c-pass" class="dh-commercial-input has-toggle" type="password" placeholder="حداقل ۸ کاراکتر" autocomplete="current-password"><button type="button" class="dh-commercial-toggle" id="dh-c-pass-toggle" aria-label="نمایش رمز عبور">◉</button></div><div id="dh-c-err" class="dh-commercial-error"></div><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-c-submit">'+action+'</button><button type="button" class="btn" id="dh-c-close">انصراف</button></div><p class="dh-commercial-note">احراز هویت و اعتباردهی در سرور انجام می‌شود.</p><div style="text-align:center;margin-top:4px"><button type="button" class="dh-commercial-link" id="dh-c-switch">'+(mode==='login'?'ساخت حساب جدید':'حساب دارم؛ ورود')+'</button></div>';addPasswordToggle('dh-c-pass','dh-c-pass-toggle');el('dh-c-close').onclick=function(){if(!BUSY)closeModal();};el('dh-c-switch').onclick=function(){if(!BUSY){mode=mode==='login'?'register':'login';paint();}};el('dh-c-submit').onclick=async function(){if(BUSY)return;BUSY=true;var b=el('dh-c-submit'),err=el('dh-c-err');setBusy(b,mode==='login'?'در حال ورود…':'در حال ارسال کد…',action,true);var phone=digits(el('dh-c-phone').value).replace(/\s+/g,''),pass=el('dh-c-pass').value,name=mode==='register'?el('dh-c-name').value.trim():'';if(mode==='register'&&name.length<2){if(err)err.textContent='نام را کامل وارد کنید.';BUSY=false;setBusy(b,'',action,false);return;}if(!/^09\d{9}$/.test(phone)){if(err)err.textContent='شماره موبایل را به‌صورت 09xxxxxxxxx وارد کنید.';BUSY=false;setBusy(b,'',action,false);return;}if(pass.length<8){if(err)err.textContent='رمز عبور باید حداقل ۸ کاراکتر باشد.';BUSY=false;setBusy(b,'',action,false);return;}try{if(mode==='login'){var d=await global.DHAuth.login(phone,pass);if(d.user)saveLocalUser(d.user);if(typeof d.quota==='number')setLocalQuota({remaining:d.quota});closeModal();await continueAfterAuth();}else{var c=await global.DHAuth.register(name,phone,pass);closeModal();showOtpModal({phone:phone,challenge_id:c.challenge_id,expires_in:c.expires_in});}}catch(e){if(err)err.textContent=text(e&&e.message?e.message:e)||'خطا در ارتباط با سرور.';}finally{BUSY=false;if(el('dh-c-submit'))setBusy(el('dh-c-submit'),'',action,false);};};}paint();}
  function paymentErrorText(e){var m=text(e&&e.message?e.message:e);if(/merchant|not configured|credential|authority/i.test(m))return 'درگاه هنوز آماده تراکنش نیست؛ وضعیت Merchant ID و فعال‌سازی زرین‌پال را بررسی کنید.';if(/timeout|network|failed to fetch/i.test(m))return 'ارتباط با درگاه برقرار نشد؛ اتصال شبکه یا وضعیت سرویس زرین‌پال را بررسی کنید.';return m||'ایجاد درخواست پرداخت ناموفق بود.';}
  function openExternalPay(url){
    if(!url)return false;
    var u=String(url);
    var isAndroid=/android/i.test(navigator.userAgent||'');
    if(isAndroid){
      try{window.location.href='intent://'+u.replace(/^https?:\/\//,'')+'#Intent;scheme=https;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;end';return true;}catch(_){}
      try{window.location.href='intent://'+u.replace(/^https?:\/\//,'')+'#Intent;scheme=https;package=com.android.chrome;end';return true;}catch(_){}
    }
    try{var w=window.open(u,'_blank');if(w)return true;}catch(_){}
    try{window.location.assign(u);return true;}catch(_){}
    try{window.location.href=u;return true;}catch(_){}
    return false;
  }
  function showPayFallback(url){
    var e=el('dh-buy-err');
    if(!e)return;
    e.style.color='#f0c040';
    e.innerHTML=
      '<div style="text-align:center;line-height:1.7;margin-bottom:6px">درگاه در اپ باز نشد — یکی را بزنید:</div>'+
      '<button type="button" id="dh-pay-intent" class="btn btn-primary" style="width:100%;margin-top:8px;padding:14px;font-weight:800">باز کردن با مرورگر سیستم</button>'+
      '<button type="button" id="dh-pay-chrome" class="btn" style="width:100%;margin-top:8px;padding:12px">باز کردن در کروم</button>'+
      '<button type="button" id="dh-pay-copy" class="btn" style="width:100%;margin-top:8px;padding:12px">کپی لینک پرداخت</button>'+
      '<textarea id="dh-pay-url" readonly style="width:100%;margin-top:10px;min-height:70px;font-size:11px;direction:ltr;text-align:left;padding:8px;border-radius:10px;background:#0d0d14;color:#d7caa9;border:1px solid rgba(212,175,55,.35)"></textarea>'+
      '<div style="margin-top:6px;font-size:.78rem;color:#b7ad98;text-align:center">یا لینک را در کروم بچسبانید</div>';
    var ta=el('dh-pay-url');
    if(ta)ta.value=url;
    function goChrome(){try{window.location.href='intent://'+String(url).replace(/^https?:\/\//,'')+'#Intent;scheme=https;package=com.android.chrome;end';}catch(_){openExternalPay(url);}}
    function goIntent(){try{window.location.href='intent://'+String(url).replace(/^https?:\/\//,'')+'#Intent;scheme=https;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;end';}catch(_){openExternalPay(url);}}
    var b1=el('dh-pay-intent');if(b1)b1.onclick=function(ev){if(ev){ev.preventDefault();ev.stopPropagation();}goIntent();};
    var b2=el('dh-pay-chrome');if(b2)b2.onclick=function(ev){if(ev){ev.preventDefault();ev.stopPropagation();}goChrome();};
    var b3=el('dh-pay-copy');if(b3)b3.onclick=function(ev){if(ev){ev.preventDefault();ev.stopPropagation();}var done=false;try{if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(function(){alert('لینک کپی شد. کروم را باز کنید و Paste کنید.');});done=true;}}catch(_){}if(!done){try{var t=el('dh-pay-url');if(t){t.focus();t.select();document.execCommand('copy');alert('لینک کپی شد.');done=true;}}catch(__){}}if(!done)alert('لینک پایین را نگه دارید و Copy کنید.');};
  }

  function openPurchaseModal(){
    BUSY=false;
    try{closeModal();}catch(_){}
    showModal(
      '<h2 class="dh-commercial-title">خرید بسته ۳ تست</h2>'+
      '<p class="dh-commercial-sub">پرداخت امن از طریق زرین‌پال (محیط تست)</p>'+
      '<div class="dh-commercial-pack"><span class="badge">بسته استاندارد</span>'+
      '<div class="dh-commercial-price">۲۴۹٬۰۰۰ تومان</div><div>۳ تست · بدون تاریخ انقضا</div></div>'+
      '<p class="dh-commercial-sub">مبلغ فقط از سمت سرور تعیین می‌شود.</p>'+
      '<div id="dh-buy-err" class="dh-commercial-error"></div>'+
      '<div id="dh-buy-status" class="dh-commercial-status" hidden><span class="dh-commercial-spinner" id="dh-buy-spin"></span><span id="dh-buy-status-text">در حال دریافت لینک پرداخت…</span></div>'+
      '<div class="dh-commercial-actions">'+
        '<button type="button" class="btn btn-primary" id="dh-buy-now">پرداخت</button>'+
        '<button type="button" class="btn" id="dh-buy-close">بستن</button>'+
      '</div>'+
      '<p class="dh-commercial-note">پس از پرداخت موفق، ۳ اعتبار به حساب اضافه می‌شود.</p>'
    );
    function unlock(){BUSY=false;try{var b=el('dh-buy-now');if(b){b.disabled=false;setBusy(b,'','پرداخت',false);}}catch(_){}try{var s=el('dh-buy-status');if(s)s.hidden=true;}catch(_){}
    }
    el('dh-buy-close').onclick=function(ev){if(ev){ev.preventDefault();ev.stopPropagation();}unlock();closeModal();};
    el('dh-buy-now').onclick=async function(ev){
      if(ev){ev.preventDefault();ev.stopPropagation();}
      if(BUSY)return;
      var b=el('dh-buy-now'),e=el('dh-buy-err'),s=el('dh-buy-status');
      if(e)e.textContent='';
      if(!global.DHAuth||!global.DHAuth.isLoggedIn()){closeModal();showAuthModal('login');return;}
      var payUrl=null;
      BUSY=true;
      if(s){s.hidden=false;s.style.color='';var st=el('dh-buy-status-text');if(st)st.textContent='در حال اتصال…';}
      setBusy(b,'…','پرداخت',true);
      try{
        var p=await global.DHAuth.createPayment();
        payUrl=(p&&(p.payment_url||p.paymentUrl||p.url))||'';
        if(!payUrl)throw new Error('آدرس درگاه از سرور نیامد.');
        if(s)s.hidden=true;
        openExternalPay(payUrl);
        unlock();
        showPayFallback(payUrl);
      }catch(x){if(e)e.textContent=paymentErrorText(x);if(s)s.hidden=true;unlock();}
    };
  }

  async function continueAfterAuth(){
    if(!global.DHAuth||!global.DHAuth.isLoggedIn()){showAuthModal('login');return;}
    try{
      var q=await global.DHAuth.quota(),r=Number(q&&q.credits_remaining||0);
      if(r<=0){await openPurchaseModal();return;}
      try{if(global.DHQuotaEnforcement&&typeof global.DHQuotaEnforcement.ensureJourneySession==='function')global.DHQuotaEnforcement.ensureJourneySession();}catch(_){}
      closeModal();
      if(global.DHShell&&typeof global.DHShell.startJourney==='function')global.DHShell.startJourney();
    }catch(e){var m=text(e&&e.message?e.message:e);if(/401|authentication/i.test(m)){global.DHAuth.logout();clearLocalUser();showAuthModal('login');return;}showModal('<h2 class="dh-commercial-title">خطا</h2><p class="dh-commercial-sub">'+escapeHtml(m)+'</p><div class="dh-commercial-actions"><button type="button" class="btn btn-primary" id="dh-error-close">باشه</button></div>');el('dh-error-close').onclick=closeModal;}
  }

  function doLogout(){
    try{if(global.DHAuth)global.DHAuth.logout();}catch(_){}
    try{localStorage.removeItem('dh_auth_v1');}catch(_){}
    try{clearLocalUser();}catch(_){}
    try{localStorage.removeItem(QUOTA_KEY);}catch(_){}
    try{localStorage.removeItem('dh_local_user_v1');}catch(_){}
    try{localStorage.removeItem('dh_local_quota_v1');}catch(_){}
    try{closeModal();}catch(_){}
    try{location.reload();}catch(_){}
  }
  function isAdminUser(){try{if(global.DHAuth&&typeof global.DHAuth.isAdmin==='function'&&global.DHAuth.isAdmin())return true;var u=global.DHAuth&&global.DHAuth.getUser&&global.DHAuth.getUser();return !!(u&&(u.role==='admin'||u.role==='support'||u.is_admin===true));}catch(_){return false;}}
  function ensureAdminFeedbackPanel(){
    if(!isAdminUser())return;
    if(el('dh-admin-feedback'))return;
    var out=el('dh-p-out');
    if(!out||!out.parentNode)return;
    var box=document.createElement('div');
    box.id='dh-admin-feedback';
    box.style.cssText='margin:14px 0 8px;padding:14px;border-radius:14px;border:1px solid rgba(212,175,55,.3);background:#12121c;text-align:right;';
    box.innerHTML=
      '<div style="color:#f0c040;font-weight:800;margin-bottom:10px;">پنل ادمین</div>'+
      '<div style="padding:12px;border:1px solid rgba(212,175,55,.24);border-radius:12px;background:#0f0f18;margin-bottom:12px;">'+
        '<div style="color:#f0c040;font-weight:800;margin-bottom:8px;">اعطای اعتبار</div>'+
        '<label for="dh-admin-grant-user-id" style="display:block;color:#cbb98a;font-size:.8rem;margin:7px 2px 4px;">user_id (شناسه عددی کاربر)</label>'+
        '<input id="dh-admin-grant-user-id" type="number" min="1" step="1" inputmode="numeric" autocomplete="off" placeholder="مثلاً 123" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;">'+
        '<label for="dh-admin-grant-plan" style="display:block;color:#cbb98a;font-size:.8rem;margin:9px 2px 4px;">plan_code</label>'+
        '<input id="dh-admin-grant-plan" value="pack_3_tests" maxlength="64" autocomplete="off" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;direction:ltr;text-align:left;">'+
        '<label for="dh-admin-grant-reason" style="display:block;color:#cbb98a;font-size:.8rem;margin:9px 2px 4px;">دلیل (اختیاری)</label>'+
        '<input id="dh-admin-grant-reason" value="هدیه مالک" maxlength="1000" autocomplete="off" style="width:100%;box-sizing:border-box;padding:11px 12px;border-radius:10px;border:1px solid #333;background:#0b0b12;color:#eee;font:inherit;">'+
        '<div id="dh-admin-grant-msg" style="min-height:1.5em;margin-top:8px;font-size:.82rem;line-height:1.7;"></div>'+
        '<button type="button" class="btn btn-primary" id="dh-admin-grant" style="width:100%;margin-top:8px;">اعطا</button>'+
      '</div>'+
      '<div id="dh-admin-dash" style="color:#b7ad98;font-size:.84rem;line-height:1.8;margin-bottom:8px;">در حال بارگذاری…</div>'+
      '<div id="dh-admin-list" style="max-height:300px;overflow:auto;font-size:.8rem;color:#d7caa9;line-height:1.7;"></div>'+
      '<button type="button" class="btn" id="dh-admin-refresh" style="width:100%;margin-top:10px;">بروزرسانی بازخوردها</button>';
    out.parentNode.insertBefore(box,out);

    async function load(){
      if(global.__dh_admin_loading)return;
      global.__dh_admin_loading=true;
      setTimeout(function(){global.__dh_admin_loading=false;},3000);
      var dash=el('dh-admin-dash'),list=el('dh-admin-list');
      if(!global.DHAuth||!global.DHAuth.adminFeedback){
        if(dash)dash.textContent='کلاینت ادمین آماده نیست';
        return;
      }
      try{
        var d=await global.DHAuth.adminDashboard();
        if(dash)dash.textContent='کاربران: '+(d.users_total||0)+' · بازخورد: '+(d.feedback_total||0)+' · پرداخت: '+(d.payments_total||0)+' · اعتبارها: '+(d.entitlements_total||0);
        var rows=await global.DHAuth.adminFeedback(40);
        if(!list)return;
        if(!rows||!rows.length){
          list.textContent='هنوز بازخوردی ثبت نشده است.';
          return;
        }
        list.innerHTML=rows.map(function(r){
          var title=r.suggested_major||r.exam_code||('#'+r.id);
          var scores='رضایت: '+(r.satisfaction_score!=null?r.satisfaction_score:'—')+' · دقت: '+(r.accuracy_rating!=null?r.accuracy_rating:'—')+' · توصیه: '+(r.would_recommend?'بله':'خیر');
          var c=text(r.comments||'').replace(/\\s*\\|?\\s*payload=.*$/,'').trim();
          var when=text(r.created_at||'').slice(0,19).replace('T',' ');
          return '<div style="border-top:1px solid rgba(255,255,255,.08);padding:9px 0;"><div style="color:#f0c040;font-weight:700;">'+escapeHtml(title)+'</div><div>'+escapeHtml(scores)+'</div><div style="color:#8f845f;font-size:.74rem;">'+escapeHtml(when)+'</div>'+(c?'<div style="margin-top:4px;color:#cbb98a;">'+escapeHtml(c.slice(0,220))+'</div>':'')+'</div>';
        }).join('');
      }catch(e){
        if(dash)dash.textContent=text(e&&e.message?e.message:e)||'خطا در بارگذاری پنل ادمین';
        if(list)list.textContent='';
      }
    }

    var grant=el('dh-admin-grant');
    if(grant)grant.onclick=async function(){
      if(global.__dh_admin_grant_loading)return;
      var userInput=el('dh-admin-grant-user-id');
      var planInput=el('dh-admin-grant-plan');
      var reasonInput=el('dh-admin-grant-reason');
      var msg=el('dh-admin-grant-msg');
      var userId=digits((userInput&&userInput.value)||'').replace(/\\D/g,'');
      var plan=text((planInput&&planInput.value)||'').trim()||'pack_3_tests';
      var reason=text((reasonInput&&reasonInput.value)||'').trim()||'هدیه مالک';
      if(!/^\\d+$/.test(userId)||Number(userId)<=0){
        if(msg){msg.style.color='#ff8787';msg.textContent='شناسه کاربر باید یک عدد صحیح مثبت باشد.';}
        if(userInput)userInput.focus();
        return;
      }
      global.__dh_admin_grant_loading=true;
      if(msg){msg.style.color='#b7ad98';msg.textContent='';}
      setBusy(grant,'در حال اعطا…','اعطا',true);
      try{
        if(!global.DHAuth||typeof global.DHAuth.adminGrantCredits!=='function')throw new Error('کلاینت اعطای اعتبار آماده نیست.');
        var result=await global.DHAuth.adminGrantCredits(Number(userId),plan,reason);
        var granted=Number(result&&result.credits_granted||0);
        var target=Number(result&&result.user_id||userId);
        if(msg){
          msg.style.color='#9fe3a2';
          msg.textContent=(granted>0?granted+' اعتبار به کاربر '+target+' اضافه شد.':'اعطای اعتبار با موفقیت ثبت شد.');
        }
        if(global.DHAuth&&typeof global.DHAuth.quota==='function'){
          try{await global.DHAuth.quota();}catch(_){}
        }
        await load();
      }catch(e){
        if(msg){
          msg.style.color='#ff8787';
          msg.textContent=text(e&&e.message?e.message:e)||'اعطای اعتبار ناموفق بود.';
        }
      }finally{
        global.__dh_admin_grant_loading=false;
        setBusy(grant,'','اعطا',false);
      }
    };

    var btn=el('dh-admin-refresh');
    if(btn)btn.onclick=function(){load();};
    load();
  }
  function installButtonHooks(){function patch(){
    document.querySelectorAll('#dh-start-journey,#dh-continue-journey,#dh-p-journey').forEach(function(b){
      if(b.__dhCommercialHooked)return;b.__dhCommercialHooked=true;
      b.onclick=function(e){if(e)e.preventDefault();continueAfterAuth();};
    });
    var buy=el('dh-p-buy');
    if(buy&&!buy.__dhCommercialHooked){buy.__dhCommercialHooked=true;buy.onclick=function(e){if(e)e.preventDefault();openPurchaseModal();};}
    var out=el('dh-p-out');if(out){out.onclick=function(e){if(e)e.preventDefault();doLogout();};
    }
    ensureAdminFeedbackPanel();
  }
  patch();
  var _obsT=null;
  new MutationObserver(function(){if(_obsT)return;_obsT=setTimeout(function(){_obsT=null;try{patch();}catch(_){}},500);}).observe(document.body,{childList:true,subtree:true});
  }

  function syncServerQuota(done){
    var now=Date.now();
    if(global.__dh_quota_last && (now-global.__dh_quota_last)<15000){if(done)done(null);return;}
    if(global.__dh_quota_busy){if(done)done(null);return;}
    if(!global.DHAuth||!global.DHAuth.isLoggedIn||!global.DHAuth.isLoggedIn()){if(done)done(null);return;}
    global.__dh_quota_busy=true;
    global.__dh_quota_last=now;
    global.DHAuth.quota().then(function(d){
      global.__dh_quota_busy=false;
      var r=Number(d&&d.credits_remaining);
      if(!isFinite(r)||r<0)r=0;
      var prev=null;
      try{prev=JSON.parse(localStorage.getItem(QUOTA_KEY)||'{}').serverRemaining;}catch(_){}
      if(prev!==r){try{if(global.DHShell&&typeof global.DHShell.renderProfile==='function')global.DHShell.renderProfile();}catch(_){}
      }
      if(done)done(r);
    }).catch(function(){global.__dh_quota_busy=false;if(done)done(null);});
  }

  function boot(){
    global.DHCommercialUI={showAuth:showAuthModal,showPurchase:openPurchaseModal,startServerAuthorizedJourney:continueAfterAuth,logout:doLogout,syncQuota:syncServerQuota};
    try{installButtonHooks();}catch(_){}
    try{handlePaymentReturn();}catch(_){}
    try{syncServerQuota();}catch(_){}
    setTimeout(function(){try{syncServerQuota();}catch(_){}},2000);
  }
  if (!global.DHCommercialUI) global.DHCommercialUI={showAuth:showAuthModal,showPurchase:openPurchaseModal,startServerAuthorizedJourney:continueAfterAuth,logout:doLogout,syncQuota:syncServerQuota};
  window.addEventListener('dh-open-purchase',function(){try{openPurchaseModal();}catch(e){console.error(e);}});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})(window);